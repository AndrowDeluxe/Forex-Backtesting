# Project: NY-Open Opening-Range-Breakout (SP500, M15-Range / M5-Entries)

**Ziel**: Eigene Strategie-Idee des Nutzers testen (kein Paper): erste M15-Kerze
nach dem NY-Cash-Open (09:30 America/New_York) auf SP500 bildet eine Opening
Range; vier verschiedene Entry-Mechaniken (Stop-Breakout, Limit-in-Range,
Breakout+Retest+Confirmation, M5-Fraktal-Reversal) und mehrere Exit-/Indikator-
Varianten (ATR-Stop, R-Vielfache inkl. ~4R, Range-Vielfache, Relative Volume
at Time, ADX-Filter) sollen verglichen werden.

**Status**: Abgeschlossen (Stage 1-5 + Phase 6 fuer SP500 + NASDAQ). Bestes
Gesamtergebnis: **3er-Portfolio SP500+US30+NASDAQ** (je eigene kalibrierte
Config, 0.6x-ATR/4R-Exit fuer alle drei), OOS-Sharpe 1.61, MaxDD -1.0%,
schlaegt jedes Einzelinstrument. Dashboard live unter
`app_pages/ny_open_orb_portfolio.py` ("NY-Open ORB Portfolio"). Die alte
`orb_strategy/`-Dashboardseite wurde entfernt (Stage 5a: risiko-gewichtete
Kombination schlaegt `ny_open_orb` allein nicht) - der Code
(`orb_strategy/pipeline.py`) bleibt im Repo, da historische Research-Skripte
ihn noch referenzieren, ist aber nicht mehr im Dashboard verlinkt.

**Prozess-Referenz**: Repo-Standard (8-Phasen-Checkliste), Phase 6 Robustheit
zwingend vor jeder "final"-Aussage oder Risk-Sizing.

## Strategie & Code-Basis

- Neues Paket `ny_open_orb/`: `data.py` (SP500 M15/M5 via
  `combined_strategy.data.fetch_timeframe`, DST-sicher `.tz_convert("America/New_York")`),
  `range.py` (Opening-Range-Berechnung, `range_bars` Parameter), `indicators.py`
  (neuer **Relative Volume at Time**-Indikator: Volumen ./. rollierendem
  Durchschnitt am SELBEN Zeitfenster (HH:MM) der letzten N Tage - anders als
  die bereits vorhandene, zeitpunkt-blinde `volume_ratio` in
  `orb_strategy/pipeline.py`), `engine.py` (vier Entry-Mechaniken +
  gemeinsamer Exit-Simulator).
- Wiederverwendet statt neu gebaut: `gold_smc_htf_ltf/structure.py::detect_fractal_swings(k=2)`
  fuer den M5-Fraktal, `strategy/indicators.py::compute_adx` fuer ATR/ADX,
  die Breakout->Retest->Confirmation-Tagesschleifen-Struktur aus
  `scripts/research_london_range_bos_retest.py::simulate()`.
- Vier Entry-Typen in `engine.py` (Details siehe Modul-Docstring):
  `stop_breakout`, `confirmed_retest`, `limit_in_range`, `fractal_reversal`
  (letzterer bar-fuer-bar kausal: feuert nur, wenn zum Zeitpunkt des
  Fraktal-Signals noch KEIN bestaetigter Bruch stattgefunden hat - nicht
  "den ganzen Tag nie gebrochen").

## Stage 1 -- Reine Range-Mechanik (`scripts/research_ny_open_orb_stage1_structure.py`)

Volle Historie 2016-07-28 bis 2026-07-28, SP500, beide `range_bars`-Varianten
(1 = 15-Min-Range, 2 = 30-Min-Range):

