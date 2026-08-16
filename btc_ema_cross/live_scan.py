"""Live/paper forward-test scanner for BTC EMA9/21 (2026-08-16) - NOT a
real trading bot: PAPER ONLY, no exchange account touched, no real orders
ever placed. Tracks a hypothetical $100k account at 1% risk/trade using the
EXACT validated logic from btc_ema_cross.engine (long/flat, ATR(14)x2.0
stop, no take-profit, no breakeven - the most heavily tested configuration,
not one of the "tested, not adopted" variants), so forward-test results
stay directly comparable to the backtest headline numbers.

Unlike cls_practical's live_scan.py (a single-session strategy that never
needs to remember yesterday), this strategy holds positions across many
days/weeks - position state is persisted across runs in
btc_ema_cross_logs/paper_state.json.

Timing: Binance daily candles close at 00:00 UTC. Scheduled via Windows
Task Scheduler ("BTC-EMA-Cross-Scan") for shortly after, in Europe/Berlin
local time - DST means the actual UTC-relative delay drifts by an hour
across the year, irrelevant here since crypto trades 24/7 and this is a
paper log, not latency-sensitive live execution.

At run time the most recently CLOSED daily bar is fully known (immutable
high/low/close); the still-forming "today" bar's OPEN price (fixed at its
start, doesn't change intra-day) is used as the fill price for any signal
computed from the closed bar - exactly the backtest's "decide on
yesterday's close, fill at today's open" convention.

Disclosed stop-checking approximation: checked once per day against the
closed bar's low, not a real-time resting stop order - if the daily low
touched the stop, this assumes a fill exactly at the stop price with no
gap-through, the same simplification the backtest itself uses. A
live-money bot would need a real resting stop order at the exchange
instead of this once-daily check."""

import csv
import json
from pathlib import Path

import pandas as pd

from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import ATR_PERIOD, ATR_STOP_MULT, COMMISSION
from btc_ema_cross.telegram_notify import send_telegram_message
from strategy.indicators import compute_atr

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_DIR / "btc_ema_cross_logs"
STATE_PATH = LOG_DIR / "paper_state.json"
TRADES_CSV = LOG_DIR / "paper_trades.csv"

PAPER_CAPITAL = 100_000.0
PAPER_RISK_PCT = 0.01
LOOKBACK_DAYS = 100  # ample warmup margin for EMA21/ATR14

TRADE_FIELDS = [
    "entry_date", "exit_date", "exit_reason", "raw_entry_price", "entry_price_filled",
    "exit_price_filled", "qty", "pnl_dollar", "r_multiple", "cash_after",
]


def _default_state() -> dict:
    return {
        "in_position": False, "entry_date": None, "entry_price": None, "raw_entry_price": None,
        "stop_price": None, "qty": None, "trade_risk_dollar": None, "cash": PAPER_CAPITAL,
    }


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return _default_state()


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _log_trade(row: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    is_new = not TRADES_CSV.exists()
    with open(TRADES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in TRADE_FIELDS})


