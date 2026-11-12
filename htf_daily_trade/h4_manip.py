"""Backtest „Final H4 HTF Entry Model“ (A6, Nutzer + Jakob, Edge Card knowledge/projects/h4-htf-entry-edge-card.md).

    python -m htf_daily_trade.h4_manip            # IS 2016-2021 + OOS bis 2026-05-11 (Tresor + Blind zu)
    python -m htf_daily_trade.h4_manip --probe    # EURUSD 2023: Signale zum Abgleich mit den 30 Beispielen

Plan freigegeben 12.11.2026. H4 zur Broker-Serverzeit (NY+7), 9 Maerkte.
Manipulation an Kerze k: Docht ueber/unter Hoch/Tief der 2 Vorkerzen, Schluss zurueck.
  W0 ohne Zusatz | W1 Docht in Sweep-Richtung >= 50 % der Kerzenspanne
Einstieg E1 Market zur Eroeffnung k+1 | E2 Schluss k+1, wenn k+1 das Manipulations-Extrem nicht bricht.
Stop Docht-Extrem von k. Ziel TA 3 R | TB naechstes unberuehrtes H4-Fractal >= 1 R | TC Vortag/Vorwoche >= 1 R
(sonst 3 R). BE B0 ohne | B1 Stop auf Einstieg nach H4-BOS in Trade-Richtung (Schluss ueber ERL). Zeitausstieg 60 H4.
Kosten Round-Trip je Markt + TTP-Swap. BIAS (mit/gegen/neutral, ohne Vorgriff): D-Struktur, H4-Struktur, T1-T7.
Sperre `h4_manip`: 24 Grundvarianten x (ohne + 9 Filter x mit/gegen) = 456 Versuche.
"""

from __future__ import annotations

import functools
import itertools
import sys

import numpy as np
import pandas as pd

from fusion_lab.patterns.crt import resample_server
from gold_smc_htf_ltf.structure import compute_market_structure
from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.c2_exit_varianten import konto
from htf_daily_trade.filter_matrix import MARKETS, trend_dirs
from htf_daily_trade.twin_trade import swap_r
from research_lock import Lock, deflated_sharpe

LOCK = "h4_manip"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2021-12-31", "2026-05-11", "2026-11-11"
WARMUP = "2014-06-01"
MAX_HOLD = 60
SWING_LOOKBACK = 120
WICKS, ENTRIES, TARGETS, BES = ("W0", "W1"), ("E1", "E2"), ("TA", "TB", "TC"), ("B0", "B1")
BASE = [" ".join(v) for v in itertools.product(WICKS, ENTRIES, TARGETS, BES)]
FILTERS = ["D", "H4", "T1", "T2", "T3", "T4", "T5", "T6", "T7"]
FILTER_NAMES = {"D": "Daily-Struktur", "H4": "H4-Struktur", "T1": "MA 12/20", "T2": "Weekly SMA 20/50",
                "T3": "SMA 200", "T4": "ADX>=20 DI", "T5": "Ribbon", "T6": "Faber 10M", "T7": "Weekly EMA 9/21"}
SRC = {"XAUUSD": ["GOLD_M15_2009-01-01_2016-01-01.parquet", "GOLD_H1_2016-01-01_2026-10-29.parquet",
                  "GOLD_H1_2018-01-01_2026-11-10.parquet"],
       "XAGUSD": ["SILVER_M15_2009-01-01_2016-01-01.parquet", "SILVER_H1_2016-01-01_2026-08-01.parquet"]}
LAKE = {"XAUUSD": ("GOLD", "H1"), "XAGUSD": ("SILVER", "H1")}


# --------------------------------------------------------------------------- Daten
@functools.lru_cache(maxsize=None)
def intraday(name: str) -> pd.DataFrame:
    files = SRC.get(name, [f"{name}_H1_2007-01-01_2026-11-10.parquet"])
    parts = [pd.read_parquet(f"data_cache/combined/{f}")[["Open", "High", "Low", "Close"]] for f in files]
    if name in LAKE:
        from data_lake.storage import read_bars
        lk = read_bars("dukascopy", *LAKE[name])
        if lk is not None and len(lk):
            parts.append(lk[["Open", "High", "Low", "Close"]])
    b = pd.concat(parts)
    b.index = b.index.tz_localize("UTC") if b.index.tz is None else b.index.tz_convert("UTC")
    return b[~b.index.duplicated(keep="first")].sort_index()


