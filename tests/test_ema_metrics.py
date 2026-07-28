import numpy as np
import pandas as pd

from ema_strategy.metrics import compute_metrics


def _equity_and_trades():
    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    equity = pd.Series([10_000 + i * 100 for i in range(10)], index=idx)  # 10_000 -> 10_900, +9%
    trades = pd.DataFrame(
        {
            "pnl": [100.0, -50.0],
            "r_multiple": [1.0, -0.5],
            "direction": ["LONG", "SHORT"],
        }
    )
    return equity, trades


def test_compute_metrics_without_price_series_has_no_benchmark_keys():
    equity, trades = _equity_and_trades()
    metrics = compute_metrics(trades, equity)
    assert "Buy & Hold %" not in metrics
    assert "Alpha vs. Buy & Hold %" not in metrics


def test_compute_metrics_with_price_series_computes_alpha():
    equity, trades = _equity_and_trades()
    price_idx = pd.date_range("2023-12-01", periods=40, freq="D")
    # Price doubles (+100%) over the full series, but only over the equity's
    # actual 10-day window it should be sliced to +10% (100 -> 110).
    price = pd.Series(np.linspace(100, 200, 40), index=price_idx)
    window_start_price = price.loc[price.index >= equity.index[0]].iloc[0]
    window_end_price = price.loc[price.index <= equity.index[-1]].iloc[-1]
    expected_bh_pct = (window_end_price / window_start_price - 1) * 100

    metrics = compute_metrics(trades, equity, price_series=price)
    total_return = (equity.iloc[-1] / 10_000 - 1) * 100

    assert metrics["Buy & Hold %"] == round(expected_bh_pct, 1)
    assert metrics["Alpha vs. Buy & Hold %"] == round(total_return - expected_bh_pct, 1)


def test_compute_metrics_empty_trades_still_reports_buy_and_hold():
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    equity = pd.Series([10_000.0] * 5, index=idx)
    trades = pd.DataFrame(columns=["pnl", "r_multiple", "direction"])
    price = pd.Series([100.0, 105.0, 110.0, 108.0, 112.0], index=idx)

    metrics = compute_metrics(trades, equity, price_series=price)
    assert metrics["Anzahl Trades"] == 0
    assert metrics["Buy & Hold %"] == round((112.0 / 100.0 - 1) * 100, 1)
    # No trades -> 0% strategy return -> alpha is just the negative of B&H.
    assert metrics["Alpha vs. Buy & Hold %"] == round(0.0 - metrics["Buy & Hold %"], 1)