- **Die Range wird an ~99,9% aller Handelstage irgendwann per Bodyclose
  gebrochen** (broke_up + broke_down + broke_both). "Den ganzen Tag nur
  angetestet, nie gebrochen" (`tested_only`/`stayed_inside`) ist mit
  0,1-0,9% praktisch nicht existent - ueber einen vollen ~6,5h-Handelstag
  bewegt sich SP500 fast immer weiter als eine 15- oder 30-Min-Opening-Range.
  **Konsequenz**: `fractal_reversal`s bar-fuer-bar-kausale Definition ("noch
  kein Bruch BISHER, nicht den ganzen Tag") ist die einzig sinnvolle - eine
  ganztaegige "nie gebrochen"-Bedingung haette praktisch keine Signale
  geliefert.
- **~35-46% aller Tage sind "broke_both"** (Range wird in beide Richtungen
  gebrochen, choppy) - haeufiger bei der 15-Min-Range (46%) als bei der
  30-Min-Range (34%). Relevant fuer `stop_breakout`/`confirmed_retest`:
  viele Tage duerften Whipsaws produzieren, nicht saubere Ein-Richtungs-Trends.
  In `engine.py` bereits beruecksichtigt: ein Bar, der beide Levels
  gleichzeitig kreuzt, wird uebersprungen (nicht erzwungen in eine Richtung).
- Aufteilung up/down-Bruch ist ueber alle Jahre relativ stabil (~grob 50/50,
  leichter Overhang Richtung "broke_up" seit 2016 - passt zum strukturellen
  Bullenmarkt-Bias von SP500, den auch `orb_strategy/pipeline.py`s
  Long-only-Filter-Befund schon zeigt).
- Range-Breite waechst deutlich mit den Jahren (Median 15-Min-Range: ~4-7 Pkt
  2016-2019, ~10-20 Pkt 2022-2026) - reiner Preis-/Volatilitaets-Level-Effekt,
  kein Regimewechsel-Signal per se, aber wichtig fuer ATR-basierte
  Stop-Skalierung (bereits ueber M15-ATR statt fixer Punktzahl geloest).

## Stage 2 -- Entry-Vergleich (`scripts/research_ny_open_orb_stage2_entries.py`)

IS/OOS-Split bei 2021-07-28 (identisch zu `app_pages/orb_strategy.py`s
`SPLIT_DATE`, gleicher SP500/2016-2026-Datensatz), Default-Exit (ATR-Stop
1.5x, Target 4R) fuer alle vier Typen:

- **`stop_breakout` (15-Min-Range) ist der klare Spitzenreiter**: Sharpe
  IS 0.28 -> OOS 0.84 (wird BESSER, nicht schlechter, out-of-sample - ein
  gutes Robustheitssignal, auch wenn Phase 6 noch pruefen muss, ob das nur
  ein guenstiges 2021-2026-Regime ist). PF 1.21 OOS, CAGR 5.1%.
- **`limit_in_range` ist in 3 von 4 IS/OOS x range_bars-Kombinationen
  negativ** (u.a. OOS Sharpe -0.15 bei 15-Min, komplett negativ bei
  30-Min-Range) - reine Range-Fade-Wette ohne echte Unterstuetzungs-/
  Widerstandslogik hat hier keinen belastbaren Edge. **Nicht weiter verfolgt.**
- `confirmed_retest` und `fractal_reversal`: durchwachsen (IS negativ, OOS
  leicht positiv bei 15-Min) - marginal, in Stage 3 mit Filtern weiter
  untersucht statt vorschnell verworfen.
- 15-Min-Range (`range_bars=1`) schlaegt durchgehend die 30-Min-Range fuer
  `stop_breakout` (OOS Sharpe 0.84 vs. 0.73) - alle weiteren Stages nutzen
  `range_bars=1`.

## Stage 3 -- Exit-/Indikator-Grid (`scripts/research_ny_open_orb_stage3_exits_indicators.py`)

Alle Zahlen OOS (>=2021-07-28), 15-Min-Range:

- **Bester `stop_breakout`-Fund: ATR-Stop 1.0x + Target 4R -> Sharpe 0.95,
  PF 1.23, Win 25.3%, CAGR 4.1%, MaxDD -6.2%** (Target 6R fast gleichwertig:
  Sharpe 0.90, aber hoehere CAGR 4.7%). Ein engerer Stop (1.0x statt 1.5x
  ATR) schlaegt hier den weiteren - anders als man bei einer reinen
  Breakout-Strategie evtl. erwarten wuerde.
- **ADX-Filter hilft hier NICHT** (adx_min=25 senkt Sharpe von 0.84 auf 0.51) -
  ein bemerkenswerter Gegensatz zu `orb_strategy/pipeline.py`s bestaetigtem
  Fund (ADX>=25 verbessert DIESE andere ORB-Definition auf SP500/Nasdaq
  deutlich). Die beiden ORB-Konzepte (Tages-ATR-Schwelle vs. erste
  15-Min-Kerze) reagieren also gegensaetzlich auf denselben Filter -
  nicht einfach auf einander uebertragbar.
- **RVOL@Time-Filter/-Exit hilft ebenfalls NICHT** fuer `stop_breakout` (Sharpe
  faellt von 0.84 auf 0.23-0.33 mit steigendem Schwellwert) - der neue
  Indikator bringt hier keinen Mehrwert, weder als Entry-Filter noch als
  Early-Exit. Ehrlicher Negativbefund, kein Bug (Code separat verifiziert).
- **Struktureller Stop (Gegenseite der Range) ist fuer `stop_breakout`
  SCHLECHTER** als der ATR-Stop (Sharpe 0.36-0.64 statt bis 0.95) - die
  Range-Breite ist als Stop-Distanz zu weit.
- **Fuer `confirmed_retest` dreht sich das um**: struktureller Stop ist hier
  der BESTE Ansatz (Sharpe 0.60-0.66, Win-Rate 42-44%) - der Entry liegt
  bereits jenseits des Levels, daher passt "Gegenseite der Range" hier als
  Stop besser. Bestes ATR-Stop-Ergebnis: 2.0x ATR + Target 3R (Sharpe 0.73).
  Insgesamt aber schwaecher als `stop_breakout`s bestes Ergebnis.
- `fractal_reversal`: bestenfalls Sharpe ~0.51-0.54 (Target 6R oder
  4x Range-Breite), RVOL-Filter verschlechtert es sogar deutlich
  (Sharpe bis -0.72) - duenner, filter-empfindlicher Edge, nicht als
  primaerer Kandidat geeignet.

**Gewaehlter Kandidat fuer Phase 6**: `stop_breakout`, `range_bars=1`,
`stop_atr_mult=1.0`, `target_mode="r_multiple"`, `target_r_mult=4.0`,
keine ADX-/RVOL-Filter.

## Phase 6 -- Robustheit: Befunde (`scripts/research_ny_open_orb_phase6.py`)

Kandidat: `stop_breakout`, `range_bars=1`, `stop_atr_mult=1.0`,
`target_mode="r_multiple"`, `target_r_mult=4.0`, keine Filter.

- **p6_1 (Walk-Forward, 3 unabhaengige ~3-Jahres-Perioden)**: 2016-2019
  Sharpe **0.10** (PF 1.02, praktisch flach) -> 2019-2022 Sharpe 0.43 (PF 1.10)
  -> 2022-2026 Sharpe **0.95** (PF 1.24). **Der Edge ist regimeabhaengig, kein
  stabiler All-Weather-Effekt**: er existiert im Wesentlichen erst ab 2020/2022,
  in der ruhigeren 2016-2019-Periode ist praktisch nichts da. Das erklaert
  auch, warum der Stage-2/3-OOS-Split (ab 2021-07-28) so stark aussah - dieser
  Zeitraum ueberschneidet sich groesstenteils mit der starken 2022-2026-Periode.
  **Konsequenz**: die OOS-Bestaetigung aus Stage 2/3 ist real, aber teilweise
  guenstig durch die Wahl des Split-Datums - keine unabhaengige Bestaetigung
  ueber alle Marktregime hinweg.
- **p6_2 (Monte Carlo, block_size=20, n_sims=2000, seed=42, auf OOS-Trades
  2021-2026)**: Median-Sharpe 0.97 (deckt sich mit dem tatsaechlichen 0.95 -
  kein Sequencing-Gluecksfall), P(MaxDD>10%)=4%, P(MaxDD>20%)=0%. Wichtiger
  Vorbehalt (siehe `monte_carlo.py`s eigene Dokumentation): das reshuffelt nur
  die BEREITS BEOBACHTETE 2021-2026-Renditeverteilung - es sagt nichts darueber,
  ob ein zukuenftiges Regime eher wie 2022-2026 (stark) oder wie 2016-2019
  (flach) aussieht.
- **p6_3 (Cost-Sweep, OOS)**: Breakeven-Spread ~2.6bps (Round-Trip) gegen
  angenommene 0.5bps -> **Sicherheitsfaktor 5.3x**. Solide Kostenmarge fuer
  ein Index-CFD.
- **p6_4 (Jaehrliche OOS-Aufschluesselung)**: 2021 Sharpe 1.51, 2022 Sharpe
  1.57, 2023 Sharpe **-0.07** (flach), 2024 Sharpe 1.22, 2025 Sharpe 1.10,
  2026 (Teiljahr) Sharpe **-0.58**. 4 von 6 Jahren positiv, aber 2023 und
  2026 zeigen: auch innerhalb der "guten" 2021-2026-Periode gibt es echte
  Verlustjahre, kein Selbstlaeufer.

### Stage 4b -- Regime-Filter (`scripts/research_ny_open_orb_stage4b_regime.py`, volle Historie ausser VIX)

- **ADR-Regime (relativ zum eigenen 60-Tage-Median) dreht die naive Erwartung
  um**: `low_adr`-Tage sind BESSER (Sharpe 0.76, PF 1.26) als `high_adr`-Tage
  (Sharpe 0.14). Nicht dasselbe wie "die 2020er sind eine hohe-Vola-Ara" aus
  Phase 6 - ADR misst hier taggenau relativ zu den letzten ~3 Monaten, nicht
  relativ zur gesamten Historie. Interpretation: ein Tag, der schon relativ
  zu seiner juengeren Vergangenheit ungewoehnlich weit/choppy ist, produziert
  eher Whipsaws als einen sauberen Breakout; ein ruhigerer Tag liefert eher
  einen cleanen Ausbruch.
- **VIX-Regime (nur ab 2022-10-04 testbar) hilft NICHT**: sowohl `high_vix`
  (Sharpe 0.52) als auch `low_vix` (Sharpe 0.55) sind schwaecher als die
  ungefilterte Baseline auf demselben Fenster (Sharpe 0.98) - eine einfache
  Median-Spaltung des VIX traegt hier keine nutzbare Information.
- **Staerkster Einzelfund dieser Stage: EMA-Ribbon-Trend "neutral"** (aus
  `strategy/mtf_ema_ribbon.py`, unveraendert wiederverwendet): wenn der
  4H/1D/1W-EMA-Stack UNEINDEUTIG ist (weder klar bullish noch bearish),
  **Sharpe 0.56 -> 1.05, PF 1.13 -> 1.45** (volle 2016-2026-Historie, n=901).
  Sowohl "mit Trend" (Sharpe -0.20) als auch "gegen Trend" (Sharpe -0.16)
  sind NEGATIV. Gegenintuitiv, aber plausibel: bei bereits etabliertem
  HTF-Trend ist der ORB-Breakout oft nur eine verlaengerte, bereits erschoepfte
  Bewegung; bei unklarem HTF-Bild ist der Opening-Range-Ausbruch eher eine
  echte neue Initiative mit Platz zum Laufen.
- **Kombiniertes ATR x ADR x RVOL-Grid**: bester Einzelfund
  `ATR=high_atr x ADR=low_adr x RVOL=high_rvol` -> PF 1.73 (n=279, duenner
  als der EMA-Filter). Alle anderen 7 Kombinationen schwach bis negativ -
  kein robustes 3-Wege-Muster, eher ein Nischen-Setup.

### Stage 4b2 -- Long-only + EMA-neutral kombiniert, erneuter Walk-Forward (`scripts/research_ny_open_orb_stage4b2_combined_walkforward.py`)

| Config | 2016-2019 Sharpe | 2019-2022 Sharpe | 2022-2026 Sharpe | Full Sharpe | Full PF | Full MaxDD | n (10J) |
|---|---|---|---|---|---|---|---|
| Baseline | 0.10 | 0.43 | 0.95 | 0.56 | 1.13 | -9.7% | 2570 |
| Long-only | 0.26 | 0.89 | 1.04 | 0.81 | 1.30 | -4.7% | 1316 |
| EMA-neutral | 0.26 | 1.34 | 1.24 | 1.05 | 1.45 | -4.1% | 901 |
| **Beide kombiniert** | **0.21** | **1.46** | **0.95** | **0.97** | **1.64** | **-3.1%** | **452** |

**Ehrlicher Befund**: Die Kombination verringert die 2016-2019-Schwaeche
(0.10 -> 0.21), **behebt sie aber nicht** - 2016-2019 bleibt mit Abstand die
schwaechste Periode, egal welche Filterkombination. Was sich massiv
verbessert, ist alles andere: Full-Sharpe fast verdoppelt (0.56->0.97),
PF deutlich besser (1.13->1.64), **MaxDD auf ein Drittel reduziert**
(-9.7%->-3.1%), und 2019-2022 wird zur staerksten Periode ueberhaupt
(Sharpe 1.46, PF 2.13). Kosten: Tradezahl faellt von 2570 auf 452 (10 Jahre,
~45/Jahr) - naeher an der bestehenden `orb_strategy`-Config (123 Trades in
5 Jahren OOS) als an der urspruenglichen NY-Open-ORB-Rohversion, aber
immer noch eine brauchbare Stichprobe.

**Neue fuehrende Config**: `stop_breakout`, `range_bars=1`, **long-only**,
**EMA-Ribbon-Bias neutral** (`strategy/mtf_ema_ribbon.py`, unveraendert),
ATR-Stop 1.0x, Target 4R. Ersetzt ab hier die Stage-2/3-Rohversion als
Basis fuer Stage 4c-4e.

### Phase 6b -- Robustheit der gefilterten Config (`scripts/research_ny_open_orb_phase6b_filtered_robustness.py`)

Trotz deutlich weniger Trades (242 statt 1287 OOS) **robuster**, nicht
fragiler, als die Rohversion:

- **Monte Carlo (OOS)**: Median-Sharpe 1.01 (deckt sich mit dem Ist-Wert),
  P(MaxDD>5%)=0.6%, **P(MaxDD>10%)=0%** (Rohversion hatte noch 4%) - das
  Tail-Risiko ist praktisch weg.
- **Cost-Sweep**: Breakeven-Spread ~4.7bps (statt 2.6bps) ->
  **Sicherheitsfaktor 9.4x** (statt 5.3x) - fast doppelt so viel Kostenpuffer,
  weil die verbliebenen Trades im Schnitt hoehere Qualitaet haben.

### Stage 4d -- SL/TP/Breakeven-Feinabstimmung (`scripts/research_ny_open_orb_stage4d_sl_tp_be.py`, auf der gefilterten Config)

- **Breakeven-Setzung schadet durchgehend**, unabhaengig von Trigger-Level
  oder Stop-/Target-Kombination (z.B. target=4R: Sharpe 1.02 ohne BE ->
  0.44 mit be_trigger=1.0R). Erklaerung: das ist eine Low-Winrate/High-R-
  Strategie (Gewinnrate ~25-31%, Ziel 4R) - fruehes Breakeven schneidet
  genau die grossen Gewinner ab, von denen die Strategie lebt, noch bevor
  sie das Ziel erreichen. **Keine Breakeven-Logik fuer diese Config.**
- **Noch engerer Stop (0.6x ATR statt 1.0x) ist leicht besser**: Sharpe 1.05,
  PF 1.63, MaxDD nur -1.1%. Nicht als neue Empfehlung uebernommen (zu nah am
  Rand eines 5er-Grids, Risiko einer Zufalls-Feinjustierung), aber als
  brauchbarer Bereich (0.6x-1.0x) dokumentiert statt eines einzelnen Werts.
- **target=4R bestaetigt sich als echtes lokales Optimum**, nicht nur "je
  hoeher desto besser": 3.5R (Sharpe 0.89) und 4.5R (0.78) sind beide
  schwaecher als 4.0R (1.02).

### Datenbefund: dukascopy_python-Bibliotheksfehler bei sehr langen M1/M5-Requests

Ein einzelner `dukascopy_python.fetch()`-Aufruf ueber 10 Jahre M1/M5 wirft
manchmal `KeyError: 0` tief in der Bibliothek (`_stream()`s Cursor-Tracking,
nicht in unserem Code) - reproduziert u.a. bei NASDAQ M5 2016-2026. Jahresweise
gestueckelte Requests (`ny_open_orb/data.py::_fetch_chunked_by_year`, verankert
am `start`-Datum selbst, nicht an Kalenderjahren) umgehen das zuverlaessig.
Bewusst NUR in `ny_open_orb/data.py` gefixt, nicht in der von vielen anderen
Strategien genutzten `combined_strategy/data.py`, um deren Verhalten nicht
anzufassen. **Nachtrag**: das Chunking allein reicht nicht immer (auch
einzelne Jahres-Chunks koennen intermittierend fehlschlagen, beobachtet bei
SP500 M5 nach vielen vorherigen erfolgreichen Aufrufen sowie bei US30) -
zusaetzlich `_fetch_with_retry` (bis zu 4 Versuche, kurzer Backoff) ergaenzt.

### Stage 4e -- NASDAQ & US30 (`scripts/research_ny_open_orb_stage4e_other_instruments.py`)

SP500-abgeleitete Config (`stop_breakout`, long-only, EMA-neutral) NICHT neu
kalibriert, nur auf anderen Instrumenten getestet (Generalisierungsfrage,
kein Fresh-Fit):

| Instrument | Sharpe roh (full) | Sharpe gefiltert (full) | Sharpe roh (OOS) | Sharpe gefiltert (OOS) |
|---|---|---|---|---|
| SP500 | 0.56 | 0.97 | 0.95 | 1.02 |
| **US30** | 0.45 | **1.01** | 0.24 | **0.70** |
| NASDAQ | 0.53 | 0.55 | 0.59 | **0.13** |

**US30 bestaetigt den Filter fast genauso stark wie SP500** (PF bis 1.69,
2019-2022 sogar PF 2.44) - spricht fuer einen echten, nicht SP500-spezifischen
Effekt auf "traditionellen" US-Blue-Chip-Indizes. **NASDAQ ist der klare
Ausreisser**: der Filter hilft kaum (full) und schadet deutlich OOS (0.59 ->
0.13). Ehrliche Interpretation: NASDAQs staerker/nachhaltiger trendende
Natur (Tech-Wachstum) bedeutet vermutlich, dass gerade die "klarer HTF-Trend"-
Tage, die der EMA-neutral-Filter herausfiltert, bei NASDAQ eher gute als
schlechte Tage fuer einen Breakout sind - der Filter ist nicht universell,
sondern SP500/US30-spezifisch. Fuer NASDAQ müsste eine eigene Stage 2/3/
Phase-6-Kalibrierung gemacht werden, nicht einfach die SP500-Filter uebernehmen.

### Stage 4f -- Kombination mit der bestehenden `orb_strategy/` (`scripts/research_ny_open_orb_stage4f_combine_with_orb_strategy.py`)

- **Korrelation der taeglichen Renditen ist sehr niedrig** (0.045 voll,
  0.029 OOS) - nur 14.2% Tage-Ueberlappung. Die beiden ORB-Konzepte
  (Tages-ATR-Schwelle vs. erste-15-Min-Range) handeln tatsaechlich groesstenteils
  verschiedene Tage.
- **Trotzdem verschlechtert ein simples 50/50-Blend das Ergebnis** gegenueber
  der neuen Strategie allein: Sharpe 0.97->0.85 (voll), 1.02->0.66 (OOS).
  Grund: `orb_strategy`s eigener Sharpe (0.44 voll, 0.21 OOS) ist deutlich
  schwaecher - eine niedrige Korrelation reicht nicht aus, um das
  Verduennen der Rendite durch eine schwaechere Teilstrategie in einem
  GLEICHGEWICHTETEN Blend auszugleichen. **Ehrliches Ergebnis: kein
  naives Blending, die neue Strategie allein zu fahren ist hier besser.**
  Eine risiko-gewichtete statt gleichgewichtete Kombination koennte das
  aendern, wurde hier nicht weiter verfolgt (kein Auftrag dazu).

### Stage 5a -- Risiko-gewichtete (Inverse-Vol) Kombination (`scripts/research_ny_open_orb_stage5_risk_weighted_combo.py`)

Gewichte aus IS-Volatilitaeten (2016-2021) berechnet, fix auf OOS angewandt
(keine Gewichtsanpassung auf den Testdaten): `ny_open_orb=73%, orb_strategy=27%`
(ny_open_orb ist von Natur aus deutlich weniger volatil: 0.09%/Tag vs. 0.24%/Tag).

- **Risk-Parity schlaegt das naive 50/50 klar**: Full-Sharpe 0.72->0.94,
  OOS-Sharpe 0.55->0.86 - der Fix wirkt wie erwartet.
- **Aber: schlaegt immer noch nicht `ny_open_orb` allein, OOS.** Full-Zeitraum
  liegt der Risk-Parity-Blend knapp VOR der reinen neuen Strategie (Sharpe
  0.94 vs. 0.88) - aber **OOS (die ehrlichere Zahl) liegt `ny_open_orb`
  allein klar vorn** (Sharpe 1.05 vs. 0.86 im Blend, MaxDD -1.1% vs. -1.8%).
  **Fazit**: die Risiko-Gewichtung behebt das Verduennungsproblem des naiven
  Blends, aber `orb_strategy`s OOS-Qualitaet (Sharpe nur 0.21) ist selbst
  richtig gewichtet zu schwach, um die neue Strategie zu verbessern - sie
  allein zu fahren bleibt die bessere Wahl.

### Stage 5b -- 3er-Portfolio SP500+US30+NASDAQ vs. NASDAQ allein (`scripts/research_ny_open_orb_stage5b_portfolio_3instruments.py`)

Jedes Instrument mit seiner EIGENEN kalibrierten Config (SP500/US30:
long-only+EMA-neutral+0.6x/4R; NASDAQ: long+short+ohne Mittwoch+0.6x/4R).
Korrelationsmatrix (volle Historie): SP500-US30 0.59 (beide "klassische"
US-Blue-Chips, aehnlicher Mechanismus), **NASDAQ nur 0.29/0.20 mit den
anderen beiden** (strukturell andere Config: long+short statt long-only) -
echtes Diversifikationspotential, kein Zufall.

**Das 3er-Portfolio schlaegt NASDAQ allein, deutlich:**

| | Sharpe (voll) | Sharpe (OOS) | MaxDD (OOS) | CAGR (OOS) |
|---|---|---|---|---|
| NASDAQ allein | 1.30 | 1.33 | -2.1% | 4.4% |
| SP500 allein | 0.88 | 1.05 | -1.1% | 1.3% |
| US30 allein | 1.10 | 1.02 | -1.2% | 1.2% |
| **3er gleichgewichtet** | **1.52** | **1.61** | **-1.0%** | 2.3% |
| 3er Risk-Parity | 1.46 | 1.61 | -0.9% | 1.9% |

Gleichgewichtung und Risk-Parity liegen praktisch gleichauf (IS-Gewichte
42.6/37.3/20.2% sind ohnehin nicht extrem von Gleichgewichtung entfernt) -
die einfachere Gleichgewichtung reicht. **Klassischer Diversifikationseffekt**:
Sharpe/Calmar deutlich besser, Drawdown fast halbiert gegenueber NASDAQ
allein - Kosten dafuer ist eine niedrigere CAGR pro eingesetztem Kapital
(2.3% vs. 4.4%), da Kapital auf drei Beine statt eins verteilt wird (ein
Vol-Target-Overlay koennte das theoretisch wieder hochskalieren, hier nicht
getestet). **Empfehlung**: das 3er-Portfolio, nicht NASDAQ allein, ist das
beste Gesamtergebnis dieses Projekts.

### Stage 4c -- Ausfuehrungs-Timeframe M1/M5/M15 (`scripts/research_ny_open_orb_stage4c_entry_timeframe.py`, OOS 2021-2026)

| Timeframe | Sharpe roh | Sharpe gefiltert |
|---|---|---|
| M1 | 0.66 | 0.84 |
| M5 (bisherige Wahl) | 0.95 | 0.95 |
| M15 | **1.85** | **1.40** |

**Wichtiger methodischer Vorbehalt, KEINE Empfehlung zum Wechsel auf M15**:
die deutlich besseren M15-Zahlen sind hoechstwahrscheinlich ein
Backtest-Artefakt, kein echter Edge. Bei M15-Ausfuehrung werden Stop/Target
nur noch einmal pro 15-Minuten-Bar geprueft statt einmal pro 5 Minuten -
das uebersieht Intrabar-Reversals, die M5s feinere Aufloesung faengt (exakt
das Problem, das `research_orb_intrabar_stop.py` im Repo bereits als
Ursache fuer unrealistisch gute Backtests identifiziert hat, dort umgekehrt:
close-only vs. intrabar). M5 bleibt die vertrauenswuerdigere Wahl, auf der
die gesamte bisherige Forschung (Stage 2-4b) aufbaut. M1 ist tatsaechlich
schwaecher als M5 (plausibel: feinere Granularitaet faengt mehr
kurzlebige/verrauschte Breakouts, die M5 durch Zufall herausfiltert) -
konsistent, kein Artefakt-Verdacht.

Von vier getesteten Entry-Mechaniken ueberlebt eine klar (`stop_breakout`),
eine zweite ist ein schwaecherer Nebenkandidat (`confirmed_retest` mit
strukturellem Stop), eine ist durchgehend negativ (`limit_in_range`, verworfen)
und eine bleibt zu duenn (`fractal_reversal`). Wichtiger methodischer Fund:
Filter, die bei der ANDEREN ORB-Strategie im Repo (`orb_strategy/`) nachweislich
helfen (ADX>=25), helfen hier NICHT.

`stop_breakout` zeigt einen echten, kostenrobusten (5.3x Sicherheitsfaktor),
durch Monte Carlo bestaetigten Edge in der 2021-2026-Periode (Sharpe 0.95,
CAGR ~4%, MaxDD ~6%) - deutlich staerker als die bestehende, bereits
bestaetigte `orb_strategy/`-Config auf demselben Instrument/Zeitraum (OOS
Sharpe 0.21, CAGR 0.7%, aber nur 123 statt 1287 Trades). ABER: Phase 6s
Walk-Forward zeigt, dass dieser Edge **regimeabhaengig** ist und in der
ruhigeren 2016-2019-Periode praktisch nicht existierte - eher ein "hohe
Volatilitaet/breite Ranges"-Effekt (passt zu Stage 1s Befund stark
wachsender Range-Breiten seit 2020) als ein zeitloser struktureller Effekt.
Dieser Vorbehalt motiviert Stage 4 (unten) - erst dort wird versucht, ihn
gezielt zu adressieren, statt die 2021-2026-Zahl unkommentiert als
Erwartungswert zu praesentieren.

