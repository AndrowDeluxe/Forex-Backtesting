"""Dollar-account backtest of the MT5 Trend+Pullback bot replication, at the
user's requested parameters: $100,000 starting equity, 1% risk per trade,
otherwise the live bot's own portfolio rules (config.py: max 3 concurrent
positions across all 5 markets, max 1 position per market at a time).

Two variants, each over the full period and OOS-only (2023-2026 - the only
period with a real edge per the earlier research passes):
  A. Baseline - the bot exactly as configured today, no regime filter.
  B. ADX>=25 filter - the regime filter from
     scripts/research_mt5_trend_pullback_adx_filter.py (chosen on IS only,
     applied untouched here), NOT currently in the live bot.

See mt5_trend_pullback/account_simulation.py's docstring for the sizing
methodology and its disclosed simplifications (balance-based, not
mark-to-market, sizing; continuous lot sizing vs the bot's round-down).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.account_simulation import account_stats, simulate_account
from mt5_trend_pullback.pipeline import (
    ATR_LEN, ATR_STOP_MULT, RR_RATIO, RSI_LEN, RSI_OVERSOLD, TREND_LEN, run_pipeline,
)
from strategy.backtest import BacktestConfig, simulate_trades

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
CHOSEN_ADX_MIN = 25.0

STARTING_EQUITY = 100_000.0
RISK_PCT = 0.01
MAX_CONCURRENT = 3

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]


def print_params():
    print("=" * 78)
    print("BACKTEST-PARAMETER")
    print("=" * 78)
    print(f"  Startkapital:              {STARTING_EQUITY:,.0f} USD")
    print(f"  Risiko pro Trade:          {RISK_PCT:.1%} des aktuellen Kontostands (fixed-fractional, compounding)")
    print(f"  Max. gleichzeitige Trades: {MAX_CONCURRENT} (ueber alle Maerkte)")
    print(f"  Max. Position pro Markt:   1")
    print(f"  Zeitraum:                  {START} -> {END}")
    print(f"  IS/OOS-Split:              {SPLIT.date()}  (IS = 2016-2022, OOS = 2023-2026)")
    print(f"  Maerkte/Timeframes:        {', '.join(f'{label} {tf}' for _, tf, label, _ in MARKETS)}")
    print(f"  Strategie:                 EMA{TREND_LEN} Trendfilter, RSI{RSI_LEN} Pullback-Kreuzung > {RSI_OVERSOLD:.0f},")
    print(f"                             ATR{ATR_LEN} x {ATR_STOP_MULT:.1f} Stop, RR {RR_RATIO:.1f}, long-only, 1 Position/Markt")
    print(f"  Spread-Annahme (Round-Trip): " + ", ".join(f"{label}={s:.1f}bp" for _, _, label, s in MARKETS))
    print(f"  ADX-Filter (Variante B):   ADX({ATR_LEN}) >= {CHOSEN_ADX_MIN:.0f} (gewaehlt auf IS 2016-2022, unveraendert auf OOS angewendet)")
    print(f"  Nicht modelliert:          Swap/Overnight-Gebuehren, Slippage, Broker-Lot-Rundung (Bot rundet ab -> reales")
    print(f"                             Risiko tendenziell <= 1%, nie mehr), Mark-to-Market waehrend offener Trades")
    print(f"                             (Sizing nutzt realisiertes Konto-Equity, nicht laufenden Buchgewinn/-verlust)")


def fmt_usd(x: float) -> str:
    return f"{x:>12,.0f} USD"


def fmt_stats(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4} (uebersprungen wg. Positionslimit: {s['n_skipped']:>4})  "
        f"WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Endkapital={fmt_usd(s['final_equity'])}  Gesamt-Return={s['total_return']:+.1%}  "
        f"MaxDD={s['max_drawdown_pct']:+.1%} ({fmt_usd(s['max_drawdown_usd'])})  "
        f"Oe.Gewinn={fmt_usd(s['avg_win_usd']) if pd.notna(s['avg_win_usd']) else 'n/a':>16}  "
        f"Oe.Verlust={fmt_usd(s['avg_loss_usd']) if pd.notna(s['avg_loss_usd']) else 'n/a':>16}"
    )


def build_trades(data: dict, adx_min: float | None) -> dict[str, pd.DataFrame]:
    out = {}
    for label, df in data.items():
        spread_bps = next(s for k, tf, lab, s in MARKETS if lab == label)
        signaled = run_pipeline(df, adx_min=adx_min)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        out[label] = simulate_trades(signaled, cfg)
    return out


def slice_period(trades_by_market: dict[str, pd.DataFrame], start: pd.Timestamp | None, end: pd.Timestamp | None) -> dict[str, pd.DataFrame]:
    out = {}
    for label, df in trades_by_market.items():
        d = df
        if start is not None:
            d = d[d["entry_time"] >= start]
        if end is not None:
            d = d[d["entry_time"] < end]
        out[label] = d
    return out


def main():
    print_params()

    print("\nLoading 5 markets (cached from prior runs where available) ...")
    data = {}
    for key, tf, label, _spread in MARKETS:
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        data[label] = df
        print(f"  {label}: {len(df)} bars")

    for variant_name, adx_min in [("A. BASELINE (kein Filter, Bot wie er ist)", None), ("B. MIT ADX>=25-FILTER", CHOSEN_ADX_MIN)]:
        print("\n" + "=" * 78)
        print(variant_name)
        print("=" * 78)
        trades_by_market = build_trades(data, adx_min)

        full = trades_by_market
        is_ = slice_period(trades_by_market, None, SPLIT)
        oos = slice_period(trades_by_market, SPLIT, None)

        for period_name, period_trades in [("Full (2016-2026)", full), ("IS (2016-2022)", is_), ("OOS (2023-2026)", oos)]:
            sim = simulate_account(period_trades, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)
            s = account_stats(sim, starting_equity=STARTING_EQUITY)
            print(f"  {period_name:<20} {fmt_stats(s)}")

        print("\n  Pro Markt (Full, dieselbe Variante, ISOLIERT simuliert -- d.h. OHNE die 3-Positionen-Konkurrenz")
        print("  der anderen 4 Maerkte, nur zur Einordnung wie viele Trades je Markt anfallen wuerden):")
        for label, df in trades_by_market.items():
            sim = simulate_account({label: df}, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)
            s = account_stats(sim, starting_equity=STARTING_EQUITY)
            print(f"    {label:<8} {fmt_stats(s)}")


if __name__ == "__main__":
    main()
