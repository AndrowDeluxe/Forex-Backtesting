# Projekt: CTNL Edge — Kosten- und Ausführungsvalidierung

Status: **Proben abgeschlossen, Entscheidung offen** (2026-09-21).
Pflichtteil p6_5–p6_8 aus
[[realkosten-und-ausfuehrungs-probe]] für die beiden CTNL-Beine auf allen
Bridges. Strategie-Kontext: [[gold-ctnl-edge-portfolio]].

Vorbild und Vergleichsfall: [[cls-practical-kostenvalidierung]] — dort deckte
**jede einzelne der vier Proben** einen echten Fehler auf, den die regulären
Phase-6-Punkte nicht gefunden hätten.

---

## Anlass

Am 2026-09-17/18 löste `ctnl_reversal` eine Order-Flut aus, die das
Echtgeld-Konto TTP Konto 1 breachte (eine neue XAUUSD-Position pro M15-Bar,
38 gleichzeitig offen gegen 3 laut Design). **Die Ursache der Flut ist
behoben** — ein fehlender Live-Deckel, siehe `CHANGELOG.md` 2026-09-19/09-21.

Dieses Projekt geht der **davon unabhängigen** zweiten Frage nach: verdient
das CTNL-Bein überhaupt seine Kosten? Der Verdacht ist nicht allgemein,
sondern steht namentlich in [[realkosten-und-ausfuehrungs-probe]]:

> Im Repo standen nebeneinander `spread_bps=0.3` (cls_practical) und
> `spread_bps=8.0` (CTNL) — beides gegriffene Zahlen.

Verifiziert: `strategy/backtest.py:30::BacktestConfig` kennt **nur**
`spread_bps`. Es gibt kein Slippage- und kein Kommissionsfeld — beide stehen
für CTNL damit auf null. Exakt die Konstellation, die bei `cls_practical` am
09-09 im ersten Live-Trade das 2,2-fache des Budgets kostete.

Nutzerauftrag 2026-09-19: Kosten- und Ausführungstest für das CTNL-Bein auf
allen Bridges. Umfang bestätigt 2026-09-21: **beide Beine, alle vier Proben,
Ergebnis als Entscheidungsvorlage** (kein Bot wird in diesem Projekt scharf
geändert).

---

## Ausgangslage — die beiden Beine haben gegensätzliche Kostenprofile

| | `ctnl_reversal` | `ctnl_continuation` |
|---|---|---|
| Kostenansatz | `spread_bps=8.0` | `spread_bps=8.0` |
| Stop | `stop_atr_mult=3.0` (weit) | `stop_atr_mult=0.5` (eng) |
| Ziel | `take_profit_r=5.0` | VWAP |
| Signal-Timeframe | M15 | M5 |
| Lane | Slow (15 Min.) | Fast (5 Min.) |

Quelle: `challenge_portfolio/paper_bot.py::_scan_ctnl`. Probe 4 (Stopdistanz
gegen Kosten) trifft deshalb fast ausschließlich das Continuation-Bein — es
ist der blinde Fleck, den eine reine Reversal-Untersuchung übersehen hätte.

---

## Befund 1 — der Ausführungsversatz ist groß, aber bemerkenswert konstant

Gemessen an **134 echten Broker-Fills** (`bridge_state_{ttp,iqmarkets,ttp1}.json`,
09-17/09-18, alle `ctnl_reversal`):

| | Wert |
|---|---|
| Versatz Signal-**Label** → Live-Entry | **Median 28 Min.** (min 28, max 29) |
| Bester Preis-Treffer (ab Signalbar) | Open der Bar **T+30**, Median-Abweichung **1,28 Preispunkte** |
| zum Vergleich | T+15 → 3,44 Punkte, T+0 → 4,97 Punkte |

Die Streuung von einer Minute über 134 Fills ist das eigentlich
Bemerkenswerte: der Versatz ist **kein Zufall, sondern Taktung** — er lässt
sich also gezielt verkleinern, statt nur als Reibung hingenommen zu werden.

### Die Falle: zwei verschiedene Nullpunkte

Hier verrechnet man sich fast zwangsläufig (die Probe-Notiz warnt genau
davor, und ihr Autor ist dort selbst einmal um eine Bar danebengelegen):

- Die Bar mit **Label** 09:30 schließt erst 09:45.
- Der Backtest füllt zum `open` der Bar **09:45** (`open_[entry_i]`,
  `entry_i` = Signalbar + 1).
- Der reale Fill lag 09:58.

Der für Probe 2 relevante Versatz ist damit **~13 Min.**, nicht 28. Gegen die
*Signalbar* gemessen ist der beste Treffer T+30, gegen die *Entry-Bar*
gemessen — und so sind die Lag-Tabellen unten indiziert — ist es **Lag 1**.
Dieselben 13 Minuten, nur anderer Anker.

Beleg: `scripts/research_ctnl_execution_costs.py` (Modul-Docstring hält die
Zuordnung fest).

---

## Befund 2 — die drei Bridges sizen CTNL unterschiedlich

Probe 3 fragt nach dem Sizing-Nenner. Die Prüfung ergab, dass die Frage je
Bridge **verschieden** zu beantworten ist:

| Bridge | SL-Verankerung | Hebel-Gate | Folge |
|---|---|---|---|
| Funded-Portfolio | absolutes Signal-Niveau | `MAX_CONSUMED_R_FOR_ENTRY = 0.50` | Hebel bei 2,0x gedeckelt, strukturelles Niveau bleibt |
| FK Instant Funding | absolutes Signal-Niveau | `MAX_CONSUMED_R_FOR_ENTRY = 0.50` | wie Funded |
| **EK-Portfolio** | **am Live-Kurs neu verankert** | **keins — und das ist konsequent** | Aufblähung strukturell unmöglich, aber Signal-Niveau verworfen |

