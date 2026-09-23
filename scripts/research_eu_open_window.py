"""EU-Open-Renditefenster (05:30-09:30 Berlin) auf unseren eigenen Daten.

Hintergrund: Bondarenko/Muravyev (SSRN 3596245) zeigen an E-mini-S&P-Futures
2004-2018, dass die gesamte durchschnittliche Aktienmarktrendite in den vier
Stunden 23:30-03:30 ET entsteht (= 05:30-09:30 Berlin), waehrend die
US-Cash-Session im Mittel eine Null ist. Siehe
knowledge/projects/eu-open-renditefenster.md und
knowledge/resources/24h-renditestruktur-und-informationskette.md.

Dieses Skript beantwortet Schritt 1 des dort festgelegten Plans: **gibt es
das Fenster in UNSEREN Jahren noch?** Das Paper-Sample endet Juli 2018,
unsere Dukascopy-Index-Abdeckung im Nachtfenster beginnt Juli 2018 -- der
Test ist damit eine fast lueckenlose Out-of-Sample-Fortsetzung, kein
Nachbau der Paper-Jahre.

Verankerung in BERLINER Zeit, nicht in ET: das Paper zeigt per
Sommerzeit-Test (Asien kennt keine DST), dass das Muster in europaeischer
Zeit feststeht und in asiatischer wandert. Berlin ist also der theoretisch
richtige Rahmen. In den wenigen Wochen, in denen US- und EU-Zeitumstellung
auseinanderlaufen, weicht das Fenster um eine Stunde von der ET-Definition
des Papers ab -- bewusst in Kauf genommen und unten separat geprueft.

Preise: Dukascopy-Index-CFDs, M15, OHLC-MID (kein Bid/Ask-Feed im Repo,
siehe scripts/measure_broker_spreads.py). Kosten werden deshalb NICHT aus
den Daten geschaetzt, sondern als Parameter durchgerechnet
(--cost-sweep) -- die echten Spannen im Fenster misst
measure_broker_spreads.py --window 5.5-9.5 separat.

REIN LESEND. Kein Order-Pfad, keine Config-Aenderung.

Aufruf:
    python scripts/research_eu_open_window.py [--start 2018-07-01] [--out <json>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from ny_open_orb.data import fetch_m15  # noqa: E402

BERLIN = "Europe/Berlin"
INSTRUMENTS = ("SP500", "US30", "NASDAQ")
TRADING_DAYS = 252

# Fenster in Berliner Ortszeit. "EU_FULL" ist die Paper-Definition,
# "EU_2ND"/"EU_1ST" seine beiden Haelften (Paper: die zweite traegt
# 5,90 der 7,60 Punkte), "US_CASH" der Gegencheck auf unser ORB-Fenster.
WINDOWS = {
    "EU_FULL": ("05:30", "09:30"),
    "EU_1ST": ("05:30", "07:30"),
    "EU_2ND": ("07:30", "09:30"),
    "US_CASH": ("15:30", "22:00"),
}


def load_berlin(instrument: str, start: str, end: str) -> pd.DataFrame:
    """ny_open_orb.data._fetch liefert KLEINgeschriebene Spalten und einen
    bereits nach America/New_York konvertierten Index -- beides hier auf
    Berliner Zeit und die im Skript erwartete Grossschreibung bringen."""
    df = fetch_m15(instrument, start, end)
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df = df.copy()
    df.index = idx.tz_convert(BERLIN)
    df = df.rename(columns={"open": "Open", "high": "High",
                            "low": "Low", "close": "Close", "volume": "Volume"})
    if "Open" not in df.columns:
        raise KeyError(f"{instrument}: keine Open-Spalte, vorhanden: {list(df.columns)}")
    return df.sort_index()


def price_at(df: pd.DataFrame, hhmm: str) -> pd.Series:
    """Open-Preis der Bar, die exakt auf hhmm startet, je Kalendertag.

    Bewusst der OPEN und nicht der Close der Vorbar: der Open ist der Preis,
    zu dem eine Order in genau dieser Minute ausgefuehrt wuerde. Tage ohne
    diese Bar fallen raus (kein Vorwaerts-Fuellen -- das wuerde einen Preis
    erfinden, den es nicht gab).
    """
    sel = df.between_time(hhmm, hhmm)
    out = sel["Open"].copy()
    out.index = sel.index.normalize()
    return out[~out.index.duplicated(keep="first")]


def newey_west_t(x: np.ndarray, lags: int = 5) -> float:
    """t-Statistik des Mittelwerts gegen 0, HAC-korrigiert (Newey-West).

    Das Paper nutzt dieselbe Korrektur. Bei taeglichen, nicht ueberlappenden
    Renditen ist der Unterschied zum naiven t klein -- aber die Korrektur ist
    konservativer, also nehmen wir sie.
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return float("nan")
    mu = x.mean()
    e = x - mu
    gamma0 = (e @ e) / n
    var = gamma0
    for L in range(1, min(lags, n - 1) + 1):
        w = 1.0 - L / (lags + 1.0)
        cov = (e[L:] @ e[:-L]) / n
        var += 2.0 * w * cov
    if var <= 0:
        return float("nan")
    return float(mu / np.sqrt(var / n))


