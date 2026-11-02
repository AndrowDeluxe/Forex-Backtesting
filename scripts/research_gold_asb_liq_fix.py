"""Gold ASB: Liquiditaetsfilter ohne Vorgriff -- IS-Auswahl, dann OOS (2026-11-02, Nutzerauftrag).

Befund 2026-11-01 (scripts/research_gold_asb_stale_filter.py): corwin_schultz_spread datiert den
Wert auf t, nutzt aber Hoch/Tief von t und t+1. Der Filter liest den Wert vom Vortag und sieht damit
den ganzen Handelstag. Live ist um 01:00 NY nur der Tagesanfang bekannt.

Varianten (vor dem ersten IS-Blick festgelegt, Quantil 2/3 unveraendert):
  V0  Live-Stand: Friktion Vortag+Handelstag bis 01:00 NY, Schwelle aus der Backtest-Friktion
  V1  Kausal vollstaendig: letztes abgeschlossenes Fenster (Vorvortag+Vortag), Schwelle wie bisher
  V2  Live-Stand mit eigener Schwelle: Quantil ueber die Teil-Fenster-Friktion selbst
Auswahl: V1/V2 mit hoechstem IS-t (n >= 100); uebernommen nur, wenn ihr IS-t ueber V0 liegt,
sonst bleibt V0 eingefroren. Danach OOS genau einmal. Tresor bleibt zu.

Vorbehalt: Das OOS 2023-09/2025 ist durch gold_asb_is_reopt_20261015 schon geoeffnet, und die
Gesamtperioden von V0 wurden am 01.11. gesehen (Ausfall-Test). Kein jungfraeulicher Test.

  python scripts/research_gold_asb_liq_fix.py --stage is
  python scripts/research_gold_asb_liq_fix.py --stage oos
"""
import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from asian_range_breakout import pending as P  # noqa: E402
from asian_range_breakout.data import fetch_gold_m15  # noqa: E402
from asian_range_breakout.engine import simulate_asian_breakout  # noqa: E402
from asian_range_breakout.filters import (  # noqa: E402
    apply_adx_filter, apply_entry_delay_filter, apply_silver_alignment_filter, apply_trend_bias_filter,
    attach_series_level, rolling_liquidity_threshold,
)
from asian_range_breakout.sizing import simulate_equity  # noqa: E402
from bond_yield_indicator.friction import _K, fetch_fx_friction  # noqa: E402
from combined_strategy.data import fetch_timeframe  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "gold_asb_liq_fix_20261102"
END = "2026-11-01"
VARIANTS = ("V0", "V1", "V2")


def partial_friction(gold_m15: pd.DataFrame, d1: pd.DataFrame) -> pd.Series:
    """Corwin-Schultz fuer Tag t mit Tag t+1 nur bis 01:00 NY -- der Wissensstand bei Range-Ende."""
    m = gold_m15.tz_convert("UTC")
    hp, lp = [], []
    for bar in d1.index:
        bar = bar.tz_convert("UTC")
        re = (pd.Timestamp(bar.date()).tz_localize(P.NY) + pd.Timedelta(hours=1)).tz_convert("UTC")
        w = m[(m.index >= bar) & (m.index < re)]
        hp.append(w["high"].max() if len(w) else np.nan)
        lp.append(w["low"].min() if len(w) else np.nan)
    H, L = d1["High"], d1["Low"]
    h2n, l2n = pd.Series(hp, index=d1.index).shift(-1), pd.Series(lp, index=d1.index).shift(-1)
    h2 = pd.concat([H, h2n], axis=1).max(axis=1)
    l2 = pd.concat([L, l2n], axis=1).min(axis=1)
    gamma = np.log(h2 / l2) ** 2
    beta = (np.log(H / L) + np.log(h2n / l2n)) ** 2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / _K - np.sqrt(gamma / _K)
    s = (2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))).where(h2n.notna())
    s.index = s.index.tz_localize(None)
    return s


