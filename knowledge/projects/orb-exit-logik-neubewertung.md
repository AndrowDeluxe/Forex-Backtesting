# Project: ORB Exit-Logik (SL/TP/Break-Even) mit realen Kosten neu bewertet

**Ziel**: Nutzerauftrag 2026-09-19 -- "schaue ob wir mit den realen Daten und
Kosten nochmal an der SL, TP und BE Logik arbeiten sollten um das Edge
profitabler zu gestalten."

**Status**: **UMGESETZT am 2026-09-21** (Nutzerfreigabe). Variante C laeuft auf
allen vier Konten -- greift ab dem ersten Handelstag NACH der Umstellung, die
am 21.09. bereits gelegten Orders trugen noch das alte Schema.
Geaendert: `challenge_portfolio/paper_bot.py`, `fk_instant_funding/paper_bot.py`,
`EK-Portfolio-Bridge/config.py`, `ek_portfolio/paper_bot.py` (Paper),
`app_pages/ny_open_orb_portfolio.py`. Risiko/Sizing je Konto unveraendert.

**Empfehlung**: Variante C (siehe unten) -- gleiches Risiko je Trade, gleicher
Tail-Drawdown wie heute, **+71 % Ergebnis**.

## Warum die alte Entscheidung ueberhaupt neu zu pruefen war

Der Stage-6-Teilausstieg (seit 2026-08-27 Standard, siehe
[[ny-open-orb-sp500]]) wurde unter zwei Annahmen validiert, die seitdem BEIDE
widerlegt sind:

1. **Ohne reale Kosten.** Spreads/Slippage waren mit 0 modelliert; gemessen
   sind es SP500 0,84 / US30 0,48 / NASDAQ 0,54 bps
   (`scripts/measure_broker_spreads.py`).
2. **Mit Marktorder-Einstieg.** Seit 2026-09-17 laeuft der Einstieg als
   ruhende Stop-Order am Level (PF 1,36 statt 0,80, siehe
   [[realkosten-und-ausfuehrungs-probe]]). Der Einstiegspreis -- und damit
   jedes R-Vielfache -- ist ein anderer.

## Methode

- `scripts/research_orb_exit_grid.py`: 396 Kombinationen je Instrument
  (Stop 0,4-1,0 ATR x Ziel 2-6R/keins x Teilausstieg 1,0-3,0R/keiner x BE
  an/aus), 2019-2026, Stop-Order-Entry, gemessene Spreads,
  Einstiegs-Slippage 0,45 bps (= Mittel der fuenf ECHTEN Fills vom 17./18.09.).
- `scripts/research_orb_exit_candidates.py`: Kandidaten mit Bootstrap
  (2.000 Ziehungen), IS/OOS-Trennung (Schnitt 2022-12-31), Jahresstabilitaet.
- `scripts/research_orb_exit_portfolio.py`: Portfolio-Sicht ueber alle drei
  Beine + "Summe R bei gleichem Drawdown".
- `scripts/research_orb_exit_montecarlo.py`: **Phase 6** -- 3.000 Pfade,
  Block-Bootstrap ueber KALENDERMONATE (nicht ueber Einzeltrades: das wuerde
  die Verlust-Cluster zerstoeren und den Drawdown systematisch zu klein
  schaetzen).

## Befund 1: Teilausstiege kosten Edge, je frueher desto mehr

Mittel ueber alle Gitter-Kombinationen (Ø R gesamt / out-of-sample):

| Teilausstieg bei | SP500 | US30 | NASDAQ |
|---|---|---|---|
| keiner | +0,366 / +0,166 | +0,336 / +0,142 | +0,192 / +0,147 |
| 1,0R | +0,148 / +0,029 | +0,134 / +0,004 | +0,037 / −0,008 |
| 2,0R | +0,252 / +0,106 | +0,228 / +0,093 | +0,096 / +0,055 |
| 3,0R | +0,310 / +0,132 | +0,281 / +0,144 | +0,140 / +0,100 |

Monoton in allen drei Instrumenten und in beiden Haelften. Das ist dasselbe
Muster wie bei CLS ([[cls-practical-kostenvalidierung]]) und beim OU-Modell
([[ou-modell-kostenvalidierung]]): **Mechanismen, die frueh Gewinn
festschreiben, schneiden genau die Trades ab, die den Edge tragen.**

