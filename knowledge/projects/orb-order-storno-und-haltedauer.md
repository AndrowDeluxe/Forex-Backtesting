# ORB: Order-Storno am geplanten SL + Haltedauer (2026-10-01)

Nutzerauftrag 2026-10-01: ORB überprüfen; backtesten, die noch nicht
gefüllte Stop-Order zu löschen, sobald der Kurs ihren geplanten SL erreicht;
danach die optimale Haltedauer neu bestimmen.

Skript: `scripts/research_orb_cancel_at_sl_and_hold.py` (`--tf m5|m1`).
Ergebnisse: `ny_open_orb/results/cancel_at_sl_{m5,m1}.csv`,
`hold_duration_{m5,m1}.csv`, `cancel_at_sl_trades_{m5,m1}.csv`.
2019-01 bis 2026-09, Live-Exit-Config (Variante C, siehe
[[orb-exit-logik-neubewertung]]), gemessene Broker-Spreads, 0,45 bps
Entry- und 0,30 bps Exit-Slippage. IS ≤ 2022, OOS ab 2023.

## Befund 1 — Live und Backtest handeln bei SP500/US30 nicht dieselben Tage

`_find_stop_breakout()` nimmt pro Tag den ERSTEN Ausbruch in beliebiger
Richtung. SP500/US30 filtern danach auf long. Bricht der Kurs zuerst nach
unten, hat der Backtest an diesem Tag **keinen** Trade. Live legen
Funded (`run_once.py::manage_orb_pending`) und EK
(`legs/ny_open_orb/executor.py`) bei SP500/US30 aber nur die Long-Order
(`ORDER_TIME_DAY` bis 16:00). Sie wird nach einem Bruch nach unten **nicht
storniert** und füllt, wenn der Kurs später doch über orb_high steigt.

Folge: live handelt rund 60 % mehr SP500/US30-Trades als der validierte
Backtest (SP500 594 statt 362, US30 605 statt 392). Diese Zusatztrades hat
nie jemand bewertet. Auf M1 gilt:

| Zusatztrades (live, nicht im Backtest) | n | Ø R | 95%-KI |
|---|---|---|---|
| SP500 | 232 | +0,132 | −0,19..+0,48 |
| US30 | 213 | −0,083 | −0,33..+0,17 |

Die Zusatztrades schaden nicht nachweisbar, aber **der MaxDD verdoppelt
sich** (SP500 −21,9 → −44,4 R, US30 −21,3 → −45,1 R). NASDAQ ist nicht
betroffen: dort ist OCO identisch mit der Backtest-Semantik.

## Befund 2 — die M5-Ausführung überzeichnet den ORB-Edge deutlich

Der SL liegt nur 8–10 bps vom Level entfernt (0,6 × M15-ATR; Median SP500
≈ 4 Pkt., US30 ≈ 29, NASDAQ ≈ 15). Er liegt an **100 %** der Tage
innerhalb der Opening Range. Auf M5 berührt bei ~70 % aller Trades schon
die **Füll-Bar** den SL. `simulate()` prüft den Stop aber erst ab der
Folgebar. Ob der Kurs in dieser Bar erst den SL und dann das Level
erreicht hat (Trade ok) oder umgekehrt (sofortiger −1R), ist auf M5 nicht
entscheidbar. Der Backtest nimmt stillschweigend immer den günstigen Fall
an.

Auf M1 sinkt die Mehrdeutigkeit auf ~22 % (SP500/US30) bzw. 33 % (NASDAQ),
und der Edge schrumpft entsprechend (Variante „opposite“ = validierter
Backtest, hold bis 16:00):

| | M5 Ø R (OOS) | M1 Ø R (OOS) |
|---|---|---|
| SP500 | +0,653 (+0,463) | +0,494 (+0,290) |
| US30 | +0,400 (+0,216) | +0,244 (**+0,005**) |
| NASDAQ | +0,253 (+0,194) | +0,137 (+0,052) |

Selbst M1 ist noch nicht die Wahrheit: wertet man jeden SL-Touch in der
Füll-Minute als Stop-out (pessimistische Grenze), wird US30 und NASDAQ
negativ, SP500 bleibt knapp positiv (+0,24 R). Die Wahrheit liegt
dazwischen. Das deckt sich mit Stage 4c (M15 > M5 > M1 im Sharpe), wo der
Effekt damals nur für M15 als Artefakt eingestuft wurde. Mit dem später
eingeführten engen 0,6-ATR-Stop betrifft er auch M5.

