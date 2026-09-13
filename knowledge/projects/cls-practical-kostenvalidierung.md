# Projekt: CLS Practical — Kostenvalidierung und Risiko-Neubewertung

**Status:** Messung + Phase-6-Validierung abgeschlossen (2026-09-09).
Risiko-Entscheidung offen — siehe [[DASHBOARD]] "Offene Aufgaben".
**Bis dahin läuft `cls_practical` auf allen drei Portfolios unverändert live**
(Nutzerentscheid: erst validieren, dann Risiko anpassen).

Verwandt: [[broker-kostenmodell-eurusd]] (die Messwerte),
[[challenge-portfolio-ttp-icapital]] (das betroffene Live-Portfolio),
[[backtest-standard-process]] (Phase 6, nach der hier vorgegangen wurde).

---

## Anlass

2026-09-09 feuerte `cls_practical` zum ersten Mal live (seit 2026-09-07 in der
5-Min-Fast-Lane; die Signale vom 09-05/09-06 liefen noch als "missed" durch).
Alle drei Konten der Funded-Portfolio-Bridge wurden binnen 16 Sekunden
ausgestoppt — mit zusammen **−$1.634,08 gegen ein Budget von $741,20 (2,20x)**.
Positionsgrößen 18,58–22,72 Lots, auf TTP Konto 2 ~$2,42 Mio. Nominal auf
$99.842 Equity (~24:1).

Nutzerauftrag: Kostenmodell validieren, getrennt für Funded und EK.

---

## Befund 1 — der Spread war unschuldig, Slippage und Kommission fehlten

Gemessen (`scripts/measure_broker_spreads.py`, Details in
[[broker-kostenmodell-eurusd]]):

| | Spread | Slippage Entry+Exit | Kommission | **Round-Trip** |
|---|---|---|---|---|
| TTPMarkets | 0,30 | 0,70 + 0,65 | 0,40 | **~2,05 Pips** |
| BeyondIQCapital | 0,10 | 0,30 + 0,40 | 0,50 | **~1,30 Pips** |

`cls_practical/engine.py` rechnete mit `spread_bps=0.3` (≈0,35 Pips) und
`slippage_bps=0.0`, Kommission gar nicht. Der Spread-Ansatz war also
ungefähr richtig — die **Slippage war der größte einzelne Kostenblock und
stand auf null**.

---

## Befund 2 — bei echten Kosten bricht die Strategie weitgehend zusammen

`scripts/research_cls_practical_broker_cost_validation.py`, 206 Trades,
2018-12 bis 2026-09, `risk_pct=0,25 %` (das real gehandelte Risiko):

| Szenario | PF | Ø R | PnL $ | MaxDD % |
|---|---|---|---|---|
| Status quo (engine-default, 0,34 Pips) | 1,57 | +0,36 | +18.632 | −3,88 |
| **Funded / TTPMarkets (2,05 Pips)** | **1,12** | **+0,10** | **+5.031** | **−7,34** |
| Funded / BeyondIQCapital (1,30 Pips) | 1,29 | +0,21 | +10.980 | −5,80 |
| EK / Tickmill (1,20 Pips, *geschätzt*) | 1,31 | +0,23 | +11.773 | −5,60 |

**Breakeven liegt bei ~2,70 Pips Round-Trip.** TTP zahlt 2,05 — nur **0,65
Pips Luft**. Drei Konsequenzen:

1. **In-Sample ist auf TTP negativ**: PF 0,94, Ø R −0,06, −$1.170.
2. **5 von 8 Jahren negativ** auf TTP (2019 −0,54 / 2021 −0,68 / 2023 −0,24 /
   2024 −0,03 / 2026 −0,09). Getragen wird alles von 2020, 2022, 2025.
3. **MaxDD 7,34 % — über der eigenen 7-%-Gesamtdrawdown-Grenze der
   TTP-Challenge** (`RULES["ttp"]["total_dd_cap"]`). Das CLS-Bein *allein*
   hätte die Challenge historisch gerissen. (Standalone-Kurve des Beins, nicht
   das Gesamtportfolio — aber als Größenordnung eindeutig.)

