"""Cross-Market-Check Teil 2 (chat 2026-08-21): S&P 500 und Bitcoin, gleiche
Disziplin wie scripts/research_gold_smc_g8_majors_crossmarket.py (finale,
gesperrte CTNL-Edge-Configs unveraendert, selber Zeitraum wie Gold
2024-08/2026-08, dann IS/OOS-Split).

SPX ueber dieselbe Dukascopy-Quelle wie Gold/FX (combined_strategy.data,
INSTRUMENTS["SP500"]). BTC ueber Binance-Klines (auction_playbook.data.
fetch_klines, wie beim btc_ema_cross-Bot) - andere Datenquelle, aber
dieselbe OHLC-Spaltenform, die Pipeline selbst ist instrumenten- UND
quellen-agnostisch (rein OHLC-basiert)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from auction_playbook.data import fetch_klines
from combined_strategy.data import fetch_timeframe
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)

REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)


def fetch_spx():
    h4 = fetch_timeframe("SP500", "H4", START, END)
    h1 = fetch_timeframe("SP500", "H1", START, END)
    m15 = fetch_timeframe("SP500", "M15", START, END)
    m5 = fetch_timeframe("SP500", "M5", START, END)
    for df in (h4, h1, m15, m5):
        df.columns = [c.lower() for c in df.columns]
        df.index = df.index.tz_convert("America/New_York")
    return h4, h1, m15, m5


def fetch_btc():
    h4 = fetch_klines("BTCUSDT", "4h", START, END)
    h1 = fetch_klines("BTCUSDT", "1h", START, END)
    m15 = fetch_klines("BTCUSDT", "15m", START, END)
    m5 = fetch_klines("BTCUSDT", "5m", START, END)
    for df in (h4, h1, m15, m5):
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York") if df.index.tz is None else df.index.tz_convert("America/New_York")
    return h4, h1, m15, m5


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:>6.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def bh_stats(price_df: pd.DataFrame, index: pd.DatetimeIndex) -> dict:
    df = price_df[(price_df.index >= index.min()) & (price_df.index <= index.max())]
    daily_close = df["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    if len(daily_ret):
        daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    return {"sharpe": annualized_sharpe(daily_ret), "cagr": cagr(daily_ret), "max_drawdown": max_drawdown(daily_ret)}


def run_market(name: str, h4, h1, m15, m5):
    print(f"\n{'='*100}\n{name}\n{'='*100}")
    print(f"  H4={len(h4)} H1={len(h1)} M15={len(m15)} M5={len(m5)}")

    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_PIPELINE_KWARGS)
    cont_trades = simulate_trades(cont_sig, CONT_BACKTEST_CFG)
    rev_sig = run_reversal(h4, h1, m15, **REV_PIPELINE_KWARGS)
    rev_trades = simulate_trades(rev_sig, REV_BACKTEST_CFG)

    cont_full = summarize(cont_trades, cont_sig.index)
    rev_full = summarize(rev_trades, rev_sig.index)
    bh_full = bh_stats(m15, m15.index)
    print(f"  VOLLPERIODE:      Cont {fmt(cont_full)}")
    print(f"                    Rev  {fmt(rev_full)}")
    print(f"                    B&H  Sharpe={bh_full['sharpe']:.2f} CAGR={bh_full['cagr']:+.1%} MaxDD={bh_full['max_drawdown']:.1%}")

    cont_is_sig, cont_oos_sig = cont_sig[cont_sig.index < SPLIT], cont_sig[cont_sig.index >= SPLIT]
    cont_is_t, cont_oos_t = cont_trades[cont_trades["entry_time"] < SPLIT], cont_trades[cont_trades["entry_time"] >= SPLIT]
    cont_is, cont_oos = summarize(cont_is_t, cont_is_sig.index), summarize(cont_oos_t, cont_oos_sig.index)

    rev_is_sig, rev_oos_sig = rev_sig[rev_sig.index < SPLIT], rev_sig[rev_sig.index >= SPLIT]
    rev_is_t, rev_oos_t = rev_trades[rev_trades["entry_time"] < SPLIT], rev_trades[rev_trades["entry_time"] >= SPLIT]
    rev_is, rev_oos = summarize(rev_is_t, rev_is_sig.index), summarize(rev_oos_t, rev_oos_sig.index)

    bh_is = bh_stats(m15, cont_is_sig.index)
    bh_oos = bh_stats(m15, cont_oos_sig.index)

    print(f"  IS (2024-08/2025-08):  Cont {fmt(cont_is)}")
    print(f"                         Rev  {fmt(rev_is)}")
    print(f"                         B&H  Sharpe={bh_is['sharpe']:.2f} CAGR={bh_is['cagr']:+.1%} MaxDD={bh_is['max_drawdown']:.1%}")
    print(f"  OOS (2025-08/2026-08): Cont {fmt(cont_oos)}")
    print(f"                         Rev  {fmt(rev_oos)}")
    print(f"                         B&H  Sharpe={bh_oos['sharpe']:.2f} CAGR={bh_oos['cagr']:+.1%} MaxDD={bh_oos['max_drawdown']:.1%}")

    return {
        "market": name, "cont_full_sharpe": cont_full["sharpe"], "cont_is_sharpe": cont_is["sharpe"], "cont_oos_sharpe": cont_oos["sharpe"],
        "rev_full_sharpe": rev_full["sharpe"], "rev_is_sharpe": rev_is["sharpe"], "rev_oos_sharpe": rev_oos["sharpe"],
        "bh_oos_sharpe": bh_oos["sharpe"],
    }


def main():
    print("Fetching SPX (Dukascopy) ...")
    spx_h4, spx_h1, spx_m15, spx_m5 = fetch_spx()
    print("Fetching BTC (Binance) ...")
    btc_h4, btc_h1, btc_m15, btc_m5 = fetch_btc()

    rows = [
        run_market("SPX (S&P 500)", spx_h4, spx_h1, spx_m15, spx_m5),
        run_market("BTC (BTCUSDT)", btc_h4, btc_h1, btc_m15, btc_m5),
    ]

    print(f"\n\n{'='*100}\nZUSAMMENFASSUNG (Sharpe)\n{'='*100}")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