## Befund 3 — Storno am geplanten SL (Nutzervorschlag)

Weil der SL immer innerhalb der Range liegt, ist die SL-Regel stets
strenger als „Storno an der Gegenseite“. Sie lässt nur Ausbrüche zu, vor
denen der Kurs nie 0,6 ATR unter das Level zurückgefallen ist, also im
Wesentlichen frühe Ausbrüche. M1, hold bis 16:00:

| | Storno | n | Ø R | OOS | Σ R | MaxDD | pessimist. Ø R |
|---|---|---|---|---|---|---|---|
| SP500 | keins (live) | 594 | +0,352 | +0,210 | +209 | −44,4 | +0,131 |
| | Gegenseite (BT) | 362 | +0,494 | +0,290 | +179 | −21,9 | +0,243 |
| | **am SL** | 160 | +0,588 | +0,211 | +94 | −18,5 | +0,448 |
| US30 | keins (live) | 605 | +0,129 | −0,048 | +78 | −45,1 | −0,091 |
| | Gegenseite (BT) | 392 | +0,244 | +0,005 | +96 | −21,3 | −0,022 |
| | **am SL** | 137 | +0,444 | **−0,174** | +61 | −15,4 | +0,188 |
| NASDAQ | keins (live = BT) | 1595 | +0,137 | +0,052 | +218 | −49,0 | −0,210 |
| | **am SL** | 568 | +0,217 | +0,155 | +123 | −33,0 | +0,007 |

Die entfernten Trades sind im Mittel **nicht negativ** (SP500 +0,27,
KI +0,02..+0,51; US30 +0,04; NASDAQ +0,09, KI −0,06..+0,24). Die Regel
verbessert die Qualität pro Trade, kostet aber bei festem Risiko je Trade
die Hälfte der Gesamt-R.

**Wo sie trotzdem trägt: NASDAQ.** OOS fast verdreifacht (+0,052 →
+0,155), 8/8 Jahre positiv, MaxDD −49 → −33 R. Vor allem ist sie
**robust gegen die Füll-Bar-Mehrdeutigkeit** (pessimistisch +0,007 statt
−0,210), weil sie genau die Tage aussortiert, an denen der Kurs um das SL-
Niveau pendelt. Die t-Statistik (Ø R × √n) ist etwa gleich (~5,2 vs.
~5,5). Ob sich die Regel lohnt, hängt also daran, ob man das Risiko je
Trade erhöhen würde, wenn es weniger, aber sauberere Trades gibt.
**SP500:** OOS gleich, Σ R halbiert, pessimistisch klar besser — dünn
(160 Trades). **US30:** OOS negativ — verwerfen.

## Befund 4 — Haltedauer

Zeitstopp ab Füllung (30 Min. bis 16:00), M1:

- **SP500:** flach ab ~120 Min.; 240–300 Min. ≈ 16:00 (+0,50 vs. +0,49
  bei Variante „Gegenseite“). Kein Grund zur Änderung.
- **US30:** 30 Min. hat das beste OOS (+0,088 vs. +0,005), aber Gesamt
  schlechter und die Kurve springt (60/90 Min. schlechter als 30 und 120).
  Rauschen, nicht verwertbar.
- **NASDAQ:** monoton steigend, kürzere Haltedauer kostet klar. 360 Min.
  (+0,153) ≈ 16:00 (+0,137), Unterschied = die letzten ~15 Minuten,
  innerhalb des Rauschens. **EOD-Exit bestätigt.**

Ergebnis: die heutige Haltedauer bis Handelsschluss ist für alle drei
richtig. Ein Zeitstopp bringt nichts, was einer IS/OOS-Prüfung standhält.

## Was daraus folgt (nicht umgesetzt — Nutzerentscheid)

1. **SP500/US30 live an den Backtest angleichen:** Long-Order stornieren,
   sobald der Kurs orb_low berührt. Halbiert den MaxDD, kostet in Σ R
   kaum (SP500) bzw. nichts (US30).
2. **NASDAQ:** Storno am geplanten SL als Kandidat — vorher Phase 6
   (Monte Carlo) auf M1.
3. **Grundsätzlich:** ORB-Kennzahlen künftig auf M1 rechnen. Die
   bisherigen M5-Zahlen (inkl. Variante C, Stage 6–9) sind um ~25–45 %
   zu hoch. US30 ist auf M1 OOS praktisch ohne Edge.

Verwandt: [[ny-open-orb-sp500]], [[orb-exit-logik-neubewertung]].