---

## Befund 3 — der Schaden sitzt vollständig in den engen Stops

Gleicher Lauf, TTP-Kosten:

| Stop-Abstand | Trades | Anteil | Ø R dieser | Ø R der übrigen |
|---|---|---|---|---|
| < 4,10 Pips (2x Kosten) | 33 | 16,0 % | **−0,567** | +0,225 |
| < 6,15 Pips (3x Kosten) | 87 | 42,2 % | **−0,238** | **+0,343** |
| < 10,25 Pips (5x Kosten) | 148 | 71,8 % | +0,072 | +0,164 |

Der Median-Stop liegt bei 7,0 Pips, p10 bei 3,5. **Würde man Stops unter
~6 Pips gar nicht handeln, stiege Ø R auf TTP von +0,10 auf +0,343** — und
das Bein läge wieder deutlich über Breakeven. Das ist das stärkste einzelne
Ergebnis dieser Untersuchung.

Der bestehende Schutz `min_sl_atr_mult = 1.0 × ATR(M5)` greift hier nicht: er
ist **relativ** und schrumpft in ruhigen Phasen mit. Am 2026-09-09 ließ er
einen 3,6-Pip-Stop durch.

---

## Befund 4 — Entry-Lag erzeugt keinen Durchschnitts-, sondern einen Tail-Schaden

`scripts/research_cls_practical_entry_lag.py`: der Backtest steigt zum
Schlusskurs der Signalbar ein, der Live-Bot beim nächsten 5-Min-Scan — der
Stop bleibt aber auf dem **absoluten** Preis aus dem Signal. Weil
`Funded-Portfolio-Bridge/sizing.py` die Lots als
`risk_dollars / |Live-Kurs − SL|` rechnet, wirkt jede günstige Drift als Hebel.

Im **Median** ist das harmlos — der effektive Abstand *wächst* sogar
(7,0 → 9,0/9,5/10,1 Pips bei 5/10/15 Min. Lag), die Lots schrumpfen auf das
0,69–0,78-fache. CLS ist eine Fortsetzungsstrategie, der Kurs läuft im Mittel
vom Stop weg.

Der **Tail** ist das Problem (Lag 10 Min., n=206):

| | Signale | Anteil |
|---|---|---|
| Kurs beim Entry schon hinter dem Stop | 10 | 4,9 % |
| Abstand < TTP-Kostenblock (2,05 Pips) | 27 | **13,1 %** |
| Abstand < 2x Kostenblock | 50 | 24,3 % |
| **Erzeugter Hebel > 5x Equity** | — | **29,1 %** |

Der Trade vom 2026-09-09 war also **kein Ausreißer, sondern ein regelmäßig
wiederkehrender Fall**: rund jedes achte Signal kommt live mit weniger Abstand
zum Stop an, als der Round-Trip überhaupt kostet, und knapp jedes dritte
erzeugt über 5x Equity an Nominal.

---

## Was daraus folgt (Entscheidung steht beim Nutzer)

Die Zahlen legen drei Eingriffe nahe, in dieser Reihenfolge der Wirkung:

1. **Absoluter Pip-Floor auf den Stop-Abstand** (~6 Pips EURUSD), zusätzlich
   zum relativen `min_sl_atr_mult`. Größter Hebel: Ø R +0,10 → +0,343.
2. **Mindest-Abstand zwischen Live-Fill und SL** als Entry-Gate in der Bridge —
   fängt die 13 %, die strukturell nicht gewinnen können.
3. **Nominal-/Hebel-Deckel** als hartes Sicherheitsnetz für alle Beine
   (29 % der CLS-Signale erzeugen >5x Equity).
4. **Kostenmodell korrigieren**: `spread_bps`/`slippage_bps` je Broker auf die
   gemessenen Werte, Kommission einbeziehen.

Offen bleibt außerdem, ob `cls_practical` auf **TTP** überhaupt weiterlaufen
soll: PF 1,12, In-Sample negativ, 5 von 8 Jahren negativ, MaxDD über der
Challenge-Grenze. Auf IQ Markets (1,30 Pips) ist die Lage spürbar besser.