## Stage 4 -- Optimierung (Filter, Regime, Timeframes, SL/TP/BE, andere Instrumente, Kombination)

Motiviert durch Phase 6s Regime-Vorbehalt: gezielt nach einem Filter suchen,
der die 2016-2019-Schwaeche erklaert/behebt, plus breitere Parameteroptimierung.
Neue Bausteine: `ny_open_orb/filters.py` (Richtung/Wochentag/Stunde/generische
Serien-/Kategorie-Filter), `ny_open_orb/regime.py` (VIX-Regime, ADR,
EMA-Trend-Bias via `strategy/mtf_ema_ribbon.py`), `simulate()` erweitert um
`breakeven_trigger_r`, `find_entries()` um `entry_cutoff_minutes`. NASDAQ und
US30 neu in `combined_strategy/data.py` registriert (Dukascopy liefert beide
direkt: `INSTRUMENT_IDX_AMERICA_E_D_J_IND`, sowie VIX ueber
`INSTRUMENT_IDX_AMERICA_VOL_IDX_USD`).

**Datenbefund**: Dukascopys VIX-Instrument hat Historie erst ab **2022-10-04**
(verifiziert) - kein Zugriff auf VIX fuer 2016-2022. ADR (aus SP500s eigener
Preishistorie) deckt dagegen die volle Historie ab und dient als
Volatilitaets-Proxy fuer die fruehen Jahre.

