"""Regime-shifted re-validation of the MT5 Trend+Pullback bot replication, at
the user's explicit request: the full-history (2016-2026) backtest treats
2016-2022 and 2023-2026 as one homogeneous sample, but the user's thesis is
that the market regime genuinely changed around 2023 (rate-hike cycle
peaking/pricing-in, 2024 US election and its follow-on policy/news-pricing
effects) - so testing the strategy across THAT regime break, rather than
within the post-break regime alone, may be understating what's achievable
going forward. This script does NOT resolve whether that thesis is correct
(that's a macro judgment call, out of scope for a backtest) - it re-runs the
exact same IS-sweep/OOS-validate discipline used throughout this series, but
confined entirely to 2023-01-01 -> 2026-08-01 (the previous "OOS" window),
split into a NEW IS (first ~18 months) and NEW OOS (remaining ~25 months).

Important, disclosed limitation: ~18 months of IS pooled across 5 markets
gives roughly 50-90 trades total depending on filter selectivity - far
thinner than the 180-300 pooled IS trades the original 2016-2022 sweeps had.
Every "chosen on IS" result below is correspondingly MORE exposed to noise/
overfitting than the earlier full-history passes - flagged inline, not
hidden.

Five passes, in order:
  1. Timeframe comparison - bot's own default config (EMA150/RSI14x35/
     ATR14x2.0/RR2.0, no filter) tested at each market's current live
     timeframe plus two alternates, on the new IS/OOS split.
  2. Filter re-sweep on the new IS (default timeframe): ADX floor (as
     before), a new ATR-rolling-quantile volatility floor, and a new
     session-hours (UTC) liquidity window - each swept independently,
     validated untouched on new OOS.
  3. TP/SL re-sweep on the new IS, with the best single filter from pass 2
     held fixed, validated untouched on new OOS.
  4. Breakeven-trigger sweep on top of pass 3's chosen TP/SL, same discipline.
  5. Dumps a consolidated CSV (results/mt5_trend_pullback_regime_shift.csv)
     used to build the final master table/artifact - one row per (market,
     config) at the DEFAULT timeframe, at the winning final configuration,
     for the new OOS window.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

DATA_START = "2016-01-01"  # keep full history for indicator warmup (EMA150 etc.) - only trade dates are restricted below
DATA_END = "2026-08-01"
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")   # ~18 months of new IS
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")  # dataset end -> ~25 months of new OOS

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]
TF_ALTERNATES = {
    "GOLD": ["H1", "H4", "D1"], "SILVER": ["H1", "H4", "D1"], "PLATINUM": ["H1", "H4", "D1"],
    "CHFJPY": ["H1", "H4", "D1"], "USDJPY": ["H1", "H4", "D1"],
}

ADX_MIN_CANDIDATES = [None, 15, 20, 25, 30, 35]
VOL_WINDOW_DAYS_CANDIDATES = [20, 40, 80]
VOL_QUANTILE_CANDIDATES = [0.25, 0.4]
SESSION_CANDIDATES = [None, (7, 17), (12, 20), (13, 22), (0, 7)]
STOP_ATR_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_R_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
BE_TRIGGER_CANDIDATES = [None, 0.5, 1.0, 1.5]
MIN_IS_TRADES = 15  # deliberately low - see module docstring on new-IS sample size

TF_BARS_PER_DAY = {"H1": 24, "H4": 6, "D1": 1}


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def combined(trades_by_market: dict, index_by_market: dict) -> dict:
    combined_trades = pd.concat(trades_by_market.values(), ignore_index=True) if trades_by_market else pd.DataFrame()
    starts = [idx.min() for idx in index_by_market.values() if len(idx)]
    ends = [idx.max() for idx in index_by_market.values() if len(idx)]
    if not starts:
        return summarize(combined_trades, pd.DatetimeIndex([]))
    full_index = pd.date_range(min(starts), max(ends), freq="D")
    return summarize(combined_trades, full_index)


def load(key: str, tf: str) -> pd.DataFrame:
    df = fetch_timeframe(key, tf, DATA_START, DATA_END)
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def slice_trades(trades: pd.DataFrame, start, end) -> pd.DataFrame:
    t = trades
    if start is not None:
        t = t[t["entry_time"] >= start]
    if end is not None:
        t = t[t["entry_time"] < end]
    return t


def slice_index(idx: pd.DatetimeIndex, start, end) -> pd.DatetimeIndex:
    if start is not None:
        idx = idx[idx >= start]
    if end is not None:
        idx = idx[idx < end]
    return idx


def main():
    print("=" * 100)
    print(f"REGIME-SHIFTED RE-VALIDATION -- new IS {NEW_IS_START.date()} -> {NEW_SPLIT.date()} "
          f"({(NEW_SPLIT - NEW_IS_START).days} days), new OOS {NEW_SPLIT.date()} -> {NEW_OOS_END.date()} "
          f"({(NEW_OOS_END - NEW_SPLIT).days} days)")
    print("=" * 100)

    default_data = {}
    for key, tf, label, spread_bps in MARKETS:
        default_data[label] = (load(key, tf), spread_bps, tf)

    # ------------------------------------------------------------ 1. Timeframe comparison
    print("\n" + "=" * 100)
    print("1. TIMEFRAME COMPARISON (bot default config, no filter: EMA150/RSI14x35/ATR14x2.0/RR2.0)")
    print("=" * 100)
    tf_rows = []
    for key, default_tf, label, spread_bps in MARKETS:
        for tf in TF_ALTERNATES[key]:
            df = load(key, tf)
            signaled = run_pipeline(df)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
            trades = simulate_trades(signaled, cfg)
            is_t = slice_trades(trades, NEW_IS_START, NEW_SPLIT)
            is_idx = slice_index(signaled.index, NEW_IS_START, NEW_SPLIT)
            oos_t = slice_trades(trades, NEW_SPLIT, NEW_OOS_END)
            oos_idx = slice_index(signaled.index, NEW_SPLIT, NEW_OOS_END)
            s_is, s_oos = summarize(is_t, is_idx), summarize(oos_t, oos_idx)
            marker = " <- LIVE" if tf == default_tf else ""
            print(f"  {label:<8} {tf:<3}{marker:<8} IS: {fmt(s_is):<70} OOS: {fmt(s_oos)}")
            tf_rows.append({"market": label, "tf": tf, "is_live_tf": tf == default_tf, "spread_bps": spread_bps,
                             "is": s_is, "oos": s_oos})

    # ------------------------------------------------------------ 2. Filter re-sweep (default TF, new IS)
    print("\n" + "=" * 100)
    print("2. FILTER RE-SWEEP on NEW IS (default timeframe per market, pooled across 5 markets)")
    print(f"   NOTE: pooled new-IS trade counts are much smaller than the original 2016-2022 sweep - treat")
    print(f"   selections here as considerably more overfitting-prone.")
    print("=" * 100)

    signaled_default = {label: (run_pipeline(df), spread_bps) for label, (df, spread_bps, tf) in default_data.items()}

    def is_result(pipeline_kwargs: dict) -> dict:
        trades_bm, idx_bm = {}, {}
        for label, (df, spread_bps, tf) in default_data.items():
            signaled = run_pipeline(df, **pipeline_kwargs)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
            trades = simulate_trades(signaled, cfg)
            trades_bm[label] = slice_trades(trades, NEW_IS_START, NEW_SPLIT)
            idx_bm[label] = slice_index(signaled.index, NEW_IS_START, NEW_SPLIT)
        return combined(trades_bm, idx_bm)

    def oos_result(pipeline_kwargs: dict) -> tuple[dict, dict, dict]:
        trades_bm, idx_bm = {}, {}
        for label, (df, spread_bps, tf) in default_data.items():
            signaled = run_pipeline(df, **pipeline_kwargs)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
            trades = simulate_trades(signaled, cfg)
            trades_bm[label] = slice_trades(trades, NEW_SPLIT, NEW_OOS_END)
            idx_bm[label] = slice_index(signaled.index, NEW_SPLIT, NEW_OOS_END)
        return combined(trades_bm, idx_bm), trades_bm, idx_bm

    s_base_is = is_result({})
    s_base_oos, _, _ = oos_result({})
    print(f"\n  BASELINE (no filter)   IS: {fmt(s_base_is)}")
    print(f"  BASELINE (no filter)  OOS: {fmt(s_base_oos)}")

    print("\n  -- ADX floor --")
    adx_rows = []
    for adx_min in ADX_MIN_CANDIDATES:
        s = is_result({"adx_min": adx_min})
        adx_rows.append({"adx_min": adx_min, **s})
        print(f"    adx_min={str(adx_min):>4}  {fmt(s)}")
    adx_df = pd.DataFrame(adx_rows)
    adx_elig = adx_df[adx_df["n_trades"] >= MIN_IS_TRADES]
    best_adx = adx_elig.loc[adx_elig["sharpe"].idxmax()] if not adx_elig.empty else None
    chosen_adx = None if best_adx is None or pd.isna(best_adx["adx_min"]) else float(best_adx["adx_min"])
    print(f"    -> chosen: adx_min={chosen_adx}")

    print("\n  -- Volatility floor (ATR >= trailing rolling quantile) --")
    vol_rows = []
    for wd in VOL_WINDOW_DAYS_CANDIDATES:
        for q in VOL_QUANTILE_CANDIDATES:
            # window in bars varies per market's own default timeframe
            results_per_market = {}
            trades_bm, idx_bm = {}, {}
            for label, (df, spread_bps, tf) in default_data.items():
                window_bars = wd * TF_BARS_PER_DAY[tf]
                signaled = run_pipeline(df, vol_window=window_bars, vol_quantile=q)
                cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
                trades = simulate_trades(signaled, cfg)
                trades_bm[label] = slice_trades(trades, NEW_IS_START, NEW_SPLIT)
                idx_bm[label] = slice_index(signaled.index, NEW_IS_START, NEW_SPLIT)
            s = combined(trades_bm, idx_bm)
            vol_rows.append({"window_days": wd, "quantile": q, **s})
            print(f"    window={wd:>3}d quantile={q}  {fmt(s)}")
    vol_df = pd.DataFrame(vol_rows)
    vol_elig = vol_df[vol_df["n_trades"] >= MIN_IS_TRADES]
    best_vol = vol_elig.loc[vol_elig["sharpe"].idxmax()] if not vol_elig.empty else None
    chosen_vol = (int(best_vol["window_days"]), float(best_vol["quantile"])) if best_vol is not None else None
    print(f"    -> chosen: window_days={chosen_vol[0] if chosen_vol else None}, quantile={chosen_vol[1] if chosen_vol else None}")

    print("\n  -- Session-hours filter (UTC) --")
    session_rows = []
    for sh in SESSION_CANDIDATES:
        s = is_result({"session_hours": sh})
        session_rows.append({"session_hours": str(sh), **s})
        print(f"    session={str(sh):>10}  {fmt(s)}")
    session_df = pd.DataFrame(session_rows)
    session_elig = session_df[session_df["n_trades"] >= MIN_IS_TRADES]
    best_session = session_elig.loc[session_elig["sharpe"].idxmax()] if not session_elig.empty else None
    chosen_session = None if best_session is None or best_session["session_hours"] == "None" else eval(best_session["session_hours"])
    print(f"    -> chosen: session_hours={chosen_session}")

    # pick the single best filter family overall (by IS sharpe) as "the" filter going forward
    candidates = [("none", {}, s_base_is)]
    if chosen_adx is not None:
        candidates.append(("adx", {"adx_min": chosen_adx}, is_result({"adx_min": chosen_adx})))
    if chosen_vol is not None:
        wd, q = chosen_vol
        kw = {}
        # vol_window is per-market (bars depend on TF) -- store as (days, quantile), resolved per-market when applying
        vol_kwargs_by_market = {label: {"vol_window": wd * TF_BARS_PER_DAY[tf], "vol_quantile": q} for label, (df, sb, tf) in default_data.items()}
        trades_bm, idx_bm = {}, {}
        for label, (df, spread_bps, tf) in default_data.items():
            signaled = run_pipeline(df, **vol_kwargs_by_market[label])
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
            trades = simulate_trades(signaled, cfg)
            trades_bm[label] = slice_trades(trades, NEW_IS_START, NEW_SPLIT)
            idx_bm[label] = slice_index(signaled.index, NEW_IS_START, NEW_SPLIT)
        candidates.append(("vol", vol_kwargs_by_market, combined(trades_bm, idx_bm)))
    if chosen_session is not None:
        candidates.append(("session", {"session_hours": chosen_session}, is_result({"session_hours": chosen_session})))

    best_name, best_kwargs, best_s = max(
        (c for c in candidates if c[2]["n_trades"] >= MIN_IS_TRADES), key=lambda c: c[2]["sharpe"], default=candidates[0]
    )
    print(f"\n  === Overall best filter family on new IS: '{best_name}' -- {fmt(best_s)} ===")

    print("\n  OOS validation of each filter family (untouched):")
    for name, kwargs, _ in candidates:
        if name == "vol":
            trades_bm, idx_bm = {}, {}
            for label, (df, spread_bps, tf) in default_data.items():
                signaled = run_pipeline(df, **kwargs[label])
                cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
                trades = simulate_trades(signaled, cfg)
                trades_bm[label] = slice_trades(trades, NEW_SPLIT, NEW_OOS_END)
                idx_bm[label] = slice_index(signaled.index, NEW_SPLIT, NEW_OOS_END)
            s_oos = combined(trades_bm, idx_bm)
        else:
            s_oos, _, _ = oos_result(kwargs)
        print(f"    {name:<8} {fmt(s_oos)}")

    # ------------------------------------------------------------ 3. TP/SL re-sweep with best filter
    print("\n" + "=" * 100)
    print(f"3. TP/SL RE-SWEEP on NEW IS, filter='{best_name}' held fixed")
    print("=" * 100)

    def signaled_with_best_filter(label, df, spread_bps, tf):
        if best_name == "none":
            return run_pipeline(df)
        if best_name == "adx":
            return run_pipeline(df, adx_min=best_kwargs["adx_min"])
        if best_name == "vol":
            return run_pipeline(df, **best_kwargs[label])
        if best_name == "session":
            return run_pipeline(df, session_hours=best_kwargs["session_hours"])
        raise ValueError(best_name)

    signaled_bf = {label: (signaled_with_best_filter(label, df, spread_bps, tf), spread_bps) for label, (df, spread_bps, tf) in default_data.items()}

    def bt_period(cfg_kwargs: dict, start, end):
        trades_bm, idx_bm = {}, {}
        for label, (signaled, spread_bps) in signaled_bf.items():
            cfg = BacktestConfig(spread_bps=spread_bps, **cfg_kwargs)
            trades = simulate_trades(signaled, cfg)
            trades_bm[label] = slice_trades(trades, start, end)
            idx_bm[label] = slice_index(signaled.index, start, end)
        return combined(trades_bm, idx_bm), trades_bm, idx_bm

    s_tpsl_base_is, _, _ = bt_period({"stop_atr_mult": 2.0, "use_vwap_target": False, "take_profit_r": 2.0}, NEW_IS_START, NEW_SPLIT)
    s_tpsl_base_oos, _, _ = bt_period({"stop_atr_mult": 2.0, "use_vwap_target": False, "take_profit_r": 2.0}, NEW_SPLIT, NEW_OOS_END)
    print(f"  Default TP/SL (2.0/2.0)   IS: {fmt(s_tpsl_base_is)}")
    print(f"  Default TP/SL (2.0/2.0)  OOS: {fmt(s_tpsl_base_oos)}")

    tpsl_rows = []
    for stop_atr in STOP_ATR_CANDIDATES:
        for tp_r in TP_R_CANDIDATES:
            s, _, _ = bt_period({"stop_atr_mult": stop_atr, "use_vwap_target": False, "take_profit_r": tp_r}, NEW_IS_START, NEW_SPLIT)
            tpsl_rows.append({"stop_atr": stop_atr, "tp_r": tp_r, **s})
    tpsl_df = pd.DataFrame(tpsl_rows)
    tpsl_elig = tpsl_df[tpsl_df["n_trades"] >= MIN_IS_TRADES]
    best_tpsl = tpsl_elig.loc[tpsl_elig["sharpe"].idxmax()]
    chosen_stop, chosen_tp = float(best_tpsl["stop_atr"]), float(best_tpsl["tp_r"])
    print(f"  -> chosen (best IS Sharpe, n>={MIN_IS_TRADES}): stop_atr={chosen_stop}, tp_r={chosen_tp} -- {fmt(best_tpsl.to_dict())}")

    s_tpsl_chosen_oos, tpsl_oos_tbm, tpsl_oos_idx = bt_period({"stop_atr_mult": chosen_stop, "use_vwap_target": False, "take_profit_r": chosen_tp}, NEW_SPLIT, NEW_OOS_END)
    print(f"  Chosen TP/SL OOS: {fmt(s_tpsl_chosen_oos)}")
    print(f"  Default TP/SL OOS (for comparison): {fmt(s_tpsl_base_oos)}")

    # ------------------------------------------------------------ 4. Breakeven sweep
    print("\n" + "=" * 100)
    print(f"4. BREAKEVEN-TRIGGER SWEEP on top of stop={chosen_stop}/tp={chosen_tp}, filter='{best_name}' -- NEW IS")
    print("=" * 100)
    be_rows = []
    for be in BE_TRIGGER_CANDIDATES:
        s, _, _ = bt_period({"stop_atr_mult": chosen_stop, "use_vwap_target": False, "take_profit_r": chosen_tp, "breakeven_trigger_r": be}, NEW_IS_START, NEW_SPLIT)
        be_rows.append({"be": be, **s})
        print(f"    be_trigger={str(be):>4}  {fmt(s)}")
    be_df = pd.DataFrame(be_rows)
    be_elig = be_df[be_df["n_trades"] >= MIN_IS_TRADES]
    best_be = be_elig.loc[be_elig["sharpe"].idxmax()]
    chosen_be = None if pd.isna(best_be["be"]) else float(best_be["be"])
    print(f"  -> chosen BE trigger: {chosen_be}")

    final_kwargs = {"stop_atr_mult": chosen_stop, "use_vwap_target": False, "take_profit_r": chosen_tp, "breakeven_trigger_r": chosen_be}
    s_final_oos, final_oos_tbm, final_oos_idx = bt_period(final_kwargs, NEW_SPLIT, NEW_OOS_END)
    s_final_full, final_full_tbm, final_full_idx = bt_period(final_kwargs, None, None)
    print(f"  FINAL config OOS: {fmt(s_final_oos)}")

    # ------------------------------------------------------------ 5. Dump per-market CSV for final config
    print("\n" + "=" * 100)
    print("5. PER-MARKET RESULTS, FINAL CHOSEN CONFIG, NEW OOS (2024-07 -> 2026-08) -- writing CSV")
    print("=" * 100)
    out_rows = []
    for label, (df, spread_bps, tf) in default_data.items():
        t = final_oos_tbm[label]
        idx = final_oos_idx[label]
        s = summarize(t, idx)
        print(f"  {label:<8} {fmt(s)}")
        out_rows.append({
            "market": label, "timeframe": tf, "spread_bps": spread_bps,
            "filter": best_name, "adx_min": chosen_adx if best_name == "adx" else None,
            "vol_window_days": chosen_vol[0] if (best_name == "vol" and chosen_vol) else None,
            "vol_quantile": chosen_vol[1] if (best_name == "vol" and chosen_vol) else None,
            "session_hours": str(chosen_session) if best_name == "session" else None,
            "stop_atr_mult": chosen_stop, "tp_r": chosen_tp, "be_trigger_r": chosen_be,
            "n_trades_oos": s["n_trades"], "win_rate_oos": s["win_rate"], "profit_factor_oos": s["profit_factor"],
            "sharpe_oos": s["sharpe"], "calmar_oos": s["calmar"], "cagr_oos": s["cagr"], "max_drawdown_oos": s["max_drawdown"],
        })

    out_dir = Path(__file__).resolve().parents[1] / "mt5_trend_pullback" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "regime_shift_final_config.csv"
    pd.DataFrame(out_rows).to_csv(out_path, index=False)
    print(f"\nWrote {out_path}")

    tf_out_path = out_dir / "regime_shift_timeframe_comparison.csv"
    tf_flat = []
    for r in tf_rows:
        tf_flat.append({
            "market": r["market"], "tf": r["tf"], "is_live_tf": r["is_live_tf"], "spread_bps": r["spread_bps"],
            "n_is": r["is"]["n_trades"], "wr_is": r["is"]["win_rate"], "pf_is": r["is"]["profit_factor"], "sharpe_is": r["is"]["sharpe"],
            "n_oos": r["oos"]["n_trades"], "wr_oos": r["oos"]["win_rate"], "pf_oos": r["oos"]["profit_factor"], "sharpe_oos": r["oos"]["sharpe"],
            "cagr_oos": r["oos"]["cagr"], "maxdd_oos": r["oos"]["max_drawdown"],
        })
    pd.DataFrame(tf_flat).to_csv(tf_out_path, index=False)
    print(f"Wrote {tf_out_path}")


if __name__ == "__main__":
    main()