def server_time(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=7)


@functools.lru_cache(maxsize=None)
def h4(name: str) -> pd.DataFrame:
    d = resample_server(intraday(name), "H4")
    srv = server_time(d.index)
    return d[srv.dayofweek < 5]


@functools.lru_cache(maxsize=None)
def daily(name: str) -> pd.DataFrame:
    b = intraday(name)
    srv = server_time(b.index)
    key = srv.normalize()
    key = key.where(key.dayofweek != 6, key + pd.Timedelta(days=1)).where(key.dayofweek != 5, key - pd.Timedelta(days=1))
    g = b.set_axis(srv).groupby(key)
    d = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(), "Low": g["Low"].min(), "Close": g["Close"].last()})
    return d[d.index.dayofweek < 5]


# --------------------------------------------------------------------------- Signale
def manipulations(x: pd.DataFrame) -> list[dict]:
    """Kerze k sweept Hoch/Tief der 2 Vorkerzen und schliesst zurueck."""
    o, h, l, c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    out = []
    for k in range(2, len(x) - 1):
        lo2, hi2 = min(l[k - 1], l[k - 2]), max(h[k - 1], h[k - 2])
        rng = h[k] - l[k]
        if rng <= 0:
            continue
        if l[k] < lo2 and c[k] > lo2:
            out.append({"k": k, "side": "long", "stop": l[k], "wick": (min(o[k], c[k]) - l[k]) / rng})
        if h[k] > hi2 and c[k] < hi2:
            out.append({"k": k, "side": "short", "stop": h[k], "wick": (h[k] - max(o[k], c[k])) / rng})
    return out


