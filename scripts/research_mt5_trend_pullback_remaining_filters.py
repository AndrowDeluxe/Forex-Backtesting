"""Tests the 3 building blocks not yet tried on the MT5 Trend+Pullback bot
(the other repo-standard ones -- ADX, Corwin-Schultz liquidity, cross-asset
metals alignment -- are already covered by research_mt5_trend_pullback_
adx_filter.py / _proven_filters.py, see that script's own docstring), on top
of the page's current "Standard-Empfehlung" (Gold/Silver-aligned/CHFJPY/
USDJPY/USDCAD, bot-default params, no ADX filter -- app_pages/
mt5_trend_pullback.py::run_standard_recommendation), same regime-shifted
window as that recommendation (new-IS 2023-01/2024-07, new-OOS 2024-07/
2026-08).

Same 3 blocks just tested on David-V2 (scripts/research_mt5_david_v2_
optimization.py), same IS-only-selection discipline: a candidate is only
adopted if it improves IS Sharpe over the unfiltered baseline, THEN gets
validated on OOS unchanged. Looking at OOS first and picking whichever
looks best there would defeat the entire point of the split.

Result: NONE of the three clears the IS bar (see module-level print at the
end) -- the existing Standard-Empfehlung remains the best-supported
recommendation, unchanged. This is documented here so it isn't re-tested.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from bond_yield_indicator.calendar import event_window_dummy
from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.filters import alignment_filter
from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.kalman_filter import kalman_smooth
from strategy.metrics import summarize
from strategy.mtf_ema_ribbon import attach_mtf_ema_ribbon, ribbon_bias

pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")

# (Dukascopy key, timeframe, MT5 label, spread bps, CB banks whose meetings move this instrument)
MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0, ["FOMC"]),
    ("SILVER", "H1", "XAGUSD", 10.0, ["FOMC"]),
    ("CHFJPY", "H4", "CHFJPY", 3.0, ["SNB", "BOJ"]),
    ("USDJPY", "H4", "USDJPY", 1.5, ["FOMC", "BOJ"]),
    ("USDCAD", "H4", "USDCAD", 1.5, ["FOMC", "BOC"]),
]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}"


def pooled(tbm: dict, ibm: dict) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    non_empty = [t for t in tbm.values() if not t.empty]
    t = pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()
    starts = [i.min() for i in ibm.values() if len(i)]
    ends = [i.max() for i in ibm.values() if len(i)]
    fi = pd.date_range(min(starts), max(ends), freq="D") if starts else pd.DatetimeIndex([])
    return t, fi


def build_trades(
    label: str, df: pd.DataFrame, spread_bps: float, banks: list[str], gold_daily: pd.Series,
    use_ribbon: bool = False,
    use_kalman: bool = False, kalman_mnf: float = 0.5, kalman_slope_len: int = 10,
    use_cb: bool = False, cb_window: int = 1,
) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    sig = run_pipeline(df)  # bot-default params, no adx_min -- matches the Standard-Empfehlung's own build()

    if use_ribbon:
        sig_r = attach_mtf_ema_ribbon(sig)
        bias = ribbon_bias(sig_r)
        agree = (bias > 0) | (sig["signal"] == 0)  # long-only bot: only need the bullish-stack case
        sig = sig.copy()
        sig.loc[~agree, "signal"] = 0

    if use_kalman:
        smoothed = kalman_smooth(sig["close"], measurement_noise_fraction=kalman_mnf)
        slope_ok = (smoothed - smoothed.shift(kalman_slope_len)) > 0
        sig = sig.copy()
        sig.loc[(sig["signal"] == 1) & ~slope_ok, "signal"] = 0

    if use_cb:
        dates = (sig.index.tz_localize(None) if sig.index.tz is not None else sig.index).normalize()
        blocked = pd.Series(False, index=sig.index)
        for bank in banks:
            d = event_window_dummy(bank, pd.DatetimeIndex(dates.unique()), window_days=cb_window)
            blocked |= pd.Series(dates.map(d).values, index=sig.index).astype(bool)
        sig = sig.copy()
        sig.loc[blocked.values, "signal"] = 0

    cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    trades = simulate_trades(sig, cfg)
    if label == "XAGUSD" and not trades.empty:
        trades = alignment_filter(trades, gold_daily)  # matches the Standard-Empfehlung's own Gold-confirms-Silver step
    return trades, sig.index


def main():
    raw = {}
    for key, tf, label, spread_bps, banks in MARKETS:
        print(f"Fetching {label} {tf} {DATA_START} -> {DATA_END} ...")
        df = fetch_timeframe(key, tf, DATA_START, DATA_END).rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        raw[label] = (df, spread_bps, banks)

    gold_daily = fetch_timeframe("GOLD", "D1", DATA_START, DATA_END)["Close"]
    if gold_daily.index.tz is not None:
        gold_daily.index = gold_daily.index.tz_localize(None)

    def run_variant(**kwargs) -> tuple[dict, dict]:
        is_t, is_idx, oos_t, oos_idx = {}, {}, {}, {}
        for label, (df, spread_bps, banks) in raw.items():
            trades, idx = build_trades(label, df, spread_bps, banks, gold_daily, **kwargs)
            is_t[label] = trades[(trades["entry_time"] >= NEW_IS_START) & (trades["entry_time"] < NEW_SPLIT)] if not trades.empty else trades
            is_idx[label] = idx[(idx >= NEW_IS_START) & (idx < NEW_SPLIT)]
            oos_t[label] = trades[trades["entry_time"] >= NEW_SPLIT] if not trades.empty else trades
            oos_idx[label] = idx[idx >= NEW_SPLIT]
        p_is, i_is = pooled(is_t, is_idx)
        p_oos, i_oos = pooled(oos_t, oos_idx)
        return summarize(p_is, i_is), summarize(p_oos, i_oos)

    print("\nReferenz (Standard-Empfehlung, kein neuer Filter):")
    is_ref, oos_ref = run_variant()
    print(f"  IS {fmt(is_ref)}   OOS {fmt(oos_ref)}")

    print("\nMit MTF-EMA-Ribbon (strategy/mtf_ema_ribbon.py):")
    is_r, oos_r = run_variant(use_ribbon=True)
    print(f"  IS {fmt(is_r)}   OOS {fmt(oos_r)}")
    print("  -> IS-Sharpe SINKT (1.92 -> 0.95) -- verworfen, verbessert nicht mal IS.")

    print("\nMit Kalman-Slope-Bestaetigung (strategy/kalman_filter.py, mnf=0.5, slope_len=10):")
    is_k, oos_k = run_variant(use_kalman=True)
    print(f"  IS {fmt(is_k)}   OOS {fmt(oos_k)}")
    print("  -> Stichprobe kollabiert auf n=2 ueber 18 Monate x 5 Maerkte -- unbrauchbar, verworfen.")

    print("\nMit CB-Event-Window (bond_yield_indicator/calendar.py, window_days=1):")
    is_cb, oos_cb = run_variant(use_cb=True)
    print(f"  IS {fmt(is_cb)}   OOS {fmt(oos_cb)}")
    print("  -> IS-Sharpe SINKT leicht (1.92 -> 1.70), obwohl OOS besser aussieht (0.90 -> 1.31).")
    print("     Nach der IS-only-Auswahlregel NICHT uebernommen -- ein Filter erst nach Blick auf")
    print("     die (bessere) OOS-Zahl zu waehlen waere genau das Data-Snooping, vor dem der")
    print("     Prozess schuetzen soll. Bleibt eine interessante, aber nicht validierte Beobachtung.")

    print("\n" + "=" * 100)
    print("FAZIT: keiner der 3 verbleibenden Bausteine verbessert die In-Sample-Sharpe gegenueber")
    print("der bestehenden Standard-Empfehlung -- keiner wird uebernommen. Standard-Empfehlung bleibt")
    print("unveraendert die beste unterstuetzte Konfiguration.")
    print("=" * 100)


if __name__ == "__main__":
    main()
