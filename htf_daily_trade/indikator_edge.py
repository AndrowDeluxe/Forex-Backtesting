"""Indikatoren 1-6 (Steckbriefe 26.11.) als eigener Edge und als Filter (Nutzerauftrag 26.11.2026).

    python -m htf_daily_trade.indikator_edge

Teil A  Kombi-Edge Daily, 9 Maerkte (Lock `indikator_kombi_daily`, IS 2016-21, OOS bis 25.05.2026, Tresor zu).
        Long-Idee (Short gespiegelt) nach Nutzer-Lesart "Multi-Length-Kaufzone + Cross":
          Zone   Z0 keine | Z1 OS-Flaeche > 0 in den letzten 3 Tagen | Z2 OS-Flaeche >= 50 %
          Trigger G1 RSI kreuzt seine MA | G2 Stoch-RSI K/D | G3 MACD 8/20/14 Linien
          Bestaet. C0 keine | C1 Tief beruehrt unteres BB(20,2) in 3 Tagen | C2 Schluss unter NW-Huelle in 3 Tagen
          Ausstieg X1 10 Handelstage | X2 Ziel 2 R, max. 10 Tage
        Einstieg Open Folgetag, Stop tiefstes Tief 5 Tage - 0,2 ATR, Kosten filter_matrix.MARKETS (ohne Swap).
        Stop vor Ziel bei gleicher Kerze. Je Markt und Seite nur ein offener Trade.
Teil B  Filter auf bestehende Trades (keine neue Optimierung der Basis):
          Daily  filter_matrix_trades.csv (Typ R, C2; IS 2016-21, OOS 2022-24), Stand Tagesschluss Signaltag
          H4     h4_ny15 Top-3-Varianten je Klasse (IS 2016-21, OOS bis 11.05.2026),
                 Stand letzte abgeschlossene H4-Kerze vor Einstieg + letzter abgeschlossener Tag
        Je Indikator Richtung +1/-1/0, "mit" = Richtung wie Trade, "gegen" = umgekehrt.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade import indikatoren as ind
from htf_daily_trade.backtest_r import stats
from htf_daily_trade.filter_matrix import MARKETS, load_market
from htf_daily_trade import h4_manip as hm
from htf_daily_trade.h4_ny15 import select
from research_lock import Lock, deflated_sharpe

LOCK = "indikator_kombi_daily"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2021-12-31", "2026-05-25", "2026-11-25"
LOOK = 3
H4_BASE = {"FX": ["N4 W70 EM S3 R2", "N4 W70 EM S3 R3", "N4 W70 LS S3 R3"],
           "Metalle": ["N4 W50 LS S3 R3", "N4 W60 LS S3 TB", "N4 W60 LS S3 R3"]}
IND = {"I1": "RSI ueber/unter MA", "I2": "RSI-MA-Cross (3 K.)", "I3": "ML-Flaeche > 0 (3 K.)",
       "I4": "ML-Flaeche >= 50 % (3 K.)", "I5": "Stoch K/D", "I6": "MACD 8/20/14 Linie/Signal",
       "I7": "BB-Band beruehrt (3 K.)", "I8": "Schluss ausserhalb BB", "I9": "Schluss ausserhalb NW (3 K.)"}


def frame(o, h, l, c) -> pd.DataFrame:
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c})


def states(df: pd.DataFrame) -> pd.DataFrame:
    """Richtung je Indikator (+1 long, -1 short, 0) zum Kerzenschluss; plus Rohsignale fuer Teil A."""
    c = df["close"]
    a = ind.alle(df)
    win = lambda b: b.astype(float).rolling(LOOK, min_periods=1).max().astype(bool)
    sg = lambda up, dn: up.astype(int) - dn.astype(int)
    s = pd.DataFrame(index=df.index)
    s["I1"] = np.sign(a["rsi"] - a["rsi_ma"]).fillna(0).astype(int)
    s["I2"] = sg(win(a["rsi_cross_up"]), win(a["rsi_cross_dn"]))
    s["I3"] = sg(win(a["rsi_ml_os_area"] > 0), win(a["rsi_ml_ob_area"] > 0))
    s["I4"] = sg(win(a["rsi_ml_os_area"] >= 50), win(a["rsi_ml_ob_area"] >= 50))
    s["I5"] = np.sign(a["stoch_k"] - a["stoch_d"]).fillna(0).astype(int)
    s["I6"] = np.sign(a["macd"] - a["macd_signal"]).fillna(0).astype(int)
    s["I7"] = sg(win(df["low"] <= a["bb_lower"]), win(df["high"] >= a["bb_upper"]))
    s["I8"] = sg(c < a["bb_lower"], c > a["bb_upper"])
    s["I9"] = sg(win(c < a["nw_lower"]), win(c > a["nw_upper"]))
    # Rohsignale Teil A (long/short getrennt)
    raw = {"G1": (a["rsi_cross_up"], a["rsi_cross_dn"]), "G2": (a["stoch_cross_up"], a["stoch_cross_dn"]),
           "G3": (a["macd_cross_up"], a["macd_cross_dn"])}
    for g, (u, d) in raw.items():
        s[f"{g}_L"], s[f"{g}_S"] = u.fillna(False), d.fillna(False)
    s["Z1_L"], s["Z1_S"] = win(a["rsi_ml_os_area"] > 0), win(a["rsi_ml_ob_area"] > 0)
    s["Z2_L"], s["Z2_S"] = win(a["rsi_ml_os_area"] >= 50), win(a["rsi_ml_ob_area"] >= 50)
    s["C1_L"], s["C1_S"] = win(df["low"] <= a["bb_lower"]), win(df["high"] >= a["bb_upper"])
    s["C2_L"], s["C2_S"] = win(c < a["nw_lower"]), win(c > a["nw_upper"])
    s["atr"] = a["atr"]
    return s


# --------------------------------------------------------------------------- Teil A
def sim_market(name: str, d: pd.DataFrame, s: pd.DataFrame, cost: float) -> list[dict]:
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    atr = s["atr"].to_numpy()
    idx = d.index
    start = idx.searchsorted(pd.Timestamp(IS_START))
    out = []
    for z, g, cf, x in itertools.product(("Z0", "Z1", "Z2"), ("G1", "G2", "G3"), ("C0", "C1", "C2"), ("X1", "X2")):
        var = f"{z} {g} {cf} {x}"
        for side, sign in (("L", 1), ("S", -1)):
            m = s[f"{g}_{side}"].to_numpy().copy()
            if z != "Z0":
                m &= s[f"{z}_{side}"].to_numpy()
            if cf != "C0":
                m &= s[f"{cf}_{side}"].to_numpy()
            busy = -1
            for t in np.flatnonzero(m):
                if t < max(start, 5) or t + 1 >= len(o) or t <= busy or np.isnan(atr[t]):
                    continue
                e = o[t + 1]
                stop = (l[t - 4:t + 1].min() - 0.2 * atr[t]) if sign == 1 else (h[t - 4:t + 1].max() + 0.2 * atr[t])
                risk = (e - stop) * sign
                if risk <= 0:
                    continue
                tgt = e + sign * 2 * risk
                ex, j = None, t + 1
                for j in range(t + 1, min(t + 11, len(o))):
                    if (l[j] <= stop) if sign == 1 else (h[j] >= stop):
                        ex = stop
                        break
                    if x == "X2" and ((h[j] >= tgt) if sign == 1 else (l[j] <= tgt)):
                        ex = tgt
                        break
                if ex is None:
                    ex = c[j]
                busy = j
                r = ((ex - e) * sign - cost) / risk
                out.append({"variante": var, "markt": name, "seite": "long" if sign == 1 else "short",
                            "datum": idx[t], "r": r, "r_brutto": (ex - e) * sign / risk})
    return out


def teil_a() -> pd.DataFrame:
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    n_var = 3 * 3 * 3 * 2
    if lock.trials == 0:
        lock.log_trials(n_var, "Kombi Z0-2 x G1-3 x C0-2 x X1-2 (26.11.)")
    rows = []
    for name, (_, _, cost) in MARKETS.items():
        d = load_market(name).rename(columns=str.lower).loc[:OOS_END]
        s = states(d)
        rows += sim_market(name, d, s, cost)
        print(f"  A {name}: fertig", flush=True)
    t = pd.DataFrame(rows)
    t["periode"] = np.where(t["datum"] <= pd.Timestamp(IS_END), "IS", "OOS")
    res = []
    for var, g in t.groupby("variante"):
        row = {"variante": var}
        for per in ("IS", "OOS"):
            st = stats(g.loc[g["periode"] == per, "r"])
            row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan), f"{per}_t": st.get("t", np.nan),
                        f"{per}_brutto": g.loc[g["periode"] == per, "r_brutto"].mean()})
        i = g.loc[g["periode"] == "IS", "r"]
        row["dsr"] = deflated_sharpe(i.mean() / i.std(ddof=1), len(i), lock.trials) if len(i) > 2 else np.nan
        isg = g[g["periode"] == "IS"]
        row["maerkte+_IS"] = f"{(isg.groupby('markt')['r'].mean() > 0).sum()}/{isg['markt'].nunique()}"
        res.append(row)
    res = pd.DataFrame(res).sort_values("IS_R", ascending=False)
    t.to_csv("htf_daily_trade/indikator_kombi_trades.csv", index=False)
    res.to_csv("htf_daily_trade/indikator_kombi_varianten.csv", index=False)
    return res


# --------------------------------------------------------------------------- Teil B
def lookup(st: pd.DataFrame, known_at: pd.DatetimeIndex, cols) -> pd.DataFrame:
    """Letzte Zeile mit Index <= known_at (Index = Zeitpunkt, ab dem der Stand bekannt ist)."""
    pos = st.index.searchsorted(known_at, side="right") - 1
    v = st[list(cols)].to_numpy()[np.clip(pos, 0, None)]
    v[pos < 0] = 0
    return pd.DataFrame(v, columns=list(cols))


def filter_table(base: pd.DataFrame, label: str, prefix: str) -> list[dict]:
    out = []
    sign = np.where(base["seite"] == "long", 1, -1)
    for f in IND:
        col = f"{prefix}{f}"
        for mode in ("mit", "gegen"):
            m = base[col].to_numpy() == (sign if mode == "mit" else -sign)
            row = {"basis": label, "filter": f"{prefix}{f} {IND[f]}", "modus": mode}
            for per in ("IS", "OOS"):
                p = base["periode"] == per
                st, b0 = stats(base.loc[p & m, "r"]), base.loc[p, "r"].mean()
                row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan),
                            f"{per}_t": st.get("t", np.nan), f"{per}_delta": st.get("mean_r", np.nan) - b0})
            out.append(row)
    return out


def teil_b() -> pd.DataFrame:
    rows = []
    # Daily-Basis
    dt = pd.read_csv("htf_daily_trade/filter_matrix_trades.csv", parse_dates=["datum"])
    parts = []
    for name in dt["markt"].unique():
        d = load_market(name).rename(columns=str.lower)
        st = states(d)
        st.index = st.index + pd.Timedelta(hours=23)                  # bekannt zum Tagesschluss
        g = dt[dt["markt"] == name].copy()
        # datum = Fuelltag -> nur Stand bis Schluss des Vortags (wie filter_matrix: known = fill - 1)
        g[[f"D{f}" for f in IND]] = lookup(st, pd.DatetimeIndex(g["datum"]), IND).to_numpy()
        parts.append(g)
    dt = pd.concat(parts)
    for setup, g in dt.groupby("setup"):
        rows += filter_table(g, f"Daily {setup}", "D")
    # H4-Basis
    ht = pd.read_parquet("htf_daily_trade/h4_ny15_trades.parquet")
    sel = []
    for kl, vs in H4_BASE.items():
        for v in vs:
            n, w, e, s_, tk = v.split()
            g = select(ht[ht["klasse"] == kl], int(n[1:]), int(w[1:]) / 100, e, s_, tk).copy()
            g["basis"] = f"H4 {kl} {v}"
            sel.append(g)
    ht = pd.concat(sel)
    parts = []
    for name in ht["markt"].unique():
        x = hm.h4(name)
        st4 = states(frame(x["Open"].values, x["High"].values, x["Low"].values, x["Close"].values).set_index(x.index))
        st4.index = (x.index + pd.Timedelta(hours=4)).tz_localize(None)    # bekannt bei Kerzenschluss (UTC)
        dd = hm.daily(name)                                               # Server-Tage
        std = states(dd.rename(columns=str.lower))
        g = ht[ht["markt"] == name].copy()
        ein = pd.DatetimeIndex(g["einstieg"])
        g[[f"H{f}" for f in IND]] = lookup(st4, ein, IND).to_numpy()
        srv_day = hm.server_time(ein.tz_localize("UTC")).normalize()
        std.index = std.index + pd.Timedelta(days=1)                      # Tag t bekannt ab Tag t+1 (Server)
        g[[f"D{f}" for f in IND]] = lookup(std, srv_day, IND).to_numpy()
        parts.append(g)
        print(f"  B {name}: fertig", flush=True)
    ht = pd.concat(parts)
    for b, g in ht.groupby("basis"):
        rows += filter_table(g, b, "H") + filter_table(g, b, "D")
    res = pd.DataFrame(rows)
    res.to_csv("htf_daily_trade/indikator_filter.csv", index=False)
    base_rows = []
    for b, g in list(dt.groupby("setup")) + list(ht.groupby("basis")):
        base_rows.append({"basis": b if str(b).startswith("H4") else f"Daily {b}",
                          **{f"{p}_n": (g["periode"] == p).sum() for p in ("IS", "OOS")},
                          **{f"{p}_R": g.loc[g["periode"] == p, "r"].mean() for p in ("IS", "OOS")}})
    pd.DataFrame(base_rows).to_csv("htf_daily_trade/indikator_filter_basis.csv", index=False)
    return res


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    import sys
    if "--nur-b" not in sys.argv:
        a = teil_a()
        print(a.head(15).to_string(index=False))
    b = teil_b()
    good = b[(b["IS_delta"] > 0.05) & (b["IS_n"] >= 30)].sort_values("IS_delta", ascending=False)
    print(good.head(40).to_string(index=False))