### Stage 4a -- Filter & Timing (`scripts/research_ny_open_orb_stage4a_filters_timing.py`, OOS 2021-2026)

- **`range_bars=1` (15-Min) bleibt optimal** - Sharpe faellt monoton auf 0.61
  bei 45 Min, leichte Erholung auf 0.68 bei 60 Min, aber nie besser als 15 Min.
- **Long-only ist eine echte, gut motivierte Verbesserung**: Sharpe 0.95->1.01,
  PF 1.23->1.38, und **MaxDD fast halbiert** (-6.2%->-3.3%). Short-only ist
  schwach (Sharpe 0.30). Deckt sich mit `orb_strategy/pipeline.py`s eigenem,
  unabhaengig gefundenem Long-Bias-Effekt auf SP500/Nasdaq - zwei verschiedene
  ORB-Konzepte, dieselbe strukturelle Erklaerung (US-Index-Long-Bias).
- **Wochentag-Ausschluss "ohne Mittwoch" sieht stark aus** (Sharpe 0.95->1.15,
  PF 1.33) - "nur Mittwoch" ist isoliert sogar der einzige Verlust-Wochentag
  (Sharpe -0.35). **Aber**: das ist bisher nur auf dem OOS-Fenster gefunden,
  nicht wie bei `orb_strategy/pipeline.py`s Wochentag-Filter per IS-Ranking +
  OOS-Bestaetigung sauber getrennt - und stimmt nicht mit jener Strategie
  ueberein (die fand Montag fuer SP500 schwach, nicht Mittwoch). **Noch nicht
  uebernommen, bis separat IS/OOS geprueft** - klassisches
  Mehrfach-Test-Risiko (5 Wochentage durchprobiert = leicht ein zufaelliger
  Treffer).
