"""Ingestion-Task fuer den Funded-Portfolio-Bridge Data-Lake-Pilot -- zieht
JEDE Quelle aus sources.py GENAU EINMAL pro Lauf, validiert (reuse von
combined_strategy.data.validate_ohlc_numeric statt Neuimplementierung),
schreibt inkrementell in den Lake (storage.write_bars, nie das komplette
Fenster neu) und pflegt die Freshness-Manifest (manifest.py).

Aufruf: `python -m data_lake.ingest --universe fast` (alle 15 Min. geplant,
Dukascopy/TradingView-Beine), `--universe fast5` (alle 5 Min., NUR die
M5/M15-Timing-kritischen Keys fuer ctnl_continuation/orb, siehe sources.py's
`lane="fast5"`-Eintraege und Funded-Portfolio-Bridge/run_once_fast.py) oder
`--universe slow` (stuendlich, OU-Modell/yfinance -- siehe sources.py-
Docstring, warum diese getrennte, seltenere Kadenz noetig ist). Ein
fehlgeschlagener Key blockiert NIE die anderen -- jede (source,key,timeframe)
laeuft in ihrem eigenen try/except, siehe Plan-Dokument Abschnitt
"Failure/fallback"."""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from combined_strategy.data import validate_ohlc_numeric  # noqa: E402
from data_lake import manifest, sources, storage  # noqa: E402
from data_lake import twelvedata_source  # noqa: E402
from data_lake.retry_util import retry  # noqa: E402

log = logging.getLogger("data_lake.ingest")

# 2026-09-06 (Nutzerauftrag, "Backup-Datenquelle falls Dukascopy weiterhin
# haengt"): ab wie vielen AUFEINANDERFOLGENDEN Dukascopy-Fehlversuchen fuer
# denselben Key wird Twelve Data als Ueberbrueckung versucht. Bewusst
# reaktiv statt jeden Zyklus parallel abzufragen -- das kostenlose 800/Tag-
# Kontingent reicht sonst nicht fuer alle 24 Keys (siehe twelvedata_source.py
# Docstring fuer die Rechnung).
FAILOVER_AFTER_N_FAILURES = 2

_OVERLAP_DAYS = 2  # kleine Ueberlappung beim inkrementellen Nachziehen, deckt einen beim letzten
# Lauf noch nicht abgeschlossenen Balken ab -- storage.write_bars dedupliziert per Index ohnehin.

_OHLC_COLUMN_SETS = (
    ["Open", "High", "Low", "Close"],
    ["open", "high", "low", "close"],
)


def _validate(df: pd.DataFrame, label: str) -> None:
    for cols in _OHLC_COLUMN_SETS:
        if all(c in df.columns for c in cols):
            validate_ohlc_numeric(df, cols)
            return
    log.warning("%s: keine erkennbaren OHLC-Spalten (%s) -- Validierung uebersprungen.", label, list(df.columns))