def scan_today(as_of: pd.Timestamp | None = None, state_override: dict | None = None,
                dry_run: bool = False, df_override: pd.DataFrame | None = None) -> tuple[dict, dict]:
    """Returns (row, new_state). `as_of`/`state_override`/`dry_run`/
    `df_override` exist so scripts/verify_btc_ema_cross_live_scan.py can
    replay this exact function day-by-day over history and diff the result
    against btc_ema_cross.engine.simulate_risk_sized's own trade list -
    normal daily use (scripts/collect_btc_ema_cross_daily_log.py) calls this
    with no arguments, using real "now", real persisted state, and writing
    for real (dry_run=False)."""
    today = (as_of if as_of is not None else pd.Timestamp.now("UTC")).normalize()

    if df_override is not None:
        df = df_override
    else:
        start = (today - pd.Timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        end = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df = fetch_klines("BTCUSDT", "1d", start, end, force_refresh=True)
    if df.empty:
        return {"date": today.date().isoformat(), "status": "keine Daten (Binance-API-Fehler?)"}, (state_override or load_state())

    if df.index[-1] < today:
        # data not yet reflecting today's forming candle - too early, skip action
        return {"date": today.date().isoformat(), "status": "Daten noch nicht aktuell (zu frueh?)"}, (state_override or load_state())

    forming = df.loc[df.index == today].iloc[0] if today in df.index else df.iloc[-1]
    closed = df.loc[df.index < today] if today in df.index else df.iloc[:-1]
    if len(closed) < 30:
        return {"date": today.date().isoformat(), "status": "nicht genug Historie fuer Warmup"}, (state_override or load_state())

    close = closed["close"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    atr = compute_atr(closed, ATR_PERIOD)

    yesterday_above = bool(above.iloc[-1])
    day_before_above = bool(above.iloc[-2])
    go_long = yesterday_above and not day_before_above
    go_flat = (not yesterday_above) and day_before_above

    state = dict(state_override) if state_override is not None else load_state()
    today_open = float(forming["open"])
    yesterday_low = float(closed["low"].iloc[-1])
    yesterday_close = float(close.iloc[-1])
    atr_yesterday = float(atr.iloc[-1])

    row = {
        "date": today.date().isoformat(),
        "yesterday_close": round(yesterday_close, 2),
        "ema9": round(float(ema_fast.iloc[-1]), 2),
        "ema21": round(float(ema_slow.iloc[-1]), 2),
        "above": yesterday_above,
        "go_long_signal": go_long,
        "go_flat_signal": go_flat,
        "action": "none",
    }

    # 1) Exit check (on a position carried over from a prior run) - always
    # before any new entry, exactly the backtest's per-bar order. STOP
    # checked first here, unlike the backtest's go_flat-first order: a daily
    # scan only learns about yesterday's stop breach AND yesterday's
    # crossunder confirmation in the same call, but the stop (an intrabar
    # price event) can only have happened no LATER than the crossunder
    # (which needs yesterday's full close to confirm) - so if both look
    # true from a single once-daily scan, the stop chronologically came
    # first and must take priority. Verified 2026-08-16 against
    # scripts/verify_btc_ema_cross_live_scan.py - this ordering was
    # required to match the batch backtest on a real stop+crossunder
    # same-day case (2025-09-25).
    if state["in_position"]:
        exit_reason, exit_raw = None, None
        if yesterday_low <= state["stop_price"]:
            exit_reason, exit_raw = "stop", state["stop_price"]
        elif go_flat:
            exit_reason, exit_raw = "crossunder", today_open

        if exit_reason:
            exit_fill = exit_raw * (1 - COMMISSION)
            pnl = state["qty"] * (exit_fill - state["entry_price"])
            r_multiple = pnl / state["trade_risk_dollar"]
            new_cash = state["cash"] + state["qty"] * exit_fill
            trade_row = {
                "entry_date": state["entry_date"], "exit_date": row["date"], "exit_reason": exit_reason,
                "raw_entry_price": state["raw_entry_price"], "entry_price_filled": state["entry_price"],
                "exit_price_filled": exit_fill, "qty": state["qty"], "pnl_dollar": pnl,
                "r_multiple": r_multiple, "cash_after": new_cash,
            }
            if not dry_run:
                _log_trade(trade_row)
                icon = "\U0001F7E2" if pnl > 0 else "\U0001F534"
                send_telegram_message(
                    f"[BTC EMA9/21 Paper] {icon} EXIT ({exit_reason}) @ ${exit_fill:,.2f}\n"
                    f"Entry {state['entry_date']} @ ${state['raw_entry_price']:,.2f} -> "
                    f"heute {row['date']}\n"
                    f"PnL: ${pnl:+,.2f} ({r_multiple:+.2f}R)  |  Cash: ${new_cash:,.2f}"
                )
            row["action"] = f"exit ({exit_reason}), pnl=${pnl:+,.2f} ({r_multiple:+.2f}R)"
            row["_trade"] = trade_row
            state = _default_state()
            state["cash"] = new_cash

    # 2) Entry check - only if flat after the exit check above.
    if not state["in_position"] and go_long and atr_yesterday > 0:
        stop_dist = ATR_STOP_MULT * atr_yesterday
        entry_fill = today_open * (1 + COMMISSION)
        equity_now = state["cash"]
        target_qty = (equity_now * PAPER_RISK_PCT) / stop_dist
        max_qty = equity_now / entry_fill
        qty = min(target_qty, max_qty)
        state.update({
            "in_position": True, "entry_date": row["date"], "entry_price": entry_fill,
            "raw_entry_price": today_open, "stop_price": today_open - stop_dist,
            "qty": qty, "trade_risk_dollar": qty * stop_dist,
        })
        state["cash"] -= qty * entry_fill
        row["action"] = f"entry long @ {entry_fill:,.2f}, stop @ {state['stop_price']:,.2f}, qty={qty:.6f}"
        if not dry_run:
            send_telegram_message(
                f"[BTC EMA9/21 Paper] \U0001F7E2 ENTRY long @ ${entry_fill:,.2f}\n"
                f"Stop: ${state['stop_price']:,.2f}  |  Groesse: {qty:.6f} BTC  |  "
                f"Risiko: ${state['trade_risk_dollar']:,.2f} (1% von ${equity_now:,.2f})"
            )

    row["in_position"] = state["in_position"]
    row["equity_mark_to_market"] = round(
        state["cash"] + (state["qty"] * row["yesterday_close"] if state["in_position"] else 0.0), 2
    )

    if not dry_run:
        save_state(state)
    return row, state


def current_signal(as_of: pd.Timestamp | None = None) -> dict:
    """Pure, stateless signal read - no paper-account state, no file writes.
    For real execution bridges (private, outside this repo): the broker
    account itself IS the position state (mt5.positions_get()), so a bridge
    doesn't need/want this module's paper-state bookkeeping - it only needs
    "does the rule say long today, and what are entry/stop". Same warmup/
    fill-timing contract as scan_today(): go_long/go_flat are evaluated on
    the most recently CLOSED bar, raw_entry_open is the still-forming
    bar's open (today's fill reference price, matching "decide on
    yesterday's close, fill at today's open").

    Returns: {date, go_long, go_flat, above, raw_entry_open, atr_yesterday,
    yesterday_low, yesterday_close, stop_price_if_entering} or
    {date, status: "..."} if data isn't ready (too early/insufficient
    history/API error) - callers must check for "status" before using the
    other fields."""
    today = (as_of if as_of is not None else pd.Timestamp.now("UTC")).normalize()
    start = (today - pd.Timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    df = fetch_klines("BTCUSDT", "1d", start, end, force_refresh=True)

    if df.empty:
        return {"date": today.date().isoformat(), "status": "keine Daten (Binance-API-Fehler?)"}
    if df.index[-1] < today:
        return {"date": today.date().isoformat(), "status": "Daten noch nicht aktuell (zu frueh?)"}

    forming = df.loc[df.index == today].iloc[0] if today in df.index else df.iloc[-1]
    closed = df.loc[df.index < today] if today in df.index else df.iloc[:-1]
    if len(closed) < 30:
        return {"date": today.date().isoformat(), "status": "nicht genug Historie fuer Warmup"}

    close = closed["close"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    atr = compute_atr(closed, ATR_PERIOD)

    yesterday_above = bool(above.iloc[-1])
    day_before_above = bool(above.iloc[-2])
    go_long = yesterday_above and not day_before_above
    go_flat = (not yesterday_above) and day_before_above
    raw_entry_open = float(forming["open"])
    atr_yesterday = float(atr.iloc[-1])
    stop_dist = ATR_STOP_MULT * atr_yesterday

    return {
        "date": today.date().isoformat(),
        "go_long": go_long,
        "go_flat": go_flat,
        "above": yesterday_above,
        "raw_entry_open": raw_entry_open,
        "atr_yesterday": atr_yesterday,
        "yesterday_low": float(closed["low"].iloc[-1]),
        "yesterday_close": float(close.iloc[-1]),
        "stop_price_if_entering": raw_entry_open - stop_dist if stop_dist > 0 else None,
    }
