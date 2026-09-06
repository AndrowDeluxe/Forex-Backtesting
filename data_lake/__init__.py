"""Lokaler Data Lake fuer Funded-Portfolio-Bridge (Pilot, 2026-09-03) --
siehe C:\\Users\\andre\\.claude\\plans\\resilient-painting-raven.md fuer den
vollen Kontext/Entwurf. Ein eigener, geplanter Ingestion-Task (siehe
ingest.py) zieht die Marktdaten, validiert sie (validation ist ein
Code-Schritt, siehe combined_strategy.data.validate_ohlc_numeric, keine
eigene "raw"-Ablage -- die bestehenden Fetch-Funktionen liefern nie
ungueltige Daten zurueck, sie werfen stattdessen), und schreibt sie EINMAL
normalisiert (reader.py macht pro Aufrufer die passende Spalten-/Zeitzonen-
Form daraus) nach data_lake_store/ (gitignored, wie data_cache/). Bots lesen
nur noch ueber reader.py, fragen nie mehr selbst Dukascopy/TradingView/
yfinance direkt an."""
