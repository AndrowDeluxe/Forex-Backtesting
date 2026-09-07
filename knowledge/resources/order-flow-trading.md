# Resource: Order-Flow-/Diskretionäres Trading -- externe Literatur

Destillate zu extern zugeführtem diskretionärem Trading-Wissen (Order Flow,
Marktmikrostruktur, Trading-Psychologie). Anders als die Quant-Ressourcen
(`opening-range-breakout.md` etc.) hier bewusst KEIN direkter Backtest-Bezug
möglich, da die Kernsignale (Order Flow, Gamma Exposure) Echtzeit-/
Optionsdaten brauchen, die im Repo nicht vorliegen -- Zweck dieser Notiz ist
das Festhalten übertragbarer Konzepte/Filter-Ideen, nicht die 1:1-Übernahme
der Strategie.

---

## Chris Creamer (IQCapital): "Trading WORLD CHAMPION Reveals the Orderflow Strategy That Won the Robbins Cup"

**Capture**
- Interviewpartner/Jahr: Chris Creamer (Robbins World Cup Micro Day Trading
  Champion, Juli-Wettbewerb, 100% Return), interviewt von IQCapital (Prop
  Firm), 2026
- Quelle/Link: https://www.youtube.com/watch?v=PL7LKUsCgIQ
- Erfasst am: 2026-09-01, verarbeitet: 2026-09-02
- Weg: Obsidian Web Clipper -> `knowledge/Clippings/Trading WORLD CHAMPION
  Reveals the Orderflow Strategy That Won the Robbins Cup (Step-by-Step).md`
- **Achtung**: Sponsored/Prop-Firm-Content (IQCapital bewirbt eigene
  Challenges im Video) und rein diskretionär -- keine unabhängig
  verifizierten Performance-Zahlen (Robbins-Cup-Ergebnis ist öffentlich,
  aber die "60-65% Winrate/1.8 Profit Factor"-Angaben sind Selbstauskunft).

**Organize**
- Thema/Tags: order-flow, market-microstructure, gamma-exposure-gex,
  volume-profile, footprint-candles, prop-firm-risk-management,
  trading-psychologie
- Verwandte Notizen: [[ny-open-orb-sp500]] (einzige Berührungspunkte: NY-Open-
  Session-Fokus, Teilnahme-/Liquiditätsfilter-Idee, siehe unten)
- Verwandtes Project/Area: keins -- rein konzeptionell, kein aktives Projekt

**Distill**
- **Kernthese**: Vier-Schritte-Framework (Environment -> Location ->
  Confirmation -> Execution) für intraday NY-Open-Trading (erste 1,5h),
  das systematisch versucht, "trapped participants" (Marktteilnehmer, die
  gegen den Trend positioniert sind und zum Glattstellen gezwungen werden)
  zu identifizieren, statt Muster/Setups zu jagen. Der Sprecher betont
  explizit: der langfristige Erfolg kam nicht aus besseren Setups, sondern
  aus Exekutions-Disziplin (Vermeiden "schlechter" Verluste) und
  Risikomanagement -- nicht aus mehr Wissen/mehr Strategien.
