# Resource: TradingAgents (TauricResearch) – Workflow-Auswertung

Am 2026-11-12 installiert und getestet (Nutzerauftrag: „was können wir vom Workflow übernehmen“).
Ziel ist der Makro-Agent (Dachprojekt [[quant-diskretionaer-fusion]], Strang 3,
Ablauf [[makro-agent-report-pruefung]]), nicht der Einsatz des Frameworks selbst.

## Was es ist

Open-Source-Multi-Agenten-Framework (LangGraph, v0.7.1, Stand 04.11.2026). Ein Lauf = ein Ticker an
einem Tag → Rating Buy / Overweight / Hold / Underweight / Sell. Rollen:

1. **Analysten (parallel):** Markt (Indikatoren), Sentiment (Reddit/News), News, Fundamentaldaten.
   Jeder ruft Daten-Tools (yfinance / Alpha Vantage) in begrenzten Runden (`max_tool_rounds`).
2. **Bull vs. Bear:** debattieren über die Analystenberichte, N Runden.
3. **Research Manager** (starkes Modell) entscheidet die Debatte → Investmentplan.
4. **Trader:** macht daraus einen Handelsvorschlag.
5. **Risiko-Debatte:** aggressiv / konservativ / neutral, N Runden.
6. **Portfolio Manager** (starkes Modell) → finales Rating als typisierte Ausgabe (JSON-Schema).
7. **Memory Log:** Entscheidung wird als „pending“ in eine Markdown-Datei geschrieben. Nach
   `holding_period_days` (Standard 5) wird abgerechnet: Rendite + Alpha gegen Benchmark, dann schreibt
   ein LLM 2–4 Sätze „Lektion“. Die letzten 5 Lektionen zum selben Ticker + 3 zu anderen werden beim
   nächsten Lauf in die Prompts von Research Manager und Portfolio Manager eingespielt.

Zwei Modellstufen: „quick“ (Analysten, Debatten) und „deep“ (Manager-Entscheide). Anbieter frei
wählbar (Anthropic, OpenAI, Google, Bedrock, lokale Endpunkte).

## Test (12.11.2026)

- Installation in `C:\Users\andre\scratch\tradingagents\` (eigene venv, außerhalb des Repos).
- Offline-Testsuite: 1.407 bestanden, 6 übersprungen (POSIX-only / Bedrock).
- Kompletter Graph-Lauf für **XAUUSD** am 06.11.2026 mit einem zählenden Platzhalter-LLM (kein API-Key
  vorhanden, keine Kosten): läuft durch, Rating + Memory-Eintrag werden geschrieben.
  **12 LLM-Aufrufe** bei je 1 Debattenrunde und ohne Tool-Runden. Mit echtem Modell kommen pro
  Analyst 1–N Tool-Runden dazu → grob 20–30 Aufrufe je Ticker und Tag.
- Echte Daten: XAUUSD wird auf **GC=F (Future)** umgemappt, EURUSD auf EURUSD=X. Kurse kamen sauber.
  Yahoo-News nur für die letzten Tage, Reddit-RSS mit HTTP 403 → historische Läufe haben praktisch
  keine News.
- **Echter Lauf mit LLM noch nicht gemacht** – braucht einen API-Key (z. B. Anthropic) und kostet je
  Lauf geschätzt einige Cent bis ~1 USD, je nach Modell.

## Bewertung

**Als Signalquelle für uns ungeeignet:**

- Kein Edge-Nachweis möglich, denn rückwirkende Läufe sind durch das Modellwissen verseucht
  (Memory „LLM-Agent nur vorwärts testbar“). Das eingebaute `backtest.py` misst nur Ratings gegen
  5-Tage-Alpha und sagt selbst, dass es keine Ausführung simuliert.
- Auf Aktien zugeschnitten (Fundamentaldaten, Reddit, SPY-Benchmark). FX/Gold laufen technisch, aber
  inhaltlich dünn: keine Zinsdifferenzen, kein COT, keine Zentralbanken, kein Kalender.
- Rating auf 5-Tage-Sicht, ohne Einstieg, Stop oder Größe. Unsere Evidenz sagt: Richtung bei
  Markteinstieg ≈ 0 R, der Edge liegt im Limit-Preis (Memory „C2-Edge liegt im Limit-Preis“,
  [[smh-makro-reports-backtest]]).

**Workflow-Bausteine, die sich übernehmen lassen** (Vorschläge, nicht entschieden):

1. **Entscheidungs-Log mit Abrechnung und Lektion.** Jeder Makro-Agent-Report schreibt seine Calls als
   „pending“ in ein Log. Nach fester Frist wird automatisch mit unseren Lake-Daten abgerechnet
   (R statt Alpha), dann eine kurze Lektion. Die Lektionen fließen nur dann in den nächsten Report,
   wenn ihr Ausgang am Report-Datum schon bekannt war (`resolution_date ≤ as_of`, ihr Point-in-time-
   Filter). Das ist genau der Forward-Test, den Memory „LLM-Agent nur vorwärts testbar“ fordert, und
   speist zusätzlich das Lernen. Gefahr: Lektionen aus n=1 sind Rauschen → Lektionen nur als Hinweis,
   Regeländerungen weiter nur über die [[overfitting-sperre]].
2. **Pflicht-Gegenposition vor dem Entscheid.** Bull/Bear-Debatte als fester Schritt zwischen
   „Faktencheck“ (Schritt 2) und „Gewichten“ (Schritt 4) unseres Ablaufs: Für jeden Trade-Kandidaten
   schreibt ein eigener Durchlauf den besten Gegen-Fall aus unseren Daten. Billig, passt zu
   Schritt 3 „Widersprüche suchen“.
3. **Zwei Modellstufen.** Datensammeln und Zusammenfassen mit kleinem Modell, nur Gewichtung und
   Trade-Ableitung mit starkem Modell. Senkt die Kosten bei täglichem Lauf.
4. **Typisierte Endausgabe.** Finale Entscheidung als festes JSON-Schema (Rating, Begründung,
   Ungültigkeit), Markdown nur daraus gerendert. Bei uns: Trade-Tabelle aus Schritt 5 als Schema
   (Trade, Wertung, Limit, Stop, Ziel, Größe, Ungültigkeit, Sperrzeiten) → direkt loggbar und
   abrechenbar (Baustein 1).
5. **„Kein Beleg“ statt Lücke.** Fehlende Daten werden ausdrücklich als „nicht verfügbar, nicht
   abwesend“ in den Prompt geschrieben (siehe News-Ausgabe oben). Passt zum Korb „? nicht prüfbar“ in
   unserem Faktencheck.
6. **Checkpoint/Resume** je Lauf (SQLite): ein abgebrochener Lauf setzt am letzten Knoten fort.
   Nützlich, wenn der Makro-Agent als geplanter Task läuft (vgl. Dukascopy-Abbrüche).

**Nicht übernehmen:** die Risiko-Debatte aggressiv/konservativ/neutral (Risiko ist bei uns Code,
Risk-Gate nur verschärfend, siehe Sechs-Bot-Idee in der Ideen-Inbox vom 09.10.); die Datenanbieter
(yfinance/Reddit); das Framework als Abhängigkeit (LangGraph + 3 Anbieter-SDKs, für unseren Bedarf
reicht ein schlanker eigener Ablauf mit dem Claude-Abo/SDK).