## Befund 2: Break-Even ist ein Drawdown-Werkzeug, kein Ertragswerkzeug

Ø R ohne BE ist hoeher (SP500 +0,263 vs. +0,243; US30 +0,250 vs. +0,208;
NASDAQ +0,115 vs. +0,089). **Aber:** schaltet man NUR den BE ab und laesst
alles andere wie heute, steigt der Drawdown ueberproportional -- bei gleichem
Drawdown steht diese Variante **schlechter** da als der Ist-Zustand (−10 %).
Der BE wird erst dann verzichtbar, wenn der Teilausstieg ohnehin spaet kommt
oder entfaellt. Isoliert abschalten waere ein Fehler.

## Befund 3: Weite Ziele schlagen nahe -- aber nicht ueberall "gar kein Ziel"

6R > 5R > 4R > 3R > 2R, durchgehend. NASDAQ ist ohne Ziel am besten (Live-Stand).
**US30 vertraegt "kein Ziel" NICHT**: out-of-sample −0,101R bei −41,9R
Drawdown, der einzige echte Ausreisser im Feld. Eine einheitliche Konfiguration
fuer alle drei Instrumente waere die falsche Vereinfachung.

## Befund 4: Der Stop ist die unwichtigste Schraube -- 0,6 ATR bleibt

Die Flaeche zwischen 0,4 und 0,6 ATR ist flach (SP500 +0,248/+0,264/+0,304),
erst ab 0,7 wird es schlechter. Das Gitter mag 0,4 leicht lieber.
**Bewusst NICHT uebernommen:** bei 0,4 ATR liegt der NASDAQ-Stop nur noch
~7 bps entfernt, und die live gemessene Einstiegsabweichung von bis zu
1,03 bps (Durchbruch-Gap am 18.09.) frisst dann >15 % des Risikos. 0,6 hat den
groesseren Sicherheitsabstand gegen genau die Slippage, die wir gemessen haben.

## Entscheidungstabelle (Portfolio, alle 3 Beine)

| Variante | Ø R | OOS Ø R | MaxDD | Summe@gleichem DD | vs. heute |
|---|---|---|---|---|---|
| IST (live) | +0,198 | +0,100 | −40,6R | +464R | — |
| A: nur BE weg | +0,222 | +0,122 | −50,6R | +416R | **−10 %** |
| B: Teil 3R spaet, TP 6R, kein BE | +0,309 | +0,207 | −55,7R | +528R | +14 % |
| **C: gemischt** | **+0,337** | **+0,236** | −56,7R | +565R | +22 % |
| D: wie C, NASDAQ ohne Teilausstieg | +0,428 | +0,305 | −67,0R | +606R | +31 % |
| E: ueberall ohne Teilausstieg | +0,440 | +0,301 | −74,0R | +565R | +22 % |

**Phase 6 (Monte Carlo, 3.000 Pfade) kippt die Reihenfolge von C und D:**

| Variante | Summe R Median | MaxDD Median | **MaxDD 95 %** | Risiko-Skalierung | Ergebnis |
|---|---|---|---|---|---|
| IST (live) | +463 | −40,9R | **−67,4R** | 100 % | +463R |
| **C: gemischt** | +793 | −43,7R | **−67,7R** | **100 %** | **+789R (+71 %)** |
| D: NASDAQ ohne Teil | +999 | −54,4R | −83,6R | 81 % | +805R (+74 %) |

Der historische Einzelpfad liess C schlechter aussehen (−56,7R vs. −40,6R) --
**ueber 3.000 Pfade ist Cs Tail-Drawdown praktisch identisch mit dem heutigen**
(−67,7 vs. −67,4R). Der historische MaxDD des Ist-Zustands war eine
guenstige Ziehung. Genau dafuer ist Phase 6 da.

D liefert nur 3 Prozentpunkte mehr, verlangt dafuer aber eine Senkung des
Risikos je Trade auf 81 % (also eine zweite, unabhaengige Aenderung an allen
vier Konten). **Das ist den Aufwand und das zusaetzliche Umstellungsrisiko
nicht wert.**

## Empfehlung: Variante C

