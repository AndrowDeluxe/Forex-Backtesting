"""151 Trading Strategies -- Wissens-Sammelseite, kein Backtest-Dashboard.

Quelle: Kakushadze, Z. & Serur, J.A. (2018), "151 Trading Strategies",
SSRN Working Paper (abstract_id=3247865) / Palgrave Macmillan. Ein
Uebersichts-Survey ueber ~150 Strategie-Familien quer durch alle Asset-
Klassen (Optionen, Aktien, ETFs, Fixed Income, Indizes, Volatilitaet, FX,
Rohstoffe, Futures, strukturierte Assets, Convertibles, Krypto, Makro, ...).

Diese Seite ist bewusst ein "erstmal alles sammeln"-Ablageort (User-Wunsch,
2026-08-06): eigenstaendig aus dem Paper destillierte Grundlagen und
Strategiebausteine, noch NICHT sortiert/gebacktestet. Sortierung, Verschieben
einzelner Bausteine nach "Strategie Bestandteile"/Education und Backtests
sind bewusst ein spaeterer, separater Schritt.
"""

import streamlit as st

st.set_page_config(page_title="151 Trading Strategies", page_icon=":material/auto_stories:", layout="wide")

st.markdown("## :material/auto_stories: 151 Trading Strategies -- Paper-Destillat")
st.caption(
    "Quelle: Kakushadze, Z., Serur, J.A. (2018). \"151 Trading Strategies.\" "
    "SSRN Working Paper, abstract_id=3247865 (spaeter Palgrave Macmillan)."
)
st.info(
    "**Sammelseite, kein Backtest.** Hier liegt erstmal alles, was aus dem Paper "
    "eigenstaendig destilliert wurde -- Grundlagen, einzeln formulierte Bausteine, "
    "Gold-Fokus und Verknuepfungsideen mit den bestehenden Strategien in diesem "
    "Repo. Sortierung/Verschieben nach `Strategie Bestandteile` bzw. Backtests "
    "folgen erst danach, auf Zuruf.",
    icon=":material/inventory_2:",
)

st.space("medium")

tab_grundlagen, tab_bausteine, tab_gold, tab_verknuepfung = st.tabs(
    ["Grundlagen", "Strategiebausteine nach Asset-Klasse", "Gold-Bausteine", "Verknuepfungsideen"]
)

