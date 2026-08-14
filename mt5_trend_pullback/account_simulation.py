"""Dollar-denominated account simulation on top of strategy.backtest's
price-only trades: turns each market's independently-simulated trades (each
already carrying an exact `r_multiple` - see strategy/backtest.py) into a
single compounding equity curve that honours the live bot's real portfolio
rules (config.py): 1% of equity risked per trade, max 3 concurrent
positions across all 5 markets, max 1 position per market at a time.

Why this needs its own engine rather than just concatenating trades: R = P&L
in units of "amount risked" is independent of dollar sizing (it only depends
on price action, already correctly simulated per-market by
strategy.backtest.simulate_trades), but the DOLLAR amount at risk on each
trade depends on account equity *at the moment that trade opens*, which
itself depends on every earlier trade's outcome and on which trades were
even allowed to open at all under the 3-concurrent-position cap - a
genuinely sequential, cross-market dependency that a per-market or
naively-pooled backtest cannot capture.

Simplification (disclosed): position sizing uses REALIZED balance only
(equity is updated when a trade closes, not continuously marked-to-market
while positions are open) - the live bot's `acc.equity` from MT5 technically
includes floating P&L of open positions too, but modelling that exactly
would require a full joint bar-by-bar replay across all 5 markets instead of
this trade-list-level engine. With <=3 small (1%-risk) concurrent positions
this difference is second-order. Also ignored: lot-size rounding (the bot
always rounds DOWN to the broker's volume step - strategy.py/CHANGELOG.md -
so real risk taken is usually a hair UNDER the 1% target, never over; this
sim's continuous sizing is a reasonable, slightly-conservative idealisation
of that)."""

import heapq

import numpy as np
import pandas as pd


def simulate_account(
    trades_by_market: dict[str, pd.DataFrame],
    starting_equity: float = 100_000.0,
    risk_pct: float = 0.01,
    max_concurrent: int = 3,
    risk_weight_by_market: dict[str, float] | None = None,
) -> dict:
    """`risk_weight_by_market`: optional per-market multiplier on `risk_pct`
    (e.g. {"XAUUSD": 1.2, "USDCAD": 0.5}) for testing an uneven risk split
    across markets instead of the uniform default (every market implicitly
    weight 1.0). Applied at the point risk_dollars is computed, so it stays
    inside the compounding chain rather than being a post-hoc rescale."""
    risk_weight_by_market = risk_weight_by_market or {}
    all_trades = []
    for market, df in trades_by_market.items():
        if df.empty:
            continue
        cols = ["entry_time", "exit_time", "r_multiple", "exit_reason"]
        optional_cols = [c for c in ("initial_risk", "entry_price") if c in df.columns]
        d = df[cols + optional_cols].copy()
        d["market"] = market
        d = d.dropna(subset=["r_multiple"])  # guards a degenerate (zero) initial_risk, mirrors BacktestConfig.min_atr's intent
        all_trades.append(d)

    if not all_trades:
        return {
            "trades": pd.DataFrame(), "equity_curve": pd.DataFrame(columns=["time", "equity"]),
            "final_equity": starting_equity, "n_taken": 0, "n_skipped": 0,
        }

    pool = pd.concat(all_trades, ignore_index=True).sort_values("entry_time").reset_index(drop=True)

    equity = starting_equity
    open_by_market: dict[str, tuple] = {}  # market -> (exit_time, risk_dollars, r_multiple)
    exit_heap: list[tuple[pd.Timestamp, str]] = []  # (exit_time, market), min-heap by time

    accepted_rows = []
    equity_points = [(pool["entry_time"].iloc[0], equity)]
    n_skipped = 0

    def settle_up_to(t: pd.Timestamp) -> None:
        nonlocal equity
        while exit_heap and exit_heap[0][0] <= t:
            exit_time, market = heapq.heappop(exit_heap)
            if market not in open_by_market or open_by_market[market][0] != exit_time:
                continue  # already settled (can happen if a market had a later re-check queued twice - defensive, not expected)
            _, risk_dollars, r_multiple = open_by_market.pop(market)
            pnl = risk_dollars * r_multiple
            equity += pnl
            equity_points.append((exit_time, equity))

    for _, row in pool.iterrows():
        t_entry = row["entry_time"]
        settle_up_to(t_entry)

        if row["market"] in open_by_market:
            n_skipped += 1  # bot: "bereits Position offen -- uebersprungen"
            continue
        if len(open_by_market) >= max_concurrent:
            n_skipped += 1  # bot: "Max. offene Positionen erreicht -- uebersprungen"
            continue

        risk_dollars = equity * risk_pct * risk_weight_by_market.get(row["market"], 1.0)
        open_by_market[row["market"]] = (row["exit_time"], risk_dollars, row["r_multiple"])
        heapq.heappush(exit_heap, (row["exit_time"], row["market"]))
        accepted_row = {
            "market": row["market"], "entry_time": t_entry, "exit_time": row["exit_time"],
            "exit_reason": row["exit_reason"], "r_multiple": row["r_multiple"],
            "risk_dollars": risk_dollars, "equity_at_entry": equity,
        }
        for c in ("initial_risk", "entry_price"):
            if c in row.index:
                accepted_row[c] = row[c]
        accepted_rows.append(accepted_row)

    settle_up_to(pd.Timestamp.max.tz_localize("UTC"))  # flush every still-open position at the end

    taken = pd.DataFrame(accepted_rows)
    if not taken.empty:
        # risk_dollars was locked in at entry time, so per-trade pnl is just
        # risk_dollars * r_multiple regardless of settlement order; the
        # running equity total itself (equity_points, built during the walk
        # above) is what's order-sensitive, and is already correct.
        taken["pnl"] = taken["risk_dollars"] * taken["r_multiple"]

    equity_curve = pd.DataFrame(equity_points, columns=["time", "equity"]).drop_duplicates(subset="time", keep="last")

    return {
        "trades": taken,
        "equity_curve": equity_curve,
        "final_equity": equity,
        "n_taken": len(taken),
        "n_skipped": n_skipped,
    }


def account_stats(sim: dict, starting_equity: float = 100_000.0) -> dict:
    trades, curve = sim["trades"], sim["equity_curve"]
    if trades.empty:
        return {
            "n_trades": 0, "n_skipped": sim["n_skipped"], "final_equity": starting_equity,
            "total_return": 0.0, "win_rate": np.nan, "profit_factor": np.nan,
            "max_drawdown_pct": 0.0, "max_drawdown_usd": 0.0, "avg_win_usd": np.nan, "avg_loss_usd": np.nan,
        }

    wins = trades["pnl"] > 0
    gross_win = trades.loc[wins, "pnl"].sum()
    gross_loss = -trades.loc[~wins, "pnl"].sum()

    eq = curve.sort_values("time")["equity"]
    running_max = eq.cummax()
    dd = eq - running_max
    dd_pct = eq / running_max - 1.0

    return {
        "n_trades": len(trades), "n_skipped": sim["n_skipped"],
        "final_equity": sim["final_equity"],
        "total_return": sim["final_equity"] / starting_equity - 1.0,
        "win_rate": wins.mean(),
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else np.inf,
        "max_drawdown_pct": dd_pct.min() if len(dd_pct) else 0.0,
        "max_drawdown_usd": dd.min() if len(dd) else 0.0,
        "avg_win_usd": trades.loc[wins, "pnl"].mean() if wins.any() else np.nan,
        "avg_loss_usd": trades.loc[~wins, "pnl"].mean() if (~wins).any() else np.nan,
    }
