"""Taeglicher Abruf der Datenschicht. Faellt eine Quelle aus oder haengt sie, laufen die
anderen weiter; Exit-Code 1, sobald eine Quelle fehlt (steht im Log des Daten-Tasks)."""

from __future__ import annotations

import argparse
import json
import sys
import threading

import pandas as pd

from . import calendar, calendar_values, sources, store

SOURCE_TIMEOUT_S = 300
JOBS = {
    "kalender": None,
    "ff_historie": None,  # Ist-Werte fuer Ueberraschungs-Faktor und Kalender-Ersatzwerte
    "kalender_werte": ("macro", calendar_values.fetch_calendar_values),  # nach "kalender", liest dessen Archiv
    "fred": ("macro", sources.fetch_fred),
    "bis": ("macro", sources.fetch_bis),
    "bis_reer": ("macro", sources.fetch_bis_reer),
    "snb_kern": ("macro", sources.fetch_snb_core),
    "oecd": ("macro", sources.fetch_oecd),
    "ecb": ("macro", sources.fetch_ecb),
    "eurostat": ("macro", sources.fetch_eurostat),
    "renditen_jp": ("macro", sources.fetch_yields_mof),
    "renditen_ca": ("macro", sources.fetch_yields_boc),
    "renditen_ch": ("macro", sources.fetch_yields_snb),
    "renditen_au": ("macro", sources.fetch_yields_rba),
    "renditen_gb_nz": ("macro", sources.fetch_yields_tvc),
    "cftc": ("positioning", sources.fetch_cftc),
    "fed_futures": ("markets", sources.fetch_fed_futures),
    "maerkte": ("markets", sources.fetch_yf_markets),
    "fx": ("markets", sources.fetch_duka_fx),
}
# Soll je Land: fehlt oder ist alt -> Luecke im Abdeckungsbericht. Tage = erlaubtes Alter.
# Datum = Periodenbeginn, darum grosszuegig: Q2 hat Datum 01.04. und ist im Oktober aktuell.
# Leitzins 45 Tage: er gilt bis zur naechsten Sitzung (~6 Wochen), Entscheide kommen aus dem Kalender.
COVERAGE = {"policy_rate": 45, "1y": 10, "2y": 10, "10y": 75, "cpi_yoy": 75, "core_yoy": 135,
            "services_yoy": 135, "unemployment": 135, "gdp_qoq": 230, "exports": 135, "trade_balance": 135,
            "reer": 75}
FF_WEEKS_BACK = 5  # FF-Historie: nur abgeschlossene Wochen, schon geladene ueberspringt das Skript


def run_job(name: str) -> dict:
    if name == "kalender":
        return {"neu": calendar.append_events(calendar.fetch_events())}
    if name == "ff_historie":
        import subprocess
        start = (pd.Timestamp.today() - pd.Timedelta(weeks=FF_WEEKS_BACK)).strftime("%Y-%m-%d")
        done = subprocess.run([sys.executable, "-m", "scripts.remy_ff_history", "--start", start],
                              cwd=calendar_values.ROOT, capture_output=True, text=True, timeout=SOURCE_TIMEOUT_S - 10)
        if done.returncode:
            raise RuntimeError(done.stderr.strip()[-300:])
        return {"ausgabe": done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""}
    area, fetch = JOBS[name]
    df = fetch()
    return {"neu": store.append(area, df), "reihen": int(df["key"].nunique())}


def run_with_timeout(name: str) -> dict:
    result: dict = {}

    def target():
        try:
            result.update(run_job(name))
        except Exception as e:  # eine Quelle darf die anderen nicht mitreissen
            result["fehler"] = f"{type(e).__name__}: {e}"[:300]

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(SOURCE_TIMEOUT_S)
    if thread.is_alive():
        return {"fehler": f"Zeitlimit {SOURCE_TIMEOUT_S} s"}
    return result


def coverage(today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Letztes Datum je Land und Groesse (Hauptreihe samt Ersatzwerten, siehe calendar_values);
    Luecken und ueberalterte Werte sind markiert."""
    today = today if today is not None else pd.Timestamp.now().normalize()
    known = calendar_values.extend(store.latest("macro"))
    last = known.groupby("key")["date"].max() if len(known) else pd.Series(dtype="datetime64[ns]")
    rows = {}
    for quantity, max_age in COVERAGE.items():
        row = {}
        for land in sources.G8:
            date = last.get(f"{land}.{quantity}")
            if date is None:
                row[land] = "FEHLT"
            else:
                row[land] = date.strftime("%y-%m-%d") + ("" if (today - date).days <= max_age else " ALT")
        rows[quantity] = row
    return pd.DataFrame(rows).T[sources.G8]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="kommagetrennt: " + ",".join(JOBS))
    parser.add_argument("--coverage", action="store_true", help="nur Abdeckung zeigen, nichts abrufen")
    parser.add_argument("--start", help="einmaliges Nachladen ab Datum (z. B. 2009-01-01); "
                                        "schreibt last_run.json nicht, damit der Task-Status stimmt")
    args = parser.parse_args()
    if args.coverage:
        print(coverage().to_string())
        return 0
    if args.start:
        sources.START = args.start

    names = args.only.split(",") if args.only else list(JOBS)
    status = {"lauf": pd.Timestamp.now().isoformat(timespec="seconds"), "quellen": {}}
    for name in names:
        status["quellen"][name] = run_with_timeout(name)
        print(name, status["quellen"][name], flush=True)
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if args.start:
        return 1 if any("fehler" in s for s in status["quellen"].values()) else 0
    (store.DATA_DIR / "last_run.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if any("fehler" in s for s in status["quellen"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
