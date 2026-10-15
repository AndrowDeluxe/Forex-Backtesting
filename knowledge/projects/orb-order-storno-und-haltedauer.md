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

## Nachtrag 2026-10-06 — Nur auf IS optimiert: OOS hält, Tresor fällt durch

Anlass: Die Live-Konfiguration wurde ab Stage 2 auf OOS ausgewählt (siehe
[[overfitting-sperre]]). Dieser Test baut die Strategie neu auf, und zwar
ausschließlich auf IS (07/2016–12/2022). Danach wurde sie eingefroren und
OOS (01/2023–09/2025) sowie der Tresor (10/2025–09/2026) je einmal geöffnet.
Die Öffnungen sind technisch gesperrt (`research_lock.py`).

**Runde 1** (`scripts/research_orb_is_only_reopt.py`): 8 Punkte, 22.680
Varianten je Index. Die Gewinner hatten einen Wochentag-Ausschluss und
bestanden die Deflated Sharpe nicht. Die Runde wurde vor jeder OOS-/Tresor-
Berechnung verworfen.

**Runde 2** (`scripts/research_orb_is_only_7p.py`): Nutzerentscheid, nur
SP500 + NASDAQ, je Index 7 Punkte (Richtwert max. 9), ohne Wochentag.

| Index | Gewählt (nur IS) | IS PF | OOS PF | Tresor Σ R / PF |
|---|---|---|---|---|
| SP500 | long + short, Ribbon neutral, kein Storno, Stop 1,0 ATR, Ziel 8R | 1,41 | 1,38 | −54 / 0,48 |
| NASDAQ | nur long, Ribbon neutral, kein Storno, Stop 1,0 ATR, Ziel 8R | 1,60 | 1,28 | −33 / 0,57 |

- **100k-Konto, 1 % vom Kontostand je Trade, im Tresor:** 40,5k, MaxDD −62 %.
- **Kein Datenfehler:** Die Trades sind normal über die Monate verteilt, die
  Verluste bei −1 R gedeckelt. NASDAQ zerfällt schon seit 2022
  (2022 −0,07; 2025 −0,08; 2026 −0,40 R je Trade).
- **Deflated Sharpe ~0,** auch mit echter Schiefe. Die Varianz der Sharpe-
  Werte über die Varianten ist so groß wie das Schätzrauschen.
- **Live-Version im selben Tresor:** SP500 +5 R, NASDAQ +55 R (M1 ohne
  Ticks). Sie wurde aber mit Blick darauf gewählt und ist kein fairer Test.

**Folgerung:** Ohne Blick auf OOS führt der ORB-Prozess zu einer Version,
die nach IS und OOS wie ein Treffer aussieht und im Tresor zusammenbricht.
Das stützt den Overfitting-Verdacht gegen die ganze Familie. Was das für die
Live-Version bedeutet, ist offen (DASHBOARD 🔍).

Dateien:
- `ny_open_orb/results/is_only_7p_*` (Auswahl, Reports, Trades, Konto)
- PDF für die Gruppenarbeit: `Claude outputs/orb_profitabilitaets_kriterien_20261005.pdf`

### Diagnose 2026-10-06: Woran der Tresor scheitert — der Trendfilter kippt

Das ist reine Diagnose auf dem bereits geöffneten Tresor, keine neue Auswahl.
Skript: `Claude outputs`-Scratch, Varianten über `run_config` aus
`research_orb_is_only_reopt.py`.

- **Der Trendfilter hat sich umgedreht.** Gemessen ist der Unterschied im Ø R
  je Trade zwischen „Ribbon neutral“ und „Ribbon mit Trend“ (beide
  Richtungen, Stop 1,0, 8R). Von 2017 bis 2025 ist er in 16 von 18 (Ausnahmen nahe null: NASDAQ 2019 −0,04, 2022 −0,01)
  Index-Jahren positiv (SP500 +0,2 bis +0,7; NASDAQ +0,3 bis +0,7). Im
  Tresor ist er erstmals bei beiden negativ: SP500 −0,65 (neutral −0,48,
  Trend +0,17), NASDAQ −0,41 (−0,28 / +0,13). Je Topf sind es ~110 Trades,
  über beide Indizes zusammen grob 2,4 σ.
- **2022 (Zinsschock, Ölpreis) hat der Filter gehalten** (SP +0,38).
  Makrostress allein erklärt den Kipp also nicht.
- **Die Mechanik der Eröffnung selbst ist unverändert:** Folgen nach dem
  ersten Ausbruch ~50 %, Range-Breite ~2,4/3,0 × ATR, Anteil Tage mit
  Ausbruch in beide Richtungen normal. Das Intraday-Momentum (erste gegen
  letzte 30 Min.) liegt im Tresor sogar bei +0,11 statt ~0.
- **Der ungefilterte ORB war nie stark** (SP500 Ø +0,04 / −0,04 / +0,23 je
  Periode). Fast der ganze Edge der IS-Version kam aus „nur neutrale Tage“.
- **Das erklärt auch die Live-Version:** NASDAQ live hat keinen
  Ribbon-Filter und blieb im Tresor positiv. SP500 live nutzt „neutral“ und
  lag im Tresor bei ~0.
- **Die Web-/SSRN-Erklärung ist eine Hypothese, nicht belegt:** Das
  Dealer-Gamma-Regime hat sich verschoben.
  - SpotGamma (03/2026): Das länger laufende Dealer-Gamma ist negativ bis
    neutral, der Markt dreht von mean-reverting zu momentum-getrieben.
  - Dim/Eraker/Vilkov: Positives Gamma stärkt Reversals, negatives
    Momentum.
  - Adams et al. (10/2025): 0DTE-Hedging dämpft das Momentum.
  - Dazu kommen der Rekord-Anteil 0DTE (~63 % des SPX-Volumens, 02/2026)
    und das Makro-Umfeld 2026: Iran-Krieg, Öl > 100 $, Q1 −9 %, Q2 bestes
    Quartal seit 2020, Fed-Erhöhung 09/2026.
  - Testbar nur mit GEX-Historie (Ideen-Inbox „ORB-Gamma-Regime-Filter“).