# =============================================================================
# Tab 1: Grundlagen
# =============================================================================
with tab_grundlagen:
    st.markdown("### Was das Paper eigentlich ist")
    st.markdown(
        "Kein einzelnes Modell, sondern ein **breiter Katalog**: ~150 Strategie-"
        "Familien in kompakter Form (Idee, grobe Mechanik, manchmal ein "
        "Beispiel-Payoff oder eine Formel), quer durch praktisch jede Asset-"
        "Klasse, die an institutionellen Maerkten gehandelt wird. Der Wert fuer "
        "uns liegt nicht in copy-paste-baren Handelsregeln (dafuer ist das Paper "
        "zu knapp), sondern in den **wiederkehrenden Grundmustern**, die quer "
        "durch alle Kapitel auftauchen -- genau diese Muster stecken (oft ohne "
        "es explizit zu benennen) schon in mehreren bestehenden Strategien "
        "dieses Repos."
    )

    st.markdown("### Die vier Grundmuster, die sich durch fast alle 150 Strategien ziehen")

    col_a, col_b = st.columns(2)
    with col_a:
        st.success(
            "**1. Relative-Value / Arbitrage**\n\nZwei eng verwandte Instrumente "
            "(Paar, Index vs. Komponenten, Kassa vs. Future, Optionsflügel) "
            "laufen auseinander -- Wette auf Rueckkehr des Spreads, nicht auf "
            "eine Richtung. Beispiele im Paper: Pairs Trading, Index-Dispersion, "
            "Cash-and-Carry, Convertible-Arbitrage, Triangular-FX-Arbitrage.",
            icon=":material/balance:",
        )
        st.warning(
            "**2. Carry**\n\nEine strukturelle Renditequelle wird vereinnahmt, "
            "solange sich das Umfeld nicht aendert (Zinsdifferenz, Contango/"
            "Backwardation-Rollrendite, Optionspraemie). Funktioniert lange gut, "
            "bricht aber in Stressphasen abrupt (\"picking up nickels in front "
            "of a steamroller\"). Beispiele: FX Carry Trade, VIX-Futures-Roll, "
            "Storage/Convenience-Yield bei Rohstoffen, kurze Vola (Straddle/"
            "Strangle-Verkauf).",
            icon=":material/trending_flat:",
        )
    with col_b:
        st.info(
            "**3. Momentum / Trend**\n\nEinmal in Bewegung, bleibt ein Markt "
            "tendenziell in Bewegung -- über Wochen (Preis-Momentum bei Aktien) "
            "genauso wie über Monate (Futures-Trendfolge/CTA-Stil). Braucht fast "
            "immer einen Filter, der Seitwaerts-/Contraction-Phasen aussortiert "
            "(z.B. das Contraction-Expansion-Prinzip, das schon bei ORB in "
            "diesem Repo verwendet wird).",
            icon=":material/trending_up:",
        )
        st.error(
            "**4. Mean-Reversion**\n\nExtreme Abweichungen von einem Anker "
            "(Fair Value, gleitendem Durchschnitt, VWAP, historischem Spread) "
            "ziehen zurueck. Das Gegenstueck zu Momentum -- beide Muster "
            "koexistieren im selben Markt, aber auf unterschiedlichen "
            "Zeitskalen/Regimes. Genau die Spannung, die z.B. bei "
            "`checklist_strategy`'s Regime-Filter-Suche schon sichtbar wurde.",
            icon=":material/sync:",
        )

    st.markdown("### Eine Meta-Beobachtung, die sich mit unseren eigenen Befunden deckt")
    st.markdown(
        "Das Paper selbst ist explizit ein Katalog von *Ideen*, keine Sammlung "
        "belastbarer, geprüfter Edges -- es macht kaum Aussagen zu Kosten, "
        "Slippage oder Out-of-Sample-Robustheit einzelner Strategien. Das passt "
        "zu unserem eigenen Muster in diesem Repo: fast jede woertlich "
        "umgesetzte Paper-These (ADX-VWAP, CLS-Varianten, Auction Playbook) war "
        "bei ehrlicher Pruefung kein robuster Edge -- der Wert einer solchen "
        "Quelle liegt im **Baustein-Vokabular**, nicht im fertigen Rezept. "
        "Genau deshalb ist diese Seite auch nur eine Bausteinsammlung, kein "
        "\"fertige Strategie\"-Claim."
    )

    st.markdown("### Der Backtesting-Appendix des Papers")
    st.markdown(
        "Das Paper enthaelt einen eigenen R-Appendix (`qrm.backtest`-Funktion) "
        "fuer generisches Signal-Backtesting -- konzeptionell dasselbe, was "
        "`strategy/backtest.py` und die anderen `*_strategy/backtest.py`-Module "
        "hier schon leisten (Long/Short-Signal rein, P&L/Metriken raus). Keine "
        "neue Erkenntnis fuer die Infrastruktur, aber eine Bestaetigung, dass "
        "der bestehende Aufbau (Signal-Funktion getrennt von Backtest-Engine, "
        "getrennt von Metriken) einem Standardmuster entspricht."
    )

