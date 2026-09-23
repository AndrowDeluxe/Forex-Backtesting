# OU-Modell: Live-Auswertung und Kostenvalidierung

Stand 2026-09-17. Auslöser: Nutzerfrage „das OU-Bein wirkt nicht profitabel —
ist das normal, und fressen Kosten/Versatz den Edge?“. Gleiche Fragestellung
wie [[cls-practical-kostenvalidierung]], anderes Bein.

## Kurzfassung

- **Das Modell hat reibungsfrei nur einen dünnen Edge:** +0,097R je Trade,
  PF 1,34 (2018–2026, 1.050 Trades, Funded-Konfiguration).
- **Realistische Ausführung halbiert ihn** (Einstieg am Folgetag, Broker-Stop
  intraday): +0,05R.
- **Die live gemessenen Kosten fressen den Rest:** Spread −0,033R, Swap
  −0,032R → **−0,013R, PF 0,96**. Seit 2023 schon ohne Kosten nur +0,012R,
  mit Kosten −0,046R.
- **Live-Ergebnis passt dazu:** 88 geschlossene Trades ≈ 0R (ohne den
  Split-Trade). Das schwache August/September-Fenster (65 Trades, −17,6R)
  liegt unter realistischen Kosten im unteren ~2–3-%-Bereich — selten, aber
  kein Beweis für einen Bruch.
- **Zusätzlich drei echte Bugs/Betriebsschäden**, die nichts mit dem Edge zu
  tun haben (unten).

## Datenbasis

- Live: MT5-Deal-Historie read-only von allen drei OU-Konten (TTP Konto 1
  echtes Geld, TTP Konto 2 Demo, Tickmill/EK echtes Geld), 2026-07-23 bis
  09-16. 123 Aktien-Positionen, davon 89 geschlossen.
- Backtest: `scripts/research_ou_execution_costs.py`, Ergebnis
  `ou_paper_backtest/results/execution_costs_20260916.json` + Trade-CSVs.
  Das Modell erzeugt die Trade-Liste, jeder Trade wird auf echten Tageskerzen
  in mehreren Ausführungsvarianten neu durchgespielt — Differenzen sind reine
  Ausführung. Replay-Variante A reproduziert die Original-Engine exakt.

## Live gemessene Kosten

| Posten | Wert | Quelle |
|---|---|---|
| Spread am Fill, Median | 12 bps | MT5-Ticks ±90 s um jeden TTP-Fill |
| Spread 09:30–10:00 NY | 26 bps (Median) | dito — 42 von 123 Einstiegen lagen hier |
| Spread ab 11:00 NY | 9–10 bps | dito |
| Fill vs. Mid | +9 bps | dito |
| Swap Aktien-CFD | 6,5 % p.a. = 1,78 bps/Tag | Deals, deckt sich mit `swap_long` −6,24 % |
| Stop-Slippage | +3 bps (Median) | Exit-Preis vs. `[sl …]`-Level |
| Kommission | 0 | beide Broker |
| Stopdistanz | Median 5,9 % | Initial-SL der Orders |

## Ergebnis nach Ausführungsvariante (Ø R je Trade, 2018–2026)

| Variante | Ø R | PF | Trefferquote |
|---|---|---|---|
| A Modell (Schlusskurse, keine Kosten) | +0,097 | 1,34 | 48 % |
| B + Einstieg Folgetag-Eröffnung | +0,070 | 1,24 | 49 % |
| C + Initial-SL intraday (= Funded) | +0,054 | 1,18 | 48 % |
| D + BE/TP broker-seitig (= Solo/EK) | +0,055 | 1,25 | 37 % |
| C$ mit Live-Kosten | **−0,011** | 0,97 | 44 % |
| D$ mit Live-Kosten | **−0,004** | 0,98 | 36 % |

Kostenzerlegung auf Variante C: ohne Kosten +0,051R · nur Spread +0,018R ·
nur Swap +0,019R · beides −0,013R · Einstieg erst ab 10:00 NY +0,001R ·
doppelte Spreads −0,043R.

**Lehre:** Swap ist hier genauso teuer wie der Spread. 63 % der Trades enden
per Max-Holding (10 Handelstage ≈ 14 Kalendertage Finanzierung) — die
Haltedauer selbst ist der Kostentreiber. Die bisherige Kostenstudie
(`results/sp500/cost_sensitivity.json`) rechnete nur pauschale bps auf den
Nominalwert und übersah Swap, Folgetag-Einstieg und Intraday-Stops.

## Betriebsschäden (unabhängig vom Edge)

1. **Signaldatum „wandert“ zwischen Scans → doppelte und verwaiste
   Positionen (Funded).** Der Bridge-Schlüssel enthält das Einstiegsdatum.
   `_scan_ou_modell()` rechnet die Portfolio-Historie bei jedem Lauf neu
   (pfadabhängig über den 5-%-Risikodeckel); dasselbe Signal taucht mal mit
   09-08, mal mit 09-11 auf. Jede neue Datumsvariante ist ein neuer Schlüssel
   → **zweiter Einstieg im selben Titel** (AMGN 2×, APD 2× auf beiden
   TTP-Konten), und die alte Position fällt aus dem Scan und **wird nie
   geschlossen**. Am 2026-09-17 betroffen: 4 Positionen auf TTP Konto 2
   (FAST, ADI, AMGN 09-11, APD 09-14), 2 auf Konto 1 (AMGN 09-11, APD 09-14) — darunter FAST/ADI, die das Modell längst per Max-Holding
   beendet hat. Vermutete Ursache für das Wandern (nicht einzeln belegt):
   das 450-Tage-Fenster rollt täglich, Lake-Kurse werden rückwirkend
   dividendenbereinigt.
2. **8 verwaiste Solo-Bot-Positionen** vom abgeschalteten
   OU-Modell-MT5-Bridge (DAL/UAL/NUE auf Konto 1, AFL/NUE/UAL/TXT auf Konto 2,
   DAL auf Tickmill), 22–27 Tage alt, nur Broker-SL/TP, laufender Swap.
