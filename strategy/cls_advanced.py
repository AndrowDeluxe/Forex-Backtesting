"""CLS Advanced settlement-window breakout/hold framework.

Source: user's "CLS Advanced" call notes (Smartmoneyhour/SMT Macro Desk,
2026-07-27). A discretionary practitioner framework, not an academic
result: CLS Payment-versus-Payment settlement runs 07:00-09:00 Berlin time;
banks square intraday liquidity in the preceding 06:00-07:00 pre-settle
window; 08:45-09:30 is a "test" of whether the resulting break holds
(-> continuation) or fails (-> reversal); 09:00-12:00 is the post-settle
funding window. This module operationalises the source material's own
decision tree (Daytrader Entscheidungsbaum) into code, restricted to what
free OHLCV data can actually measure.

Mapping from the source's checkpoints to code:
- Check 1/2 ("echte News oder Rates-Bestaetigung", "bestaetigen andere
  Crosses die Richtung?"): no free intraday rates feed (e.g. US 2Y yield)
  was wired up, so only the *cross-pair* half is implemented here -
  `compute_cross_confirmation` checks whether a pair's 06:00-09:00 move is
  part of a broad-dollar move shared by the other 5 majors, vs. an
  isolated move. Treat any "confirmed" trade below as cross-pair-confirmed
  only, not rates-confirmed - the Rates check is left for the trader to
  add on top manually.
- Check 3 ("Haelt der Break nach 09:00?"): `holds_0915` - is the close of
  the 09:15 bar (the source's "09:15 Akzeptanz?" checkpoint) still beyond
  the Asia-range level that was broken. Entry is placed at the following
  bar's open (09:30, the source's "09:30 Entscheidung"), matching this
  codebase's no-lookahead convention (strategy/backtest.py: entries fill
  at the *next* bar's open after the signal bar's close).

All hour boundaries are Europe/Berlin local time ("deutsche Zeit" in the
source material), converted from the UTC-indexed Dukascopy OHLCV data.
Asia-range hours (00:00-06:00 Berlin) are an operational assumption, not
given explicitly in the source - it is the window immediately preceding
the framework's own Pre-Settle start (06:00) and roughly spans the CLS
Initial-Pay-In / In-Out-Swap period shown on the source's intraday map.
"""

import numpy as np
import pandas as pd

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]

# XXXUSD pairs: USD is the quote currency, so a *positive* return in the
# pair itself means USD *weaker*. USDXXX pairs: USD is the base currency, a
# positive return means USD *stronger*. Needed to fold all 6 pairs' moves
# onto one common "USD strength" scale for the cross-pair confirmation check.
_USD_IS_QUOTE = {
    "EURUSD": True, "GBPUSD": True, "AUDUSD": True,
    "USDJPY": False, "USDCHF": False, "USDCAD": False,
}

ASIA_START, ASIA_END = 0.0, 6.0   # Asia range window, Berlin hours
SETTLE_END = 9.0                  # 09:00 settlement target
TEST_HOUR = 9.25                  # 09:15 "Akzeptanz?" checkpoint bar
ENTRY_HOUR = 9.5                  # 09:30 "Entscheidung" -> entry fills here
FUNDING_END = 12.0                # 12:00 post-settle funding target / time exit


