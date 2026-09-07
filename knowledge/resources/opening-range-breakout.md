# Resource: Opening Range Breakout (ORB) -- externe Literatur

Destillate zu extern zugeführten ORB-Papers, abgeglichen mit der
bestehenden Repo-Strategie [[ny-open-orb-sp500]] (SP500/US30/NASDAQ-Index-CFDs,
M15-Range/M5-Ausführung) und der älteren, verworfenen `orb_strategy/`
(Tages-ATR-Schwellen-ORB). Beide Paper unten sind NICHT eigene
Repo-Forschung, sondern vom Nutzer geteilte PDFs -- Verwendung nur soweit
sie sich sauber auf das bestehende Setup übertragen lassen, siehe
Vorbehalte je Eintrag.

---

## Opening Range Breakout in NQ E-Mini Futures -- A Replication Study Under the AFML Framework

**Capture**
- Autoren/Jahr: "Private Quantitative Research", Juli 2026
- Quelle/Link: vom Nutzer als PDF geteilt (`nq_orb_research_paper.pdf`),
  kein öffentlicher Link/Autorenname angegeben
- Erfasst am: 2026-09-01
- Weg: manuell im Chat

**Organize**
- Thema/Tags: opening-range-breakout, NQ-E-Mini-Futures, AFML, Triple-Barrier-Method,
  execution-gap, deflated-sharpe-ratio, meta-labeling
- Verwandte Notizen: [[ny-open-orb-sp500]] (Index-CFD-ORB im Repo, gleiche
  Kern-Idee: Stop-Order an Opening-Range-Level), [[opening-range-breakout]]
  (dieses Dokument, siehe Eintrag unten)
- Verwandtes Project/Area: [[ny-open-orb-sp500]]

**Distill**
- **Kernthese**: Ein AFML/Triple-Barrier-Pipeline-Replikat eines NQ-Futures-ORB
  findet einen echten, aber sehr schmalen Edge (In-Sample WR 70.3%/Kelly +0.109,
  Out-of-Sample WR 78.0%/Kelly +0.340, 7/7 Konsens-Tests) -- ABER nur für
  Sessions mit enger Opening Range (ORB-Width <= IS-33stem-Perzentil, 33% der
  IS- bzw. nur noch 20% der OOS-Sessions wegen eines strukturellen Regime-Shifts,
  ORB-Width-Mittelwert +40% OOS ggü. IS). Beim Übergang von "Research-Label"
  (Triple-Barrier-"Touch") zu echter Order-Ausführung verschwindet der Edge
  fast komplett: bestes von drei getesteten Adaptern erreicht nur WR 54%
  (Breakeven liegt bei 62.2%) -- ein struktureller, nicht durch bessere
  Order-Typen schließbarer 24-Prozentpunkte-Gap. AFML-Strategy-Risk-Analyse:
  P(Scheitern)≈97.5%; Deflated-Sharpe-Ratio-Korrektur stellt sogar den
  IS-Edge selbst infrage (5 unabhängige Backtest-Entscheidungen im Grid).
- **Zentrales Modell/Filter/Formel**:
  - ORB = erste 30 Min nach Handelsbeginn (08:30-09:00 ET), ORB_Width = High-Low
    dieses Fensters, als Setup-Qualitäts-Filter genutzt (enge Range = weniger
    Marktteilnehmer-Uneinigkeit beim Open = stärkeres Richtungssignal beim Bruch).
  - Triple-Barrier-Labeling: SL = ORB_Low (Struktur-Level, nicht ATR), TP = Entry
    + R x Risiko mit R=0.50 (niedriges R-Multiple schlägt hohe im Sweep),
    Timeout 14:00 ET.
  - Drei Execution-Methoden verglichen: (A) Market-Order nach TP-Touch-Erkennung
    -> WR 44%; (B) Market-Entry + vorab platzierter Limit-TP -> WR 52%;
    (C) Stop-Market-Entry am Range-Level, TP/SL aus dem TATSÄCHLICHEN Fill-Preis
    neu berechnet -> WR 54%, beste Methode, aber immer noch unprofitabel.
  - Drei benannte Slippage-Quellen: Entry-Slippage (Market-Order nach
    Breakout-Erkennung füllt 10-20 Pkt über dem Level), TP-Fill-Slippage
    (Touch-Label ≠ realer Fill nach Erkennungsverzögerung), False-Breakout-Inflation
    (Stop-Market triggert bei JEDER Intraday-Durchdringung, nicht nur bei
    bestätigtem Bar-Close-Bruch).