class Market:
    """Alle Arrays eines Marktes fuer Simulation, Ziele und BIAS."""

    def __init__(self, name: str, end: str = OOS_END):
        self.name = name
        _, grid, self.cost = MARKETS[name]
        x = h4(name)
        x = x[(x.index >= pd.Timestamp(WARMUP, tz="UTC")) & (x.index <= pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23))]
        self.x = x
        self.o, self.h, self.l, self.c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        self.srv = server_time(x.index)
        self.day = self.srv.normalize()
        s = compute_market_structure(x.rename(columns=str.lower), k=2)
        self.bias_h4 = s["bias"].to_numpy()
        self.up_break = s["erl_high_broken"].to_numpy()
        self.dn_break = s["erl_low_broken"].to_numpy()
        conf_h, conf_l = s["swing_high_confirmed"].to_numpy(), s["swing_low_confirmed"].to_numpy()
        ph, pl = s["swing_high_price"].to_numpy(), s["swing_low_price"].to_numpy()
        self.sw_hi = [(i, i - 2, ph[i]) for i in np.flatnonzero(conf_h)]   # (bestaetigt, Kerze, Preis)
        self.sw_lo = [(i, i - 2, pl[i]) for i in np.flatnonzero(conf_l)]
        d = daily(name).loc[:pd.Timestamp(end)]
        fx = features(d, grid)
        td = trend_dirs(fx)
        td["D"] = compute_market_structure(d.rename(columns=str.lower), k=2)["bias"].to_numpy()
        pos = d.index.searchsorted(self.day) - 1          # letzter abgeschlossener Tag vor dem Kerzentag
        self.dirs = {f: np.where(pos >= 0, td[f].to_numpy()[np.clip(pos, 0, None)], 0) for f in FILTERS if f != "H4"}
        self.prev_day = np.where(pos >= 0, pos, -1)
        self.d_hi, self.d_lo = d["High"].to_numpy(), d["Low"].to_numpy()
        wk = d.resample("W-FRI").agg({"High": "max", "Low": "min"})
        wpos = wk.index.searchsorted(self.day - pd.to_timedelta(self.day.dayofweek, unit="D")) - 1
        self.w_hi = np.where(wpos >= 0, wk["High"].to_numpy()[np.clip(wpos, 0, None)], np.nan)
        self.w_lo = np.where(wpos >= 0, wk["Low"].to_numpy()[np.clip(wpos, 0, None)], np.nan)
        self.sigs = manipulations(x)

    def target(self, kind: str, sign: int, entry: float, risk: float, known: int, live: int) -> float:
        three = entry + sign * 3 * risk
        if kind == "TA":
            return three
        if kind == "TB":
            sw = self.sw_hi if sign == 1 else self.sw_lo
            best = None
            for ci, bi, p in reversed(sw):
                if ci > known:
                    continue
                if bi < known - SWING_LOOKBACK:
                    break
                if sign * (p - entry) < risk:
                    continue
                seg = self.h[bi + 1:known + 1] if sign == 1 else self.l[bi + 1:known + 1]
                if len(seg) and (seg.max() >= p if sign == 1 else seg.min() <= p):
                    continue                              # schon abgeholt
                if best is None or sign * (p - best) < 0:
                    best = p
            return best if best is not None else three
        pd_i = self.prev_day[live]
        cands = []
        if pd_i >= 0:
            cands.append(self.d_hi[pd_i] if sign == 1 else self.d_lo[pd_i])
        wv = self.w_hi[live] if sign == 1 else self.w_lo[live]
        if np.isfinite(wv):
            cands.append(wv)
        cands = [p for p in cands if sign * (p - entry) >= risk]
        return min(cands, key=lambda p: sign * (p - entry)) if cands else three

    def trade(self, s: dict, e: str, t: str, b: str, end_idx: int):
        k, sign = s["k"], 1 if s["side"] == "long" else -1
        stop = s["stop"]
        if e == "E1":
            live, entry, known = k + 1, self.o[k + 1], k
        else:
            if k + 2 > end_idx:
                return None
            broke = self.l[k + 1] <= stop if sign == 1 else self.h[k + 1] >= stop
            if broke:
                return None
            live, entry, known = k + 2, self.c[k + 1], k + 1
        risk = sign * (entry - stop)
        if not (risk > 0) or live > end_idx:
            return None
        tgt = self.target(t, sign, entry, risk, known, live)
        brk = self.up_break if sign == 1 else self.dn_break
        cur, last = stop, min(end_idx, live + MAX_HOLD - 1)
        exit_px, j = None, live
        for j in range(live, last + 1):
            if (sign == 1 and self.l[j] <= cur) or (sign == -1 and self.h[j] >= cur):
                exit_px = cur
                break
            if (sign == 1 and self.h[j] >= tgt) or (sign == -1 and self.l[j] <= tgt):
                exit_px = tgt
                break
            if b == "B1" and brk[j] and sign * (self.c[j] - entry) > 0:
                cur = entry if sign * (entry - cur) > 0 else cur
        if exit_px is None:
            j, exit_px = last, self.c[last]
        gross = sign * (exit_px - entry) / risk
        sw = swap_r(self.name, s["side"], entry, risk, self.x.index[live].tz_localize(None), self.x.index[j].tz_localize(None))
        return {"exit_k": j, "entry": entry, "risk": risk, "ziel": tgt, "r_brutto": gross,
                "r": gross - self.cost / risk - sw, "live": live}

    def state(self, f: str, k: int, sign: int) -> str:
        v = self.bias_h4[k - 1] if f == "H4" else self.dirs[f][k]
        v = int(np.sign(v)) * sign
        return "mit" if v > 0 else "gegen" if v < 0 else "neutral"