- **Wochentag-Filter WIDERLEGT durch saubere IS/OOS-Trennung**
  (`scripts/research_ny_open_orb_stage4a2_weekday_validation.py`, long-only-Basis):
  IS-Ranking (2016-2021) findet Dienstag als schwaechsten Tag (PF 0.83) - aber
  OOS (2021-2026) ist "nur Dienstag" stark (PF 1.81!) und "ohne Dienstag"
  schlechter als die Baseline (Sharpe 0.73 vs. 1.01). **Lehrbuchbeispiel fuer
  das Mehrfach-Test-Risiko** aus Stage 4a's OOS-only-Scan (dort "ohne Mittwoch"
  gefunden) - kein Wochentag-Filter wird fuer diese Strategie uebernommen.
- **Entry-Stunden-Fenster/Cutoff aendern praktisch nichts** (Sharpe 0.95-0.96
  fuer 1h/2h/3h-Fenster und 60/120/180-Min-Cutoff) - fast alle Breakouts
  feuern ohnehin in der ersten Stunde nach Range-Ende (nur 3 Trades im
  gesamten OOS-Fenster nach 11:30 Uhr). cutoff=30min schneidet noch echte
  Signale ab (Sharpe faellt auf 0.84) - keine sinnvolle Restriktion unter
  60 Minuten.