- **Was ist potenziell integrierbar?**
  - **Bestätigt bereits Getroffenes, keine Änderung nötig**: Methode C
    (Stop-Order am Range-Level, Exit-Level aus echtem Fill-Preis) entspricht
    exakt `ny_open_orb`s `stop_breakout`-Entry -- von der Literatur selbst als
    beste verfügbare Methode identifiziert. Die Kernwarnung (Touch-Label ≠
    realer Fill, gröbere Bar-Auflösung überschätzt Performance) deckt sich
    unabhängig mit dem bereits im Repo dokumentierten Grund, M15- statt
    M5-Ausführung zu verwerfen (Stage 4c, `research_orb_intrabar_stop.py`).
  - **Neu, noch nicht getestet**: ein ORB-Width-Perzentil-Filter. `orb_width`
    wird in `ny_open_orb/range.py` bereits berechnet, aber nirgends als Filter
    verwendet. Konzeptionell verwandt mit dem bereits bestätigten ADR-Regime-Fund
    (`low_adr` schlägt `high_adr`, Stage 4b) -- aber präziser, weil
    Session-spezifisch statt auf die Tagesrange der letzten 60 Tage bezogen.
  - **Übertragbarer Vorbehalt**: gefilterte Edges auf kleinen Stichproben
    (hier N=50 OOS) sind fragil -- bei jedem neuen Filter-Kandidat auf
    `ny_open_orb` Stichprobengröße und IS/OOS-Trennung genauso streng prüfen
    wie beim bereits erlebten Wochentag-Fehlalarm (Stage 4a2).

**Express**
- Nächster Schritt: erledigt -- siehe [[ny-open-orb-sp500]] Stage 8.
- Ergebnis (2026-09-01): ORB-Width-Perzentil-Filter (als rollierender
  60-Session-Perzentilrang statt statischem IS-Threshold implementiert)
  **verworfen** -- verschlechtert Sharpe auf allen drei Instrumenten (SP500
  OOS 1.20->0.44, US30 1.12->0.89, NASDAQ 1.41->0.49) UND die Richtung ist
  auf Index-CFDs/NY-Cash-Open umgekehrt zum Paper: breite statt enge Ranges
  schneiden hier tendenziell besser ab (passt zum eigenen Stage-1/Phase-6-Befund,
  dass die staerkeren Jahre 2022-2026 auch die breiteren-Range-Jahre sind).
  Kein Transfer von NQ-Futures (08:30-09:00-CT-Session) auf NY-Open-Index-CFDs.

---

## A Profitable Day Trading Strategy For The U.S. Equity Market

**Capture**
- Autoren/Jahr: Carlo Zarattini (Concretum Research), Andrea Barbon
  (Uni St.Gallen/Swiss Finance Institute), Andrew Aziz (Peak Capital
  Trading/Bear Bull Traders) -- Swiss Finance Institute Research Paper
  Series N°24-98, Erstversion 16. Februar 2024
- Quelle/Link: vom Nutzer als PDF geteilt (`ORB M5.pdf`), SSRN/Swiss Finance
  Institute
- Erfasst am: 2026-09-01
- Weg: manuell im Chat

**Organize**
- Thema/Tags: opening-range-breakout, 5-minute-ORB, stocks-in-play,
  relative-volume, US-equities, cross-sectional-selection
- Verwandte Notizen: [[ny-open-orb-sp500]] (Index-CFD-ORB, kein
  Aktienuniversum), [[opening-range-breakout]] (dieses Dokument, Eintrag oben)
- Verwandtes Project/Area: [[ny-open-orb-sp500]]

**Distill**
- **Kernthese**: 5-Min-ORB auf ~7.000 US-Aktien (2016-2023, survivorship-bias-frei)
  ist im ungefilterten Basisfall nur marginal profitabel (Sharpe 0.48, Alpha
  3.3%/Jahr, Beta ~0.01) -- aber beschränkt auf "Stocks in Play" (Top-20 nach
  Relative Volume im Opening-5-Min-Fenster, RVOL >= 100%) explodiert die
  Performance: Sharpe 2.81, Alpha 35.8%/Jahr, Gesamtrendite 1.637% ggü. 198%
  für S&P500 Buy&Hold im selben Zeitraum. Der Edge liegt fast vollständig in
  der AKTIENAUSWAHL (welche der 7.000 Titel man an einem Tag handelt),
  nicht in der ORB-Mechanik selbst. 5-Min-Opening-Range schlägt 15/30/60-Min-
  Varianten klar (Sharpe 2.81 vs. 1.43 vs. 0.21 vs. 0.40).
