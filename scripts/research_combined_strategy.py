"""Ablation test for the three ADX-VWAP-paper-derived additions to EMA S/R,
proposed after reviewing the paper's theoretical framework for ideas
transferable to a trend-following strategy:

  A) VWAP-overextension entry filter (Foundation 1)
  B) Prior-session-extreme confluence entry filter (Foundation 2)
  C) ADX-exhaustion exit (Foundation 3, applied as an exit instead of entry
     trigger since EMA S/R trades *with* the trend)

Tests each individually against the unmodified EMA S/R baseline, then all
three combined, across the 6 paper FX pairs plus Gold, Silver, S&P 500,
Nasdaq-100 and Oil. In-sample (first 70%) / out-of-sample (last 30%) split,
matching the existing ema_sr.py dashboard's convention - but on the full
~10-year Dukascopy history (H4/D1/W1), not yfinance's 730-day hourly cap.
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
    "Baseline (unmodified EMA S/R)": dict(),
    "+A VWAP-overextension filter": dict(use_vwap_filter=True, vwap_theta_window_bars=250, vwap_theta_multiplier=1.0),
    "+B Session-extreme confluence": dict(use_session_confluence_filter=True, confluence_atr_mult=1.0),
    "+C ADX-exhaustion exit": dict(exit_on_adx_exhaustion=True, adx_exhaustion_entry_threshold=25.0, adx_exhaustion_confirm_bars=2),
    "+A+B+C combined": dict(
        use_vwap_filter=True, vwap_theta_window_bars=250, vwap_theta_multiplier=1.0,
        use_session_confluence_filter=True, confluence_atr_mult=1.0,
        exit_on_adx_exhaustion=True, adx_exhaustion_entry_threshold=25.0, adx_exhaustion_confirm_bars=2,
    ),
}


def split(h4: pd.DataFrame, frac: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = int(len(h4) * frac)
    return h4.iloc[:cut], h4.iloc[cut:]


def main():
    print("Loading real Dukascopy H4/D1/W1 history for all 11 instruments (cached after first run)...")
    data = load_all("2016-07-28", "2026-07-28")

    is_rows, oos_rows = [], []
    for config_name, params in CONFIGS.items():
        for key in INSTRUMENTS:
            h4, daily, weekly = data[key]
            h4_is, h4_oos = split(h4, IN_SAMPLE_FRAC)

            _, _, _, m_is = run_pipeline(h4_is, daily, weekly, **params)
            _, _, _, m_oos = run_pipeline(h4_oos, daily, weekly, **params)

            is_rows.append({"config": config_name, "instrument": key, **m_is})
            oos_rows.append({"config": config_name, "instrument": key, **m_oos})
        print(f"  {config_name:35s} done")

    is_df = pd.DataFrame(is_rows)
    oos_df = pd.DataFrame(oos_rows)

    def summarize(df: pd.DataFrame, label: str):
        df = df.copy()
        df["Anzahl Trades"] = df["Anzahl Trades"].fillna(0)
        agg = df.groupby("config").agg(
            total_trades=("Anzahl Trades", "sum"),
            mean_trades_per_instrument=("Anzahl Trades", "mean"),
            mean_win_rate=("Trefferquote %", "mean"),
            mean_profit_factor=("Profit Factor", "mean"),
            median_profit_factor=("Profit Factor", "median"),
            mean_r_multiple=("Ø R-Multiple", "mean"),
            instruments_pf_above_1=("Profit Factor", lambda s: (s > 1).sum()),
        )
        print(f"\n=== {label} (aggregated across {oos_df['instrument'].nunique()} instruments) ===")
        print(agg.reindex(CONFIGS.keys()))

    summarize(is_df, "In-sample (first 70%)")
    summarize(oos_df, "Out-of-sample (last 30%)")

    print("\n=== Out-of-sample detail, all instruments, all configs ===")
    print(
        oos_df.pivot_table(
            index="instrument", columns="config",
            values="Ø R-Multiple", aggfunc="first",
        ).reindex(columns=list(CONFIGS.keys()))
    )


if __name__ == "__main__":
    main()
