"""Regime-Untersuchung (chat 2026-08-20): warum performen Continuation/
Reversal-Kaskade in 2024-08/2026-08 gut, aber negativ im Walk-Forward
2016-2024? Hypothese aus Web-Recherche: Rekord-Zentralbankkaeufe (2022:
1136t, 2023: 1051t, 2024: 1045t - alle weit ueber dem 2010-2021-Schnitt
von 473t/Jahr, ausgeloest u.a. durch die Russland-Sanktionen 2022 und
strukturelle De-Dollarisierung, World Gold Council 2024) UND die
eigentliche Kursbeschleunigung erst ab Fruehjahr/Sommer 2024 (Ausbruch
$2200 Maerz -> $2400 April -> $2500 August -> $2685 September 2024, nach
dem initialen ATH-Ausbruch bereits im Dezember 2023). Zentralbankkaeufe
ALLEIN erklaeren die Zeitgrenze nicht sauber (2022-08/2024-08 war schon
ein Rekordkaeufe-Fenster, performte aber NEGATIV im Walk-Forward) - die
Hypothese wird daher hier direkt an eigenen Preisdaten getestet, nicht
nur an der Makro-Story: Distanz zum rollierenden Hoch (frische ATHs -
kein Overhead-Widerstand, "blue sky") und Trendstaerke (ADX) als
messbare, in Echtzeit berechenbare Proxys.

Ziel: einen konkreten, rueckwirkend testbaren Regimefilter finden, der
2024-08/2026-08 als "an" und moeglichst viel von 2016-2024 als "aus"
klassifiziert - Werkzeug fuer ein kuenftiges Kipp-Signal, nicht Grund,
die Strategie zu verwerfen (chat 2026-08-20: "die Vergangenheit ist
vergangen, aber die Zukunft kommt noch").
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.indicators import compute_adx
from strategy.metrics import summarize

pd.set_option("display.width", 160)

FULL_START, FULL_END = "2016-01-01", "2026-08-01"
SPREAD_BPS = 8.0

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)

REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)

SUB_PERIODS = [
    ("2016-01-01", "2018-08-01"), ("2018-08-01", "2020-08-01"),
    ("2020-08-01", "2022-08-01"), ("2022-08-01", "2024-08-01"),
    ("2024-08-01", "2026-08-01"),
]

ATH_WINDOW_DAYS = 504  # ~2 Handelsjahre
ADX_WINDOW = 14


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:>6.2f}  CAGR={s['cagr']:+.1%}"


def main():
    print(f"Fetching GOLD D1/H4/H1/M15/M5 {FULL_START} -> {FULL_END} ...")
    d1 = fetch_gold_d1(FULL_START, FULL_END)
    h4 = fetch_gold_h4(FULL_START, FULL_END)
    h1 = fetch_gold_h1(FULL_START, FULL_END)
    m15 = fetch_gold_m15(FULL_START, FULL_END)
    m5 = fetch_gold_m5(FULL_START, FULL_END)

    # ---- Regime-Kennzahlen auf D1 ----
    d1 = d1.copy()
    d1["rolling_ath"] = d1["close"].rolling(ATH_WINDOW_DAYS, min_periods=60).max()
    d1["ath_dist_pct"] = (d1["close"] - d1["rolling_ath"]) / d1["rolling_ath"] * 100
    d1 = compute_adx(d1, n=ADX_WINDOW)

    print("\n" + "=" * 100)
    print(f"REGIME-KENNZAHLEN PRO SUB-PERIODE (rollierendes {ATH_WINDOW_DAYS}-Tage-Hoch, ADX({ADX_WINDOW}) auf D1)")
    print("=" * 100)
    for sp_start, sp_end in SUB_PERIODS:
        sp = d1.loc[sp_start:sp_end]
        print(f"  {sp_start} -> {sp_end}:  median ATH-Distanz={sp['ath_dist_pct'].median():>7.2f}%   "
              f"%Tage <2% v. Hoch={((sp['ath_dist_pct'] > -2).mean() * 100):>5.1f}%   "
              f"median ADX={sp['adx'].median():>5.1f}   %Tage ADX>25={((sp['adx'] > 25).mean() * 100):>5.1f}%")

    # ---- Signale ueber den GESAMTEN Zeitraum erzeugen (finale, gesperrte Configs) ----
    print("\nGeneriere Signale ueber den vollen Zeitraum (gesperrte Configs, kein Retuning) ...")
    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_PIPELINE_KWARGS)
    rev_sig = run_reversal(h4, h1, m15, **REV_PIPELINE_KWARGS)

    # Regime-Reihen auf die jeweilige Signal-Zeitachse mappen (asof, taeglich aufgeloest reicht)
    regime_daily = d1[["ath_dist_pct", "adx"]].copy()
    regime_daily.index = regime_daily.index.normalize()

    def attach_regime(sig: pd.DataFrame) -> pd.DataFrame:
        sig = sig.copy()
        day_key = sig.index.normalize()
        reg = regime_daily.reindex(day_key, method="ffill")
        sig["ath_dist_pct"] = reg["ath_dist_pct"].to_numpy()
        sig["regime_adx"] = reg["adx"].to_numpy()
        return sig

    cont_sig = attach_regime(cont_sig)
    rev_sig = attach_regime(rev_sig)

    print("\n" + "=" * 100)
    print("FILTER-TEST: nur traden, wenn D1 innerhalb X% vom rollierenden 2J-Hoch UND ADX(D1) > Y")
    print("=" * 100)
    candidates = [
        (None, None, "kein Filter (Baseline)"),
        (-2.0, None, "ATH-Naehe <2%"),
        (-5.0, None, "ATH-Naehe <5%"),
        (-10.0, None, "ATH-Naehe <10%"),
        (None, 20.0, "ADX(D1)>20"),
        (None, 25.0, "ADX(D1)>25"),
        (-5.0, 20.0, "ATH-Naehe <5% UND ADX(D1)>20"),
        (-10.0, 20.0, "ATH-Naehe <10% UND ADX(D1)>20"),
    ]

    for ath_thresh, adx_thresh, label in candidates:
        cont_mask = pd.Series(True, index=cont_sig.index)
        rev_mask = pd.Series(True, index=rev_sig.index)
        if ath_thresh is not None:
            cont_mask &= cont_sig["ath_dist_pct"] > ath_thresh
            rev_mask &= rev_sig["ath_dist_pct"] > ath_thresh
        if adx_thresh is not None:
            cont_mask &= cont_sig["regime_adx"] > adx_thresh
            rev_mask &= rev_sig["regime_adx"] > adx_thresh

        cont_sig_f = cont_sig.copy()
        cont_sig_f.loc[~cont_mask, "signal"] = 0
        rev_sig_f = rev_sig.copy()
        rev_sig_f.loc[~rev_mask, "signal"] = 0

        print(f"\n--- {label} ---")
        for sp_start, sp_end in SUB_PERIODS:
            sp_start_ts, sp_end_ts = pd.Timestamp(sp_start, tz="America/New_York"), pd.Timestamp(sp_end, tz="America/New_York")
            cont_sp = cont_sig_f[(cont_sig_f.index >= sp_start_ts) & (cont_sig_f.index < sp_end_ts)]
            rev_sp = rev_sig_f[(rev_sig_f.index >= sp_start_ts) & (rev_sig_f.index < sp_end_ts)]
            cont_t = simulate_trades(cont_sp, CONT_BACKTEST_CFG)
            rev_t = simulate_trades(rev_sp, REV_BACKTEST_CFG)
            print(f"  {sp_start}->{sp_end}:  Cont {fmt(summarize(cont_t, cont_sp.index))}   |   Rev {fmt(summarize(rev_t, rev_sp.index))}")


if __name__ == "__main__":
    main()