**Nicht belastbar:** EK/Tickmill. Die Tickhistorie deckt das Handelsfenster
mit 15 Ticks nicht ab; die EK-Zeile oben ist geschätzt. Braucht
Vorwärts-Sampling. (EK hat den Trade vom 2026-09-09 ohnehin nicht genommen —
der 8-%-Gesamtrisiko-Deckel hat ihn geblockt, siehe [[DASHBOARD]].)

---

## Verifikation

1. **Messung plausibel** — TTP-Spread (0,30) liegt wie vom Live-Vorfall
   vorhergesagt über IQ (0,10). Keine Werte außerhalb des plausiblen Bandes.
2. **Keine MT5-Terminals hinterlassen** — alle vier Zielterminals liefen schon
   vorher, das Skript hat keines gestartet und folglich keines geschlossen.
3. **Referenzlauf NICHT reproduzierbar — und das ist ein eigener Befund.**
   `cls_practical/results/final_verification_vs_buyhold.csv` weist $60.393,55
   aus, derselbe Aufruf liefert heute **$73.558,93** (+22 %). Ursache gefunden:
   die CSV stammt vom **2026-08-13**, `cls_practical/engine.py` wurde am
   **2026-08-20** geändert (`f549b23`, führte u.a. `test_hour=9.0` ein — ein
   Parameter, der die Trade-Auswahl verändert). Die gespeicherte CSV ist also
   **veraltet und irreführend**, nicht mein Harness. Sie sollte neu erzeugt
   werden. (Zweiter Fall dieser Art nach dem Gold-ASB-Liquiditätsfilter.)
4. **Plausibilitätsanker gegen die Realität — teilweise erreicht.** Der Trade
   vom 2026-09-09 im Backtest:

   | Kostenannahme | R |
   |---|---|
   | Status quo (0,34 Pips) | −1,097 |
   | IQ (1,30 Pips) | −1,376 |
   | TTP (2,05 Pips) | −1,593 |
   | **real auf TTP Konto 2** | **−2,33 (nur Kurs) / −2,67 (mit Kommission)** |

   Das korrigierte Kostenmodell schließt also gut die Hälfte der Lücke
   (−1,10 → −1,59), **aber nicht die ganze**. Der Rest ist genau der Effekt,
   den ein Kostenmodell strukturell nicht abbilden kann: der Backtest sizet auf
   `sl_dist` (3,6 Pips), der Live-Bot auf `|Live-Fill − SL|` (1,2 Pips) — also
   dreifache Positionsgröße bei gleichem $-Budget. Bestätigt Befund 4.
5. **Keine Änderung an Bridge-Code, Config oder Scheduled Tasks durch diese
   Arbeit.** `sizing.py` unverändert seit 2026-08-28.

### Achtung: Datenlage-Fußnoten

- Der Auswertungslauf lief mit `--end 2026-09-09`; das Enddatum der
  Dukascopy-Fetches ist **exklusiv**, der 2026-09-09 selbst fehlt darin. 206
  statt 207 Trades. Für die Aussagen ohne Belang, für Wiederholungen relevant.
- Eine **parallele Session** hat am selben Abend (22:11–22:28) unabhängig an
  `Funded-Portfolio-Bridge/run_once.py` + `executor.py` gearbeitet (Signal-
  Alter/Stop-Gate) und die Scheduled Tasks hinter den DataLake-Ingest gelegt
  (`Funded-Portfolio-Bridge-Fast` von ≡0 auf ≡3 mod 5). Letzteres verschiebt
  die reale Entry-Latenz und damit die Verteilung aus Befund 4 leicht — die
  dortige Lag-Spanne von 5–15 Minuten deckt den neuen Zustand weiterhin ab.

---

## Befund 5 — SL-Varianten: nur der absolute Pip-Boden trägt (2026-09-10)