def build() -> dict:
    gold = fetch_gold_m15(P.HISTORY_START, END)
    silver = fetch_timeframe("SILVER", "M15", P.HISTORY_START, END)
    d1 = fetch_timeframe("GOLD", "D1", P.HISTORY_START, END)
    fr = fetch_fx_friction("GOLD", P.HISTORY_START, END)
    fl = partial_friction(gold, d1)
    dc = gold["close"].tz_localize(None).resample("D").last().dropna()
    ds = silver["Close"].tz_localize(None).resample("D").last().dropna()
    raw = simulate_asian_breakout(gold, range_start=P.RANGE_START, range_end=P.RANGE_END,
                                  exit_time=P.EXIT_TIME, stop_frac=P.STOP_FRAC)
    raw = apply_entry_delay_filter(apply_adx_filter(raw, adx_min=P.ADX_MIN), max_delay_bars=P.MAX_DELAY_BARS)
    raw = apply_trend_bias_filter(raw, dc, sma_window=P.TREND_SMA_WINDOW)
    raw = apply_silver_alignment_filter(raw, ds, window=P.SILVER_ALIGNMENT_WINDOW)
    q, mp = P.LIQUIDITY_QUANTILE, P.LIQUIDITY_MIN_PERIODS
    thr = rolling_liquidity_threshold(fr, quantile=q, min_periods=mp)
    spec = {"V0": (fl, thr), "V1": (fr.shift(1), thr),
            "V2": (fl, rolling_liquidity_threshold(fl, quantile=q, min_periods=mp))}
    out = {}
    for name, (f, t) in spec.items():
        x = attach_series_level(raw, f, "friction_prior")
        x = attach_series_level(x, t, "thr").dropna(subset=["friction_prior", "thr"])
        x = simulate_equity(x[x["friction_prior"] <= x["thr"]], starting_equity=100_000.0, risk_pct=0.005)
        x.index = pd.DatetimeIndex(x["entry_time"].dt.tz_localize(None))
        out[name] = x
    return out


def stats(x: pd.DataFrame) -> dict:
    r = x["r_multiple"]
    n = len(r)
    if n < 2:
        return {"n": n}
    g, l_ = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": n, "avg": r.mean(), "std": r.std(), "t": r.mean() / r.std() * n ** .5, "sum": r.sum(),
            "pf": g / l_ if l_ else np.inf, "skew": float(r.skew()), "kurt": float(r.kurt() + 3)}


def fmt(s: dict) -> str:
    if s["n"] < 2:
        return f"n={s['n']}"
    return f"n {s['n']:4d} | PF {s['pf']:.2f} | Oe R {s['avg']:+.3f} | t {s['t']:+.2f} | Summe R {s['sum']:+6.1f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["is", "oos"], required=True)
    stage = ap.parse_args().stage
    lk = Lock(STRATEGY)
    lk.register_split("2016-01-01", "2022-12-31", "2025-09-30", "2026-09-30")
    res = build()
    if stage == "is":
        if lk.trials == 0:
            lk.log_trials(len(VARIANTS), "V0 Live-Stand, V1 kausal vollstaendig, V2 Live-Stand eigene Schwelle")
        st = {k: stats(lk.is_only(v)) for k, v in res.items()}
        for k in VARIANTS:
            half = lk.is_only(res[k])
            h1, h2 = half[half.index < "2019-07-01"], half[half.index >= "2019-07-01"]
            print(f"IS {k}: {fmt(st[k])} | Haelften Oe R {h1['r_multiple'].mean():+.3f} / {h2['r_multiple'].mean():+.3f}")
        cands = [k for k in ("V1", "V2") if st[k]["n"] >= 100]
        best = max(cands, key=lambda k: st[k]["t"]) if cands else None
        win = best if best and st[best]["t"] > st["V0"]["t"] else "V0"
        srs = [st[k]["avg"] / st[k]["std"] for k in VARIANTS]
        w = st[win]
        dsr = deflated_sharpe(w["avg"] / w["std"], w["n"], len(VARIANTS), w["skew"], w["kurt"], float(np.var(srs)))
        h = lk.freeze({"liq_variant": win, "quantile": P.LIQUIDITY_QUANTILE})
        print(f"Gewinner {win} (bester Kandidat {best}), Deflated Sharpe {dsr:.2f}, eingefroren {h[:12]}")
    else:
        state = lk._load()
        win = state["frozen"]["config"]["liq_variant"]
        print("OOS geoeffnet:", lk.unseal("oos", state["frozen"]["hash"]))
        for k in VARIANTS:
            print(f"OOS {k}{' (eingefroren)' if k == win else ''}: {fmt(stats(lk.stage_slice(res[k], 'oos')))}")


if __name__ == "__main__":
    main()
