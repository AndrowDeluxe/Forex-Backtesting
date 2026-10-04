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

## Nachtrag 2026-10-01 — Monte Carlo (Phase 6) zur SL-Storno-Regel

`scripts/research_orb_cancel_at_sl_montecarlo.py`, M1, 3.000 Pfade,
Block = Kalendermonat. Drei Bewertungen der mehrdeutigen Füll-Minuten:
basis (wie `simulate()`), mitte (50 % Stop-out), pessim (immer Stop-out).
Entscheidend ist Ertrag/MaxDD (skalierungsfrei, weil die Regel weniger
Trades übrig lässt):

| NASDAQ | basis | mitte | pessim |
|---|---|---|---|
| heute (kein Storno): Ertrag/DD Median | 4,03 | **−0,48** | −0,96 |
| heute: P(Σ R < 0) | 1,0 % | **76 %** | 100 % |
| Storno am SL: Ertrag/DD Median | 3,76 | **1,58** | 0,04 |
| Storno am SL: P(Σ R < 0) | 1,2 % | **11 %** | 48 % |

**NASDAQ: bestanden.** Im optimistischen Fall gleichwertig, in jedem
anderen klar besser. Der heutige NASDAQ-Edge hängt komplett daran, dass
die mehrdeutigen Füll-Minuten (1/3 aller Trades) fast alle gut ausgehen.
**SP500:** „Gegenseite“ (jetzt umgesetzt) schlägt die SL-Regel in basis/
mitte (7,35/5,11 vs. 5,30/4,62), nur pessimistisch nicht → keine SL-Regel.

Nächster sinnvoller Schritt: die mehrdeutigen Füll-Minuten mit Tickdaten
auflösen, dann ist der NASDAQ-Edge nicht mehr ein Bereich, sondern eine Zahl.

## Nachtrag 2026-10-04 — Tick-Auflösung + M1-Exit-Gitter + Portfolio-MC

Skripte: `research_orb_fill_minute_ticks.py`, `research_orb_exit_grid_m1.py`
(eigener numpy-Simulator, Trade für Trade = `simulate()`, max |ΔR| = 0),
`research_orb_m1_candidates_montecarlo.py`.

**Füll-Minuten mit Ticks aufgelöst (1.225 von 1.225):** nur 12–22 % der
mehrdeutigen Minuten (Stop 0,6) sind echte Stop-outs nach dem Fill, 78–88 %
hatten den SL-Touch VOR dem Fill (Trade gültig). Tick-Korrektur Ø R:
SP500 0,494 → 0,455, US30 0,244 → 0,230, NASDAQ 0,137 → 0,127. **M1 ist
damit praktisch die Wahrheit**, die pessimistische Grenze war viel zu
streng. M5 bleibt zu hoch (dort 70 % mehrdeutig).

**NASDAQ — das Teilziel ist das Problem, nicht der Stop:**

| Stop 0,6 | Trades | Ø R | OOS | Σ R | MaxDD | Jahre+ |
|---|---|---|---|---|---|---|
| heute (Teilziel 3R) | 1595 | 0,127 | 0,047 | 203 | −49 | 7/8 |
| ohne Teilziel | 1595 | 0,254 | 0,139 | 404 | −65 | 7/8 |
| Storno am SL + ohne Teilziel | 442 | 0,463 | 0,372 | 205 | −39 | **8/8** |

Ohne Teilziel hängt 65 % des Ergebnisses an 2021/22 (2023: −26,5 R); mit
Storno nur 40 %, schlechtestes Jahr +11,6 R.

**Portfolio-MC (Monatsblöcke, 3.000 Pfade, 1 R je Trade):**

| Portfolio | Σ R | OOS Σ R | MaxDD Median / P95 | Ertrag/DD |
|---|---|---|---|---|
| A heute (Variante C) | +459 | +88 | −54 / −100 | 8,5 |
| B NASDAQ ohne Teilziel | +661 | +159 | −61 / −110 | 10,6 |
| C NASDAQ Storno + ohne Teilziel | +457 | +138 | −41 / −74 | 11,0 |
| E = C ohne US30 | +372 | +137 | −32 / −56 | **11,8** |

**US30:** OOS (ab 2023) +1,0 R aus 197 Trades (Ø +0,005); nur 19 von 112
Gitter-Varianten sind IS und OOS positiv. Kein belastbarer Edge mehr.
**SP500:** heutige Config (0,6 / 6R / ohne Teilziel) bleibt — Nachbarn
schwächer, nichts Besseres im Gitter.

**UMGESETZT 2026-10-04 (Nutzerentscheid)** auf allen drei Bridges, siehe CHANGELOG. Live gepollt: Blitz-Trades (Fill zwischen SL-Touch und nächstem Lauf) kosten ~−21 R von +205 R (`research_orb_sl_cancel_poll_latency.py`). Ursprüngliche Empfehlung: NASDAQ auf Storno am SL + ohne
Teilziel (Portfolio C); US30 pausieren (E). Beides keine frisch gefischten
Parameter: „NASDAQ ohne Teilziel“ war schon Variante D vom 21.09., die
Storno-Schwelle ist der bestehende Stop. Auf M5 sah das Teilziel nur besser
aus, weil M5 die Füll-Bar falsch rechnet.

Verwandt: [[ny-open-orb-sp500]], [[orb-exit-logik-neubewertung]].