`scripts/research_cls_practical_sl_optimization.py`, alle Läufe unter
TTP-Kosten (2,05 Pips). Dafür wurden `cls_practical/engine.py` drei Parameter
ergänzt — `min_sl_pips`, `sl_floor_mode`, `session_sl_mult` — **mit Defaults,
die das bisherige Verhalten exakt reproduzieren** (Regressionslauf: 207 Trades,
identische PnL mit und ohne explizite No-Op-Parameter). Wichtig, weil der
Live-Bot diese Datei über `challenge_portfolio/paper_bot.py` direkt importiert.

| Variante | Trades | PF | Ø R | IS | OOS | MaxDD | Hebel max |
|---|---|---|---|---|---|---|---|
| Baseline | 207 | 1,11 | 0,09 | −0,06 | +0,19 | −7,34 % | 10,0 |
| Pip-Boden 4 (drop) | 173 | 1,31 | 0,22 | +0,09 | +0,33 | −5,27 % | 6,1 |
| **Pip-Boden 5 (drop)** | **152** | **1,52** | **0,34** | **+0,28** | **+0,38** | **−3,10 %** | **5,0** |
| Pip-Boden 6 (drop) | 122 | 1,65 | 0,38 | +0,45 | +0,34 | −1,80 % | 4,2 |
| Pip-Boden 7 (drop) | 102 | 1,61 | 0,34 | +0,68 | +0,16 | −1,93 % | 3,6 |
| ATR-Mult 1,5 (drop) | 92 | 1,36 | 0,20 | +0,18 | +0,21 | −2,92 % | 6,4 |
| Pip-Boden 5 (**widen**) | 307 | 0,99 | −0,01 | 0,00 | −0,02 | −11,68 % | 5,0 |
| Session-Vol-SL ×1,0 | 171 | 0,61 | −0,47 | −0,47 | −0,47 | −21,70 % | 9,2 |
| Session-Vol-SL ×3,0 | 307 | 1,11 | 0,07 | +0,04 | +0,08 | −3,03 % | 3,4 |

**Verworfen:**
- **Stop aufweiten statt Trade verwerfen ("widen")** — PF 0,97–1,09 über alle
  Stufen. Das TP-Ziel (`adr_mult × ADR`) bleibt stehen, wenn der Stop breiter
  wird, also kollabiert das R:R. Man behält den schlechten Trade und zerstört
  zusätzlich sein Chancenverhältnis.
- **Volatilitätsgemittelter fester Stop** — bestenfalls Baseline-Niveau
  (×3,0: PF 1,11), bei ×1,0 katastrophal (Ø R −0,47). Er ersetzt das
  **strukturelle** SL-Niveau durch eine reine Volatilitätsdistanz. Offenbar
  trägt genau dieses Niveau — der Punkt, an dem das Setup invalidiert wird —
  den Edge. Es ist nicht egal, *wo* der Stop liegt, nur *wie weit*.
- **Höheres ATR-Multiple** — hilft (Ø R 0,20), aber deutlich weniger als der
  absolute Boden, und verwirft mehr Trades (92 statt 152). Bleibt relativ und
  lässt in ruhigen Phasen weiter dünne Stops durch.

**Warum "drop" funktioniert:** der strukturelle Stop UND das R:R bleiben
erhalten, es werden nur Setups ausgelassen, deren Struktur innerhalb des
Kostenbandes liegt. Faustformel: **Boden ≈ 2,5 × Round-Trip-Kosten.**
Das Optimum ist ein breites Plateau von 4–6 mit Abfall erst ab 7 — kein
Einzelspike. Auf IQ-Kosten gegengeprüft: derselbe Boden trägt (PF 1,70).

### Aber: löst das Kosten-, nicht das Hebelproblem

Entry-Lag-Tail bei 10 Min. Verzögerung:

| | hinter SL | Abstand < 2,05 Pips | Hebel > 5x | Hebel max |
|---|---|---|---|---|
| Baseline | 4,8 % | 13,5 % | 29,5 % | **125x** |
| Boden 5 | 5,3 % | 9,9 % | 19,1 % | **125x** |
| Boden 6 | 3,3 % | 8,2 % | 14,8 % | **125x** |

Der Boden drückt den Tail, **das Extrem bleibt unverändert**. Es braucht
zusätzlich ein Entry-Gate und einen Hebel-Deckel in der Bridge.

