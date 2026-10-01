"""EK: was kostet die Mindestlot-Anhebung auf der echten Kontogroesse? (2026-10-01)

Nutzerauftrag: "Backteste die Mindestlotanhebung und gib mir die Daten auf
meiner Kontogroesse der letzten 3 Jahre."

WARUM DAS NICHT MIT R-MULTIPLES GEHT
Alle bisherigen CTNL-Rechnungen laufen in R -- das ist risikoneutral und
blendet genau den Effekt aus, um den es hier geht. Die Anhebung wirkt
NICHT konstant:
  * ihr Faktor haengt an der STOPDISTANZ des einzelnen Trades (ein enger
    Stop heisst mehr Lots fuer dasselbe Ziel-Risiko, also faellt die
    Anhebung kleiner aus),
  * und an der EQUITY, die sich mit jedem Trade aendert. Faellt das Konto,
    sinkt das Ziel-Risiko, waehrend das Mindestlot gleich bleibt -- die
    Anhebung wird groesser, genau wenn man sie am wenigsten gebrauchen kann.
Beides ist pfadabhaengig und wird hier Trade fuer Trade nachgebildet,
mit Verzinsung.

ECHTE KONTOPARAMETER (gelesen, nicht gesetzt; Stand 2026-10-01)
  Equity                     2.843,35 EUR
  CAPITAL_WEIGHT             1/8
  LEG_RISK_PCT[ctnl_reversal] 0,0015  -> Ziel 0,53 EUR/Trade
  LEG_RISK_PCT[gold_asb]      0,2816  -> Ziel 100,07 EUR/Trade
  MAX_SINGLE_TRADE_RISK_PCT  5 %  -> harte Obergrenze, darueber faellt der
                                     Trade aus (core/sizing.py::SizingError)
  XAUUSD: volume_min 0,01, step 0,01, 88,55 EUR je Kurspunkt und Lot
          (= 100 USD / EURUSD 1,1292)

`gold_asb` laeuft als GEGENPROBE mit: dort liegt das Ziel-Risiko weit ueber
dem Mindestlot, die Anhebung greift also nie. Wenn die Rechnung dort nichts
veraendert, misst sie den Effekt und nicht sich selbst.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "scripts"))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h4  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_KWARGS, REV_MAX_CONCURRENT  # noqa: E402
from gold_smc_htf_ltf.ribbon_gate import ribbon_direction  # noqa: E402
from research_ctnl_execution_costs import _utc_naive  # noqa: E402
from research_ctnl_optimization import leg_trades, to_live  # noqa: E402

# --- Kontoparameter, aus EK-Portfolio-Bridge/config.py + MT5 gelesen
EQUITY_START = 2843.35
CAPITAL_WEIGHT = 0.125
MAX_SINGLE_TRADE_RISK_PCT = 0.05
EUR_JE_PUNKT_JE_LOT = 88.55     # XAUUSD, EUR-Konto, EURUSD 1,1292
VOLUME_MIN = 0.01
VOLUME_STEP = 0.01
LEG_RISK = {"ctnl_reversal": 0.0015, "gold_asb": 0.2816}


def _robust(fn, *a, versuche: int = 4, **kw):
    """dukascopy_python wirft sporadisch KeyError/TypeError mitten im Stream
    (bekannt, siehe DASHBOARD.md "dukascopy-Hang"). Ein zweiter Anlauf
    reicht fast immer -- ohne ihn scheitert ein 10-Minuten-Lauf an einem
    Sekundenfehler."""
    import time
    for i in range(versuche):
        try:
            return fn(*a, **kw)
        except (KeyError, TypeError, ValueError) as e:
            if i == versuche - 1:
                raise
            print(f"    {getattr(fn,'__name__',fn)} Versuch {i+1} fehlgeschlagen "
                  f"({type(e).__name__}: {e}) -- neuer Anlauf")
            time.sleep(3)


def simuliere(trades: pd.DataFrame, leg: str, *, anheben: bool,
              start: float = EQUITY_START) -> dict:
    """Trade fuer Trade mit Verzinsung. `anheben=False` ist die
    Kontrollrechnung: Bruchteils-Lots waeren handelbar, die Formel greift
    also unverfaelscht. Das ist kein realistischer Broker -- es ist der
    Massstab, gegen den die Anhebung gemessen wird."""
    eq = start
    kurve, zeilen = [], []
    for _, t in trades.iterrows():
        # Stopdistanz in Kurspunkten. `effective_risk` ist der REALE Nenner,
        # auf den die Bridge sized (|Live-Kurs - SL| nach dem Einstiegsversatz,
        # siehe sizing.py) -- er liegt in der gegateten CTNL-Liste vor.
        # `initial_risk` (geplante Distanz) ist der Rueckfall fuer Trade-Listen
        # ohne Replay, z.B. gold_asb.
        stop_punkte = float(t["effective_risk"] if "effective_risk" in t.index
                            else t["initial_risk"])
        if stop_punkte <= 0:
            continue
        verlust_je_lot = stop_punkte * EUR_JE_PUNKT_JE_LOT
        ziel = eq * CAPITAL_WEIGHT * LEG_RISK[leg]
        roh_lots = ziel / verlust_je_lot

        if anheben:
            lots = math.floor(roh_lots / VOLUME_STEP) * VOLUME_STEP
            gebumpt = lots < VOLUME_MIN
            if gebumpt:
                lots = VOLUME_MIN
        else:
            lots, gebumpt = roh_lots, False

        echtes_risiko = lots * verlust_je_lot
        if echtes_risiko > eq * MAX_SINGLE_TRADE_RISK_PCT:
            zeilen.append({"zeit": t["entry_time"], "status": "abgelehnt_5pct",
                           "ziel": ziel, "echtes_risiko": echtes_risiko, "equity": eq})
            continue   # core/sizing.py wirft hier SizingError -> kein Trade

        pnl = float(t["r"]) * echtes_risiko
        eq += pnl
        kurve.append(eq)
        zeilen.append({"zeit": t["entry_time"], "status": "gehandelt", "lots": lots,
                       "gebumpt": gebumpt, "ziel": ziel, "echtes_risiko": echtes_risiko,
                       "faktor": echtes_risiko / ziel if ziel > 0 else np.nan,
                       "r": float(t["r"]), "pnl": pnl, "equity": eq})
        if eq <= 0:
            break

    df = pd.DataFrame(zeilen)
    gehandelt = df[df["status"] == "gehandelt"] if not df.empty else df
    k = pd.Series(kurve) if kurve else pd.Series([start])
    hoch = k.cummax()
    dd = (k / hoch - 1.0)
    return {
        "trades_angeboten": int(len(df)),
        "gehandelt": int(len(gehandelt)),
        "abgelehnt_5pct": int((df["status"] == "abgelehnt_5pct").sum()) if not df.empty else 0,
        "gebumpt": int(gehandelt["gebumpt"].sum()) if len(gehandelt) else 0,
        "anteil_gebumpt": float(gehandelt["gebumpt"].mean()) if len(gehandelt) else 0.0,
        "faktor_median": float(gehandelt.loc[gehandelt["gebumpt"], "faktor"].median())
                          if len(gehandelt) and gehandelt["gebumpt"].any() else None,
        "faktor_max": float(gehandelt.loc[gehandelt["gebumpt"], "faktor"].max())
                       if len(gehandelt) and gehandelt["gebumpt"].any() else None,
        "risiko_median_eur": float(gehandelt["echtes_risiko"].median()) if len(gehandelt) else None,
        "risiko_median_pct": float((gehandelt["echtes_risiko"] / gehandelt["equity"]).median())
                              if len(gehandelt) else None,
        "equity_ende": float(eq),
        "rendite_pct": float((eq / start - 1) * 100),
        "max_dd_pct": float(dd.min() * 100) if len(dd) else 0.0,
        "_df": df,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jahre", type=float, default=3.0)
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ek_mindestlot_3jahre.json")
    args = ap.parse_args()

    ende = pd.Timestamp.now(tz="UTC")
    ab = ende - pd.Timedelta(days=int(args.jahre * 365))
    print(f"Zeitraum: {ab:%Y-%m-%d} bis {ende:%Y-%m-%d} ({args.jahre:g} Jahre)")
    print(f"Startkapital: {EQUITY_START:,.2f} EUR (echte EK-Equity)\n")

    # NUR h4/h1/m15 holen, kein M5: ctnl_reversal und gold_asb laufen beide
    # auf M15, und der M5-Abruf ab 2021 reisst regelmaessig am bekannten
    # dukascopy-Fehler (KeyError: 0) -- ein Datum, das dieser Test nicht
    # braucht, soll ihn auch nicht zum Scheitern bringen.
    from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_m15
    _von, _bis = "2021-01-01", ende.strftime("%Y-%m-%d")
    bars = {"h4": _robust(fetch_gold_h4, _von, _bis),
            "h1": _robust(fetch_gold_h1, _von, _bis),
            "m15": _robust(fetch_gold_m15, _von, _bis)}
    rib = ribbon_direction(bars["h4"], _robust(fetch_gold_d1, _von, _bis))
    ri = pd.to_datetime(rib.index); rib.index = ri.tz_convert(None) if ri.tz is not None else ri

    listen = {}
    # ctnl_reversal: wie live -- Ribbon-gefiltert, Deckel aus live_signal
    rep = to_live(leg_trades(bars, "ctnl_reversal", tp_r=5.0, sig_kwargs=REV_KWARGS), bars["m15"])
    t = _utc_naive(rep["entry_time"])
    rep = rep.assign(rib=rib.reindex(t, method="ffill").to_numpy())
    g = rep[((rep["direction"] == 1) & (rep["rib"] > 0)) | ((rep["direction"] == -1) & (rep["rib"] < 0))]
    listen["ctnl_reversal"] = g[_utc_naive(g["entry_time"]) >= ab.tz_localize(None)]

    # gold_asb als Gegenprobe
    try:
        ga = pb._scan_gold_asb(ende, force_refresh=False, source="live")
        ga = ga.assign(r=ga["r_multiple"])
        listen["gold_asb"] = ga[_utc_naive(ga["entry_time"]) >= ab.tz_localize(None)]
    except Exception as e:
        print(f"gold_asb-Scan fehlgeschlagen: {type(e).__name__}: {e}")

    result = {"equity_start": EQUITY_START, "jahre": args.jahre, "beine": {}}
    for leg, tr in listen.items():
        if tr.empty:
            print(f"{leg}: keine Trades im Zeitraum"); continue
        print(f"{'='*94}\n{leg}: {len(tr)} Trades im Zeitraum "
              f"(Ziel-Risiko {EQUITY_START*CAPITAL_WEIGHT*LEG_RISK[leg]:.2f} EUR/Trade)\n{'='*94}")
        mit = simuliere(tr, leg, anheben=True)
        ohne = simuliere(tr, leg, anheben=False)
        result["beine"][leg] = {"mit_anhebung": {k: v for k, v in mit.items() if k != "_df"},
                                "ohne_anhebung": {k: v for k, v in ohne.items() if k != "_df"}}
        print(f"  {'':28} {'MIT Anhebung (Realitaet)':>26} {'ohne (Bruchteils-Lots)':>24}")
        zeilen = [
            ("Trades gehandelt", f"{mit['gehandelt']}", f"{ohne['gehandelt']}"),
            ("davon angehoben", f"{mit['gebumpt']} ({mit['anteil_gebumpt']:.0%})", "0"),
            ("vom 5-%-Deckel abgelehnt", f"{mit['abgelehnt_5pct']}", f"{ohne['abgelehnt_5pct']}"),
            ("Risiko je Trade (Median)", f"{mit['risiko_median_eur']:.2f} EUR"
                if mit['risiko_median_eur'] else "-", f"{ohne['risiko_median_eur']:.2f} EUR"
                if ohne['risiko_median_eur'] else "-"),
            ("  = % der Equity", f"{mit['risiko_median_pct']:.2%}" if mit['risiko_median_pct'] else "-",
                f"{ohne['risiko_median_pct']:.3%}" if ohne['risiko_median_pct'] else "-"),
            ("Anhebungsfaktor Median", f"{mit['faktor_median']:.0f}x" if mit['faktor_median'] else "-", "-"),
            ("Anhebungsfaktor max", f"{mit['faktor_max']:.0f}x" if mit['faktor_max'] else "-", "-"),
            ("Endkapital", f"{mit['equity_ende']:,.0f} EUR", f"{ohne['equity_ende']:,.0f} EUR"),
            ("Rendite", f"{mit['rendite_pct']:+,.1f} %", f"{ohne['rendite_pct']:+,.2f} %"),
            ("max. Drawdown", f"{mit['max_dd_pct']:.1f} %", f"{ohne['max_dd_pct']:.2f} %"),
        ]
        for a, b, c in zeilen:
            print(f"  {a:28} {b:>26} {c:>24}")
        print()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Geschrieben: {args.out}")


if __name__ == "__main__":
    main()