| Instrument | Stop | Ziel | Teilausstieg | Break-Even |
|---|---|---|---|---|
| SP500 | 0,6 ATR (unveraendert) | **6R** (statt 4R) | **keiner** (statt 2,0R) | **aus** |
| US30 | 0,6 ATR (unveraendert) | **6R** (statt 4R) | **3,0R** (statt 2,0R) | **aus** |
| NASDAQ | 0,6 ATR (unveraendert) | keins (unveraendert) | **3,0R** (statt 1,5R) | **aus** |

- **Risiko je Trade bleibt exakt wie heute** auf allen vier Konten.
- Tail-Drawdown bleibt auf heutigem Niveau, Ergebnis +71 %.
- Out-of-sample +0,236 statt +0,100 Ø R; alle 8 Jahre positiv.
- Umsetzung waere klein: `ORB_EXIT_CFG_BY_INSTRUMENT` in
  `challenge_portfolio/paper_bot.py`, `fk_instant_funding/paper_bot.py` und
  `EK-Portfolio-Bridge/config.py`. Die Stop-Order-Pfade lesen diese Config
  direkt -- ohne Teilausstieg legen sie automatisch EINE Order statt zwei.

## Offene Vorbehalte (ehrlich)

- **Ein Instrument bleibt mit Teilausstieg besser, zwei ohne** -- das ist
  keine saubere Regel, sondern eine je Instrument kalibrierte Entscheidung.
  Das Risiko, dass darin Anpassung an die Vergangenheit steckt, ist real; die
  IS/OOS-Trennung und die Jahresstabilitaet (8/8 positiv) sprechen dagegen,
  beweisen es aber nicht.
- **Die Live-Erfahrung mit dem neuen Einstieg ist zwei Handelstage alt.** Die
  0,45 bps Einstiegs-Slippage stammen aus fuenf echten Fills.
- **Nicht getestet:** Trailing-Stop, zeitbasierter Ausstieg (z. B. erste
  Stunde), Teilausstieg in mehreren Stufen.

## Verweise

- [[ny-open-orb-sp500]] -- Ursprungs-Strategie, Stage-6-Entscheidung
- [[realkosten-und-ausfuehrungs-probe]] -- Standardprozess fuer genau diese Art Probe
- `ny_open_orb/results/exit_grid_{SP500,US30,NASDAQ}.csv` -- vollstaendiges Gitter


## Nachtrag 2026-09-22: EK-Risiko nachkalibriert

Nutzerfrage "ist das EK Risiko nicht etwas klein?" -- ja, und zwar aus einem
Versehen: die MC-Kalibrierung vom 2026-09-10 enthielt ORB gar nicht
(`ek_v2_realistic_final.json`, `removed_strategies`: "keine Evidenz, dass der
Broker die noetigen Instrumente anbietet" -- gemeint war das alte
`orb_strategy`-Paket). ORB lief deshalb mit FKs Default: 0,042 % effektiv je
Instrument, rund 1/70 von gold_asb.

Nachgeholt mit `scripts/research_ek_orb_risk_calibration.py` (ORB frisch unter
Variante C, 6 Kernbeine, gemeinsames Fenster 2018-12-02..2026-07-28, MC 3.000
Pfade, Block-Bootstrap ueber Monate):

| ORB je Instrument | CAGR | hist. MaxDD | P(MaxDD>40 %) | Sharpe |
|---|---|---|---|---|
| 0,042 % (alt) | 237 % | -38,1 % | 33,9 % | 2,14 |
| **0,30 % (neu)** | **333 %** | -38,2 % | **24,1 %** | 2,45 |
| 0,40 % | 375 % | -38,3 % | 24,0 % | 2,53 |
| 0,75 % | 543 % | -38,7 % | 34,3 % | 2,62 |

**Mehr ORB senkt die Reissgefahr bis ca. 0,4-0,5 %** -- das Bein ist weitgehend
unkorreliert zu Gold/BTC/FX. Gewaehlt 0,30 %: statistisch gleichauf mit 0,40 %
(5 Startwerte, Spanne +/-2 Punkte), aber mitten in der flachen Mulde.

**Offen und separat zu entscheiden:** dieselbe Rechnung gibt fuer EKs
IST-Zustand 33,9 % Reissgefahr, dokumentiert sind 7,8 %. Nicht methodisch
erklaerbar (Block-Bootstrap 22,7 % vs. Tagespermutation 24,7 %). Siehe
DASHBOARD.
