"""Freshness-Kontrollebene fuer den Data Lake -- getrennt von der eigentlichen
Marktdaten-Ablage (storage.py), gleiches Prinzip wie die bestehenden
State-Dateien im Projekt (challenge_portfolio_logs/paper_state.json,
Funded-Portfolio-Bridge/bridge_state_*.json): ein kleines JSON pro Konto/
Domaene statt einer eigenen DB. EIN Eintrag pro (source, key, timeframe).

Ein fehlgeschlagener Ingest-Versuch aktualisiert NUR last_attempt_at/
last_error -- last_success_at und die gespeicherte Parquet-Datei bleiben
unangetastet (gleiche Philosophie wie combined_strategy.data.
validate_ohlc_numeric: ein Fehlversuch wird nie persistiert)."""

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "data_lake_store" / "manifest.json"
_LOCK_PATH = MANIFEST_PATH.with_suffix(".lock")
_LOCK_STALE_SECONDS = 30  # ein record_success/failure-Zyklus dauert Millisekunden -- alles
# Aeltere ist ein verwaister Lock von einem abgestuerzten Prozess, kein echtes Halten.
_LOCK_WAIT_TIMEOUT_SECONDS = 10


@contextmanager
def _locked():
    """Fund 2026-09-06 (Data-Lake-Pilot, live beobachtet): DataLake-Ingest-Fast/
    -Fast5/-Slow koennen sich zeitlich ueberlappen (siehe Scheduled-Task-
    Zeiten) und schrieben bisher ALLE ohne gegenseitige Sperre in dieselbe
    manifest.json -- storage.py's Tmp-Datei-plus-Rename schuetzt nur vor
    einem HALB geschriebenen Read, nicht vor zwei gleichzeitigen Schreibern,
    die denselben Tmp-Dateinamen benutzen. Real aufgetreten: manifest.json
    enthielt zwei aneinandergehaengte JSON-Objekte, jeder is_fresh()/
    get_entry()-Aufruf crashte -- legte damit ALLE 6 Funded-Portfolio-Bridge-
    Beine lahm, bis von Hand repariert. Gleiches os.O_CREAT|O_EXCL-Muster wie
    Funded-Portfolio-Bridge/run_once.py::account_state_lock() (dort fuer
    denselben Bug bei bridge_state_*.json bereits eingebaut)."""
    deadline = time.monotonic() + _LOCK_WAIT_TIMEOUT_SECONDS
    while True:
        try:
            fd = os.open(_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - _LOCK_PATH.stat().st_mtime > _LOCK_STALE_SECONDS:
                    _LOCK_PATH.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue  # zwischen stat() und unlink() von einem anderen Prozess schon freigegeben
            if time.monotonic() > deadline:
                raise TimeoutError(f"manifest.lock nach {_LOCK_WAIT_TIMEOUT_SECONDS}s weiterhin von einem anderen Prozess gehalten.")
            time.sleep(0.1)
    try:
        yield
    finally:
        _LOCK_PATH.unlink(missing_ok=True)

# Cutoff-Klassen: wie alt darf last_success_at fuer einen gegebenen Timeframe
# hoechstens sein, bevor reader.py die Daten als zu alt fuer eine LIVE-
# Entscheidung ablehnt? Bewusst deutlich UNTER Funded-Portfolio-Bridge/
# run_once.py::MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY (60) gehalten, damit ein
# stiller Lake-Ausfall als EIGENER, klar zuordenbarer Scan-Fehler auffaellt,
# statt 5 Minuten spaeter unter einem irrefuehrenden "Signal zu alt"
# verschwunden zu sein.
_FAST_TIMEFRAMES = {"M1", "M5", "M15", "H1", "H4"}
_STALENESS_MINUTES = {
    "fast": 35,     # M1/M5/M15/H1/H4, 15-Min-Ingestion
    "daily": 240,   # D1/W1, seltener noetig
    "slow": 90,     # OU-Modell/yfinance, stuendliche Ingestion
}


def cutoff_class_for(timeframe: str) -> str:
    if timeframe in _FAST_TIMEFRAMES:
        return "fast"
    if timeframe in ("D1", "W1"):
        return "daily"
    return "slow"


def _load() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = MANIFEST_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp_path.replace(MANIFEST_PATH)


def _manifest_key(source: str, key: str, timeframe: str) -> str:
    return f"{source}:{key}_{timeframe}"


def record_success(source: str, key: str, timeframe: str, last_bar_ts, n_rows: int, origin: str = "dukascopy") -> None:
    """`origin` (2026-09-06, Twelve-Data-Backup): welche Quelle DIESEN Erfolg
    tatsaechlich geliefert hat -- "dukascopy" im Normalfall, "twelvedata" nach
    einem Failover. Immer unter demselben (source,key,timeframe)-Schluessel
    gespeichert (source bleibt "dukascopy" fuers Storage-Verzeichnis, siehe
    ingest.py) -- reader.py braucht dadurch KEINE Fallback-Logik, es liest
    weiterhin einfach denselben Platz. `consecutive_failures` wird bei jedem
    Erfolg (unabhaengig von der Quelle) auf 0 zurueckgesetzt."""
    with _locked():
        data = _load()
        now = datetime.now(timezone.utc).isoformat()
        data[_manifest_key(source, key, timeframe)] = {
            "last_attempt_at": now, "last_success_at": now, "last_error": None,
            "last_bar_ts": str(last_bar_ts), "n_rows": n_rows,
            "consecutive_failures": 0, "last_source_used": origin,
        }
        _save(data)


def record_failure(source: str, key: str, timeframe: str, error: str) -> int:
    """Gibt die neue consecutive_failures-Zahl zurueck -- ingest.py entscheidet
    darauf basierend, ob ein Twelve-Data-Failover-Versuch faellig ist (siehe
    dortige FAILOVER_AFTER_N_FAILURES-Schwelle)."""
    with _locked():
        data = _load()
        mkey = _manifest_key(source, key, timeframe)
        entry = data.get(mkey, {"last_success_at": None, "last_bar_ts": None, "n_rows": None, "consecutive_failures": 0})
        entry["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
        entry["last_error"] = error
        entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
        data[mkey] = entry
        _save(data)
        return entry["consecutive_failures"]


def is_fresh(source: str, key: str, timeframe: str) -> bool:
    """False sowohl bei komplett fehlendem Eintrag (noch nie erfolgreich
    ge-ingest-et) als auch bei einem zu alten last_success_at -- reader.py
    unterscheidet die beiden Faelle nicht weiter, beide fuehren zum selben
    "Lake-Daten nicht verfuegbar/zu alt"-Scan-Fehler."""
    data = _load()
    entry = data.get(_manifest_key(source, key, timeframe))
    if entry is None or entry.get("last_success_at") is None:
        return False
    last_success = datetime.fromisoformat(entry["last_success_at"])
    max_age = timedelta(minutes=_STALENESS_MINUTES[cutoff_class_for(timeframe)])
    return datetime.now(timezone.utc) - last_success <= max_age


def get_entry(source: str, key: str, timeframe: str) -> dict | None:
    return _load().get(_manifest_key(source, key, timeframe))
