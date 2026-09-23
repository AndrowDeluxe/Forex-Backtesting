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

## Was daraus folgt (Entscheidung steht bei dir)

Zur Einordnung: **kein Handlungsdruck.** Beide Beine sind bei echten Kosten
und am realen Betriebspunkt profitabel. Es geht um Verbesserung, nicht um
Schadensbegrenzung.

**A — Nichts ändern.** Die Beine sind profitabel, die Schutzmechanismen
greifen nachweislich. Die 8 bps bleiben als bewusst konservative Reserve
stehen. *Kosten: der Backtest weist CTNL dauerhaft schlechter aus, als es ist
— was bei künftigen Portfolio-Gewichtungen gegen das Bein arbeitet.*

**B — Kostenzahl korrigieren, sonst nichts** *(meine Empfehlung)*.
`spread_bps` in `_scan_ctnl()` von 8,0 auf einen gemessenen Wert setzen,
broker-getrennt wie bei CLS (TTP 1,95 / BeyondIQ 0,73 / Tickmill 1,07).
*Nutzen: Backtest und Realität stimmen wieder überein, Portfolio-Gewichtung
wird fair. Risiko: gering — die Änderung macht das Modell konservativer in
der Aussage, nicht in der Ausführung.* **Aber:** die Phase-6-Referenzwerte
(`CTNL_KILL_SWITCH_DD_THRESHOLD = −0,066`) sind mit den alten Kosten gezogen
und müssten neu gerechnet werden, sonst passt der Kill-Switch nicht mehr zur
Kostenannahme.

**C — B plus EK-Angleichung.** Zusätzlich EKs CTNL auf das absolute
Signal-SL-Niveau + R-Detektor umstellen, wie es EK für CLS am 2026-09-11
bereits getan hat. *Nutzen: potenziell derselbe Sprung wie dort (PF 1,42 →
1,85). Risiko: für CTNL **nicht gemessen** — siehe offener Punkt unten. Ohne
diese Messung wäre es eine Übertragung per Analogie, und genau das ist die
Sorte Annahme, die dieses Projekt gerade widerlegt hat.*

---

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
