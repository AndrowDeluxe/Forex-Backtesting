"""Multi-asset extension of research_ema_9_21_cross_btc.py: the same EMA9/21
long/flat crossover run independently on BTCUSDT, ETHUSDT and SOLUSDT, sized
by fixed-fractional risk against an ATR stop, sharing one account with an
optional aggregate open-risk cap (`max_total_risk_pct`) - same mechanism as
gold_bitcoin_dual_momentum/risk_engine.py and the lesson documented in
app_pages/risk_management.py: for a MULTI-position book, the aggregate risk
cap (not the per-trade risk_pct) is usually what controls drawdown.

Motivation (from the single-asset script's funded-challenge check): BTC
alone trades ~1x/month, so a single-instrument account spends most of its
time in cash. Diversifying across a few liquid, largely-uncorrelated-in-
timing crypto pairs raises trade frequency and should smooth the equity
curve, without changing the underlying signal logic at all.

Explicitly disclosed limitations:
  - SOLUSDT only starts 2020-08-11 on Binance - the "full history" run here
    is bounded by SOL's listing, not BTC's 2017-08-17 (shorter than the
    single-asset script's full-history window).
  - Entries are processed in a fixed order (BTC, ETH, SOL) each day: if the
    aggregate cap would be breached by more than one same-day signal, later
    assets in that order are skipped, not proportionally scaled down.
  - Correlation is not measured or filtered - BTC/ETH/SOL trend fairly
    together, so "diversification" here is really "more, not less
    correlated, positions" that raises trade COUNT more than it truly
    diversifies risk. Flagged explicitly in the results, not just assumed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from auction_playbook.data import fetch_klines
from strategy.indicators import compute_atr

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
FULL_START = "2017-08-17"
END = "2026-08-13"
OOS_START = "2023-12-02"  # matches the single-asset script's IS/OOS split date
COMMISSION = 0.001
ATR_PERIOD = 14
ATR_STOP_MULT = 2.0
STARTING_CAPITAL = 100_000.0
RISK_PCT = 0.01


def prep_asset(sym: str) -> dict:
    df = fetch_klines(sym, "1d", FULL_START, END)
    close = df["close"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    go_long = above & ~above.shift(1).fillna(False)
    go_flat = ~above & above.shift(1).fillna(False)
    atr = compute_atr(df, ATR_PERIOD)
    return {"df": df, "go_long": go_long, "go_flat": go_flat, "atr": atr}


def simulate_portfolio(prepped: dict, full_index: pd.DatetimeIndex, capital: float,
                        risk_pct: float, max_total_risk_pct: float | None,
                        sim_from: pd.Timestamp | None = None) -> dict:
    """`full_index` should be the entire common trading calendar (from the
    true common start of all assets in `prepped`) - the loop always walks it
    from the beginning so a windowed report (sim_from set) still carries
    correct warmup/position-state across the boundary, exactly like
    simulate_risk_sized's sim_from contract in the single-asset script.
    Equity/trades are only RECORDED (for the returned stats) once the date
    reaches sim_from; the day right before sim_from is not itself dropped -
    it's used as the last 'yesterday' lookup for the first recorded day."""
    cash = capital
    positions = {sym: None for sym in prepped}  # each: dict(qty, entry_price, raw_entry, stop_price, stop_dist, risk_dollar)
    trades = []  # dicts: asset, pnl, r, stopped_out
    skipped_by_cap = 0
    equity_curve = []
    equity_dates = []
    recording = sim_from is None

    for i in range(1, len(full_index)):
        today, yesterday = full_index[i], full_index[i - 1]
        if not recording and today >= sim_from:
            recording = True
            # Fresh $100k account at the window boundary (matches
            # simulate_risk_sized's sim_from contract: indicators keep full
            # warmup, but the account/position state resets here) - any
            # position open going into the boundary is discarded, not
            # carried in, so IS/OOS/Full stay independently comparable.
            cash, positions = capital, {sym: None for sym in prepped}
        exited_today = set()

        equity_open = cash + sum(
            pos["qty"] * prepped[sym]["df"]["close"].loc[yesterday]
            for sym, pos in positions.items() if pos is not None
        )

        for sym in prepped:
            pos = positions[sym]
            if pos is None:
                continue
            p = prepped[sym]
            o, l = p["df"]["open"].loc[today], p["df"]["low"].loc[today]
            if p["go_flat"].loc[yesterday]:
                exit_fill = o * (1 - COMMISSION)
                pnl = pos["qty"] * (exit_fill - pos["entry_price"])
                if recording:
                    trades.append({"asset": sym, "pnl": pnl, "r": pnl / pos["risk_dollar"], "stopped_out": False})
                cash += pos["qty"] * exit_fill
                positions[sym] = None
                exited_today.add(sym)
            elif l <= pos["stop_price"]:
                exit_fill = pos["stop_price"] * (1 - COMMISSION)
                pnl = pos["qty"] * (exit_fill - pos["entry_price"])
                if recording:
                    trades.append({"asset": sym, "pnl": pnl, "r": pnl / pos["risk_dollar"], "stopped_out": True})
                cash += pos["qty"] * exit_fill
                positions[sym] = None
                exited_today.add(sym)

        open_risk_dollar = sum(pos["risk_dollar"] for pos in positions.values() if pos is not None)

        for sym in prepped:
            if positions[sym] is not None or sym in exited_today:
                continue  # no same-day re-entry right after a stop-out/crossunder exit
            p = prepped[sym]
            if not p["go_long"].loc[yesterday] or pd.isna(p["atr"].loc[yesterday]):
                continue
            raw_entry = p["df"]["open"].loc[today]
            entry_fill = raw_entry * (1 + COMMISSION)
            stop_dist = ATR_STOP_MULT * p["atr"].loc[yesterday]
            if stop_dist <= 0:
                continue
            target_qty = (equity_open * risk_pct) / stop_dist
            max_qty = equity_open / entry_fill
            qty = min(target_qty, max_qty)
            candidate_risk = qty * stop_dist
            if max_total_risk_pct is not None and open_risk_dollar + candidate_risk > max_total_risk_pct * equity_open:
                skipped_by_cap += 1
                continue
            cash -= qty * entry_fill
            positions[sym] = {
                "qty": qty, "entry_price": entry_fill, "raw_entry": raw_entry,
                "stop_price": raw_entry - stop_dist, "stop_dist": stop_dist, "risk_dollar": candidate_risk,
            }
            open_risk_dollar += candidate_risk

        equity_close = cash + sum(
            pos["qty"] * prepped[sym]["df"]["close"].loc[today]
            for sym, pos in positions.items() if pos is not None
        )
        if recording:
            equity_curve.append(equity_close)
            equity_dates.append(today)

    equity = pd.Series(equity_curve, index=equity_dates)
    n_years = (equity_dates[-1] - equity_dates[0]).days / 365.25
    total_return = equity.iloc[-1] / capital - 1
    cagr = (equity.iloc[-1] / capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()
    daily_ret = equity.pct_change().fillna(0.0)
    worst_day_pct = daily_ret.min() * 100
    worst_day_date = daily_ret.idxmin()
    target_equity = capital * 1.10
    hit = equity[equity >= target_equity]
    days_to_10pct = (hit.index[0] - equity.index[0]).days if not hit.empty else None

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(trades) if trades else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")
    per_asset_n = {sym: sum(1 for t in trades if t["asset"] == sym) for sym in prepped}

    return {
        "n_trades": len(trades), "per_asset_n": per_asset_n, "win_rate": win_rate,
        "profit_factor": profit_factor, "total_return": total_return, "cagr": cagr,
        "max_dd": max_dd, "end_equity": equity.iloc[-1], "worst_day_pct": worst_day_pct,
        "worst_day_date": worst_day_date, "breached_3pct_daily_rule": worst_day_pct < -3.0,
        "days_to_10pct_target": days_to_10pct, "skipped_by_cap": skipped_by_cap,
    }


def fmt(label: str, m: dict) -> str:
    calmar = m["cagr"] / abs(m["max_dd"]) if m["max_dd"] < 0 else float("nan")
    days = m["days_to_10pct_target"] if m["days_to_10pct_target"] is not None else "not reached"
    per_asset = ", ".join(f"{s.replace('USDT','')}={n}" for s, n in m["per_asset_n"].items())
    return (
        f"{label}: n={m['n_trades']:>3} ({per_asset})  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}\n"
        f"    TotalReturn={m['total_return']:+.1%}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}  Calmar={calmar:.2f}\n"
        f"    WorstDay={m['worst_day_pct']:+.2f}% ({m['worst_day_date'].date()})  "
        f"DaysTo+10%={days}  EndEquity=${m['end_equity']:,.0f}  SkippedByCap={m['skipped_by_cap']}"
    )


def main():
    print("All backtest parameters:")
    print(f"  Assets                : {', '.join(ASSETS)}, 1D (Binance spot klines)")
    print(f"  Signal per asset      : EMA9 close-cross EMA21 (long above, flat below) - independent per asset")
    print(f"  Direction             : long/flat only")
    print(f"  Fill timing           : signal on bar close, filled at NEXT bar's open")
    print(f"  Commission            : {COMMISSION:.2%} per side (entry and exit)")
    print(f"  Slippage              : not modeled")
    print(f"  Starting capital      : ${STARTING_CAPITAL:,.0f} (shared cash pool across all 3 assets)")
    print(f"  Risk per trade        : {RISK_PCT:.1%} of current total equity, per asset independently")
    print(f"  Stop-loss             : entry - {ATR_STOP_MULT} x ATR({ATR_PERIOD}), per asset's own ATR")
    print(f"  Stop fill assumption  : exact stop price if that day's low touches it (no gap-through)")
    print(f"  Leverage              : none per position (notional <= equity at entry time)")
    print(f"  Aggregate risk cap    : tested both uncapped (up to 3% simultaneous) and 2.5% (matches")
    print(f"                          the precedent already running on the live bot's Konto 2)")
    print(f"  Entry order on ties   : fixed BTC -> ETH -> SOL; a later asset can be skipped by the")
    print(f"                          aggregate cap on a day when multiple assets signal at once")
    print(f"  Same-day re-entry     : blocked right after a stop-out/crossunder exit (same asset)")
    print(f"  Funding-rate cost     : NOT modeled (spot data only, no funding-rate source in this repo)")
    print()
    print(f"Fetching BTCUSDT/ETHUSDT/SOLUSDT daily {FULL_START} -> {END} ...")
    prepped = {sym: prep_asset(sym) for sym in ASSETS}
    for sym in ASSETS:
        idx = prepped[sym]["df"].index
        print(f"  {sym}: {idx[0].date()} -> {idx[-1].date()} ({len(idx)} bars)")

    common_start = max(prepped[sym]["df"].index[0] for sym in ASSETS)
    common_idx = prepped["BTCUSDT"]["df"].index
    for sym in ASSETS[1:]:
        common_idx = common_idx.intersection(prepped[sym]["df"].index)
    full_common_idx = common_idx[common_idx >= common_start]
    oos_start_ts = pd.Timestamp(OOS_START, tz="UTC")
    oos_common_idx = full_common_idx[full_common_idx >= oos_start_ts]
    print(f"\nCommon window (all 3 assets have data): {full_common_idx[0].date()} -> {full_common_idx[-1].date()} "
          f"({len(full_common_idx)} bars) - bounded by SOL's 2020-08-11 listing")
    print(f"OOS common window: {oos_common_idx[0].date()} -> {oos_common_idx[-1].date()} ({len(oos_common_idx)} bars)")
    print(
        "Note: OOS runs below use the FULL common index with sim_from=OOS-start (same warmup-preserving\n"
        "contract as the single-asset script's simulate_risk_sized) - the account resets to a fresh $100k\n"
        "at the boundary, but EMA/ATR keep their full history, and same-day re-entry right after a\n"
        "stop-out/crossunder exit is blocked, matching the single-asset script's behavior."
    )

    # (label, full_index, sim_from)
    reports = [("Full-common", full_common_idx, None), ("OOS", full_common_idx, oos_start_ts)]

    print("\n" + "=" * 78)
    print("MULTI-ASSET (BTC+ETH+SOL), 1% risk/trade, no aggregate cap (up to 3% simultaneous)")
    print("=" * 78)
    for label, idx, sim_from in reports:
        m = simulate_portfolio(prepped, idx, STARTING_CAPITAL, RISK_PCT, max_total_risk_pct=None, sim_from=sim_from)
        print("  " + fmt(label, m))

    print("\n" + "=" * 78)
    print("MULTI-ASSET (BTC+ETH+SOL), 1% risk/trade, 2.5% aggregate cap (matches live Konto 2 precedent)")
    print("=" * 78)
    for label, idx, sim_from in reports:
        m = simulate_portfolio(prepped, idx, STARTING_CAPITAL, RISK_PCT, max_total_risk_pct=0.025, sim_from=sim_from)
        print("  " + fmt(label, m))

    print("\n" + "=" * 78)
    print("BTC-ONLY BASELINE on the SAME common window (apples-to-apples vs. multi-asset above)")
    print("=" * 78)
    btc_only = {sym: prepped[sym] for sym in ["BTCUSDT"]}
    for label, idx, sim_from in reports:
        m = simulate_portfolio(btc_only, idx, STARTING_CAPITAL, RISK_PCT, None, sim_from=sim_from)
        print("  " + fmt(label, m))

    print(
        "\nCaveat: BTC/ETH/SOL trend together most of the time (not independent bets) - this raises\n"
        "TRADE COUNT and can smooth day-to-day noise, but does not eliminate correlated drawdown risk\n"
        "the way diversifying into an uncorrelated asset class would. Funding-rate cost not modeled\n"
        "(spot data only, same limitation as the single-asset script)."
    )


if __name__ == "__main__":
    main()