def to_berlin(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = index.tz_localize("UTC") if index.tz is None else index
    return idx.tz_convert("Europe/Berlin")


def compute_daily_features(df: pd.DataFrame) -> pd.DataFrame:
    """One row per Berlin calendar day: Asia range, the 06:00-09:00 move and
    whether it breaks the Asia range, whether that break still holds at the
    09:15 test checkpoint, and the realised 09:00-12:00 post-settle outcome.
    """
    berlin = to_berlin(df.index)
    hour = berlin.hour + berlin.minute / 60.0
    date = berlin.date

    d = pd.DataFrame(
        {
            "date": date, "hour": hour,
            "open": df["open"].to_numpy(), "high": df["high"].to_numpy(),
            "low": df["low"].to_numpy(), "close": df["close"].to_numpy(),
        }
    )

    rows = []
    for day, g in d.groupby("date"):
        asia = g[(g["hour"] >= ASIA_START) & (g["hour"] < ASIA_END)]
        settle = g[(g["hour"] >= ASIA_END) & (g["hour"] < SETTLE_END)]
        if asia.empty or settle.empty:
            continue

        asia_high, asia_low = asia["high"].max(), asia["low"].min()
        settle_open = settle["open"].iloc[0]
        settle_close = settle["close"].iloc[-1]

        break_up = settle["high"].max() > asia_high
        break_down = settle["low"].min() < asia_low
        if break_up and not break_down:
            direction = 1
        elif break_down and not break_up:
            direction = -1
        elif break_up and break_down:
            # swept both sides intraday - resolve by where the 09:00 close landed
            direction = 1 if settle_close > (asia_high + asia_low) / 2 else -1
        else:
            direction = 0

        move_06_09 = settle_close / settle_open - 1

        test_bar = g[(g["hour"] >= TEST_HOUR) & (g["hour"] < ENTRY_HOUR)]
        holds = np.nan
        if direction != 0 and not test_bar.empty:
            test_close = test_bar["close"].iloc[-1]
            holds = bool(test_close > asia_high) if direction == 1 else bool(test_close < asia_low)

        post = g[(g["hour"] >= SETTLE_END) & (g["hour"] < FUNDING_END)]
        post_settle_return, realized_continuation = np.nan, np.nan
        if direction != 0 and not post.empty:
            post_settle_return = post["close"].iloc[-1] / settle_close - 1
            realized_continuation = bool(np.sign(post_settle_return) == direction)

        rows.append(
            {
                "date": day, "asia_high": asia_high, "asia_low": asia_low,
                "direction": direction, "move_06_09": move_06_09,
                "holds_0915": holds, "post_settle_return": post_settle_return,
                "realized_continuation": realized_continuation,
            }
        )
    return pd.DataFrame(rows).set_index("date")


def compute_cross_confirmation(daily_by_pair: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    """For each pair/day: is its 06:00-09:00 move part of a broad-dollar move
    shared by the *other* 5 majors, or an isolated move confined to that one
    pair (the source material's "isolierte Waehrungsstaerke" red flag)?
    """
    usd_strength = {
        pair: (-daily["move_06_09"] if _USD_IS_QUOTE[pair] else daily["move_06_09"])
        for pair, daily in daily_by_pair.items()
    }
    usd_df = pd.DataFrame(usd_strength)

    confirm = {}
    for pair in daily_by_pair:
        avg_other = usd_df.drop(columns=[pair]).mean(axis=1, skipna=True)
        own = usd_df[pair]
        confirm[pair] = (np.sign(own) == np.sign(avg_other)) & (own.abs() > 1e-9)
    return confirm


def build_backtest_frame(
    df: pd.DataFrame,
    daily: pd.DataFrame,
    confirm: pd.Series,
    mode: str = "continuation",
) -> pd.DataFrame:
    """Attach signal/prev_high/prev_low/atr/vwap/session columns so the
    existing `strategy.backtest.simulate_trades` engine can run this
    signal unmodified (same pattern as `strategy/cls_squeeze.py`).

    `mode="continuation"`: enter in the breakout direction only if the break
    still holds at the 09:15 test *and* the cross-pair check confirms it.
    `mode="reversal"`: enter *against* the breakout direction when the break
    fails to hold at 09:15 (no cross-pair check - a failed, unconfirmed
    break is exactly the "reversal" branch of the source's decision tree).
    """
    if mode not in ("continuation", "reversal"):
        raise ValueError(f"mode must be 'continuation' or 'reversal', got {mode!r}")

    from strategy.indicators import assign_sessions, compute_adx

    out = df.copy()
    out = compute_adx(out, n=14)  # adds atr (needed for the stop) and adx (simulate_trades logs adx_at_entry)
    out["session"] = assign_sessions(out.index, reset_hour=22)  # Berlin midnight, CEST
    out["vwap"] = out["close"]  # placeholder column; unused since use_vwap_target=False

    berlin = to_berlin(out.index)
    hour = berlin.hour + berlin.minute / 60.0
    date = pd.Series(berlin.date, index=out.index)

    out["prev_high"] = date.map(daily["asia_high"])
    out["prev_low"] = date.map(daily["asia_low"])

    direction = date.map(daily["direction"])
    holds = date.map(daily["holds_0915"])
    conf = date.map(confirm)

    signal_bar = (hour >= TEST_HOUR) & (hour < ENTRY_HOUR)

    if mode == "continuation":
        active = (direction != 0) & (holds == True) & (conf == True)  # noqa: E712
        sig_dir = direction
    else:
        active = (direction != 0) & (holds == False)  # noqa: E712
        sig_dir = -direction

    out["signal"] = 0
    mask = signal_bar & active.fillna(False)
    out.loc[mask, "signal"] = sig_dir[mask]
    return out
