"""Sweep of every UNTESTED filter idea already validated (or explicitly
rejected) elsewhere in this repo, applied to ORB on Nasdaq/SP500 - on top of
the already-confirmed baseline (long_only + ADX>=25 + per-asset weekday
exclusion, see orb_strategy/pipeline.py / app_pages/orb_strategy.py).

Each candidate is tested ONE AT A TIME on top of that baseline (not
stacked), using the SAME In-Sample(2016-2021)-rank / Out-of-Sample(2021-
2026)-confirm discipline already established and trusted for the weekday
filter (see research_orb_weekday_filter_oos.py) - rank buckets by profit
factor using ONLY the In-Sample half, then check whether dropping the
IS-weakest bucket still helps on the untouched OOS half. Continuous filters
are tercile-bucketed using IS-only quantile edges (no OOS leakage into the
bucket boundaries themselves); binary alignment filters are naturally
2-bucketed (aligned / not aligned).

Deliberately NOT re-tuning any numeric threshold beyond what the ranking
itself picks - per-filter constants (SMA window, theta multiplier, ADX
ceiling, lookback bars) are carried over AS-IS from wherever they were
already validated in another project, not re-optimized against ORB's own
IS data (that is exactly the pattern that produced the rejected volume-
confirmation filter: "looks better in-sample the stricter you sweep it").

Explicitly OUT OF SCOPE for this pass (see chat writeup for why): COT
sentiment (Gold-specific hardcoded fetch, itself rejected there), GMM
regime clustering (rejected elsewhere for trade fragmentation reasons that
do not obviously transfer, but building a leakage-safe version is a
separate, bigger effort), N-bar breakout-acceptance/retest confirmation
(requires shifting the entry bar itself, a bigger change to the execution
model, not a drop-in trades-frame filter like everything else here),
volume-profile LVN/HVN proximity (weak effect elsewhere, extra engineering
for a rolling profile), and the execution-timing overlay (a fill-price
mechanic, not a signal filter - separate follow-up).
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.jump_activity import compute_daily_jump_ratio
from asian_range_breakout.vix import fetch_vix_daily
from bond_yield_indicator.calendar import event_window_dummy
from bond_yield_indicator.fred import fetch_yield
from bond_yield_indicator.friction import corwin_schultz_spread
from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import compute_orb_frame, generate_orb_signal
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.indicators import compute_adaptive_theta, compute_adx
from strategy.metrics import summarize, trade_stats

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
WEEKDAY_FILTER = {"NASDAQ": "Thursday", "SP500": "Monday"}
MIN_BUCKET_N = 10


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _prior_value(entry_dates: np.ndarray, daily_series: pd.Series) -> np.ndarray:
    """Most recent value of daily_series strictly BEFORE each entry date -
    same no-lookahead convention as asian_range_breakout.filters._attach_prior_day_series."""
    s = daily_series.dropna().sort_index()
    idx = s.index.searchsorted(entry_dates, side="left") - 1
    idx_c = idx.clip(min=0)
    vals = s.to_numpy(dtype=float)[idx_c]
    vals[idx < 0] = np.nan
    return vals


def _tercile_bucket(values: pd.Series, is_mask: np.ndarray) -> pd.Series:
    is_vals = values[is_mask].dropna()
    if is_vals.nunique() < 3 or len(is_vals) < 30:
        return pd.Series(np.nan, index=values.index, dtype=object)
    try:
        _, edges = pd.qcut(is_vals, 3, retbins=True, duplicates="drop")
    except ValueError:
        return pd.Series(np.nan, index=values.index, dtype=object)
    if len(edges) < 4:
        return pd.Series(np.nan, index=values.index, dtype=object)
    edges = edges.copy()
    edges[0], edges[-1] = -np.inf, np.inf
    labels = ["low", "mid", "high"][: len(edges) - 1]
    return pd.cut(values, bins=edges, labels=labels, include_lowest=True).astype(object)


def _binary_align(nan_mask: np.ndarray, aligned_mask: np.ndarray) -> np.ndarray:
    """Object array of 'aligned'/'not_aligned'/NaN - avoids numpy's
    float/str DType promotion error from mixing np.nan into a np.where
    string branch."""
    out = np.full(nan_mask.shape, np.nan, dtype=object)
    valid = ~nan_mask
    out[valid] = np.where(aligned_mask[valid], "aligned", "not_aligned")
    return out


def _bucket_table(trades_subset: pd.DataFrame, bucket_col: str, min_n: int = MIN_BUCKET_N) -> pd.DataFrame:
    rows = []
    for b, g in trades_subset.groupby(bucket_col, observed=True):
        if pd.isna(b) or len(g) < min_n:
            continue
        s = trade_stats(g)
        rows.append({"bucket": b, "n": s["n_trades"], "win_rate": s["win_rate"], "profit_factor": s["profit_factor"]})
    return pd.DataFrame(rows).set_index("bucket").sort_values("profit_factor") if rows else pd.DataFrame()


def test_bucket_filter(label: str, trades: pd.DataFrame, bucket_col: str, split_ts: pd.Timestamp, full_index: pd.DatetimeIndex):
    print(f"\n--- {label} ---")
    is_trades = trades[trades["entry_time"] < split_ts]
    oos_all = trades[trades["entry_time"] >= split_ts]
    oos_index = full_index[full_index >= split_ts]

    is_table = _bucket_table(is_trades, bucket_col)
    if is_table.empty or len(is_table) < 2:
        print("  zu wenig IS-Buckets (< 2 mit genug Trades) - uebersprungen.")
        return
    print("IS-Ranking (schwaechster Bucket zuerst):")
    print(is_table.to_string())

    weakest = is_table.index[0]
    oos_baseline = summarize(oos_all, oos_index)
    oos_filtered = summarize(oos_all[oos_all[bucket_col] != weakest], oos_index)
    print(f"-> IS-schwaechster Bucket: {weakest!r} (PF {is_table.iloc[0]['profit_factor']:.2f}, n={int(is_table.iloc[0]['n'])})")
    print(f"OOS Baseline:        n={oos_baseline['n_trades']:>4}  sharpe={oos_baseline['sharpe']:>6.2f}  pf={oos_baseline['profit_factor']:>5.2f}  win={oos_baseline['win_rate']:.1%}")
    print(f"OOS ohne {str(weakest):<9}n={oos_filtered['n_trades']:>4}  sharpe={oos_filtered['sharpe']:>6.2f}  pf={oos_filtered['profit_factor']:>5.2f}  win={oos_filtered['win_rate']:.1%}")


def test_direct_filter(label: str, trades: pd.DataFrame, keep_mask: pd.Series, split_ts: pd.Timestamp, full_index: pd.DatetimeIndex):
    print(f"\n--- {label} ---")
    for seg_name, lo, hi in [("IS", None, split_ts), ("OOS", split_ts, None)]:
        if lo is None:
            seg_trades = trades[trades["entry_time"] < hi]
            seg_index = full_index[full_index < hi]
        else:
            seg_trades = trades[trades["entry_time"] >= lo]
            seg_index = full_index[full_index >= lo]
        seg_mask = keep_mask.reindex(seg_trades.index).fillna(False)
        base = summarize(seg_trades, seg_index)
        filt = summarize(seg_trades[seg_mask], seg_index)
        print(f"{seg_name} Baseline:  n={base['n_trades']:>4}  sharpe={base['sharpe']:>6.2f}  pf={base['profit_factor']:>5.2f}  win={base['win_rate']:.1%}")
        print(f"{seg_name} Gefiltert: n={filt['n_trades']:>4}  sharpe={filt['sharpe']:>6.2f}  pf={filt['profit_factor']:>5.2f}  win={filt['win_rate']:.1%}")


def build_frame(raw_df: pd.DataFrame) -> pd.DataFrame:
    base = compute_orb_frame(raw_df, atr_n=14, atr_mult=1.0)
    base["adx10"] = compute_adx(base, n=10)["adx"]
    base["adx20"] = compute_adx(base, n=20)["adx"]
    base["momentum_r"] = (base["close"] - base["close"].shift(8)) / base["atr"]
    if "volume" in base.columns:
        typical = (base["high"] + base["low"] + base["close"]) / 3.0
        pv = typical * base["volume"]
        cum_pv = pv.groupby(base["session"]).cumsum()
        cum_vol = base["volume"].groupby(base["session"]).cumsum()
        base["session_vwap"] = cum_pv / cum_vol
        base["deviation"] = (base["close"] - base["session_vwap"]) / base["session_vwap"]
        theta = compute_adaptive_theta(base, window_bars=500, multiplier=1.0)
        base["dev_over_theta"] = base["deviation"].abs() / theta
    signaled = generate_orb_signal(base)
    return signaled


def daily_series(base: pd.DataFrame) -> dict:
    close = base["close"].tz_localize(None).resample("1D").last().dropna() if base.index.tz else base["close"].resample("1D").last().dropna()
    high = base["high"].tz_localize(None).resample("1D").max().dropna() if base.index.tz else base["high"].resample("1D").max().dropna()
    low = base["low"].tz_localize(None).resample("1D").min().dropna() if base.index.tz else base["low"].resample("1D").min().dropna()
    sma100 = close.rolling(100).mean()
    # corwin_schultz_spread's own window is [t, t+1] (needs tomorrow's H/L to
    # know today's value) - shift(1) on top of that so the value used for a
    # "prior day" join is only ever built from data at least 2 days old,
    # never same-day-or-later.
    cs_spread = corwin_schultz_spread(high, low).shift(1)
    cs_threshold = cs_spread.expanding(min_periods=250).quantile(2 / 3).shift(1)
    jump_ratio = compute_daily_jump_ratio(base)
    if jump_ratio.index.tz is not None:
        jump_ratio.index = jump_ratio.index.tz_localize(None)
    return {
        "close": close, "sma100": sma100, "cs_spread": cs_spread,
        "cs_threshold": cs_threshold, "jump_ratio": jump_ratio,
    }


def run_asset(name: str, base: pd.DataFrame, daily: dict, other_daily_close_sma: pd.Series, vix_daily: pd.Series, y10_daily: pd.Series):
    print(f"\n{'=' * 20} {name} {'=' * 20}")
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)

    signaled = base.copy()
    if True:  # baseline confirmed filters: long_only + adx>=25 + per-asset weekday
        signaled.loc[signaled["signal"] == -1, "signal"] = 0
        signaled.loc[signaled["adx"] < 25.0, "signal"] = 0
        signaled.loc[signaled.index.day_name() == WEEKDAY_FILTER[name], "signal"] = 0

    trades = simulate_trades(signaled, cfg)
    if trades.empty:
        print("Keine Trades in der Baseline-Konfiguration.")
        return

    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    full_index = signaled.index

    pos = base.index.get_indexer(trades["entry_time"]) - 1
    sig_time = base.index[pos]
    entry_dates = sig_time.tz_localize(None).normalize().to_numpy() if sig_time.tz else sig_time.normalize().to_numpy()

    t = trades.reset_index(drop=True).copy()
    is_mask = (t["entry_time"] < split_ts).to_numpy()

    # 1. vol_regime (day_atr expansion/contraction) - already computed, never wired as a filter
    t["vol_regime"] = base["vol_regime"].to_numpy()[pos]
    test_bucket_filter("1. vol_regime (expansion/contraction, Tages-ATR vs. rollierendem Median) - bereits berechnet, nie verdrahtet", t, "vol_regime", split_ts, full_index)

    # 2. ADX ceiling (10/14/20 all >= 25 -> ensemble; separately, plain ceiling bucket)
    t["adx_sig"] = base["adx"].to_numpy()[pos]
    t["adx_bucket"] = _tercile_bucket(t["adx_sig"], is_mask)
    test_bucket_filter("2. ADX-Ceiling (Tercile des ADX am Signal-Bar, oberhalb des bestehenden ADX>=25-Floors)", t, "adx_bucket", split_ts, full_index)

    # 3. SMA100 trend-bias (own instrument, prior day close vs prior day SMA100)
    close_prior = _prior_value(entry_dates, daily["close"])
    sma_prior = _prior_value(entry_dates, daily["sma100"])
    aligned = close_prior > sma_prior  # baseline is long-only, so "aligned" = uptrend
    t["trend_bias"] = _binary_align(np.isnan(close_prior) | np.isnan(sma_prior), aligned)
    test_bucket_filter("3. SMA100-Trendbias (eigenes Instrument, Vortages-Close vs. Vortages-SMA100) - cls_practical-Konvention", t, "trend_bias", split_ts, full_index)

    # 4. Corwin-Schultz liquidity (own instrument, causal expanding 2/3-quantile threshold)
    fric = _prior_value(entry_dates, daily["cs_spread"])
    thr = _prior_value(entry_dates, daily["cs_threshold"])
    keep = pd.Series(np.where(np.isnan(fric) | np.isnan(thr), np.nan, fric <= thr), index=t.index)
    keep_bool = keep.fillna(False).astype(bool)
    test_direct_filter("4. Corwin-Schultz-Liquiditaetsfilter (eigenes Instrument, kausale expandierende 2/3-Quantil-Schwelle, wie bei Gold-ASB validiert)", t, keep_bool, split_ts, full_index)

    # 5. VWAP-deviation "not overextended" (session VWAP, adaptive theta mult=1.0)
    if "dev_over_theta" in base.columns:
        t["dev_bucket"] = _tercile_bucket(pd.Series(base["dev_over_theta"].to_numpy()[pos]), is_mask)
        test_bucket_filter("5. VWAP-Abstand / adaptive Theta (Tercile von |Deviation|/Theta am Signal-Bar) - Fundament-Baustein der ADX-VWAP-Strategie", t, "dev_bucket", split_ts, full_index)

    # 6. Pre-breakout momentum alignment (8-bar ATR-normalized net move ending at signal bar)
    mom = base["momentum_r"].to_numpy()[pos]
    t["mom_align"] = _binary_align(np.isnan(mom), mom > 0)
    test_bucket_filter("6. Pre-Breakout-Momentum-Alignment (8-Bar ATR-normierte Bewegung vor dem Signal-Bar, asian_range_breakout-Konvention)", t, "mom_align", split_ts, full_index)

    # 7. Ensemble ADX agreement (10/14/20 all >= 25)
    adx10 = base["adx10"].to_numpy()[pos]
    adx20 = base["adx20"].to_numpy()[pos]
    t["adx_ensemble"] = _binary_align(np.isnan(adx10) | np.isnan(adx20), (adx10 >= 25) & (adx20 >= 25))
    test_bucket_filter("7. ADX-Ensemble (ADX(10)/ADX(14)/ADX(20) muessen alle >=25 sein, statt nur ADX(14))", t, "adx_ensemble", split_ts, full_index)

    # 8. Cross-asset trend alignment (other US index's own SMA100 bias)
    if other_daily_close_sma is not None:
        other_close_p, other_sma_p = other_daily_close_sma
        oc = _prior_value(entry_dates, other_close_p)
        os_ = _prior_value(entry_dates, other_sma_p)
        t["cross_asset"] = _binary_align(np.isnan(oc) | np.isnan(os_), oc > os_)
        test_bucket_filter("8. Cross-Asset-Bestaetigung (SMA100-Trendbias des JEWEILS ANDEREN US-Index, Nasdaq<->SP500)", t, "cross_asset", split_ts, full_index)

    # 9. Session-hour gate (IS-rank weakest entry hour, same method as exclude_weekday)
    t["entry_hour"] = trades["entry_time"].dt.hour.to_numpy()
    test_bucket_filter("9. Session-Stunden-Filter (IS-Ranking der Einstiegsstunde, gleiche Methode wie exclude_weekday)", t, "entry_hour", split_ts, full_index)

    # 10. Jump-activity ratio (bipower-variation jump share, prior day)
    jr = _prior_value(entry_dates, daily["jump_ratio"])
    t["jump_bucket"] = _tercile_bucket(pd.Series(jr), is_mask)
    test_bucket_filter("10. Jump-Activity-Ratio (Bipower-Variation-Sprunganteil des Vortages, asian_range_breakout-Baustein)", t, "jump_bucket", split_ts, full_index)

    # 11 & 12. VIX level & 5-day change (prior day)
    if vix_daily is not None:
        vix_lvl = _prior_value(entry_dates, vix_daily)
        t["vix_bucket"] = _tercile_bucket(pd.Series(vix_lvl), is_mask)
        test_bucket_filter("11. VIX-Level (Vortages-Schlusskurs, Tercile) - bei Gold verworfen, hier direkter relevant (VIX = SP500-Options-implizit)", t, "vix_bucket", split_ts, full_index)

        vix_chg = vix_daily.pct_change(5) * 100
        vix_chg_v = _prior_value(entry_dates, vix_chg)
        t["vix_chg_bucket"] = _tercile_bucket(pd.Series(vix_chg_v), is_mask)
        test_bucket_filter("12. VIX-5-Tage-Aenderungsrate (Vortages-Wert, Tercile)", t, "vix_chg_bucket", split_ts, full_index)

    # 13. US10Y yield 20-day change (prior day)
    if y10_daily is not None:
        y_chg = y10_daily.diff(20)
        y_chg_v = _prior_value(entry_dates, y_chg)
        t["y10_bucket"] = _tercile_bucket(pd.Series(y_chg_v), is_mask)
        test_bucket_filter("13. US-10J-Rendite 20-Tage-Aenderung (Vortages-Wert, Tercile)", t, "y10_bucket", split_ts, full_index)

    # 14. FOMC event-window blackout (+/-1 Tag, same-day dummy, no lag needed - fully known calendar)
    day_range = pd.date_range(pd.Timestamp(START).normalize(), pd.Timestamp(END).normalize(), freq="D")
    fomc_dummy = event_window_dummy("FOMC", day_range, window_days=1)
    entry_day = pd.Series(sig_time).dt.tz_localize(None).dt.normalize() if sig_time.tz is not None else pd.Series(sig_time).dt.normalize()
    is_blackout = fomc_dummy.reindex(entry_day).to_numpy()
    keep = pd.Series(np.where(np.isnan(is_blackout), np.nan, is_blackout == 0), index=t.index).fillna(True).astype(bool)
    test_direct_filter("14. FOMC-Event-Window-Blackout (+/-1 Tag um Fed-Sitzungen, Yildirim-Konvention)", t, keep, split_ts, full_index)


def main():
    print("Loading NASDAQ + SP500 M15 ...")
    nasdaq_raw = _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END))
    sp500_raw = _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END))

    nasdaq_base = build_frame(nasdaq_raw)
    sp500_base = build_frame(sp500_raw)

    nasdaq_daily = daily_series(nasdaq_base)
    sp500_daily = daily_series(sp500_base)

    print("Fetching VIX ...")
    try:
        vix_daily = fetch_vix_daily(START, END)
    except Exception as e:
        print(f"  VIX-Abruf fehlgeschlagen ({e}), VIX-Filter werden uebersprungen.")
        vix_daily = None

    print("Fetching US 10y yield (FRED DGS10) ...")
    try:
        y10_daily = fetch_yield("US")
        if y10_daily.index.tz is not None:
            y10_daily.index = y10_daily.index.tz_localize(None)
        y10_daily = y10_daily[(y10_daily.index >= START) & (y10_daily.index <= END)]
    except Exception as e:
        print(f"  FRED-Abruf fehlgeschlagen ({e}), Renditefilter wird uebersprungen.")
        y10_daily = None

    run_asset(
        "NASDAQ", nasdaq_base, nasdaq_daily,
        other_daily_close_sma=(sp500_daily["close"], sp500_daily["sma100"]),
        vix_daily=vix_daily, y10_daily=y10_daily,
    )
    run_asset(
        "SP500", sp500_base, sp500_daily,
        other_daily_close_sma=(nasdaq_daily["close"], nasdaq_daily["sma100"]),
        vix_daily=vix_daily, y10_daily=y10_daily,
    )


if __name__ == "__main__":
    main()
