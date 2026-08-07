"""Dollar-denominated portfolio simulation on a fixed starting account (default
100k), with risk-based position sizing -- mirrors the position-sizing pattern
already used by the live OU-Modell bot (OU-Modell-MT5-Bridge/sizing.py +
executor.calc_open_risk): each trade risks a fixed % of current equity against its
stop distance, and a portfolio-level cap limits aggregate open risk across all
concurrent positions. The paper itself doesn't specify sizing/capital, so this is
an explicit, realistic assumption layered on top of its entry/exit rules.

Same entry/exit rules as bollinger.py (band entry, MA/stop/max-holding exit), but
driven as a single chronological loop across the whole universe so positions share
one equity curve and one risk budget, instead of being backtested independently
per ticker.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config


@dataclass
class _Position:
    ticker: str
    direction: int  # 1 long, -1 short
    shares: float
    entry_price: float
    entry_date: pd.Timestamp
    last_price: float
    stop_price: float
    risk_dollars: float
    days_held: int = 0


@dataclass
class _BracketPosition:
    ticker: str
    direction: int
    shares: float
    entry_price: float
    entry_date: pd.Timestamp
    last_price: float
    stop_price: float
    tp_price: float | None
    stop_distance: float  # fixed at entry, used for the BE trigger (be_trigger_r * stop_distance)
    risk_dollars: float
    be_moved: bool = False
    days_held: int = 0


@dataclass
class _TrailingPosition:
    ticker: str
    shares: float
    entry_price: float
    entry_date: pd.Timestamp
    last_price: float
    stop_price: float
    highest_price: float  # highest close seen since entry (long-only), anchors the trail
    risk_dollars: float
    days_held: int = 0


def _precompute_indicators(
    panel: pd.DataFrame, tickers: list[str], lookback: int, k: float, trend_window: int | None = None
) -> dict:
    ind = {}
    for t in tickers:
        if t not in panel.columns:
            continue
        price = panel[t].dropna()
        ma = price.rolling(lookback).mean()
        std = price.rolling(lookback).std()
        entry = {
            "price": price,
            "ma": ma,
            "std": std,
            "upper": ma + k * std,
            "lower": ma - k * std,
        }
        if trend_window:
            entry["trend"] = price.rolling(trend_window).mean()
        ind[t] = entry
    return ind


def simulate_portfolio(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    initial_equity: float = config.INITIAL_EQUITY,
    risk_pct: float = config.RISK_PCT_PER_TRADE,
    max_total_risk_pct: float = config.MAX_TOTAL_RISK_PCT,
    max_position_pct: float = config.MAX_POSITION_PCT,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    stop_sigma: float = config.STOP_LOSS_SIGMA,
    allowed_directions: tuple[int, ...] = (1, -1),
) -> tuple[pd.Series, list[dict]]:
    ind = _precompute_indicators(panel, tickers, lookback, k)
    all_dates = panel.loc[start:end].index

    equity = initial_equity
    open_risk = 0.0
    positions: dict[str, _Position] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        # 1. mark-to-market + process exits for open positions
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]
            ma_t = data["ma"].loc[date]
            if pd.isna(ma_t):
                continue

            signed_change = (price_t - pos.last_price) if pos.direction == 1 else (pos.last_price - price_t)
            equity += pos.shares * signed_change
            pos.last_price = price_t
            pos.days_held += 1

            exit_now, reason = False, None
            if pos.direction == 1:
                if price_t <= pos.stop_price:
                    exit_now, reason = True, "stop_loss"
                elif price_t >= ma_t:
                    exit_now, reason = True, "mean_revert"
                elif pos.days_held >= max_hold:
                    exit_now, reason = True, "max_holding"
            else:
                if price_t >= pos.stop_price:
                    exit_now, reason = True, "stop_loss"
                elif price_t <= ma_t:
                    exit_now, reason = True, "mean_revert"
                elif pos.days_held >= max_hold:
                    exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (
                    (price_t - pos.entry_price) if pos.direction == 1 else (pos.entry_price - price_t)
                )
                trades.append(
                    {
                        "ticker": t,
                        "direction": "long" if pos.direction == 1 else "short",
                        "entry_date": pos.entry_date,
                        "exit_date": date,
                        "entry_price": pos.entry_price,
                        "exit_price": price_t,
                        "shares": pos.shares,
                        "days_held": pos.days_held,
                        "pnl_dollars": pnl_dollars,
                        "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price),
                        "reason": reason,
                    }
                )
                open_risk -= pos.risk_dollars
                del positions[t]

        # 2. new entries for flat tickers
        for t in tickers:
            if t in positions or t not in ind:
                continue
            data = ind[t]
            if date not in data["price"].index:
                continue
            price_t = data["price"].loc[date]
            ma_t, std_t = data["ma"].loc[date], data["std"].loc[date]
            upper_t, lower_t = data["upper"].loc[date], data["lower"].loc[date]
            if pd.isna(ma_t) or pd.isna(std_t) or std_t == 0:
                continue

            direction = 0
            if price_t < lower_t:
                direction = 1
            elif price_t > upper_t:
                direction = -1
            if direction == 0 or direction not in allowed_directions:
                continue

            stop_distance = stop_sigma * std_t
            risk_dollars = equity * risk_pct
            if open_risk + risk_dollars > equity * max_total_risk_pct:
                continue  # portfolio-level risk cap reached, skip this signal

            shares = risk_dollars / stop_distance
            max_shares_by_notional = (equity * max_position_pct) / price_t
            shares = min(shares, max_shares_by_notional)
            shares = float(np.floor(shares))
            if shares <= 0:
                continue

            stop_price = price_t - stop_distance if direction == 1 else price_t + stop_distance
            positions[t] = _Position(
                ticker=t, direction=direction, shares=shares, entry_price=price_t,
                entry_date=date, last_price=price_t, stop_price=stop_price, risk_dollars=risk_dollars,
            )
            open_risk += risk_dollars

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades


def simulate_bracket_portfolio(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    initial_equity: float = config.INITIAL_EQUITY,
    risk_pct: float = config.RISK_PCT_PER_TRADE,
    max_total_risk_pct: float = config.MAX_TOTAL_RISK_PCT,
    max_position_pct: float = config.MAX_POSITION_PCT,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    stop_sigma: float = config.STOP_LOSS_SIGMA,
    rr_ratio: float | None = 1.5,
    be_trigger_r: float = 0.5,
    allowed_directions: tuple[int, ...] = (1,),
    trend_filter_window: int | None = None,
    regime_filter: pd.Series | None = None,
) -> tuple[pd.Series, list[dict]]:
    """Fixed-CRV bracket exit -- mirrors the live OU-Modell-MT5-Bridge bot's actual
    mechanism (not the paper's own "exit at MA" rule used by simulate_portfolio):
    entry on a band breach, then a hard SL at `stop_sigma` * rolling std and a hard
    TP at `rr_ratio` * that same distance (live default rr_ratio=1.5, i.e. the
    website's "Ziel (1:1,5)"), with the SL moved to breakeven once price has moved
    `be_trigger_r` * stop_distance in favor (live default 0.5, same as all 3
    accounts' `be_trigger_r` in OU-Modell-MT5-Bridge/config.py). `max_hold` is a
    hard forced exit here for backtest tractability -- live treats it as a
    warn-only signal (check_max_holding_period()), so this is slightly more
    conservative than the real bot. `rr_ratio=None` disables the TP entirely
    (only SL/breakeven/max_holding decide the exit). `trend_filter_window`, if
    set (e.g. 200), is a PER-STOCK pre-entry filter: a long signal is only taken
    when that stock's own price is above its N-day SMA -- found (2026-08-05) to
    hurt more than it helps, since individual names routinely dip below their own
    200d SMA during normal pullbacks in an otherwise healthy market. `regime_filter`,
    if set, is a boolean pd.Series indexed by date (True = entries allowed that day)
    applied MARKET-WIDE to every ticker alike (e.g. benchmark-index-trend or VIX-based)
    -- meant to gate out only genuine broad bear/panic regimes without chopping away
    good idiosyncratic single-stock dip-buys the way the per-stock filter did.
    """
    ind = _precompute_indicators(panel, tickers, lookback, k, trend_filter_window)
    all_dates = panel.loc[start:end].index

    equity = initial_equity
    open_risk = 0.0
    positions: dict[str, _BracketPosition] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]

            signed_change = (price_t - pos.last_price) if pos.direction == 1 else (pos.last_price - price_t)
            equity += pos.shares * signed_change
            pos.last_price = price_t
            pos.days_held += 1

            if not pos.be_moved and be_trigger_r > 0:
                trigger_dist = be_trigger_r * pos.stop_distance
                favorable = (price_t - pos.entry_price) if pos.direction == 1 else (pos.entry_price - price_t)
                if favorable >= trigger_dist:
                    pos.stop_price = pos.entry_price
                    pos.be_moved = True

            exit_now, reason = False, None
            has_tp = pos.tp_price is not None
            if pos.direction == 1:
                if price_t <= pos.stop_price:
                    exit_now, reason = True, ("breakeven" if pos.be_moved else "stop_loss")
                elif has_tp and price_t >= pos.tp_price:
                    exit_now, reason = True, "take_profit"
                elif pos.days_held >= max_hold:
                    exit_now, reason = True, "max_holding"
            else:
                if price_t >= pos.stop_price:
                    exit_now, reason = True, ("breakeven" if pos.be_moved else "stop_loss")
                elif has_tp and price_t <= pos.tp_price:
                    exit_now, reason = True, "take_profit"
                elif pos.days_held >= max_hold:
                    exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (
                    (price_t - pos.entry_price) if pos.direction == 1 else (pos.entry_price - price_t)
                )
                trades.append(
                    {
                        "ticker": t,
                        "direction": "long" if pos.direction == 1 else "short",
                        "entry_date": pos.entry_date,
                        "exit_date": date,
                        "entry_price": pos.entry_price,
                        "exit_price": price_t,
                        "shares": pos.shares,
                        "days_held": pos.days_held,
                        "pnl_dollars": pnl_dollars,
                        "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price),
                        "reason": reason,
                    }
                )
                open_risk -= pos.risk_dollars
                del positions[t]

        regime_ok = True
        if regime_filter is not None:
            regime_ok = bool(regime_filter.get(date, False))

        for t in tickers:
            if not regime_ok:
                break
            if t in positions or t not in ind:
                continue
            data = ind[t]
            if date not in data["price"].index:
                continue
            price_t = data["price"].loc[date]
            ma_t, std_t = data["ma"].loc[date], data["std"].loc[date]
            upper_t, lower_t = data["upper"].loc[date], data["lower"].loc[date]
            if pd.isna(ma_t) or pd.isna(std_t) or std_t == 0:
                continue

            direction = 0
            if price_t < lower_t:
                direction = 1
            elif price_t > upper_t:
                direction = -1
            if direction == 0 or direction not in allowed_directions:
                continue

            if trend_filter_window:
                trend_t = data["trend"].loc[date]
                if pd.isna(trend_t):
                    continue
                # only take dip-buys (long) in a confirmed uptrend, mirror for shorts
                if (direction == 1 and price_t < trend_t) or (direction == -1 and price_t > trend_t):
                    continue

            stop_distance = stop_sigma * std_t
            risk_dollars = equity * risk_pct
            if open_risk + risk_dollars > equity * max_total_risk_pct:
                continue

            shares = risk_dollars / stop_distance
            max_shares_by_notional = (equity * max_position_pct) / price_t
            shares = min(shares, max_shares_by_notional)
            shares = float(np.floor(shares))
            if shares <= 0:
                continue

            if direction == 1:
                stop_price = price_t - stop_distance
                tp_price = (price_t + rr_ratio * stop_distance) if rr_ratio else None
            else:
                stop_price = price_t + stop_distance
                tp_price = (price_t - rr_ratio * stop_distance) if rr_ratio else None

            positions[t] = _BracketPosition(
                ticker=t, direction=direction, shares=shares, entry_price=price_t,
                entry_date=date, last_price=price_t, stop_price=stop_price, tp_price=tp_price,
                stop_distance=stop_distance, risk_dollars=risk_dollars,
            )
            open_risk += risk_dollars

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades


def simulate_trailing_bracket_portfolio(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    initial_equity: float = config.INITIAL_EQUITY,
    risk_pct: float = config.RISK_PCT_PER_TRADE,
    max_total_risk_pct: float = config.MAX_TOTAL_RISK_PCT,
    max_position_pct: float = config.MAX_POSITION_PCT,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    trail_type: str = "stddev",
    trail_mult: float = 3.0,
    trail_pct: float = 0.10,
    atr_panel: pd.DataFrame | None = None,
    regime_filter: pd.Series | None = None,
) -> tuple[pd.Series, list[dict]]:
    """Trailing-stop variant of simulate_bracket_portfolio, requested (2026-08-06) as a
    "step back" from the fixed-CRV bracket to see whether letting winners run (instead of
    a fixed 3-sigma SL + one-shot breakeven move + no TP) helps. Replaces the fixed
    SL/breakeven/TP mechanism entirely -- a trailing stop already achieves "lock in gains
    as price moves favorably" on its own, so layering the old be_trigger_r on top would be
    redundant. Long-only (the only direction validated so far, see final_config_summary.csv).

    `trail_type` selects how the trailing distance is computed, recalculated fresh each day
    off the CURRENT day's volatility/price (not fixed at entry, unlike the fixed bracket's
    stop_distance) -- so the stop can tighten in calm markets and widen in volatile ones:
      - "stddev": trail_mult * rolling close-to-close std (same std already used for the
        fixed-bracket SL, just re-applied every day instead of only at entry)
      - "atr": trail_mult * Average True Range (needs real High/Low data -- see atr_data.py --
        since the rest of this package only caches Close prices; pass `atr_panel`)
      - "pct": trail_pct * highest close since entry (simplest, no volatility input at all)

    The stop only ever ratchets UP (never back down) off the highest close since entry --
    standard chandelier-exit behavior. Initial stop at entry uses the same formula as the
    ongoing trail, so day-1 risk sizing is consistent with the exit rule that governs it.
    """
    if trail_type not in ("stddev", "atr", "pct"):
        raise ValueError(f"unknown trail_type: {trail_type!r}")
    if trail_type == "atr" and atr_panel is None:
        raise ValueError("trail_type='atr' requires atr_panel (see atr_data.build_atr_panel)")

    ind = _precompute_indicators(panel, tickers, lookback, k)
    all_dates = panel.loc[start:end].index

    def _trail_distance(t: str, date: pd.Timestamp, ref_price: float) -> float | None:
        if trail_type == "pct":
            return trail_pct * ref_price
        if trail_type == "stddev":
            std_t = ind[t]["std"].get(date)
            return trail_mult * std_t if pd.notna(std_t) and std_t > 0 else None
        atr_t = atr_panel[t].get(date) if t in atr_panel.columns else None
        return trail_mult * atr_t if atr_t is not None and pd.notna(atr_t) and atr_t > 0 else None

    equity = initial_equity
    open_risk = 0.0
    positions: dict[str, _TrailingPosition] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]

            equity += pos.shares * (price_t - pos.last_price)
            pos.last_price = price_t
            pos.days_held += 1
            pos.highest_price = max(pos.highest_price, price_t)

            dist = _trail_distance(t, date, pos.highest_price)
            if dist is not None:
                candidate_stop = pos.highest_price - dist
                pos.stop_price = max(pos.stop_price, candidate_stop)

            exit_now, reason = False, None
            if price_t <= pos.stop_price:
                exit_now = True
                reason = "trailing_stop" if pos.stop_price > pos.entry_price else "stop_loss"
            elif pos.days_held >= max_hold:
                exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (price_t - pos.entry_price)
                trades.append({
                    "ticker": t, "direction": "long", "entry_date": pos.entry_date, "exit_date": date,
                    "entry_price": pos.entry_price, "exit_price": price_t, "shares": pos.shares,
                    "days_held": pos.days_held, "pnl_dollars": pnl_dollars,
                    "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price), "reason": reason,
                })
                open_risk -= pos.risk_dollars
                del positions[t]

        regime_ok = True
        if regime_filter is not None:
            regime_ok = bool(regime_filter.get(date, False))

        for t in tickers:
            if not regime_ok:
                break
            if t in positions or t not in ind:
                continue
            data = ind[t]
            if date not in data["price"].index:
                continue
            price_t = data["price"].loc[date]
            ma_t, std_t, lower_t = data["ma"].loc[date], data["std"].loc[date], data["lower"].loc[date]
            if pd.isna(ma_t) or pd.isna(std_t) or std_t == 0 or price_t >= lower_t:
                continue

            dist = _trail_distance(t, date, price_t)
            if dist is None:
                continue  # e.g. missing ATR for this ticker/date -- skip rather than mis-size

            risk_dollars = equity * risk_pct
            if open_risk + risk_dollars > equity * max_total_risk_pct:
                continue

            shares = risk_dollars / dist
            max_shares_by_notional = (equity * max_position_pct) / price_t
            shares = min(shares, max_shares_by_notional)
            shares = float(np.floor(shares))
            if shares <= 0:
                continue

            positions[t] = _TrailingPosition(
                ticker=t, shares=shares, entry_price=price_t, entry_date=date, last_price=price_t,
                stop_price=price_t - dist, highest_price=price_t, risk_dollars=risk_dollars,
            )
            open_risk += risk_dollars

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades


def simulate_bracket_portfolio_margin_capped(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    initial_equity: float,
    risk_pct: float,
    max_leverage: float = 30.0,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    stop_sigma: float = config.STOP_LOSS_SIGMA,
    rr_ratio: float | None = None,
    be_trigger_r: float = 0.25,
    regime_filter: pd.Series | None = None,
) -> tuple[pd.Series, list[dict]]:
    """simulate_bracket_portfolio's SAME risk_pct-driven position sizing (shares =
    risk_dollars/stop_distance, so `risk_pct` still determines how big a position is
    for a given stop distance -- this is the "Risk Management" the user wants
    optimized), but the AGGREGATE cap is the account's actual margin/leverage
    ceiling (equity * max_leverage total notional, e.g. 3500 EUR * 30 = 105,000 EUR)
    instead of an artificial max_total_risk_pct. Requested (2026-08-07) for a small
    own-capital/no-challenge-rules account (Konto 3) where the ONLY real constraint
    is the broker's leverage limit.

    IMPORTANT precedent from simulate_leveraged_book's pure-margin-maximization
    result: sizing purely by "use all available margin" (ignoring risk_pct) blows
    up catastrophically here, because 30x leverage times this strategy's ~5-10%
    stop distance implies a 150-300%-of-margin loss on a single stop-out. This
    function avoids that failure mode structurally -- risk_pct still caps how much
    is actually risked per trade (in equity terms), and the leverage ceiling is
    just a backstop on total notional, not the sizing driver. Long-only (the only
    validated direction)."""
    ind = _precompute_indicators(panel, tickers, lookback, k)
    all_dates = panel.loc[start:end].index

    equity = initial_equity
    open_notional = 0.0
    positions: dict[str, _BracketPosition] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]

            equity += pos.shares * (price_t - pos.last_price)
            pos.last_price = price_t
            pos.days_held += 1

            if not pos.be_moved and be_trigger_r > 0:
                trigger_dist = be_trigger_r * pos.stop_distance
                favorable = price_t - pos.entry_price
                if favorable >= trigger_dist:
                    pos.stop_price = pos.entry_price
                    pos.be_moved = True

            exit_now, reason = False, None
            has_tp = pos.tp_price is not None
            if price_t <= pos.stop_price:
                exit_now, reason = True, ("breakeven" if pos.be_moved else "stop_loss")
            elif has_tp and price_t >= pos.tp_price:
                exit_now, reason = True, "take_profit"
            elif pos.days_held >= max_hold:
                exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (price_t - pos.entry_price)
                trades.append({
                    "ticker": t, "direction": "long", "entry_date": pos.entry_date, "exit_date": date,
                    "entry_price": pos.entry_price, "exit_price": price_t, "shares": pos.shares,
                    "days_held": pos.days_held, "pnl_dollars": pnl_dollars,
                    "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price), "reason": reason,
                })
                open_notional -= pos.shares * pos.entry_price
                del positions[t]

        regime_ok = True
        if regime_filter is not None:
            regime_ok = bool(regime_filter.get(date, False))

        for t in tickers:
            if not regime_ok:
                break
            if t in positions or t not in ind:
                continue
            data = ind[t]
            if date not in data["price"].index:
                continue
            price_t = data["price"].loc[date]
            ma_t, std_t, lower_t = data["ma"].loc[date], data["std"].loc[date], data["lower"].loc[date]
            if pd.isna(ma_t) or pd.isna(std_t) or std_t == 0 or price_t >= lower_t:
                continue

            stop_distance = stop_sigma * std_t
            risk_dollars = equity * risk_pct
            shares = risk_dollars / stop_distance

            available_margin = max(0.0, equity * max_leverage - open_notional)
            max_shares_by_margin = available_margin / price_t
            shares = min(shares, max_shares_by_margin)
            shares = float(np.floor(shares))
            if shares <= 0:
                continue

            stop_price = price_t - stop_distance
            tp_price = (price_t + rr_ratio * stop_distance) if rr_ratio else None

            positions[t] = _BracketPosition(
                ticker=t, direction=1, shares=shares, entry_price=price_t,
                entry_date=date, last_price=price_t, stop_price=stop_price, tp_price=tp_price,
                stop_distance=stop_distance, risk_dollars=risk_dollars,
            )
            open_notional += shares * price_t

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades


def simulate_leveraged_book(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    initial_equity: float,
    max_leverage: float = 30.0,
    regime_filter: pd.Series | None = None,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    stop_sigma: float = config.STOP_LOSS_SIGMA,
    rr_ratio: float | None = None,
    be_trigger_r: float = 0.25,
) -> tuple[pd.Series, list[dict]]:
    """Margin/leverage-based sizing, requested (2026-08-07) for a small own-capital
    account (Konto 3, ~3500 EUR) with NO drawdown constraint at all -- the only real
    limit on a retail CFD/leveraged account is the broker's max leverage (EU/ESMA-style
    1:30 default here) and the margin it implies, not a risk-of-loss budget. Sizing is
    therefore NOT risk_pct-driven like simulate_bracket_portfolio: each new signal gets
    an equal share of whatever margin capacity is still free that day (equity *
    max_leverage - already-committed notional of open positions), mirroring
    simulate_concentrated_book's equal-split-among-today's-candidates approach but
    capped by margin instead of by a 1/8-of-equity fraction. Margin per position is
    fixed at entry (notional / max_leverage, held constant until the position closes)
    -- a standard simplification, real margin can move with mark-to-market P&L but
    modeling that adds complexity without changing the core leverage-ceiling story.

    Same configurable bracket exit (stop_sigma/rr_ratio/be_trigger_r/max_hold) as
    simulate_bracket_portfolio, since which exit logic maximizes raw growth is exactly
    what's being swept on top of this sizing rule -- unconstrained-drawdown growth
    can favor a different SL/TP than a drawdown-conscious challenge account would.
    """
    ind = _precompute_indicators(panel, tickers, lookback, k)
    all_dates = panel.loc[start:end].index

    equity = initial_equity
    open_notional = 0.0
    positions: dict[str, _BracketPosition] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]

            equity += pos.shares * (price_t - pos.last_price)
            pos.last_price = price_t
            pos.days_held += 1

            if not pos.be_moved and be_trigger_r > 0:
                trigger_dist = be_trigger_r * pos.stop_distance
                if (price_t - pos.entry_price) >= trigger_dist:
                    pos.stop_price = pos.entry_price
                    pos.be_moved = True

            exit_now, reason = False, None
            has_tp = pos.tp_price is not None
            if price_t <= pos.stop_price:
                exit_now, reason = True, ("breakeven" if pos.be_moved else "stop_loss")
            elif has_tp and price_t >= pos.tp_price:
                exit_now, reason = True, "take_profit"
            elif pos.days_held >= max_hold:
                exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (price_t - pos.entry_price)
                trades.append({
                    "ticker": t, "direction": "long", "entry_date": pos.entry_date, "exit_date": date,
                    "entry_price": pos.entry_price, "exit_price": price_t, "shares": pos.shares,
                    "days_held": pos.days_held, "pnl_dollars": pnl_dollars,
                    "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price), "reason": reason,
                })
                open_notional -= pos.shares * pos.entry_price
                del positions[t]

        regime_ok = True if regime_filter is None else bool(regime_filter.get(date, False))

        candidates = []
        if regime_ok:
            for t in tickers:
                if t in positions or t not in ind:
                    continue
                data = ind[t]
                if date not in data["price"].index:
                    continue
                price_t = data["price"].loc[date]
                std_t, lower_t = data["std"].loc[date], data["lower"].loc[date]
                if pd.isna(std_t) or std_t == 0 or pd.isna(lower_t):
                    continue
                if price_t < lower_t:
                    candidates.append((t, price_t, std_t))

        if candidates:
            available_margin = max(0.0, equity * max_leverage - open_notional)
            notional_per_candidate = available_margin / len(candidates)
            for t, price_t, std_t in candidates:
                shares = notional_per_candidate / price_t
                if shares <= 0:
                    continue
                stop_distance = stop_sigma * std_t
                stop_price = price_t - stop_distance
                tp_price = (price_t + rr_ratio * stop_distance) if rr_ratio else None
                positions[t] = _BracketPosition(
                    ticker=t, direction=1, shares=shares, entry_price=price_t,
                    entry_date=date, last_price=price_t, stop_price=stop_price, tp_price=tp_price,
                    stop_distance=stop_distance, risk_dollars=0.0,
                )
                open_notional += shares * price_t

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades


def simulate_leveraged_trailing_book(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    initial_equity: float,
    max_leverage: float = 30.0,
    regime_filter: pd.Series | None = None,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    trail_mult: float = 3.0,
) -> tuple[pd.Series, list[dict]]:
    """Trailing-stop exit (std-dev type only, see simulate_trailing_bracket_portfolio)
    combined with simulate_leveraged_book's margin/leverage-based sizing instead of
    risk_pct sizing -- same rationale as simulate_leveraged_book: a no-drawdown-
    constraint account should let the exit-logic sweep consider trailing stops too,
    not just fixed brackets."""
    ind = _precompute_indicators(panel, tickers, lookback, k)
    all_dates = panel.loc[start:end].index

    equity = initial_equity
    open_notional = 0.0
    positions: dict[str, _TrailingPosition] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]

            equity += pos.shares * (price_t - pos.last_price)
            pos.last_price = price_t
            pos.days_held += 1
            pos.highest_price = max(pos.highest_price, price_t)

            std_t = ind[t]["std"].get(date)
            if pd.notna(std_t) and std_t > 0:
                candidate_stop = pos.highest_price - trail_mult * std_t
                pos.stop_price = max(pos.stop_price, candidate_stop)

            exit_now, reason = False, None
            if price_t <= pos.stop_price:
                exit_now = True
                reason = "trailing_stop" if pos.stop_price > pos.entry_price else "stop_loss"
            elif pos.days_held >= max_hold:
                exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (price_t - pos.entry_price)
                trades.append({
                    "ticker": t, "direction": "long", "entry_date": pos.entry_date, "exit_date": date,
                    "entry_price": pos.entry_price, "exit_price": price_t, "shares": pos.shares,
                    "days_held": pos.days_held, "pnl_dollars": pnl_dollars,
                    "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price), "reason": reason,
                })
                open_notional -= pos.shares * pos.entry_price
                del positions[t]

        regime_ok = True if regime_filter is None else bool(regime_filter.get(date, False))

        candidates = []
        if regime_ok:
            for t in tickers:
                if t in positions or t not in ind:
                    continue
                data = ind[t]
                if date not in data["price"].index:
                    continue
                price_t = data["price"].loc[date]
                std_t, lower_t = data["std"].loc[date], data["lower"].loc[date]
                if pd.isna(std_t) or std_t == 0 or pd.isna(lower_t):
                    continue
                if price_t < lower_t:
                    candidates.append((t, price_t, std_t))

        if candidates:
            available_margin = max(0.0, equity * max_leverage - open_notional)
            notional_per_candidate = available_margin / len(candidates)
            for t, price_t, std_t in candidates:
                shares = notional_per_candidate / price_t
                if shares <= 0:
                    continue
                positions[t] = _TrailingPosition(
                    ticker=t, shares=shares, entry_price=price_t, entry_date=date, last_price=price_t,
                    stop_price=price_t - trail_mult * std_t, highest_price=price_t, risk_dollars=0.0,
                )
                open_notional += shares * price_t

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades


def simulate_concentrated_book(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    book_equity: float,
    regime_filter: pd.Series | None = None,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    stop_sigma: float = config.STOP_LOSS_SIGMA,
    be_trigger_r: float = 0.25,
    max_position_frac: float = 0.125,
) -> tuple[pd.Series, list[dict]]:
    """Concentrated, equal-weight-among-today's-signals position sizing for a single
    "book" (one market's capital pool) -- an alternative to simulate_bracket_portfolio's
    risk-based sizing, requested as a comparison against an external reference's
    scheme: today's book equity is split equally across however many NEW entry
    signals fire on the same day in this book (1/N), capped at `max_position_frac`
    (1/8 default) of the book's current equity per position. Same entry rule (band
    breach + regime filter) and exit rule (3.0-sigma SL, no fixed TP, breakeven-move)
    as the validated final config -- only the position-sizing mechanism differs, to
    isolate its effect. Two independent books (e.g. one call per market) are meant to
    be combined by the caller (e.g. summing two 50/50-split book equity curves).
    """
    ind = _precompute_indicators(panel, tickers, lookback, k)
    all_dates = panel.loc[start:end].index

    equity = book_equity
    positions: dict[str, _BracketPosition] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]

            equity += pos.shares * (price_t - pos.last_price)
            pos.last_price = price_t
            pos.days_held += 1

            if not pos.be_moved:
                trigger_dist = be_trigger_r * pos.stop_distance
                if (price_t - pos.entry_price) >= trigger_dist:
                    pos.stop_price = pos.entry_price
                    pos.be_moved = True

            exit_now, reason = False, None
            if price_t <= pos.stop_price:
                exit_now, reason = True, ("breakeven" if pos.be_moved else "stop_loss")
            elif pos.days_held >= max_hold:
                exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (price_t - pos.entry_price)
                trades.append({
                    "ticker": t, "direction": "long", "entry_date": pos.entry_date, "exit_date": date,
                    "entry_price": pos.entry_price, "exit_price": price_t, "shares": pos.shares,
                    "days_held": pos.days_held, "pnl_dollars": pnl_dollars,
                    "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price), "reason": reason,
                })
                del positions[t]

        regime_ok = True if regime_filter is None else bool(regime_filter.get(date, False))

        candidates = []
        if regime_ok:
            for t in tickers:
                if t in positions or t not in ind:
                    continue
                data = ind[t]
                if date not in data["price"].index:
                    continue
                price_t = data["price"].loc[date]
                std_t, lower_t = data["std"].loc[date], data["lower"].loc[date]
                if pd.isna(std_t) or std_t == 0 or pd.isna(lower_t):
                    continue
                if price_t < lower_t:
                    candidates.append((t, price_t, std_t))

        if candidates:
            position_frac = min(1.0 / len(candidates), max_position_frac)
            for t, price_t, std_t in candidates:
                stop_distance = stop_sigma * std_t
                position_value = equity * position_frac
                shares = position_value / price_t
                if shares <= 0:
                    continue
                positions[t] = _BracketPosition(
                    ticker=t, direction=1, shares=shares, entry_price=price_t,
                    entry_date=date, last_price=price_t, stop_price=price_t - stop_distance,
                    tp_price=None, stop_distance=stop_distance, risk_dollars=0.0,
                )

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades
