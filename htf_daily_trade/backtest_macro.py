"""Daily-Edge mit Makro-Filter (Typ R) und Typ C (Continuation) -- nur IS 2016-2021.

    python -m htf_daily_trade.backtest_macro

Typ R (Lock `htf_daily_trade_r`, +24 Versuche): E2 x S1/S2 x alle/gate x X1/X4 x Makro
(regime / g8 / beide). Referenz „ohne“ ist bereits gezaehlt (backtest_r).
Typ C (Lock `htf_daily_trade_c`, 24 Versuche): C1/C2 x S1/S2 x X1/X4 x Makro (ohne/regime/g8).
  C1: Manipulationskerze bricht ueber (unter) die Hochs (Tiefs) der 3 Vorkerzen, Docht >= 50 %
      der Spanne, im Trend MA12 < (>) MA20; Einstieg Eroeffnung des Folgetags; S1 = Kerzenextrem.
  C2: Schluss unter (ueber) den Dochten der 3 Vorkerzen, Manipulation in den 7 Tagen davor;
      Einstieg Eroeffnung des Folgetags; S1 = Extrem seit der Manipulation.
Kontrolle (nicht gezaehlt, keine Kandidaten): „gegen_regime“.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_r import MARKETS, features, load_market, signals, simulate, stats
from htf_daily_trade.macro import MacroGate
from research_lock import Lock, deflated_sharpe

R_VARIANTS = list(itertools.product(("S1", "S2"), ("alle", "gate"), ("X1", "X4"), ("regime", "g8", "beide")))
C_VARIANTS = list(itertools.product(("C1", "C2"), ("S1", "S2"), ("X1", "X4"), ("ohne", "regime", "g8")))


def c_signals(x: pd.DataFrame) -> list[dict]:
    h, l, o, c = (x[k].to_numpy() for k in ("High", "Low", "Open", "Close"))
    down = (x["ma_fast"] < x["ma_slow"]).to_numpy()
    atr = x["atr"].to_numpy()
    n = len(x)
    out = []
    for t in range(60, n - 1):
        p_hi, p_lo = h[t - 3:t].max(), l[t - 3:t].min()
        rng = h[t] - l[t]
        if rng > 0:
            if down[t] and h[t] > p_hi and (h[t] - max(o[t], c[t])) >= 0.5 * rng:
                out.append(dict(kind="C1", i=t, e=t + 1, etype="E2", side="short", entry=o[t + 1],
                                frac_lvl=h[t], atr=atr[t]))
            if (not down[t]) and l[t] < p_lo and (min(o[t], c[t]) - l[t]) >= 0.5 * rng:
                out.append(dict(kind="C1", i=t, e=t + 1, etype="E2", side="long", entry=o[t + 1],
                                frac_lvl=l[t], atr=atr[t]))
        for side in ("short", "long"):
            trend = down[t] if side == "short" else not down[t]
            trig = c[t] < p_lo if side == "short" else c[t] > p_hi
            if not (trend and trig):
                continue
            sweep = [s for s in range(max(3, t - 7), t + 1)
                     if (h[s] > h[s - 3:s].max() if side == "short" else l[s] < l[s - 3:s].min())]
            if not sweep:
                continue
            s0 = sweep[0]
            stop = h[s0:t + 1].max() if side == "short" else l[s0:t + 1].min()
            out.append(dict(kind="C2", i=t, e=t + 1, etype="E2", side=side, entry=o[t + 1],
                            frac_lvl=stop, atr=atr[t]))
    return out


def run(data, pick, stop_kind, exit_kind, macro, gate_obj, is_start, is_end):
    rows = []
    for name, (x, sigs, cost) in data.items():
        end_idx = int(np.searchsorted(x.index, is_end, side="right")) - 1
        busy = {"long": -1, "short": -1}
        for s in sorted(filter(pick, sigs), key=lambda s: s["e"]):
            t = x.index[s["e"]]
            if t < is_start or t > is_end or s["e"] > end_idx or s["e"] <= busy[s["side"]]:
                continue
            if not gate_obj.ok(macro, name, s["side"], t):
                continue
            res = simulate(x, s, stop_kind, exit_kind, cost, end_idx)
            if res is None:
                continue
            busy[s["side"]] = res["exit_k"]
            rows.append({"markt": name, "datum": t.date(), "seite": s["side"], "r": res["r"]})
    return pd.DataFrame(rows)


def report(title, rows, trades, lock):
    res = pd.DataFrame(rows).sort_values("t", ascending=False)
    pd.set_option("display.width", 180)
    print(f"\n===== {title} =====")
    print(res.round(3).to_string(index=False))
    best = res.iloc[0]
    tb = trades[best["variante"]]
    sr = tb["r"].mean() / tb["r"].std(ddof=1)
    print(f"Beste: {best['variante']} -- n {len(tb)}, Sharpe/Trade {sr:.3f}, "
          f"Deflated Sharpe ({lock.trials} Versuche) {deflated_sharpe(sr, len(tb), lock.trials):.3f}")
    print(tb.groupby("markt")["r"].agg(["size", "mean"]).round(2).T.to_string())
    print(tb.groupby(pd.to_datetime(tb["datum"]).dt.year)["r"].agg(["size", "mean"]).round(2).T.to_string())
    return res


def main() -> None:
    lr, lc = Lock("htf_daily_trade_r"), Lock("htf_daily_trade_c")
    lc.register_split("2016-01-01", "2021-12-31", "2024-12-31")
    lc.register_blind("2010-01-01", "2015-12-31")
    if lr.trials < 32 + len(R_VARIANTS):
        lr.log_trials(len(R_VARIANTS), "Typ R + Makro-Filter (Regime Angelo/Matrix, G8, beide) 02.11.")
    if lc.trials == 0:
        lc.log_trials(len(C_VARIANTS), "Typ C: C1/C2 x S1/S2 x X1/X4 x ohne/regime/g8 02.11.")
    is_start, is_end = pd.Timestamp("2016-01-01"), pd.Timestamp("2021-12-31")
    gate = MacroGate()
    data_r, data_c = {}, {}
    for name, (_, grid, cost) in MARKETS.items():
        df = load_market(name).loc[pd.Timestamp("2015-01-01"):is_end]
        x = features(df, grid)
        data_r[name] = (x, signals(x), cost)
        data_c[name] = (x, c_signals(x), cost)

    # --- Typ R mit Makro ---
    rows, trades = [], {}
    for stop, g, ex, mac in R_VARIANTS + [(s, g, e, m) for s in ("S1", "S2") for g in ("alle", "gate")
                                          for e in ("X1", "X4") for m in ("ohne", "gegen_regime")]:
        pick = (lambda s: s["etype"] == "E2") if g == "alle" else (lambda s: s["etype"] == "E2" and s["n_confis"] >= 3)
        t = run(data_r, pick, stop, ex, mac, gate, is_start, is_end)
        key = f"E2 {stop} {g} {ex} {mac}"
        trades[key] = t
        rows.append({"variante": key, **stats(t["r"])})
    report("Typ R mit Makro-Filter (ohne/gegen_regime = Referenz/Kontrolle)", rows, trades, lr)

    # --- Typ C ---
    rows, trades = [], {}
    for kind, stop, ex, mac in C_VARIANTS + [(k, s, e, "gegen_regime") for k in ("C1", "C2")
                                              for s in ("S1", "S2") for e in ("X1", "X4")]:
        t = run(data_c, lambda s, k=kind: s["kind"] == k, stop, ex, mac, gate, is_start, is_end)
        key = f"{kind} {stop} {ex} {mac}"
        trades[key] = t
        rows.append({"variante": key, **(stats(t["r"]) if len(t) > 1 else {"n": len(t)})})
    res_c = report("Typ C (gegen_regime = Kontrolle)", rows, trades, lc)
    res_c.to_csv("htf_daily_trade/backtest_c_is.csv", index=False)


if __name__ == "__main__":
    main()