EKs CTNL-Pfad (`legs/ctnl_edge/executor.py::_send_entry`) rechnet:

```python
stop_price = entry_price - direction * sl_distance
```

Es übernimmt also nur die **Distanz** des Signals, nicht sein **Niveau**. Der
Nenner ist damit konstruktionsbedingt immer exakt `sl_distance` — ein
`consumed_r`-Gate wäre dort gegenstandslos. Dass es fehlt, ist kein
Versäumnis.

**Aber:** genau diese Variante hat EK für das CLS-Bein selbst vermessen und
verworfen. Aus dem Docstring von `EK-Portfolio-Bridge/run_once.py::_check_cls_practical()`:

| CLS auf EK | PF | Ø R | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|
| neu verankert | 1,42 | 0,25 | 0,65 | −5,57 % | 0,48 |
| absoluter SL | **1,85** | **0,42** | **1,02** | **−4,20 %** | **0,93** |

> Besser auf jeder Kennzahl außer dem maximalen Hebel (15,5x statt 11,0x) —
> und das über alle getesteten Kostenannahmen.

Begründet wurde das damit, dass „das strukturelle Invalidierungs-Niveau den
Edge trägt, nicht die bloße Distanz". Für CLS wurde daraus am 2026-09-11 eine
Umstellung. **Für CTNL läuft EK bis heute auf der Variante, die für CLS
gemessen unterlegen war.**

Ob das für CTNL genauso gilt, ist damit *nicht* gezeigt — CLS und CTNL sind
verschiedene Strategien. Es ist ein begründeter Verdacht mit einem
konkreten Gegenbeleg aus dem eigenen Repo, nicht mehr. Die Quantifizierung
steht noch aus.

---

## Befund 3 — die 8 bps sind nicht zu niedrig, sondern 4- bis 11-fach zu hoch

Probe 1 (p6_5), gemessen mit `scripts/measure_broker_spreads.py --symbols
XAUUSD --window 7-22`, 20 Handelstage (2026-08-24..09-18), Rohdaten in
`_data/broker_spreads_xauusd.json`:

| Broker | Spread | Slippage RT | Kommission | **= Round-Trip** | **bps** | n (Ein/Aus) |
|---|---|---|---|---|---|---|
| TTPMarkets | 48,0 | 34,0 | 3,0 | 85,0 | **1,95** | 50/17 |
| BeyondIQCapital (IQ) | 26,0 | 1,0 | 5,0 | 32,0 | **0,73** | 46/12 |
| Tickmill (EK) | 8,0 | 38,5 | 0,0 | 46,5 | **1,07** | 11/6 |
| BeyondIQCapital (FK) | 26,0 | 15,5 | 5,0 | 46,5 | **1,07** | 16/4 |

*Einheit Points (1 Point = 0,01 Kurspunkte), bps gegen Gold ≈ 4.360.*

> **Angenommen: 8,00 bps. Gemessen: 0,73–1,95 bps.**
> Der Backtest rechnet mit dem **4,1- bis 10,9-fachen** der echten Kosten.

**Das ist die umgekehrte Richtung zum CLS-Fall.** Dort waren die Kosten
unterschätzt und die Strategie brach bei echten Kosten zusammen. Hier ist der
Backtest *konservativ* — das CTNL-Ergebnis ist also besser, als die
veröffentlichten Zahlen zeigen, nicht schlechter. Eine gegriffene Zahl bleibt
trotzdem eine gegriffene Zahl: dass sie diesmal zugunsten der Vorsicht daneben
lag, war Glück, nicht Methode.

Nebenbefunde:

- **Tickmill hat den mit Abstand besten Spread** (8 Points gegen 26 bei
  BeyondIQ und 48 bei TTP) und **keine Kommission** — aber die höchste
  Exit-Slippage. Bei n=6 ist das keine belastbare Aussage, nur ein Hinweis.
- **Die Slippage-Stichproben sind durchweg klein** (n=4 bis n=17 auf der
  Ausstiegsseite) und stammen überwiegend aus dem Flut-Zeitfenster
  09-17/09-18 — also aus schnellen Stop-Outs in einer Rally. Das ist eher
  Worst Case als Normalfall.
- **TTPs Slippage (34 Points RT) ist der größte Einzelposten** und übersteigt
  Spread plus Kommission zusammen nicht, liegt aber in derselben
  Größenordnung. Genau dieser Posten stand im Backtest auf null.

---

## Befund 4 — bei echten Kosten sind beide Beine profitabel, und der Lag ist nicht das Problem

Proben 2/3, `scripts/research_ctnl_execution_costs.py`, 2023-01-01..2026-09-18,
mit nachgebildetem 0,50R-R-Detektor (**so verhält sich die Bridge wirklich**).
Lag gemessen ab der Entry-Bar — **Lag 1 ist der reale Betriebspunkt** (siehe
Befund 1).

**`ctnl_reversal`** (433 Trades, M15, 1 Lag-Bar = 15 Min.):

| Lag | Min. | TTP (1,95 bps) Ø R / PF | IQ (0,73 bps) Ø R / PF |
|---|---|---|---|
| 0 | 0 | +0,194 / 1,23 | +0,209 / 1,25 |
| **1** | **15** | **+0,266 / 1,31** | **+0,299 / 1,35** |
| 2 | 30 | +0,256 / 1,31 | +0,276 / 1,34 |
| 3 | 45 | +0,205 / 1,25 | +0,238 / 1,30 |
| 4 | 60 | +0,166 / 1,21 | +0,191 / 1,24 |

**`ctnl_continuation`** (173 Trades, M5, 1 Lag-Bar = 5 Min.):