---

## Befund 6 — TP-Varianten: nichts schlägt das bestehende Ziel belastbar (2026-09-10)

`scripts/research_cls_practical_tp_variants.py`, 40 Kombinationen aus
Pip-Boden × TP-Ziel, plus Break-even-Nachziehen und IQ-Gegenprobe.

**Fester 2R-TP (explizit angefragt): klar schlechter.** Mit Boden 5p PF 1,14 /
Ø R 0,09 gegen PF 1,52 / Ø R 0,34 beim bestehenden ADR-Ziel. Ohne Boden sogar
PF 0,98. Der feste R-Multiplikator zeigt eine U-Form (1R 1,14 / 1,5R 1,18 /
2R 1,14 / 2,5R 1,28 / **3R 1,47** / 4R 1,29) — ausgerechnet 2R liegt in der
Senke.

**Break-even-Nachziehen: durchgehend schädlich.** Auf jeder getesteten
Konfiguration schlechter als ohne (z.B. Boden 5p + adr 0,75: Ø R 0,55 → 0,13
bei BE 1R, → 0,35 bei BE 1,5R). Es schneidet die Gewinner ab, die diese
Strategie trägt.

**Weiteres ADR-Ziel sah zunächst besser aus — hält aber der Prüfung nicht
stand.** `adr_mult=0.75` + Boden 5p ergab PF 1,64 / Ø R 0,55. Zwei Gründe,
das NICHT zu übernehmen:

1. **Das Optimum lag am Gitterrand.** Nach Erweiterung auf 0,6–1,5 zeigt sich
   eine *zackige, nicht-monotone* Fläche (Boden 5p, Ø R OOS): 0,35→0,38 /
   0,5→0,30 / 0,6→0,33 / 0,75→0,49 / 0,9→0,34 / 1,0→0,43 / 1,25→0,34 /
   1,5→0,61. Kein Plateau, kein stabiles Optimum — das Muster von Rauschen.
2. **Bootstrap (Phase 6, p6_2; 10.000 Resamples, 90 %-Intervall):**

| Konfiguration | n | Treffer% | Ø R | 90 %-Intervall | P(Ø R < 0) |
|---|---|---|---|---|---|
| Ist-Zustand, kein Boden | 207 | 39,6 % | 0,09 | [−0,14 .. +0,32] | **26,6 %** |
| **Boden 5p, TP adr 0,35 (Ist-TP)** | 152 | 48,0 % | 0,34 | [+0,09 .. +0,58] | **1,2 %** |
| Boden 5p, TP adr 0,75 | 152 | 29,6 % | 0,55 | [+0,14 .. +0,98] | 1,1 % |
| Boden 5p, TP adr 1,0 | 152 | 23,0 % | 0,57 | [+0,08 .. +1,08] | 2,8 % |
| Boden 5p, TP 2R fix | 152 | 44,1 % | 0,09 | [−0,11 .. +0,29] | 21,6 % |
| Boden 5p, TP 3R fix | 152 | 39,5 % | 0,35 | [+0,09 .. +0,61] | 1,2 % |
| Boden 6p, TP adr 1,5 | 122 | 18,0 % | 0,65 | [+0,01 .. +1,36] | 4,5 % |

Die Intervalle der TP-Varianten **überlappen fast vollständig**. Der höhere
Punktschätzer der weiten Ziele wird von einer proportional größeren
Unsicherheit begleitet, weil die Trefferquote von 48 % auf 23 % fällt — immer
weniger Gewinner tragen immer mehr Ergebnis. Es gibt **keinen Beleg**, dass ein
weiteres Ziel wirklich besser ist. `3R fix` ist statistisch nicht vom
Ist-Zustand unterscheidbar (0,35 vs. 0,34).

**Was der Bootstrap dagegen eindeutig zeigt:** der Pip-Boden senkt die
Wahrscheinlichkeit eines negativen Erwartungswerts von **26,6 % auf 1,2 %**.
Das ist der eine belastbare Hebel dieser ganzen Untersuchung.

### Schlussfolgerung

