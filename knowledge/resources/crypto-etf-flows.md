# Resource: Crypto-ETF-Flows & Price Impact

Erste Notiz zum Thema Crypto in `knowledge/` -- Destillate von Papers, die
institutionelle Kapitalflüsse (Spot-ETFs) und ihre Preiswirkung auf
Kryptowährungen untersuchen.

---

## Liquidity Fragmentation and the Price Impact of ETF Flows

**Capture** -- Lim, Boon Chuan (2026, Independent Researcher, Working Paper,
Draft April 2026); erfasst 2026-08-11, manuell im Chat. Daten/Code laut
Paper unter github.com/boonchuan (nicht verifiziert).

**Organize** -- Tags: crypto, bitcoin-etf, price-impact, market-fragmentation,
kyle-lambda, order-flow, momentum. Verwandt: [[fx-microstructure]] (gleiche
Methoden-Familie -- Kyle's Lambda / Marktmikrostruktur, dort FX statt
Crypto), [[monetary-policy-spillover]] (Flow-zu-Preis-Transmission als
wiederkehrendes Motiv über Asset-Klassen hinweg). Kein bestehendes
Crypto-Project in `knowledge/` -- diese Datei ist der Ausgangspunkt.

**Distill**
- **Kernthese**: Erweitert Kyle (1985) auf fragmentierte Multi-Venue-Märkte
  (Bitcoin handelt auf >200 Exchanges). Aggregierte Preiswirkung ΔP(Q)=Λ(Q)·Q
  ist linear für moderate Flows, konvex sobald der Flow die Kapazität
  einzelner Venues übersteigt; effektive Markttiefe = harmonisches Mittel
  der Venue-Tiefen. Empirisch an 563 Handelstagen US-Spot-BTC-ETF-Netflows
  (Jan 2024-Apr 2026, Quelle Farside Investors) bestätigt:
  - IV-Kausalschätzung 0.20% Preiswirkung pro $100M Netinflow (t=2.65,
    First-Stage-F=89.5); OLS überschätzt mit 0.41% (t=10.38) durch
    Simultanität (Flows reagieren selbst auf Intraday-Returns).
  - Volatilität verstärkt die Preiswirkung (Flow×Vol-Interaktion t=2.51).
  - **Kein Reversal bis 12 Monate** (250 Handelstage) -- Gegensatz zur
    quartalsweisen Reversal-Evidenz bei Equity-Mutual-Fund-Flows (Lou 2012).
    Erklärung im Modell: venue-spezifische Deviationen werden in Stunden
    arbitriert, aber die gemeinsame Flow-Komponente ist permanent, weil
    fragmentierte Märkte keine schnelle/billige Cross-Venue-Arbitrage für
    das AGGREGAT erlauben.
  - Flow-Autokorrelation (Lag 1 = 0.530) erzeugt Next-Day-Return-
    Vorhersagbarkeit aus aktuellem Flow (t=2.26), R²=1.6% -- mechanisch,
    ökonomisch klein, Kosten würden es vermutlich auffressen.
  - GBTC-Redemptions zeigen ~50% größeren Per-Dollar-Impact als übrige
    ETF-Flows (nicht signifikant im Wald-Test, t=1.43) -- suggestiv für
    uninformed Liquidation, nicht belastbar.
- **Zentrales Modell/Filter**: Testbare Kern-Prädiktion für einen Signal-
  Baustein: `E[R(t+1) | Q(t)] = Λ·ρ·Q(t)` -- Tagesnetflow sagt
  Folgetagesrendite voraus, OHNE Mean-Reversion-Erwartung (explizites
  Gegenteil einer Fade-Strategie gegen große Flow-Tage).
- **Was ist potenziell integrierbar**: Ein "ETF-Flow-Momentum-Filter" für
  BTC -- Long-Bias am Folgetag nach starkem Netto-Inflow-Tag, verstärkt in
  Hochvolatilitätsregimen, explizit NICHT gegen den Flow faden. Voraussetzung
  ist die tägliche US-Spot-BTC-ETF-Netflow-Zeitreihe (Farside Investors) als
  Prädiktor -- reine Preisdaten reichen nicht, da der Mechanismus über den
  Flow selbst läuft, nicht über Preis-Autokorrelation.

**Express**
- **Backtest aktuell nicht möglich -- Datenlücke**: Das zentrale
  Prädiktor-Signal des Papers (tägliche ETF-Netflows von Farside Investors)
  ist nicht im Datenstack. Vorhandene Crypto-Daten (`data_cache_crypto/`,
  Binance BTCUSDT/ETHUSDT über `auction_playbook.fetch_klines`, u.a. genutzt
  in `gold_bitcoin_dual_momentum/`) liefern ausschließlich Preise, keine
  ETF-Flow-Daten. Farside hat kein offizielles API (nur HTML-Tabellen) --
  Nächster Schritt falls verfolgt: Tagesdaten manuell/per Scraping
  beschaffen und als neue Datenquelle cachen, analog zum FRED-Loader-Muster
  aus [[bond-yield-spread-indikator]].
- **Cross-Check**: Kein Baustein im Repo nutzt aktuell Flow-Daten, daher
  keine direkt übertragbare Formel auf eine bestehende Strategie. Konzeptionell
  relevant für `gold_bitcoin_dual_momentum` (BTC-Preisdaten vorhanden): die
  "kein Reversal, permanenter Impact"-Evidenz spricht tendenziell gegen
  Mean-Reversion-Fading großer BTC-Bewegungen und stützt damit indirekt eine
  Momentum-Grundannahme -- aber ohne Flow-Daten bleibt das eine Beobachtung,
  kein testbarer Filter.
- **Ergebnis**: n/a -- kein Test durchgeführt, Grund s.o.
