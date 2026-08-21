"""Der ECHTE Front-End-2Y-Zinsfilter (User-Anfrage 2026-08-21: "Baue den
Zinsfilter"), im Anschluss an den Feasibility-Spike vom 2026-08-20: die
bisher adoptierte Zins-Skalierung (cls_practical/rates.py) nutzt BUND/
USTBOND-CFD-PREISE als LONG-END-Duration-Proxy, weil kein freier Intraday-
Front-End-Feed existierte ("Front End Rates oder kurze Zinserwartungen" aus
der Quelle war nie umsetzbar, siehe rates.py-Docstring). Jetzt verifiziert:
TVC:US02Y / TVC:DE02Y (ueber die bestehende tvDatafeed-Bridge,
tradingview/data.py) liefern echte 2Y-Rendite-Tagesbalken bis 2014 zurueck,
auch ohne Login. Gegen FRED DGS2 gegengeprueft (2026-08-18: TVC 4.177% vs.
FRED 4.19%) - passt.

Wichtiger methodischer Unterschied zur BUND/USTBOND-Version: das sind
RENDITEN (Prozentpunkte), keine Preise. compute_rate_support_score/
compute_daily_rate_score nutzen bei CFD-PREISEN eine relative Tagesrendite
(close/open-1) und ein PREIS-Vorzeichen, das wegen der inversen Preis/
Rendite-Beziehung schon umgedreht ist (ustbond_return - bund_return). Bei
echten Renditen braucht es (a) die absolute Tagesaenderung in Prozentpunkten
statt einer relativen Rendite (2020-2022 waren DE-Renditen zeitweise negativ,
eine "%-Rendite" einer negativen Rendite ist bedeutungslos) und (b) das
Vorzeichen MUSS NICHT umgedreht werden, weil eine steigende Rendite direkt
"Zinsen dieses Landes werden staerker" bedeutet (keine Preis-Inversion):

    daily_rate_score_2y = de02y_day_change - us02y_day_change

Positiv, wenn DE-Renditen relativ zu US-Renditen steigen (EUR-Staerke) ->
stuetzt EUR/USD long. Direkt analog zu rates.py's Vorzeichenkonvention
("EUR rates strengthen" -> Bund-PREIS faellt -> in der CFD-Version negativ
bund_return, hier stattdessen DIREKT positive de02y_day_change - dieselbe
oekonomische Aussage, nur ohne den Preis/Rendite-Umweg).

lag_days shiftet wie bei compute_daily_rate_score, damit nur der bereits
vollstaendig geschlossene Vortag(e) verwendet wird - kein Lookahead.

Teil A: Risk-SKALIERUNG (das Muster, das sich beim Long-End-Proxy bewaehrt
hat) - Sweep ueber lag_days x z_threshold x Multiplikator, Equity-Metriken
am Standard-Split. Teil B: Split-Robustheit (5 Splits + Jahre) des besten
Kandidaten, exakt wie research_cls_practical_daily_rate_filter_robustness.py.
Teil C: Kombination mit dem bereits adoptierten Long-End-Proxy (beide
Multiplikatoren multiplikativ gestapelt) - ersetzt der Front-End-Filter den
Long-End-Proxy, oder ergaenzt er ihn?"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from cls_practical.rates import classify_rates_ampel, compute_daily_rate_risk_multiplier
from strategy.cls_advanced import PAIRS, compute_daily_features
from tradingview.data import fetch_ohlcv

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
SPLITS = ["2020-06-01", "2021-06-01", "2022-06-01", "2023-06-01", "2024-06-01"]
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
BASE_RISK_PCT = 0.01
TRADING_DAYS_PER_YEAR = 252
INITIAL_EQUITY = 100_000.0


def fetch_2y_daily(symbol: str) -> pd.DataFrame:
    """Taegliche TVC-Renditebalken, Index auf reine Kalendertage (date-
    Objekte) reduziert - passend zu daily.index / trades['date'] im Rest des
    Repos (siehe strategy/cls_advanced.py::compute_daily_features)."""
    df = fetch_ohlcv(symbol, "TVC", interval="1d", n_bars=3500)
    df = df.sort_index()
    df.index = pd.Index(df.index.date, name="date")
    return df[~df.index.duplicated(keep="last")]


def compute_daily_rate_score_2y(de02y: pd.DataFrame, us02y: pd.DataFrame, lag_days: int = 1) -> pd.Series:
    joined = pd.concat(
        {"de": de02y["close"] - de02y["open"], "us": us02y["close"] - us02y["open"]}, axis=1, join="outer"
    ).sort_index()
    score = (joined["de"] - joined["us"]).rename("daily_rate_score_2y")
    return score.shift(lag_days)


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


def report(label: str, trades: pd.DataFrame, **extra) -> dict:
    row = {"label": label, "n": len(trades), **extra}
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
    print(f"  {label:46s}: n={row['n']:>3d} | Gesamt PnL=${row['gesamt_total_pnl']:+,.0f} Sharpe={row['gesamt_sharpe']:.2f} "
          f"Calmar={row['gesamt_calmar']:.2f} MaxDD={row['gesamt_max_drawdown_pct']:.2f}% "
          f"| IS Sharpe={row['is_sharpe']:.2f} PnL=${row['is_total_pnl']:+,.0f} "
          f"| OOS Sharpe={row['oos_sharpe']:.2f} PnL=${row['oos_total_pnl']:+,.0f}")
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 + BUND/USTBOND M5 + TVC US02Y/DE02Y)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    de02y = fetch_2y_daily("DE02Y")
    us02y = fetch_2y_daily("US02Y")
    print(f"DE02Y: {len(de02y)} Tage ({de02y.index.min()}..{de02y.index.max()}), "
          f"US02Y: {len(us02y)} Tage ({us02y.index.min()}..{us02y.index.max()})")

    daily = compute_daily_features(eurusd_m5)
    direction = daily["direction"]

    print(f"\n{'='*118}\nTEIL A: Risk-Skalierungs-Sweep bei Standard-Split {SPLIT}\n{'='*118}")
    flat_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, risk_pct=BASE_RISK_PCT)
    rows = [report(f"Flach {BASE_RISK_PCT*100:.0f}% (keine Skalierung)", flat_trades)]

    for lag_days in (1, 2, 3):
        score = compute_daily_rate_score_2y(de02y, us02y, lag_days=lag_days)
        for z_threshold in (0.0, 0.25, 0.5):
            ampel = classify_rates_ampel(score, direction, z_window=60, z_threshold=z_threshold)
            confirmed_share = (ampel == "grün").mean() * 100
            for mult in (1.25, 1.5, 1.75):
                risk_mult = pd.Series(1.0, index=ampel.index)
                risk_mult[ampel == "grün"] = mult
                label = f"2Y lag={lag_days}d z>={z_threshold} {mult}x ({confirmed_share:.0f}% gruen)"
                trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                                 risk_pct=BASE_RISK_PCT, risk_multiplier=risk_mult)
                rows.append(report(label, trades, lag_days=lag_days, z_threshold=z_threshold, mult=mult))

    df = pd.DataFrame(rows)
    out_a = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "2y_frontend_rate_risk_scaling_sweep.csv"
    df.to_csv(out_a, index=False)
    print(f"\nGespeichert: {out_a}")

    non_flat = df[df["lag_days"].notna()]
    best = non_flat.loc[non_flat["gesamt_sharpe"].idxmax()]
    print(f"\nBester Kandidat nach Gesamt-Sharpe: {best['label']} (Sharpe={best['gesamt_sharpe']:.2f}, "
          f"vs. Flach Sharpe={rows[0]['gesamt_sharpe']:.2f})")

    print(f"\n{'='*118}\nTEIL B: Split-Robustheit des besten Kandidaten -- mehrere Split-Punkte + Jahre\n{'='*118}")
    best_lag, best_z, best_mult = int(best["lag_days"]), float(best["z_threshold"]), float(best["mult"])
    print(f"Kandidat: lag={best_lag}d z>={best_z} mult={best_mult}x\n")
    best_score = compute_daily_rate_score_2y(de02y, us02y, lag_days=best_lag)
    best_ampel = classify_rates_ampel(best_score, direction, z_window=60, z_threshold=best_z)
    best_risk_mult = pd.Series(1.0, index=best_ampel.index)
    best_risk_mult[best_ampel == "grün"] = best_mult
    scaled_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                            risk_pct=BASE_RISK_PCT, risk_multiplier=best_risk_mult)

    print("-- Jahres-Aufschluesselung ($PnL pro Kalenderjahr) --")
    for label, trades in (("Flach", flat_trades), (f"2Y lag={best_lag}d z>={best_z} {best_mult}x", scaled_trades)):
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
              f"| 2Y-skaliert IS Sharpe={msi['sharpe']:+.2f} -> OOS={mso['sharpe']:+.2f} | beide besser: {both_beat}")
        rows_b.append({"split": split, "flat_sharpe_is": mfi["sharpe"], "flat_sharpe_oos": mfo["sharpe"],
                        "scaled_sharpe_is": msi["sharpe"], "scaled_sharpe_oos": mso["sharpe"], "both_beat": both_beat})

    n_both_beat = sum(r["both_beat"] for r in rows_b)
    print(f"\n  -> schlaegt Baseline (Sharpe) auf IS UND OOS gleichzeitig bei {n_both_beat}/{len(rows_b)} Split-Punkten.")
    out_b = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "2y_frontend_rate_split_robustness.csv"
    pd.DataFrame(rows_b).to_csv(out_b, index=False)
    print(f"Gespeichert: {out_b}")

    print(f"\n{'='*118}\nTEIL C: Kombination mit dem adoptierten Long-End-Proxy (BUND/USTBOND CFD, lag=2d z>=0.5, 1.75x)\n{'='*118}")
    longend_mult = compute_daily_rate_risk_multiplier(bund_m5, ustbond_m5, direction, lag_days=2, z_window=60,
                                                        z_threshold=0.5, confirmed_mult=1.75)
    longend_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                             risk_pct=BASE_RISK_PCT, risk_multiplier=longend_mult)
    rows_c = [report("Long-End only (adoptiert)", longend_trades)]
    rows_c.append(report(f"Front-End 2Y only ({best_mult}x)", scaled_trades))

    combined_mult = pd.Series(
        longend_mult.reindex(direction.index, fill_value=1.0).to_numpy()
        * best_risk_mult.reindex(direction.index, fill_value=1.0).to_numpy(),
        index=direction.index,
    )
    combined_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                              risk_pct=BASE_RISK_PCT, risk_multiplier=combined_mult)
    rows_c.append(report("Long-End x Front-End 2Y (multiplikativ gestapelt)", combined_trades))

    out_c = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "2y_frontend_vs_longend_comparison.csv"
    pd.DataFrame(rows_c).to_csv(out_c, index=False)
    print(f"Gespeichert: {out_c}")


if __name__ == "__main__":
    main()