**SL-Boden ändern, TP unangetastet lassen.** Die 48 %-Trefferquote des
bestehenden Ziels ist zudem robuster gegen Verluststrecken als die 23–30 % der
weiten Varianten.

---

## Befund 7 — Umbau umgesetzt und final verifiziert (2026-09-11)

**Implementiert** (Details im `CHANGELOG.md`-Eintrag vom 2026-09-11):
`min_sl_pips=5` + `LEG_RISK_PCT` 0,015 → 0,010 in `challenge_portfolio/paper_bot.py`;
R-Detektor `MAX_CONSUMED_R_FOR_ENTRY = 0.50` in
`Funded-Portfolio-Bridge/run_once.py`; Margin-Deckel
`MAX_MARGIN_PCT_OF_EQUITY = 0.20` in `Funded-Portfolio-Bridge/sizing.py`.

### Abschluss-Backtest, Live-Simulation, implementiertes Risiko (0,1667 %/Trade)

| | TTP (2,05 Pips) | IQ (1,30 Pips) |
|---|---|---|
| Trades (≈/Jahr) | 140 (19,7) | 139 (19,6) |
| Trefferquote | 52,1 % | 52,5 % |
| Profit-Faktor | 1,48 | 1,68 |
| Ø R | +0,25 | +0,35 |
| Ø R In-Sample / OOS | +0,17 / **+0,31** | +0,28 / **+0,39** |
| P(Ø R < 0), Bootstrap | 2,16 % | 0,47 % |
| Gesamt-Return (7,8 J.) | +5,91 % | +8,02 % |
| CAGR | **0,78 %** | 1,05 % |
| Sharpe / Sortino | 0,69 / 4,24 | 0,89 / 8,55 |
| MaxDD | −1,66 % | −1,25 % |
| Calmar | **0,47** | 0,84 |
| schlechtester Tag | −0,23 % | −0,19 % |
| längste DD-Phase | 574 Tage (~2,3 J.) | 415 Tage |
| Hebel max | 5,70x | 4,22x |

**Regeleinhaltung: deutlich entschärft.** MaxDD 1,66 % = 24 % des
TTP-Budgets (vorher 40 %), schlechtester Tag −0,23 % gegen eine
3-%-Grenze, maximaler Hebel 5,7x statt 58,8x.

**Ø R je Jahr** (TTP): 2019 −0,05 / 2020 +0,56 / 2021 **−0,46** /
2022 +0,65 / 2023 −0,21 / 2024 +0,47 / 2025 +0,79 / 2026 +0,11 —
drei von acht Jahren negativ.

### Bewertung: Edge real, Beitrag zu klein

**Dafür:** OOS (+0,31) liegt ÜBER In-Sample (+0,17) — kein Overfit-Muster,
das stärkste Einzelargument. P(negativer Erwartungswert) 2,16 %. Beide
Broker positiv. Regelkonform mit großem Abstand.

**Dagegen:** **CAGR 0,78 %.** In einem Challenge-Konto mit +10 %-Ziel und
begrenzter Laufzeit kann ein Bein, das pro Jahr unter einem Prozent liefert,
seinen Anteil am Ziel nicht beitragen — rechnerisch bräuchte es für seinen
Sechstel-Anteil (1,67 %) gut zwei Jahre. Dazu Calmar 0,47 und 2,3 Jahre
längste Unterwasserphase.

**Entscheidung: behalten, aber auf Bewährung** — mit Abbruchkriterium statt
unbefristet. Begründung: das Bein gefährdet die Challenge nicht mehr (24 %
Drawdown-Budget), der Edge ist statistisch real, und ein Bein wegzuwerfen,
dessen Out-of-Sample besser ist als sein In-Sample, unmittelbar nachdem es
repariert wurde, würde nie zeigen, ob die Reparatur trägt.

**Offen und entscheidungsrelevant:** die Calmar-Werte der anderen fünf Beine
sind nicht erhoben. Ohne sie lässt sich nicht sagen, ob 0,47 im Portfolio
schwach ist oder normal — und damit nicht, ob der Platz besser vergeben wäre.
Das ist die nächste sinnvolle Messung.
