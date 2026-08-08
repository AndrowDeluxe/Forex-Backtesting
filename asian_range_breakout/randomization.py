"""Structure-preserving (dwell-preserving) randomization inference for
post-hoc trade filters, per the critique behind Patel et al.'s "Structure-
Preserving Randomization Inference": naive permutation/Reality-Check tests
that reshuffle trade identity or order destroy the run-length ("dwell")
structure of the filter itself - a filter that just happens to produce a
handful of long quiet-vs-active stretches can look "significant" against a
shuffle that ignores its own footprint entirely. These two null generators
instead only randomize WHEN the filter's keep/drop pattern falls in
calendar time, holding its own dwell structure (run count, run lengths,
total kept count) exactly fixed:

- rotation: circular-shift the boolean keep/drop sequence by a random
  offset (block-bootstrap style) - every run keeps its exact length, only
  its phase relative to calendar time changes.
- run_permutation: decompose the sequence into its runs (constant-value
  stretches), shuffle the ORDER of the runs, reassemble - same run count,
  same individual run lengths, same total kept count, but runs can now
  land next to different neighbors than they originally did.

Either way, the null answers: "would a filter with exactly this footprint
(how often it turns on, how long each on/off stretch runs) have looked
this good if it had been triggered by an arbitrary, signal-blind process
instead of by the actual indicator (ADX, trend, delay, Silver, ...)?" If
the real filter's metric doesn't clear that null distribution, its
apparent edge is plausibly just this exposure shape, not genuine
selection skill.
"""

import numpy as np
import pandas as pd


def _runs(mask: np.ndarray) -> list[tuple[bool, int]]:
    """Decomposes a boolean array into (value, run_length) tuples, in order."""
    if len(mask) == 0:
        return []
    runs = []
    current = mask[0]
    length = 1
    for v in mask[1:]:
        if v == current:
            length += 1
        else:
            runs.append((current, length))
            current = v
            length = 1
    runs.append((current, length))
    return runs


def rotation_shuffle(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    n = len(mask)
    if n < 2:
        return mask.copy()
    k = int(rng.integers(1, n))
    return np.roll(mask, k)


def run_permutation_shuffle(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    runs = _runs(mask)
    order = rng.permutation(len(runs))
    out = np.empty(len(mask), dtype=bool)
    pos = 0
    for i in order:
        value, length = runs[i]
        out[pos : pos + length] = value
        pos += length
    return out


def dwell_preserving_test(
    trades: pd.DataFrame,
    mask: pd.Series,
    metric_fn,
    n_shuffles: int = 1000,
    seed: int = 42,
) -> dict:
    """Runs both null generators against `mask` (boolean, aligned to
    `trades`, assumed already chronologically sorted by entry_time) and
    reports where the actual filter's metric falls in each null
    distribution. `metric_fn(sub_trades_df) -> float` (e.g. profit factor);
    may return inf/nan for degenerate subsets (kept for the p-value
    comparison, excluded from the reported null mean/std/percentiles)."""
    rng = np.random.default_rng(seed)
    mask_arr = mask.to_numpy()
    actual_metric = metric_fn(trades[mask_arr])

    out = {"actual_metric": actual_metric, "n_kept": int(mask_arr.sum()), "n_total": len(mask_arr)}
    for method_name, shuffle_fn in [("rotation", rotation_shuffle), ("run_permutation", run_permutation_shuffle)]:
        nulls = np.empty(n_shuffles)
        for i in range(n_shuffles):
            null_mask = shuffle_fn(mask_arr, rng)
            nulls[i] = metric_fn(trades[null_mask])
        finite = nulls[np.isfinite(nulls)]
        p_value = float(np.mean(nulls >= actual_metric)) if np.isfinite(actual_metric) else float("nan")
        out[method_name] = {
            "null_mean": float(np.mean(finite)) if len(finite) else float("nan"),
            "null_std": float(np.std(finite)) if len(finite) else float("nan"),
            "null_p05": float(np.percentile(finite, 5)) if len(finite) else float("nan"),
            "null_p95": float(np.percentile(finite, 95)) if len(finite) else float("nan"),
            "p_value": p_value,
            "n_valid_shuffles": int(len(finite)),
        }
    return out