- **Zentrales Modell/Filter/Formel**:
  - Entry: Stop-Order am 5-Min-Range-High/-Low -- aber Richtung vorab durch
    die FARBE der ersten 5-Min-Kerze gesperrt (bullische Kerze -> nur Long
    erlaubt, auch wenn später das Low bricht; bearische Kerze -> nur Short).
  - Stop-Loss: 10% des 14-Tage-ATR ab Entry-Preis (eng), Ziel: Position bis
    Handelsschluss (16:00 ET) halten, kein festes R-Multiple/Kursziel.
  - Relative Volume = Volumen der ersten 5 Min / 14-Tage-Durchschnitt DESSELBEN
    Zeitfensters (nicht des ganzen Tages) -- Filter auf Titel mit RVOL >= 100%,
    gehandelt werden nur die Top-20-RVOL-Titel des Tages.
  - Basisfilter für das Handelsuniversum: Kurs > $5, 14-Tage-Volumen >= 1 Mio.
    Stück/Tag, 14-Tage-ATR > $0.50.
  - Sizing: 1% Risiko/Trade, max. 4x Leverage (FINRA-konform).
- **Was ist potenziell integrierbar?**
  - **NICHT direkt übertragbar**: der Kern-Edge ist Cross-Sectional-Selektion
    aus einem Universum von tausenden Titeln -- `ny_open_orb` handelt aber
    fix 3 Index-CFDs ohne Auswahluniversum. Deckt sich mit dem bereits
    bestätigten Negativbefund der eigenen "Relative Volume at Time"-Implementierung
    (`ny_open_orb/indicators.py`, Stage 3): als Entry-Filter/Exit auf einem
    fixen Instrument getestet, half NICHT (Sharpe 0.84 -> 0.23-0.33). Kein
    Widerspruch zum Paper, sondern zwei verschiedene Anwendungsfälle
    desselben Signals (Selektion vs. Timing).
  - **Testbar, noch offen**: Erste-Kerze-Richtungssperre als zusätzlicher
    Filter zum bestehenden `stop_breakout` -- orthogonal zu den bestehenden
    Filtern (Long-only+EMA-neutral bzw. Long+Short+ohne-Mittwoch), bisher
    nicht getestet.
  - **Testbar, noch offen**: EOD-Close statt festem 4R-Ziel als alternative
    Exit-Philosophie -- bisher nur das R-Multiple-Grid getestet (3.5R-4.5R),
    nie "laufen lassen bis Handelsschluss".
  - **Tangential, außerhalb des aktuellen Projekt-Scopes**: der komplette
    Stocks-in-Play-Ansatz (5-Min-ORB + RVOL-Selektion über ein breites
    US-Aktien-Universum) als eigenständige neue Asset-Klasse/Strategie-Familie
    -- in DASHBOARD.md Ideen-Inbox festgehalten statt hier verfolgt.

**Express**
- Nächster Schritt: erledigt -- siehe [[ny-open-orb-sp500]] Stage 8. Stocks-in-Play-
  Idee separat in DASHBOARD.md Ideen-Inbox (2026-09-01), nicht Teil dieses Projekts.
- Ergebnis (2026-09-01):
  - **Erste-Kerze-Richtungssperre verworfen** -- kein Mehrwert auf allen drei
    Instrumenten (SP500 OOS Sharpe 1.20->0.98, US30 1.12->0.95, NASDAQ
    1.41->1.05), nur weniger Trades. `stop_breakout` laesst bewusst beide
    Richtungen offen, das war schon gut kalibriert.
  - **EOD-Close-Exit statt festem 4R-Ziel: fuer SP500/US30 verworfen**
    (Sharpe faellt deutlich, MaxDD verdoppelt sich etwa), **fuer NASDAQ ein
    echter, auf rohen UND gefilterten Entries reproduzierter Fund**: Sharpe
    praktisch gleich (1.41->1.42), CAGR fast verdreifacht (3.2%->9.1%), PF
    besser (1.37->1.67) -- aber Win-Rate stuerzt auf 14.9% (Trendfolge-Payoff,
    genaue Umkehrung der bewusst gegenteiligen Stage-6-Entscheidung) und
    MaxDD steigt (-2.3%->-3.8%). Noch KEIN Phase-6-Durchlauf, also noch nicht
    "final" -- vielversprechender, aber ungeprüfter NASDAQ-Kandidat.