## Fazit (Gesamtprojekt nach Stage 4)

**Finale Config**: `stop_breakout`, `range_bars=1` (15-Min-Range), **M5-Ausfuehrung**,
**long-only**, **EMA-Ribbon-Bias neutral** (`strategy/mtf_ema_ribbon.py`),
ATR-Stop 1.0x (0.6x-1.0x brauchbarer Bereich), Target 4R, **keine** Breakeven-
Logik, **kein** Wochentag- oder ADX-/RVOL-Filter (alle getestet, keiner haelt
sauberer IS/OOS-Pruefung stand bzw. verbessert nichts).

**Was sich bestaetigt hat**:
- SP500 full-Sharpe 0.56 -> 0.97, PF 1.13 -> 1.64, **MaxDD auf ein Drittel**
  (-9.7% -> -3.1%), Monte-Carlo-bestaetigt (P(MaxDD>10%)=0%), Cost-Sicherheitsfaktor
  9.4x.
- **US30 bestaetigt denselben Filter unabhaengig** (Sharpe 0.45 -> 1.01) -
  spricht fuer einen echten, nicht SP500-spezifischen Effekt auf klassischen
  US-Blue-Chip-Indizes.
- Long-Bias-Fund deckt sich mit dem unabhaengigen Fund der bestehenden
  `orb_strategy/` (beide ORB-Konzepte, gleiche strukturelle Erklaerung).

