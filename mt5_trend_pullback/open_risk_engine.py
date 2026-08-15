"""Aggregate open-risk-cap acceptance engine, replicating the mechanism used
by the OU-Modell's LIVE bridge (OU-Modell-MT5-Bridge/executor.py::
calc_open_risk() and execute_signal(), outside this repo but the canonical
source - see app_pages/risk_management.py for the in-repo writeup) rather
than mt5_trend_pullback.account_simulation's position-COUNT cap
(max_concurrent).

Mechanism: a new trade is accepted only if
  current_open_risk + this_trade's risk_dollars <= equity * max_total_risk_pct
where current_open_risk sums risk_dollars over every OPEN position whose
stop has NOT yet moved to breakeven (be_time is None, or be_time is still in
the future relative to the candidate's entry_time) - once a position reaches
breakeven it can no longer lose money (worst case ~0), so the live bridge
excludes it entirely from the risk sum (`pos.sl >= pos.price_open` check),
freeing capacity for new trades without waiting for that position to fully
close. This is the reason a sensible breakeven trigger matters here in a way
it didn't for the plain position-count cap: it directly controls how much
new-trade capacity a working position frees up before it exits.

Unlike account_simulation.simulate_account there is no explicit
max_concurrent count limit here - the OU bridge doesn't count positions,
only aggregate dollar risk, so however many positions fit under
max_total_risk_pct (given how many have already reached breakeven) may be
open at once. The existing one-position-per-market rule still applies
(matches the live bot's own per-market position limit, independent of the
portfolio risk cap).

Requires `strategy.backtest.BacktestConfig.breakeven_trigger_r` to be set
when the trades were simulated (see strategy/backtest.py's `be_time` field)
- without it, `be_time` is always None and every position counts as
"at risk" for its whole life, which degenerates to a plain aggregate-risk
cap with no breakeven relief.
"""

import heapq

import numpy as np
import pandas as pd


def simulate_open_risk_account(
    trades_by_market: dict[str, pd.DataFrame],
    starting_equity: float = 100_000.0,
    risk_pct: float = 0.005,
    max_total_risk_pct: float = 0.02,
    risk_weight_by_market: dict[str, float] | None = None,
) -> dict:
    risk_weight_by_market = risk_weight_by_market or {}
    all_trades = []
    for market, df in trades_by_market.items():
        if df.empty:
            continue
        cols = ["entry_time", "exit_time", "r_multiple", "exit_reason"]
        optional_cols = [c for c in ("initial_risk", "entry_price", "be_time") if c in df.columns]
        d = df[cols + optional_cols].copy()
        d["market"] = market
        d = d.dropna(subset=["r_multiple"])
        all_trades.append(d)

    if not all_trades:
        return {"trades": pd.DataFrame(), "equity_curve": pd.DataFrame(columns=["time", "equity"]),
                "final_equity": starting_equity, "n_taken": 0, "n_skipped": 0}

    pool = pd.concat(all_trades, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    if "be_time" not in pool.columns:
        pool["be_time"] = pd.NaT

    equity = starting_equity
    # market -> dict(exit_time, be_time, risk_dollars, r_multiple)
    open_positions: dict[str, dict] = {}
    exit_heap: list[tuple[pd.Timestamp, str]] = []

    accepted_rows = []
    equity_points = [(pool["entry_time"].iloc[0], equity)]
    n_skipped = 0

    def settle_up_to(t: pd.Timestamp) -> None:
        nonlocal equity
        while exit_heap and exit_heap[0][0] <= t:
            exit_time, market = heapq.heappop(exit_heap)
            pos = open_positions.get(market)
            if pos is None or pos["exit_time"] != exit_time:
                continue
            open_positions.pop(market, None)
            pnl = pos["risk_dollars"] * pos["r_multiple"]
            equity += pnl
            equity_points.append((exit_time, equity))

    def current_open_risk(as_of: pd.Timestamp) -> float:
        total = 0.0
        for pos in open_positions.values():
            be_time = pos["be_time"]
            if be_time is not None and not pd.isna(be_time) and be_time <= as_of:
                continue  # already at breakeven as of this moment - excluded, matching the live bridge
            total += pos["risk_dollars"]
        return total

    for _, row in pool.iterrows():
        t_entry = row["entry_time"]
        settle_up_to(t_entry)

        if row["market"] in open_positions:
            n_skipped += 1
            continue

        weight = risk_weight_by_market.get(row["market"], 1.0)
        risk_dollars = equity * risk_pct * weight
        open_risk_before = current_open_risk(t_entry)
        if open_risk_before + risk_dollars > equity * max_total_risk_pct:
            n_skipped += 1
            continue

        open_positions[row["market"]] = {
            "exit_time": row["exit_time"], "be_time": row.get("be_time"),
            "risk_dollars": risk_dollars, "r_multiple": row["r_multiple"],
        }
        heapq.heappush(exit_heap, (row["exit_time"], row["market"]))
        accepted_row = {
            "market": row["market"], "entry_time": t_entry, "exit_time": row["exit_time"],
            "exit_reason": row["exit_reason"], "r_multiple": row["r_multiple"],
            "risk_dollars": risk_dollars, "equity_at_entry": equity,
            "open_risk_at_entry": open_risk_before,
        }
        for c in ("initial_risk", "entry_price", "be_time"):
            if c in row.index:
                accepted_row[c] = row[c]
        accepted_rows.append(accepted_row)

    settle_up_to(pd.Timestamp.max.tz_localize("UTC") if pool["entry_time"].dt.tz is not None else pd.Timestamp.max)

    taken = pd.DataFrame(accepted_rows)
    if not taken.empty:
        taken["pnl"] = taken["risk_dollars"] * taken["r_multiple"]

    equity_curve = pd.DataFrame(equity_points, columns=["time", "equity"]).drop_duplicates(subset="time", keep="last")

    return {
        "trades": taken, "equity_curve": equity_curve,
        "final_equity": equity, "n_taken": len(taken), "n_skipped": n_skipped,
    }


def account_stats(sim: dict, starting_equity: float = 100_000.0) -> dict:
    trades, curve = sim["trades"], sim["equity_curve"]
    if trades.empty:
        return {"n_trades": 0, "n_skipped": sim["n_skipped"], "final_equity": starting_equity,
                "total_return": 0.0, "win_rate": np.nan, "profit_factor": np.nan,
                "max_drawdown_pct": 0.0, "max_drawdown_usd": 0.0, "avg_win_usd": np.nan, "avg_loss_usd": np.nan}

    wins = trades["pnl"] > 0
    gross_win = trades.loc[wins, "pnl"].sum()
    gross_loss = -trades.loc[~wins, "pnl"].sum()

    eq = curve.sort_values("time")["equity"]
    running_max = eq.cummax()
    dd = eq - running_max
    dd_pct = eq / running_max - 1.0

    return {
        "n_trades": len(trades), "n_skipped": sim["n_skipped"], "final_equity": sim["final_equity"],
        "total_return": sim["final_equity"] / starting_equity - 1.0,
        "win_rate": wins.mean(),
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else np.inf,
        "max_drawdown_pct": dd_pct.min() if len(dd_pct) else 0.0,
        "max_drawdown_usd": dd.min() if len(dd) else 0.0,
        "avg_win_usd": trades.loc[wins, "pnl"].mean() if wins.any() else np.nan,
        "avg_loss_usd": trades.loc[~wins, "pnl"].mean() if (~wins).any() else np.nan,
    }
