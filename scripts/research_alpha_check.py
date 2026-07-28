"""Does the strategy generate real alpha over simply buying and holding the
instrument, or is the earlier "indices/metals outperform" pattern just beta?
Uses the new Buy & Hold / Alpha metrics (ema_strategy.metrics.compute_metrics)
across all 11 instruments, out-of-sample, for the baseline and the combined
(+A+B+C) configuration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import INSTRUMENTS, load_all
from combined_strategy.pipeline import run_pipeline

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

IN_SAMPLE_FRAC = 0.7

CONFIGS = {
    "Baseline": dict(),
    "+A+B+C combined": dict(
        use_vwap_filter=True, vwap_theta_window_bars=250, vwap_theta_multiplier=1.0,
        use_session_confluence_filter=True, confluence_atr_mult=1.0,
        exit_on_adx_exhaustion=True, adx_exhaustion_entry_threshold=25.0, adx_exhaustion_confirm_bars=2,
    ),
}


def split(h4: pd.DataFrame, frac: float):
    cut = int(len(h4) * frac)
    return h4.iloc[:cut], h4.iloc[cut:]


def main():
    print("Loading real Dukascopy H4/D1/W1 history for all 11 instruments (cached after first run)...")
    data = load_all("2016-07-28", "2026-07-28")

    for config_name, params in CONFIGS.items():
        rows = []
        for key in INSTRUMENTS:
            h4, daily, weekly = data[key]
            _, h4_oos = split(h4, IN_SAMPLE_FRAC)
            _, _, _, m = run_pipeline(h4_oos, daily, weekly, **params)
            rows.append(
                {
                    "instrument": key,
                    "n_trades": m.get("Anzahl Trades", 0),
                    "strategy_return_%": m.get("Gesamtrendite %", float("nan")),
                    "buy_and_hold_%": m.get("Buy & Hold %", float("nan")),
                    "alpha_%": m.get("Alpha vs. Buy & Hold %", float("nan")),
                }
            )
        df = pd.DataFrame(rows).set_index("instrument")
        print(f"\n=== {config_name}, out-of-sample (last 30%) ===")
        print(df)
        print(f"mean alpha: {df['alpha_%'].mean():.1f}%, instruments with positive alpha: {(df['alpha_%'] > 0).sum()}/{len(df)}")


if __name__ == "__main__":
    main()
