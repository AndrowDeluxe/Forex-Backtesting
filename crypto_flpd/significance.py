"""Structure-preserving (dwell-preserving) randomization test for SIGNAL
TIMING, not trade-keep/drop filtering. asian_range_breakout.randomization.
dwell_preserving_test answers "would this filter's keep/drop pattern have
looked this good against a same-footprint random placement" for a post-hoc
trade filter - it does not fit a strategy where the boolean/signed signal
itself changes WHEN trades happen (Baustein 1's Hurst-collapse exit timing,
Baustein 3's Psi entry timing). This module reuses the EXACT same
dwell-preserving shuffle primitives (rotation_shuffle, run_permutation_
shuffle - same run-count/run-length-preserving null), but re-runs the FULL
strategy simulation under each shuffled signal instead of subsetting an
already-simulated trade list, then compares the real signal's profit
factor against that null distribution."""

import numpy as np
import pandas as pd

from asian_range_breakout.randomization import rotation_shuffle, run_permutation_shuffle


def signal_timing_significance(signal: pd.Series, simulate_fn, n_shuffles: int = 500, seed: int = 42) -> dict:
    """`simulate_fn(shuffled_signal: pd.Series) -> dict` must re-run the
    full strategy simulation with `signal` REPLACED by the shuffled version
    (holding every other rule/parameter fixed) and return a dict containing
    at least "profit_factor" and "n_trades" - e.g. a closure over
    crypto_flpd.engine.simulate_ema_cross_with_hurst_exit's `hurst_collapse`
    argument, or simulate_flpd's `entry_target_override` argument.

    `signal` may be boolean (Hurst-collapse timing) or a signed {-1,0,1}
    array (Psi entry timing) - both rotation_shuffle (a plain np.roll) and
    run_permutation_shuffle (equality-based run decomposition) work
    unchanged on either dtype."""
    rng = np.random.default_rng(seed)
    signal_arr = signal.to_numpy()

    actual_result = simulate_fn(signal)
    actual_pf = actual_result["profit_factor"]

    out = {"actual_profit_factor": actual_pf, "actual_n_trades": actual_result["n_trades"]}
    for method_name, shuffle_fn in [("rotation", rotation_shuffle), ("run_permutation", run_permutation_shuffle)]:
        nulls = np.empty(n_shuffles)
        for i in range(n_shuffles):
            shuffled_arr = shuffle_fn(signal_arr, rng)
            shuffled_series = pd.Series(shuffled_arr, index=signal.index)
            result = simulate_fn(shuffled_series)
            nulls[i] = result["profit_factor"]
        finite = nulls[np.isfinite(nulls)]
        p_value = float(np.mean(nulls >= actual_pf)) if np.isfinite(actual_pf) else float("nan")
        out[method_name] = {
            "null_mean": float(np.mean(finite)) if len(finite) else float("nan"),
            "null_std": float(np.std(finite)) if len(finite) else float("nan"),
            "null_p05": float(np.percentile(finite, 5)) if len(finite) else float("nan"),
            "null_p95": float(np.percentile(finite, 95)) if len(finite) else float("nan"),
            "p_value": p_value,
            "n_valid_shuffles": int(len(finite)),
        }
    return out
