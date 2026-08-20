"""Verifies gold_smc_htf_ltf.live_signal's TRAILING-LOOKBACK-WINDOW signal
reads against the FULL-HISTORY backtest pipeline, same discipline as
scripts/verify_btc_ema_cross_live_scan.py: "run the bot's --backfill
command and check its trade list matches your backtest. If they disagree,
stop and fix - never run logic you haven't verified."

Unlike btc_ema_cross's incremental day-by-day state machine, this
pipeline is memoryless GIVEN SUFFICIENT LOOKBACK (no state carried between
calls - a bridge just re-reads the rules fresh each poll). The risk here
isn't a state bug, it's TRUNCATION: does live_signal.py's LOOKBACK_DAYS=90
trailing window produce the IDENTICAL signal at a given bar as the full,
multi-year backtest history would at that same timestamp? Tests this
directly: compute the reference signal ONCE over the full history, then
for many sampled cutoff dates, slice the SAME already-fetched data down to
a 90-day trailing window (exactly what a live poll would see) and diff.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.live_signal import CONT_KWARGS, LOOKBACK_DAYS, REV_KWARGS
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal

FULL_START, FULL_END = "2024-01-01", "2026-08-01"
N_SAMPLE_SIGNAL_DAYS = 60   # alle Tage mit einem echten Signal (begrenzt auf die letzten N)
N_SAMPLE_RANDOM_DAYS = 100  # zufaellige zusaetzliche Tage (auch "kein Signal"-Faelle)
RNG_SEED = 7


def check_pipeline(name: str, run_pipeline, kwargs: dict, ltf_key: str, full_frames: dict) -> None:
    print(f"\n{'='*90}\n{name}\n{'='*90}")
    full_merged = run_pipeline(full_frames["h4"], full_frames["h1"], full_frames[ltf_key], **({"trend_df": full_frames["m15"]} if ltf_key == "m5" else {}), **kwargs)
    ref_signal_bars = full_merged.index[full_merged["signal"] != 0]
    print(f"Vollhistorie: {len(full_merged)} Bars, {len(ref_signal_bars)} Signal-Bars insgesamt")

    rng = np.random.default_rng(RNG_SEED)
    signal_sample = list(ref_signal_bars[-N_SAMPLE_SIGNAL_DAYS:])
    all_bars = full_merged.index
    random_idx = rng.choice(len(all_bars), size=min(N_SAMPLE_RANDOM_DAYS, len(all_bars)), replace=False)
    random_sample = list(all_bars[random_idx])
    test_points = sorted(set(signal_sample + random_sample))
    # nur Punkte, die genug Vorlauf fuer ein volles Lookback-Fenster haben
    min_valid = all_bars.min() + pd.Timedelta(days=LOOKBACK_DAYS + 5)
    test_points = [t for t in test_points if t >= min_valid]
    print(f"Teste {len(test_points)} Cutoff-Zeitpunkte ({len(signal_sample)} Signal-Bars + Zufallsstichprobe)")

    mismatches = []
    for cutoff in test_points:
        window_start = cutoff - pd.Timedelta(days=LOOKBACK_DAYS)
        h4_w = full_frames["h4"][(full_frames["h4"].index >= window_start) & (full_frames["h4"].index <= cutoff)]
        h1_w = full_frames["h1"][(full_frames["h1"].index >= window_start) & (full_frames["h1"].index <= cutoff)]
        m15_w = full_frames["m15"][(full_frames["m15"].index >= window_start) & (full_frames["m15"].index <= cutoff)]
        ltf_w = full_frames[ltf_key][(full_frames[ltf_key].index >= window_start) & (full_frames[ltf_key].index <= cutoff)]

        kw = dict(kwargs)
        if ltf_key == "m5":
            windowed = run_pipeline(h4_w, h1_w, ltf_w, trend_df=m15_w, **kw)
        else:
            windowed = run_pipeline(h4_w, h1_w, ltf_w, **kw)
        if windowed.empty:
            mismatches.append((cutoff, "leeres Fenster", None, None))
            continue

        win_sig = int(windowed.iloc[-1]["signal"])
        ref_row = full_merged.loc[full_merged.index == cutoff]
        ref_sig = int(ref_row.iloc[0]["signal"]) if not ref_row.empty else None

        if win_sig != ref_sig:
            mismatches.append((cutoff, "signal", win_sig, ref_sig))

    n_ok = len(test_points) - len(mismatches)
    print(f"\n{n_ok}/{len(test_points)} Cutoff-Punkte stimmen exakt ueberein")
    if mismatches:
        print(f"MISMATCH bei {len(mismatches)} Punkten (erste 10):")
        for cutoff, kind, win_sig, ref_sig in mismatches[:10]:
            print(f"  {cutoff}: window_signal={win_sig}  ref_signal={ref_sig}  ({kind})")
        print("STOP - live_signal.py's LOOKBACK_DAYS nicht vertrauenswuerdig, bevor das verstanden/behoben ist.")
    else:
        print("MATCH - LOOKBACK_DAYS=%d reicht fuer identische Live-Signale." % LOOKBACK_DAYS)


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {FULL_START} -> {FULL_END} (fuer Referenz + alle Trailing-Fenster) ...")
    h4 = fetch_gold_h4(FULL_START, FULL_END)
    h1 = fetch_gold_h1(FULL_START, FULL_END)
    m15 = fetch_gold_m15(FULL_START, FULL_END)
    m5 = fetch_gold_m5(FULL_START, FULL_END)
    frames = {"h4": h4, "h1": h1, "m15": m15, "m5": m5}
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} M5={len(m5)}")

    check_pipeline("CONTINUATION (M5)", run_continuation, CONT_KWARGS, "m5", frames)
    check_pipeline("REVERSAL-KASKADE (M15)", run_reversal, REV_KWARGS, "m15", frames)


if __name__ == "__main__":
    main()
