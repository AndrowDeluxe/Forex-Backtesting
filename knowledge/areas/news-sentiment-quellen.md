# Area: News- und Sentiment-Quellen + Quellen-Ledger

Seit 2026-11-21 (Nutzerentscheid, Plan „Prosper Lektion 5 mit Claude statt Grok“). Code:
`fusion_lab/news_sources/`, Tests `tests/test_news_sources.py`, Task „News-Sources-Ledger“ (täglich 22:30,
`scripts/news_sources_task.ps1`). Speist das Prosper-Kursprojekt als Research-Provider anstelle von Grok
([[prosper-education-uebernahme]] Planpunkt 4).

## Warum

Grok bringt zwei Dinge: (1) Auswertung gelieferter Texte, (2) Live-Zugriff auf X. (1) macht hier Claude über das
Abo (`claude.exe -p`), ohne Zusatzkosten. (2) ist nicht nachbaubar (X-API kostenpflichtig); StockTwits und
Reddit sind der freie, gröbere Ersatz. Ziel: messen, **welche Quelle trägt und welche nicht**.

## Quellen (Stand 21.11.2026, live geprüft)

| Quelle | Gruppe | Status | Bemerkung |
|---|---|---|---|
| Google-News-RSS je Symbol | news (Text) | ok | Parser aus `macro_data/geo.py` |
| Zentralbank-RSS Fed/EZB/BoE/BoJ | offiziell (Text) | ok | Fed-RSS hat ein BOM, als Bytes parsen |
| SEC EDGAR (8-K/10-Q/10-K) | offiziell (Text) | ok | `data.sec.gov/submissions` |
| StockTwits | social (Text + Zahl) | ok | Bull/Bear-Anteil der letzten 30 Nachrichten, auch FX/Gold; gelegentlich 403 (Rate-Limit) |
| CNN Fear & Greed + Put/Call-Teilwert | Zahl (auf SPY) | ok | inoffizieller Endpunkt |
| Krypto Fear & Greed (alternative.me) | Zahl (auf BTC) | ok | |
| Finnhub Company News | news (Text) | ok (Key seit 21.11.) | Sentiment-Endpunkt kostet, nur News gratis |
| Alpha Vantage News-Sentiment | Zahl | kostenpflichtig | Gratis-Key bekommt „premium endpoint“ (21.11.); Sammler bricht nach der ersten Antwort ab |
| Reddit | social (Text) | nicht konfiguriert | ohne Login 403/429; App-Anlage scheitert mit „Max clients have been reached“ (21.11.) |
| AAII-Umfrage | – | blockiert (403) | nicht eingebaut |
| GDELT | – | für unsere IP gesperrt seit 12.11. | nicht eingebaut |

## Regeln

- **Claude ordnet nur ein.** Ein Aufruf für alle Symbole, getrennt nach Gruppe (news / social / offiziell),
  Stimmung −2…+2 mit zitierten Eintrags-IDs. Validator verwirft erfundene IDs, Gruppen ohne Einträge und fremde
  Märkte und warnt bei Zahlen, die nicht in den zitierten Quellen stehen.
- **Ledger nur anhängen**, erster Lauf je Tag zählt (`ledger/werte.csv`, Status je Lauf in `ledger/laeufe.csv`).
- **Kein Vorgriff:** Folgerendite ab dem ersten Schlusskurs NACH dem Aufzeichnungstag, Horizonte 1/3/5/10 Tage.
- **Wochenende läuft mit** (Task täglich, auch Sa/So): Krypto handelt durch, der Sonntagslauf 22:30 ist der Stand
  kurz vor der FX-Eröffnung. Bei Aktien/FX teilen sich Sa und So denselben Montags-Startkurs; die Auswertung
  zählt dann nur den letzten Wert (Sonntag), sonst würde die Trefferquote doppelt gezählt.
- Reddit: Nutzer versucht die App-Anlage in ein paar Tagen erneut (Stand 21.11.).
- **Kontrolle gegen die Marktrichtung:** „vorsprung“ = Trefferquote minus bester Wert aus immer long/immer short.
  Eine Quelle trägt nur, wenn der Vorsprung über Monate positiv bleibt (ab ~60 Beobachtungen je Quelle).
- **LLM-Einordnung ist nur vorwärts testbar** (Memory „LLM-Agent nur vorwärts testbar“).
- Auswertung: `python -m fusion_lab.news_sources report`.

## Später

Makro-Agent als eigener „Macro Analyst“ andocken, sobald die Wirkketten stehen (Plan Phase C); dann
Filter-Wirkung (mit/ohne) im selben Ledger-Stil vorwärts messen. Für Forex echte FX-Kurse aus dem Data Lake.
