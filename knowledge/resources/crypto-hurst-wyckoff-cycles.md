# Resource: Multifractal Hurst-Exponent / Wyckoff-AD-Zyklen (Crypto Perp Futures)

Destillate zu Papers, die den Wyckoff-Accumulation/Distribution-Zyklus mit
dynamischen Hurst-Exponenten/Multifraktalanalyse zur Trendende-/Regime-
Erkennung verbinden. Verwandt: [[fx-microstructure]] und
[[crypto-volume-profile-mean-reversion]] (gleiches wiederkehrendes Muster --
Paper-Edge sieht auf dem Papier glänzend aus, hält auf echten Daten meist
nicht), Crash-Vorwarn-Filter-Suche in [[trend-following-momentum]]
(Nachtrag 2026-08-14 (5) -- 3 Kandidaten getestet, alle negativ; Hurst-
Kollaps dort noch NICHT versucht).

---

## Multifractal Price Delivery in Algorithmic Futures Markets (FLPD)

**Capture**
- Autoren/Jahr: Max Matthews, Eller College of Management, University of
  Arizona; Working Paper 2026 (SSRN, unveröffentlicht/nicht peer-reviewed)
- Quelle/Link: vom Nutzer als PDF geteilt (ssrn-6880798)
- Erfasst am: 2026-08-25
- Weg: manuell im Chat

**Organize**
- Tags: multifractal, hurst-exponent, dfa, wyckoff-ad-cycle, regime-change,
  change-point-detection, crypto-perpetual-futures, order-book-microstructure
- Verwandte Notizen: [[fx-microstructure]], [[crypto-volume-profile-mean-reversion]],
  Crash-Vorwarn-Filter-Suche in [[trend-following-momentum]]
- Verwandtes Project/Area: [[paper-verarbeitung]] (Area)

**Distill**
- **Kernthese**: unter neuer, aufgeblähter Terminologie im Kern ein Trio aus
  drei bekannten Bausteinen -- Wyckoff-Accumulation/Distribution-Zyklus +
  dynamischer Hurst-Exponent (Multifractal DFA) + gewichtete HTF/LTF-
  Signalaggregation. Behauptung: AD-Zyklen wiederholen sich selbstähnlich
  über alle Zeitebenen (H≈0.62-0.71, statistisch ununterscheidbar von
  5-Minuten- bis Tagesskala), und der Übergang Markup→Distribution
  ("Terminal Macro-Attractor") kündigt sich durch einen abrupten,
  nachweisbaren Hurst-Kollaps an (CUSUM-Change-Point-Test), median ~22
  Ticks / 4.7s Vorlaufzeit vor der Umkehr.

- **Zentrales Modell/Filter** (jargon-bereinigt, 3 Bausteine):
  1. **Dynamischer Hurst-Exponent als Erschöpfungssignal** -- rollierendes
     DFA (Ordnung q=2) auf W=2000 Ticks, gestept um 200 Ticks; Abfall >2
     rollierende Std.-Abw. markiert Trendende/Regimewechsel. Einziger
     Baustein, der ohne Orderbuch-Tiefendaten testbar ist (nur Preisserie
     nötig, auf OHLC-Bar-Basis übertragbar statt Tick-Basis).
  2. **Temporal Liquidity Vacuum (TLV)** -- Orderbuch-Tiefe über alle
     Preislevel signifikant unter 30-Tage-Mittel (KS-Test) -> Power-Law-
     verteilte "Liquiditätsvakuum"-Dauer. Braucht Level-3-Orderbuch-Tiefe
     je Preislevel -- nicht im Repo-Datenstack vorhanden.
  3. **Ψ-Matrix (HTF/LTF-Aggregation)** -- gewichtete Summe abgeschlossener
     LTF-AD-Zyklen (exponentieller Zeit-Decay) als HTF-Kompositsignal --
     im Kern nur "gewichte jüngere Sub-Zyklen-Abschlüsse stärker für ein
     übergeordnetes Signal", eine generische Multi-Timeframe-Aggregations-
     idee, kein eigenständig neues Konzept.

