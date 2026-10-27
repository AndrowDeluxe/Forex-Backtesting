# SMH CLS-Praxis-Call: Abgleich mit unserer Engine

Quelle: Aufzeichnung des Smartmoneyhour-Calls "CLS Practical" (lokal,
`OneDrive\...\Institutial Mandate\Calls\CLS Practical Call.mp4`, ~34 Min.),
am 2026-10-21 mit Whisper transkribiert. Das Transkript liegt daneben
(`CLS Practical Call - Transkript.txt`) und nicht im Repo, weil es bezahlter
Kursinhalt ist. Die Folien stammen aus
demselben `CLS_Praxis_Playbook.pdf`, aus dem `cls_practical/engine.py` im
August gebaut wurde. Neu ist vor allem das, was im Call gesagt und an
Live-Beispielen gezeigt wurde (AUDUSD 04.08., USDCAD 13.08., USDCHF).
Verwandt: [[cls-practical-kostenvalidierung]], [[overfitting-sperre]],
[[makro-faktoren-katalog]], [[smh-session-pips-call]] (Folge-Call).

## Einordnung
- **Status der Quelle:** Der Mentor nennt es ausdrücklich ein
  *Kontext-Framework* und kein Einstiegssystem ("kannst du mit allem
  umsetzen"). Alle Beispiele sind von Hand ausgesuchte "beste Setups" (n=1),
  es gibt keine Statistik. Damit ist das eine Ideenquelle und kein Beleg.
- **Ablauf laut Call:**
  - 06–07 Uhr: Nachfrage ("Depot wird aufgefüllt")
  - 07–08 Uhr: Funding
  - 08–09 Uhr: Pre-London-Manipulation
  - 08:45–09:30 Uhr: "kritische Zeitbox" zur Bestätigung
  - Ein Move bis 08:45 gegen HTF, Crosses und Rates gilt als Fake durch
    Funding-Druck, danach wird in Trendrichtung gehandelt.

  Das deckt sich mit unserem Reversal-Setup (Trend gegen den Break).

## Unterschiede zur Engine, sortiert nach Testwert

| # | Call | Engine heute | Schon getestet? |
|---|---|---|---|
| 1 | **Limit-Entry am 06:00-Preis** oder bei 50 % Retracement der Akkumulation, nach der 09:00-Bestätigung; Re-Entry über den Tag erlaubt | Stop-Order über dem Pullback-Fraktal ab 09:30 | Nein. Verworfen sind nur die Stop-Varianten (`breakout_stop` 08/2026, ruhende Stop-Order 04.10.). |
| 2 | **Zeitausstieg 12:00** ("Endfenster", Beispieltrade "um 12 Uhr geschlossen") | kein Zeitausstieg, nur SL/TP | Nein |
| 3 | **TP an externer Liquidität oder Range-Gegenseite** | 0,35 × ADR(14) | Teilweise: Fixed-R und adr_mult verworfen, Liquiditätsziel nicht getestet |
| 4 | **Crosses der Nicht-USD-Währung**, 2–4 Paare (vs. JPY = Risk, vs. EUR = Dollar-Proxy, vs. Blockpartner wie NZD), Struktur Daily→H4→H1 gleichgerichtet | 06–09-Move von EUR/USD gegen 5 USD-Majors | Teilweise: Index-Filter (Basis- minus Quote-Index) und MTF-Trend-Vote auf dem USD-Korb verworfen. Trend-Vote auf den **EUR**-Crosses fehlt noch. |
| 5 | Rates = **Niveau** (Carry-Vorzeichen, HTF) **plus Änderung** des 2Y-Spreads (4h) | nur Änderung (z-Score), als Risikoskalierung | Niveau nicht getestet. Für EUR/USD war es seit Jahren fast konstant negativ, der Erkenntniswert ist daher gering. |
| 6 | Asia-Range **bis 07:00** ("dort fließt westliche Liquidität ein") | 00:00–06:00 | Für AUD/USD 04–08 getestet und verworfen (08/2026). Für EUR/USD bis 07:00 nicht getestet. |
| 7 | Andere Paare (AUDUSD, USDCAD, USDCHF) mit eigenen Zeiten und Crosses | nur EUR/USD | Andere Majors verworfen, aber mit EUR-Zeiten und USD-Korb |

**Nicht testbar ohne Erfindung:** SMC-Kontext (Order Block, Inducement,
Imbalance), "chaotisch" als dritter 09:00-Zustand, Qualität 1–5,
Fib-Ziele 1,272–1,618, Stärke-Ranking über die DXY-Komponenten (gibt es
schon als Kontext-Baustein aus [[quant-diskretionaer-fusion]], dort ohne
eigenes Signal).

## Warum #1 am meisten verspricht
Der größte bekannte Leck-Punkt von CLS ist der Entry-Versatz: Live liegen
etwa 10 Minuten zwischen Signal und Order, und das kostet rund 0,2 R je
Trade, mehr als alle Brokerkosten zusammen (Befunde 5–7 in
[[cls-practical-kostenvalidierung]]). Eine ruhende **Limit**-Order hat
diesen Versatz nicht, weil sie beim Broker liegt. Der Stop sitzt außerdem
an einer festen Struktur (06:00-Preis/Low), statt bei der Größenberechnung
am Live-Preis zu hängen. Gegenrisiko: Ein Limit wird bevorzugt dann
gefüllt, wenn der Markt gegen die Idee läuft (adverse Selektion). Das muss
der Test zeigen.

## Regeln für einen Test
CLS ist live und der Tresor ist geöffnet ([[live-strategien-tresor-check]]).
Nach [[overfitting-sperre]] Punkt 6 werden Änderungen deshalb nur auf IS
gerechnet und als Versuche gezählt. Ein Gewinner geht danach in einen
Forward-/Schattenlauf und wird nicht erneut auf dem alten OOS geprüft.
Vom Nutzer am 2026-10-21 freigegeben: #1–#3 als drei Varianten, OOS bis
heute.

## Ergebnis (2026-10-21): alle drei verworfen, Live-Konfiguration bleibt
`scripts/research_cls_practical_smh_call_variants.py`, Lock
`cls_practical_smh_call`. Gerechnet auf der Live-Konfiguration mit
TTP-Kosten (2,05 Pips), 1 Bar Versatz und Gates ≤ 0,5 R. Bewertet je Trade
in R.

| Variante | IS n | IS Ø R | IS P(Ø R<0) | OOS n | OOS Ø R | OOS PF |
|---|---|---|---|---|---|---|
| Basis (live) | 56 | +0,168 | 22 % | 85 | **+0,311** | 1,64 |
| V1 Limit am 06:00-Kurs | 12 | +0,844 | 3,8 % | 51 | +0,146 | 1,21 |
| V2 Zeitausstieg 12:00 | 56 | +0,051 | 37 % | 85 | +0,141 | 1,44 |
| V3 TP Liquidität/Range-Gegenseite | 56 | +0,121 | 28 % | 85 | +0,340 | 1,80 |

- **V1** hat die vorab festgelegte Regel erfüllt (DSR 0,79). Die
  IS-Stärke beruhte aber auf nur 12 Trades und ist im OOS zerfallen
  (2022 und 2026 negativ). Der Limit-Kurs liegt außerdem bei 63 von 154
  Setups schon auf der falschen Seite, damit fallen viele Trades weg.
- **V2:** Der Zeitausstieg kappt die Gewinner, die bis zum ADR-Ziel laufen,
  in IS wie OOS. Das passt zum früheren Befund, dass Breakeven-Trailing
  schadet ([[cls-practical-kostenvalidierung]] Befund 6).
- **V3** liegt im OOS knapp vorn, verliert aber im IS. Würde man es nach dem
  OOS übernehmen, wäre das genau die Auswahl auf OOS, die die Sperre
  verbietet. Gleichstand im Rahmen des Rauschens.
- **Einschränkung:** Das OOS ab 06/2022 wurde in früheren CLS-Studien schon
  oft angesehen und ist nicht mehr unberührt. Unverbraucht ist nur der
  Zeitraum seit dem Livegang (07.09.2026), und dort liegt erst 1 Trade.
- **Nebenbefund:** Die Engine prüft Ausstiege ab der Signalbar, also vor dem
  Live-Einstieg. Neu gerechnet ab der Bar nach dem Einstieg ändert sich
  kaum etwas (IS +0,166 → +0,168, OOS +0,312 → +0,311). Die bisherigen
  CLS-Zahlen sind davon also nicht verzerrt.
