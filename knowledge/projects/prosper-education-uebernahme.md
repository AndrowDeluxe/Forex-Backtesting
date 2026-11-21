# Project: Prosper-AI-Education → Übernahme ins eigene System

**Status:** Education läuft (seit 2026-11-21 festgehalten). **Umsetzung erst, wenn die Education durch ist**
(Nutzerentscheid 21.11.). Bis dahin wird je Lektion nur gesammelt, nichts gebaut.

**Worum es geht:** Prosper AI ist die Haupt-Education des Nutzers zum Thema KI-Trading. Am Ende wird das
Kurssystem mit unserem Stand verglichen. Was besser ist, wird übernommen oder optimiert. Unser System nutzt
andere Daten (echte Kurse, Live-Bridges). Besonders interessant für den Nutzer: die Aktienanalyse und die
Marktinformationen von Prosper.

Kurse:
- **„Grok AI Trading Team“** (13 Lektionen), lokal `C:\Users\andre\prosper-ai-grok-trading-team` (nur Simulation).
- **„AI Day Trader Quick Start“** (5 Lektionen), Lektion 4 Risk Management am 20.11. durchgearbeitet.

Verwandt: [[prosper-bot-trendregel-echtdaten]] (Kurs-Handelsregel auf echten Daten: kein Edge),
[[aktien-analyse-und-bot]] (unser Aktien-Screener, schon im Prosper-Stil), [[risk-management-bausteine]],
[[signal-hub]].

## Ablauf

1. **Education komplett durchgehen.** Je Lektion unten 3–5 Kernpunkte und „Übernehmbar?“ eintragen.
2. **Abschlussvergleich:** Kurs gegen unseren Stand, Bereich für Bereich (Dashboard, Agenten, Risiko,
   Aktienanalyse, Marktinformationen, Grok/LLM-Anbindung, Paper Trading).
3. **Umsetzungsplan** daraus (im Plan-Modus, Fragen an den Nutzer vorab), dann bauen.

**Regel für Handelslogik:** Eine Kursstrategie wird nur übernommen, wenn sie unseren
[[backtest-standard-process]] mit [[overfitting-sperre]] auf echten Daten besteht. Aufbau, Dashboard,
Abläufe und Werkzeuge dürfen direkt übernommen werden.

## Feste Planpunkte (aus Lektion 4 Dashboard, Nutzerentscheid 21.11.; Punkt 4 Nutzergedanke 21.11.)

1. **Ein zentraler Zustand, aus dem das Dashboard liest.** Prosper: ein Endpunkt `/api/state` liefert alles,
   das Frontend zeigt nur an. Bei uns heute verteilt (Bridge-States, Signal-Hub-Journal, Screener-Ledger,
   Data Lake, Makro-Agent). Ziel: eine Zustands-Schicht für Makro-Agent und Trading-System.
2. **Freigabe direkt im Dashboard.** Prosper: Approve/Reject je Vorschlag + Freigabe-Modus. Bei uns heute
   per Telegram Ja/Nein (Signal-Hub). Ziel: dieselbe Freigabe zusätzlich im Dashboard, gleiches Journal.
3. **Fehlendes beschriften statt erfinden.** Keine Platzhalter-Zahlen, keine falschen „Live“-Anzeigen. Ist
   eine Quelle nicht angeschlossen oder veraltet, steht das sichtbar da (passt zu
   [[live-abgleich-fehlerklassen]]).

4. **Jeden Bereich/Agenten von Demo- auf echte Daten umstellen** (Nutzergedanke 21.11., nach Lektion 4).
   Im Kursprojekt laufen heute alle Kategorien mit Demodaten bzw. ohne Quelle. Ziel ist ein profitables
   Gesamtsystem, in dem jeder Agent echte Daten bekommt. Erste Zuordnung (Vorschlag, beim Abschlussvergleich
   zu klären):
   | Agent / Bereich | heute | echte Quelle bei uns (Kandidat) |
   |---|---|---|
   | Market Analyst / Markt-Intelligenz | Zufallskurse | Data Lake (Dukascopy/MT5), yfinance/Binance aus `fusion_lab/screener/` |
   | News Analyst | „not connected“ (ohne Grok) | Google-News-RSS + LLM-Einordnung aus dem Screener, Wirtschaftskalender, später Grok (Lektion 5) |
   | Strategy Agent | Trendregel (auf echten Daten ohne Edge) | unsere getesteten Edges / Signal-Hub-Setups, Makro-Agent als Filter |
   | Risk Manager | Kursregeln | Bridge-Regeln je Konto (Risiko je Trade, Deckel, Kill-Switch, TTP-Tageslimit) |
   | Portfolio Manager | Paper-Broker | Paper zuerst; Live nur über die Bridges, nie direkt aus diesem Projekt |
   | Performance Analyst | Sim-Kennzahlen | Soll/Ist, Weekly-Report-Kennzahlen, Benchmark-/Long-Beta-Kontrolle |
   „Profitabel“ heißt dabei: jede Handelslogik besteht vorher den [[backtest-standard-process]]; echte Daten
   allein machen eine Regel nicht profitabel (siehe [[prosper-bot-trendregel-echtdaten]]).

