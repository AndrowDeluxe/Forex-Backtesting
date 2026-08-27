import numpy as np
import pandas as pd

from crypto_flpd.phases import completion_signal, psi_matrix, rolling_percentile_threshold


def test_completion_signal_fires_only_on_crossover_bar():
    idx = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
    # Monotonically rising close forces a bullish EMA(2)/EMA(3) crossover
    # early and then holds "above" - exactly one +1, no -1s in this window.
    close = pd.Series(np.linspace(100, 200, 10), index=idx)
    sig = completion_signal(close, fast=2, slow=3)
    assert (sig == 1.0).sum() == 1
    assert (sig == -1.0).sum() == 0


def test_psi_matrix_htf_signal_not_visible_before_htf_bar_closes():
    # One HTF (4h) bar spanning 4 LTF (1h) bars. The HTF completion fires
    # "at" the HTF bar's OPEN-time index (fetch_klines convention) - but it
    # must only become visible on the LTF timeline from the HTF bar's CLOSE
    # time onward, never at LTF bars that fall strictly inside the still-
    # forming HTF bar.
    htf_index = pd.date_range("2024-01-01 00:00", periods=3, freq="4h", tz="UTC")
    htf_completion = pd.Series([0.0, 1.0, 0.0], index=htf_index)  # fires in the 2nd HTF bar

    ltf_index = pd.date_range("2024-01-01 00:00", periods=12, freq="1h", tz="UTC")

    psi = psi_matrix(
        htf_completion, htf_bar_duration=pd.Timedelta("4h"), ltf_index=ltf_index,
        decay_lambda=0.0, lookback_bars=10,
    )

    htf_bar_2_open = htf_index[1]  # 04:00 - the bar whose completion=1.0
    htf_bar_2_close = htf_bar_2_open + pd.Timedelta("4h")  # 08:00

    still_forming = psi.loc[(psi.index >= htf_bar_2_open) & (psi.index < htf_bar_2_close)]
    assert (still_forming == 0.0).all(), "Psi leaked a not-yet-closed HTF bar's completion onto the LTF"

    after_close = psi.loc[psi.index >= htf_bar_2_close]
    assert (after_close == 1.0).all()


def test_rolling_percentile_threshold_uses_only_trailing_data():
    idx = pd.date_range("2024-01-01", periods=50, freq="D", tz="UTC")
    s = pd.Series(np.arange(50, dtype=float), index=idx)
    thresh = rolling_percentile_threshold(s, quantile=0.5, window=10, min_periods=10)
    # median of a strictly increasing trailing 10-window at position i
    # (0-indexed, using values [i-9..i]) is s[i] - 4.5
    assert np.isclose(thresh.iloc[20], s.iloc[20] - 4.5)
    # Appending future data must not change an already-computed past value.
    thresh_short = rolling_percentile_threshold(s.iloc[:25], quantile=0.5, window=10, min_periods=10)
    assert np.isclose(thresh.iloc[20], thresh_short.iloc[20])
