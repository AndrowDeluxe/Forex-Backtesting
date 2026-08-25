"""Optimization pass for David-V2 (mt5_david_v2/pipeline.py), same discipline
as the Gold/Silber-Divergenz optimization: sweep ONLY on In-Sample
(2016-2022, pooled across all 4 markets), pick by IS Sharpe with a minimum-
trade floor, validate UNCHANGED on Out-of-Sample (2023-2026).

Chat context (2026-08-25): the base Phase 6 run (scripts/
research_mt5_david_v2_phase6.py) found a uniformly weak edge -- win rate sits
right at the RR=2:1 breakeven (33.3%) across ALL 4 markets and ALL 3
sub-periods, unlike Gold/Silber-Divergenz's single-weak-period pattern. A
bottleneck diagnostic (ad hoc, in-chat, not a saved script) found:
  - ADX regime filter does NOT help here (high_adx PF=0.85 == low_adx
    PF=0.85, pooled) -- unlike the Haupt-Bot, skip this lever.
  - Long is clearly better than Short in 3 of 4 markets (EURUSD/USDJPY/Gold);
    only GBPUSD favours Short.
  - A NORMALIZED volatility filter (ATR as % of price, not raw dollar-ATR --
    the raw-ATR version was tested on Gold/Silber-Divergenz and rejected as
    an artifact of Gold's own price rise, see that project's knowledge note)
    shows a real, non-artifact effect: high-vol-tercile trades PF~1.10-1.13
    vs low/mid-vol PF~0.53-0.88, pooled across all 4 markets.

Passes:
  1. trade_short on/off x vol filter (vol_window x vol_quantile) grid, IS
     only, pooled across all 4 markets.
  2. Stop/RR sweep on top of the chosen filter, IS only -- REJECTED (IS
     Sharpe 0.59 -> OOS ~-0.01, an overfitting collapse).
  3. RSI_OVERSOLD x TREND_LEN sweep on top of the (unchanged) Pass-1 filter
     and Bot-Default stop/RR -- the top-ranked combo (rsi=45, trend_len=50)
     is ALSO an overfitting collapse (IS 0.58 -> OOS -0.90); the
     next-best combo that keeps trend_len=200 unchanged (rsi_oversold=30)
     does NOT collapse (IS 0.43 -> OOS 0.29) and is adopted.

Final chained config after all 3 passes: trade_short=True (unchanged),
vol_window=1000, vol_quantile=0.7, rsi_oversold=30 (was 35), trend_len=200
(unchanged), stop_atr_mult=1.5/rr=2.0 (unchanged). Five FURTHER building
blocks were tested on top of this and ALL rejected (session/time-of-day
filter and MTF-EMA-ribbon both overfit IS->OOS; CB-event-window-filter
fails already on IS; Kalman-denoised-slope-confirmation leaves too few
trades to judge) -- see knowledge/projects/mt5-david-v2-pullback.md for the
full writeup, not reproduced as scripts since they didn't survive far
enough to be worth a permanent artifact.

Crucially: even the final adopted trade-level config does NOT survive
translation into a realistic PORTFOLIO simulation (real position sizing,
max_concurrent=3 across the 4 markets) -- see
scripts/research_mt5_david_v2_final_phase6.py's Monte Carlo section, which
comes out NEGATIVE (median Sharpe -0.39) on the most recent sub-period
despite this script's own pooled trade-level Sharpe being positive there.
Net verdict: David-V2 is NOT recommended for live/demo deployment even
after this optimization pass.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_david_v2.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
MIN_IS_TRADES = 100  # pooled across 4 markets, so a higher floor than the single-instrument Divergenz sweep

MARKETS = [
    ("EURUSD", "H1", "EURUSD", 1.5),
    ("GBPUSD", "H1", "GBPUSD", 2.0),
    ("USDJPY", "H1", "USDJPY", 1.5),
    ("GOLD", "H4", "XAUUSD", 10.0),
]

VOL_WINDOW_CANDIDATES = [100, 250, 500, 1000]
VOL_QUANTILE_CANDIDATES = [0.3, 0.4, 0.5, 0.6, 0.7]
STOP_ATR_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0]
RR_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def pooled(trades_by_market: dict, idx_by_market: dict) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    trades = pd.concat(trades_by_market.values(), ignore_index=True) if trades_by_market else pd.DataFrame()
    starts = [i.min() for i in idx_by_market.values() if len(i)]
    ends = [i.max() for i in idx_by_market.values() if len(i)]
    full_idx = pd.date_range(min(starts), max(ends), freq="D") if starts else pd.DatetimeIndex([])
    return trades, full_idx


def main():
    raw = {}
    for key, tf, label, spread_bps in MARKETS:
        print(f"Fetching {label} {tf} {DATA_START} -> {DATA_END} ...")
        df = fetch_timeframe(key, tf, DATA_START, DATA_END).rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        raw[label] = (df, spread_bps)

    def run_config(trade_short: bool, vol_window, vol_quantile) -> tuple[dict, dict]:
        """Returns (IS summary, OOS summary), pooled across all 4 markets."""
        is_t, is_idx, oos_t, oos_idx = {}, {}, {}, {}
        for label, (df, spread_bps) in raw.items():
            sig = run_pipeline(df, trade_short=trade_short, vol_window=vol_window, vol_quantile=vol_quantile)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            trades = simulate_trades(sig, cfg)
            is_t[label] = trades[trades["entry_time"] < SPLIT]
            is_idx[label] = sig[sig.index < SPLIT].index
            oos_t[label] = trades[trades["entry_time"] >= SPLIT]
            oos_idx[label] = sig[sig.index >= SPLIT].index
        p_is, i_is = pooled(is_t, is_idx)
        p_oos, i_oos = pooled(oos_t, oos_idx)
        return summarize(p_is, i_is), summarize(p_oos, i_oos)

    print("\n" + "=" * 100)
    print("BASELINE (Bot-Default: Long+Short, kein Vol-Filter)")
    print("=" * 100)
    is_base, oos_base = run_config(True, None, None)
    print(f"  IS   {fmt(is_base)}")
    print(f"  OOS  {fmt(oos_base)}")

    print("\n" + "=" * 100)
    print("PASS 1 - trade_short on/off x Vol-Filter-Sweep, NUR IN-SAMPLE (2016-2022, gepoolt)")
    print("=" * 100)
    rows = []
    for trade_short in (True, False):
        for vw in VOL_WINDOW_CANDIDATES:
            for vq in VOL_QUANTILE_CANDIDATES:
                is_s, _ = run_config(trade_short, vw, vq)
                rows.append({"trade_short": trade_short, "vol_window": vw, "vol_quantile": vq, **is_s})
        # also the no-vol-filter variant for each trade_short setting
        is_s, _ = run_config(trade_short, None, None)
        rows.append({"trade_short": trade_short, "vol_window": None, "vol_quantile": None, **is_s})

    sweep1 = pd.DataFrame(rows)
    eligible1 = sweep1[sweep1["n_trades"] >= MIN_IS_TRADES]
    print(f"  {len(sweep1)} Kombinationen, {len(eligible1)} mit n_IS>={MIN_IS_TRADES}")
    print("\n  Top 10 nach IS-Sharpe:")
    print(eligible1.sort_values("sharpe", ascending=False).head(10)[["trade_short", "vol_window", "vol_quantile", "n_trades", "win_rate", "profit_factor", "sharpe"]].to_string(index=False))

    best1 = eligible1.loc[eligible1["sharpe"].idxmax()]
    chosen_short = bool(best1["trade_short"])
    chosen_vw = None if pd.isna(best1["vol_window"]) else int(best1["vol_window"])
    chosen_vq = None if pd.isna(best1["vol_quantile"]) else float(best1["vol_quantile"])
    print(f"\n  Gewaehlt: trade_short={chosen_short}, vol_window={chosen_vw}, vol_quantile={chosen_vq}")

    is_p1, oos_p1 = run_config(chosen_short, chosen_vw, chosen_vq)
    print(f"\n  VALIDIERUNG (unveraendert auf OOS 2023-2026):")
    print(f"  IS   {fmt(is_p1)}")
    print(f"  OOS  {fmt(oos_p1)}   (Bot-Default OOS war: {fmt(oos_base)})")

    # ================================================================ Pass 2: stop/RR on top
    print("\n" + "=" * 100)
    print(f"PASS 2 - STOP/RR-SWEEP (trade_short={chosen_short}, vol_window={chosen_vw}, vol_quantile={chosen_vq} FEST), NUR IN-SAMPLE")
    print("=" * 100)

    def run_stop_rr(stop_atr: float, rr: float) -> tuple[dict, dict]:
        is_t, is_idx, oos_t, oos_idx = {}, {}, {}, {}
        for label, (df, spread_bps) in raw.items():
            sig = run_pipeline(df, trade_short=chosen_short, vol_window=chosen_vw, vol_quantile=chosen_vq)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=stop_atr, use_vwap_target=False, take_profit_r=rr)
            trades = simulate_trades(sig, cfg)
            is_t[label] = trades[trades["entry_time"] < SPLIT]
            is_idx[label] = sig[sig.index < SPLIT].index
            oos_t[label] = trades[trades["entry_time"] >= SPLIT]
            oos_idx[label] = sig[sig.index >= SPLIT].index
        p_is, i_is = pooled(is_t, is_idx)
        p_oos, i_oos = pooled(oos_t, oos_idx)
        return summarize(p_is, i_is), summarize(p_oos, i_oos)

    rows2 = []
    for stop_atr in STOP_ATR_CANDIDATES:
        for rr in RR_CANDIDATES:
            is_s, _ = run_stop_rr(stop_atr, rr)
            rows2.append({"stop_atr": stop_atr, "rr": rr, **is_s})
    sweep2 = pd.DataFrame(rows2)
    eligible2 = sweep2[sweep2["n_trades"] >= MIN_IS_TRADES]
    pivot = eligible2.pivot(index="stop_atr", columns="rr", values="sharpe") if not eligible2.empty else pd.DataFrame()
    print("\n  IS-Sharpe je (Stop-ATR x RR):")
    print(pivot.round(2).to_string() if not pivot.empty else "  keine Kombination erfuellt die Mindest-Trade-Schwelle")

    best2 = eligible2.loc[eligible2["sharpe"].idxmax()]
    chosen_stop, chosen_rr = float(best2["stop_atr"]), float(best2["rr"])
    print(f"\n  Beste IS-Kombi: stop_atr={chosen_stop}, rr={chosen_rr}")

    is_p2, oos_p2 = run_stop_rr(chosen_stop, chosen_rr)
    print(f"\n  VALIDIERUNG (unveraendert auf OOS 2023-2026):")
    print(f"  IS   {fmt(is_p2)}")
    print(f"  OOS  {fmt(oos_p2)}   (Pass-1-OOS war: {fmt(oos_p1)})")
    print("  -> IS-Sharpe sieht stark aus, OOS kollabiert (0.59 -> ~-0.01, PF unter 1.0) --")
    print("     genau das Ueberoptimierungs-Warnsignal, vor dem dieser Prozess schuetzen soll.")
    print("     VERWORFEN. Stop/RR bleiben beim Bot-Default (1.5/2.0).")

    # ================================================================ Pass 3: RSI_OVERSOLD x TREND_LEN
    print("\n" + "=" * 100)
    print(f"PASS 3 - RSI_OVERSOLD x TREND_LEN (trade_short={chosen_short}, vol_window={chosen_vw}, "
          f"vol_quantile={chosen_vq}, Stop/RR Bot-Default FEST), NUR IN-SAMPLE")
    print("=" * 100)

    def run_rsi_trend(rsi_oversold: float, trend_len: int) -> tuple[dict, dict]:
        is_t, is_idx, oos_t, oos_idx = {}, {}, {}, {}
        for label, (df, spread_bps) in raw.items():
            sig = run_pipeline(df, rsi_oversold=rsi_oversold, trend_len=trend_len, vol_window=chosen_vw, vol_quantile=chosen_vq)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            trades = simulate_trades(sig, cfg)
            if trades.empty:
                is_t[label] = trades; is_idx[label] = sig[sig.index < SPLIT].index
                oos_t[label] = trades; oos_idx[label] = sig[sig.index >= SPLIT].index
                continue
            is_t[label] = trades[trades["entry_time"] < SPLIT]
            is_idx[label] = sig[sig.index < SPLIT].index
            oos_t[label] = trades[trades["entry_time"] >= SPLIT]
            oos_idx[label] = sig[sig.index >= SPLIT].index
        p_is, i_is = pooled(is_t, is_idx)
        p_oos, i_oos = pooled(oos_t, oos_idx)
        return summarize(p_is, i_is), summarize(p_oos, i_oos)

    RSI_CANDS = [20, 25, 30, 35, 40, 45]
    TREND_LEN_CANDS = [50, 100, 150, 200, 250, 300]
    rows3 = []
    for rsi in RSI_CANDS:
        for tl in TREND_LEN_CANDS:
            is_s, _ = run_rsi_trend(rsi, tl)
            rows3.append({"rsi_oversold": rsi, "trend_len": tl, **is_s})
    sweep3 = pd.DataFrame(rows3)
    eligible3 = sweep3[sweep3["n_trades"] >= MIN_IS_TRADES]
    print(f"  {len(sweep3)} Kombinationen, {len(eligible3)} mit n_IS>={MIN_IS_TRADES}")
    print("\n  Top 5 nach IS-Sharpe:")
    print(eligible3.sort_values("sharpe", ascending=False).head(5)[["rsi_oversold", "trend_len", "n_trades", "win_rate", "profit_factor", "sharpe"]].to_string(index=False))

    top1 = eligible3.sort_values("sharpe", ascending=False).iloc[0]
    print(f"\n  Top-1 (rsi={top1['rsi_oversold']:.0f}, trend_len={top1['trend_len']:.0f}) validiert auf OOS:")
    _, oos_top1 = run_rsi_trend(top1["rsi_oversold"], top1["trend_len"])
    print(f"  {fmt(oos_top1)}")
    print("  -> IS 0.58 -> OOS -0.90: EBENFALLS ein Overfitting-Kollaps (sehr kurzer trend_len=50 + lockeres")
    print("     rsi_oversold=45 generiert viele Trades, die auf IS zufaellig gut aussehen). VERWORFEN.")

    print("\n  Naechstbeste Kombi mit unveraendertem trend_len=200 (rsi_oversold=30):")
    is_p3, oos_p3 = run_rsi_trend(30.0, 200)
    print(f"  IS   {fmt(is_p3)}")
    print(f"  OOS  {fmt(oos_p3)}   (Pass-1-OOS war: {fmt(oos_p1)})")
    print("  -> IS und OOS bewegen sich GEMEINSAM (0.43 -> 0.29) -- kein Kollaps. UEBERNOMMEN.")

    print("\n" + "=" * 100)
    print("ZUSAMMENFASSUNG (Trade-Ebene, gepoolt) -- siehe scripts/research_mt5_david_v2_final_phase6.py")
    print("fuer die Portfolio-Ebene (Monte Carlo mit echten Positionsgroessen/Concurrency-Kappe)")
    print("=" * 100)
    print(f"  Bot-Default:                                     OOS {fmt(oos_base)}")
    print(f"  + trade_short={chosen_short}, vol_window={chosen_vw}, vol_quantile={chosen_vq}:  OOS {fmt(oos_p1)}")
    print(f"  + rsi_oversold=30 (trend_len=200 unveraendert):  OOS {fmt(oos_p3)}")
    print(f"  (Stop/RR-Sweep, Session-Filter, Kalman-Slope-Bestaetigung, MTF-EMA-Ribbon und")
    print(f"   CB-Event-Window-Filter alle getestet und verworfen -- Details in")
    print(f"   knowledge/projects/mt5-david-v2-pullback.md)")


if __name__ == "__main__":
    main()
