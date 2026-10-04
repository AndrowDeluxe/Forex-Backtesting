# Project: Quant × diskretionäres Trading (Dachprojekt)

**Ziel**: Die frühere diskretionäre Analyse des Nutzers (Makro, Struktur,
Planung -- das Journal ist bereits übernommen) reproduzieren, testen und das
Beste davon automatisieren. Endziel: ein voll automatisierter,
selbstlernender Bot, der auf dem Wissen des Nutzers startet, sich selbst
weiterentwickelt und profitabel handelt -- wo sinnvoll mit Agenten/
Subagenten. Börse allgemein, aber **Aktien getrennt von Forex/Rohstoffen**.

**Status**: Gestartet 2026-10-04. Aktueller Strang: **0 (Inventur /
Material-Import)**. Code-Ordner: `fusion_lab/` (Repo-Wurzel).

Löst den Dashboard-Punkt "Manuelles Monatsjournal + Quant-System-
Verschmelzung" (2026-09-02) ab -- der Journal-Teil ist laut Nutzer erledigt.

## Entscheidungen (Nutzer, 2026-10-04)

- **Notion = Cockpit + Zwischenablage** (Sichtbarkeit: Makro-Übersicht,
  Analysen, Entscheidungslog des Bots). `knowledge/` bleibt die
  verbindliche, git-gesicherte Quelle der Wahrheit -- Regeln und
  Entscheidungen werden hierher zurückgeschrieben, nicht nur in Notion.
- **Material-Import automatisch** über APIs: OneNote (Microsoft Graph),
  Telegram-Gruppen (Telethon), inkl. Mentor-Material.
- **Start mit Makro** als Basis für FX/Rohstoffe, übergreifend Aktien. Die
  Makro-Analyse des Mentors soll künftig automatisiert werden.
- **Aktienanalyse + Aktienbot = eigenes Projekt** ([[aktien-analyse-und-bot]]),
  startet erst, wenn die Makro-Basis steht.
- **Eigener Repo-Ordner `fusion_lab/`** statt separatem Repo -- vorhandene
  Makro-Bausteine bleiben direkt importierbar, ein Second Brain.

## Freigabe-Gates (3 Stufen, Nutzer bestätigt 2026-10-04)

| Stufe | Wer entscheidet | Beispiele |
|---|---|---|
| 1 | Bot/Agent autonom, mit Log + Rückgängig | Retries, Datenlücken, kleine Bugfixes in Paper-/Analyse-Code |
| 2 | Autonom, mit Telegram-Meldung | Parameter innerhalb vorher freigegebener Bandbreiten |
| 3 | Nur der Nutzer (Plan-Modus) | neue Regeln, Risiko, **alles mit echtem Geld** |

## Leitplanken

- **Strikt getrennt von den Live-Bridges**: `fusion_lab/` importiert keine
  Bridge und wird von keiner importiert (Muster siehe
  [[agentisches-research-system-und-self-learning-bot]]).
- **Makro muss sich im Test beweisen** wie jede andere Idee: der frühere
  Zins-Spread-Indikator hatte keinen Edge ([[bond-yield-spread-indikator]]).
  "Der Mentor macht es so" ist kein Mechanismus (Edge-Card-Grundregel 4).
- Rohmaterial (OneNote, Telegram) ist privat → `fusion_lab/raw/` gitignored.

## Stränge

- [ ] **0 Inventur** -- Material automatisch importieren
  (`fusion_lab/ingest/`), Bestandteile der alten Analyse listen, je mit
  Quelle (eigenes Wissen / Mentor). Ergebnis befüllt die Checkliste in
  [[persoenlicher-tradingplan-validierung]].
- [ ] **1 Edge Cards** je Bestandteil ([[edge-card-workflow]]).
- [ ] **2 Reproduzieren + Testen** -- Phasen 4-6 ([[backtest-standard-process]]).
- [ ] **3 Analyse automatisieren** -- zuerst Makro: tägliche Analyse,
  noch ohne Handel.
- [ ] **4 Sichtbarkeit** -- Notion-Cockpit: Makro-Übersicht, Analysen,
  Entscheidungslog mit dem "Warum" jeder Handlung (gleichzeitig die
  Lerndaten für Strang 7).
- [ ] **5 Ausführung auf Paper** -- FX/Rohstoffe über MT5-Demo (Aktien siehe
  [[aktien-analyse-und-bot]]).
- [ ] **6 Agentenschicht** = Strang A in
  [[agentisches-research-system-und-self-learning-bot]].
- [ ] **7 Selbstlernen** = Strang B dort; lernt aus dem Entscheidungslog,
  Änderungen laufen durch die Gates oben.

Jeder Strang bekommt beim Start einen eigenen Plan-Modus-Durchlauf.

## Wiederverwendbare Bausteine (für Strang 3)

- `bond_yield_indicator/fred.py` -- FRED-Loader
- `asian_range_breakout/cot.py` -- CFTC-COT-Positionierung
- `news_calendar/` (`fred_releases.py`, `eurostat_calendar.py`, `filter.py`) -- Wirtschaftskalender
- `ou_paper_backtest/monte_carlo.py`, `walk_forward.py`, `strategy/metrics.py` -- Phase 6
- **Unverarbeitetes Clipping `Clippings/Systematic Macro Modell 1.pdf`**
  (gefunden beim Lint 2026-10-04) -- vor Strang 3 sichten, möglicher
  Rahmen für die Makro-Automatisierung.

## Nächster Schritt

Strang 0: Nutzer legt die Zugänge an (Anleitung in `fusion_lab/README.md`):
Azure-App für OneNote, Telegram-API-Zugang, Notion-Connector in claude.ai.
Danach Vollimport, dann Inventur.
