# Quantum OmniGold EA: Nachbau (Klon + Edge-Prüfung)

Status: Schritt 3 von 6 läuft (Regeln herleiten). Stand 2026-10-20.
Plan: `C:\Users\andre\.claude\plans\floating-finding-bear.md`. Code: `mt5_quantum_omnigold/`.

Der kommerzielle MT5-EA „Quantum OmniGold“ (.ex5, nicht lesbar) wird aus seinem Verhalten im Strategietester nachgebaut. Ziel ist zuerst ein Klon, der ≥ 80 % der MT5-Einstiege trifft (±5 Min.). Erst danach folgt die Edge-Prüfung ab 2018 unter der [[overfitting-sperre]]. Danach kommen Quantum Valkyrie und Ultimate Breakout System an die Reihe.

## Quellen
- Berichte in `OneDrive\…\Institutial Mandate\Bots\Quantum Omni Gold\`:
  - `ReportTester-5057577303.html`: 424 Trades, 01/2022–07/2023, Endstand 210.867,21
  - `ReportTester-5057577303_1.html`: 1.000 Trades, 07/2023–10/2026, Start 100k, Endstand 1.415.740,88
- Tester-Log `…\Agent-127.0.0.1-3000\logs\20261019.log`: zwei Läufe 2025-01 bis 2026-10, 595 Einstiege mit EA-Ausgaben.
- **Berichte nie in den Chat ziehen.** Die 2-MB-HTML-Datei hat am 20.10. eine Session gesprengt („Prompt is too long“, auch nach der Komprimierung). Immer nur den Pfad nennen.

## Eingaben (beide Läufe gleich)
`InpSlUSD=30`, `InpTpUSD=40`, `InpTpHighATR=60`, `MaxRangeToRecalculate=40`, Auto-Lot (Risikostufe 3, 0,01 Lot je 1.000 $), Lot-Verdopplung an, NFP-Tage gesperrt, alle Wochentage erlaubt.

## Bestätigte Regeln (`reverse.py`)
| Regel | Befund | Treffer |
|---|---|---|
| Brokerzeit | Europe/Athens (EET, **EU**-Sommerzeit), nicht „NY + 7 h“ | 99,2 % der Einstiege in der M1-Kerze |
| ATR | iATR(M15, 30), einfacher Durchschnitt; Dukascopy liefert ~4 % mehr | Wert × 30 = ganze Cent in 100 % der Fälle |
| res/support | wird neu berechnet, wenn die geschlossene M15-Kerze ein neues Hoch/Tief macht; Wert = dieses Extrem (+0,2 $ Datenversatz) | 98,5 % |
| Einstieg | Ausbruch über Hoch/Tief der letzten ~72 M15-Kerzen (~18 h, Kerzen gezählt, Feiertage übersprungen) | 73,5 % (86 % bei Kanalbreite ≤ 40 $) |
| SL/TP | Abstand X zum Fenster-Extrem der Gegenseite: TP = Einstieg ± X (max. 40 $), SL = X + ~0,9 $ Puffer (max. 30 $; bei hoher ATR auch > 30 $) | Struktur klar, Fenster für X erst ~50 % |

## Ausstieg (Stand 2026-10-21, noch nicht als Regel bestätigt)
- 448 EA-Ausstiege, alle im Gewinn (≥ +2,0 $).
- **Intrabar-Ausstieg „Close by trailing profit“**: 40 Fälle, alle 2–20 Min. nach dem Einstieg, bei genau +2,9 bis +3,00 $.
- **Ausstiege zur vollen Minute** (403): Entschieden wird auf dem Schluss der vorherigen M1-Kerze, ausgeführt zur Eröffnung der nächsten.
  - Der Gewinn ist zweigipflig: eine Häufung bei 2–4 $, eine bei 8–11 $.
  - Der Rücksetzer vom Höchststand wächst mit dessen Höhe, etwa 20 % des Höchstgewinns.
  - Beim Ausstieg steht der Kurs fast immer über allen Durchschnitten, ein Umkehrsignal gibt es nicht.
  - Feste, ATR-basierte und prozentuale Trailing-Regeln treffen jeweils nur ~25 % der Ausstiegsminuten. Sie würden oft zu früh aussteigen.
- **Grenze der Daten:** Die entscheidenden Rücksetzer sind 0,3–1 $ groß. Genau so groß ist auch die Abweichung zwischen Dukascopy und MT5. Für eine minutengenaue Ausstiegsregel braucht es die Original-Ticks von MetaQuotes-Demo.
  - Sie liegen lokal in den TTP-Terminals (`844E…`: 2019–2026). Die gehören aber zur Funded-Bridge (live) und sind tabu.
  - Das freie Terminal `C:\Program Files\MetaTrader 5` scheitert an der Anmeldung („Authorization failed“, Demo-Konto abgelaufen).
- **SL-Trailing:** Der SL wird pro Tick um 0,02 $ nachgezogen, mit großem Abstand (~35 $). Das ist für das Ergebnis zweitrangig.

## Original-Ticks (seit 2026-10-21)
- Quelle: das freie Terminal `C:\Program Files\TTP MT5 Terminal`, Demo-Konto 5057577303. Keine Bridge nutzt es. Export mit `ticks_mt5.py` nach `results/ticks/`.
- Die Ticks stimmen zu 100 % mit den Bid/Ask-Preisen im Tester-Log überein.
- Abgedeckt sind 27.05.2025 bis 10/2026 und 2019–2020. **2021 bis 04/2025 hat MetaQuotes-Demo keine Ticks.** Daher kommt die „Qualität der Historie 79 %“. Der Tester hat 2022–2025 mit Ersatzdaten gerechnet.
- Das Terminal gibt per API nur 100.000 M1-Kerzen heraus (`maxbars`). Bei Bedarf lässt sich das in den Terminal-Einstellungen erhöhen.

## Ausstieg mit exakten Daten (299 Ausstiege zur vollen Minute)
- Bisher erklärt keine Regel mehr als ~11 % der Ausstiegsminuten. Getestet wurden:
  - Trailing in $, in % und in ATR
  - Mindestgewinn plus Kerzenmuster
  - Kreuzen von Levels: runde Zahlen, Hochs/Tiefs auf M15–D1, eigene Linie
  - Überdehnung: RSI, Bollinger, EMA-Abstand, Stochastik
  - ein Entscheidungsbaum über alle Merkmale
- Gemeinsames Muster: Die Regeln würden zu ~80 % **zu früh** aussteigen. Der EA lässt viele gleichartige Momente aus, irgendein Sperrzustand fehlt noch.
- Gesichert ist: Der Ausstieg kommt erst ab einem Gewinn von ~0,4 × ATR, und zwar bei Stärke, nie bei Schwäche. 83 % der Ausstiege folgen erst, nachdem die eigene Linie seit dem Einstieg neu berechnet wurde.

## Tick-Modell-Vergleich (2026-10-21, Berichte _2/_3 = „1 Minute OHLC“, 99 % Qualität)
Gleicher EA, gleiche Parameter und Zeiträume, nur das Tick-Modell ist anders:

| Zeitraum | echte Ticks (79 %) | 1-Min-OHLC |
|---|---|---|
| 01/2022–07/2023 | +110.867 $, DD 6,0 % | +78.202 $, DD 7,0 % |
| 07/2023–10/2026 | +1.315.741 $, DD 63,2 % | +131.842 $, DD 54,1 % |

Ohne Lot-Einfluss gerechnet, in $ Kursbewegung je Unze und Trade:
- 2022–2025 bleibt der EA in beiden Modellen positiv. Mit OHLC ist er 20–57 % schwächer.
- 2026 liegt er mit OHLC bei **−212 $** (mit echten Ticks +492 $).
- Nur **50 % der Einstiege** fallen in beiden Läufen in dieselbe Minute.

Profil:
- Trefferquote 75–92 %
- Durchschnittlicher Gewinn 4–14 $, durchschnittlicher Verlust −14 bis −35 $
- Erwartungswert 1–3 $ je Trade

**Folgerung:** Der Edge hängt am feinen Tick-Pfad, also an den Mikro-Ausstiegen bei 2–3 $. Kleine Unterschiede bei Daten, Spread oder Ausführung kippen ihn. Die 1,3 Mio. sind überwiegend Zinseszins plus Lot-Verdopplung im Lauf 2025. Live-Slippage geht direkt vom Erwartungswert ab.

## Eingebaute Datumssperre vor 2022 (2026-10-21, Bericht _4)
- Die Testläufe 2017–2023 und 2018–05/2021 (Modell 1-Min-OHLC, M1-Historie ab 2011 vorhanden) zeigen bis zum 02.01.2022 **keine einzige EA-Ausgabe**: keine ATR, keine Linien, keine Trades.
- Ab dem 03.01.2022 02:45 läuft der EA sofort normal.
- Bericht _4 enthält nur 265 Trades von 01/2022 bis 01/2023. Das ist ein Teillauf ab 13.05.2021, also nichts Neues.
- **Der Anbieter verhindert also Backtests vor 2022.** Das ist ein starkes Warnsignal für Kurvenanpassung: Gerade die Jahre ohne Goldboom lassen sich nicht prüfen.
- Ein Robustheitstest 2018–2021 ginge nur noch über einen eigenen Klon. Dem fehlt aber die Ausstiegsregel.

## Quantum Valkyrie: Schnelltest (2026-10-21)
Laut eigenen Eingaben „Optimized XAUUSD (Gold) strategy for M15“. Bericht `…\Bots\Report.html`, Teil 2 aus dem Tester-Log.
- **Mechanik:**
  - Einstieg über Buy-/Sell-Stop-Orders mit SL 15 $ und TP 50 $
  - Ausstieg fast nur über den nachgezogenen SL (833 von 836)
  - Mehrere Positionen gleichzeitig möglich
  - Martingale: Nach einem Verlust kommt die nächste Order mit ×2, aber nur eine Stufe, nicht fortgesetzt. Die verdoppelten Trades bringen nur 6 % des Gewinns.
- **Handelt erst ab dem 17.01.2020**, obwohl M1-Daten ab 2016 vorliegen. Das ist wieder eine Datumssperre, diesmal 2020 statt 2022.
- 1-Min-OHLC, 2020 bis 10/2023: +131.734 $, Profitfaktor 1,35, Drawdown 18,9 %.
- Echte Ticks (Forward), 10/2023 bis 09/2026: Endstand 1.055.716 $.
- Lot-neutral, in $ je Unze und Trade:
  - OHLC: 0,44–1,78 $ (2022 am schwächsten)
  - Echte Ticks: 2,3–4,4 $
- Profil wie beim OmniGold: Trefferquote 81–87 %, durchschnittlicher Gewinn 4–11 $, durchschnittlicher Verlust −13 bis −37 $.
- **Tick-Vergleich 2020–10/2023** (`Quantum Valkyrie\ReportTester-5057577303_1.html`, echte Ticks, 88 % Qualität): +93.788 $ gegenüber +131.734 $ mit OHLC, Profitfaktor 1,31 gegenüber 1,35.
  - Aussagekräftig ist nur 2020. Für 2021–2023 hat MetaQuotes-Demo keine Ticks, beide Läufe sind dort gleich.
  - 2020: 0,70 $ je Trade gegenüber 0,88 $ (−20 %), 163 gegenüber 217 Trades.
  - **Viel robuster als der OmniGold** (der verlor −90 %).
- **OHLC 01/2023 bis 09/2026** (`Quantum Valkyrie\ReportTester-5057577303_2.html`): +1.547.557 $, Profitfaktor 2,01, Drawdown 24,4 %.
  - In 2024–2026 sind die Trades **praktisch identisch** mit dem Lauf auf echten Ticks: gleiche Anzahl, je Trade 2,31/3,31/4,37 $ gegenüber 2,33/3,32/4,37 $.
  - Das gilt auch für 05/2025–09/2026, wo echte Ticks vorliegen (326 Trades, 3,67 gegenüber 3,68 $).
  - **Valkyrie hängt also nicht am Tick-Modell.** Stop-Orders auf M15 reagieren kaum auf den Tick-Pfad.
  - Pro Trade: 2020 0,9 $, 2021 1,1 $, 2022 0,4 $, 2023 1,8 $, 2024 2,3 $, 2025 3,3 $, 2026 4,4 $. Der Ertrag wächst mit Goldpreis und Volatilität. 2022 ist die dünne Stelle.
- Gegenstück vorher (erledigt): OHLC 10/2023 bis 09/2026 zum zum Forward-Teil mit echten Ticks (gesichert in `results/valkyrie_log_trades.parquet`; die Tester-Logs hat MT5 am 24.10. geleert).

## Offen
- Fenster für X: Ein festes Fenster von 18 h trifft nur ~50 %. Vermutlich wird es neu berechnet, wenn die Kanalbreite > `MaxRangeToRecalculate` (40 $) ist.
- SL > 30 $ bei hoher ATR (Median 10,5): Die Regel fehlt noch, vermutlich `InpTpHighATR`.
- TP wird in derselben Sekunde wie der Einstieg geändert und danach mit nachgezogen (Modify mit TP < SL → „invalid stops“).
- Exit: „Close by trailing profit“ (40×). Die übrigen EA-Exits fallen auf die volle Minute. Die Regel fehlt noch.
- Lot-Regel: Verdopplung nach Gewinn, Rückstellung.
- Dann Schritt 4: Klon-Simulator + `match_report`.
