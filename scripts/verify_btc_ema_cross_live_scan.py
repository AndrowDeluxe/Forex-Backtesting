"""Verifies btc_ema_cross.live_scan.scan_today()'s day-by-day incremental
logic against btc_ema_cross.engine.simulate_risk_sized's own (already
heavily tested) batch backtest, over the same historical window - same
discipline "The Backtest Machine" cheat sheet itself calls for before
trusting a bot: "run the bot's --backfill command and check its trade list
matches your backtest. If they disagree, stop and fix - never run logic
you haven't verified."

Replays scan_today() with dry_run=True (writes nothing to
btc_ema_cross_logs/) once per day over the last ~400 days, carrying its
returned state from one day to the next exactly like the real daily
Task Scheduler run would, and diffs the resulting trade list against
simulate_risk_sized() over the identical window."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import ATR_PERIOD, ATR_STOP_MULT, simulate_risk_sized
from btc_ema_cross.live_scan import PAPER_CAPITAL, PAPER_RISK_PCT, _default_state, scan_today

VERIFY_DAYS = 3000
FULL_START = "2017-08-17"


def main():
    end = pd.Timestamp.now("UTC").normalize()
    full = fetch_klines("BTCUSDT", "1d", FULL_START, (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    verify_start = end - pd.Timedelta(days=VERIFY_DAYS)
    print(f"Replaying live_scan.scan_today() day-by-day, {verify_start.date()} -> {end.date()} ({VERIFY_DAYS} days)")

    state = _default_state()
    replayed_trades = []
    for day in pd.date_range(verify_start, end, freq="D"):
        df_slice = full.loc[full.index <= day + pd.Timedelta(days=1)]  # scan_today wants "today" possibly forming
        row, state = scan_today(as_of=day, state_override=state, dry_run=True, df_override=df_slice)
        if "_trade" in row:
            replayed_trades.append(row["_trade"])

    print(f"\nReplayed (day-by-day, live_scan logic): {len(replayed_trades)} closed trades")
    for t in replayed_trades:
        print(f"  {t['entry_date']} -> {t['exit_date']} ({t['exit_reason']}): "
              f"pnl=${t['pnl_dollar']:+,.2f} ({t['r_multiple']:+.2f}R)")

    sim_from = verify_start
    ref = simulate_risk_sized(full, 9, 21, PAPER_CAPITAL, PAPER_RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
    print(f"\nReference (batch simulate_risk_sized, same window): {len(ref['trades'])} closed trades")
    for t in ref["trades"]:
        ed = t.get("entry_date")
        xd = t.get("exit_date")
        print(f"  {ed.date() if ed is not None else '?'} -> {xd.date() if xd is not None else '?'}"
              f"{'  [STOPPED]' if t.get('stopped_out') else ''}: pnl=${t['pnl']:+,.2f} ({t['r']:+.2f}R)")

    n_match = len(replayed_trades) == len(ref["trades"])
    print(f"\n{'MATCH' if n_match else 'MISMATCH'}: replayed n={len(replayed_trades)} vs. reference n={len(ref['trades'])}")
    if not n_match:
        print("STOP - do not trust the live scanner until this is understood and fixed.")
    else:
        pnl_diffs = [abs(rt["pnl_dollar"] - refT["pnl"]) for rt, refT in zip(replayed_trades, ref["trades"])]
        max_diff = max(pnl_diffs) if pnl_diffs else 0.0
        print(f"Max per-trade PnL difference: ${max_diff:.4f} (rounding-level differences expected, "
              f"day-boundary/float-precision - should be near zero, not systematic)")


if __name__ == "__main__":
    main()