def run_market(name: str, end: str = OOS_END) -> pd.DataFrame:
    m = Market(name, end)
    end_idx = len(m.x) - 1
    start_idx = int(m.x.index.searchsorted(pd.Timestamp(IS_START, tz="UTC")))
    rows = []
    for w, e, t, b in itertools.product(WICKS, ENTRIES, TARGETS, BES):
        busy = {"long": -1, "short": -1}
        for s in m.sigs:
            if s["k"] < start_idx or s["k"] + 1 > end_idx or (w == "W1" and s["wick"] < 0.5):
                continue
            if s["k"] + 1 <= busy[s["side"]]:
                continue
            res = m.trade(s, e, t, b, end_idx)
            if res is None:
                continue
            busy[s["side"]] = res["exit_k"]
            sign = 1 if s["side"] == "long" else -1
            ts = m.x.index[res["live"]].tz_localize(None)
            rows.append({"variante": f"{w} {e} {t} {b}", "markt": name, "seite": s["side"],
                         "einstieg": ts, "ausstieg": m.x.index[res["exit_k"]].tz_localize(None),
                         "slot": m.srv[s["k"]].hour, "r": res["r"], "r_brutto": res["r_brutto"],
                         "risiko_atr": res["risk"], "kurs": res["entry"], "stop": s["stop"], "ziel": res["ziel"],
                         **{f: m.state(f, s["k"], sign) for f in FILTERS}})
    return pd.DataFrame(rows)


def random_baseline(trades: pd.DataFrame, seed: int = 7, draws: int = 5) -> pd.DataFrame:
    """Gegenprobe: gleiche Seite, gleiche Stopweite, Ziel 3 R, Einstieg zur Eroeffnung einer zufaelligen H4-Kerze."""
    rng = np.random.default_rng(seed)
    out = []
    for name, g in trades.groupby("markt"):
        x = h4(name)
        x = x[(x.index >= pd.Timestamp(IS_START, tz="UTC")) & (x.index <= pd.Timestamp(OOS_END, tz="UTC"))]
        o, h, l, c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        cost = MARKETS[name][2]
        for _ in range(draws):
            for r in g.itertuples():
                i = int(rng.integers(1, len(x) - MAX_HOLD - 1))
                sign = 1 if r.seite == "long" else -1
                entry, risk = o[i], r.risiko_atr
                stop, tgt = entry - sign * risk, entry + sign * 3 * risk
                px = c[i + MAX_HOLD - 1]
                for j in range(i, i + MAX_HOLD):
                    if (sign == 1 and l[j] <= stop) or (sign == -1 and h[j] >= stop):
                        px = stop
                        break
                    if (sign == 1 and h[j] >= tgt) or (sign == -1 and l[j] <= tgt):
                        px = tgt
                        break
                out.append({"markt": name, "periode": "IS" if x.index[i] <= pd.Timestamp(IS_END, tz="UTC") else "OOS",
                            "r_brutto": sign * (px - entry) / risk, "r": sign * (px - entry) / risk - cost / risk})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- Auswertung
def summarize(g: pd.DataFrame, n_trials: int) -> dict:
    row = {}
    for per in ("IS", "OOS"):
        p = g[g["periode"] == per]
        st = stats(p["r"])
        row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan), f"{per}_t": st.get("t", np.nan),
                    f"{per}_brutto": p["r_brutto"].mean(), f"{per}_treffer": (p["r"] > 0).mean()})
    i = g[g["periode"] == "IS"]["r"]
    row["dsr"] = deflated_sharpe(i.mean() / i.std(ddof=1), len(i), n_trials) if len(i) > 2 else np.nan
    row["jahre+"] = f"{(g.groupby(g['einstieg'].dt.year)['r'].mean() > 0).sum()}/{g['einstieg'].dt.year.nunique()}"
    row["maerkte+"] = f"{(g.groupby('markt')['r'].mean() > 0).sum()}/{g['markt'].nunique()}"
    k = konto(g.rename(columns={"einstieg": "datum", "ausstieg": "exit_datum"})[["datum", "exit_datum", "r"]], lambda x: 0.01)
    row.update({"cagr": k["cagr"], "dd": k["max_dd"]})
    return row


