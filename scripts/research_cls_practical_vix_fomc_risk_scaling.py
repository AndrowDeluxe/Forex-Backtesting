"""VIX/FOMC-ECB als RISIKO-SKALIERUNG (nicht Gate) fuer cls_practical, User-
Anfrage 2026-08-20 im Anschluss an einen alten, nie zu Ende gefuehrten Fund
aus scripts/research_cls_practical_external_filters.py (2026-08-13, IS-only
2018-12-01..2022-06-01): dort machte das AUSSCHLIESSEN von VIX>20-Tagen
avg_R von +0.155 auf -0.227 KAPUTT (n=85->41), und NUR FOMC/EZB-Fenster
(+/-1 Tag) zu handeln gab avg_R=+0.515 (n=17) gegen +0.065 wenn man genau
diese Fenster ausschliesst (n=68) - beide Signale scheinen die Edge zu
TRAGEN statt sie zu verwaschen. Nahe liegender Schluss: nicht rausfiltern,
sondern hochskalieren, exakt das Muster, das sich beim Zins-Filter bewaehrt
hat (cls_practical/rates.py::compute_daily_rate_risk_multiplier, ADOPTED
2026-08-19) - der 2026-08-18 gebaute, aber bis dahin ungenutzte
`risk_multiplier`-Parameter von simulate_cls_practical().

R-Vielfache sind skaleninvariant (siehe research_cls_practical_daily_rate_
risk_scaling.py) - eine reine Risiko-Skalierung aendert avg_R pro Trade
NICHT, der Nutzen zeigt sich nur in der $-Equity-Kurve (Sharpe/Calmar/
MaxDD/Gesamt-PnL). Gleiche Equity-Methodik wie dort.

Teil A: VIX-only / FOMC+EZB-only / kombiniert, je bei mehreren Multiplikatoren,
am Standard-Split 2022-06-01 (Gesamt/IS/OOS).
Teil B: der interessanteste Kandidat aus Teil A zusaetzlich ueber mehrere
Split-Punkte + Jahres-Aufschluesselung (dieselbe Robustheits-Methodik wie
research_cls_practical_daily_rate_filter_robustness.py Teil A)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asian_range_breakout.vix import fetch_vix_daily
from bond_yield_indicator.calendar import event_window_dummy
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS, compute_daily_features

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
SPLITS = ["2020-06-01", "2021-06-01", "2022-06-01", "2023-06-01", "2024-06-01"]
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
BASE_RISK_PCT = 0.01
TRADING_DAYS_PER_YEAR = 252
INITIAL_EQUITY = 100_000.0


def daily_pnl_series(trades: pd.DataFrame, start: str, end: str) -> pd.Series:
    full_days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    if len(trades) == 0:
        return pd.Series(0.0, index=full_days)
    exit_day = trades["exit_time"].dt.tz_localize(None).dt.floor("D")
    return trades.groupby(exit_day)["pnl_usd"].sum().reindex(full_days, fill_value=0.0)


def equity_metrics(daily_pnl: pd.Series) -> dict:
    equity = INITIAL_EQUITY + daily_pnl.cumsum()
    daily_ret = equity.pct_change().fillna(0.0)
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    max_dd = dd.min()
    years = len(daily_pnl) / TRADING_DAYS_PER_YEAR
    cagr = (equity.iloc[-1] / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else float("nan")
    sharpe = (daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_ret.std(ddof=1) > 0 else 0.0
    calmar = cagr / abs(max_dd) if max_dd not in (0, float("nan")) else float("nan")
    return {"total_pnl": daily_pnl.sum(), "cagr_pct": cagr * 100, "max_drawdown_pct": max_dd * 100,
            "sharpe": sharpe, "calmar": calmar}


def report(label: str, trades: pd.DataFrame, variant: str | None = None, mult: float | None = None) -> dict:
    row = {"label": label, "variant": variant, "mult": mult, "n": len(trades)}
    for period, p_start, p_end in (("gesamt", START, END), ("is", START, SPLIT), ("oos", SPLIT, END)):
        if period == "gesamt":
            t = trades
        elif period == "is":
            t = trades[trades["entry_time"].dt.tz_localize(None) < SPLIT]
        else:
            t = trades[trades["entry_time"].dt.tz_localize(None) >= SPLIT]
        m = equity_metrics(daily_pnl_series(t, p_start, p_end))
        for k, v in m.items():
            row[f"{period}_{k}"] = v
    print(f"  {label:42s}: n={row['n']:>3d} | Gesamt PnL=${row['gesamt_total_pnl']:+,.0f} Sharpe={row['gesamt_sharpe']:.2f} "
          f"Calmar={row['gesamt_calmar']:.2f} MaxDD={row['gesamt_max_drawdown_pct']:.2f}% "
          f"| IS Sharpe={row['is_sharpe']:.2f} PnL=${row['is_total_pnl']:+,.0f} "
          f"| OOS Sharpe={row['oos_sharpe']:.2f} PnL=${row['oos_total_pnl']:+,.0f}")
    return row


def build_flag_series(daily_index, vix_flag: bool, cb_flag: bool, vix_thresh: float = 20.0) -> pd.Series:
    """Boolean Series ueber daily_index (date-Objekte, wie daily.index /
    trades['date']): True an Tagen, die (je nach Flags) VIX>vix_thresh
    (Vortages-Schluss, kein Lookahead) und/oder in einem FOMC/EZB-Fenster
    (+/-1 Tag, Termine lange vorher bekannt) liegen."""
    flagged = pd.Series(False, index=daily_index)
    if vix_flag:
        vix = fetch_vix_daily((pd.Timestamp(START) - pd.Timedelta(days=10)).date().isoformat(), END)
        vix_known = vix.copy()
        vix_known.index = vix_known.index + pd.Timedelta(days=1)
        daily_cal = pd.date_range(vix_known.index.min(), pd.Timestamp(END), freq="D")
        vix_daily = vix_known.reindex(daily_cal).ffill()
        high_vix_days = set(vix_daily[vix_daily > vix_thresh].index.normalize().date)
        flagged |= pd.Series([d in high_vix_days for d in daily_index], index=daily_index)
    if cb_flag:
        date_index = pd.DatetimeIndex(sorted(set(daily_index)))
        fomc_dummy = event_window_dummy("FOMC", date_index, window_days=1)
        ecb_dummy = event_window_dummy("ECB", date_index, window_days=1)
        cb_days = set(date_index[(fomc_dummy == 1) | (ecb_dummy == 1)].date)
        flagged |= pd.Series([d in cb_days for d in daily_index], index=daily_index)
    return flagged


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 + BUND/USTBOND M5 + VIX + FOMC/EZB-Kalender)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    daily = compute_daily_features(eurusd_m5)

    print(f"\n{'='*115}\nTEIL A: Sweep bei Standard-Split {SPLIT}\n{'='*115}")
    flat_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, risk_pct=BASE_RISK_PCT)
    rows = [report(f"Flach {BASE_RISK_PCT*100:.0f}% (keine Skalierung)", flat_trades)]

    variants = {
        "VIX>20": build_flag_series(daily.index, vix_flag=True, cb_flag=False),
        "FOMC/EZB +/-1d": build_flag_series(daily.index, vix_flag=False, cb_flag=True),
        "VIX>20 ODER FOMC/EZB": build_flag_series(daily.index, vix_flag=True, cb_flag=True),
    }
    for name, flag in variants.items():
        share = flag.mean() * 100
        for mult in (1.25, 1.5, 1.75):
            risk_mult = pd.Series(1.0, index=flag.index)
            risk_mult[flag] = mult
            label = f"{name} {mult}x ({share:.0f}% d. Tage)"
            trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                             risk_pct=BASE_RISK_PCT, risk_multiplier=risk_mult)
            rows.append(report(label, trades, variant=name, mult=mult))

    df = pd.DataFrame(rows)
    out_a = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "vix_fomc_risk_scaling_sweep.csv"
    df.to_csv(out_a, index=False)
    print(f"\nGespeichert: {out_a}")

    non_flat = df[df["variant"].notna()]
    best = non_flat.loc[non_flat["gesamt_sharpe"].idxmax()]
    print(f"\nBester Kandidat nach Gesamt-Sharpe: {best['label']} (Sharpe={best['gesamt_sharpe']:.2f}, "
          f"vs. Flach Sharpe={rows[0]['gesamt_sharpe']:.2f})")

    print(f"\n{'='*115}\nTEIL B: Robustheit des besten Kandidaten -- mehrere Split-Punkte + Jahre\n{'='*115}")
    best_name, best_mult = best["variant"], float(best["mult"])
    print(f"Kandidat: {best_name}, Multiplikator={best_mult}x\n")
    flag = variants[best_name]
    risk_mult = pd.Series(1.0, index=flag.index)
    risk_mult[flag] = best_mult
    scaled_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                            risk_pct=BASE_RISK_PCT, risk_multiplier=risk_mult)

    print("-- Jahres-Aufschluesselung ($PnL pro Kalenderjahr) --")
    for label, trades in (("Flach", flat_trades), (f"{best_name} {best_mult}x", scaled_trades)):
        t = trades.copy()
        t["year"] = t["entry_time"].dt.year
        yearly = t.groupby("year")["pnl_usd"].sum()
        print(f"  {label}:")
        for year, pnl in yearly.items():
            print(f"    {year}: ${pnl:+,.0f}")

    print("\n-- Mehrere Split-Punkte (Sharpe IS -> OOS) --")
    rows_b = []
    for split in SPLITS:
        def m(trades, p_start, p_end):
            return equity_metrics(daily_pnl_series(trades, p_start, p_end))

        flat_is = flat_trades[flat_trades["entry_time"].dt.tz_localize(None) < split]
        flat_oos = flat_trades[flat_trades["entry_time"].dt.tz_localize(None) >= split]
        scaled_is = scaled_trades[scaled_trades["entry_time"].dt.tz_localize(None) < split]
        scaled_oos = scaled_trades[scaled_trades["entry_time"].dt.tz_localize(None) >= split]

        mfi, mfo = m(flat_is, START, split), m(flat_oos, split, END)
        msi, mso = m(scaled_is, START, split), m(scaled_oos, split, END)
        both_beat = (msi["sharpe"] > mfi["sharpe"]) and (mso["sharpe"] > mfo["sharpe"])
        print(f"  Split={split}: Flach IS Sharpe={mfi['sharpe']:+.2f} -> OOS={mfo['sharpe']:+.2f} "
              f"| Skaliert IS Sharpe={msi['sharpe']:+.2f} -> OOS={mso['sharpe']:+.2f} | beide besser: {both_beat}")
        rows_b.append({"split": split, "flat_sharpe_is": mfi["sharpe"], "flat_sharpe_oos": mfo["sharpe"],
                        "scaled_sharpe_is": msi["sharpe"], "scaled_sharpe_oos": mso["sharpe"], "both_beat": both_beat})

    n_both_beat = sum(r["both_beat"] for r in rows_b)
    print(f"\n  -> schlaegt Baseline (Sharpe) auf IS UND OOS gleichzeitig bei {n_both_beat}/{len(rows_b)} Split-Punkten.")

    out_b = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "vix_fomc_risk_scaling_split_robustness.csv"
    pd.DataFrame(rows_b).to_csv(out_b, index=False)
    print(f"\nGespeichert: {out_b}")


if __name__ == "__main__":
    main()
