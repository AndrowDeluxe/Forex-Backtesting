"""Rolling L1-logistic spillover model: for each rebalancing month and
target pair, predicts P(next-1-month return > 0) from the OTHER 6 pairs'
momentum signals at the same lookback (L1 penalty for sparsity, matching
the paper's description). Mirrors the paper's own stated setup (see
knowledge/resources/cross-asset-momentum-spillover.md): rolling retrain on
every rebalancing date, regularization grid {0.05, 0.1, 0.2} selected via
TimeSeriesSplit, training window max(2*lookback, 252 trading days) - just
on a 7-pair FX-only universe instead of 42 cross-asset futures."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit

REG_GRID = [0.05, 0.1, 0.2]


def forward_returns(closes: pd.DataFrame, horizon: int = 21) -> pd.DataFrame:
    """horizon-trading-day forward return per pair, NaN for the last
    `horizon` rows (future not yet observed)."""
    return closes.shift(-horizon) / closes - 1.0


def monthly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last trading day of each calendar month present in `index`."""
    s = pd.Series(index.to_numpy(), index=index)
    last_per_month = s.groupby([index.year, index.month]).max()
    return pd.DatetimeIndex(sorted(last_per_month.to_numpy()))


def _best_C(X: np.ndarray, y: np.ndarray, seed: int = 0) -> float:
    """Picks a regularization strength from REG_GRID via TimeSeriesSplit CV
    accuracy - degrades to the middle grid value when too few samples/
    classes for CV (early in the sample, or a quiet training window)."""
    n_splits = min(3, max(1, len(y) // 20))
    if n_splits < 2 or len(np.unique(y)) < 2:
        return REG_GRID[len(REG_GRID) // 2]
    tscv = TimeSeriesSplit(n_splits=n_splits)
    best_c, best_score = REG_GRID[len(REG_GRID) // 2], -np.inf
    for c in REG_GRID:
        scores = []
        for train_idx, test_idx in tscv.split(X):
            y_train = y[train_idx]
            if len(np.unique(y_train)) < 2:
                continue
            clf = LogisticRegression(l1_ratio=1.0, solver="liblinear", C=c, random_state=seed)
            clf.fit(X[train_idx], y_train)
            scores.append(clf.score(X[test_idx], y[test_idx]))
        if scores:
            avg = float(np.mean(scores))
            if avg > best_score:
                best_score, best_c = avg, c
    return best_c


def rolling_spillover_predictions(
    momentum_df: pd.DataFrame,
    fwd_returns: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    horizon: int,
    min_train_window: int,
    min_train_samples: int = 60,
    seed: int = 0,
) -> pd.DataFrame:
    """momentum_df / fwd_returns: DataFrame (date x pair), same index,
    ALREADY the single lookback's signal (caller loops over lookbacks).
    Returns a DataFrame (rebalance_dates x pair) of predicted P(next-month
    return > 0), NaN wherever there isn't enough clean trailing history.

    No-lookahead: training row at position d is only used if d + horizon
    <= the rebalance position (i.e. that row's forward-return LABEL is
    already fully observed by the rebalance date) - a plain `.loc[:dt]`
    slice would leak up to `horizon` days of future information into
    training, this explicitly guards against that."""
    dates = momentum_df.index
    pairs = list(momentum_df.columns)
    pos_of_date = {d: i for i, d in enumerate(dates)}

    mom = momentum_df.to_numpy()
    fwd = fwd_returns.reindex(dates).to_numpy()
    y_all = np.where(np.isnan(fwd), np.nan, (fwd > 0).astype(float))

    out = pd.DataFrame(index=rebalance_dates, columns=pairs, dtype=float)

    for target_j, target in enumerate(pairs):
        other_idx = [j for j in range(len(pairs)) if j != target_j]
        X_all = mom[:, other_idx]
        y_target = y_all[:, target_j]

        for dt in rebalance_dates:
            if dt not in pos_of_date:
                continue
            i = pos_of_date[dt]
            last_train_pos = i - horizon
            if last_train_pos < 0:
                continue
            start_train_pos = max(0, last_train_pos - min_train_window + 1)
            Xtr = X_all[start_train_pos : last_train_pos + 1]
            ytr = y_target[start_train_pos : last_train_pos + 1]
            valid = ~(np.isnan(Xtr).any(axis=1) | np.isnan(ytr))
            Xtr, ytr = Xtr[valid], ytr[valid]
            if len(ytr) < min_train_samples or len(np.unique(ytr)) < 2:
                continue

            x_today = X_all[i]
            if np.isnan(x_today).any():
                continue

            C = _best_C(Xtr, ytr, seed=seed)
            clf = LogisticRegression(l1_ratio=1.0, solver="liblinear", C=C, random_state=seed)
            clf.fit(Xtr, ytr)
            out.loc[dt, target] = clf.predict_proba(x_today.reshape(1, -1))[0, 1]

    return out
