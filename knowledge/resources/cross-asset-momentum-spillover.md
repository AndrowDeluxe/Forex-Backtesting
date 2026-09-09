# Resource: Cross-Asset Momentum Spillover

Destillat zu Spillover-Momentum (Momentum eines Assets als Prädiktor für ein
ANDERES Asset, nicht nur sich selbst) als Ergänzung zu klassischem
Individual-Momentum. Verwandt: [[trend-following-momentum]] (Momentum als
Grundkonzept, dort einfaches MA-Crossover statt statistisches Modell),
[[monetary-policy-spillover]] (anderer Spillover-Mechanismus: Makro/Zentralbank
statt Preis-Momentum), [[fx-microstructure]] (FX-Teilmenge des hier
verwendeten Asset-Universums).

---

## Cross Asset Momentum Spillover (J.P. Morgan, Salopek/Tzotchev)

**Capture**
- Autoren/Jahr: Thomas Salopek, Dobromir Tzotchev (J.P. Morgan Global Cross
  Asset Strategy), 28.05.2025
- Quelle/Link: vom Nutzer als PDF geteilt ("gs trading.pdf", J.P. Morgan
  "Cross Asset Systematic Highlights")
- Erfasst am: 2026-09-08
- Weg: manuell im Chat

**Organize**
- Thema/Tags: momentum, spillover, cross-asset, logistic-regression,
  L1-regularisierung, monatliches-rebalancing, futures, FX, Gold, Bonds
- Verwandte Notizen: [[trend-following-momentum]], [[monetary-policy-spillover]],
  [[fx-microstructure]]
- Verwandtes Project/Area: [[paper-verarbeitung]] (Area). Kein aktives Project
  bisher angelegt -- siehe Express/offene Rückfrage unten.

**Distill**
- **Kernthese**: Klassisches Individual-Momentum (Trend eines Assets in sich
  selbst) lässt sich durch "Spillover-Momentum" verbessern -- ein Modell, das
  aus den Momentum-Signalen ALLER anderen Assets im Universum lernt, welche
  das künftige Vorzeichen der Rendite des Ziel-Assets am besten erklären.
  Kombination aus Individual- + Spillover-Momentum schlägt beide Einzelvarianten
  (Sharpe 0.66 individual -> 0.75 mit Spillover-Ergänzung, aggregiert über 5
  Lookbacks, Backtest ab Ende 1996).
- **Zentrales Modell/Filter/Formel**:
  - Basis-Momentum-Signal: statistischer Hypothesentest auf die mittlere
    Rendite je Lookback (32/64/126/252/504 Tage), Wertebereich [-1,1] --
    **Formel selbst stammt aus einem referenzierten VORGÄNGER-Paper
    ("Designing robust trend-following system") und ist in diesem Dokument
    NICHT enthalten.**
  - Spillover-Modell: rollierende L1-regularisierte logistische Regression
    (Regularisierungs-Grid {0.05, 0.1, 0.2} via Time-Series-Split),
    Trainingsfenster = max(2×Lookback, 252 Tage), Ziel = Vorzeichen der
    1-Monats-Vorwärtsrendite, Features = Momentum-Signale ALLER 42 Assets im
    Universum (Sparsity durch L1 -> jedes Asset wird nur von einer kleinen
    Auswahl anderer Assets beeinflusst).
  - Portfolio-Konstruktion: monatliches Rebalancing, Long wenn mittlere
    vorhergesagte Wahrscheinlichkeit > 0.5 sonst Short, Positionsgröße invers
    zur realisierten Vol, 10% Ziel-Annualvol (rollierend 1 Jahr), 1-Tag
    Execution-Lag, 2.5bps Kosten je Asset.
  - Wiederkehrende Cross-Asset-Beziehung (Fig. 5-9, über alle 5 Lookbacks):
    Bond-Momentum wirkt POSITIV auf künftige Aktienrenditen, Aktien-Momentum
    wirkt NEGATIV auf künftige Bondrenditen (deckt sich mit Pitkäjärvi et al.
    2020, im Paper referenziert). Spillover-Effekt ist überwiegend
    kurzfristig -- schwächt sich mit steigendem Lookback klar ab (hellere
    Heatmap-Farben bei 252/504 Tagen).
  - Aktuelle Modell-Empfehlung Stand 28.05.2025 (Snapshot, nicht ohne
    Live-Neuberechnung reproduzierbar): Gold + GBP hoch auf Individual UND
    Spillover; US Long Bond + Wheat niedrig auf beiden; AUD hoch auf
    Spillover, aber (noch) schwach auf Individual.
  - Investment-Universum: 42 Futures (Appendix Tabelle 4) -- 21 Commodities,
    8 Equity-Indizes, 6 Fixed-Income, 7 FX-Paare (EURUSD, JPYUSD [invertiert
    notiert], AUDUSD, GBPUSD, CADUSD, CHFUSD, NZDUSD).