| Lag | Min. | TTP (1,95 bps) Ø R / PF | IQ (0,73 bps) Ø R / PF |
|---|---|---|---|
| 0 | 0 | +0,257 / 1,27 | +0,374 / 1,40 |
| **1** | **5** | **+0,194 / 1,22** | **+0,328 / 1,40** |
| 2 | 10 | +0,126 / 1,15 | +0,235 / 1,29 |
| 3 | 15 | +0,171 / 1,22 | +0,273 / 1,36 |
| 4 | 20 | +0,122 / 1,16 | +0,215 / 1,29 |

Beide Beine bleiben über den gesamten geprüften Lag-Bereich positiv. Die
Lag-Kurve ist in **keinem** der vier Läufe monoton — der Lag-Effekt ist in
diesem Bereich also Rauschen, keine belastbare Größe. Dass Lag 1 jeweils
besser aussieht als Lag 0, ist damit **kein** Argument für einen absichtlich
verzögerten Einstieg, sondern nur ein weiterer Beleg dafür, dass hier nichts
Systematisches liegt.

**Das ist der zentrale Unterschied zu CLS.** Dort kostete der Versatz mehr
Edge als sämtliche Broker-Kosten zusammen. Hier ist er innerhalb des real
auftretenden Bereichs nicht vom Rauschen zu trennen — weil CTNLs Stops
(Median 24x bzw. 7x Round-Trip-Kosten) um Größenordnungen weiter sind als
CLS' enge Stops.

---

## Befund 5 — der R-Detektor ist tragend, nicht kosmetisch

Der wichtigste Einzelfund. Dieselbe Rechnung **ohne** das 0,50R-Gate,
`ctnl_continuation` bei TTP-Kosten:

| Lag | mit Gate Ø R / PF | **ohne Gate** Ø R / PF | Hebel max ohne Gate |
|---|---|---|---|
| 0 | +0,257 / 1,27 | +0,257 / 1,27 | 1,00 |
| **1** | **+0,194 / 1,22** | **−0,008 / 0,99** | **16,0x** |
| 2 | +0,126 / 1,15 | −0,466 / 0,65 | 180,8x |
| 3 | +0,171 / 1,22 | −0,873 / 0,51 | **380,5x** |
| 4 | +0,122 / 1,16 | −0,378 / 0,67 | 126,7x |

**Das Gate ist der Unterschied zwischen einem profitablen und einem
verlustbringenden Bein.** Ohne es kippt `ctnl_continuation` schon am realen
Betriebspunkt auf PF 0,99, und einzelne Trades erreichen Hebel jenseits von
100x — der Kurs ist dann bis fast an den Stop gelaufen, der Sizing-Nenner geht
gegen null.

Die Identität aus der Probe-Notiz (`Aufblähung = 1/(1−X)`, 0,50R → 2,0x)
bestätigt sich dabei exakt: der gemessene **Hebel max liegt mit Gate bei
1,94–2,00** in allen Läufen. Ein separater Hebel-Deckel ist überflüssig.

