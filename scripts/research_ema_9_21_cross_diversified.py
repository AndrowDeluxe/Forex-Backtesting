"""Diversification step 1 (per the sheet's own caveat 1: "test YOUR asset on
YOUR timeframe, never borrow a backtest from a different market" - the sheet
itself shows EMA9/21 beating BTC buy-and-hold but LOSING to buy-and-hold on
Nasdaq). Before combining BTC with Gold/FX/S&P into one portfolio, this
tests the EXACT SAME EMA9/21 long/flat rule, unmodified, independently on
each of Gold (XAUUSD), EURUSD and S&P 500 - real Dukascopy daily data
already used elsewhere in this repo (`combined_strategy.data`).

Same risk-sizing contract as scripts/research_ema_9_21_cross_btc.py
(simulate_risk_sized): 1% risk of current equity per trade against an
ATR(14)*2.0 stop, no leverage, fill at next bar's open, EMA/ATR computed on
the FULL series with sim_from marking the IS/OOS boundary (fixes the same
cold-start warmup bug documented in the BTC script).

Cost assumption differs from crypto: 5bps round-trip-style cost (0.05% per
side), matching this repo's own established convention for Gold/FX CFDs
(scripts/research_gold_pullback_ma_strategy.py: COST_BPS=5.0) - about half
the 0.1%/side used for BTC, reflecting tighter typical spreads on these
instruments. Dukascopy data here is BID-side only (no ask/spread series
available), so this bps charge is the entire disclosed transaction-cost
model - no separate spread simulation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from strategy.indicators import compute_atr

INSTRUMENTS = ["GOLD", "EURUSD", "SP500"]
START, END = "2010-01-01", "2026-08-13"
COMMISSION = 0.0005  # 5bps per side, see module docstring
ATR_PERIOD = 14
ATR_STOP_MULT = 2.0
STARTING_CAPITAL = 100_000.0
RISK_PCT = 0.01
IS_FRACTION = 0.7


def load(key: str) -> pd.DataFrame:
    df = fetch_timeframe(key, "D1", START, END)
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})[
        ["open", "high", "low", "close"]
    ].dropna()


def simulate_risk_sized(df: pd.DataFrame, capital: float, risk_pct: float,
                         sim_from: pd.Timestamp | None = None) -> dict:
    """Same contract as research_ema_9_21_cross_btc.py's simulate_risk_sized
    (fast=9/slow=21 EMA long/flat, ATR stop, no leverage, sim_from warmup
    handling) - reimplemented standalone here so this script has no import
    dependency on the BTC-specific COMMISSION global."""
    close, open_, low = df["close"], df["open"], df["low"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    above_prev = above.shift(1, fill_value=False)

    go_long = (above & ~above_prev).to_numpy()

    go_flat = (~above & above_prev).to_numpy()
    atr = compute_atr(df, ATR_PERIOD)

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    cash = capital
    qty = 0.0
    entry_price = None
    stop_price = None
    trade_risk_dollar = None
    in_pos = False
    capped_count = 0
    trades = []
    equity_curve = [capital]
    equity_dates = [df.index[start_i - 1]]

    for i in range(start_i, len(df)):
        exited_today = False
        if in_pos and go_flat[i - 1]:
            exit_fill = open_.iloc[i] * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True
        elif in_pos and low.iloc[i] <= stop_price:
            exit_fill = stop_price * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True

        if not in_pos and not exited_today and go_long[i - 1] and pd.notna(atr.iloc[i - 1]):
            raw_entry = open_.iloc[i]
            entry_fill = raw_entry * (1 + COMMISSION)
            stop_dist = ATR_STOP_MULT * atr.iloc[i - 1]
            if stop_dist > 0:
                target_qty = (cash * risk_pct) / stop_dist
                max_qty = cash / entry_fill
                if target_qty > max_qty:
                    target_qty = max_qty
                    capped_count += 1
                qty = target_qty
                entry_price = entry_fill
                stop_price = raw_entry - stop_dist
                trade_risk_dollar = qty * stop_dist
                cash -= qty * entry_fill
                in_pos = True

        equity_curve.append(cash + (qty * close.iloc[i] if in_pos else 0.0))
        equity_dates.append(df.index[i])

    equity = pd.Series(equity_curve, index=equity_dates)
    n_years = (equity_dates[-1] - equity_dates[0]).days / 365.25
    total_return = equity.iloc[-1] / capital - 1
    cagr = (equity.iloc[-1] / capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(trades) if trades else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")

    daily_ret = equity.pct_change().fillna(0.0)
    worst_day_pct = daily_ret.min() * 100

    return {
        "n_trades": len(trades), "win_rate": win_rate, "profit_factor": profit_factor,
        "total_return": total_return, "cagr": cagr, "max_dd": max_dd,
        "end_equity": equity.iloc[-1], "worst_day_pct": worst_day_pct, "n_capped": capped_count,
    }


def fmt(label: str, m: dict) -> str:
    calmar = m["cagr"] / abs(m["max_dd"]) if m["max_dd"] < 0 else float("nan")
    return (
        f"{label}: n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  "
        f"TotalReturn={m['total_return']:+.1%}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}  "
        f"Calmar={calmar:.2f}  WorstDay={m['worst_day_pct']:+.2f}%  SizeCapped={m['n_capped']}/{m['n_trades']}"
    )


def main():
    print("Testing the UNMODIFIED EMA9/21 long/flat rule on Gold/EURUSD/S&P500 individually.")
    print(f"Cost: {COMMISSION:.2%}/side (5bps round-trip-style, matches research_gold_pullback_ma_strategy.py)")
    print(f"Risk: {RISK_PCT:.1%}/trade, ATR({ATR_PERIOD})x{ATR_STOP_MULT} stop, no leverage, ${STARTING_CAPITAL:,.0f} start\n")

    for key in INSTRUMENTS:
        df = load(key)
        print("=" * 78)
        print(f"{key}: {df.index[0].date()} -> {df.index[-1].date()} ({len(df)} bars)")
        print("=" * 78)

        bh_ret = df["close"].iloc[-1] / df["close"].iloc[0] - 1
        bh_dd = (df["close"] / df["close"].cummax() - 1).min()
        print(f"  Buy & Hold: TotalReturn={bh_ret:+.1%}  MaxDD={bh_dd:.1%}")

        split_i = int(len(df) * IS_FRACTION)
        oos_split = df.index[split_i]
        windows = [("Full", df, None), ("IS", df.iloc[:split_i], None), ("OOS", df, oos_split)]
        for label, part, sim_from in windows:
            m = simulate_risk_sized(part, STARTING_CAPITAL, RISK_PCT, sim_from=sim_from)
            print("  " + fmt(label, m))
        print()

    print(
        "Reminder: this is the SAME rule set that worked on BTC, run unmodified - not re-tuned per\n"
        "instrument. A weak/negative result here does not mean Gold/EURUSD/S&P can't be traded, only\n"
        "that THIS specific rule set doesn't transfer - matches the sheet's own caveat 1."
    )


if __name__ == "__main__":
    main()
