"""Indikatoren uebereinander + MTF-Einstieg im LTF (Nutzerauftrag 26.11.2026, Idee "wie CTNL").

    python -m htf_daily_trade.indikator_mtf

Lock `indikator_mtf_ltf` (IS 2016-21, OOS bis 25.05.2026, Tresor zu). Kosten filter_matrix.MARKETS, ohne Swap.

Teil 1  Uebereinanderlegen / Risikoskalierung auf den Daily-Kombi-Trades (indikator_kombi_trades.csv):
        Score = Anzahl Zusatz-Bestaetigungen am Signaltag in Trade-Richtung (je 3 Tage Fenster):
        MACD-8/20/14-Cross, Stoch-K/D-Cross, BB-Band beruehrt, Schluss ausserhalb NW (+ ML >= 50 % bei Z0).
        Skalierung S1: Risiko 0,5 + 0,5 x Score (max 2).
Teil 2  MTF: Setup im HTF, Einstieg im LTF (H1, M15).
        HTF  HA Daily ML-Flaeche >= 50 % (3 T) | HB HA + Daily RSI-MA-Cross (3 T) = Kandidat
             HC Daily >= 2 von {ML >= 50 %, RSI-Cross, MACD-Cross, Stoch-Cross} (je 3 T)
             HD H4 >= 2 derselben (je 3 H4-Kerzen) | HE HA + H4 >= 1
        LTF  E0 erste Kerze im Setup (Kontrolle) | E1 BB(20,2): Tief unter Band, Schluss wieder drin
             E2 NW: Schluss zurueck in die Huelle | E3 E1 oder E2 | E4 LTF-RSI-MA-Cross
        Exit XA LTF-Stop (5-Kerzen-Extrem - 0,3 LTF-ATR), Ziel 3 R, max 10 Tage
             XB LTF-Stop, Zeitausstieg 10 Tage | XC Daily-Stop (5-Tage-Extrem - 0,2 D-ATR), 10 Tage
        Einstieg Open der Folgekerze. Je Markt und Seite ein offener Trade. Stop vor Ziel in derselben Kerze.
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd

from htf_daily_trade import h4_manip as hm
from htf_daily_trade import indikatoren as ind
from htf_daily_trade.backtest_r import stats
from htf_daily_trade.filter_matrix import MARKETS, load_market
from htf_daily_trade.ltf_entry import LTF_FILES, METAL_FILES
from research_lock import Lock, deflated_sharpe

LOCK = "indikator_mtf_ltf"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2021-12-31", "2026-05-25", "2026-11-25"
HTFS, LTFS, ENTRIES, EXITS = ("HA", "HB", "HC", "HD", "HE"), ("H1", "M15"), ("E0", "E1", "E2", "E3", "E4"), ("XA", "XB", "XC")
TF_HOURS = {"H1": 1.0, "M15": 0.25}
HOLD = pd.Timedelta(days=14)   # ~10 Handelstage


def ohlc(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"open": df["Open"].values, "high": df["High"].values, "low": df["Low"].values,
                         "close": df["Close"].values}, index=df.index)


def win(b, n=3):
    return pd.Series(b).astype(float).rolling(n, min_periods=1).max().fillna(0).astype(bool).to_numpy()


def htf_flags(df: pd.DataFrame) -> dict:
    """Bullische/baerische Bausteine je HTF-Kerze (Stand Kerzenschluss)."""
    a = ind.alle(df)
    f = {}
    for s, (ml, rc, mc, sc) in {"L": ("rsi_ml_os_area", "rsi_cross_up", "macd_cross_up", "stoch_cross_up"),
                                "S": ("rsi_ml_ob_area", "rsi_cross_dn", "macd_cross_dn", "stoch_cross_dn")}.items():
        f[f"ml_{s}"] = win(a[ml] >= 50)
        f[f"rsi_{s}"] = win(a[rc].fillna(False))
        f[f"macd_{s}"] = win(a[mc].fillna(False))
        f[f"stoch_{s}"] = win(a[sc].fillna(False))
        f[f"cnt_{s}"] = f[f"ml_{s}"].astype(int) + f[f"rsi_{s}"] + f[f"macd_{s}"] + f[f"stoch_{s}"]
    lo = (df["low"] <= a["bb_lower"]).to_numpy()
    hi = (df["high"] >= a["bb_upper"]).to_numpy()
    f["bb_L"], f["bb_S"] = win(lo), win(hi)
    f["nw_L"], f["nw_S"] = win((df["close"] < a["nw_lower"]).to_numpy()), win((df["close"] > a["nw_upper"]).to_numpy())
    f["atr"] = a["atr"].to_numpy()
    f["lo5"] = df["low"].rolling(5).min().to_numpy()
    f["hi5"] = df["high"].rolling(5).max().to_numpy()
    return f


# --------------------------------------------------------------------------- Teil 1
def teil1(lock: Lock) -> pd.DataFrame:
    t = pd.read_csv("htf_daily_trade/indikator_kombi_trades.csv", parse_dates=["datum"])
    t = t[t["variante"].isin(["Z2 G1 C0 X1", "Z1 G1 C0 X1", "Z0 G1 C0 X1"])].copy()
    parts = []
    for name, g in t.groupby("markt"):
        d = ohlc(load_market(name)).loc[:OOS_END]
        f = htf_flags(d)
        pos = d.index.get_indexer(pd.DatetimeIndex(g["datum"]))
        sd = np.where(g["seite"] == "long", "L", "S")
        g = g.copy()
        sc = np.zeros(len(g), int)
        for k in ("macd", "stoch", "bb", "nw"):
            sc += np.where(sd == "L", f[f"{k}_L"][pos], f[f"{k}_S"][pos]).astype(int)
        g["score"] = sc + np.where(g["variante"].str.startswith("Z0"),
                                   np.where(sd == "L", f["ml_L"][pos], f["ml_S"][pos]).astype(int), 0)
        parts.append(g)
    t = pd.concat(parts)
    t["periode"] = np.where(t["datum"] <= pd.Timestamp(IS_END), "IS", "OOS")
    t["w"] = np.clip(0.5 + 0.5 * t["score"], 0.5, 2.0)
    rows = []
    for (v, per), g in t.groupby(["variante", "periode"]):
        for s, gs in g.groupby(np.clip(g["score"], 0, 3)):
            rows.append({"variante": v, "periode": per, "score": f"{s}{'+' if s == 3 else ''}", "n": len(gs),
                         "R": gs["r"].mean()})
        flat_sr = g["r"].mean() / g["r"].std(ddof=1)
        wr = g["r"] * g["w"]
        rows.append({"variante": v, "periode": per, "score": "flach", "n": len(g), "R": g["r"].mean(), "sharpe": flat_sr})
        rows.append({"variante": v, "periode": per, "score": "skaliert S1", "n": len(g), "R": wr.sum() / g["w"].sum(),
                     "sharpe": wr.mean() / wr.std(ddof=1)})
    res = pd.DataFrame(rows)
    res.to_csv("htf_daily_trade/indikator_skalierung.csv", index=False)
    return res


# --------------------------------------------------------------------------- Teil 2
def load_ltf(name: str, tf: str) -> pd.DataFrame | None:
    files = METAL_FILES[tf].get(name) or [LTF_FILES[tf].format(m=name)]
    parts = []
    for fn in files:
        try:
            parts.append(pd.read_parquet(f"data_cache/combined/{fn}")[["Open", "High", "Low", "Close"]])
        except FileNotFoundError:
            return None
    d = pd.concat(parts).sort_index()
    d = d[~d.index.duplicated(keep="last")]
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    return d.loc[pd.Timestamp("2014-06-01", tz="UTC"):pd.Timestamp(OOS_END, tz="UTC") + HOLD]


def map_state(known: pd.DatetimeIndex, arr, at: pd.DatetimeIndex, fill=False):
    pos = known.searchsorted(at, side="right") - 1
    out = np.asarray(arr)[np.clip(pos, 0, None)]
    return np.where(pos >= 0, out, fill)


def run_market(name: str, tf: str) -> list[dict]:
    x = load_ltf(name, tf)
    if x is None:
        return []
    cost = MARKETS[name][2]
    d = ohlc(load_market(name)).loc[:OOS_END]
    fd = htf_flags(d)
    dk = (d.index + pd.Timedelta(days=1)).tz_localize("UTC")          # Tag bekannt ab Folgetag 00:00 UTC
    h = hm.h4(name)
    h = h[h.index <= pd.Timestamp(OOS_END, tz="UTC") + HOLD]
    fh = htf_flags(ohlc(h))
    hk = h.index + pd.Timedelta(hours=4)
    lt = ohlc(x)
    a = ind.alle(lt)
    o, hi, lo, c = (lt[k].to_numpy() for k in ("open", "high", "low", "close"))
    close_t = x.index + pd.Timedelta(hours=TF_HOURS[tf])              # Zeitpunkt Kerzenschluss
    n = len(o)
    atr_l = a["atr"].to_numpy()
    lo5, hi5 = lt["low"].rolling(5).min().to_numpy(), lt["high"].rolling(5).max().to_numpy()
    d_atr, d_lo5, d_hi5 = (map_state(dk, fd[k], close_t, np.nan) for k in ("atr", "lo5", "hi5"))
    # Zeitgrenze fuer Ausstieg
    end_idx = x.index.searchsorted(x.index + HOLD) - 1
    start = x.index.searchsorted(pd.Timestamp(IS_START, tz="UTC"))
    stop_at = x.index.searchsorted(pd.Timestamp(OOS_END, tz="UTC"))
    out = []
    for side, sg in (("L", 1), ("S", -1)):
        htf = {}
        ml = map_state(dk, fd[f"ml_{side}"], close_t)
        htf["HA"] = ml.astype(bool)
        htf["HB"] = htf["HA"] & map_state(dk, fd[f"rsi_{side}"], close_t).astype(bool)
        htf["HC"] = map_state(dk, fd[f"cnt_{side}"], close_t, 0) >= 2
        h4cnt = map_state(hk, fh[f"cnt_{side}"], close_t, 0)
        htf["HD"] = h4cnt >= 2
        htf["HE"] = htf["HA"] & (h4cnt >= 1)
        if side == "L":
            e1 = (lo <= a["bb_lower"].to_numpy()) & (c > a["bb_lower"].to_numpy())
            nwb = a["nw_lower"].to_numpy()
            e2 = (np.r_[False, c[:-1] < nwb[:-1]]) & (c >= nwb)
            e4 = a["rsi_cross_up"].fillna(False).to_numpy()
        else:
            e1 = (hi >= a["bb_upper"].to_numpy()) & (c < a["bb_upper"].to_numpy())
            nwb = a["nw_upper"].to_numpy()
            e2 = (np.r_[False, c[:-1] > nwb[:-1]]) & (c <= nwb)
            e4 = a["rsi_cross_dn"].fillna(False).to_numpy()
        for hn, en, xn in itertools.product(HTFS, ENTRIES, EXITS):
            act = htf[hn]
            if en == "E0":
                trig = act & ~np.r_[False, act[:-1]]
            else:
                trig = act & {"E1": e1, "E2": e2, "E3": e1 | e2, "E4": e4}[en]
            busy = -1
            for k in np.flatnonzero(trig):
                if k < start or k >= stop_at or k + 1 >= n or k <= busy:
                    continue
                i = k + 1
                e = o[i]
                if xn == "XC":
                    if np.isnan(d_atr[k]):
                        continue
                    stop = d_lo5[k] - 0.2 * d_atr[k] if sg == 1 else d_hi5[k] + 0.2 * d_atr[k]
                else:
                    if np.isnan(atr_l[k]):
                        continue
                    stop = lo5[k] - 0.3 * atr_l[k] if sg == 1 else hi5[k] + 0.3 * atr_l[k]
                risk = (e - stop) * sg
                if risk <= 0:
                    continue
                last = max(end_idx[i], i)
                seg_l, seg_h = lo[i:last + 1], hi[i:last + 1]
                hit_s = (seg_l <= stop) if sg == 1 else (seg_h >= stop)
                js = int(np.argmax(hit_s)) if hit_s.any() else None
                jt = None
                if xn == "XA":
                    tgt = e + sg * 3 * risk
                    hit_t = (seg_h >= tgt) if sg == 1 else (seg_l <= tgt)
                    jt = int(np.argmax(hit_t)) if hit_t.any() else None
                if js is not None and (jt is None or js <= jt):
                    ex, j = stop, i + js
                elif jt is not None:
                    ex, j = tgt, i + jt
                else:
                    ex, j = c[last], last
                busy = j
                out.append({"variante": f"{hn} {tf} {en} {xn}", "markt": name, "seite": side, "datum": x.index[i],
                            "r": ((ex - e) * sg - cost) / risk, "r_brutto": (ex - e) * sg / risk,
                            "kosten_r": cost / risk})
    return out


def teil2(lock: Lock) -> pd.DataFrame:
    rows = []
    for tf in LTFS:
        for name in MARKETS:
            rows += run_market(name, tf)
            print(f"  MTF {tf} {name}: fertig", flush=True)
    t = pd.DataFrame(rows)
    t["datum"] = pd.to_datetime(t["datum"], utc=True)
    t["periode"] = np.where(t["datum"] <= pd.Timestamp(IS_END, tz="UTC") + pd.Timedelta(hours=23), "IS", "OOS")
    res = []
    for v, g in t.groupby("variante"):
        row = {"variante": v}
        for per in ("IS", "OOS"):
            p = g[g["periode"] == per]
            st = stats(p["r"])
            row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan), f"{per}_t": st.get("t", np.nan),
                        f"{per}_brutto": p["r_brutto"].mean(), f"{per}_kosten": p["kosten_r"].median()})
        i = g.loc[g["periode"] == "IS", "r"]
        row["dsr"] = deflated_sharpe(i.mean() / i.std(ddof=1), len(i), lock.trials) if len(i) > 2 else np.nan
        isg = g[g["periode"] == "IS"]
        row["maerkte+_IS"] = f"{(isg.groupby('markt')['r'].mean() > 0).sum()}/{isg['markt'].nunique()}"
        res.append(row)
    res = pd.DataFrame(res).sort_values("IS_R", ascending=False)
    t.to_parquet("htf_daily_trade/indikator_mtf_trades.parquet")
    res.to_csv("htf_daily_trade/indikator_mtf_varianten.csv", index=False)
    return res


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    if lock.trials == 0:
        lock.log_trials(len(HTFS) * len(LTFS) * len(ENTRIES) * len(EXITS) + 1,
                        "MTF HA-HE x H1/M15 x E0-E4 x XA-XC + Skalierung S1 (26.11.)")
    if "--nur-2" not in sys.argv:
        print(teil1(lock).to_string(index=False))
    r = teil2(lock)
    print(r.head(25).to_string(index=False))
