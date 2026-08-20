"""Cross-Market-Check (chat 2026-08-21): die finalen, gesperrten CTNL-Edge-
Configs (Continuation + Reversal-Kaskade) unveraendert auf die G8-Majors
angewendet (strategy/cls_advanced.py::PAIRS - EURUSD, GBPUSD, USDJPY,
USDCHF, AUDUSD, USDCAD, dieselbe Liste wie in den cls_practical-Skripten),
im selben Zeitraum wie Gold (2024-08-01 bis 2026-08-01).

Zweck: die Strategie-LOGIK (H4->H1->LTF-Kaskade, Fractal/BOS/Sweep-and-
Reject, ATR-basierte Stops/Ziele) ist rein OHLC-basiert und komplett
instrumenten-agnostisch - kein Code wird hier veraendert, nur die
Datenquelle. Testet die Hypothese aus der Regime-Untersuchung (knowledge/
projects/gold-ctnl-edge-portfolio.md) von der anderen Seite: wenn der Edge
NUR eine Gold-2024-26-spezifische Anomalie ist, sollte er auf FX-Majors
nicht auftauchen. Wenn er auch dort (zumindest teilweise) sichtbar ist,
spricht das fuer einen echten strukturellen Mechanismus statt eines reinen
Gold-Regime-Zufalls.

Ablauf pro Paar: 1) Kompletter Zeitraum (Vollperiode). 2) Standardprozess
IS/OOS-Split (IS 2024-08/2025-08, OOS 2025-08/2026-08), gegen Buy&Hold."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.cls_advanced import PAIRS
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)

REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)


def fetch_pair(key: str):
    h4 = fetch_timeframe(key, "H4", START, END)
    h1 = fetch_timeframe(key, "H1", START, END)
    m15 = fetch_timeframe(key, "M15", START, END)
    m5 = fetch_timeframe(key, "M5", START, END)
    for df in (h4, h1, m15, m5):
        df.columns = [c.lower() for c in df.columns]
        df.index = df.index.tz_convert("America/New_York")
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


def main():
    rows_full = []
    rows_is = []
    rows_oos = []

    for pair in PAIRS:
        print(f"\n{'='*100}\n{pair}\n{'='*100}")
        h4, h1, m15, m5 = fetch_pair(pair)
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
        rows_full.append({"pair": pair, "cont_sharpe": cont_full["sharpe"], "cont_n": cont_full["n_trades"], "rev_sharpe": rev_full["sharpe"], "rev_n": rev_full["n_trades"], "bh_sharpe": bh_full["sharpe"]})

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

        rows_is.append({"pair": pair, "cont_sharpe": cont_is["sharpe"], "cont_n": cont_is["n_trades"], "rev_sharpe": rev_is["sharpe"], "rev_n": rev_is["n_trades"], "bh_sharpe": bh_is["sharpe"]})
        rows_oos.append({"pair": pair, "cont_sharpe": cont_oos["sharpe"], "cont_n": cont_oos["n_trades"], "rev_sharpe": rev_oos["sharpe"], "rev_n": rev_oos["n_trades"], "bh_sharpe": bh_oos["sharpe"]})

    print(f"\n\n{'='*100}\nZUSAMMENFASSUNG - VOLLPERIODE (Sharpe)\n{'='*100}")
    print(pd.DataFrame(rows_full).to_string(index=False))
    print(f"\n{'='*100}\nZUSAMMENFASSUNG - IS (Sharpe)\n{'='*100}")
    print(pd.DataFrame(rows_is).to_string(index=False))
    print(f"\n{'='*100}\nZUSAMMENFASSUNG - OOS (Sharpe)\n{'='*100}")
    print(pd.DataFrame(rows_oos).to_string(index=False))


if __name__ == "__main__":
    main()
