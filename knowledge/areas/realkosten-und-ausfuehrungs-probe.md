# Area: Realkosten- und Ausführungs-Probe (Pflichtteil von Phase 6)

Laufende Verantwortlichkeit ohne Enddatum: **jede Strategie, die live gehen
soll, durchläuft zusätzlich zu [[backtest-standard-process]] Phase 6 diese
vier Proben.** Als Checklistenpunkte `p6_5`–`p6_8` in
`app_pages/education_gold_intraday.py` verankert (die Quelle der Wahrheit),
diese Notiz ist die Methoden-Referenz dazu.

Angelegt 2026-09-10 nach dem `cls_practical`-Vorfall vom 2026-09-09 (siehe
[[cls-practical-kostenvalidierung]]). **Jede der vier Proben hat dort einen
realen Fehler aufgedeckt, den die bestehenden Punkte p6_1–p6_4 nicht gefunden
hätten** — der Backtest wies das Bein als profitabel aus, der erste Live-Trade
verlor das 2,2-fache seines Budgets.

Zweiter vollstaendiger Durchlauf: [[ctnl-kostenvalidierung]] (2026-09-21, beide CTNL-Beine). Dort lagen die gegriffenen Kosten **zu hoch** statt zu niedrig — die Proben taugen also in beide Richtungen, nicht nur zur Entzauberung.

Verwandt: [[broker-kostenmodell-eurusd]] (die gemessenen Werte),
[[backtest-standard-process]] (der übergeordnete Prozess).

---

## Warum das nötig war

Der Backtest sagte: profitabel. Die Realität sagte: 2,2x Budgetverlust im
ersten Trade. Dazwischen lagen **vier voneinander unabhängige Lücken**, von
denen keine ein Bug im klassischen Sinn war — jede war eine stillschweigende
Annahme, die niemand je geprüft hatte.

---

## Probe 1 (p6_5) — Kosten messen, nicht annehmen

**Die Falle:** Kostenparameter werden beim Anlegen einer Engine einmal gesetzt
und nie wieder hinterfragt. Im Repo standen nebeneinander `spread_bps=0.3`
(cls_practical) und `spread_bps=8.0` (CTNL) — beides gegriffene Zahlen.

**Die Probe:** Spread, Slippage **und Kommission** aus den echten
Broker-Terminals ziehen, je Broker getrennt. Muster:
`scripts/measure_broker_spreads.py` (rein lesend, über
`mt5.copy_ticks_range` / `history_orders_get` / `history_deals_get`).

**Was dabei zu beachten ist:**
- **Im Handelsfenster messen**, nicht über 24 h — Asien-Session und Rollover
  verzerren den Median massiv.
- **Slippage getrennt nach Ein- und Ausstieg.** Die Einstiegs-Slippage ist die
  gefährlichere: sie geht in die Positionsgröße ein.
- **Kommission gehört dazu.** Sie war in *keiner* Engine des Repos modelliert
  und machte bei cls_practical 0,4–0,5 Pips aus.
- **Broker unterscheiden sich real.** Identisches Signal, identischer SL:
  TTP realisierte 2,8 Pips Verlust, IQ Markets 1,8. Ein globales `spread_bps`
  kann für beide nicht stimmen.

**Der Befund im Fall CLS:** der Spread war unschuldig (0,10–0,30 Pips). Die
komplett fehlenden Blöcke waren Slippage (`slippage_bps=0.0`) und Kommission.
Round-Trip real: TTP 2,05 Pips, IQ 1,30 — gegen ein Modell von 0,35.

---

## Probe 2 (p6_6) — Ausführungs-Lag simulieren

**Die Falle — die teuerste von allen:** der Backtest steigt zum Schlusskurs
der Signalbar ein. Der Live-Bot steigt beim nächsten Scan-Zyklus ein. Diese
Differenz ist kein Rundungsfehler.

**Die Probe:** jeden Trade auf den verzögerten Einstieg umrechnen. Wenn SL und
TP am Signal-Level hängen (und nicht am Einstiegspreis), ist das billig — es
verschiebt sich nur der Einstiegspreis und die Positionsgröße, die
Ausstiegsseite bleibt. Muster:
`scripts/research_cls_practical_entry_gate.py::simulate_live_entries`.

**Was dabei zu beachten ist:**
- **Den Lag richtig ansetzen.** Bar-Label ≠ Bar-Schluss: ein M5-Bar mit Label
  10:20 schließt um 10:25. Ich habe hier zunächst selbst um eine Bar zu
  pessimistisch gerechnet.
- **Mehrere Lags rechnen, nicht einen.** Ist die Kurve nicht monoton, ist der
  Effekt in diesem Bereich Rauschen — und ein einzelner Lag-Wert wäre eine
  Zufallszahl gewesen.