- **Was ist potenziell integrierbar**: NUR Baustein (1) ist mit den im
  Repo vorhandenen Datenquellen (OHLC/Klines, keine Orderbuch-Tiefe je
  Preislevel) überhaupt testbar. Naheliegender Wiederverwendungs-Kandidat:
  die Crash-Vorwarn-Filter-Suche in [[trend-following-momentum]] hat
  bereits 3 Kandidaten (ATR-Expansion, Cross-Asset-Korrelation BTC-ETH,
  Taker-Sell-Aggression) auf voller BTCUSDT-Historie getestet -- alle mit
  negativem/unzuverlässigem Ergebnis (siehe Nachtrag 2026-08-14 (5)). Ein
  rollierender Hurst-Exponent/DFA-Kollaps wäre ein vierter, dort noch
  nicht versuchter Kandidat für denselben Zweck (Regime-/Trendende-Timing,
  ggf. auch als Exit-Signal für die bestehende `btc_ema_cross`-Strategie
  statt eines neuen Vorwarn-Filters).

- **Kritischer Vorbehalt (Red Flags, nicht nur Nacherzählen)**:
  - **Aufgeblähte Neubenennung**: "Fractal Law of Price Delivery",
    "Terminal Macro-Attractor", "Discretized Multiscale Hierarchical
    Delivery Matrix" klingen neu, sind aber im Kern Wyckoff (1931) +
    Hurst/DFA (Mandelbrot, Kantelhardt et al. 2002) + HMM-Regime-Erkennung.
    Gleiches Marketing-Muster wie die "FATAL FINDING"-Sprache im
    SOL/USDT-Paper in [[crypto-volume-profile-mean-reversion]].
  - **Unrealistisch glatte Robustheit**: ALLE 8 Robustheitschecks
    bestehen, OOS-Sharpe 2.41 übersteht Bonferroni, Cross-Asset (ETH:
    2.19), Event-Exclusion (LUNA/FTX), vollen Parameter-Grid UND
    Latenz-Stress bis 50ms/1.5-Tick-Slippage (Sharpe fällt nur auf 1.42)
    -- kein einziger negativer Teilbefund irgendwo. In diesem Repo hat
    bislang JEDE eigene Robustheitsprüfung (Gold-ADX/US-Yield-Filter,
    EMA-Cross-Regimefilter/Take-Profit/Chandelier-Tests) mindestens einen
    negativen oder uneinheitlichen Teilbefund gezeigt -- ein Paper ganz
    ohne Ausreißer ist ein Warnsignal, kein Qualitätsmerkmal.
  - **Datenanforderung unrealistisch**: Level-3-Orderbuch-Tickdaten (4.18
    Mrd. Events über 36 Monate, "Binance institutional research data
    program") -- nicht frei verfügbar, nicht im Repo-Datenstack
    (`auction_playbook/data.py` liefert Klines + aggregierte
    Taker-Buy/Sell-Volumina, keine Tiefe je Preislevel).
  - **Exekutionsanforderung inkompatibel**: eigene Latenz-Sensitivität
    des Papers zeigt Sharpe 2.41->1.42 bei nur 50ms Latenz; die Strategie
    braucht ein 4.7-Sekunden-Exekutionsfenster bei 2.3 Signalen/Tag --
    passt nicht zur Poll-basierten MT5-Bridge-Architektur dieses Repos
    (`BTC-EMA-Cross-Bridge/` u.a.), die für Sekunden-/Minuten-Timing
    gebaut ist, nicht Sub-Sekunde.
  - Theorem 1(b) und Proposition 2 werden vom Paper selbst als
    unvollständig bewiesen bzw. als "Conjecture" geflaggt -- ungewöhnlich
    selbstkritische Formulierung bei gleichzeitig ungewöhnlich perfekten
    empirischen Resultaten (typisches Muster überzeichneter/KI-generierter
    "Working Paper"-Texte).

**Express (2026-08-25 -- alle 3 Bausteine realistisch nachgebaut und getestet, auf Nutzerwunsch)**

Trotz fehlender Orderbuch-Tiefe wurden alle 3 Bausteine mit ehrlichen Proxys
auf echten Binance-Daten (BTCUSDT + ETHUSDT, volle Historie seit 2017-08-17
bzw. Listing, IS/OOS-Split 2023-12-01) nachgebaut und getestet:
1. **Hurst/DFA** (`crypto_flpd/hurst.py`) -- eigene DFA2-Implementierung
   (Hat-Matrix-vektorisiert), gegen synthetisches weißes Rauschen (H≈0.5)
   und AR(1)-Prozess (H>0.5) verifiziert.
2. **TLV-Proxy** (`crypto_flpd/liquidity.py`) -- n_trades-Ausdünnungs-
   Perzentil + wiederverwendeter Corwin-Schultz-Spread aus
   `bond_yield_indicator/friction.py`.
3. **Ψ-Matrix** (`crypto_flpd/phases.py`) -- EMA9/21-Completion-Signal
   (identisch zu `btc_ema_cross`) statt Baum-Welch-HMM, decay-gewichtete
   HTF→LTF-Aggregation, Kausalität/No-Lookahead per Unit-Test verifiziert
   (10 pytest-Fälle in `tests/test_crypto_flpd_*.py`, alle grün).

Zwei Testphasen (`scripts/research_btc_flpd_hurst_wyckoff.py`,
Randomisierung via `crypto_flpd/significance.py`, n=300 Shuffles, gleiche
Rotation/Run-Permutation-Methodik wie
`asian_range_breakout/randomization.py`):

**0. Premise-Check -- Kernannahme widerlegt.** Der von Baustein 1
vorausgesetzte Skaleninvarianz-Hurst (Papers Tabelle 3: H≈0.62-0.71 über
alle Skalen) zeigt sich auf echten BTCUSDT-OHLC-Daten NICHT: gemessenes H
liegt bei 0.483 (15m) / 0.483 (1h) / 0.517 (4h) / 0.529 (Daily) -- praktisch
der Random-Walk-Benchmark H=0.5, nicht die vom Paper behauptete
Persistenz. Die Skalenkonstanz selbst hält zwar (Spread nur 0.046 über alle
4 Auflösungen), aber auf einem fundamental anderen NIVEAU als im Paper.
Plausible Erklärung: Persistenz aus Nanosekunden-Tick-/Orderflow-Daten
verschwindet bei Aggregation auf Bar-Schlusskurse (bekannter
Aggregations-Effekt) -- die theoretische Grundlage der ganzen FLPD trägt
schlicht nicht auf Bar-Daten.

**Phase A -- Hurst-Kollaps als Exit-Overlay auf die validierte
EMA9/21-Baseline: klar schädlich, auf BEIDEN Assets, in JEDEM Fenster.**

| | BTCUSDT Full | BTCUSDT OOS | ETHUSDT Full | ETHUSDT OOS |
|---|---|---|---|---|
| Baseline PF | 3.301 | 2.211 | 3.385 | 1.536 |
| + Hurst-Exit PF | 1.723 | 1.384 | 1.995 | **0.802** |
| Baseline Return | +3582.7% | +89.5% | +7697.4% | +74.7% |
| + Hurst-Exit Return | +95.1% | +27.7% | +176.3% | **-15.5%** |

Randomisierungstest (BTCUSDT, Full, n=300): p=0.573 (rotation) / p=0.623
(run_permutation) -- der Hurst-Kollaps-Exit-Zeitpunkt ist statistisch NICHT
von einem zufälligen, footprint-gleichen vorzeitigen Exit unterscheidbar.
Reiht sich exakt in das bereits dokumentierte Muster in
[[trend-following-momentum]] ein (TP/Chandelier/Volumen-Exhaustion-Exit
schaden alle gleichermaßen) -- die Kante der EMA9/21-Strategie lebt von
seltenen großen Trades, jeder vorzeitige Exit-Mechanismus kappt genau das,
unabhängig vom Trigger. **Vierter (und damit letzter offener) Kandidat für
die Crash-/Trendende-Filter-Frage aus Nachtrag 2026-08-14 (5) -- ebenfalls
gescheitert.**

**Phase B -- volle Ψ-Strategie (alle 3 Bausteine kombiniert): kein
robuster Edge.**

| | BTCUSDT Full | BTCUSDT OOS | ETHUSDT Full | ETHUSDT OOS |
|---|---|---|---|---|
| PF | 1.022 | 1.144 | 0.904 | **0.579** |
| CAGR | -2.1% | +6.9% | -16.2% | **-36.2%** |
| MaxDD | -68.5% | -32.6% | -86.7% | -72.1% |

BTCUSDT liegt bestenfalls bei Breakeven (PF≈1.0) bei gleichzeitig sehr
hohem Drawdown -- IS sogar leicht negativ (PF 0.986), nur OOS leicht
positiv (PF 1.144), keine konsistente Richtung. ETHUSDT (Papers eigener
Robustheitscheck #1, identischer Code, keine Neukalibrierung) ist klar
NEGATIV, OOS sogar deutlich (PF 0.579, CAGR -36.2%). Randomisierungstest
(BTCUSDT Entry-Timing, n=300): rotation p=0.037 (< 0.05), ABER
run_permutation p=0.320 (klar nicht signifikant) -- nach der in diesem
Repo etablierten Regel ("p<0.05 unter BEIDEN Methoden" --
`scripts/research_gold_liquidity_event_filters.py`) zählt das NICHT als
Beleg für echten Timing-Skill, zumal der ETHUSDT-Cross-Check klar
gegenteilig ausfällt.

**Ergebnis: kein integrierbarer Baustein.** Alle 3 Elemente wurden so
realistisch wie mit den vorhandenen Daten möglich nachgebaut (siehe oben)
-- die Kernannahme (Hurst-Persistenz) trägt nicht auf Bar-Daten, der
Hurst-Kollaps als Exit-Signal schadet nachweisbar (statt zu helfen), und
die volle Ψ-Strategie zeigt bestenfalls Breakeven auf einem Asset und
einen klaren Verlierer auf dem zweiten. Reiht sich nahtlos in das
Repo-weite Muster ein (siehe [[fx-microstructure]],
[[crypto-volume-profile-mean-reversion]]): Paper-Edges verschwinden fast
immer auf echten Daten. Code: `crypto_flpd/` (hurst.py, liquidity.py,
phases.py, engine.py, significance.py),
`scripts/research_btc_flpd_hurst_wyckoff.py`,
`tests/test_crypto_flpd_*.py`. Die Crash-/Trendende-Filter-Frage aus
[[trend-following-momentum]] gilt damit als ausgeschöpft (4/4 Kandidaten
gescheitert) -- kein weiterer naheliegender Kandidat offen.

**Nachtrag 2026-08-25 -- Übertragung auf eine andere Strategie
(auction_playbook): Baustein 3 vereinfacht als HTF-Trend-Bias, ebenfalls
kein Edge**

Nutzerfrage: lassen sich die Bausteine auf eine andere Strategie übertragen
statt (nochmal) eine eigene daraus zu bauen? Von drei angebotenen Optionen
(Liquiditätsfilter auf `btc_ema_cross`, HTF-Trend-Bias auf
`auction_playbook`, Hurst-Level als Regime-Klassifikator) hat der Nutzer
**HTF-Trend-Bias auf `auction_playbook`** gewählt -- die naheliegendste
Übertragung, weil strukturell identisch mit Golds bereits validiertem
SMA200-Trend-Bias-Filter (`asian_range_breakout/filters.py::
attach_trend_bias`): Baustein 3 (Ψ-Matrix) auf den einen Teil reduziert,
der dort schon einmal funktioniert hat -- ein binäres Richtungs-Gate
(`crypto_flpd/phases.py::trend_state`, EMA9/21 auf 4h/Daily) statt der
gescheiterten decay-gewichteten Aggregation.

`auction_playbook/filters.py::attach_htf_trend_bias`/
`apply_htf_trend_bias_filter` (neu, Kausalität per 3 Unit-Tests in
`tests/test_auction_playbook_filters.py` verifiziert) angehängt an BEIDE
Setups (`trend_continuation`, `mean_reversion`) -- "aligned" = Trade-
Richtung stimmt mit dem übergeordneten Trend überein, exakt wie
`attach_trend_bias` es Setup-unabhängig behandelt. Getestet mit deutlich
längerer Historie als der ursprüngliche 1-Jahres-Test (2019-2026 statt nur
Aug 2025-Jul 2026), um dem Filtertest selbst genug Trades zu geben: 1085
BTCUSDT-/1000 ETHUSDT-Trades statt vorher n=30-42
(`scripts/research_auction_playbook_htf_trend_bias.py`, gleiche
Randomisierungs-/Walk-Forward-Methodik wie beim Gold-Liquiditätsfilter,
direkt wiederverwendet aus `asian_range_breakout/randomization.py` +
`walkforward.py`).

**Ergebnis über 12 Kombinationen (2 Assets × 2 HTF-Auflösungen [4h/Daily] ×
2 Setups + kombiniert): kein konsistenter Effekt, nirgends signifikant.**
Die Richtung kippt je nach Symbol/Auflösung/Setup komplett um -- bei
BTCUSDT schadet "im Trend handeln" fast durchgehend (z.B. 4h
Trend-Continuation: Aligned PF 0.839 vs. Misaligned PF 1.429), bei ETHUSDT
hilft es meistens (4h Trend-Continuation: Aligned PF 1.466 vs. Misaligned
PF 1.232), bei ETHUSDT Daily dreht es sich sogar INNERHALB desselben
Symbols um (Trend-Continuation: Misaligned massiv besser, PF 2.071 vs.
0.982; Mean-Reversion: Aligned besser, PF 1.673 vs. 1.039) -- klassisches
Rauschmuster. Randomisierungstest: in KEINER der 12 Kombinationen p<0.05
unter beiden Methoden (rotation + run_permutation); der beste Fall
(ETHUSDT Daily Mean-Reversion) liegt bei p=0.054/0.056 -- bei 12 Tests
genau das, was reines Rauschen statistisch erwarten lässt, und dieser eine
Fall repliziert nicht auf BTCUSDT (dort schadet derselbe Filter). Walk-
Forward zeigt zusätzlich das bekannte Overfitting-Muster aus
`app_pages/risk_management.py`: selbst wenn der Filter auf Trainingsdaten
"bestätigt" wird, ist er im folgenden Testjahr oft schlechter als
ungefiltert (z.B. ETHUSDT 4h Trend-Continuation 2025: bestätigt, PF fällt
trotzdem von 1.158 (ungefiltert) auf 0.885 (gefiltert)).

**Einordnung**: selbst die einfachste, am besten vorvalidierte
Vereinfachung eines FLPD-Bausteins (binäres Trend-Gate, strukturell
identisch mit einem in diesem Repo bereits bewährten Filter) überträgt
sich nicht auf eine andere Strategie/Asset-Kombination. Kein
integrierbarer Baustein. Code: `auction_playbook/filters.py`,
`crypto_flpd/phases.py::trend_state`,
`scripts/research_auction_playbook_htf_trend_bias.py`,
`tests/test_auction_playbook_filters.py`. Damit sind jetzt alle 3
ursprünglichen Bausteine UND die naheliegendste Übertragung auf eine
andere Strategie getestet und verworfen -- Thema gilt als abgeschlossen,
kein weiterer Testkandidat offen, außer der Nutzer bringt ein neues Paper
oder eine neue Idee ein.
