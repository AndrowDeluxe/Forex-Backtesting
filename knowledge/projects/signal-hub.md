# Project: Signal-Hub – Hybrid-Bestätigungssystem

**Status (19.11.2026):** Stufe 1 live (nur Paper/Journal, keine Orders). Plan freigegeben 19.11. Teil des
[[quant-diskretionaer-fusion]] (neue Hauptrichtung). Code `signal_hub/`, Tasks „Signal-Hub-Scan“ (alle 10 Min., Mo–Fr)
und „Signal-Hub-Listener“ (alle 2 Min., Mo–Sa).

## Warum

- 2026 kippte das Hand-Trading durch Overtrading, zu viel Risiko, emotionale Trades und Trades außerhalb des Systems
  (Nutzer 19.11.).
- Die Edge-Tests haben gezeigt: Die Regeln finden die Nutzer-Trades exakt, aber die **Auswahl** lässt sich nicht mechanisch
  nachbauen ([[h4-htf-entry-edge-card]], [[htf-daily-trade-edge-card]]).
- Lösung: Die Maschine findet und bewertet Setups, der Nutzer bestätigt nur mit Ja/Nein, die Maschine führt aus.
  Jede Entscheidung wird Datenpunkt (Forward-Nachweis, später Selbstlernen Strang 7).
- Ziel: nachhaltiges System ohne Emotion/Overtrading. Nach dem Forward ein 100k Instant Funding
  (~1 %/Monat ≈ 750 $ netto).

## Nutzerentscheide (19.11.)

- **Kanal:** zuerst Telegram (Alarm + Entscheidung); App parallel, später vergleichen.
- **Nach „Ja“:** Paper-Simulation **und** MT5-Demo-Order parallel (Demo in Stufe 2).
- **Risiko je Kontotyp, Ausführung identisch:**
  - Funded: FK-/IQ-Regeln (0,5 % je Position, 5 % Trailing-DD)
  - EK: 1 %, max. 3 Trades/Tag, −5 %/Woche
  - später A+-Stufe 2–3 % bei vielen Confis
- **Setups:**
  - Start: H4-Spike, Qualitätssignale ca. 3/Woche, ⭐ = beste Test-4-Variante
  - danach: Daily C2/W50 und Typ R nach Handprüfung „auf meine Sichtweise“
  - Indikatoren später, auch als Live-Dashboard
  - Inventur-Edges nach und nach

## Roadmap

| Stufe | Inhalt | Stand |
|---|---|---|
| 1 | H4-Scanner, Telegram-Alarm (Chart, Merkmale, Makro-Ampel, Ja/Nein/Später + Nein-Grund), Journal, Paper-Simulation, Risiko-Sperre | **live seit 19.11.** |
| 2 | MT5-Demo-Ausführung (Bridge-Muster, eigenes Terminal), Risiko je Kontotyp | braucht Demokonto (Login/Server) |
| 3 | Makro-Agent täglich automatisch, Markt-Ampel aus dem Fact Sheet | offen |
| 4 | Daily-Setups (C2/W50, Typ R) nach Handprüfung in den Scanner | offen |
| 5 | Indikator-Bibliothek + Signale/Indikatoren als Live-Dashboard in der App, Bestätigung auch dort | offen (Daten liegen in `signal_hub/out/signals.json`) |
| 6 | Inventur-Edges je Edge mit 2 Fragen (findet die Regel deine Trades? brutto > 0?) → Hub | offen |
| 7 | Forward-Auswertung (~50 Entscheidungen oder 3 Monate) → Livegang 100k Instant Funding | offen |
| 8 | Bot-Status zusätzlich in die App | offen |
| später | Händische LTF-Trades im selben Stil | — |

## Stufe 1: wie es funktioniert

1. **Scan** (`python -m signal_hub scan`):
   - Für jeden Markt die jüngste vollständig mit Daten abgedeckte H4-Kerze (Serverzeit NY+7).
   - Merkmale mit **demselben Code wie der Backtest** (`h4_v4.features_at`; Abgleich EURUSD: 5.993 Signale, Abweichung 0).
   - Alarm nur bei Qualität + Aktivität/Kalender (`h4_v4.masks` Q & A); Rückwärtsprobe November: 9 Alarme in
     2,5 Wochen.
   - Alle Grundsignale landen zusätzlich in `journal/grundsignale.csv`.
   - Veraltete Daten (> 8 h) werden übersprungen.
2. **Alarm:**
   - Chartbild (60 H4-Kerzen, Signalkerze, Einstieg/Stop/3R/Swing/Marke, Vormonats-Range).
   - Legende: Merkmale, Makro-Ampel (FX: 0–2 / 3–4 / ≥ 5 von 7 Filtern gegen; Gold: Makro-Veto; Silber: Realzins),
     Lot-Vorschlag je Kontotyp.
   - Gültig bis zum nächsten H4-Schluss.
   - Bei Risiko-Sperre 🔒 ohne Ja-Knopf.
3. **Listener** (`python -m signal_hub listen`):
   - Telegram-`getUpdates`: Ja / Nein → Grund (Trend, Lage, Kerze, Makro, Momentum, Sonstiges) / Später (1 h).
   - Verfall; Erinnerungen.
4. **Paper:**
   - Jedes Signal zum Signalkurs („was wäre gewesen“), bestätigte zusätzlich zum Kurs bei Bestätigung.
   - Stop am Docht, 3R, BE nach 1R, max. 10 Tage, Kosten + Swap.
   - Telegram bei Schluss.
5. **Journal** `signal_hub/journal/signals.csv` (committet, höchstens stündlich), App-Daten `signal_hub/out/signals.json`.

## Bekannte Punkte

- **Die Q-Regel (Docht ≥ 40 %, ein geholtes „unberührtes“ H4-Swing) hätte die echten Nutzer-Trades EURUSD 10./12.11.
  nicht alarmiert** (12.11.: Docht 30 %, kein Swing nach k=2-Definition). Nach ~1 Woche Signalmenge und Treffer
  der Auswahl prüfen, ggf. Schwelle lockern.
- Lake-Key NZDUSD M15 neu (19.11.) für den Scanner.
- Test-Alarm 19.11. (`…_TEST`) im Journal, nicht in die Auswertung zählen.