**Der Befund im Fall CLS:** ohne Schutzmechanismen kostet der Versatz mehr
Edge als sämtliche Broker-Kosten zusammen (Ø R von −0,02 bei Lag 0 auf −0,19
bei 15 Min, monoton). Mit Stop-Boden und Entry-Gates verschwindet die
Lag-Abhängigkeit im Rauschen — die Schutzmechanismen neutralisieren den
Versatz weitgehend.

---

## Probe 3 (p6_7) — Den Sizing-Nenner prüfen

**Die Falle:** der Backtest sizet auf die *geplante* Stopdistanz, der Live-Bot
auf `|Live-Kurs − SL|`. Läuft der Kurs zwischen Signal und Ausführung auf den
Stop zu, schrumpft der Nenner — und die Position wächst, obwohl der
$-Risikobetrag konstant bleibt.

**Die Probe:** Verteilung des real erzeugten Hebels ausweisen, **nicht nur den
Median**. Der Median ist typischerweise harmlos.

**Nützliche Identität:** sind bereits X R der Stopdistanz gegen das Signal
aufgebraucht, ist die Position um exakt `1/(1−X)` aufgebläht. Ein Entry-Gate
auf X R **ist** damit ein Hebel-Deckel — man braucht nicht beides:

| Schwelle | max. Aufblähung |
|---|---|
| 0,50R | 2,0x |
| 0,60R | 2,5x |
| 0,75R | 4,0x |
| 0,90R | 10,0x |

**Der Befund im Fall CLS:** Median-Hebel 2,4x — unauffällig. Maximum 58,8x
Equity. Der Vorfallstrade lag bei 0,76R aufgebrauchter Distanz und damit bei
20,8 statt der geplanten ~6,9 Lots.

---

## Probe 4 (p6_8) — Stop-Abstand gegen die Kosten stellen

**Die Falle:** relative Stop-Böden (`min_sl_atr_mult × ATR`) schrumpfen in
ruhigen Phasen mit. Sie schützen genau dann nicht, wenn der Schutz nötig wäre.

**Die Probe:** Anteil der Trades mit Stopdistanz < 3x Round-Trip-Kosten und
deren Ø R **separat** ausweisen. Sitzt dort der gesamte Verlust, ist ein
absoluter Boden fällig.

**Der Befund im Fall CLS:** Trades mit Stop < 6,15 Pips (42 % aller) hatten
Ø R −0,238, die übrigen +0,343. Ein absoluter Boden von 5 Pips
(≈ 2,5x Round-Trip-Kosten) senkte die Wahrscheinlichkeit eines negativen
Erwartungswerts von 26,6 % auf 1,2 %.

---

## Was im Fall CLS NICHT half — als Warnung vor Umwegen

Getestet und verworfen, jeweils mit Zahlen in
[[cls-practical-kostenvalidierung]]:

- **Stop aufweiten statt Trade verwerfen.** Das TP-Ziel bleibt stehen, das
  R:R kollabiert. Man behält den schlechten Trade *und* verschlechtert ihn.
- **Stop aus der durchschnittlichen Session-Volatilität.** Ersetzt das
  *strukturelle* SL-Niveau — und genau das trägt den Edge. Es ist nicht egal,
  **wo** der Stop liegt, nur **wie weit**.
- **ATR-Böden auf höheren Timeframes** (M15/M30/H1). Die Vermutung "nicht
  relativ war das Problem, sondern M5" war falsch; keine Variante erreichte
  den festen Boden, alle mit großer IS/OOS-Lücke.
- **Feste R-Ziele** (1R–4R) und **Break-even-Nachziehen**. Letzteres schneidet
  die Gewinner ab, die solche Strategien tragen.

---

## Methodenregel, die aus alldem folgt

**Vor jeder Parameterwahl den Bootstrap rechnen** (p6_2 ist dafür schon da,
wurde hier aber erst nachträglich angewandt). Im Fall CLS entlarvte er ein
scheinbar deutlich besseres TP-Ziel (PF 1,64 gegen 1,52) als Rauschen —
überlappende Konfidenzintervalle, Trefferquote von 48 % auf 23 % gefallen —
und bestätigte gleichzeitig den Stop-Boden als echten Effekt.

**Zwei Warnsignale, die immer zum Verwerfen führen sollten:**
1. Das Optimum liegt am **Rand des getesteten Gitters** — dann ist das Gitter
   zu klein, nicht der Parameter gut.
2. Die Parameterfläche ist **zackig statt plateauförmig** — ein Optimum ohne
   Nachbarn, die fast genauso gut sind, ist ein Zufallstreffer.
