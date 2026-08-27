"""Kelly-criterion sizing test for ORB (Nasdaq/SP500, long-only + ADX>=25 +
per-asset weekday filter, atr_mult=1.0 / stop_atr_mult=2.0 - the same
confirmed baseline as orb_strategy/pipeline.py and research_orb_filter_bank.py).

Same f* = p - q/b convention (Kelly on R-multiples) already established for
this repo's OU-Modell (scripts/research_kelly_ou_model.py) and cls_practical
(scripts/research_cls_practical_kelly.py) - applied here for the first time
to ORB. R-multiple per trade = return_pct / stop_frac, stop_frac =
stop_atr_mult * atr_at_entry / entry_price - exactly the same
proportional-stop convention already used by research_orb_stress_test.py's
capital_growth_demo/monte_carlo_bootstrap (which is why that demo could only
ever report on ONE risk_pct - fixed 1% - never asked what Kelly would say
about that number).

Kelly is computed separately In-Sample (2016-2021) and Out-of-Sample
(2021-2026) for two reasons: (1) same IS-inform/OOS-confirm discipline as
every other ORB finding in this project, (2) Kelly is famously unstable
out of sample (it's a function of the FUTURE win-rate/payoff ratio, which
you don't actually know) - showing both makes that instability visible
instead of hiding it behind a single reassuring number.

The capital-growth demo then asks the practical question: sized off the
IS-derived half/quarter-Kelly fraction (the only ones knowable BEFORE
trading the OOS period), how would the actual OOS trade sequence have
grown, compared to the already-used flat risk_pct=1%? An OOS-derived Kelly
fraction is also shown for reference, but flagged as hindsight-only (not a
number a real trader could have used going in)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import calmar_ratio, max_drawdown

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
WEEKDAY_FILTER = {"NASDAQ": "Thursday", "SP500": "Monday"}
STOP_ATR_MULT = 2.0
CURRENT_RISK_PCT = 0.01  # what research_orb_stress_test.py's capital demo already uses


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _r_multiples(trades: pd.DataFrame) -> np.ndarray:
    stop_frac = STOP_ATR_MULT * trades["atr_at_entry"] / trades["entry_price"]
    return (trades["return_pct"] / stop_frac).to_numpy()


def kelly_stats(r: np.ndarray) -> dict:
    n = len(r)
    if n == 0:
        return {"n_trades": 0, "win_rate": float("nan"), "payoff_ratio_b": float("nan"), "kelly_f": float("nan"), "half_kelly_f": float("nan"), "quarter_kelly_f": float("nan")}
    wins, losses = r[r > 0], r[r <= 0]
    p = len(wins) / n
    q = 1 - p
    avg_win_r = wins.mean() if len(wins) else float("nan")
    avg_loss_r = losses.mean() if len(losses) else float("nan")
    b = avg_win_r / abs(avg_loss_r) if len(losses) and avg_loss_r != 0 else float("nan")
    kelly_f = p - q / b if b == b and b != 0 else float("nan")
    return {
        "n_trades": n, "win_rate": p, "avg_win_r": avg_win_r, "avg_loss_r": avg_loss_r,
        "payoff_ratio_b": b, "kelly_f": kelly_f,
        "half_kelly_f": kelly_f / 2 if kelly_f == kelly_f else float("nan"),
        "quarter_kelly_f": kelly_f / 4 if kelly_f == kelly_f else float("nan"),
    }


def print_kelly(label: str, s: dict):
    if s["n_trades"] == 0:
        print(f"  {label}: keine Trades.")
        return
    print(
        f"  {label}: n={s['n_trades']}, win_rate={s['win_rate']:.1%}, "
        f"avg_win={s['avg_win_r']:.2f}R, avg_loss={s['avg_loss_r']:.2f}R, b={s['payoff_ratio_b']:.2f}, "
        f"Kelly f*={s['kelly_f']:.1%}, half={s['half_kelly_f']:.1%}, quarter={s['quarter_kelly_f']:.1%}"
    )


def capital_demo(trades: pd.DataFrame, risk_pct: float, start_capital: float = 10_000.0) -> dict:
    t = trades.sort_values("entry_time")
    if t.empty or risk_pct <= 0:
        return {"end_equity": start_capital, "cagr": float("nan"), "max_dd": float("nan"), "calmar": float("nan")}
    equity = start_capital
    rows = []
    for _, row in t.iterrows():
        stop_frac = STOP_ATR_MULT * row["atr_at_entry"] / row["entry_price"]
        position_value = (equity * risk_pct) / stop_frac
        pnl = position_value * row["return_pct"]
        equity = max(equity + pnl, 0.0)  # a >100%-of-equity blow-up (possible at aggressive risk_pct) can't go negative
        rows.append({"entry_time": row["entry_time"], "equity": equity})
    curve = pd.DataFrame(rows).set_index("entry_time")["equity"]
    n_years = (t["entry_time"].max() - t["entry_time"].min()).days / 365.25
    cagr = (max(equity, 1e-9) / start_capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    running_max = curve.cummax()
    dd = (curve - running_max) / running_max
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else float("nan")
    return {"end_equity": equity, "cagr": cagr, "max_dd": max_dd, "calmar": calmar}


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 20} {name} {'=' * 20}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday=WEEKDAY_FILTER[name])
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)
    if trades.empty:
        print("Keine Trades.")
        return

    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    is_trades = trades[trades["entry_time"] < split_ts]
    oos_trades = trades[trades["entry_time"] >= split_ts]

    is_kelly = kelly_stats(_r_multiples(is_trades))
    oos_kelly = kelly_stats(_r_multiples(oos_trades))

    print("\nKelly-Statistik (auf R-Vielfachen, f* = p - q/b):")
    print_kelly("In-Sample  (2016-2021)", is_kelly)
    print_kelly("Out-of-Sample (2021-2026, NICHT was ein Trader vorher gewusst haette)", oos_kelly)

    print("\nKapital-Demo auf der Out-of-Sample-Handelsreihenfolge (Start 10.000, verschiedene risk_pct):")
    scenarios = {
        f"aktuell fest (risk_pct={CURRENT_RISK_PCT:.1%})": CURRENT_RISK_PCT,
    }
    if is_kelly["half_kelly_f"] == is_kelly["half_kelly_f"] and is_kelly["half_kelly_f"] > 0:
        scenarios[f"IS-Half-Kelly (bekannt VOR der OOS-Periode, {is_kelly['half_kelly_f']:.1%})"] = is_kelly["half_kelly_f"]
    if is_kelly["quarter_kelly_f"] == is_kelly["quarter_kelly_f"] and is_kelly["quarter_kelly_f"] > 0:
        scenarios[f"IS-Quarter-Kelly ({is_kelly['quarter_kelly_f']:.1%})"] = is_kelly["quarter_kelly_f"]
    if is_kelly["kelly_f"] == is_kelly["kelly_f"] and is_kelly["kelly_f"] > 0:
        scenarios[f"IS-Full-Kelly ({is_kelly['kelly_f']:.1%}) - zur Warnung, nicht als Empfehlung"] = is_kelly["kelly_f"]
    if oos_kelly["half_kelly_f"] == oos_kelly["half_kelly_f"] and oos_kelly["half_kelly_f"] > 0:
        scenarios[f"OOS-Half-Kelly (NUR im Rueckblick bekannt, {oos_kelly['half_kelly_f']:.1%})"] = oos_kelly["half_kelly_f"]

    for label, risk_pct in scenarios.items():
        r = capital_demo(oos_trades, risk_pct)
        print(
            f"  {label:<62} end={r['end_equity']:>12,.0f}  cagr={r['cagr']:>7.1%}  "
            f"max_dd={r['max_dd']:>7.1%}  calmar={r['calmar']:>5.2f}"
        )


def main():
    print("Loading NASDAQ + SP500 M15 ...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