**Was NICHT haelt / offen bleibt**:
- Die 2016-2019-Regimeschwaeche ist **verringert, nicht behoben** (Sharpe
  dort bleibt bei ~0.2-0.3, deutlich unter 2019-2026). Diese Strategie ist
  kein all-wetter-taugliches System, sondern (bisher) am staerksten in
  Perioden mit klarerem HTF-Bild-Wechsel.
- **NASDAQ generalisiert NICHT** - eigene Kalibrierung noetig, SP500/US30-Filter
  nicht blind uebernehmen.
- **Naives 50/50-Blending mit der bestehenden `orb_strategy/` verschlechtert
  das Ergebnis** trotz sehr niedriger Korrelation (0.045) - die neue Strategie
  allein zu fahren ist hier besser als zu kombinieren.
- M15-Ausfuehrung sieht in den Rohzahlen am staerksten aus, ist aber
  hoechstwahrscheinlich ein Backtest-Artefakt (groebere Stop-Pruefung) -
  M5 bleibt die empfohlene Ausfuehrungs-Timeframe.
- Unterwegs entdeckter, dokumentierter Bug in der `dukascopy_python`-Bibliothek
  bei langen M1/M5-Requests, mit Chunking+Retry-Workaround in
  `ny_open_orb/data.py` behoben (nur dort, nicht in der gemeinsam genutzten
  `combined_strategy/data.py`).

**Naechste sinnvolle Schritte** (noch nicht gemacht): eigene Stage 2/3/Phase-6-
Kalibrierung fuer NASDAQ statt SP500-Filter zu uebernehmen; risiko-gewichtete
(statt gleichgewichtete) Kombination mit `orb_strategy/` pruefen; die
0.6x-1.0x-ATR-Stop-Bandbreite auf einem frischen/laengeren Zeitraum
gegenpruefen, bevor sie als "final" gilt.

**Verknuepfung**: [[gold-ctnl-edge-portfolio]] (Lehre zur Phase-6-Reihenfolge,
hier von Anfang an eingehalten - und Phase 6 hat tatsaechlich einen wichtigen
Regime-Vorbehalt aufgedeckt, den Stage 2/3 allein nicht gezeigt haetten;
Stage 4 hat ihn verringert, aber nicht vollstaendig aufgeloest - auch das
ehrlich stehen gelassen statt schoengeredet).

## NASDAQ-Kalibrierung (eigenstaendig, NICHT die SP500-Filter uebernommen)

Stage 4e zeigte, dass der SP500-Filter (long-only + EMA-neutral) auf NASDAQ
NICHT generalisiert (OOS Sharpe 0.59 -> 0.13). Deshalb eigene Kalibrierung
von Grund auf, analog zu SP500s Stage 2/3/4, statt den Filter blind zu
uebernehmen.

### `scripts/research_nasdaq_orb_stage2_entries_exits.py` (OOS 2021-2026)

