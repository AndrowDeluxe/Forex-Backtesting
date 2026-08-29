# Area: Paper-Portfolio-Bot-Architektur (mehrere Strategien, ein Konto)

Laufende Verantwortlichkeit ohne Enddatum -- jeder neue Paper-Forward-Test-
Bot, der mehrere bereits validierte Einzelstrategien zu EINER gemeinsamen,
kompoundierenden Papier-Equity-Kurve kombiniert (Vorbild: `gold_smc_htf_ltf/
paper_bot.py` -> `fk_instant_funding/paper_bot.py` -> `ek_portfolio/
paper_bot.py`), folgt demselben Muster. Abzugrenzen von `mt5-bot-
deployment.md` (echte MT5-Order-Ausfuehrung) -- dieser Bot-Typ sendet NIE
echte Orders, nur Telegram-Alerts + eine persistierte JSON/CSV-Kurve.

## Standard-Architektur

1. **Echte Engine wiederverwenden, nie duplizieren.** Jede Bein-Scan-
   Funktion laesst die ECHTE, bereits validierte Signal-/Backtest-Engine
   der Strategie frisch auf einem eigenen Trailing-Fenster laufen (z.B.
   `asian_range_breakout.engine.simulate_asian_breakout`,
   `strategy.backtest.simulate_trades`) -- keine zweite Implementierung
   der Entry-/Exit-Regeln. Das Fenster muss lang genug fuer die Warmup-
   Beduerfnisse DIESER Strategie sein (z.B. Gold ASB: volle Historie seit
   2016 wegen expanding Liquiditaets-Quantile) -- nicht pauschal ein
   Fenster fuer alle Beine.

2. **Ein Bein pro echtem Konto, das schon LIVE mit echtem Kapital handelt,
   bekommt KEINE Paper-Simulation** -- stattdessen die ECHTEN Tages-
   Renditen aus dessen eigenem Log einlesen (Vorbild: `ek_portfolio/
   paper_bot.py::_load_ou_modell_daily_returns` liest `ou_modell_logs/
   daily_log.csv`, keine Nachsimulation von OU-Modells ~147-Positionen-
   Engine). Eine Nachbildung waere aufwaendiger UND ungenauer als die
   echten Zahlen. Gilt als Entscheidungsregel: sobald ein Bein schon real
   auf einem eigenen Konto handelt, erst pruefen, ob seine echten Zahlen
   einlesbar sind, bevor eine Paper-Nachsimulation gebaut wird.

3. **Dedupe-Key normalisiert auf UTC-naiv.** Jede Strategie liefert
   Zeitstempel in ihrer EIGENEN Zeitzonen-Konvention (America/New_York,
   Europe/Berlin, UTC, ...) -- ohne Normalisierung auf UTC-naiv crasht das
   Zusammenfuehren mehrerer Beine in EINER Trades-Tabelle mit "Mixed
   timezones detected". Trade-Key = `{leg}_{market}_{entry_time_utc_naiv.
   isoformat()}_{direction}` (market noetig, sobald ein Bein mehrere
   Instrumente teilt -- sonst koennen zwei verschiedene Instrumente mit
   zufaellig identischem entry_time+direction denselben Key erzeugen).

4. **`account_start`-Anker, einmalig beim ersten Lauf gesetzt.** Manche
   Beine brauchen Jahre an Historie fuer ihre eigene Warmup-Berechnung --
   das darf nicht heissen, dass ihre komplette Mehrjahres-Historie ins
   Paper-Konto einfliesst. Nur Trades mit `entry_time >= account_start`
   zaehlen. Ohne diesen Anker: ein Bein mit langer Historie compoundiert
   de facto seit Jahren, waehrend ein anderes erst seit Tagen mitzaehlt --
   ein bereits real aufgetretener Bug ("+32% seit heute" war in Wahrheit
   ein 10-Jahre-Backtest eines einzelnen Beins).

5. **Kapitalanteil-Verduennungsformel, EIN chronologischer Event-Stream.**
   `risk_dollars = CAPITAL_WEIGHT (1/n Beine, Equal-Weight -- siehe
   Walk-Forward-Fazit: Max-Sharpe/Mean-Variance ueberpasst sich, Equal-
   Weight generalisiert besser) x internes Risiko/Trade x AKTUELLE
   gemeinsame Equity`. Alle Beine (diskrete R-Multiple-Trades UND ein
   echtes-Tages-Rendite-Bein wie Punkt 2) werden in EINE nach Zeit
   sortierte Ereignis-Liste gemischt und sequenziell abgearbeitet -- jedes
   Ereignis bezieht sich auf die Equity VOR sich selbst, sonst ist das
   Compounding zwischen Beinen falsch. Sub-Beine, die sich ein
   "Portfolio-Bein" teilen (z.B. ORB ueber 3 Instrumente, CTNL
   Continuation+Reversal), bekommen JEWEILS die VOLLE Kapitalscheibe
   dieses einen Beins, nicht je einen Anteil davon (das interne
   Risiko/Trade jedes Sub-Beins ist bereits entsprechend klein kalibriert).

6. **Trailing-Drawdown-Floor nur aus abgeschlossenen VORTAGEN.** Der
   EOD-Hoechststand, gegen den der Floor berechnet wird, darf NIE den
   heutigen, noch laufenden Wert enthalten -- sonst passt sich der Floor
   an ein reines Intraday-Hoch des HEUTIGEN Tages an und wird nie
   gerissen, egal wie tief die Equity faellt (echter, bereits gefundener
   Bug). Heutiger Wert wird erst NACH dem Vergleich in den State
   geschrieben.

7. **Heartbeat/Digest-Dedupe ueber einen persistierten Zeitstempel-Guard**
   (`last_heartbeat_hour`/`ou_notified_dates` o.ae.), damit wiederholte
   Laeufe innerhalb derselben Stunde/desselben Tages nicht doppelt
   Telegram spammen. Sofort-Alarme (Entry/Exit/Fehler) bleiben davon
   unabhaengig und feuern bei jedem Lauf, in dem sie neu auftreten.

8. **Kein Eingriff in bereits live laufende Bridges.** Ein Paper-Bot ruehrt
   an KEINER Stelle die tatsaechlichen Order-Ausfuehrer der einzelnen
   Strategien an (liest bestenfalls deren Logs, siehe Punkt 2) -- er ist
   ein komplett separates, zusaetzliches Tracking-Modul.

## Verhaeltnis zu `mt5-bot-deployment.md`

Ein Paper-Bot kann spaeter zu einer echten Order-Bridge ausgebaut werden
(siehe EK-Portfolio-Bridge, 2026-08-28ff.) -- das ist dann ein Wechsel in
die ANDERE Area (`mt5-bot-deployment.md`), mit eigenem Terminal, eigenem
Risiko-Deckel-Design und einer expliziten, separaten User-Freigabe, bevor
`DRY_RUN` jemals auf `False` steht. Die Signal-Erkennung (Punkt 1 oben)
bleibt dabei wiederverwendbar, die Order-Ausfuehrung ist komplett neuer,
eigenstaendiger Code.