- **Zentrales Modell/Filter (diskretionär, nicht quantifiziert im Video)**:
  1. **Environment**: höhere Zeitebenen (1h/4h) auf Marktstruktur prüfen
     (Value-up/-down/sideways) PLUS Gamma Exposure (GEX) der Optionsmärkte
     -- positives Gamma = Dealer dämpfen Volatilität (Rip verkaufen/Dip
     kaufen, Breakouts scheitern häufiger), negatives Gamma = Dealer
     verstärken Volatilität (Rip kaufen/Dip verkaufen).
  2. **Location**: nur in Richtung der übergeordneten Struktur handeln,
     und dort nur im "Discount" (unterhalb Value Area, per Fibonacci
     70,5/78,8/88,6% vom letzten Swing) einsteigen -- 88,6% als harte
     Invalidierungsgrenze.
  3. **Confirmation**: Order-Flow/Footprint-Candles (Volumen- und
     Delta-Profil pro Kerze) zeigen "Absorption" (aggressive Verkäufer im
     Extrembereich der Kerze OHNE Ergebnis/Fortschritt) gefolgt von
     Dominanzwechsel (nächste Kerze bullisch, Verkäufer scheitern beim
     zweiten Versuch) als Einstiegssignal. Stop unter/über dem
     gescheiterten Extrem, Ziel meist Swing-Punkte/POC, 1,5-2R im Schnitt.
  4. **Liquiditätsfilter**: kein Trade unterhalb eines festen Schwellwerts
     (im Video: 20.000 Kontrakte/5-Min-Kerze für MNQ) -- sinkendes Volumen
     signalisiert nahende Mittagspause/geringe Teilnahme, Setup wird dann
     ignoriert, unabhängig davon wie es aussieht.
  5. **Risikomanagement/Psychologie**: harte Regel "nach 2 Verlusten in
     Folge aufhören" (statt erst nach 3, wo laut Sprecher die Tilt-
     Wahrscheinlichkeit auf ~50% steigt); Unterscheidung "guter Verlust"
     (Setup korrekt ausgeführt, Markt lief trotzdem dagegen) vs. "schlechter
     Verlust" (eigene Regeln gebeugt/antizipiert statt bestätigt) als
     zentrale Selbstdiagnose-Kategorie.
- **Was ist potenziell integrierbar?**
  - **NICHT direkt übertragbar**: Order Flow/Footprint-Candles und GEX
    brauchen Echtzeit-Order-Book- bzw. Optionsmarktdaten (Tanuki Trade,
    ATAS, Bookmap o.ä.) -- im Repo nicht vorhanden und mit historischen
    OHLC-Daten nicht rekonstruierbar. Diskretionäre Fibonacci-/
    Value-Area-Level ebenfalls nicht 1:1 in eine deterministische
    Backtest-Regel übersetzbar, ohne die Kernaussage (Diskretion beim
    "Dominanzwechsel"-Timing) zu verlieren.
  - **Konzeptionell bereits vorhanden/bestätigt**: der NY-Open-Session-Fokus
    (erste 1,5h) deckt sich mit dem bestehenden [[ny-open-orb-sp500]]-Ansatz
    (NY-Open-ORB). Der Liquiditäts-/Teilnahme-Schwellwert-Gedanke ist
    konzeptionell verwandt mit der bereits getesteten und VERWORFENEN
    "Relative Volume at Time"-Filterung in `ny_open_orb/indicators.py`
    (Stage 3, siehe [[opening-range-breakout]]) -- dort half ein
    Volumen-Filter auf einem fixen Index-CFD-Instrument nicht. Kein neuer
    Test-Kandidat, da bereits mit negativem Ergebnis geprüft.
  - **Testbar, noch offen, aber niedrige Priorität**: eine simple
    Teilnahme-/Liquiditäts-Untergrenze ist etwas anderes als Relative
    Volume (absolut statt relativ zum eigenen 14-Tage-Schnitt) -- prinzipiell
    ein neuer, noch nicht getesteter Filter-Kandidat für `ny_open_orb`,
    aber ohne Tick-/Volumendaten auf CFD-Ebene (Broker-Volumen ist bei
    CFDs kein echtes Marktvolumen) fraglich, ob er überhaupt sauber
    replizierbar ist.
  - **Übertragbar, aber nicht quant-spezifisch**: die "guter Verlust vs.
    schlechter Verlust"-Unterscheidung und die harte "2 Verluste in Folge
    -> Stopp"-Regel sind generelle Risikomanagement-/Prozessdisziplin-
    Prinzipien, keine Backtest-Parameter -- relevant höchstens als
    Kill-Switch-Philosophie-Referenz für die live laufenden Bots (die
    bereits eigene Kill-Switches/Drawdown-Limits haben, siehe DASHBOARD-
    Status), nicht als neue Konfiguration.

**Express**
- Nächster Schritt: kein Backtest geplant -- Kernsignale sind mit den im
  Repo verfügbaren Daten (historische CFD-OHLC, kein Order-Book/GEX) nicht
  sauber replizierbar. Als konzeptionelle Referenz abgelegt, falls das Repo
  künftig Order-Flow-/Tick-Daten für ein Instrument bekommt.
- Kein Backtest-Ergebnis, daher kein Bestätigt/Verworfen-Vermerk.