- **Was ist potenziell integrierbar**: NICHT 1:1 nachbaubar, siehe zwei
  Lücken: (1) die eigentliche Momentum-Signal-Formel steht in einem anderen,
  hier nicht vorliegenden Paper: (2) das Zielspektrum ist ein monatlicher,
  cross-sektionaler Multi-Asset-Ansatz über 42 Futures inkl. US-Treasury-
  Futures/Agrar-Futures/Aktienindex-Futures -- strukturell ein anderes Genre
  als die bisherigen Repo-Strategien (Intraday/Swing, einzelne oder wenige
  Instrumente, Dukascopy-FX/CFD-Daten). Direkteste Repo-Berührungspunkte:
  7 der 42 Assets sind FX-Paare, die im Repo bereits als Instrumente
  existieren; Gold (im Paper aktuell top-attraktiv auf beiden
  Momentum-Dimensionen) ist ebenfalls bereits mehrfach im Repo vertreten
  (asian_range_breakout, Gold ASB, CTNL, gold_bitcoin_dual_momentum).
  Cross-Check-Idee: die QUALITATIVE Beziehung "Bond-Momentum -> positives
  Signal für Aktien/Risk-Assets" könnte als externes Regime-Signal für
  bestehende Gold-Strategien getestet werden. Korrektur nach genauerem
  Blick ins Repo (2026-09-09): die dafür vermutete Datenlücke besteht NICHT
  -- `cls_practical/data.py` holt BUND/USTBOND-CFDs (Dukascopy) und
  DE02Y/US02Y (TradingView-Bridge) bereits für den dort validierten
  Rate-Momentum-Risk-Scaling-Filter (`cls_practical/rates.py`, siehe
  [[cls-practical-strategy-state]]-Memory).

**Express**
- Nächster Schritt: **Nutzerentscheid 2026-09-09** auf die Rückfrage:
  Option (b) FX-only-Nachbau UND Option (c) Gold-Cross-Check, beide
  parallel verfolgt; das volle 42-Asset-Universum bewusst zurückgestellt
  (Ideen-Inbox in `DASHBOARD.md`). Details/Design-Entscheidungen im Plan
  dieser Session, umgesetzt als:
  - **Workstream A** (FX-only, neues Package `fx_momentum_spillover/`):
    Ersatz-Momentum-Signal (t-Test auf mittlere Tagesrendite, durch
    Standardnormal-CDF auf [-1,1] gemappt -- passend zur eigenen
    Paper-Beschreibung "statistical hypothesis tests on the mean return"),
    rollierende L1-Logit-Spillover-Regression (sklearn), eigene monatliche
    Portfolio-Engine, volle Phase-4-7-Kette inkl. Sample-Size-Warnung
    (7 statt 42 Assets, ~270 Monatsbeobachtungen).
  - **Workstream B** (Gold-Cross-Check): NICHT die bereits gescheiterte
    Alignment-Gate-Variante wiederholen (siehe [[fx-microstructure]],
    US-10J-Filter bereits verworfen), sondern die bei `cls_practical`
    validierte kontinuierliche Risk-SCALING-Mechanik zum ersten Mal auf
    `asian_range_breakout` (Gold ASB) anwenden.
- **Ergebnis (2026-09-09, beide Workstreams durchlaufen)**: **negativ, in
  beiden Fällen.** Workstream A (FX-only-Nachbau) reproduziert die
  Paper-These NICHT -- Details + volle Tabellen in
  `knowledge/projects/fx-momentum-spillover.md`. Workstream B
  (Gold-Cross-Check) siehe Nachtrag in
  `knowledge/resources/fx-microstructure.md` -- Risk-Scaling-Mechanik
  besteht Randomisierungstest nicht (p=0.665-0.670), reines
  Leverage-Artefakt statt echtem Timing-Signal.