3. **Aktiensplit auf TTP nicht umgebucht.** MNST 2:1 am 2026-08-11: Tickmill
   buchte die Position korrekt um (`[split 2-1 close/open]`), TTP nicht — der
   alte SL 85,68 wurde zum Split-Kurs 45,69 ausgelöst. **−2.492,56 $ auf
   Konto 1 (echtes Geld), keine Ausgleichsbuchung.** Allein dieser Trade
   entspricht ~10R.

## Offene Entscheidungen

Siehe DASHBOARD.md „Braucht deine Bestätigung“ — Bein weiterführen/pausieren,
Umgang mit verwaisten Positionen, Fix der Schlüssel-Drift, TTP-Support wegen
MNST.

---

# Optimierungsversuch (2026-09-19): Ausführung, Einstiegszeit, Zeitraum

Fortsetzung der Auswertung oben, Plan `.claude/plans/breezy-wiggling-dove.md`.
Frage: Gibt es eine Ausführung (Zeitpunkt, Ordertyp, Abweichungsgrenze), die
das Bein wieder profitabel macht — belastbar, nicht überangepasst?

Skript `scripts/research_ou_execution_optimization.py`, Ergebnis
`ou_paper_backtest/results/execution_optimization_20260917.json`. Die
Trade-Liste des Modells bleibt fix (1.050 Trades, 2018–2026), variiert wird
nur die Ausführung. **Rangfolge ausschließlich auf In-Sample**
(Tageskerzen: Signal < 2023; Stundenkerzen: Signal < 2025), Out-of-Sample nur
berichtet, mit Bootstrap-Konfidenzintervall (2.000 Ziehungen).

**Regressionstest bestanden:** das erweiterte Replay trifft die Werte vom
16.09. exakt (A +0,0969R bei 1.050 Trades, C$ −0,0103R bei 1.025).

## Block 0 — Spread über den Handelstag (TTP-Ticks, ~4 Wochen, 59 Titel)

| NY-Zeit | 09:35 | 09:45 | 10:00 | 10:30 | 11:00 | 12:00 | 14:00 | 15:45 |
|---|---|---|---|---|---|---|---|---|
| Median bps | **27,9** | 19,8 | 17,0 | 14,2 | 12,4 | 10,4 | 10,0 | **8,3** |

Deckt sich mit den 78 live gemessenen Fills (Median 12 bps, Eröffnungsphase
26 bps). Die erste halbe Stunde kostet also gut das Dreifache des Nachmittags.
**Aber:** der Unterschied 09:35 → 15:45 sind ~10 bps auf den Kurs, bei einer
Median-Stopdistanz von 5,9 % entspricht das **0,017R** — real, aber eine
Größenordnung kleiner als die Lücke, die zu schließen wäre.

## Block 1 — Ausführungsvarianten auf Tageskerzen (Funded-Familie)

| Variante | IS Ø R | OOS Ø R | OOS-KI 95 % | übersprungen |
|---|---|---|---|---|
| close_d1 (Folgetag vor Schluss) — **IS-Sieger** | **+0,067** | −0,024 | [−0,102; +0,056] | 8,7 % |
| close_d0 (noch am Signaltag) | +0,047 | −0,006 | [−0,072; +0,059] | 0 % |
| open_d1 Gate 3,5 % (**heute live**) | +0,010 | **−0,046** | [−0,112; +0,023] | 2,4 % |
| Gate 1 / 2 / 3 / 5 % / kein Gate | −0,022 … +0,016 | −0,032 … −0,046 | — | 0,3–23 % |
| Limit-Order (k = 0 / 0,25 / 0,5) | −0,33 … +0,000 | −0,47 … +0,015 | — | bis 92 % |

