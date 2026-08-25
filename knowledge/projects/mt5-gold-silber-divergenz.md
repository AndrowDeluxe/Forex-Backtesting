# Project: MT5 Gold/Silber-Divergenz (Long-only Gold, Silber-Referenz)

**Ziel**: Dritten von drei "Neue Bots" (Community-Release-Paket,
`OneDrive/.../Bots/Neue Bots/3-Divergenz-Gold-Silber/`) als backtestbare
Basis rekonstruieren und gegen den Standardprozess pruefen. Bot ist auf
dieser Maschine noch NICHT deployed.

**Status**: Phase 5 (Optimierung) + Phase 6 (Robustheit, auf der optimierten
Config wiederholt) abgeschlossen. **Befund: POSITIV -- staerkster der drei
Bots in diesem Paket, robust ueber Sub-Perioden, Kosten und
Sequenzrisiko-Bootstrap, seit 2026-08-25 mit einer validierten, verbesserten
Konfiguration.** Neu gebaut (Paket existierte nicht im Repo).

**Prozess-Referenz**: `app_pages/education_gold_intraday.py`, Phase 6. Code:
`mt5_gold_silver_divergenz/pipeline.py`,
`scripts/research_mt5_gold_silver_divergenz.py`,
`scripts/research_mt5_gold_silver_divergenz_phase6.py`.

## Zur Herkunftsangabe in config.py