# =============================================================================
# Tab 2: Strategiebausteine nach Asset-Klasse
# =============================================================================
with tab_bausteine:
    st.caption(
        "Breite statt Tiefe (auf Wunsch): jeder Baustein ist eigenstaendig "
        "formuliert (keine Paper-Zitate), knapp gehalten, mit einem Bezug "
        "darauf, was er fuer dieses Repo bedeuten koennte. Kapitelverweise "
        "grob, nicht auf die Nachkommastelle."
    )

    with st.expander(":material/candlestick_chart: Optionen (Kap. 2) -- Spreads, Straddle, Condor & Co.", icon=":material/candlestick_chart:"):
        st.markdown(
            """
**Kernidee:** Optionsstrategien kombinieren Kaeufe/Verkaeufe mehrerer Strikes/
Laufzeiten, um ein bestimmtes Payoff-Profil zu formen -- Richtung, Vola oder
Zeitwert gezielt isoliert statt alles gleichzeitig zu handeln wie bei einer
nackten Aktie/einem Future.

- **Vertical Spreads** (Bull/Bear Call/Put): begrenzter Gewinn UND begrenztes
  Risiko, im Grunde eine "Richtungswette mit Deckel" -- güstiger als eine
  nackte Option, aber Gewinn gekappt.
- **Straddle/Strangle:** reine Vola-Wette (long = Ausbruch erwartet, short =
  Vola-Praemie vereinnahmen, Carry-Muster von oben).
- **Condor/Butterfly:** Wette auf *begrenzte* Bewegung -- Gewinn maximal wenn
  der Kurs am Verfallstag nahe einem Zielpunkt bleibt. Strukturell das
  Gegenteil eines Trendfolgers.
- **Calendar Spread:** kurze naahe Laufzeit gegen lange ferne Laufzeit --
  Wette auf die Form der Vola-Terminstruktur, nicht auf Richtung.
- **Risk Reversal:** synthetische Long/Short-Position aus Call+Put statt der
  Aktie selbst, oft zur Absicherung/als Sentiment-Indikator (Put-Call-Skew)
  genutzt.

**Bezug zum Repo:** wir handeln aktuell nirgends echte Optionen (keine
Infrastruktur fuer Optionsdaten). Der uebertragbare Teil ist die **Skew/Vola-
Terminstruktur als Kontext-Signal** (siehe Vola-Kapitel unten) -- nicht die
Options-Payoffs selbst.
"""
        )

    with st.expander(":material/show_chart: Aktien -- Momentum, Mean-Reversion, Stat-Arb (Kap. 3)", icon=":material/show_chart:"):
        st.markdown(
            """
**Price Momentum (Kap. 3.1):** Rang-Sortierung nach Rendite der letzten
3-12 Monate, long Top-Dezil / short Bottom-Dezil, meist mit 1-Monats-Skip
(vermeidet kurzfristige Reversal-Kontamination). Der akademische
Standard-Baustein hinter fast jeder systematischen Trendfolge.

**Pairs Trading / Stat-Arb (Kap. 3.8-3.10):** zwei ko-integrierte
Instrumente, Spread z-normiert, Entry bei Extremabweichung, Exit bei
Rueckkehr zum Mittel -- die Aktien-Variante desselben Prinzips, das unser
eigenes OU-Modell fuer FX/Indizes nutzt (Ornstein-Uhlenbeck-Mean-Reversion).
Cluster-/gewichtete Regressions-Varianten bilden den Spread aus mehreren
Instrumenten statt nur zwei.

**KNN-/ML-Klassifikation:** einfache Nearest-Neighbor-Klassifikation von
Kursmustern in "kaufen/verkaufen/halten" -- konzeptionell simpler als die im
Repo schon vorhandenen State-Machines (Auction Playbook, CLS-Strategie),
aber derselbe Grundgedanke: Marktzustand klassifizieren, bevor gehandelt
wird.

**Bezug zum Repo:** die Mean-Reversion-Variante ist praktisch identisch zum
[[ou-paper-backtest-project|OU-Modell]] (bereits gebaut, S&P/DAX/Nasdaq
getestet). Price-Momentum ist strukturell verwandt mit `triple_ma`'s
TEMA/TSMA-Bausteinen (beide sind Trendfortsetzungs-Wetten, nur andere
Signalquelle: Rang vs. gleitender Durchschnitt).
"""
        )

    with st.expander(":material/pie_chart: ETFs -- Sektor- & Faktor-Rotation (Kap. 4)", icon=":material/pie_chart:"):
        st.markdown(
            """
**Sektor-Rotation:** monatlich/quartalsweise in die Sektor-ETFs mit der
staerksten relativen Staerke (Momentum-Rang) umschichten, Rest halten/meiden.

**Alpha-/Faktor-Rotation:** dasselbe Prinzip eine Ebene abstrakter -- statt
Sektoren werden Faktor-ETFs (Value, Quality, Low-Vol, Momentum selbst)
rotiert, je nachdem welcher Faktor gerade "arbeitet".

**Bezug zum Repo:** kein direktes Aequivalent vorhanden, aber konzeptionell
uebertragbar auf unsere bestehende Multi-Asset-Instrumentenliste (6 FX-
Majors + Gold/Silber/Oel/Indizes) -- ein monatliches Relative-Staerke-Ranking
ueber genau diese Instrumente waere ein neuer, eigenstaendiger Baustein
(bisher testen wir jede Strategie pro Instrument einzeln, nie im
Rotations-/Ranking-Verbund).
"""
        )

    with st.expander(":material/account_balance: Fixed Income -- Ladder, Butterfly, Carry & Roll-Down (Kap. 5)", icon=":material/account_balance:"):
        st.markdown(
            """
**Bullet/Barbell/Ladder:** drei Arten, ein Anleihe-Portfolio ueber Laufzeiten
zu verteilen (konzentriert / an beiden Enden / gleichmaessig gestaffelt) --
unterschiedliche Konvexitaets-/Durationsprofile bei gleicher
Ziel-Duration.

**Duration/Convexity-Butterfly:** Wette auf die *Form* der Zinskurve
(Versteilerung/Abflachung/Buckel), nicht auf das Zinsniveau selbst --
strukturell verwandt mit Calendar Spreads bei Optionen (Terminstruktur-Wette
statt Richtungswette).

**Carry & Roll-Down:** eine Anleihe "rollt" mit der Zeit die Kurve
herunter (wird kuerzer, wandert bei normaler/steiler Kurve zu tieferer
Rendite/hoeherem Preis) -- reiner Zeitablauf-Ertrag ohne Marktbewegung,
dasselbe Carry-Muster wie FX Carry oder Futures-Contango-Roll.

**Bezug zum Repo:** keine Fixed-Income-Instrumente im Repo vorhanden. Der
uebertragbare Baustein ist **Roll-Down/Carry als generisches Konzept** --
bei uns am ehesten anwendbar auf FX (Zinsdifferenz, siehe FX-Kapitel unten).
"""
        )

    with st.expander(":material/query_stats: Indizes -- Dispersion & Cash-and-Carry (Kap. 6)", icon=":material/query_stats:"):
        st.markdown(
            """
**Dispersion Trading:** Index-implizite Vola vs. die *gewichtete Summe* der
Einzelaktien-Volas -- wenn Diversifikation ueberteuert/unterteuert
eingepreist ist (Korrelationswette, nicht Richtungswette).

**Index-Rebalancing-Arbitrage:** vor einer bekannten Index-Umschichtung
(Auf-/Abstieg) antizipieren, dass Index-Fonds mechanisch kaufen/verkaufen
muessen -- Wette auf vorhersehbaren, nicht-informierten Orderflow.

**Cash-and-Carry:** Future kaufen/verkaufen gegen die physische
Replikation des Index (oder umgekehrt), Spread zwischen beiden vereinnahmen
-- reine Arbitrage, kein Marktrisiko bei exakter Absicherung.

**Bezug zum Repo:** Dispersion braucht Optionsdaten (nicht vorhanden).
Cash-and-Carry ist konzeptionell am naechsten an dem, was `ou_paper_backtest`
(Mean-Reversion ueber ein breites Aktienuniversum) und die OU-Modell-Familie
ohnehin schon als Grundidee nutzen: struktureller Spread statt Richtung.
"""
        )

    with st.expander(":material/monitoring: Volatilitaet -- VIX-Futures, Variance Swaps, Vola-Praemie (Kap. 7)", icon=":material/monitoring:"):
        st.markdown(
            """
**VIX-Futures-Terminstruktur-Carry:** die Kurve ist meist in Contango (Roll
kostet), gelegentlich Backwardation (Roll bringt Ertrag, meist in
Stressphasen) -- ein weiteres reines Carry-Muster, diesmal auf Vola selbst.

**Variance Swaps / Vola-Risikopraemie:** implizite Vola liegt im Mittel
ueber der spaeter realisierten Vola -- struktureller Verkaeufer-Vorteil, aber
mit fetten linken Taeln (Crash-Risiko), dasselbe "Nickel vor der Dampfwalze"-
Muster wie beim Options-Straddle-Verkauf.

**Gamma-Scalping/Delta-Hedging:** eine Optionsposition wird laufend
delta-neutral gehalten -- der Hedge-Turnover selbst wird zur Ertragsquelle
(Long Gamma: profitiert von Bewegung; Short Gamma: profitiert von
Ruhe).

**Bezug zum Repo:** kein Optionsbuch vorhanden, aber der **VIX-Level/-Struktur
als Kontext-Filter** ist direkt uebertragbar -- genau das wurde beim
Asian-Range-Breakout-Regimefilter schon *getestet* (`vix.py`,
[[fx-vwap-adx-strategy-project]]: kein robuster Edge gefunden, aber die
Infrastruktur existiert bereits und liesse sich fuer andere Strategien
wiederverwenden).
"""
        )

    with st.expander(":material/currency_exchange: Waehrungen -- Carry, HP-Filter-Momentum, Triangular Arb (Kap. 8)", icon=":material/currency_exchange:"):
        st.markdown(
            """
**FX Carry Trade:** long Hochzins-, short Niedrigzins-Waehrung, vereinnahmt
die Zinsdifferenz solange der Wechselkurs nicht gegenlaeufig genug bewegt
(deckte-interest-parity-Verletzung als struktureller Edge, mit
Crash-Risiko bei Risk-Off-Phasen -- selbes Carry-Muster wie ueberall sonst).

**HP-Filter-Momentum:** ein Hodrick-Prescott-Filter trennt Trend von
Zyklus/Rauschen in der Kursreihe; Positionsrichtung folgt der geglaetteten
Trendkomponente statt des Rohkurses -- ein alternativer Weg zum selben
Ziel wie unser Kalman-Filter-Baustein (`strategy/kalman_filter.py`):
Signal glaetten, bevor eine Trend-Entscheidung getroffen wird.

**Triangular Arbitrage:** Preisinkonsistenzen zwischen drei Waehrungspaaren
(z.B. EUR/USD, USD/JPY, EUR/JPY) mechanisch ausnutzen -- braucht Latenz-
Vorteil und ist bei liquiden Majors praktisch wegarbitriert; eher als
Konzept relevant (Konsistenz-Check ueber verwandte Instrumente) denn als
handelbare Strategie fuer uns.

**Bezug zum Repo:** direkt anwendbar auf unsere 6 FX-Majors. HP-Filter ist
ein *alternativer* Glaettungs-Baustein zum bestehenden Kalman-Filter -- eine
sinnvolle A/B-Erweiterung des schon durchgefuehrten
`research_kalman_filter_adx_vwap.py`-Tests
([[fx-vwap-adx-strategy-project]]: Kalman half der ADX-VWAP-Strategie
NICHT), statt eines neuen unabhaengigen Bausteins.
"""
        )

    with st.expander(":material/grain: Rohstoffe -- Storage, Backwardation/Contango, Saisonalitaet (Kap. 9)", icon=":material/grain:"):
        st.markdown(
            """
**Storage/Convenience-Yield:** wer physisch lagert statt Futures zu halten,
verzichtet auf Optionalitaet (kurzfristig verfuegbar zu sein) -- dieser Wert
zeigt sich in der Futures-Kurvenform (Backwardation = Lager-Knappheit,
Contango = Lager-Ueberschuss). Bei Gold (kein Verbrauchsgut, kaum
"Convenience") ist dieser Effekt strukturell schwaecher als bei Oel/
Agrarrohstoffen.

**Roll-Yield-Strategien:** systematisch in Rohstoffe mit staerkster
Backwardation investieren (bester Rollertrag), analog zum VIX-Futures-
Carry oben, nur auf physische Rohstoffe uebertragen.

**Saisonalitaet:** wiederkehrende Muster (Erntezyklen, Heizsaison bei
Energie) -- bei Gold am ehesten indirekt relevant (saisonale
Nachfragemuster z.B. um indische Hochzeitssaison/Diwali, schwaecher als bei
Agrar/Energie).

**Bezug zum Repo:** Roll-Yield/Backwardation-Signale brauchen Futures-
Kurvendaten (mehrere Faelligkeiten) -- aktuell nicht im Datenbestand
(Dukascopy liefert Kassa-/CFD-artige Reihen, keine Terminkurve). Waere ein
neuer Datenbeschaffungs-Baustein, kein reiner Code-Baustein.
"""
        )

    with st.expander(":material/trending_up: Futures -- Trendfolge/CTA, Calendar Spreads (Kap. 10)", icon=":material/trending_up:"):
        st.markdown(
            """
**Time-Series-Momentum / CTA-Trendfolge (Kap. 10.4):** long wenn die
Rendite der letzten n Monate positiv war, short wenn negativ -- pro
Instrument einzeln (im Unterschied zum Cross-Sectional-Momentum bei
Aktien oben, das *relativ* zu anderen Aktien rangiert). Der Klassiker
hinter den meisten CTA-/Managed-Futures-Fonds.

**Calendar/Futures-Spread-Trading:** naahe gegen ferne Faelligkeit
desselben Kontrakts -- Wette auf die Kurvenform, nicht auf den
Kassa-Kurs (dasselbe Muster wie Options-Calendar-Spreads und
Fixed-Income-Butterflies weiter oben -- Terminstruktur statt Richtung
zieht sich durch fast jede Asset-Klasse im Paper).

**Bezug zum Repo:** Time-Series-Momentum ist strukturell fast identisch zu
`triple_ma`'s einfachster Variante (n=252 EMA/SMA long/flat) --
bereits gebaut und getestet (profitabel vor Kosten, aber deutlich hinter
Buy & Hold, siehe [[fx-vwap-adx-strategy-project]]). Calendar-Spreads
brauchen wieder Terminkurven-Daten (siehe Rohstoffe oben).
"""
        )

    with st.expander(":material/hub: Strukturierte Assets, Convertibles, Sonstiges (Kap. 11-18)", icon=":material/hub:"):
        st.markdown(
            """
Knapp gehalten -- diese Kapitel sind fuer unser Setup am wenigsten
uebertragbar, aber der Vollstaendigkeit halber:

- **CDO-Tranchen/Korrelationshandel (Kap. 11):** Wette auf
  Ausfallkorrelation zwischen vielen Krediten -- braucht Kreditderivate-
  Infrastruktur, kein Bezug zu FX/Gold/Indizes.
- **Convertible Arbitrage (Kap. 12):** Wandelanleihe kaufen, zugrunde
  liegende Aktie leerverkaufen (Delta-Hedge) -- vereinnahmt die
  eingebettete Optionalitaet, braucht Einzelanleihen-/Aktienzugriff.
- **Steuerarbitrage (Kap. 13):** z.B. Dividend Capture, Tax-Loss
  Harvesting -- steuerjurisdiktionsabhaengig, fuer ein Backtest-Repo ohne
  konkretes Konto-Setup nicht sinnvoll modellierbar.
- **Wetter-/Energie-Spread-Derivate (Kap. 15):** Spark Spread (Strom vs.
  Gas), Wetterderivate -- Nischenmaerkte ohne Datenzugang hier.
- **Distressed Debt (Kap. 16), Immobilien/REITs (Kap. 17), Cash/Repo
  (Kap. 18):** alle mit eigener, spezialisierter Datenbasis (Bond-Preise,
  REIT-Kurse, Repo-Saetze), aktuell ausserhalb des Repo-Datenbestands.

**Bezug zum Repo:** keiner dieser Bloecke liefert einen direkt umsetzbaren
Baustein mit den vorhandenen Datenquellen (Dukascopy FX/Metalle/Indizes,
yfinance, Binance). Bewusst nur grob dokumentiert statt vertieft.
"""
        )

    with st.expander(":material/currency_bitcoin: Krypto -- ANN-Kursprognose, Sentiment (Kap. 19)", icon=":material/currency_bitcoin:"):
        st.markdown(
            """
**ANN-basierte BTC-Prognose:** ein neuronales Netz sagt die naechste
Kursbewegung aus technischen Features voraus -- EMA (Trend), EMSD
(exponentiell geglaettete Standardabweichung, ein Vola-Proxy) und RSI
(Momentum-Oszillator) als Eingaben. Im Kern klassisches Feature-
Engineering, nur mit einem ML-Modell statt fester Regeln am Ende.

**Sentiment-basiert (Naive-Bayes-Bernoulli auf Twitter-Text):** Tweets als
bullish/bearish klassifizieren, aggregiertes Sentiment als zusaetzliches
Signal -- braucht eine Text-/Sentiment-Datenquelle, die aktuell nicht im
Repo vorhanden ist.

**Bezug zum Repo:** `auction_playbook` handelt bereits BTCUSDT/ETHUSDT
(Binance) mit einer State-Machine, aber ohne ML-Komponente. Die
EMA/EMSD/RSI-Feature-Idee liesse sich als *zusaetzliches* Regime-/
Filter-Signal in `auction_playbook` einbauen, ohne die bestehende
State-Machine zu ersetzen -- naeher an "neuer Filter-Baustein" als an
"neue Strategie". Sentiment-Baustein braucht zuerst eine Datenquelle,
aktuell nicht vorhanden.
"""
        )

    with st.expander(":material/public: Global Macro & Infrastruktur (Kap. 20-21)", icon=":material/public:"):
        st.markdown(
            """
**Global Macro:** thematische Positionen aus makrooekonomischen
Ungleichgewichten (Leistungsbilanz, Zinsdifferenzen, Wachstumsdivergenz)
-- eher diskretionaer/langfristig als systematisch/kurzfristig, passt
schlecht zu diesem Repos Intraday-/Swing-Fokus.

**Infrastruktur-Investments:** Beteiligungen an realen Infrastruktur-
Assets (Maut, Energienetze) -- Private-Markets-Charakter, kein liquides,
backtestbares Instrument.

**Bezug zum Repo:** beide Kapitel liefern eher *Kontext* (z.B. warum
Zinsdifferenzen den FX-Carry-Trade treiben, siehe FX-Kapitel oben) als
einen eigenstaendigen, testbaren Baustein.
"""
        )

