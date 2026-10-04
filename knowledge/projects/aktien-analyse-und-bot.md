# Project: Automatisierte Aktienanalyse + Aktienbot

**Ziel**: Eine automatisierte Aktienanalyse ähnlich der KI von Investing.com
(Fair Value, Kennzahlen-Scoring, News-/Earnings-Zusammenfassung), aber
nachprüfbar und backtestbar statt Blackbox. Darauf aufbauend ein Aktienbot
mit Ausführung.

**Status**: **Geparkt bis die Makro-Basis steht** (Nutzerentscheid
2026-10-04). Eigenes Projekt, getrennt vom FX-/Rohstoff-Teil des
Dachprojekts [[quant-diskretionaer-fusion]], baut aber auf dessen
Makro-Strang auf.

## Bisheriger Stand der Überlegungen

- **Datenquellen (frei)**: yfinance (Kurse, Fundamentaldaten), SEC EDGAR
  (Pflichtmeldungen, 10-K/10-Q/8-K), FRED (Makro), News per Websuche.
- **Anthropic-Finanzangebot**: die fertigen Datenconnectors (S&P Capital IQ,
  FactSet, Morningstar u.a.) sind kostenpflichtige institutionelle Abos und
  hier nicht verbunden -- nicht als gegeben annehmen.
- **Ausführung**: Alpaca Paper-Trading (offizieller MCP-Server
  `alpacahq/alpaca-mcp-server`, siehe
  [[agentisches-research-system-und-self-learning-bot]]).
- Gleiche Freigabe-Gates (3 Stufen) wie im Dachprojekt.

## Nächster Schritt

Nichts, bis Strang 3 (Makro-Analyse) des Dachprojekts läuft.
