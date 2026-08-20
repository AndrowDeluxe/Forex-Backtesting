# Area: Live-/Paper-Bot-Aufsetzung (MT5)

Laufende Verantwortlichkeit ohne Enddatum -- jede neue Strategie, die live
oder papierbasiert über eine MT5-Bridge/einen Scheduled Task läuft,
durchläuft denselben Aufsetzungs-Prozess, bevor der Task auf "Enabled"
bleibt.

**Grundregel**: ein eigenes, dediziertes MT5-Terminal (eigene Installation/
eigenes Verzeichnis, analog `C:\Users\andre\MT5-Terminals\MT5 Terminal -
FK1` / `- FK2` / `TTP MT5 Terminal - Konto2`) pro Bot/Konto. Nie mehrere
Bots/Bridges über dieselbe gerade laufende Terminal-Instanz fahren.

**Warum (zwei reale Incidents, nicht hypothetisch)**:
1. ORB-Forward-Test hat sich wochenlang mit dem falschen Konto verbunden
   (`connected to account 15514`/`5053949028, expected 110209087`,
   `orb_forward_test_logs/task_run.log`) -- `MetaTrader5`-Python's
   `initialize()` hängt sich an irgendein gerade offenes Terminal, wenn kein
   fester Terminal-Pfad hinterlegt ist, nicht zwingend an das richtige.
2. Gold-ASB-Order wurde am 2026-08-20 zweimal abgelehnt (`retcode=10027,
   comment='AutoTrading disabled by client'`, `gold_asb_logs/task_run.log`)
   -- AutoTrading ist ein Terminal-weiter Schalter; bei geteilten Terminals
   wirkt sich ein deaktivierter Schalter unbemerkt auf alle Bots aus, die
   darüber laufen.

**Standardablauf pro neuem Bot (vor dem ersten produktiven Task-Lauf)**:
1. Neues MT5-Terminal-Verzeichnis unter `C:\Users\andre\MT5-Terminals\`
   anlegen, mit dem Zielkonto einloggen, Pfad fest in der Bridge-Config
   hinterlegen -- nie auf "irgendein laufendes Terminal" verlassen.
2. Im neuen Terminal: AutoTrading-Button aktivieren (grün) UND Extras ->
   Optionen -> Experts -> "Automatisierten Handel zulassen" anhaken,
   verifizieren bevor der Task live geht.
3. Bridge/Executor: Kontonummer nach Connect gegen die erwartete
   Kontonummer prüfen und bei Abweichung hart sichtbar machen/failen
   (Pattern wie ORB's "connected to account X, expected Y" -- als Standard
   in jede neue Bridge übernehmen, nicht nur ins Log schreiben und
   ignorieren).
4. Ersten produktiven Order-Send im Log auf `retcode`/Erfolg prüfen, bevor
   der Scheduled Task dauerhaft aktiv bleibt.
5. Scheduled-Task-Trigger-Frequenz muss zur Bar-Größe der Strategie passen
   (z.B. Daily-Bar-Strategie = 1x/Tag, keine Wiederholung alle 30 Min
   innerhalb des Tages). Mehrfache Same-Day-Läufe können zustandsbehaftete
   Positions-Logik verfälschen -- gefunden 2026-08-20 im BTC-EMA-Cross-Bot
   (`btc_ema_cross/live_scan.py`): ein Same-Day-Rerun verglich den frisch
   berechneten Stop gegen den Low des VORTAGS (der schon vor dem Entry
   feststand) und löste dadurch zweimal einen fiktiven Stop-Hit aus, ohne
   dass sich der Kurs bewegt hätte. Fix: Exit-/Entry-Logik pro Kalendertag
   nur einmal auswerten (`state["last_scan_date"]`-Guard).

**Grundregel Ende**: kein Bot geht live (auch nicht papierbasiert mit
echter MT5-Order-Kette), bevor Schritt 1-5 einmal durchlaufen und im Log
verifiziert wurden.
