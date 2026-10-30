# Quantum Valkyrie EA: Nachbau + Edge Card

Status: Schritt A3 läuft (Regeln herleiten). Stand 2026-10-28.
Plan: `C:\Users\andre\.claude\plans\bubbly-coalescing-pumpkin.md`. Code: `mt5_valkyrie/`.
Vorgeschichte und Schnelltest: [[quantum-omnigold-nachbau]] (Abschnitt Valkyrie).

Valkyrie ist der stärkste der drei gekauften Gold-EAs:
- jedes Jahr 2020–2026 positiv, Profitfaktor 1,31–2,01
- unabhängig vom Tick-Modell
- Datumssperre vor dem 17.01.2020

Der Nachbau soll klären, worauf Einstieg, SL und TP beruhen. Er soll außerdem 2018–2019 testen, also genau die Jahre, die der EA verbirgt.

## Daten
- **`mt5_valkyrie/data_mt5.py`** liest die drei Berichte:
  - `Bots\Report.html` (OHLC 2020–23)
  - `Quantum Valkyrie\…_1.html` (Ticks 2020–23)
  - `…_2.html` (OHLC 2023–26)
  - Ergebnis: 3.084 Orders und 2.424 Positionen, Zuordnung Ein-/Ausstieg über den Gewinn **fehlerfrei** (0,000 $). Die Endstände stimmen auf den Cent.
- **Kursdaten:** exakte MT5-Ticks ab 27.05.2025. Volle M1-Historie von MetaQuotes-Demo über das portable Tester-Terminal ([[mt5-tester-portable]]).

## Stand 2026-10-28 abends: exakte Tester-Daten
- **M1 von MetaQuotes-Demo 2018–2026** über das portable Terminal exportiert (`mt5_valkyrie/data.py`, `results/xau_m1_mq.parquet`). 2026 zu 100 % identisch mit den Kerzen aus Original-Ticks.
- **Tick-Modell nachgebaut** (`mt5_valkyrie/ohlc_ticks.py`): 4 Ticks je M1 bei Sekunde 0/20/40/59, Open → Low/High bzw. High/Low → Close. **Alle 1.528 OHLC-Einstiege liegen exakt auf einem dieser Ticks.**
- **Level, Restfälle gelöst:** Die 15 % ohne Swing-Treffer liegen alle **genau 0,30 $ über dem Ask bzw. unter dem Bid**. Regel: Level = max(Swing-Hoch, Ask + 0,30).
- **Swing-Definition:** jüngstes bestätigtes Pivot mit 12 Kerzen links (≤) und 6 rechts (<) auf M15. Trifft **80 %** der Levels auf den Cent (Donchian 59 %, Fraktal 2/2 bis 8/6 weniger, MT5-ZigZag 12/5/3 nur 50 %).
- **Trailing-Stopp gelöst:** Ab einem Gewinn von **0,22 × SL-Abstand** zieht der SL bei jedem Tick auf Höchststand − 0,50 $ nach, sobald das mehr als 0,10 $ Verbesserung bringt. Trifft **90 % der Ausstiegszeiten (±1 Min.) und 86 % der Ausstiegskurse exakt**. Die Spitze bei 0,22 ist scharf: 0,21 bzw. 0,23 ergeben nur 78–79 %.
- **Filter:** Max-Spread 0,30 $ (`InpMaxSpread=30`) bestätigt. Trend: Orders liegen deutlich auf der Trendseite langer Durchschnitte (EMA200 M15 im Median +3,5 ATR gegenüber +0,6 ATR bei Nicht-Orders). Den genauen Filter gibt es noch nicht.
- **Auslöser-Zeitpunkt weiter offen:**
  - Die Momentum-Regel (Körper > 0, 4-Kerzen-Bewegung > 1 ATR, eine Order je Pivot) erfasst 36 % der Orders zeitlich, feuert aber 5× zu oft.
  - Geprüft und verworfen: Gegen-Pivot-Bestätigung, Kopplung an eigene EA-Ereignisse (nur 2,5 % < 15 Min.), Tageslimit.

## Hergeleitete Regeln (Kalibrierung nur auf Übereinstimmung, nie auf Gewinn)
| Element | Regel | Treffer |
|---|---|---|
| Zeitpunkt | Buy-/Sell-Stop immer zur Eröffnung einer M15-Kerze (Sekunde 0) | 100 % |
| Richtung | **Momentum-Fortsetzung:** Die zuletzt geschlossene M15-Kerze läuft in Order-Richtung (Körper > 0), die letzten ~4 Kerzen ebenso | 149:1 bzw. 131:3 bei > 1 ATR |
| Level | ein noch ungebrochenes M15-Hoch (Buy) bzw. -Tief (Sell) von vor 2–8 h (9–33 Kerzen) | 88 % auf den Cent auf einem M15-Extrem der letzten 100 h; Donchian(32) 63 %, Fraktal 72 % |
| Vor der Order | Rücksetzer ≥ ~2,4 ATR vom Level, danach Erholung ≥ ~1 ATR | 5 %-Quantile |
| SL | **≈ 3,5 × ATR(M15, 100–120), begrenzt auf 15–60 $.** 2020–24 meist an der Untergrenze 15 $ (ruhiges Gold) | Streuung 4 % |
| TP | 50 $ fest; selten 8/12/22 $ (offen) | 91 % |
| Ablauf | Nicht ausgelöste Orders verfallen nach ~29,75 h | |
| Ausstieg | 99 % über den nachgezogenen SL (Regel offen) | |
| Lot | 0,01 je 1.000 $ (Risikostufe 3); nach einem Verlust ×2, nur eine Stufe (6 % des Gewinns) | |
| Mehrfach | Mehrere offene Orders/Positionen je Seite erlaubt | |

## Offen
- **Auslöser-Zeitpunkt:** Die beste Ereignisregel (Rücksetzer ≥ 2 ATR, Erholung ≥ 2 ATR, eine Order je Level, Donchian 40) trifft 93 von 422 Orders exakt nach Zeit und Level (22 %). Sie feuert aber rund 8× zu oft, ein Filter fehlt.
- Trailing-SL-Regel, TP-Sonderwerte, NFP-/Feiertagsfilter.
- Danach: Engine, `match_report` (Ziel ≥ 80 %), Edge Card, Prüfung unter der Overfitting-Sperre mit Blindtest 2018–2019.
