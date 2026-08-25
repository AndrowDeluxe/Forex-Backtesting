"""Optimization pass for the Gold/Silber-Divergenz bot
(mt5_gold_silver_divergenz/pipeline.py), following the standard repo
discipline used throughout mt5_trend_pullback's own scripts: sweep a
parameter ONLY on In-Sample (2016-2022), pick the best by IS Sharpe (with a
minimum-trade-count floor to avoid picking noise), then validate that choice
UNCHANGED on Out-of-Sample (2023-2026). Passes are chained sequentially --
each pass locks in the prior pass's choice before sweeping the next
dimension, same pattern as scripts/research_mt5_trend_pullback_adx_filter.py
-> ..._tp_sl_be_sweep.py.

Chat context (2026-08-25): walk-forward across 3 rolling sub-periods showed
2016-2019 is the weak link (WR 34.5%, PF 0.71) vs. 2019-2022/2022-2026 (WR
50-59%, PF 1.7-2.4). Root-caused to the Gold/Silver RATIO itself being in a
smooth structural uptrend in 2016-2019 (76.6->83.0, std=5.0, the lowest of
any period) vs. choppier/mean-reverting in the other two periods (std=11.4,
9.8) -- catch-up crossings during a persistent structural drift are mostly
false starts, not real reversion. A raw-ATR "volatility filter" was tested
first and REJECTED: it only looked good because raw ATR-in-dollars tracks
gold's own secular price rise (1200->3000+), not real volatility -- the
effect vanishes once ATR is normalized by price (see chat, not re-derived
here). A genuine ratio-trendiness filter is NOT tested with real IS/OOS
rigor in this script: Silver data via combined_strategy.data only goes back
to 2014-07-25, giving no additional independent regime instance beyond the
existing 3 periods -- flagged, not attempted.

Passes:
  1. Band parameters (ret_len x band_lookback x band_mult) -- the strategy's
     own untouched parameters, never swept before (bot's config.py values
     are the SSRN/community defaults, not repo-validated).
  2. Stop/RR (atr_stop_mult x rr_ratio) -- on top of pass 1's choice.
  3. Silver-confirms-Gold alignment filter -- require Silver's own N-bar
     momentum to also be positive at entry (plausibility check that the
     catch-up is real, not noise) -- same idea as
     mt5_trend_pullback/filters.py's alignment_filter, adapted for this
     strategy's single-signal (no separate confirming asset available here,
     so this uses Silver's own recent trend instead).
  4. Diagnostic-only: Gold/Silver ratio ADX as a would-be regime filter --
     explicitly labelled as NOT IS/OOS-validated (insufficient independent
     regime samples), shown for completeness only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_gold_silver_divergenz.pipeline import (
    ATR_LEN, ATR_STOP_MULT, BAND_LOOKBACK, BAND_MULT, RET_LEN, RR_RATIO, TREND_LEN, run_pipeline,
)
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.indicators import compute_adx
from strategy.metrics import summarize

pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
SPREAD_BPS = 10.0
MIN_IS_TRADES = 25  # floor to avoid picking a config on a noisy handful of IS trades

RET_LEN_CANDIDATES = [10, 15, 20, 25, 30]
BAND_LOOKBACK_CANDIDATES = [50, 75, 100, 150, 200]
BAND_MULT_CANDIDATES = [1.0, 1.25, 1.5, 1.75, 2.0]
STOP_ATR_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0]
RR_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
CONFIRM_LEN_CANDIDATES = [3, 5, 10, 20]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def is_oos(signaled: pd.DataFrame, cfg: BacktestConfig) -> tuple[dict, dict]:
    trades = simulate_trades(signaled, cfg)
    is_t = trades[trades["entry_time"] < SPLIT]
    is_idx = signaled[signaled.index < SPLIT].index
    oos_t = trades[trades["entry_time"] >= SPLIT]
    oos_idx = signaled[signaled.index >= SPLIT].index
    return summarize(is_t, is_idx), summarize(oos_t, oos_idx)


def main():
    print(f"Fetching XAUUSD/XAGUSD H4 {DATA_START} -> {DATA_END} ...")
    xau = fetch_timeframe("GOLD", "H4", DATA_START, DATA_END).rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    xag = fetch_timeframe("SILVER", "H4", DATA_START, DATA_END).rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})

    base_cfg_kwargs = dict(stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)

    # baseline (bot default) for reference throughout
    sig_default = run_pipeline(xau, xag)
    is_default, oos_default = is_oos(sig_default, BacktestConfig(spread_bps=SPREAD_BPS, **base_cfg_kwargs))
    print("\n" + "=" * 100)
    print("BASELINE (Bot-Default: ret_len=20, band_lookback=100, band_mult=1.5, stop=2.0, rr=2.0)")
    print("=" * 100)
    print(f"  IS   {fmt(is_default)}")
    print(f"  OOS  {fmt(oos_default)}")

    # ================================================================ Pass 1: band parameters
    print("\n" + "=" * 100)
    print("PASS 1 - BAND-PARAMETER-SWEEP (ret_len x band_lookback x band_mult), NUR IN-SAMPLE (2016-2022)")
    print("=" * 100)
    rows = []
    for ret_len in RET_LEN_CANDIDATES:
        for band_lookback in BAND_LOOKBACK_CANDIDATES:
            for band_mult in BAND_MULT_CANDIDATES:
                sig = run_pipeline(xau, xag, ret_len=ret_len, band_lookback=band_lookback, band_mult=band_mult)
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, **base_cfg_kwargs)
                is_s, _ = is_oos(sig, cfg)
                rows.append({"ret_len": ret_len, "band_lookback": band_lookback, "band_mult": band_mult, **is_s})
    sweep1 = pd.DataFrame(rows)
    eligible1 = sweep1[sweep1["n_trades"] >= MIN_IS_TRADES]
    print(f"  {len(sweep1)} Kombinationen getestet, {len(eligible1)} mit n_IS>={MIN_IS_TRADES}")
    print("\n  Top 10 nach IS-Sharpe (n_IS>={}):".format(MIN_IS_TRADES))
    print(eligible1.sort_values("sharpe", ascending=False).head(10)[["ret_len", "band_lookback", "band_mult", "n_trades", "win_rate", "profit_factor", "sharpe"]].to_string(index=False))

    if eligible1.empty:
        print("  Kein Kandidat erfuellt die Mindest-Trade-Schwelle -- Bot-Default wird beibehalten.")
        chosen_ret_len, chosen_band_lookback, chosen_band_mult = RET_LEN, BAND_LOOKBACK, BAND_MULT
    else:
        best1 = eligible1.loc[eligible1["sharpe"].idxmax()]
        chosen_ret_len, chosen_band_lookback, chosen_band_mult = int(best1["ret_len"]), int(best1["band_lookback"]), float(best1["band_mult"])
        print(f"\n  Gewaehlt (beste IS-Sharpe): ret_len={chosen_ret_len}, band_lookback={chosen_band_lookback}, band_mult={chosen_band_mult}")

    sig_p1 = run_pipeline(xau, xag, ret_len=chosen_ret_len, band_lookback=chosen_band_lookback, band_mult=chosen_band_mult)
    is_p1, oos_p1 = is_oos(sig_p1, BacktestConfig(spread_bps=SPREAD_BPS, **base_cfg_kwargs))
    print(f"\n  VALIDIERUNG (unveraendert auf OOS 2023-2026):")
    print(f"  IS   {fmt(is_p1)}")
    print(f"  OOS  {fmt(oos_p1)}   (Bot-Default OOS war: {fmt(oos_default)})")

    # ================================================================ Pass 2: stop/RR
    print("\n" + "=" * 100)
    print(f"PASS 2 - STOP/RR-SWEEP (ret_len={chosen_ret_len}, band_lookback={chosen_band_lookback}, band_mult={chosen_band_mult} FEST), NUR IN-SAMPLE")
    print("=" * 100)
    rows2 = []
    for stop_atr in STOP_ATR_CANDIDATES:
        for rr in RR_CANDIDATES:
            cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_atr, use_vwap_target=False, take_profit_r=rr)
            is_s, _ = is_oos(sig_p1, cfg)
            rows2.append({"stop_atr": stop_atr, "rr": rr, **is_s})
    sweep2 = pd.DataFrame(rows2)
    eligible2 = sweep2[sweep2["n_trades"] >= MIN_IS_TRADES]
    pivot = eligible2.pivot(index="stop_atr", columns="rr", values="sharpe") if not eligible2.empty else pd.DataFrame()
    print("\n  IS-Sharpe je (Stop-ATR x RR):")
    print(pivot.round(2).to_string() if not pivot.empty else "  keine Kombination erfuellt die Mindest-Trade-Schwelle")

    if eligible2.empty:
        chosen_stop, chosen_rr = ATR_STOP_MULT, RR_RATIO
        print("  Bot-Default (2.0/2.0) wird beibehalten.")
    else:
        best2 = eligible2.loc[eligible2["sharpe"].idxmax()]
        chosen_stop, chosen_rr = float(best2["stop_atr"]), float(best2["rr"])
        print(f"\n  Gewaehlt (beste IS-Sharpe): stop_atr={chosen_stop}, rr={chosen_rr}")

    is_p2, oos_p2 = is_oos(sig_p1, BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=chosen_stop, use_vwap_target=False, take_profit_r=chosen_rr))
    print(f"\n  VALIDIERUNG (unveraendert auf OOS 2023-2026):")
    print(f"  IS   {fmt(is_p2)}")
    print(f"  OOS  {fmt(oos_p2)}   (Pass-1-OOS war: {fmt(oos_p1)})")

    # ================================================================ Pass 3: Silver-confirm alignment filter
    print("\n" + "=" * 100)
    print(f"PASS 3 - SILBER-EIGENER-TREND-BESTAETIGUNGSFILTER (auf Pass-1/2-Config), NUR IN-SAMPLE")
    print("=" * 100)
    print("  Idee: nur handeln, wenn Silbers eigene N-Kerzen-Rendite bei Entry auch positiv ist")
    print("  (Plausibilitaetscheck: 'holt Silber wirklich auf' statt reinem Rauschen).")

    final_cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=chosen_stop, use_vwap_target=False, take_profit_r=chosen_rr)
    trades_p2 = simulate_trades(sig_p1, final_cfg)
    xag_ret = {}
    for n in CONFIRM_LEN_CANDIDATES:
        xag_ret[n] = (xag["close"] / xag["close"].shift(n) - 1.0).reindex(sig_p1.index, method="ffill")

    rows3 = []
    for n in CONFIRM_LEN_CANDIDATES:
        confirm_series = xag_ret[n]
        confirmed_entries = trades_p2["entry_time"].map(lambda t: confirm_series.asof(t) > 0 if pd.notna(confirm_series.asof(t)) else False)
        t_filtered = trades_p2[confirmed_entries.values]
        is_t = t_filtered[t_filtered["entry_time"] < SPLIT]
        is_idx = sig_p1[sig_p1.index < SPLIT].index
        is_s = summarize(is_t, is_idx)
        rows3.append({"confirm_len": n, **is_s})
    sweep3 = pd.DataFrame(rows3)
    print(sweep3[["confirm_len", "n_trades", "win_rate", "profit_factor", "sharpe"]].to_string(index=False))
    print(f"  (Referenz ohne Filter, IS: {fmt(is_p2)})")

    eligible3 = sweep3[sweep3["n_trades"] >= MIN_IS_TRADES]
    if eligible3.empty or eligible3["sharpe"].max() <= is_p2["sharpe"]:
        print("\n  Kein Confirm-Filter verbessert die IS-Sharpe gegenueber ungefiltert (oder zu wenig Trades) -- NICHT uebernommen.")
    else:
        best3 = eligible3.loc[eligible3["sharpe"].idxmax()]
        chosen_n = int(best3["confirm_len"])
        confirm_series = xag_ret[chosen_n]
        confirmed_entries = trades_p2["entry_time"].map(lambda t: confirm_series.asof(t) > 0 if pd.notna(confirm_series.asof(t)) else False)
        t_filtered = trades_p2[confirmed_entries.values]
        oos_t = t_filtered[t_filtered["entry_time"] >= SPLIT]
        oos_idx = sig_p1[sig_p1.index >= SPLIT].index
        oos_s = summarize(oos_t, oos_idx)
        print(f"\n  Gewaehlt: confirm_len={chosen_n}")
        print(f"  VALIDIERUNG OOS: {fmt(oos_s)}   (ohne Filter OOS war: {fmt(oos_p2)})")

    # ================================================================ Pass 4: diagnostic-only ratio-trendiness
    print("\n" + "=" * 100)
    print("PASS 4 - DIAGNOSE (NICHT IS/OOS-validiert: nur 3 unabhaengige Regime-Instanzen im 10J-Fenster, Silber-Daten reichen nicht weiter zurueck)")
    print("=" * 100)
    ratio_df = pd.DataFrame({"close": xau["close"] / xag["close"].reindex(xau.index, method="ffill")})
    ratio_df["high"], ratio_df["low"] = ratio_df["close"], ratio_df["close"]
    ratio_adx = compute_adx(ratio_df, n=14)["adx"]
    trades_p2 = trades_p2.copy()
    trades_p2["ratio_adx_at_entry"] = trades_p2["entry_time"].map(lambda t: ratio_adx.asof(t))
    trades_p2["ratio_regime"] = np.where(trades_p2["ratio_adx_at_entry"] >= 25, "ratio_trending (ADX>=25)", "ratio_choppy (ADX<25)")
    for name, g in trades_p2.groupby("ratio_regime"):
        wins = g[g["return_pct"] > 0]["return_pct"].sum()
        losses = -g[g["return_pct"] < 0]["return_pct"].sum()
        pf = wins / losses if losses > 0 else float("inf")
        print(f"  {name}: n={len(g)}, WR={(g['return_pct']>0).mean():.1%}, PF={pf:.2f}")
    print("  Nur als Hinweis zu lesen -- keine Empfehlung, das live umzusetzen.")


if __name__ == "__main__":
    main()