- **`stop_breakout` gewinnt wieder** unter den vier Entry-Typen (Sharpe 0.76),
  knapp vor `confirmed_retest` (0.70) - dieselbe Rangfolge wie bei SP500.
- **Bester Exit: stop=0.6x ATR, target=4R -> Sharpe 1.18, PF 1.28,
  MaxDD nur -2.9%**. Bemerkenswert: 0.6x ATR war auch bei SP500s Feingrid
  (Stage 4d) der beste Einzelwert - **konvergierender, cross-asset-
  bestaetigter Fund**, nicht nur NASDAQ-Rauschen. stop=1.0x ist hier sogar
  ein lokales Tief (Sharpe 0.37-0.84 im Grid) - **0.6x/4R ersetzt 1.0x/4R
  als bevorzugte Exit-Config fuer BEIDE Instrumente**, nicht nur NASDAQ.
- **range_bars=2 (30-Min) schlaegt range_bars=1** bei der (damals noch
  falschen) 1.0x/4R-Exit-Platzierung (Sharpe 0.82 vs 0.59) - anders als bei
  SP500. Mit dem korrekten 0.6x/4R-Exit **widerlegt**: range_bars=1 gewinnt
  auch bei NASDAQ klar (Sharpe 1.18 vs 1.04 bei range_bars=2) - war ein
  Artefakt der (damals noch nicht optimierten) Exit-Platzierung im ersten
  Grid, kein echter Instrument-Unterschied.

### `scripts/research_nasdaq_orb_stage3_filters_regime.py` + `stage3b_combine.py`

**NASDAQ tickt in mehreren Punkten anders als SP500/US30** - Filter nicht
blind uebertragen bestaetigt sich als richtige Entscheidung:

- **Long+Short schlaegt Long-only** (Sharpe 1.18 vs 0.91) - die Short-Seite
  traegt bei NASDAQ selbst positiv bei (Short-only allein: Sharpe 0.75).
  Genaues Gegenteil von SP500/US30, wo Long-only klar gewann.
- **Wochentag-Filter haelt hier ECHTER OOS-Bestaetigung stand** (anders als
  SP500s widerlegter Mittwoch-Fund): IS-Ranking (2016-2021) findet Mittwoch
  als schwaechsten Tag (PF 0.95) - OOS (2021-2026) bestaetigt: "ohne Mittwoch"
  verbessert Long-only-Sharpe 0.91->1.10. **Auf der eigentlichen long+short-
  Basis geprueft** (`stage3b_combine.py`): siehe Tabelle unten.
- **EMA-Ribbon-Bias "mit Trend" gewinnt** (Sharpe 0.88 auf der Long-only-Slice) -
  **Gegenteil von SP500/US30** ("neutral" gewann dort). Bestaetigt die in
  Stage 4e geaeusserte Vermutung: NASDAQs staerker nachhaltig trendende Natur
  bedeutet, dass klare-Trend-Tage hier eher gute als schlechte Setups sind.
  "Gegen Trend" ist klar schlecht (Sharpe 0.13).
- **ADR-Regime hilft nicht** (beide Buckets schwaecher als ungefiltert) -
  wie bei SP500.

**Finale NASDAQ-Config** (auf long+short-Basis geprueft, `stage3b_combine.py`):
`stop_breakout`, `range_bars=1`, **long+short**, **ohne Mittwoch**, ATR-Stop
0.6x, Target 4R -> OOS Sharpe 1.18 -> **1.33**, PF 1.38, MaxDD -2.1%, n=1029.
EMA-Trend-Filter obendrauf schadet (schrumpft Stichprobe auf 344 ohne
Sharpe-Vorteil) - **nicht Teil der finalen NASDAQ-Config**, obwohl er isoliert
auf der Long-only-Slice gut aussah.

### Phase 6 fuer NASDAQ (`scripts/research_nasdaq_orb_phase6.py`)

**Deutlich robuster als die SP500-Config - keine Regimeschwaeche:**

- **p6_1 Walk-Forward**: 2016-2019 Sharpe **1.78**, 2019-2022 Sharpe 1.04,
  2022-2026 Sharpe 1.36 - alle drei Perioden stark UND konsistent, die
  fruehste Periode ist sogar die staerkste. Genaues Gegenteil von SP500s
  monoton ansteigendem, regimeabhaengigem Muster (0.10/0.43/0.95).
- **p6_2 Monte Carlo (OOS)**: Median-Sharpe 1.34 (deckt sich mit Ist-Wert
  1.30), P(MaxDD>5%)=1.8%, **P(MaxDD>10%)=0%**.
- **p6_3 Cost-Sweep**: Breakeven ~4.0bps -> **Sicherheitsfaktor 8.0x**.
- **p6_4 Jaehrlich (OOS)**: **JEDES Jahr 2021-2026 positiv** (Sharpe 0.44-1.72) -
  kein einziges Verlustjahr, sauberer als SP500 (dort 2023 und 2026 negativ).

**Fazit NASDAQ**: die eigenstaendige Kalibrierung war die richtige Entscheidung -
NASDAQs finale Config (`long+short`, ohne Mittwoch, 0.6x/4R) ist nicht nur
anders aufgebaut als SP500s (long-only + EMA-neutral), sondern in der
Walk-Forward-Konsistenz sogar **robuster/weniger regimeabhaengig** als das
SP500-Ergebnis. Kein "final" ohne diesen Hinweis: 0.6x-ATR-Stop wurde auf
demselben Datensatz gefunden wie er hier validiert wird (kein komplett
frischer Drittdatensatz) - die grundsaetzliche Meta-Vorsicht (Parameter aus
Stage 2/3 landen automatisch in Phase 6 desselben Zeitraums) bleibt bestehen,
auch wenn die 3-Perioden-Konsistenz das Risiko mindert.