5. **Prosper-Dashboard als eigener Bereich „Trading“ in die Lebens-App** (Nutzerfrage 21.11., gemeint ist die
   Lebens-App, eigenes Repo „Lebensjournal“). Empfehlung Claude, noch offen: erst, wenn es echte Kurse und echte
   (Paper-)Trades testet, nicht mit Demo-Kursen neben den Live-Bridges.

Dazu der Wunsch des Nutzers: **das Prosper-Dashboard als Vorlage** für Makro-Agent und Trading-System
(schwarz-gold, sechs Bereiche: Übersicht, Agenten-Zentrale, Markt-Intelligenz, Portfolio, Performance,
Risiko & Freigaben; „SIMULATION ONLY“-Hinweis wird bei uns zur Anzeige Live/Paper je Konto).

## Lektionen-Log

### Day Trader Quick Start, Lektion 4: Risk Management (20.11.)
- Sieben Schutzregeln: Positionslimit, Exposure, Risiko je Trade, Tageslimit, Stop, Pause nach Serie,
  Kill-Switch ohne Auto-Reset. Einstiege sperren, Ausstiege laufen immer.
- Übernehmbar? Als Prüfschritt ja (fester Teil von Phase 5 seit 20.11.). Als Regel auf unseren Beinen
  nein: auf allen Edges gerechnet, hilft fast nirgends ([[risk-management-bausteine]]).

### Grok Trading Team, Lektion 4: Dashboard (21.11.)
- Sechs Bereiche (s. o.), echte Backend-Daten statt Attrappe, Fehlendes beschriften, „SIMULATION ONLY“.
- Design: Schwarz/Anthrazit, Gold-Akzente, Grün = Plus, Rot = Minus/Warnung, schlichte Charts.
- Technik: ein `/api/state` + Schalt-Endpunkte (approve/reject/approval-mode/toggle/reset).
- „Fertig“ heißt getestet: jeden Bereich prüfen, Reload, kleiner Bildschirm.
- Übernehmbar? Ja, Aufbau und Regeln → Planpunkte 1–3.
- **Umgesetzt 21.11.** im Kursprojekt (Backup `_backup_vor_lektion4/`): `/api/state` um Übersicht, Agenten-Rolle/
  Zeitstempel/Fehler, Analysten-Werte je Symbol, Exposure, abgelehnte Einstiege, Kill-Switch, Quellen-Labels und
  bekannte Grenzen erweitert; `risk_manager.halt_reason()` als gemeinsame Regel für Risk Manager und Dashboard;
  Dashboard neu in sechs Bereichen. 19 Unit-Tests + Browser-Check 21/21 bestanden.
- Funde im Kurscode: Kill-Switch hebt sich selbst auf (wie EK), das Tageslimit misst seit App-Start statt
  seit Tagesbeginn, die Equity-Kurve lebt nur im Speicher. Im Dashboard beschriftet, nicht geändert.

### Grok Trading Team, Lektion 5: Grok anbinden (21.11.)
- Grok = optionaler Research-Baustein: wertet *gelieferte* Markt-/News-Daten aus, liefert strukturiertes JSON.
  Kann nicht handeln, den Risk Manager nicht übergehen, sich nicht selbst freigeben.
- Key nur in `.env` (`XAI_API_KEY`, `XAI_MODEL`), `.env.example` ohne Werte, nie ins Frontend/Git/Screenshot.
- Adapter: Antwort validieren, bei fehlendem/ungültigem Key oder Fehler sauber auf Offline-Modus zurückfallen.
- Dashboard zeigt echten Verbindungsstatus (verbunden / offline / Fehler) + Zeitpunkt der letzten Antwort.
- Kein Erfolg melden ohne echte Antwort. Lektion gilt auch als erledigt, wenn der Offline-Modus sauber dokumentiert ist.
- Nutzer hat keinen Grok-Zugang (kostenpflichtig). Ersatz-Idee: Claude-Abo (`claude.exe -p`, wie im Screener) als
  Research-Provider + freie, belegbare News-/Sentiment-Quellen. Einzig nicht nachbaubar: Groks Live-Zugriff auf X.
- Übernehmbar? Ja, das Muster (Provider-Adapter mit Fallback, Statusanzeige, Validierung) → Planpunkt 4.
- **Umgesetzt 21.11. (Variante a):** Claude-Abo als Research-Provider statt Grok, echte Quellen aus
  `fusion_lab/news_sources/` ([[news-sentiment-quellen]]), Forward-Ledger je Quelle. Kursprojekt-Backup
  `_backup_vor_lektion5/`. Verbindungstest: connected 01:07:59, Fehlertest: error mit Grund. Checkliste:
  Developer-Account Grok NOT SET UP (bewusst), Claude-Provider PASSED, Antwort validiert YES, Market Analyst
  bewusst regelbasiert bis Lektion 6 (Demo-Kurse), Risk Manager nicht umgehbar (Test).