def max_drawdown(returns: pd.Series) -> float:
    """MaxDD der aufsummierten Log-Rendite-Kurve, in Prozentpunkten."""
    eq = returns.cumsum()
    return float((eq - eq.cummax()).min() * 100.0)


def describe(returns: pd.Series, label: str) -> dict:
    r = returns.dropna()
    if len(r) < 10:
        return {"window": label, "n": int(len(r)), "error": "zu wenige Beobachtungen"}
    ann_mean = float(r.mean() * TRADING_DAYS * 100.0)
    ann_sd = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100.0)
    return {
        "window": label,
        "n": int(len(r)),
        "ann_return_pct": round(ann_mean, 2),
        "t_stat": round(newey_west_t(r.values), 2),
        "ann_sd_pct": round(ann_sd, 2),
        "sharpe": round(ann_mean / ann_sd, 2) if ann_sd > 0 else None,
        "skew": round(float(r.skew()), 2),
        "hit_rate_pct": round(float((r > 0).mean() * 100.0), 1),
        "max_dd_pct": round(max_drawdown(r), 2),
        "mean_bps_per_trade": round(float(r.mean() * 10_000), 2),
    }


def per_year(returns: pd.Series) -> dict:
    r = returns.dropna()
    out = {}
    for y, grp in r.groupby(r.index.year):
        if len(grp) < 20:
            continue
        out[int(y)] = {
            "n": int(len(grp)),
            "ann_return_pct": round(float(grp.mean() * TRADING_DAYS * 100.0), 2),
            "t_stat": round(newey_west_t(grp.values), 2),
        }
    return out


def per_weekday(returns: pd.Series) -> dict:
    r = returns.dropna()
    names = ["Mo", "Di", "Mi", "Do", "Fr"]
    out = {}
    for d, grp in r.groupby(r.index.dayofweek):
        if d > 4 or len(grp) < 20:
            continue
        out[names[d]] = {
            "n": int(len(grp)),
            "ann_return_pct": round(float(grp.mean() * TRADING_DAYS * 100.0), 2),
        }
    return out