def main() -> None:
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    if lock._load().get("blind") is None:
        lock.register_blind("2010-01-01", "2015-12-31")
    n_var = len(BASE) * (1 + 2 * len(FILTERS))
    if lock.trials == 0:
        lock.log_trials(n_var, "H4-Manipulation: 2 Docht x 2 Einstieg x 3 Ziele x 2 BE x (ohne + 9 Filter mit/gegen) (12.11.)")
    parts = []
    for name in MARKETS:
        parts.append(run_market(name))
        print(f"  {name}: {len(parts[-1])} Trades (alle Varianten)", flush=True)
    t = pd.concat(parts, ignore_index=True)
    t["periode"] = np.where(t["einstieg"] <= pd.Timestamp(IS_END) + pd.Timedelta(hours=23, minutes=59), "IS", "OOS")
    t.to_csv("htf_daily_trade/h4_manip_trades.csv", index=False)
    rows = []
    for v, g in t.groupby("variante"):
        rows.append({"variante": v, "filter": "ohne", **summarize(g, lock.trials)})
        for f in FILTERS:
            for z in ("mit", "gegen"):
                sel = g[g[f] == z]
                if (sel["periode"] == "IS").sum() >= 30:
                    rows.append({"variante": v, "filter": f"{f} {z}", **summarize(sel, lock.trials)})
    res = pd.DataFrame(rows).sort_values("IS_t", ascending=False)
    res.to_csv("htf_daily_trade/h4_manip_varianten.csv", index=False)
    pd.set_option("display.width", 260)
    print(f"\nLock {LOCK}: {lock.trials} Versuche. Trades IS+OOS je Grundvariante ~{len(t) // len(BASE)}")
    base = res[res["filter"] == "ohne"].sort_values("IS_t", ascending=False)
    print("\n== Grundvarianten (ohne Filter) ==\n" + base.round(3).to_string(index=False))
    print("\n== Top 25 mit Filter nach IS-t ==\n" + res[res["filter"] != "ohne"].head(25).round(3).to_string(index=False))
    fs = res[res["filter"] != "ohne"].assign(f=lambda d: d["filter"]).groupby("f")[["IS_R", "OOS_R", "IS_n", "OOS_n"]].mean()
    print("\n== Ø je Filter-Zustand (über alle Grundvarianten) ==\n" + fs.sort_values("IS_R", ascending=False).round(3).to_string())
    best = base.iloc[0]["variante"]
    g = t[t["variante"] == best]
    print(f"\n== Beste Grundvariante {best}: je Markt / je Slot (Serverzeit) / je Jahr ==")
    for key in ("markt", "slot"):
        print(g.groupby([key, "periode"])["r"].agg(["size", "mean"]).unstack().round(3).to_string())
    print(g.groupby(g["einstieg"].dt.year)["r"].agg(["size", "mean", "sum"]).round(3).to_string())
    rb = random_baseline(t[(t["variante"] == "W0 E1 TA B0")])
    sig = t[t["variante"] == "W0 E1 TA B0"]
    print("\n== Gegenprobe Zufallseinstieg (gleiche Seite/Stopweite, 3 R) vs. W0 E1 TA B0 ==")
    for per in ("IS", "OOS"):
        print(f"{per}: Signal {sig.loc[sig.periode == per, 'r_brutto'].mean():+.3f} R brutto / "
              f"{sig.loc[sig.periode == per, 'r'].mean():+.3f} netto | Zufall {rb.loc[rb.periode == per, 'r_brutto'].mean():+.3f} brutto / "
              f"{rb.loc[rb.periode == per, 'r'].mean():+.3f} netto")
    probe(t)


def probe(t: pd.DataFrame | None = None) -> None:
    if t is None:
        t = run_market("EURUSD", "2023-12-31")
        t["periode"] = "IS"
    e = t[(t["markt"] == "EURUSD") & (t["einstieg"].dt.year == 2023) & (t["variante"] == "W1 E1 TA B1")]
    print(f"\n== EURUSD 2023, W1 E1 TA B1: {len(e)} Trades (Original: 30 Beispiele, 26 TP / 4 BE / 0 SL) ==")
    print(f"Ø R {e['r'].mean():+.3f}, Ziel erreicht {(e['r'] > 2).mean():.0%}, BE/klein {((e['r'] > -0.5) & (e['r'] <= 2)).mean():.0%}, "
          f"Stop {(e['r'] <= -0.5).mean():.0%}")
    print(e[["seite", "einstieg", "kurs", "stop", "ziel", "r", "D", "T1"]].head(12).round(5).to_string(index=False))


if __name__ == "__main__":
    probe() if "--probe" in sys.argv else main()
