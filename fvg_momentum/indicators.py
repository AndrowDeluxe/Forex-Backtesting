"""HTF (1H) structural reference levels for the FVG-momentum strategy:
EMA-20, EMA-50, and a rolling 30-period Point of Control approximated via a
NumPy histogram of closing prices - same POC method already used in
auction_playbook/indicators.py::volume_profile's bin-with-max-count logic,
reused here (on price alone, no volume weighting - the source paper's own
"NumPy histogram" description doesn't mention volume either) for consistency
rather than inventing a second POC convention in this repo."""

import numpy as np
import pandas as pd


def compute_htf_levels(h1: pd.DataFrame, poc_window: int = 30, poc_bins: int = 20) -> pd.DataFrame:
    out = pd.DataFrame(index=h1.index)
    out["ema20"] = h1["Close"].ewm(span=20, adjust=False).mean()
    out["ema50"] = h1["Close"].ewm(span=50, adjust=False).mean()

    close = h1["Close"].to_numpy()
    poc = np.full(len(close), np.nan)
    for i in range(poc_window, len(close)):
        window = close[i - poc_window : i]
        hist, edges = np.histogram(window, bins=poc_bins)
        top_bin = int(hist.argmax())
        poc[i] = (edges[top_bin] + edges[top_bin + 1]) / 2
    out["poc"] = poc
    return out