`config.py` des Live-Bots behauptet einen bereits existierenden
Forschungsbefund (Out-of-Sample-Verhaeltnis 2,43-2,65 ueber 3 Split-Methoden,
142 Trades/10 Jahre H4, Top-5-Konzentration 10,7%) aus einem Skript
`backtest-pipeline/idea_r28_intermarket_divergenz.py`. Dieses Skript wurde
auf der GESAMTEN Maschine gesucht (nicht nur diesem Repo) und existiert
nirgends auffindbar -- das "Neue Bots"-Paket ist laut eigenem CHANGELOG.md
bewusst ohne interne Forschungsskripte veroeffentlicht ("Nicht enthalten:
interne Test-/Backtest-Skripte und Forschungsnotizen"). Diese Notiz ist
deshalb eine UNABHAENGIGE Neu-Rekonstruktion, keine Verifikation jenes
Befunds -- die Zahlen unten weichen leicht von der config.py-Behauptung ab
(130 statt 142 Trades, Top-5 15,5% statt 10,7%), was bei unterschiedlicher
Datenquelle/Methodik zu erwarten ist. Die grobe Richtung (klar profitabel,
niedrige Gewinnkonzentration, mehrjaehrig bestaetigt) deckt sich aber.

## Strategie & Signal-Parität

Intermarket-Mean-Reversion, kein reines Trendfolgen: 20-Kerzen-Rendite-
Differenz zwischen Gold und Silber (`d`), bezogen auf ihr eigenes rollierendes
100-Kerzen-Band bei -1,5 Standardabweichungen. Faellt `d` unter das Band
(Gold haengt Silber ab) und kreuzt danach wieder darueber (echtes
Uebergangsereignis, kein Dauerzustand), gilt das kombiniert mit
`close > EMA(150)` als Long-Signal fuer Gold. Silber wird referenziert
(letzter bekannter Kurs on-or-before jedem Gold-Balken, kausal, kein
Lookahead), aber nie gehandelt. Stop = ATR(14) x 2.0, Ziel = 2R. Markt: nur
XAUUSD H4, MAX_OPEN_POSITIONS=1 (deckt sich exakt mit `simulate_trades`'
eingebauter "eine Position gleichzeitig"-Logik -- kein zusaetzlicher
Portfolio-Engine noetig).

Vor jeder Ergebnis-Interpretation gegen die eigene `check_signal()`-Funktion
des Live-Bots Balken-fuer-Balken bit-exakt geprueft (2016-2020 H4, 6393
Balken, 0 Abweichungen bei 71 Signalen).

## Phase 6 -- Robustheit: Befunde

**p6_1/p6_4 Walk-Forward (3 rollierende Sub-Perioden)**:

| Periode | n | WR | PF | Sharpe | CAGR |
|---|---|---|---|---|---|
| 2016-2019 | 29 | 34.5% | 0.71 | -0.53 | -2.1% |
| 2019-2022 | 42 | 50.0% | 1.67 | +0.61 | +3.8% |
| 2022-2026 | 59 | 59.3% | 2.39 | +1.11 | +8.7% |

2 von 3 Perioden klar positiv, mit steigender Tendenz (nicht nur ein
Zufallstreffer im letzten Fenster) -- die schwaechste Periode (2016-2019) ist
negativ, aber nicht katastrophal (PF 0.71, kein Totalausfall).

**p6_2 Monte-Carlo-Bootstrap** (block_size=20/n_sims=2000, RISK_PERCENT=1.0%
Bot-Default, einfache Compounding-Sim da MAX_OPEN_POSITIONS=1):

| Fenster | Median TotalReturn | Median MaxDD | P(MaxDD>20%) | Median Sharpe |
|---|---|---|---|---|
| Full History (n=130) | +93.2% | -11.5% | 5.1% | 0.68 |
| OOS only 2023-2026 (n=50) | +57.9% | -7.5% | 0.8% | 1.15 |

Deutlich guenstigeres Sequenzrisiko-Profil als der Haupt-Bot (P(MaxDD>20%)
5.1% vs. dessen 6.0% bei gleichem Risiko, aber hier bei doppelt so hohem
Ziel-Risiko-Prozentsatz) und WEIT guenstiger als David-V2 (P(MaxDD>30%)
79.8% dort).

**p6_3 Kosten-Sensitivitaet** (OOS 2023-2026): Breakeven-Spread zwischen
100-150bps gegen 10bps Annahme -- **15x Sicherheitsfaktor**, der mit Abstand
robusteste Wert aller drei Bots in diesem Paket (Haupt-Bot/David-V2 liegen
deutlich niedriger).

**Outlier-Check**: bester Trade entfernt -> PF 1.73->1.66, Sharpe 0.69->0.64
(Full History). Kein nennenswerter Einbruch -- bestaetigt die eigene
Beobachtung des Bots zu niedriger Gewinnkonzentration (Top-5 hier: 15.5% des
Bruttogewinns).

## Fazit

Robustester Fund der drei Bots in diesem Paket: 2 von 3 Sub-Perioden positiv
mit steigender Tendenz, guenstiges Sequenzrisiko-Profil, sehr hoher
Kosten-Puffer, keine Abhaengigkeit von einzelnen Ausreisser-Trades. Einzige
offene Fragen: (1) n=130 Trades ueber 10 Jahre ist ein kleines Sample fuer
ein Instrument (kein Cross-Market-Check gemacht, im Unterschied zum
Haupt-Bot, der 5 Maerkte poolt), (2) die schwache 2016-2019-Periode zeigt,
dass der Edge nicht in JEDEM Regime traegt. Kein Blocker fuer eine
Demo-Freigabe (Bot hat den eingebauten `ALLOW_REAL_ACCOUNT=False`-Schutz),
aber vor einer eventuellen Echtgeld-Freigabe waere ein laengerer
Demo-Beobachtungszeitraum sinnvoll, gerade wegen des kleinen Samples.

**Verknuepfung**: [[mt5-haupt-bot-trend-pullback]], [[mt5-david-v2-pullback]]
(die anderen beiden Bots desselben Pakets), [[backtest-standard-process]].

## Nachtrag 2026-08-25 -- Phase 5 (Optimierung) + erneute Phase 6

**Bottleneck zuerst korrekt eingegrenzt.** Erste Hypothese (rohe ATR als
Volatilitaetsfilter, da die Regime-Zerlegung "hohe Vol besser" zeigte) wurde
GEPRUEFT UND VERWORFEN: nach Normierung auf ATR/Preis (statt Dollar-ATR)
verschwindet der Effekt fast vollstaendig (WR 47.7%/58.1%/46.5% je Tertile,
nicht monoton) -- der urspruengliche Befund war ein Artefakt von Golds
eigenem Kursanstieg (1200->3000+), nicht echte Volatilitaet. Stattdessen
Ursache empirisch eingegrenzt: die schwache 2016-2019-Periode faellt exakt
mit der einzigen Phase zusammen, in der die Gold/Silber-Ratio selbst in
einem glatten STRUKTURELLEN Aufwaertstrend lief (76.6->83.0, Std.-Abw. nur
5.0 -- die niedrigste aller 3 Perioden; die anderen beiden Perioden sind
Netto-Rueckgaenge mit hoeherer Streuung, 11.4 bzw. 9.8 -- echtes
Hin-und-Her). Nicht erklaerbar durch Golds eigenen Trend (Gold stieg 2016/17)
oder ADX/Trendstaerke (2016-19 hatte sogar hoeheren mittleren ADX als die
anderen Perioden). Ein direkter Test mit ADX(14) AUF der Ratio (falsche
Zeitskala -- misst Tage, nicht Jahre) zeigt folgerichtig keinen Unterschied
-- als Diagnose gemeldet, NICHT als validierten Fund.

**Ratio-Trendigkeits-Filter bleibt ungetestet mit echter IS/OOS-Disziplin**:
Silber-Daten via `combined_strategy.data` reichen nur bis 2014-07-25 zurueck
(Gold bis 2003) -- keine zusaetzliche unabhaengige Regime-Instanz verfuegbar,
also keine faire OOS-Validierung moeglich. Bewusst nicht implementiert.

**Was stattdessen sauber IS(2016-2022)/OOS(2023-2026)-validiert wurde**
(`scripts/research_mt5_gold_silver_divergenz_optimization.py`, 125
Band-Kombinationen + Stop/RR-Raster + Silber-Bestaetigungsfilter-Sweep,
gekettet wie bei den Trend-Pullback-Bot-Skripten):

1. **Band-Parameter**: `ret_len=25, band_lookback=50, band_mult=1.75`
   (war 20/100/1.5) -- IS-Sharpe 0.39->0.85, UND OOS-Sharpe verbessert sich
   mit (1.12->1.20, MaxDD -8.1%->-5.2%, mehr Trades) -- kein
   IS-gut-OOS-schlecht-Kollaps wie beim Trend-Pullback-Bot-TP/SL-Sweep.
2. **Stop/RR**: unveraendert (2.0/2.0) -- im vollen Sweep selbst der beste
   IS-Wert, keine Aenderung noetig.
3. **Silber-Bestaetigungsfilter** (neu in `pipeline.py` als optionaler
   `confirm_len`-Parameter, Default `None`/aus): Silbers eigene 10-Kerzen-
   Rendite muss bei Entry auch positiv sein (nicht nur "weniger negativ als
   Gold") -- IS-Sharpe 0.85->0.91, OOS-Sharpe 1.20->1.31, PF 2.28->2.77.
   Kostet Tradezahl (55->45 OOS).

**Komplette Phase 6 auf der finalen Config wiederholt**
(`scripts/research_mt5_gold_silver_divergenz_final_phase6.py`, nicht nur der
IS/OOS-Split -- Lektion aus [[backtest-standard-process]]: Phase 6 muss auf
der tatsaechlich vorgeschlagenen finalen Config laufen, nicht nur einmal auf
dem Ausgangspunkt):

| | Bot-Original | Optimiert |
|---|---|---|
| 2016-2019 Sharpe | -0.53 | **+0.14** (nicht mehr negativ) |
| 2019-2022 Sharpe | +0.61 | **+0.94** |
| 2022-2026 Sharpe | +1.11 | **+1.35** |
| Monte-Carlo P(MaxDD>20%), Full | 5.1% | **0.4%** |
| Monte-Carlo P(MaxDD>20%), OOS | 0.8% | **0.1%** |
| Kosten-Sicherheitsfaktor | 15.0x | 15.0x (unveraendert) |
| Top-10-Gewinnkonzentration | 27.6% | 25.3% |

Der fruehere Bottleneck ist nicht mehr negativ, aber nicht vollstaendig
"repariert" -- bleibt die schwaechste der 3 Perioden. Ehrlich gemeldet.

**Einordnung/Risiko**: 125 Kombinationen auf ~190 gepoolten Trades zu
sweepen traegt reales Overfitting-Risiko, auch wenn IS und OOS sich hier
GEMEINSAM verbessert haben (das Warnsignal-Muster, das anderswo in diesem
Repo Overfitting anzeigt -- IS besser, OOS schlechter -- ist hier NICHT
aufgetreten). Mit 45-50 OOS-Trades nach dem Silber-Filter bleibt die
Stichprobe duenn. Als starker Kandidat zu werten, nicht als endgueltig
bewiesen -- die offenen Fragen aus dem ersten Fazit oben (kleines
Ein-Instrument-Sample, kein Cross-Market-Check) gelten unveraendert weiter.

**Code**: `mt5_gold_silver_divergenz/pipeline.py` (neuer optionaler
`confirm_len`-Parameter, Bot-Original-Defaults unveraendert -- Signal-Paritaet
zum Live-Bot bleibt bei `confirm_len=None` exakt erhalten).
`app_pages/mt5_gold_silver_divergenz.py` (neuer erster Tab "Empfehlung
(Optimiert)", alle anderen Tabs zeigen weiterhin unveraendert das
Bot-Original zur Dokumentation).