# =============================================================================
# Tab 3: Gold-Bausteine
# =============================================================================
with tab_gold:
    st.markdown("### Auf Gold zugeschnitten -- welche Bausteine aus dem Paper wirklich passen")
    st.markdown(
        "Gold ist im Repo bereits gut abgedeckt (`asian_range_breakout` als "
        "einzige bislang tragfaehige Kante, PF 1.09-1.12, siehe "
        "[[fx-vwap-adx-strategy-project]]) und laeuft ausserdem als eigener "
        "Live-Bot (`GoldASB-MT5-Bridge`). Diese Auswahl filtert die Bausteine "
        "von oben gezielt auf das, was fuer **Gold spezifisch** sinnvoll ist -- "
        "nicht als neue Strategie, sondern als moegliche Ergaenzungs-Filter "
        "oder eigenstaendige neue Ideen fuer spaeteren Backtest."
    )

    with st.expander(":material/looks_one: Vola-Risikopraemie / VIX-Aenderungsrate -- getestet, verworfen", icon=":material/looks_one:"):
        st.markdown(
            """
Gold gilt klassisch als "Safe Haven" -- steigt tendenziell, wenn Aktien-
Vola (VIX) steigt. Der statische VIX-Level-Filter war schon vorher getestet
([[fx-vwap-adx-strategy-project]]: kein robuster Bucket-Edge, Dünn-Sample-
Rauschen). **Update 2026-08-07:** die naeherliegende Variante -- VIX-
*Aenderungsrate* ("frischer Vola-Schub" statt statisches Niveau) -- wurde
jetzt ebenfalls getestet (`scripts/research_gold_dxy_vix_change_filters.py`,
gegen die ADX-gefilterte Produktionskonfiguration, Fenstersweep 3/5/10/20
Tage plus IS/OOS-Split).

**Ergebnis: ebenfalls keine robuste Kante** -- bei 3/5/10 Tagen ist "kein
Spike" durchweg leicht besser als "Spike" (Fenster=5: PF 1.15 vs. 1.06,
konsistent in IS und OOS), bei 20 Tagen kippt das Vorzeichen -- dasselbe
Rauschmuster wie beim Level-Filter. **Nicht implementiert**, siehe
`app_pages/asian_range_breakout.py` (Tab "Strategiebestandteile") fuer die
volle Tabelle.
"""
        )

    with st.expander(":material/looks_two: Dollar-Index (DXY) als Cross-Asset-Kontext-Signal -- getestet, Gegenteil gefunden", icon=":material/looks_two:"):
        st.markdown(
            """
Aus dem FX-Carry-/Cross-Asset-Kapitel: Gold ist in USD notiert, ein
generell schwaecher/staerker werdender Dollar (DXY) ist ein struktureller
Rueckenwind/Gegenwind fuer Gold, unabhaengig vom Gold-Chart selbst. Aehnlich
zur bereits getesteten "Cross-Pair-Confirmation" in `cls_advanced.py`.

**Update 2026-08-07, getestet:** Hypothese war "Trades *mit* dem DXY-Trend
halten besser als Trades dagegen" (`asian_range_breakout/dxy.py` +
`filters.py::attach_dxy`/`attach_series_change`, Fenstersweep 3/5/10/20
Tage). **Ergebnis: das Gegenteil, und zwar konsistent** -- ueber alle 4
Fenster sowie IS und OOS haben Trades GEGEN den DXY-Trend den hoeheren
Profit Factor (Fenster=5: PF 1.21 "misaligned" vs. 1.04 "aligned", IS 1.14
vs. 0.95, OOS 1.25 vs. 1.11). Konsistent im Vorzeichen, aber **nicht
implementiert** -- kein ökonomisch plausibler Mechanismus fuer ein
*umgekehrtes* Signal, und dieses Repo hat schon mehrfach erlebt, dass ein
zunaechst konsistentes Muster bei genauerer Pruefung Rauschen war. Als
Beobachtung dokumentiert (siehe Asian-Range-Breakout-Dashboard), nicht als
Filter gebaut.
"""
        )

    with st.expander(":material/looks_3: Roll-Yield/Terminstruktur -- eher nicht umsetzbar", icon=":material/looks_3:"):
        st.markdown(
            """
Aus dem Rohstoff-Kapitel waere Backwardation/Contango in der Gold-
Futures-Kurve ein potenzieller Carry-Baustein -- **aber** Gold hat (anders
als Oel/Agrar) kaum physischen Convenience-Yield, das Signal ist strukturell
schwach, und wir haben ohnehin keine Mehrfach-Faelligkeits-Daten im
Bestand (Dukascopy liefert nur eine Kassa-/CFD-artige Reihe). Bewusst als
"eher nicht weiterverfolgen" markiert statt als offene Aufgabe.
"""
        )

    with st.expander(":material/looks_4: Time-Series-Momentum als eigenstaendiger Gold-Baustein", icon=":material/looks_4:"):
        st.markdown(
            """
`triple_ma` deckt das fuer Gold technisch schon ab (n=252 EMA/SMA
long/flat, bereits getestet: profitabel vor Kosten, aber hinter Buy & Hold
zurueck). Aus dem Futures-Kapitel kommt keine neue Variante hinzu, die
nicht schon abgedeckt waere -- eher eine Bestaetigung, dass der
bestehende Baustein den Standard-Ansatz aus der Literatur korrekt
abbildet, kein neuer Arbeitsauftrag.
"""
        )

    st.error(
        "**Ehrlich eingeordnet (Update 2026-08-07):** beide konkret pruefbaren Ideen aus diesem "
        "Paper -- VIX-Aenderungsrate und DXY-Kontextfilter -- wurden inzwischen gegen die "
        "ADX-gefilterte Produktionskonfiguration des Asian-Range-Breakout getestet. **Keine "
        "liefert eine implementierbare Kante**: die VIX-Aenderungsrate ist genauso Rauschen wie "
        "der schon vorher verworfene Level-Filter, und der DXY-Filter zeigt zwar ein konsistentes "
        "Muster, aber genau umgekehrt zur Hypothese (ohne plausiblen Mechanismus, daher nicht "
        "eingebaut). Aus dem 151-Strategies-Paper kommt damit aktuell **kein** neuer, "
        "umsetzbarer Gold-Baustein -- passt zum Grundmuster dieses Repos, dass woertlich "
        "uebertragene Paper-Ideen selten ohne Weiteres tragen. Details: "
        "`app_pages/asian_range_breakout.py` (Tab \"Strategiebestandteile\").",
        icon=":material/fact_check:",
    )