def _fetch_window(entry: "sources.LakeSource", now: pd.Timestamp) -> tuple[str, str]:
    end_str = (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    existing = storage.read_bars(entry.source, entry.key, entry.timeframe)
    if existing is None or existing.empty:
        start = now - pd.Timedelta(days=max(entry.lookback_days, 1))
    else:
        last_bar_ts = existing.index.max()
        if getattr(last_bar_ts, "tzinfo", None) is not None:
            last_bar_ts = last_bar_ts.tz_localize(None)
        start = last_bar_ts - pd.Timedelta(days=_OVERLAP_DAYS)
    return start.strftime("%Y-%m-%d"), end_str


def _try_twelvedata_failover(entry: "sources.LakeSource", label: str, n_failures: int) -> bool:
    """Rueckgabe True, wenn Twelve Data erfolgreich uebernommen hat (Aufrufer
    muss dann NICHTS weiter tun -- Erfolg ist schon vollstaendig verbucht)."""
    if n_failures < FAILOVER_AFTER_N_FAILURES:
        return False
    if not twelvedata_source.is_covered(entry.key):
        log.info("%s: %dx in Folge gescheitert, aber Twelve Data deckt diesen Key nicht ab -- kein Failover moeglich.", label, n_failures)
        return False
    try:
        df = twelvedata_source.fetch(entry.key, entry.timeframe)
        _validate(df, f"{label} (twelvedata-Failover)")
        merged = storage.write_bars(entry.source, entry.key, entry.timeframe, df)
        manifest.record_success(entry.source, entry.key, entry.timeframe, merged.index.max(), len(merged), origin="twelvedata")
        log.warning("%s: Dukascopy %dx gescheitert -- Twelve-Data-Failover erfolgreich, %d Zeilen, letzter Balken %s",
                    label, n_failures, len(merged), merged.index.max())
        return True
    except Exception as e:
        log.error("%s: Twelve-Data-Failover ebenfalls gescheitert: %s", label, e)
        return False


def ingest_one(entry: "sources.LakeSource", now: pd.Timestamp) -> None:
    label = f"{entry.source}:{entry.key}_{entry.timeframe}"
    start_str, end_str = _fetch_window(entry, now)
    try:
        df = retry(lambda: entry.fetch(start_str, end_str, True))
        if df is None or df.empty:
            raise ValueError("leerer DataFrame")
        _validate(df, label)
        merged = storage.write_bars(entry.source, entry.key, entry.timeframe, df)
        manifest.record_success(entry.source, entry.key, entry.timeframe, merged.index.max(), len(merged))
        log.info("%s: OK, %d Zeilen gesamt, letzter Balken %s", label, len(merged), merged.index.max())
    except Exception as e:
        n_failures = manifest.record_failure(entry.source, entry.key, entry.timeframe, str(e))
        log.error("%s: FEHLGESCHLAGEN (%dx in Folge): %s", label, n_failures, e)
        _try_twelvedata_failover(entry, label, n_failures)


def ingest_fast() -> None:
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    for entry in sources.FAST_SOURCES:
        if entry.lane != "fast":
            continue  # 2026-09-0X: FAST_SOURCES enthaelt jetzt auch lane="fast5"-Eintraege (siehe
            # sources.py) -- ohne diesen Filter wuerde ingest_fast() sie ZUSAETZLICH zur eigenen
            # ingest_fast5() anfassen, beide races auf demselben storage.write_bars()-Tmp-Dateinamen
            # (nicht PID-eindeutig, siehe storage.py).
        ingest_one(entry, now)


def ingest_fast5() -> None:
    """5-Minuten-Kadenz NUR fuer die M5/M15-Timing-kritischen Keys, die
    ctnl_continuation/orb brauchen (siehe sources.py-Kommentare bei den
    lane="fast5"-Eintraegen und Funded-Portfolio-Bridge/run_once_fast.py).
    Disjunkt von ingest_fast()'s 15-Minuten-Kadenz -- nie dieselbe
    (source,key,timeframe)-Datei aus beiden Kadenzen gleichzeitig anfassen."""
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    for entry in sources.FAST_SOURCES:
        if entry.lane != "fast5":
            continue
        ingest_one(entry, now)


def ingest_slow() -> None:
    """OU-Modell: ~163 Ticker, jeder einzeln ueber yfinance -- ein
    fehlschlagender Ticker darf die anderen nie blockieren. Speichert unter
    source="yfinance", ein Parquet pro Ticker (timeframe="D1", identisch zu
    ou_paper_backtest/data.py::get_prices()'s Ein-Datei-pro-Ticker-Muster)."""
    import yfinance as yf

    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    end_str = (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    tickers = sources.ou_modell_tickers()
    log.info("OU-Modell: %d Ticker zu aktualisieren.", len(tickers))
    for ticker in tickers:
        label = f"yfinance:{ticker}_D1"
        existing = storage.read_bars("yfinance", ticker, "D1")
        if existing is None or existing.empty:
            start_str = (now - pd.Timedelta(days=460)).strftime("%Y-%m-%d")
        else:
            last_bar_ts = existing.index.max()
            if getattr(last_bar_ts, "tzinfo", None) is not None:
                last_bar_ts = last_bar_ts.tz_localize(None)
            start_str = (last_bar_ts - pd.Timedelta(days=_OVERLAP_DAYS)).strftime("%Y-%m-%d")
        try:
            df = retry(lambda: yf.download(ticker, start=start_str, end=end_str, auto_adjust=True, progress=False))
            if df is None or df.empty:
                raise ValueError("leerer DataFrame")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            _validate(df, label)
            merged = storage.write_bars("yfinance", ticker, "D1", df)
            manifest.record_success("yfinance", ticker, "D1", merged.index.max(), len(merged), origin="yfinance")
        except Exception as e:
            manifest.record_failure("yfinance", ticker, "D1", str(e))
            log.error("%s: FEHLGESCHLAGEN: %s", label, e)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", choices=["fast", "fast5", "slow"], required=True)
    args = parser.parse_args()

    if args.universe == "fast":
        ingest_fast()
    elif args.universe == "fast5":
        ingest_fast5()
    else:
        ingest_slow()
    return 0


if __name__ == "__main__":
    sys.exit(main())