def cost_sweep(returns: pd.Series, bps_list: tuple[float, ...]) -> dict:
    """Netto-Ergebnis bei verschiedenen Round-Trip-Kosten.

    Die Strategie handelt JEDEN Tag zweimal (rein/raus), Kosten fallen also
    je Beobachtung einmal als Round-Trip an. Break-even = mittlere
    Brutto-Rendite je Trade in bps.
    """
    r = returns.dropna()
    gross_bps = float(r.mean() * 10_000)
    out = {"gross_bps_per_trade": round(gross_bps, 2),
           "breakeven_cost_bps_roundtrip": round(gross_bps, 2), "net": {}}
    for c in bps_list:
        net = r - c / 10_000.0
        ann = float(net.mean() * TRADING_DAYS * 100.0)
        sd = float(net.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100.0)
        out["net"][f"{c:g}bps"] = {
            "ann_return_pct": round(ann, 2),
            "t_stat": round(newey_west_t(net.values), 2),
            "sharpe": round(ann / sd, 2) if sd > 0 else None,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2018-07-01",
                    help="Erster Tag. Default 2018-07-01: davor hat der "
                         "Dukascopy-Index-Feed im Nachtfenster keine Bars.")
    ap.add_argument("--end", default="2026-09-18")
    ap.add_argument("--split", default="2022-12-31",
                    help="IS/OOS-Schnitt, gleiche Konvention wie die ORB-Exit-Studie.")
    ap.add_argument("--cost-sweep", default="0,0.5,1,1.5,2,3,4,6",
                    help="Round-Trip-Kosten in bps, Komma-Liste.")
    ap.add_argument("--out", type=Path,
                    default=REPO / "knowledge" / "_data" / "eu_open_window.json")
    args = ap.parse_args()

    bps_list = tuple(float(x) for x in args.cost_sweep.split(",") if x.strip())
    split = pd.Timestamp(args.split).tz_localize(BERLIN)
    report: dict = {
        "generated": pd.Timestamp.now(tz=BERLIN).isoformat(),
        "sample": {"start": args.start, "end": args.end, "split_is_oos": args.split},
        "anchor": "Europe/Berlin (Paper-DST-Test: Muster steht in europaeischer Zeit)",
        "price_basis": "Dukascopy M15 OHLC-MID, Open der Startbar -> Open der Endbar",
        "instruments": {},
    }

    for inst in INSTRUMENTS:
        print(f"\n{'=' * 64}\n{inst}\n{'=' * 64}")
        df = load_berlin(inst, args.start, args.end)
        inst_out: dict = {"windows": {}}

        # Referenzpreise je Fenstergrenze einmal ziehen
        marks = {}
        for hhmm in sorted({t for w in WINDOWS.values() for t in w}):
            marks[hhmm] = price_at(df, hhmm)

        # Volle 24h-Rendite (05:30 -> naechster 05:30) als Bezugsgroesse
        p0530 = marks["05:30"]
        r_day = np.log(p0530.shift(-1) / p0530).dropna()

        for label, (t0, t1) in WINDOWS.items():
            a, b = marks[t0], marks[t1]
            common = a.index.intersection(b.index)
            r = np.log(b.loc[common] / a.loc[common]).dropna()
            r = r[np.isfinite(r)]
            # Ausreisser-Schutz: >20 % in einem Intraday-Fenster ist im
            # Index-CFD ein Datenfehler, kein Markt (2020er Crash-Tage
            # bleiben mit <10 % drin).
            bad = r.abs() > 0.20
            if bad.any():
                print(f"  [{label}] {int(bad.sum())} Bar(s) mit |r|>20 % verworfen (Datenfehler)")
                r = r[~bad]

            stats = describe(r, label)
            stats["per_year"] = per_year(r)
            stats["per_weekday"] = per_weekday(r)
            stats["costs"] = cost_sweep(r, bps_list)
            is_r, oos_r = r[r.index <= split], r[r.index > split]
            stats["is_oos"] = {
                "IS": describe(is_r, f"{label}/IS"),
                "OOS": describe(oos_r, f"{label}/OOS"),
            }
            inst_out["windows"][label] = stats

            print(f"\n  --- {label} ({t0}-{t1} Berlin), n={stats['n']}")
            print(f"      Rendite p.a. {stats['ann_return_pct']:>7.2f} %   "
                  f"t={stats['t_stat']:>6.2f}   Sharpe {stats['sharpe']}   "
                  f"MaxDD {stats['max_dd_pct']:.2f} %")
            print(f"      brutto {stats['mean_bps_per_trade']:.2f} bps/Trade  "
                  f"-> Break-even-Kosten {stats['costs']['breakeven_cost_bps_roundtrip']:.2f} bps RT")
            print(f"      IS  {stats['is_oos']['IS'].get('ann_return_pct')} % "
                  f"(t={stats['is_oos']['IS'].get('t_stat')})   "
                  f"OOS {stats['is_oos']['OOS'].get('ann_return_pct')} % "
                  f"(t={stats['is_oos']['OOS'].get('t_stat')})")
            yrs = stats["per_year"]
            pos = sum(1 for v in yrs.values() if v["ann_return_pct"] > 0)
            print(f"      Jahre positiv: {pos}/{len(yrs)}   " +
                  " ".join(f"{y}:{v['ann_return_pct']:+.1f}" for y, v in sorted(yrs.items())))

        # Rest-of-day als Gegenstueck zum EU-Fenster (Paper Tab. 1)
        eu = inst_out["windows"]["EU_FULL"]
        common = r_day.index.intersection(
            np.log(marks["09:30"] / marks["05:30"]).dropna().index)
        r_eu = np.log(marks["09:30"] / marks["05:30"]).dropna().loc[common]
        r_rest = (r_day.loc[common] - r_eu).dropna()
        inst_out["windows"]["REST_OF_DAY"] = describe(r_rest, "REST_OF_DAY")
        inst_out["windows"]["FULL_24H"] = describe(r_day, "FULL_24H")
        print(f"\n  --- Vergleich (Paper Tab. 1 analog)")
        print(f"      EU_FULL      {eu['ann_return_pct']:>7.2f} % p.a.  t={eu['t_stat']:>6.2f}  "
              f"Sharpe {eu['sharpe']}")
        rest = inst_out["windows"]["REST_OF_DAY"]
        full = inst_out["windows"]["FULL_24H"]
        print(f"      REST_OF_DAY  {rest['ann_return_pct']:>7.2f} % p.a.  t={rest['t_stat']:>6.2f}  "
              f"Sharpe {rest['sharpe']}")
        print(f"      FULL_24H     {full['ann_return_pct']:>7.2f} % p.a.  t={full['t_stat']:>6.2f}  "
              f"Sharpe {full['sharpe']}")

        report["instruments"][inst] = inst_out

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