Damit bekommt [Befund 2](#befund-2--die-drei-bridges-sizen-ctnl-unterschiedlich)
mehr Gewicht — aber nicht in die erwartete Richtung: EK hat kein
`consumed_r`-Gate, ist aber durch die Neuverankerung des Stops am Live-Kurs
**strukturell gegen genau diese Pathologie immun** (der Nenner ist dort immer
exakt `sl_distance`). EK ist also nicht gefährdet. Offen bleibt allein, ob die
Neuverankerung Edge kostet — siehe unten.

---

## Befund 6 — die engen Stops waren ein Artefakt der falschen Kostenzahl

Probe 4, `ctnl_continuation`, je nach angesetzten Kosten:

| Kostenansatz | Stopdistanz Median | Anteil < 3x Kosten | Ø R eng | Ø R weit |
|---|---|---|---|---|
| angenommen 8,00 bps | 2,1x | **75,7 %** (131) | −0,312 | +0,321 |
| gemessen 1,95 bps (TTP) | 7,0x | 5,8 % (10) | −0,109 | +0,280 |
| gemessen 0,73 bps (IQ) | 17,8x | **0,0 %** (0) | — | +0,374 |

`ctnl_reversal` ist in jedem Szenario unauffällig (Median 6,3x / 24,2x /
63,8x, Anteil eng 1,6 % / 0,0 % / 0,0 %).

Bei den angenommenen 8 bps sah `ctnl_continuation` exakt wie der CLS-Fall aus:
drei Viertel aller Trades mit zu engem Stop, und der gesamte Verlust sitzt
dort. **Das war eine Folge der um Faktor 4–11 zu hohen Kostenzahl, nicht der
Strategie.** Bei echten Kosten verschwindet das Muster.

**Ein absoluter Stop-Boden ist damit nicht fällig** — anders als bei CLS. Die
Warnung der Probe-Notiz vor relativen ATR-Böden bleibt richtig, greift hier
aber nicht, weil die Stops ohnehin ein Vielfaches der Kosten betragen.

---

## Befund 9 — Optimierung: vier von fünf Schrauben bringen nichts, eine schon

`scripts/research_ctnl_optimization.py`, 2016-01..2026-09, gemessene Kosten
(2,01 bps), Lag 1, R-Detektor. Rohdaten `_data/ctnl_optimization.json`.

**Methode: Anker-Walk-Forward.** Für jedes Jahr Y wird der Parameter auf allen
Trades **vor** Y gewählt und auf Y ausgewertet. Gemessen wird damit nicht „was
war rückblickend am besten", sondern „hätte die Auswahlprozedur geholfen".
Nur wenn sie die gesperrte Baseline out-of-sample schlägt, ist der Parameter
ein Hebel.

### 9a — TP: die 5R stehen auf einem Plateau, die Auswahl verliert

`ctnl_reversal`, Parameterfläche über die Gesamthistorie:

| TP | 2R | 3R | 4R | **5R** | 6R | 7R | 8R | 10R |
|---|---|---|---|---|---|---|---|---|
| Ø R | −0,064 | −0,031 | +0,047 | **+0,109** | +0,066 | +0,106 | +0,114 | +0,116 |
| PF | 0,92 | 0,96 | 1,05 | **1,12** | 1,07 | 1,12 | 1,12 | 1,13 |

Unter 4R bricht es weg; ab 5R ist die Fläche **flach** (+0,106 bis +0,116 über
5R–10R). Das ist die gute Nachricht: die gesperrten 5R sitzen nicht auf einem
Grat, sondern auf einem Plateau — genau die Form, die man haben will.

Walk-Forward: die Prozedur wählt je nach Jahr 5,0 / 8,0 / 10,0 und liefert
OOS **+100,7 ΣR gegen +143,4** der Baseline, besser in **1 von 8** Jahren.
**TP ist kein Hebel — 5R bleibt.**

> **Korrektur zu Befund 7c.** Meine MFE-Hypothese („ein niedrigeres Ziel
> sammelt die Hälfte ein, die zwischen 3R und 5R zurückfällt") ist
> **widerlegt**. Sie übersah, dass ein niedrigeres Ziel auch die Trades kappt,
> die tatsächlich 5R erreichen — und deren +5R tragen das Ergebnis. Die
> Fläche bei 2R/3R ist negativ. Genau dafür ist der Walk-Forward da.
> Ebenso korrigiert: ich hatte geschrieben, höhere Ziele seien wegen der
> MFE-Zensur nicht beurteilbar. Das gilt nur für die **Diagnose** — die
> **Simulation** lässt den Trade weiterlaufen und rechnet sie problemlos.

### 9b — Signal-Parameter: das Lehrbuchbeispiel für Überfittung

`ctnl_reversal`, Walk-Forward über sechs Varianten:

| Jahr | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | **Σ** |
|---|---|---|---|---|---|---|---|---|---|
| gewählt | — alle Jahre `ohne_ema_reject` — | | | | | | | | |
| Diff zur Baseline | +147 | +47 | +41 | −65 | −86 | +0 | −78 | −67 | **−60,6** |

`ohne_ema_reject` ist **in jedem einzelnen Jahr IS-Sieger** und verliert
out-of-sample: Ø R +0,053 gegen +0,165, PF 1,06 gegen 1,19. Die frühen Jahre
tragen den IS-Vorsprung, ab 2022 dreht es. Exakt das OU-Muster.
**Die gesperrten Signal-Parameter bleiben.**

### 9c — Der Regime-Filter ist der einzige echte Hebel

`ctnl_reversal`, Effizienz-Filter (nur Trades unterhalb der IS-Quantilgrenze,
Schwelle als absoluter Wert ins OOS übernommen):

| | OOS Σ R | Ø R | PF | Jahre besser |
|---|---|---|---|---|
| Baseline | +143,4 | +0,165 | 1,19 | — |
| **Filter q50** | **+170,8** | **+0,398** | **1,48** | 5 von 8 |

Der Walk-Forward wählt in **allen acht Jahren** dieselbe Schwelle (q50) — ein
stabiler Pick, kein Herumspringen.

**Monte Carlo** (`ou_paper_backtest/monte_carlo.py`, Block 20, 2.000 Pfade,
0,15 %/Trade = FK-Reversal-Split):

| | Median MaxDD | P5 MaxDD | P(MaxDD>6 %) | Median Return | Median Sharpe |
|---|---|---|---|---|---|
| Baseline | −15,63 % | −28,07 % | 99,9 % | +18,8 % | 0,25 |
| **Filter q50** | **−8,37 %** | **−15,15 %** | **86,4 %** | **+32,2 %** | **0,56** |

**Der Drawdown halbiert sich und die Rendite steigt** — kein Tausch, beide
Achsen verbessern sich. Das ist der einzige Befund dieser Untersuchung, der
eine Änderung rechtfertigt.

**Was dagegen spricht, es sofort scharf zu schalten:** der Filter verliert in
den Jahren 2022, 2024 und 2025 (je ca. −30 ΣR) und gewinnt in 2019–2021 und
2023 — er glättet also, indem er in guten Trendphasen aussetzt. Wer nur die
letzten zwei Jahre betrachtet, sieht einen Verschlechterer.

### 9d — Risiko: die dokumentierte Kalibrierung hängt an einem einzigen Jahr

Die Projektnotiz nennt für FK (0,50 %/0,15 %) einen Bootstrap-Median-MaxDD von
**−3,5 %** und **P(MaxDD>6 %) = 7,8 %**. Meine Rechnung für das
Reversal-Bein **allein** bei 0,15 % über die **volle** Historie:
Median MaxDD **−15,63 %**, P(MaxDD>6 %) **99,9 %**.

Die Zahlen sind **nicht direkt vergleichbar** — die alte stammt aus dem
OOS-Fenster 2025-08/2026-08 (ein einziges, gutes Jahr) und galt dem
kombinierten Portfolio, meine läuft über zehn Jahre inklusive der schlechten
und enthält Kosten, Lag und R-Detektor. Genau das ist der Punkt: **die
dokumentierte Risikokalibrierung ruht auf einem Jahr.** Bevor an den
Risikogrößen gedreht wird, gehört sie über die volle Historie neu gezogen.

### 9e — `ctnl_continuation` ist über die Historie nicht zu retten

Jede geprüfte Variante ist negativ:

| Variante | VWAP (Baseline) | TP 2R | TP 5R | TP 10R | htf_valid_12 |
|---|---|---|---|---|---|
| Ø R | −0,060 | −0,136 | −0,269 | −0,185 | −0,022 |
| PF | 0,94 | 0,84 | 0,76 | 0,84 | 0,98 |

TP-Walk-Forward: **0 von 8** Jahren besser. Signal-Walk-Forward: Ø R +0,024
gegen −0,002 — rechnerisch besser, aber beides ist null. Regime-Filter:
+0,4 gegen −0,5 ΣR, ebenfalls null.

Monte Carlo bei 0,50 %/Trade: **Median Return −16,4 %, Median Sharpe −0,20,
Median MaxDD −31,68 %.**

**Hier ist keine Parameterfrage offen, sondern eine Existenzfrage.** Über 436
Trades und zehn Jahre gibt es keinen Edge. Das einzige gute Jahr ist 2026 mit
20 Trades.

---

## Befund 10 — auf EK kehrt das Mindestlot die Risiko-Hierarchie um

Nutzerhinweis 2026-09-23 („zu viel Risiko im Markt"). Nachgerechnet, **read-only**.

### Die Formel wird korrekt angewendet — die Memory war veraltet

`core/sizing.py:67` wendet `CAPITAL_WEIGHT` seit 2026-09-10 an. Der alte Fund
„Kapitalverdünnung definiert, aber nie benutzt" ist **behoben**. Das ist nicht
die Ursache.

### Die Ursache ist die Mindestlot-Anhebung

EK-Equity: **2.939 EUR**. Beabsichtigtes Risiko je Trade = Equity × 1/8 ×
`LEG_RISK_PCT`. Auf XAUUSD riskiert das kleinste handelbare Lot (0,01) bei der
aktuellen Stopdistanz von 28,90 Punkten aber **25,38 EUR**:

| Bein | Ziel-Risiko | % Equity | Mindestlot riskiert | **Faktor** |
|---|---|---|---|---|
| `gold_asb` | 103,47 EUR | 3,52 % | 25,38 EUR | — (kein Bump) |
| `gold_silver` | 103,47 EUR | 3,52 % | 25,38 EUR | — |
| `trend_pullback` | 64,67 EUR | 2,20 % | 25,38 EUR | — |
| `ctnl_continuation` | **1,84 EUR** | 0,062 % | 25,38 EUR | **14x** |
| `ctnl_reversal` | **0,55 EUR** | 0,019 % | 25,38 EUR | **46x** |

**Die beiden CTNL-Beine sind die einzigen Gold-Beine, die angehoben werden —
und sie landen dadurch bei einem Viertel dessen, was `gold_asb` als
*größtes* Bein beabsichtigt, obwohl sie auf 1/56 bzw. 1/188 davon kalibriert
wurden.** Die Hierarchie der Studie ist damit auf diesem Konto aufgehoben.

### Was real offen ist (Stand 2026-09-23)

| Bein | n | offenes Risiko | % Equity | Nominal |
|---|---|---|---|---|
| `ou_modell` | 10 | 118 EUR | 4,00 % | 2.202 EUR |
| **`ctnl_reversal`** | **3** | **76 EUR** | **2,59 %** | **12.860 EUR** |
| **Gesamt** | 13 | 194 EUR | 6,59 % | 15.062 EUR |

`ctnl_reversal` hält mit **drei** Positionen (`REV_MAX_CONCURRENT = 3`)
**2,59 %** der Equity im Risiko — beabsichtigt waren 3 × 0,019 % = **0,06 %**.
Und **12.860 EUR Nominal auf einem 2.939-EUR-Konto**, also **4,4-facher
Hebel allein aus dem Bein, das das konservativste sein sollte.**
Der Gesamthebel liegt bei 5,1x.

### Das ist kein Bug — aber die Folge war so vermutlich nicht gemeint

Die Anhebung ist ein dokumentierter Nutzerentscheid (`core/sizing.py`,
2026-09-10, Muster aus FK): ohne sie würden die kleinen Beine auf einem
~3-k-Konto schlicht verstummen. Es gibt einen harten Deckel
(`MAX_SINGLE_TRADE_RISK_PCT = 5 %` = 147 EUR) und eine Warnung im Log.

Der Kommentar dort nennt das Ziel-Risiko von `ctnl_continuation` mit „~2 EUR" —
er kannte also die Zielgröße. Was dort **nicht** steht, ist die Gegenrechnung:
dass die Anhebung daraus 25 EUR macht und das Bein damit an die Spitze der
Risikoliste hebt. Der 5-%-Deckel greift erst bei 147 EUR und hat in diesem
Fall nie ausgelöst.

**Zusätzlich:** `MAX_TOTAL_RISK_PCT = 0,30` erlaubt **30 % der Equity** als
offenes Gesamtrisiko. Aktuell sind 6,59 % ausgeschöpft (22 % des Deckels) —
der Deckel ist also weit weg und schützt hier nicht.

---

## Befund 11 — der Edge von `ctnl_reversal` liegt vollständig auf der Long-Seite

`scripts/research_ctnl_entry_origin.py`, 2016-01..2026-09, gesperrte Config,
gemessene Kosten, Lag 1, R-Detektor. Rohdaten `_data/ctnl_entry_origin.json`.

Diese Frage war in der bisherigen Untersuchung **nicht gestellt**. Der
Signal-Sweep (Befund 9b) hat an den Kaskaden-Parametern gedreht, ohne zu
prüfen, ob die Kaskade auf beiden Seiten überhaupt funktioniert.

| Richtung | Trades | Ø R | Σ R | PF |
|---|---|---|---|---|
| **long** | 662 | **+0,391** | **+258,9** | **1,46** |
| **short** | 591 | **−0,207** | **−122,3** | **0,79** |

**Die Short-Seite vernichtet knapp die Hälfte dessen, was die Long-Seite
erwirtschaftet.** Aus +258,9 ΣR werden netto +136,7.

### Walk-Forward und Monte Carlo bestätigen es

Anker-Walk-Forward über vier Varianten — die Prozedur wählt in 5 von 8 Jahren
`long + Regime`, in 2019 und 2026 `nur long`, und **nie** die Baseline oder
`nur short`:

| | OOS Σ R | Ø R | PF | Jahre besser |
|---|---|---|---|---|
| Baseline | +143,4 | +0,165 | 1,19 | — |
| **Richtungs-Prozedur** | **+171,8** | **+0,542** | **1,68** | 5 von 8 |

Monte Carlo (0,15 %/Trade, Block 20, 2.000 Pfade):

| Variante | Median MaxDD | P5 MaxDD | P(MaxDD>6 %) | Median Return | Sharpe |
|---|---|---|---|---|---|
| beide (Baseline) | −15,63 % | −28,07 % | 99,9 % | +18,8 % | 0,25 |
| nur long | −8,12 % | −14,26 % | 84,1 % | **+43,6 %** | 0,71 |
| nur short | −22,86 % | −37,43 % | 99,9 % | −17,7 % | −0,44 |
| **long + Regime** | **−4,84 %** | **−8,47 %** | **23,3 %** | +38,6 % | **0,83** |

`long + Regime` senkt den Median-Drawdown von −15,6 % auf **−4,84 %** und die
Wahrscheinlichkeit, 6 % zu reißen, von 99,9 % auf **23,3 %** — bei mehr als
verdoppelter Rendite. Das ist der stärkste Einzeleffekt der gesamten
Untersuchung.

### Der Einwand, der alles relativiert

**Gold ist über den gesamten Stichprobenzeitraum gestiegen** (2016 ≈ 1.150,
2026 ≈ 4.400). „Long funktioniert, Short nicht" auf einem einseitig steigenden
Markt ist nahe an einer Tautologie. Die Stichprobe enthält **keine echte
Gold-Baisse**, an der sich prüfen ließe, ob die Asymmetrie ein Struktur- oder
ein Regime-Effekt ist.

Ein Hinweis darauf, dass sie **nicht** strukturell ist, steckt in der
Walk-Forward-Tabelle selbst: **2022** — die Zinserhöhungsphase, in der Gold
seitwärts bis abwärts lief — ist eines der Jahre, in denen die
richtungsbeschränkte Variante **schlechter** ist als die Baseline (−19,2 ΣR).
Die Shorts haben dort also gearbeitet. Dasselbe Muster in 2024 (−24,9) und
2025 (−35,2), beides starke Aufwärtsjahre — dort kostet die Beschränkung
Rendite, weil der Regime-Filter zusätzlich aussetzt.

**Was daraus folgt:** Long-only ist keine Erkenntnis über die Strategie,
sondern eine **Wette darauf, dass Gold weiter steigt**. Das kann eine
vernünftige Wette sein — aber sie muss als solche getroffen werden, nicht als
vermeintliche Edge-Verbesserung. Wer sie eingeht, braucht dieselbe
Ausstiegsregel wie für jede Richtungswette.

---

## Befund 12 — Struktur oder Regime? Die Daten zeigen auf **Regime**

`scripts/research_ctnl_direction_regime.py`. Der Test, den Befund 11 offen
gelassen hatte: verdient die Short-Seite in Jahren, in denen Gold **fällt**?

`ctnl_reversal`, Short-Ergebnis gegen die Gold-Jahresrendite:

| Jahr | Gold | short Σ R | | Jahr | Gold | short Σ R |
|---|---|---|---|---|---|---|
| 2017 | +13,2 % | −54,7 | | **2021** | **−3,6 %** | **+18,2** |
| **2018** | **−1,6 %** | **−19,1** | | **2022** | **−0,3 %** | **+7,1** |
| 2019 | +18,3 % | −17,4 | | 2023 | +13,1 % | −27,7 |
| 2020 | +25,1 % | −43,4 | | 2024 | +27,2 % | +0,1 |
| | | | | 2025 | +64,6 % | −11,5 |
| | | | | 2026 | +1,0 % | −2,6 |

| | Jahre | short Ø R | short Σ R |
|---|---|---|---|
| Gold **fällt** | 3 | **+0,116** | **+6,2** |
| Gold **steigt** | 7 | **−0,390** | **−157,1** |

Korrelation Gold-Jahresrendite ↔ short Ø R: **−0,38**.

**Die Short-Seite ist in fallenden Jahren etwa neutral bis leicht positiv und
verliert praktisch den gesamten Schaden in steigenden Jahren.** Das ist ein
**Regime-Effekt**, keine strukturelle Schwäche der Kaskade auf der
Short-Seite.

**Was das für E6 heißt:** Long-only ist bestätigt als **Trendwette**. Die
Kaskade ist auf der Short-Seite nicht kaputt — sie wird vom
Gold-Aufwärtstrend überfahren. Bei einer Trendwende müsste die Beschränkung
zurückgedreht werden, sonst verliert man genau den Teil, der dann arbeitet.

> **Grenzen dieser Aussage, deutlich:** nur **3** fallende Jahre im Sample,
> und alle drei waren mild (−1,6 %, −3,6 %, −0,3 %) — eine echte Gold-Baisse
> ist nicht enthalten. Eines der drei (2018) war für die Shorts trotzdem
> negativ (−19,1). Eine Korrelation von −0,38 über n=10 ist ein Hinweis,
> kein Beweis. Die Richtung der Datenlage ist klar, ihre Belastbarkeit nicht.

---

## Befund 13 — bei `ctnl_continuation` rettet keine Richtung etwas

Dieselbe Aufteilung für das Continuation-Bein:

| Variante | Trades | Ø R | Σ R | PF |
|---|---|---|---|---|
| beide (Baseline) | 436 | −0,060 | −26,2 | 0,94 |
| nur long | 245 | −0,076 | −18,6 | 0,92 |
| nur short | 191 | −0,040 | −7,6 | 0,96 |
| long + Regime | 115 | −0,130 | −14,9 | 0,86 |

**Alles negativ.** Anders als beim Reversal-Bein, wo die Long-Seite alles
trägt, ist hier keine Seite profitabel. Der Walk-Forward macht es sogar
schlechter: OOS **−24,7** gegen **−0,5** der Baseline, besser in **1 von 8**
Jahren.

Monte Carlo (0,50 %/Trade): jede Variante hat negative Median-Rendite
(−5,4 % bis −16,4 %), negativen Sharpe und **P(MaxDD>6 %) ≈ 100 %**.

Auch der Struktur-gegen-Regime-Test läuft hier ins Leere: Korrelation −0,04,
und die Vorzeichen sind gegenüber dem Reversal-Bein invertiert (fallende
Jahre −0,523, steigende +0,582) — bei 9 bis 27 Trades pro Jahr ist das
Rauschen, kein Signal.

**Das ist die vierte unabhängige Bestätigung für E3** (nach Jahresbilanz,
TP-/Signal-Sweep und Eimer-Analyse): dieses Bein hat keinen Edge.

---

## Was daraus folgt (Entscheidung steht bei dir)

Nach Kostenvalidierung, Diagnose und Optimierung stehen **vier** Entscheidungen
an. Sie sind unabhängig voneinander — du kannst einzeln zustimmen.

### E1 — Kostenzahl korrigieren *(Empfehlung: ja)*

`spread_bps` von 8,0 auf die gemessenen Werte, broker-getrennt
(TTP 2,01 / BeyondIQ 0,73 / Tickmill 0,53). *Wirkung: Backtest und Realität
stimmen überein, das Bein wird bei Portfolio-Gewichtungen nicht mehr
benachteiligt. Risiko: gering.* **Haken:** die Phase-6-Referenz
`CTNL_KILL_SWITCH_DD_THRESHOLD = −0,066` ist mit 8 bps gezogen und muss
mit E4 zusammen neu gerechnet werden.

### E2 — Regime-Filter einführen *(Empfehlung: ja, aber als Paper-Lauf zuerst)*

Effizienz-Filter q50 auf `ctnl_reversal`. *Wirkung laut Monte Carlo: Median
MaxDD −15,6 % → −8,4 %, Median Return +18,8 % → +32,2 %, Sharpe 0,25 → 0,56.
Beide Achsen besser.* **Haken:** halbiert die Trade-Zahl und setzt in
Trendphasen aus — 2022, 2024 und 2025 wäre er schlechter gewesen. Wer nur die
letzten zwei Jahre anschaut, sieht einen Verschlechterer. Deshalb der
Vorschlag, ihn erst mitlaufen zu lassen (Signal protokollieren, nicht
handeln), bevor er scharf geschaltet wird.

### E3 — `ctnl_continuation` stilllegen *(Empfehlung: ja)*

Über 436 Trades und zehn Jahre: PF 0,94, 3 von 11 Jahren positiv, Monte Carlo
bei 0,50 %/Trade Median Return **−16,4 %**. Keine der geprüften Varianten
(TP, Signal-Parameter, Regime-Filter) dreht das. *Das einzige Gegenargument
ist 2026 (+1,48 Ø R) — auf 20 Trades.* **Live-Trigger bleibt bei dir; ich
bereite nur vor.**

### E4 — Risikokalibrierung über die volle Historie neu ziehen *(Empfehlung: ja)*

Die dokumentierten FK-Zahlen (Median MaxDD −3,5 %, P(MaxDD>6 %) = 7,8 %)
stammen aus **einem** OOS-Jahr. Über zehn Jahre liegt allein das
Reversal-Bein bei −15,6 % Median und P(>6 %) = 99,9 %. Solange das nicht neu
gezogen ist, ist jede Aussage über Challenge-Verträglichkeit unbelegt.
**Reihenfolge beachten** (Repo-Vorgabe): erst E1/E2/E3, dann E4 — die
Risikozahl hängt von allen dreien ab.

### E5 — EK: Mindestlot-Anhebung für CTNL entscheiden *(dringendste Frage)*

Auf EK riskiert `ctnl_reversal` real **0,86 %/Trade statt 0,019 %** (Faktor 46,
siehe Befund 10) und hält mit drei Positionen **2,59 %** der Equity plus
**4,4-fachen Nominal-Hebel** — aus dem Bein, das das konservativste sein
sollte. Vier Wege:

| | Vorgehen | Wirkung | Haken |
|---|---|---|---|
| **a** | Nichts ändern | — | Die Studien-Allokation gilt auf EK faktisch nicht; das kleinste Bein ist eines der größten |
| **b** | Anhebung für CTNL abschalten | Bein verstummt auf EK, bis das Konto groß genug ist | Kein CTNL auf EK — arguably ehrlich, denn 0,019 % sind dort nicht darstellbar |
| **c** | `REV_MAX_CONCURRENT` auf EK von 3 auf 1 | Deckelt das Bein bei 0,86 % statt 2,59 % | Ändert die Strategie-Logik, die mit 3 validiert wurde |
| **d** | CTNL-`LEG_RISK_PCT` anheben, bis das Ziel ≥ Mindestlot liegt | Formel und Realität stimmen wieder überein | Bewusste Abkehr von der Studien-Gewichtung — muss neu MC-validiert werden |

**Meine Empfehlung: b oder c**, und zwar bevor E1–E4 angefasst werden. Beide
wirken sofort und ohne Neukalibrierung. **d** ist die sauberste Lösung, setzt
aber E4 (Risikokalibrierung über die volle Historie) voraus.

**Hinweis zur Tragweite:** dasselbe Muster betrifft potenziell jedes Bein, das
auf diesem Konto angehoben wird — geprüft habe ich nur die Gold-Beine, weil
dort eine reale Stopdistanz vorlag. `cls_practical` (19,40 EUR Ziel),
`ou_modell` (10,77) und die drei ORB-Beine (10,58) liegen ebenfalls niedrig
genug, dass eine Anhebung plausibel ist. **Das habe ich nicht nachgerechnet.**

### E6 — `ctnl_reversal` auf Long beschränken? *(größter Effekt, größter Vorbehalt)*

Monte Carlo: Median MaxDD **−15,6 % → −4,84 %**, P(MaxDD>6 %)
**99,9 % → 23,3 %**, Sharpe **0,25 → 0,83** (Variante `long + Regime`).
Walk-Forward bestätigt in 5 von 8 Jahren.

**Aber** (Befund 11): die Stichprobe enthält keine Gold-Baisse. Long-only ist
eine Wette auf den fortgesetzten Aufwärtstrend, keine Struktur-Erkenntnis —
2022 hat die Short-Seite nachweislich gearbeitet.

| | Vorgehen | |
|---|---|---|
| **a** | Nichts ändern | Short bleibt, kostet im Schnitt −122 ΣR über 10 Jahre |
| **b** | Long-only + Regime-Filter scharf | Größter Effekt, volle Trendwette |
| **c** | Long-only, Regime-Filter nur mitlaufend | Hälfte des Effekts, weniger Modellrisiko |
| **d** | Erst mitlaufen lassen (beides protokollieren, nichts ändern) | Kostet Zeit, kostet nichts sonst |

**Befund 12 hat den offenen Punkt geklärt:** die Short-Seite ist ein
**Regime**-Effekt, keine strukturelle Schwäche — in fallenden Jahren ist sie
neutral bis positiv (+0,116 Ø R), in steigenden verliert sie alles
(−0,390). Long-only ist damit **definitiv eine Trendwette** und muss bei
einer Gold-Trendwende zurückgedreht werden.

**Entschieden (2026-09-23): d — mitlaufen lassen.** Der Effekt ist groß genug, dass ein paar
Wochen Mitschrift ihn nicht zerstören — und der Bull-Market-Vorbehalt ist
groß genug, dass ich ihn nicht auf Basis dieser Stichprobe scharf schalten
würde.

**Erledigt:** der Struktur-gegen-Regime-Test ist gerechnet, siehe Befund 12.

### Was NICHT geändert werden sollte

| Schraube | Warum sie bleibt |
|---|---|
| `take_profit_r = 5.0` | flaches Plateau 5R–10R, Auswahl verliert OOS (1/8 Jahre) |
| `stop_atr_mult = 3.0` | ein 0,5R-Stop hätte 49,5 % der Gewinner gekillt |
| `REV_KWARGS` | `ohne_ema_reject` ist IS-Sieger in 8/8 Jahren und verliert OOS |
| Ausführungstakt | real verkürzbar, aber P&L-Gewinn nicht belegt (Befund 8) |

## Noch offen

- **Kostet EKs Neuverankerung Edge?** Nicht quantifiziert, und bewusst nicht
  geschätzt. Die Replay-Methode oben rechnet nur die **Einstiegsseite** neu —
  sie darf das, weil Stop und Ziel am Signal-Niveau hängen. Bei EK wandert das
  Stop-Niveau mit dem Einstieg mit, also verschiebt sich auch die
  Ausstiegsseite. Das lässt sich mit diesem Skript nicht abbilden; es braucht
  einen eigenen Engine-Lauf mit am Einstieg verankertem Stop.
- **Phase-6-Referenz neu ziehen**, falls B oder C kommt (siehe oben).

---

## Verifikation (was geprüft wurde, damit die Zahlen tragen)

1. **Regressionstest der Messskript-Änderung.** `measure_broker_spreads.py`
   rechnete die Kommission mit `usd_per_pip_per_lot = 10.0` — auf EURUSD
   hartkodiert und damit für XAUUSD um Faktor 10 falsch. Ersetzt durch
   `info.trade_contract_size * pip`. Gegenprobe mit `--symbols EURUSD`:
   TTP $4,00/Lot = 0,40 Pips, IQ $5,00/Lot = 0,50 Pips — **identisch** zu
   [[broker-kostenmodell-eurusd]]. Die Änderung ist damit rückwärtskompatibel.
2. **FK Instant Funding fehlte als Messziel** und ist ergänzt — es fährt
   beide CTNL-Beine mit echtem Geld und wäre sonst ausgelassen worden.
3. **Config-Divergenz-Schutz.** `research_ctnl_execution_costs.py` dupliziert
   die Engine-Configs aus `_scan_ctnl()` (die Funktion lässt sich keine eigene
   Historie übergeben). `_assert_live_config_match()` hält sie bei jedem Start
   gegen `gold_smc_htf_ltf/live_signal.py` und bricht bei Abweichung ab —
   lieber ein harter Stopp als eine Auswertung, die eine andere Strategie
   beschreibt als die gehandelte.
4. **Alle Broker-Zugriffe read-only** (`copy_ticks_range`, `history_deals_get`,
   `positions_get`). Kein `order_send` im gesamten Projekt.

### Achtung: Datenlage-Fußnoten

- Die 134 Fills aus Befund 1 stammen **alle aus dem Flut-Zeitfenster
  09-17/09-18**, also aus einer einzigen zweitägigen Gold-Rally. Für die
  *Taktung* (28 Min.) ist das unkritisch — sie ist eine Eigenschaft des
  Scan-Zyklus, nicht des Marktes. Für alles, was von der Kursentwicklung
  abhängt, ist es eine schmale Stichprobe.
- Das Messfenster für Probe 1 (07:00–22:00 Berlin) ist aus den realen
  CTNL-Entry-Zeiten abgeleitet, nicht gegriffen: die Signale verteilen sich
  über diese 15 Stunden annähernd gleichmäßig. Ein enges Fenster wäre hier
  falsch gewesen — die Probe-Notiz warnt vor 24-h-Messungen wegen
  Asien-Session und Rollover, beides liegt außerhalb dieses Fensters.