**Kein einziger Kandidat der Funded-Familie ist out-of-sample positiv.** Die
Abweichungsgrenze („3,5-%-Punkt") ist praktisch wirkungslos: ob 1 %, 3,5 % oder
gar kein Gate, OOS liegt alles zwischen −0,03 und −0,05R. Limit-Einstiege
scheitern an der Adverse Selection — bei k = 0,5 werden 92 % der Trades nicht
gefüllt, und die gefüllten sind die schlechten.

In der EK-Familie (BE/TP broker-seitig) liegen close_d0 (+0,029 OOS) und
close_d1 (+0,007 OOS) knapp über null, aber beide Konfidenzintervalle
umschließen die Null ([−0,031; +0,088] bzw. [−0,052; +0,068]) — das ist kein
Nachweis eines Edges.

## Block 2 — Einstiegsstunde am Folgetag (TTP-Stundenkerzen 2023-03 … 2026-09)

| Einstieg NY | 09:35 | 10:00 | 11:00 | 12:00 | 13:00 | 14:00 | 15:00 |
|---|---|---|---|---|---|---|---|
| IS Ø R (bis 2024) | −0,035 | −0,062 | −0,043 | −0,047 | −0,049 | −0,043 | −0,049 |
| OOS Ø R (ab 2025) | +0,020 | −0,008 | +0,003 | −0,004 | +0,005 | −0,006 | −0,001 |

**Die Einstiegsstunde ist kein Hebel.** Jede Stunde ist in-sample negativ,
out-of-sample liegt alles innerhalb ±0,02R bei Konfidenzintervallen von rund
±0,10R. Der Spread-Vorteil des späten Einstiegs (0,017R, Block 0) verschwindet
im Rauschen — er ist da, aber er trägt nichts.

Damit ist die Aussage aus der Auswertung vom 17.09. („nur Einstieg nach
10:00 NY bringt es auf ±0") **präzisiert**: die Rechnung stimmt als reine
Kostenrechnung, aber sie hält auf echten Stundenkerzen keiner Zeitraum-Trennung
stand.

Ausreißer, bewusst nicht als Empfehlung geführt: EK-Familie mit Einstieg 09:35
liefert OOS +0,102R (KI [+0,012; +0,191]) — bei in-sample −0,052R. Nach der
IS-Rangfolge wäre diese Variante nie ausgewählt worden, und sie behauptet
ausgerechnet vom teuersten Einstiegszeitpunkt den besten Ertrag. Das ist mit
hoher Wahrscheinlichkeit Zufall (n = 210).

## Zeitraumtest — wo genau der Edge verloren geht

| Variante | IS 2018–22 Ø R (PF) | OOS 2023–26 Ø R (PF) |
|---|---|---|
| A Modell, reibungsfrei | +0,117 (1,38) | **+0,075 (1,28)** |
| C realistisch ausgeführt (Funded) | +0,086 (1,28) | +0,017 (1,06) |
| C$ + Live-Kosten | +0,017 (1,05) | **−0,041 (0,86)** |
| D realistisch ausgeführt (EK/Solo) | +0,069 (1,30) | +0,039 (1,18) |
| D$ + Live-Kosten | +0,008 (1,03) | −0,018 (0,93) |

Je Signaljahr (Ø R): 2018 −0,03 · 2019 +0,17 · 2020 +0,22 · 2021 +0,22 ·
2022 −0,44 (nur 28 Trades, Regimefilter) · 2023 +0,05 · 2024 +0,08 ·
2025 +0,07 · 2026 +0,11 — jeweils Variante A.

**Das ist der eigentliche Befund:** Der Modell-Edge ist NICHT verschwunden. Er
ist seit 2023 mit +0,075R je Trade (PF 1,28) noch da, nur rund ein Drittel
kleiner als 2018–2022. Verloren geht er in zwei Stufen:

1. **Ausführung** frisst OOS 0,058R (A → C: Folgetag-Einstieg + Broker-Stop
   intraday). 2018–2022 waren das nur 0,031R — der Verlust durch die
   Ausführung hat sich fast verdoppelt.
2. **Kosten** frisst 0,064R je Trade (Spread + Swap), davon etwa die Hälfte
   Swap, weil 63 % der Trades die vollen 10 Tage laufen (Ø Haltedauer 8,4
   Handelstage).

Der Bruttoedge von +0,075R muss also 0,122R Reibung tragen. **Das Bein
scheitert nicht an einem toten Edge, sondern daran, dass Ausführung und Kosten
zusammen anderthalb Mal so groß sind wie der Edge.** Und genau das kann die
Ausführungswahl allein nicht drehen — Block 1 und 2 sagen übereinstimmend, dass
dort höchstens 0,02R zu holen sind.

## Block 3 — Modell-Hebel (54 Kombinationen, Engine je Kombination neu)

`max_hold` × `stop_sigma` × `be_trigger_r`, gespielt auf der IS-besten
Ausführung aus Block 1 (Folgetags-Schluss). Live-Konfiguration ist heute
`max_hold=10, stop_sigma=3,0, be_trigger_r=0,35`.

| Kombination (Funded) | IS Ø R | OOS Ø R |
|---|---|---|
| hold 10 · σ 3,0 · **BE aus** — IS-Sieger aller 54 | **+0,079** | +0,010 |
| hold 10 · σ 3,0 · BE 0,35 (**heutige Konfig**) | +0,067 | −0,024 |
| hold 7 · σ 3,0 · BE aus | +0,050 | +0,012 |
| hold 5 · σ 3,0 · BE 0,35 | +0,036 | −0,025 |
| hold 10 · σ 3,5 · BE 0,35 | +0,012 | −0,040 |
| hold 10 · σ 2,5 · BE 0,35 | −0,014 | +0,028 |

Drei Antworten:

1. **Der Breakeven-Stop kostet Geld.** BE aus ist die beste Kombination
   in-sample UND dreht das OOS-Vorzeichen. Er nimmt Gewinner zu früh heraus,
   während die Verlierer voll durchlaufen — bei 48 % Trefferquote ist das teuer.
2. **`max_hold` kürzen hilft NICHT.** Das war die naheliegende Idee gegen den
   Swap (63 % der Trades laufen die vollen 10 Tage). Aber von hold 10 auf 5
   fällt der IS-Wert von +0,079 auf +0,025: die eingesparte Finanzierung ist
   kleiner als der Edge, der in den letzten Tagen noch entsteht. Die
   Mean-Reversion braucht die Zeit.
3. **`stop_sigma` 3,0 ist bereits richtig gewählt.** 2,5 und 3,5 sind beide
   in-sample schlechter. Die σ-2,5-Zeilen mit gutem OOS (+0,03…+0,08) sind
   in-sample negativ — nach der IS-Rangfolge nicht wählbar, und genau das
   Muster, das eine Überanpassung erzeugt, wenn man es umgekehrt liest.

## Die zwei Hebel getrennt (2×2, identische Trade-Basis)

Im Block-3-Ranking vermischen sich zwei sehr verschiedene Dinge: ein
Config-Flip (BE aus) und eine Betriebsänderung (Einstieg zum Folgetags-Schluss
statt zur Eröffnung). Getrennt gemessen, Funded-Familie, OOS Ø R:

| | Einstieg Eröffnung (**heute live**) | Einstieg Folgetags-Schluss |
|---|---|---|
| **BE 0,35 (heute live)** | **−0,051** (PF 0,83) | −0,025 (PF 0,92) |
| **BE aus** | −0,022 (PF 0,93) | **+0,012** (PF 1,04) |

Beide Hebel wirken, und sie addieren sich näherungsweise: BE aus bringt
+0,029R, der spätere Einstieg +0,026R. Zusammen +0,063R — vom klar negativen
Zustand auf knapp positiv.

**Warum der spätere Einstieg hilft:** die Eröffnung ist nicht nur der teuerste
Spread (27,9 statt 8,3 bps), sie ist auch der Moment, in dem die Overnight-
Bewegung noch weiterläuft. Bis zum Schluss des Folgetags hat sich der Kurs im
Mittel weiter in Richtung des Signals gedreht.

## Gegenprobe: kommt der Gewinn aus verstecktem Hebel?

Der Einstieg am Folgetags-Schluss liegt öfter dicht am Stop, und die Bridges
sizen auf die TATSÄCHLICHE Stopdistanz — eine kurze Distanz heißt automatisch
eine große Position. Gemessen:

| Einstieg | Median-Stopdistanz | Anteil < 2 % | Minimum | Nominal bei 1 % Risiko (P95) |
|---|---|---|---|---|
| Eröffnung | 6,6 % | 0,8 % | 0,65 % | 33× Konto |
| Folgetags-Schluss | 6,3 % | **3,8 %** | **0,16 %** | **42× Konto** |

Ein 0,16-%-Stop bei 1 % Risiko wäre ein Nominal von 625× Konto — das gibt kein
Broker her. Deshalb nachgerechnet mit gedeckelter Position (Risiko skaliert
herunter, wenn die Stopdistanz unter der Mindestdistanz liegt):

| Mindest-Stopdistanz | IS Ø R | OOS Ø R | OOS PF | OOS-KI 95 % |
|---|---|---|---|---|
| keine | +0,079 | +0,012 | 1,04 | [−0,064; +0,096] |
| 2 % | +0,026 | +0,018 | 1,06 | [−0,055; +0,086] |
| **3 %** | +0,029 | **+0,020** | **1,07** | [−0,049; +0,092] |
| 4 % | +0,036 | +0,020 | 1,08 | [−0,045; +0,083] |

**Der Befund hält.** Die Deckelung halbiert zwar den In-Sample-Wert (+0,079 →
+0,029 — ein Teil des IS-Siegs WAR Hebel), verbessert aber das
Out-of-Sample-Ergebnis leicht. Der OOS-Gewinn stammt also nicht aus
überhebelten Trades dicht am Stop. In der EK-Familie dasselbe Bild
(+0,025R OOS, PF 1,10).

## Fazit und Empfehlung

**Die Ausführung allein rettet das Bein nicht** — das war die Ausgangsfrage,
und die Antwort ist nein. Weder Einstiegszeitpunkt noch Ordertyp noch
Abweichungsgrenze bringen mehr als ~0,02R, und keine Variante der heutigen
Konfiguration ist out-of-sample positiv.

**Zwei Änderungen zusammen drehen das Vorzeichen:**

| Zustand | OOS Ø R | OOS PF |
|---|---|---|
| heute (Eröffnung, BE 0,35) | −0,051 | 0,83 |
| + BE-Stop aus | −0,022 | 0,93 |
| + Einstieg Folgetags-Schluss, Mindest-Stop 3 % | **+0,020** | **1,07** |

**Aber das ist kein nachgewiesener Edge.** Das Konfidenzintervall
[−0,049; +0,092] umschließt die Null. Ehrlich gelesen: aus einem Bein, das
zuverlässig Geld verliert, wird ein Bein, das ungefähr nichts verdient — bei
weiterhin echtem Risiko und echtem Swap.

Entscheidungsvorlage (liegt bei dir, an den Bridges wurde nichts geändert):

- **A — BE-Stop aus, sonst alles lassen.** Reiner Config-Flip
  (`OU_MODELL_BE_TRIGGER_R = 0`), betrifft `challenge_portfolio/paper_bot.py`
  (und damit direkt die Funded-Bridge) sowie die EK-Bridge. Hebt das Bein von
  −0,051 auf −0,022R — immer noch negativ, aber der am besten belegte
  Einzelschritt (IS-Sieger aller 54 Kombinationen).
- **B — zusätzlich Einstieg zum Folgetags-Schluss** (statt zur Eröffnung), mit
  Mindest-Stopdistanz 3 %. Das ist eine echte Betriebsänderung: die Bridge
  müsste zur US-Schlussauktion handeln statt morgens. Ergebnis ±0.
- **C — Bein pausieren.** Vertretbar, solange der Bruttoedge (+0,075R) unter
  der Reibung (0,122R) liegt und die Verbesserung nur bis „ungefähr null"
  reicht.

Vor JEDER Live-Änderung fehlt nach Repo-Prozess Phase 6 (Robustheit/Monte
Carlo) — die Zahlen hier sind Punktschätzer mit Konfidenzintervallen, keine
Robustheitsprüfung. Und: der MNST-Split-Schaden (−2.492 $, oben) ist
ungefähr so groß wie alles, worüber diese Optimierung entscheidet.

---

# Vertiefung (2026-09-19): SL/TP-Logik und Broker-Kosten EK vs. FK

Nutzerfrage: "gehe tiefer in den Backtest und pruefe mit den festgestellten
Kosten eine andere SL/TP-Logik. Alle Ausfuehrungen hast du bereits
durchgeschaut? Wie unterschiedlich sind die Kosten auf EK und FK und wie
unterschiedlich entwickelt sich dadurch das Bein?"

**Zur Zwischenfrage ehrlich: nein, waren sie nicht.** Block 1 hat den EINSTIEG
durchvariiert, Block 3 drei Parameter. Die Ausstiegs-LOGIK selbst — Stop-Art,
Kursziel-Regel, ob es ueberhaupt ein festes Ziel gibt — war in allen bisherigen
Laeufen gesetzt und wurde nie hinterfragt.

Skripte: `scripts/research_ou_exit_logic.py` (Ausstiegslogiken),
`scripts/research_ou_broker_costs.py` (Broker-Kosten, rein lesend aus beiden
MT5-Terminals). Ergebnisse: `ou_paper_backtest/results/exit_logic_20260919.json`,
`exit_logic_engine_20260919.json`, `exit_logic_sigma_plateau_20260919.json`,
`broker_costs_ou_20260919.json`.

## Was die heutige Logik eigentlich tut

Exit-Gruende der replayten Trades unter der Live-Logik:

| Grund | Anteil |
|---|---|
| max_hold (10 Tage abgelaufen) | 63 % |
| Stop-Loss | 18 % |
| Breakeven-Stop | 15 % |
| **Take-Profit 1,5R** | **4,8 %** |

**Das Kursziel feuert in 5 % der Trades.** Der Grund ist Geometrie: der
Einstieg liegt am unteren Bollinger-Band, also 2 Sigma unter dem Mittel. Das
Kursziel 1,5R liegt bei 1,5 x 3 Sigma = **4,5 Sigma** ueber dem Einstieg — mehr
als doppelt so weit wie die Mean Reversion, auf die die Strategie ueberhaupt
wettet. Direkter Beleg: die Variante "MA-Ausstieg ODER TP 1,5R" liefert auf
vier Nachkommastellen dasselbe Ergebnis wie "nur MA-Ausstieg". Das Ziel wird
nie erreicht, bevor der Kurs am Mittel ankommt.

## Ausstiegslogiken im Vergleich (FK-Kosten, OOS 2023-2026)

| Logik | brutto | mit Kosten | PF | Tage | schlechtester |
|---|---|---|---|---|---|
| Bracket + BE (**heute live**) | +0,013 | **-0,052** | 0,83 | 8,4 | -2,54R |
| Bracket ohne BE | +0,019 | -0,048 | 0,85 | 8,9 | -2,54R |
| Trailing-Stop (2 / 3 Sigma) | +0,014 | -0,043 | 0,86 | 8,9 | -2,54R |
| TP-Sweep 0,75 / 1 / 2 / 3R | +0,014…+0,035 | -0,017…-0,040 | <= 0,94 | 7,8-9,0 | -2,54R |
| **MA-Ausstieg** (Regel des Original-Papers) | +0,036 | **-0,027** | 0,91 | **7,5** | -2,54R |
| kein Stop, nur MA + max_hold | +0,085 | +0,014 | 1,05 | 8,4 | -2,51R |

Der Trailing-Stop bringt nichts — er zieht fast nie an, weil der Kurs selten
weit genug ueber den Einstieg laeuft. Der MA-Ausstieg ist die beste
*regelbasierte* Variante und verkuerzt die Haltedauer um 1,5 Tage, spart also
zusaetzlich Swap. Die mit Abstand beste Zeile ist aber die ganz ohne Stop.
Das war der Hinweis, dem nachzugehen war.

## Der Stop ist zu eng — und ein breiterer Stop verbessert AUCH das Risiko

Stop-Weite durchgetestet, Engine bei jeder Weite NEU gerechnet (ein breiterer
Stop heisst kleinere Position, anderer Risikodeckel, andere Trade-Auswahl — das
Replay allein haette das verdeckt). Kosten FK, Einstieg wie heute:

| Stop | Stopdistanz Median | Position vs. heute | OOS Ø R (MA-Ausstieg) | PF | schlechtester | P05 |
|---|---|---|---|---|---|---|
| 3 Sigma (**heute**) | 6,2 % | 100 % | -0,015 | 0,95 | -2,54R | -1,05R |
| 6 Sigma | 12,6 % | 50 % | -0,003 | 0,98 | -1,24R | -0,68R |
| **8 Sigma** | **16,7 %** | **37,5 %** | **+0,008** | **1,08** | **-0,90R** | **-0,47R** |
| 12 Sigma | 25,1 % | 25 % | +0,007 | 1,11 | -0,61R | — |
| 16 Sigma | 33,5 % | 18,8 % | +0,006 | 1,12 | -0,46R | — |

Das Ergebnis verbessert sich **auf beiden Seiten gleichzeitig**. Das klingt
beim Lesen zuerst falsch: ein weiterer Stop macht den schlechtesten Trade nicht
schlimmer, sondern besser. Der Grund ist die Positionsgroesse — die Bridge
sized auf die Stopdistanz, also ist die Position bei 8 Sigma nur noch 37,5 %
so gross wie heute, bei gleichem Dollar-Risiko. Ein Gap, das den Stop
ueberspringt, kostet dann 0,9R statt 2,5R. Fuer ein Funded-Konto mit
Drawdown-Regeln ist das die wichtigere Zahl als der Mittelwert.

Der enge 3-Sigma-Stop verwandelt also Rueckschlaege, aus denen sich die Aktie
wieder erholt, in realisierte Verluste — genau der Fehler, den eine
Mean-Reversion-Strategie am wenigsten machen darf.

**Kein Rand-Artefakt:** ueber 8 / 10 / 12 / 16 Sigma hinaus getestet. Das
Ergebnis bleibt durchgehend positiv und faellt nur langsam ab (OOS PF 1,19 ->
1,18 auf EK), das Maximum liegt bei 8 Sigma. Es ist ein Plateau, kein Gipfel am
Rand des getesteten Fensters — und damit nicht auf einen Bestwert hin
ausgesucht.

## Kosten EK (Tickmill) vs. FK (TTP)

Bisher wurde fuer BEIDE Portfolios mit denselben Kostenzahlen gerechnet — die
stammten aber ausschliesslich von TTP (die Tickfenster am 17.09. liefen ueber
das Funded-Terminal). Fuer das EK-Bein war nie etwas gemessen. Nachgeholt,
H1-Spreadfeld ueber 120 Tage, alle 59 Universum-Titel, beide Terminals:

| | FK (TTP) | EK (Tickmill) | Verhaeltnis |
|---|---|---|---|
| Spread Median (NY-Session) | 5,67 bps | **2,63 bps** | 0,46 |
| Spread erste Stunde | 9,31 bps | **4,95 bps** | 0,53 |
| Spread ab 12:00 NY | 5,05 bps | 2,38 bps | 0,47 |
| Swap long | -6,24 % p.a. | -6,23 % p.a. | **1,00** |
| nicht handelbare Titel | 0 von 59 | 0 von 59 | — |

**Tickmill ist beim Spread rund doppelt so guenstig, beim Swap exakt gleich
teuer.** Da der Swap etwa die Haelfte des Kostenblocks ausmacht, halbiert sich
der Vorteil auf dem Weg ins Ergebnis.

Methodenhinweis: das H1-Spreadfeld unterschaetzt den echten Spread systematisch
(TTP H1 9,31 bps zur Eroeffnung gegen 27,9 bps aus den Ticks — es wird am
Kerzenschluss gestempelt). Verwendet wird deshalb nicht der H1-Wert selbst,
sondern das VERHAELTNIS beider Broker, angewendet auf die tick-kalibrierten
TTP-Zahlen: Einstieg EK 10,4 bps statt FK 16,9 bps, Ausstieg 4,1 statt 5,0.

## Wie unterschiedlich entwickelt sich das Bein dadurch?

OOS 2023-2026, je Portfolio mit SEINER Ausfuehrungsfamilie (FK: nur Initial-SL
beim Broker; EK: BE/TP broker-seitig intraday):

| Logik | FK (TTP) | EK (Tickmill) | Differenz |
|---|---|---|---|
| heute live | -0,052 (PF 0,83) | -0,028 (PF 0,90) | +0,024 |
| MA-Ausstieg | -0,027 | -0,015 | +0,011 |
| 8 Sigma + MA-Ausstieg | +0,005 (PF 1,05) | +0,010 (PF 1,10) | +0,005 |

Die Differenz von 0,024R bei der heutigen Logik zerfaellt in **0,011R
Broker-Kosten** und **0,013R Ausfuehrungsfamilie** (dass EK Breakeven und TP
broker-seitig intraday liegen hat, FK nicht). Dieselbe Strategie verliert auf
dem EK-Konto also etwa halb so viel wie auf den Funded-Konten — aber kein
Vorzeichenwechsel: der Broker-Vorteil ist zu klein, um eine verlustbringende
Logik zu drehen.

In absoluten Zahlen ueber die 486 OOS-Trades:

| | FK | EK |
|---|---|---|
| heute live | **-25,3R** | -13,6R |
| 8 Sigma + MA-Ausstieg | +2,4R | +4,6R |

**Korrektur 2026-09-22:** hier stand zuerst "bei 1 % Risiko je Trade, rund
-25 % Konto". Das war die falsche Bezugsgroesse. Live riskiert das Bein
`capital_weight x LEG_RISK_PCT x Equity` -- auf FK 1/6 x 0,01 = **0,167 %**, auf
EK 1/8 x 0,0293 = **0,366 %** je Trade. Die -25,3R sind also rund **-4,2 %**
der FK-Kontoequity, nicht -25 %. Gleiche Falle wie in
`backtest_zahlen_gegen_szenario_pruefen` (Memory): eine R-Summe sagt nichts
ueber die Kontowirkung, solange die Risikoscheibe nicht danebensteht.

## Bestes belastbares Ergebnis

Engine bei 8 Sigma neu gerechnet, MA-Ausstieg, kein BE, kein TP:

| Einstieg | Broker | IS | OOS | PF | KI 95 % | schlechtester |
|---|---|---|---|---|---|---|
| heute (Eroeffnung) | FK | +0,004 | +0,008 | 1,08 | [-0,016; +0,032] | -0,90R |
| heute (Eroeffnung) | EK | +0,009 | +0,013 | 1,13 | [-0,012; +0,037] | -0,90R |
| Folgetags-Schluss | FK | +0,007 | +0,015 | 1,16 | [-0,011; +0,039] | -0,90R |
| **Folgetags-Schluss** | **EK** | +0,012 | **+0,020** | **1,21** | [-0,006; +0,045] | -0,90R |

Erstmals ist eine Variante **in-sample UND out-of-sample auf beiden Brokern und
bei beiden Einstiegsarten positiv**, ohne dass an der Rangfolge gedreht wurde.

**Was das nicht ist: ein Beweis.** Das Konfidenzintervall umschliesst bei drei
von vier Zeilen die Null. Und die Groessenordnung bleibt bescheiden: +0,015R je
Trade sind bei 1 % Risiko rund +2,4R ueber 3,7 Jahre. Der Gewinn liegt darin,
dass die -25R aufhoeren, nicht darin, dass das Bein Geld verdient.

**Reproduzierbarkeit:** zwei Laeufe derselben Konfiguration im Abstand von zwei
Tagen ergaben +0,0147R und +0,0128R. Ursache ist die rueckwirkende
Dividendenbereinigung von yfinance (`auto_adjust`) plus gelegentlich
fehlschlagende Einzeldownloads (955 statt 970 Trades im letzten Lauf). Alle
Zahlen hier sind auf etwa +-0,002R genau zu lesen — an den Vorzeichen und
Groessenordnungen aendert das nichts, an der dritten Nachkommastelle schon.

## Einordnung

Die Engine kennt die MA-Ausstiegsregel bereits: `portfolio.py::simulate_portfolio`
ist die Original-Regel des Papers ("exit at MA"), `simulate_bracket_portfolio`
der 2026 gebaute Ersatz mit festem Kursziel, Breakeven und engem Stop. Die
Umstellung auf die Bracket-Logik hat drei Dinge eingefuehrt, die einzeln
messbar Geld kosten: ein Kursziel, das in 5 % der Faelle erreicht wird, einen
Breakeven-Stop, der Gewinner herausnimmt, und einen Stop, der eng genug ist, um
normale Rueckschlaege zu realisieren. Der Backtest sagt: zurueck zur
Paper-Regel, mit weiterem Stop.

# Finale Konfiguration (Empfehlung, NICHT umgesetzt)

Alles zusammengenommen — Einstieg (Block 1-3), Ausstieg und Broker-Kosten:

| Parameter | heute live | Empfehlung | Wirkung OOS |
|---|---|---|---|
| `OU_MODELL_STOP_SIGMA` | 3,0 | **8,0** | groesster Einzelhebel, +0,023R, Tail -2,54R -> -0,90R |
| `OU_MODELL_BE_TRIGGER_R` | 0,35 | **0 (aus)** | +0,029R, IS-Sieger aller 54 Kombinationen |
| `rr_ratio` (TP) | 1,5 (sp500) | **keiner** | feuert ohnehin nur in 4,8 % der Trades |
| Ausstiegsregel | SL/TP/max_hold | **Ruecklauf ans MA20** | +0,024R, 1,5 Tage kuerzer = weniger Swap |
| `max_hold` | 10 | **10 (unveraendert)** | kuerzen kostet mehr Edge als es Swap spart |
| Einstieg | Folgetags-Eroeffnung | Folgetags-Schluss *(optional)* | +0,007R, aber Betriebsaenderung |
| Mindest-Stopdistanz | keine | 3 % *(nur mit Schluss-Einstieg noetig)* | verhindert versteckten Hebel |

Ergebnis: FK von -0,052R (PF 0,83) auf **+0,008R (PF 1,08)**, EK von -0,028R
auf **+0,013R (PF 1,13)** — ohne Einstiegsaenderung. Mit Schluss-Einstieg
+0,015R (FK) bzw. +0,020R (EK).

**Was das an Code heisst** (keine reine Config-Aenderung):

1. `ou_paper_backtest/portfolio.py`: `simulate_bracket_portfolio` braucht einen
   MA-Ausstieg als Option. Die Regel existiert in `simulate_portfolio`, dort
   fehlen aber `regime_filter` und `rr_ratio` — eine der beiden Funktionen muss
   erweitert werden.
2. `challenge_portfolio/paper_bot.py`: STOP_SIGMA 8,0 · BE_TRIGGER_R 0 ·
   rr_ratio None · MA-Ausstieg an. **Achtung:** diese Datei wird von der
   Funded-Portfolio-Bridge DIREKT importiert — ein Commit wirkt beim naechsten
   Bridge-Lauf auf echtes Geld.
3. EK-Portfolio-Bridge `legs/ou_modell/`: dieselben Parameter, und der Executor
   darf keinen TP mehr setzen und den Stop nicht mehr auf Breakeven ziehen.

**Vorher fehlt Phase 6** (Robustheit/Monte Carlo) nach Repo-Prozess. Die Zahlen
oben sind Punktschaetzer mit Konfidenzintervallen, keine Robustheitspruefung —
und eine Stopweite von 8 Sigma ist noch nie durch den 8-Phasen-Prozess
gelaufen.

**Offene Folgefrage (nicht gerechnet):** bei 8 Sigma ist die Position nur noch
37,5 % so gross wie heute, das Risikobudget je Trade (1 %) und der
5-%-Gesamtdeckel bleiben aber unveraendert. Es waere also Platz fuer mehr
Risiko je Trade oder mehr gleichzeitige Positionen. Das ist eine
Risiko-Kalibrierung und gehoert hinter Phase 6, nicht davor.

---

# Phase 6 (Robustheit) fuer die empfohlene Konfiguration (2026-09-22)

Nutzerauftrag: "lasse deine Empfehlung noch ueber die anderen Tests der Phase 6
laufen". Geprueft: stop_sigma 8,0 · BE aus · kein TP · MA20-Ausstieg ·
max_hold 10 · Einstieg wie heute live. Skript `scripts/research_ou_phase6.py`,
Ergebnisse `phase6_ou_final_20260922.json` +
`phase6_ou_montecarlo_live_20260922.json`.

| Punkt | Status | Woher |
|---|---|---|
| p6_1 Walk-Forward / echter OOS-Split | ✅ | IS 2018-22 / OOS 2023-26, Rangfolge nur auf IS |
| p6_2 Monte-Carlo der Trade-Sequenz | ✅ **neu** | unten |
| p6_3 Kosten-Sensitivitaet bis Breakeven | ✅ **neu** | unten |
| p6_4 mehrere Jahre / Regime | ⚠️ **neu** | unten — 2 von 4 OOS-Jahren negativ |
| p6_5 Kosten gemessen je Broker | ✅ | `research_ou_broker_costs.py`, 19.09. |
| p6_6 Ausfuehrungs-Lag simuliert | ✅ | Einstieg Folgetag statt Signalschluss |
| p6_7 Sizing-Nenner / Hebelverteilung | ✅ **neu** | unten |
| p6_8 Stop gegen Round-Trip-Kosten | ✅ **neu** | unten |

## Die richtige Risikoscheibe zuerst

Der erste Monte-Carlo-Lauf rechnete mit 1 % Risiko je Trade und ergab
Bein-Drawdowns von 6,5 % mit **P(DD > 7 %) = 43 %** — das haette geheissen: auf
einem TTP-Konto mit 7-%-Deckel unbrauchbar. Die Zahl war in der falschen
Einheit. Live gilt:

| | Formel | Risiko je Trade |
|---|---|---|
| FK (TTP) | `account.capital_weight 1/6 x LEG_RISK_PCT 0,01` | **0,167 %** |
| EK (Tickmill) | `CAPITAL_WEIGHT 1/8 x LEG_RISK_PCT 0,0293` | **0,366 %** |

EK faehrt das Bein also mit gut dem Doppelten des FK-Risikos. Die
Kapitalverduennung auf EK ist seit 2026-09-10 scharf geschaltet — und zwar
INNERHALB von `core/sizing.py::calc_lot_size_detailed()`, nicht an den
Aufrufstellen. Wer nur die Aufrufstelle liest, nennt eine um Faktor 8 falsche
Risikozahl (laut Memory bereits zweimal passiert).

## p6_2 Monte-Carlo der Trade-Sequenz (Block-Bootstrap, 5.000 Pfade)

Circular Block-Bootstrap mit Bloecken von 10 Trades — Bloecke statt
Einzeltrades, damit Gut- und Schlechtphasen zusammenhaengend bleiben. Genau die
Sequenzabhaengigkeit, die ein Konto mit Drawdown-Deckel umbringt. Equity je
Pfad: `equity *= (1 + Risiko x R)`, mit den echten Live-Risikogroessen oben.

| | Zeitraum | Ergebnis Median | P05 | Pfade negativ | MaxDD Median | MaxDD P95 | worst |
|---|---|---|---|---|---|---|---|
| FK | OOS 2023-26 | **+0,57 %** | -1,49 % | 32 % | -1,10 % | -2,31 % | -4,41 % |
| FK | gesamt 2018-26 | +0,83 % | -2,56 % | 34 % | -1,95 % | -3,98 % | -7,63 % |
| EK | OOS 2023-26 | **+1,88 %** | -2,61 % | 25 % | -2,28 % | -4,59 % | -8,56 % |
| EK | gesamt 2018-26 | +3,37 % | -4,40 % | 23 % | -3,87 % | -7,84 % | -13,97 % |

**P(DD > 7 %) auf FK = 0,00 %** ueber den OOS-Zeitraum, ueber den Gesamtzeitraum
P(DD > 4 %) = 4,9 %. Die TTP-Grenze ist also nicht in Gefahr — das Bein ist bei
dieser Risikoscheibe harmlos.

Es ist aber auch fast wirkungslos: **+0,57 % ueber 3,7 Jahre** auf FK, und ein
Drittel der Pfade endet trotzdem im Minus. Auf EK mit dem doppelten Risiko
+1,88 % bei 2,3 % typischem Drawdown — ein Calmar von etwa 0,2.

## p6_3 Kosten-Sensitivitaet bis zum Breakeven

| Einstiegskosten | 0 | 8,4 | **16,9 (heute FK)** | 25 | 34 | 50 | 70 bps |
|---|---|---|---|---|---|---|---|
| Ø R | +0,017 | +0,011 | **+0,006** | +0,001 | -0,005 | -0,015 | -0,027 |

| Swap je Tag | 0 | **1,71 (heute)** | 2,5 | 3,5 | 5,0 | 7,0 bps |
|---|---|---|---|---|---|---|
| Ø R | +0,019 | **+0,006** | 0,000 | -0,007 | -0,019 | -0,033 |

**Der Puffer ist duenn.** Breakeven liegt bei rund 25,5 bps Einstiegskosten
(heute 16,9) und bei 2,5 bps Swap je Tag (heute 1,71). Es vertraegt also etwa
**50 % hoehere Spreads ODER 46 % hoeheren Swap** — nicht beides. Ein
Swap-Anstieg auf 9 % p.a. (heute 6,24 %) killt das Bein allein. Auf EK ist der
Puffer entsprechend groesser, weil der Spread dort halb so hoch ist.

## p6_4 Jahresaufriss der empfohlenen Konfiguration

Ø R je Signaljahr (FK-Kosten, Trades in Klammern):

| 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| -0,054 (109) | +0,060 (110) | -0,027 (83) | +0,049 (129) | -0,111 (27) | **-0,033 (98)** | **-0,015 (126)** | +0,053 (108) | +0,030 (89) |

**Das ist die Schwachstelle der Empfehlung.** Der positive OOS-Schnitt von
+0,008R stammt vollstaendig aus 2025 und 2026 — **2023 und 2024 sind auch mit
der neuen Konfiguration negativ**. Vier OOS-Jahre, davon zwei im Minus, zwei im
Plus. Das ist kein "funktioniert ueber Regime hinweg", das ist "die letzten
beiden Jahre waren gut". Die Konfiguration ist nachweislich besser als die
heutige (die in ALLEN vier OOS-Jahren verliert), aber sie ist nicht regimefest.

## p6_7 Sizing-Nenner und Hebel

Der Live-Bot sized auf `|Live-Kurs - SL|`, die Verteilung entscheidet also:

| | Median | P05 |
|---|---|---|
| Stopdistanz | 16,9 % | 7,4 % |
| Nominal je Trade | **0,06x Konto** | P95 0,13x |

Bei 3 Sigma waeren es 0,16x Median. Die 8-Sigma-Konfiguration halbiert den
Hebel also noch einmal — Margin ist bei diesem Bein kein Thema mehr, und der
Tail-Schaden eines Gaps ueber den Stop faellt entsprechend (schlechtester Trade
-0,90R statt -2,54R).

## p6_8 Stop gegen Round-Trip-Kosten

| | Round-Trip Median | Stop in Vielfachen davon | Anteil < 3x |
|---|---|---|---|
| FK | 45,8 bps | **41x** | **0,00 %** (n=0) |
| EK | 38,4 bps | 50x | 0,00 % |

Der Punkt, an dem `cls_practical` am 2026-09-09 gescheitert ist (Stops so eng,
dass die Kosten einen relevanten Teil des Risikobudgets fraßen), existiert hier
nicht — kein einziger Trade hat einen Stop unter dem Dreifachen der
Round-Trip-Kosten. Mit der alten 3-Sigma-Konfiguration waere der Stop bei 15x
gelegen, also ebenfalls unkritisch; dieser Punkt war nie das Problem des Beins.

## Phase-6-Fazit

Die Empfehlung **besteht** die Robustheitspruefung in dem Sinn, dass sie nicht
gefaehrlich ist: kein Deckelrisiko auf FK, kein Hebelproblem, kein
Kosten-Stop-Missverhaeltnis, und die Sequenzrisiken sind klein. Sie besteht sie
**nicht** in dem Sinn, dass ein verlaesslicher Edge nachgewiesen waere: zwei von
vier OOS-Jahren negativ, ein Drittel der Monte-Carlo-Pfade negativ, Kostenpuffer
rund 50 %, Ertrag +0,57 % (FK) bzw. +1,88 % (EK) ueber 3,7 Jahre.

Ehrliche Lesart: **das Bein ist mit dieser Konfiguration von "verliert
zuverlaessig" auf "kostet nichts mehr" gehoben, nicht auf "verdient Geld".**
Ob es das Betriebsrisiko (MNST-Split, verwaiste Positionen, Signaldatum-Drift —
alles reale Vorfaelle der letzten vier Wochen) und den Platz im Risikobudget
wert ist, ist eine Portfolio-Entscheidung, keine Backtest-Frage mehr.
