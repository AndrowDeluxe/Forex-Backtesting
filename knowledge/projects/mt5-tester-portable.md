# Portables MT5-Tester-Terminal + Skill `mt5-robot-tester`

Angelegt am 2026-10-28 für automatisierte Strategietester-Läufe gekaufter EAs, ohne die Live- oder Demo-Terminals anzufassen.

- **Programm:** `C:\Users\andre\MT5-Terminals\Tester-Portable\` (Kopie von `C:\Program Files\TTP MT5 Terminal`).
  - Läuft ohne `/portable`. Der Datenordner ist deshalb `AppData\Roaming\MetaQuotes\Terminal\D14881EC69F0F0B10655DE06FF95177D\`.
  - Den Datenordner nutzt nur dieses Terminal, keine Bridge.
- **Konto:** MetaQuotes-Demo 5057577303, gespeichert. `MaxBars` steht auf unbegrenzt (`common.ini`).
- **Kursdaten:** M1-Historie (24 Symbole) und XAUUSD-Ticks aus dem TTP-Terminal übernommen.
- **EA-Ordner:** `MQL5\Experts\candidates | in-testing | finalists` (verlangt der Skill).
- **Skill-Konfiguration:** außerhalb von Git, im Scratchpad der Session vom 28.10. (`ubs_config.json`). Ausgabe nach `mt5_ultimate_breakout/skill_run/`.

## Eigenheiten
- Der Tester schreibt seine Berichte **auf Deutsch**. `Language=English` in `common.ini` wirkt nicht.
- Der Skill kannte nur englische und spanische Bezeichnungen. Deshalb wurden am 28.10. in `~/.claude/skills/mt5-robot-tester/scripts/` deutsche Aliase ergänzt:
  - `parse_mt5_report.py`: Nettogewinn gesamt, Ersteinlage, Profitfaktor, LR Korrelation, Sharpe-Ratio, Gesamtanzahl Trades, Rückgang …, Kontostand/Zeit
  - `mt5_common.py`: Durchlauf, Ergebnis, Gewinn, Profitfaktor, Erwartetes Ergebnis, Erholungsfaktor
- Dabei auch einen Fehler des Skills behoben: Zahlen ab 1000 ohne Tausender-Leerzeichen (z. B. 11009) wurden abgeschnitten (110).
- Die Skill-Dateien liegen nicht in Git.
- MT5 leert die Tester-Logs automatisch (am 24.10. beobachtet). Wichtige Läufe sofort auswerten oder sichern.

## Ergebnis Ultimate Breakout System (28.10.)
- Runde 1: 10 Symbole, M15, 1-Min-OHLC, 2018-01-01 bis 2026-10-16, Standard-Eingaben, fest 0,01 Lot.
- **Abgelehnt.** Nur XAUUSD positiv: +1.511 $ auf 100.000, Profitfaktor 1,04, 11.009 Trades; 2018–2020 negativ, 2025–26 positiv. Alle 9 Devisenpaare leicht negativ.
- Der EA ist für Anbieter-Set-Dateien gebaut („AutoLoad Set Files“). Der Nutzer hat keine. Runde 3 entfiel damit (keine .set).
- Keine Datumssperre.

Siehe [[quantum-valkyrie-nachbau]], [[quantum-omnigold-nachbau]].