# =============================================================================
# Tab 4: Verknuepfungsideen
# =============================================================================
with tab_verknuepfung:
    st.markdown("### Wie neue Bausteine mit Bestehendem zusammenspielen koennten")
    st.markdown(
        "Konkrete, priorisierte Hypothesen, die aus den obigen Bausteinen und "
        "den schon vorhandenen Strategien/Bausteinen dieses Repos entstehen -- "
        "noch keine davon ist getestet. Gedacht als Ausgangsliste fuer die "
        "naechste Runde, wenn wir gemeinsam sortieren."
    )

    st.markdown("#### Hoechste Prioritaet (direkt mit vorhandenen Daten/Code testbar)")
    st.markdown(
        """
1. ~~**DXY-Kontextfilter fuer Gold-Strategien**~~ -- **getestet, 2026-08-07:**
   konsistentes Muster, aber genau umgekehrt zur Hypothese (siehe
   Gold-Bausteine-Tab) -- nicht implementiert, kein plausibler Mechanismus.
2. **HP-Filter als A/B-Alternative zum Kalman-Filter** auf ADX-VWAP --
   derselbe Testaufbau wie `research_kalman_filter_adx_vwap.py` existiert
   schon, nur die Glaettungsmethode tauschen. **Noch offen.**
3. ~~**VIX-Aenderungsrate statt Level**~~ -- **getestet, 2026-08-07:**
   genauso Rauschen wie der Level-Filter (siehe Gold-Bausteine-Tab) --
   nicht implementiert.
"""
    )

    st.markdown("#### Mittlere Prioritaet (brauchen etwas neuen Code, keine neuen Daten)")
    st.markdown(
        """
4. **Cross-Sectional-Relative-Staerke-Ranking** ueber alle 11 Instrumente
   (FX-Majors + Gold/Silber/Oel/Indizes), monatlich neu sortiert, nur die
   Top-N traden -- uebertraegt die ETF-/Sektor-Rotations-Idee auf unser
   bestehendes Multi-Asset-Universum, komplementaer zu den Instrument-
   fuer-Instrument-Tests, die wir bisher ausschliesslich fahren.
5. **EMA/EMSD/RSI-Feature-Filter fuer `auction_playbook`** (Krypto) --
   ergaenzt die bestehende State-Machine um ein einfaches Regime-Signal,
   ohne sie zu ersetzen.
"""
    )

    st.markdown("#### Eher nicht weiterverfolgen (Daten-/Infrastruktur-Luecke)")
    st.markdown(
        """
6. Roll-Yield/Terminstruktur-Strategien (Rohstoffe, VIX-Futures-Carry,
   Calendar Spreads) -- brauchen Mehrfach-Faelligkeits-Daten, die aktuell
   in keiner Datenquelle des Repos vorhanden sind.
7. Alles, was echte Optionsdaten braucht (Dispersion, Straddle/Strangle-
   Vola-Praemie, Convertible-Arbitrage) -- kein Optionsbuch im Repo.
8. Sentiment-/Text-basierte Signale (Twitter-Krypto-Sentiment) -- keine
   Textdatenquelle angebunden.
"""
    )

    st.info(
        "**Naechster Schritt:** nichts hiervon ist bereits umgesetzt oder "
        "gebacktestet. Sobald du dir diese Seite angeschaut hast, sortieren wir "
        "gemeinsam, was in `Strategie Bestandteile` wandert, was direkt einen "
        "Backtest bekommt und was hier als Ideen-Pool bleibt.",
        icon=":material/hourglass_empty:",
    )