### Anatomie des Tresor-Kipps + Exit-Varianten (07.10., Diagnose)

Skript `scripts/research_orb_tresor_kipp_anatomie.py`; der Simulator ist
paritätisch zu `sim()`, max |ΔR| = 0. Betrachtet wird die IS-only-7p-Version
in IS 2016–22, OOS 2023–09/25 und Tresor.

| | SP500 IS / OOS / Tresor | NASDAQ IS / OOS / Tresor |
|---|---|---|
| Trefferquote | 22 % / 22 % / **12 %** | 27 % / 23 % / **18 %** |
| Ø Gewinner | 5,1 / 5,2 / **3,8 R** | 4,5 / 4,3 / **2,7 R** |
| Ø Verlierer | −1,05 / −1,05 / −1,04 R | −1,03 / −1,02 / −1,01 R |
| Anteil Stop | 77 % / 78 % / **88 %** | 73 % / 75 % / 80 % |
| Median Minuten bis Stop | 14 / 12 / **7,5** | 17 / 12 / 14 |
| Trades mit MFE ≥ 4R | 24 % / 24 % / **14 %** | 23 % / 19 % / **13 %** |
| erst +1R, dann Stop | 29 % / 29 % / 30 % | 29 % / 27 % / 28 % |

**Befund:** Der Edge kippt vollständig.
- Die Verluste sind **nicht größer** (−1 R gedeckelt), sondern **häufiger und
  schneller**.
- Es gibt weniger Läufer, und die Gewinner sind kleiner.
- „Gewinne wieder abgeben“ hat nicht zugenommen.
- Long und Short sind beide negativ.

**Exit-Varianten** (TP 2/3/4R, BE ab +1/+2R, 50 % bei 1R/2R + BE, Zeitstopp
60/120 Min.): Keine macht den Tresor positiv. Die besten dämpfen ihn nur:
SP500 −0,48 → −0,21 R (Zeitstopp), NASDAQ −0,36 → −0,13 R (TP 2R). Zugleich
kosten alle Varianten in IS/OOS Edge. **Ein Exit-Problem ist es nicht.**
Gekippt ist das Durchziehen der Ausbrüche selbst.

## Nachtrag 2026-10-16 — NASDAQ mit/ohne Storno, sauber über 10 Jahre

Nutzerfrage: „Warum haben wir die Storno-Variante gewählt, wenn sie schlechter ist?“
Skript `scripts/research_orb_nasdaq_storno_vergleich.py` (M1, gleicher Simulator, Live-Config
sonst gleich: OCO, ohne Mittwoch, Stop 0,6, kein Ziel, 16:00). Zahlen
`ny_open_orb/results/nasdaq_storno_vergleich*.csv`.

| | IS 2016–22 | OOS 2023–09/25 | Tresor 10/25–09/26 | 10 Jahre gesamt |
|---|---|---|---|---|
| mit Storno: n / Ø R / Σ R | 440 / +0,23 / +101 | 208 / +0,21 / +43 | 89 / **+0,62** / **+55** | 737 / +0,27 / **+198** (t 1,8, DD −65) |
| ohne Storno: n / Ø R / Σ R | 1.322 / +0,36 / **+477** | 566 / +0,15 / **+86** | 205 / +0,10 / +21 | 2.093 / +0,28 / **+584** (t 3,2, DD −64) |
| durch Storno weggefallene Tage: Ø R | **+0,43** | +0,12 | **−0,29** | +0,28 |

Je Jahr Σ R (mit / ohne): 2016 −24/+8 · 2017 −13/+73 · 2018 −7/+88 · 2019 +44/+30 ·
2020 +20/+13 · 2021 +42/+125 · 2022 +39/+140 · 2023 +12/−27 · 2024 +13/+34 · 2025 +12/+64 · 2026 +61/+35.

**Warum am 04.10. trotzdem gewählt:**
1. **Fenster 2019–2026.** Die drei Jahre 2016–18, in denen die Storno-Variante verliert,
   lagen nicht im Test. Ab 2019 ist sie 8/8 Jahre positiv; das war das Hauptargument.
2. **„OOS“ ab 2023 enthielt 2026.** Genau dort glänzt sie (+61 R). Das war vor der
   Overfitting-Sperre (eingeführt 05.10., einen Tag später) — heute wäre das ein Blick in den Tresor.
3. **Robustheit gegen mehrdeutige Füll-Minuten** (MC 01.10.: ohne Storno P(Σ<0) 76 % im
   mittleren Szenario). Dasselbe Ziel lösten die Ticks am 04.10. auf: 78–88 % der
   mehrdeutigen Minuten waren gültige Trades. Damit fiel das Argument weitgehend weg.
4. Bewertet wurde Ertrag/DD und Qualität je Trade, nicht Σ R. Über 10 Jahre ist aber auch
   Σ R/DD ohne Storno besser (9,1 gegen 3,0).

**Lesart:** Die Storno-Variante ist im Kern ein 2026-Fit. Über die saubere Historie ist die
Variante ohne Storno klar besser; im Tresor schlechter. Die weggefallenen Tage drehen
genau 2026 ins Minus — dasselbe Regime-Muster wie beim Ribbon-Kipp.
Entscheidung offen (Dashboard 🔍).
