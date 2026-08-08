"""Fuenf FX-Papers (User-Upload, 2026-08-09) -- Wissens-Sammelseite, kein
Backtest-Dashboard, gleiches Muster wie goldi_papers_202608.py/paper151.py:
eigenstaendig destillierte Kernaussagen/Bausteine/Machbarkeit pro Paper, ein
Tab pro Paper. Anders als der Gold-Batch liegt hier ein besonderer Fund vor:
Paper 5 ist mit sehr hoher Wahrscheinlichkeit die (bisher im Repo nicht
attributierte) theoretische Quelle von `strategy/adx_vwap.py` selbst.

Quellen:
1. Chaboud, Rime, Sushko (2023) -- The Foreign Exchange Market (BIS/Fed,
   fuer "The Research Handbook of Financial Markets") -- Marktstruktur-Survey,
   keine Handelsstrategie.
2. Lu Jialong (2026) -- Fibonacci Ratios Are Weighted Averages -- reine
   Mathematik (SSRN 4063213 ist NICHT dieses Paper -- eigene, undatierte
   SSRN-ID im PDF nicht angegeben), zeigt VWAP/Fibonacci/gleitender
   Durchschnitt als dieselbe gewichtete-Mittelwert-Familie.
3. Leander Seeck (2026) -- Intraday Momentum in Spot FX and Currency Futures
   (Limes Technologies, SSRN Working Paper) -- London-Open-30-Min-Momentum,
   JPY-Amplifikation, Kosten-Barriere, Spot-vs-Futures-Divergenz bei BOJ YCC.
4. Martin D.D. Evans (2017) -- Forex Trading and the WMR Fix (Georgetown,
   Journal of Banking and Finance, SSRN 2487991) -- peer-reviewed,
   Pre-Fix-Volatilitaet + negative Pre/Post-Fix-Autokorrelation, im Kontext
   der 2013-2015 Kollusions-Aufdeckung.
5. Amaanullah Bhatti / Hafzan Osmanoglu (2026) -- Momentum Exhaustion and
   Fair Value Reversion: An ADX-Conditioned VWAP Strategy in FX Markets
   (Symbiosis International University, SSRN 6454659) -- reines Theorie-
   Paper, keine eigenen Backtest-Ergebnisse.
"""

import streamlit as st

st.set_page_config(page_title="FX-Papers (Aug. 2026)", page_icon=":material/currency_exchange:", layout="wide")

st.markdown("## :material/currency_exchange: Fuenf FX-Papers -- Bausteine, Kontext & Quellenfund")
st.info(
    "**Sammelseite, kein Backtest.** Fuenf vom User geteilte Papers rund um FX-Marktstruktur, "
    "VWAP-Theorie, Intraday-Momentum und die WMR-Fix-Manipulation -- ein Tab pro Paper, mit "
    "ausfuehrlicherer Analyse als beim Gold-Batch (Kernaussage, Methodik, kritische Einordnung, "
    "extrahierte Bausteine, Machbarkeit) plus expliziten Verbindungen zu bereits vorhandenen "
    "Repo-Modulen. **Besonderer Fund:** Paper 5 ist mit sehr hoher Wahrscheinlichkeit die "
    "bisher nicht attributierte theoretische Quelle von `strategy/adx_vwap.py` -- siehe Tab 5.",
    icon=":material/inventory_2:",
)

st.space("medium")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "1. FX-Marktstruktur (Kontext)",
        "2. Fibonacci = gewichtete Mittelwerte",
        "3. Intraday-Momentum (Kandidat)",
        "4. WMR-Fix & Kollusion",
        "5. ADX-VWAP-Quelle (Fund)",
        "6. Unabhängige Erkenntnisse",
    ]
)

# =============================================================================
# Tab 1: Chaboud, Rime, Sushko -- The Foreign Exchange Market
# =============================================================================
with tab1:
    st.markdown("### Chaboud, Rime, Sushko (2023) -- The Foreign Exchange Market")
    st.caption(
        "BIS / Federal Reserve Board, fuer *The Research Handbook of Financial Markets* -- "
        "Uebersichtskapitel (peer-reviewed Sammelband), kein eigenstaendiges Strategie-Paper."
    )

    st.markdown("**Kernaussage**")
    st.markdown(
        """
Ein umfassender Survey der Struktur des globalen Spot-FX-Marktes (~2.11 Bio. USD/Tag, April
2022): Konzentration auf wenige Handelszentren (London 38%, Top-4 74%), Dominanz weniger
Waehrungspaare (EUR/USD 23%, USD/JPY 14%, GBP/USD 10%), und eine historische Entwicklung von
zwei-stufigem Dealer-Markt (1990er) ueber Multi-Dealer-Plattformen (2000er) zu einem stark
fragmentierten Markt mit Primary CLOBs (EBS/Refinitiv Matching), Secondary ECNs, Prime-Broker-
vermittelten PTFs (Principal Trading Firms/HFTs) und Futures-Maerkten (2020er). Zentrale
strukturelle Trends: (1) Interdealer-Handel ist von ~2/3 des Volumens (1990er) auf einen
Bruchteil gesunken, weil Banken zunehmend "internalisieren" (bis zu 80%+ des Kundenflusses ohne
Interdealer-Hedge); (2) algorithmischer Handel dominiert inzwischen fast vollstaendig (EBS
Market 2022: ~42% Bank-API, ~42% Non-Bank-API, nur ~15% manuell -- 2004 war es noch fast 100%
manuell); (3) "Last Look" (die Praxis, dass ein Liquiditaetsanbieter eine Order nach Empfang
nochmal pruefen und ablehnen kann) ist auf Secondary ECNs/MDPs/SDPs weit verbreitet, auf den
Primary CLOBs aber verboten -- die 2021er Ueberarbeitung des FX Global Code fuehrte zu einer
schnellen, messbaren Verhaltensaenderung (Banken beendeten "additional hold time").
"""
    )

    st.markdown("**Fuer dieses Repo besonders relevante Abschnitte**")
    with st.expander("Details: Fixing-Skandal, Flash Events, Marktfragmentierung", icon=":material/list:"):
        st.markdown(
            """
- **Abschnitt 6.2, "FX benchmark rates and the fixing scandal":** kurze Zusammenfassung des
  4pm-WMR-Fixing-Skandals (Vorwuerfe ab 2013, Milliarden-Bussen, Reform 2015: Fixing-Fenster von
  1 Minute auf 5 Minuten verlaengert). Deckt sich vollstaendig mit Tab 4 (Evans 2017) -- dieses
  Survey-Paper bestaetigt unabhaengig, dass die Reform genau auf das Problem zielte, das Evans'
  Paper empirisch (bis 2013, also VOR der Reform) dokumentiert.
- **Abschnitt 6.1, "Flash events":** GBP-Flash-Crash (7. Okt. 2016, -9% und Erholung binnen
  Minuten), JPY-Appreciation (3. Jan. 2019), beide in der "witching hour" (duennste Liquiditaet,
  spaeter NY-Nachmittag/frueher Asien-Morgen) und mit Futures-Handelsstopps/-Luecken
  koinzidierend. SNB-Franken-Freigabe (15. Jan. 2015) als extremstes Einzelereignis (+40%
  intraday). Relevanter Kontext fuer jede Session-/Uhrzeit-basierte Strategie in diesem Repo
  (Asian-Range-Breakout, CLS-Fenster-Strategien) -- bestaetigt, dass Liquiditaetsluecken
  strukturell an bestimmten Tageszeiten auftreten, nicht zufaellig verteilt sind.
- **Abschnitt 3.2/3.3, Primary CLOBs als Referenzpreis:** trotz sinkendem Volumenanteil bleiben
  EBS/Refinitiv Matching der Haupt-Ankerpunkt fuer Preisfindung, weil sie die einzigen "firm
  liquidity" (kein Last Look) Venues sind. Relevanter Hintergrund fuer die Wahl von Dukascopy
  (aggregiert Interbanken-Kassa-Preise) als Datenquelle in diesem Repo.
- **Abschnitt 7 (Forschungsfragen):** explizit offene Frage, ob "last look" zu einer
  "liquidity mirage" fuehrt (aggregierte Tiefe über Venues taeuscht mehr Liquiditaet vor als
  real verfuegbar) -- relevant als Vorsicht, wenn irgendwann echte Order-Book-Tiefe statt nur
  OHLCV-Daten verwendet werden soll.
"""
        )

    st.warning(
        "**Machbarkeit: kein extrahierbarer Trading-Baustein -- reiner Kontext/Hintergrund.** "
        "Dieses Paper beschreibt Marktstruktur, nicht ein Signal. Es liefert aber wertvolle "
        "Rahmenbedingungen fuer bereits im Repo getroffene Entscheidungen (Session-basierte "
        "Strategien, Fokus auf Preis-/Volumendaten statt Order-Book, WMR-Fix-bezogene Vorsicht) "
        "und stuetzt unabhaengig die Grundannahme hinter Tab 4. Kein Code, nur als "
        "Referenz-/Hintergrundwissen dokumentiert.",
        icon=":material/menu_book:",
    )

# =============================================================================
# Tab 2: Lu Jialong -- Fibonacci Ratios Are Weighted Averages
# =============================================================================
with tab2:
    st.markdown("### Lu Jialong (2026) -- Fibonacci Ratios Are Weighted Averages")
    st.caption(
        "Working Paper (2026), reine Mathematik -- \"foundational paper\" eines angekuendigten "
        "3-Paper-Programms (Companion B: stochastische Version unter geometrischer Brownscher "
        "Bewegung; Companion C: empirische Validierung). Beide Folgepapers nicht vorliegend."
    )

    st.markdown("**Kernaussage**")
    st.markdown(
        """
Das Paper zeigt eine strukturelle (nicht empirische) Herleitung der klassischen Fibonacci-
Retracement-Level 0.382/0.500/0.618 aus drei kanonischen Akkumulationsstrategien auf einem
geometrischen Preispfad: **Equal-Share** (arithmetisches Mittel der Preise, "CPR_E"),
**Equal-Dollar/Dollar-Cost-Averaging** (harmonisches Mittel, "CPR_D") und **Geometrisch-
gewichtet** (exponentiell wachsende Positionsgroesse mit dem Preis, "CPR_G"). Diese drei
"Cost Penetration Ratios" sind strikt geordnet (CPR_D < CPR_E < CPR_G, via AM-HM- und
Chebyshev-Ungleichung) und erfuellen eine Dualitaets-Identitaet (CPR_E x CPR_D = r^-n). Unter
Gewichtung mit dem Goldenen Schnitt (k=phi) liefert der Horizont-Grenzwert von CPR_G bei
n=1,2,unendlich exakt 0.618/0.500/0.382 -- **die drei "First-Order"-Levels sind also keine
willkuerliche Konvention, sondern folgen zwingend aus der Mathematik gewichteter Mittelwerte.**
Der vierte Level (0.236) folgt als "Dualitaets-Bild" der ersten drei bei r^n=phi^3 (Second-
Order-Objekt); der fuenfte (0.786 = phi^-1/2) liegt explizit **ausserhalb** der Konstruktion
(halbzahlige Potenz von phi ist mit ganzzahligen Akkumulations-Horizonten nicht erreichbar) --
das Paper grenzt seinen eigenen Geltungsbereich damit selbst sauber ab, statt alle fuenf Levels
gleichermassen zu "erklaeren".

**Der fuer dieses Repo wichtigste Abschnitt ist Kapitel 7:** VWAP und der gleitende Durchschnitt
(Moving Average) werden formal als Mitglieder **derselben** Cost-Penetration-Familie gezeigt --
VWAP mit den Gewichten w_i = Volumen_i, MA mit Gewicht 1 auf den letzten W Preisen und 0 sonst.
**Proposition 9/10:** CPR_VWAP = CPR_E genau dann, wenn das Volumen pro Bar konstant ist; wenn
das Volumen jedoch geometrisch MIT dem Preis waechst (V_i ~ k^i, also z.B. Volumen nimmt in
einem Trend zu), dann konvergiert CPR_VWAP gegen CPR_G -- das obere Ende der Ordnung. Anders
gesagt: **VWAP ist selbst kein fixer "Fair Value"-Anker, sondern ein bewegliches Ziel, das umso
staerker in Richtung des laufenden Trends gezogen wird, je staerker das Volumen mit dem Preis
mitwaechst** (Corollary 11, "Weight-Centroid-Prinzip"). Das Paper zitiert dazu explizit seine
eigene (nicht vorliegende) Companion-C-Studie: VWAP-implizierte Retracement-Tiefe korreliert dort
sogar **negativ** mit der tatsaechlich realisierten Retracement-Tiefe -- VWAP misst laut dem
Autor "wo Volumen den Besitzer wechselte", nicht die Kostenbasis, auf die der Kurs zurueckstrebt.
"""
    )

    st.markdown("**Kritische Einordnung**")
    st.markdown(
        """
Sauber bewiesene, elementare Mathematik (Appendix A enthaelt vollstaendige Beweise + einen
manuellen Sanity-Check n=2,r=2,k=2) -- keine Marktannahme, keine Verhaltensannahme, keine
empirische Behauptung ("This paper proves mathematical identities. It does not claim markets
empirically reverse at these levels" -- explizit im Abstract). Das ist gleichzeitig Staerke
(nichts zu widerlegen) und Grenze (nichts direkt testbar/handelbar). Der Autor selbst warnt vor
Ueberinterpretation: die Partition-Struktur zeigt nicht, dass {0.236, 0.382, 0.5, 0.618, 0.786}
gegenueber jeder beliebigen anderen Fuenf-Punkte-Menge ausgezeichnet sind ("structural
existence, not exhaustive uniqueness"). Das explizit zitierte Companion-Paper-Ergebnis (VWAP
negativ korreliert mit realisiertem Retracement) selbst ist **nicht ueberprueft** -- das Paper
liegt uns nicht vor, es ist nur eine Behauptung ueber eine externe Quelle.
"""
    )

    st.success(
        "**Der eine echte, uebertragbare Baustein: eine mathematische Erklaerung fuer einen "
        "bereits empirisch gefundenen Fix.** `strategy/adx_vwap.py`'s Refined-Konfiguration "
        "hat einen `adx_ceiling=25` eingefuehrt, *weil* die Verluste des reinen Paper-Signals "
        "sich in echten starken Trends konzentrierten (siehe Projekt-Memory). Dieses Paper "
        "liefert dafuer jetzt eine strukturelle Begruendung: in einem echten Trend waechst das "
        "Volumen typischerweise mit dem Preis (Momentum-Chasing/FOMO-Zufluesse), wodurch VWAP "
        "selbst Richtung Hoch/Tief gezogen wird (CPR_G-Regime) -- die gemessene Abweichung D_t "
        "*unterschaetzt* dadurch systematisch, wie ueberdehnt der Kurs *tatsaechlich* relativ "
        "zur \"echten\" Kostenbasis (Equal-Share-Mittel) ist, genau wenn ADX (Trendstaerke) hoch "
        "ist. Das ist keine neue Handelsregel, sondern eine plausible Erklaerung, warum der "
        "bereits empirisch gefundene ADX-Deckel funktioniert -- Theorie bestaetigt Praxis, "
        "nicht umgekehrt.",
        icon=":material/check_circle:",
    )
    st.caption(
        "Machbarkeit als eigener Baustein: die Mathematik selbst braucht keine neuen Daten "
        "(reine Formel), aber sie erzeugt keine direkt testbare neue Regel -- nur eine "
        "Interpretationshilfe fuer ein bereits vorhandenes Ergebnis. Kein neuer Code."
    )

# =============================================================================
# Tab 3: Seeck -- Intraday Momentum in Spot FX and Currency Futures
# =============================================================================
with tab3:
    st.markdown("### Leander Seeck (2026) -- Intraday Momentum in Spot FX and Currency Futures")
    st.caption(
        "Limes Technologies, Independent Research, SSRN Working Paper (Juni 2026) -- "
        "eigenpubliziert, nicht peer-reviewed, aber methodisch ungewoehnlich sauber "
        "(prae-registrierter IS/OOS-Split, Permutationstests, Chow-Test)."
    )

    st.markdown("**Kernaussage**")
    st.markdown(
        """
Testet den aus Gao et al. (2018, S&P-500-ETFs) und Baltussen et al. (2021, 60+ Futures-Maerkte)
bekannten Intraday-Momentum-Effekt -- die Rendite der ersten 30 Minuten nach Handelsbeginn sagt
die Rendite des restlichen Tages positiv voraus -- erstmals systematisch fuer **Retail-FX-CFDs**
(statt institutionelle Futures). Signal: Vorzeichen der Log-Rendite in den ersten 30 Minuten nach
London Open (Vorzeichen-Regel, kein Level). Daten: Dukascopy M5, 2012-2024, IS 2012-2018/OOS
2019-2024, fuenf Spot-Paare (EUR/USD, GBP/USD, AUD/JPY, GBP/JPY, USD/JPY) plus CME 6J-Futures
(Databento M1, 2019-2024).

**Drei Hauptbefunde:**
1. **Signal ist auf 5 von 6 Instrumenten statistisch signifikant** (Permutations-Test,
   10.000 Iterationen, p<0.001) in BEIDEN Perioden -- GBP/USD ist die Ausnahme mit umgekehrtem,
   insignifikantem Vorzeichen (kein JPY-Carry-Verstaerker vorhanden).
2. **JPY-Amplifikations-Mechanismus:** JPY-Paare zeigen ~3.8x groessere Regressionskoeffizienten
   als Nicht-JPY-Paare (OOS-Beta 0.000859 vs. 0.000226) -- zugeschrieben der Doppelrolle des Yen
   als globaler Carry-Trade-Finanzierungswaehrung UND Safe-Haven (Brunnermeier/Nagel/Pedersen
   2008, Lustig/Verdelhan 2007), was zu synchronisiertem institutionellem Orderflow am London
   Open fuehrt.
3. **Kosten-Barriere:** nach realistischen Round-Trip-Kosten (EUR/USD 0.70 Pip, GBP/USD 1.00 Pip,
   AUD/JPY 2.30 Pip, GBP/JPY 3.10 Pip, USD/JPY 1.47 Pip, 6J-Futures ~0.25 Pip-Aequivalent) bleibt
   **nur USD/JPY Spot** mit positivem Netto-Edge (OOS Sortino +0.748) -- AUD/JPY und GBP/JPY
   haben das groesste Rohsignal, werden aber von ihren breiteren Spreads komplett aufgefressen.
   6J-Futures sind ebenfalls positiv (Sortino +0.430), aber wegen fehlender Micro-/Mini-Kontrakte
   (Mindestgroesse ~80.000 USD Nominalwert) fuer Prop-Firm-Konten mit typischem 3.000-USD-
   Drawdown-Limit strukturell ungeeignet (3 Verlust-Trades in Folge, ~12% Wahrscheinlichkeit,
   reichen zum Ausschoepfen des Limits) -- Spot-FX mit fraktionierbarer Lot-Groesse ist hier
   klar besser geeignet.

**Zusatzbefund (Abschnitt 7, oekonomisch besonders interessant):** waehrend der BOJ-Yield-Curve-
Control-Verteidigung 2022 kollabierte das USD/JPY-Spot-Signal (Jahres-Sharpe -0.557), waehrend
6J-Futures im selben Jahr positiv blieben (+0.383) -- die Autoren interpretieren das als
Hinweis, dass direkte Zentralbank-Spot-Intervention institutionelle Rebalancing-Fluesse (die
laut Baltussen et al. den Momentum-Mechanismus antreiben) im Futures-Markt weniger stark stoert
als im Spot-Markt.
"""
    )

    st.markdown("**Kritische Einordnung**")
    st.markdown(
        """
Methodisch deutlich rigoroser als der Grossteil der bisher in diesem Repo verarbeiteten Papers:
echter prae-spezifizierter IS/OOS-Split (Parameter nur auf IS gewaehlt), Permutationstest statt
nur t-Statistik, ein sauberer Chow-Test fuer den USD/JPY-Regimewechsel (verwirft die
Gesamt-Parameter-Stabilitaet NICHT auf 5%-Niveau, aber Beta allein verschiebt sich signifikant --
die Autoren interpretieren das ehrlich als graduelle Institutionalisierung, nicht als scharfen
Bruch). Der Regime-Filter-Test (Abschnitt 6.1) ist bemerkenswert: **alle vier getesteten Filter
(ATR-Perzentil, Signal-Magnitude, BOJ-YCC-Naehe, kombiniert) verschlechtern das Ergebnis
gegenueber der ungefilterten Baseline** -- die Autoren werten das als Robustheits-Beweis ("Edge
ist breit verteilt, nicht auf ein Sub-Regime konzentriert"). Das ist eine plausible, aber nicht
zwingende Interpretation -- dieselbe Beobachtung waere auch mit "die Baseline selbst ist leicht
ueberoptimiert und jeder zusaetzliche Filter reduziert nur die Stichprobe" vereinbar. Sollte bei
einer eigenen Nachimplementierung explizit mitgeprueft werden, nicht einfach uebernommen werden.
Einschraenkung: eigenpubliziert (kein Peer-Review), ein einzelner Broker-Kostendatensatz, und
die 2022-BOJ-Episode ist ein Einzeljahr-Ereignis (n=1 fuer die Spot-vs-Futures-Divergenz-These).
"""
    )

    st.error(
        "**Update 2026-08-09, getestet: repliziert NICHT auf diesem Repo's eigener "
        "Dukascopy-M5-Historie -- weder Signifikanz noch JPY-Amplifikation noch der "
        "behauptete USD/JPY-Netto-Edge.** Neues Package `intraday_momentum/` (eigener "
        "M5-Fetcher inkl. AUD/JPY, GBP/JPY, Signal-/Kosten-/Metrik-Module), Backtest via "
        "`scripts/research_intraday_momentum.py` -- 14,5 Jahre, alle 5 Papiere, exakt "
        "denselben IS-(2012-2018)/OOS-(2019-2024)-Split wie das Paper, plus ein echter "
        "Holdout 2025-2026 (nach dem Paper entstanden). Signifikanz (beta, Permutations-"
        "p-Wert) auf Rohrenditen, Performance auf kostenbereinigten Renditen -- exakt die "
        "Paper-eigenen Round-Trip-Kosten (Sec. 3.1) uebernommen.",
        icon=":material/block:",
    )
    with st.expander("Vollstaendige Ergebnistabelle + Vergleich zu den Paper-Zahlen", icon=":material/table_chart:"):
        st.markdown("**Beta / Permutations-p-Wert / kostenbereinigter Sortino, je Paar x Periode (OOS-Zeile hervorgehoben):**")
        st.markdown(
            """
| Paar | Periode | n | beta | p-Wert | Sortino (netto) | Win-Rate |
|---|---|---|---|---|---|---|
| EUR/USD | IS 12-18 | 1805 | -0.0001 | 0.297 | -0.639 | 49.1% |
| EUR/USD | **OOS 19-24** | 1552 | -0.0002 | **0.022** | +0.051 | 49.6% |
| EUR/USD | Holdout 25-26 | 405 | -0.0000 | 0.826 | +0.355 | 52.8% |
| GBP/USD | IS 12-18 | 1793 | -0.0001 | 0.313 | +0.452 | 50.8% |
| GBP/USD | OOS 19-24 | 1553 | -0.0001 | 0.323 | -0.265 | 48.5% |
| AUD/JPY | IS 12-18 | 1800 | -0.0001 | 0.615 | -0.350 | 48.2% |
| AUD/JPY | OOS 19-24 | 1553 | -0.0002 | 0.184 | -0.193 | 47.3% |
| GBP/JPY | IS 12-18 | 1801 | +0.0001 | 0.442 | +0.080 | 50.0% |
| GBP/JPY | OOS 19-24 | 1555 | +0.0001 | 0.529 | -0.314 | 46.8% |
| USD/JPY | IS 12-18 | 1797 | +0.0002 | 0.091 | -0.090 | 49.5% |
| USD/JPY | **OOS 19-24** | 1553 | +0.0001 | 0.245 | **-0.434** | 47.9% |
"""
        )
        st.markdown(
            """
**Kein Paar/Periode erreicht die vom Paper behauptete Signifikanz auf der Vorzeichenseite,
die im Backtest auch zaehlt** (EUR/USD OOS wird zwar p<0.05, aber mit dem FALSCHEN
Vorzeichen gegenueber dem Paper -- und die anderen beiden Perioden bestaetigen das nicht,
klassisches Muster eines einzelnen zufaelligen Treffers). **Der zentrale Befund des Papers
(USD/JPY Spot ist das einzige Paar mit positivem Netto-Edge, Sortino +0.748 OOS) dreht sich
in unserem Test komplett um: Sortino -0.434.** JPY-Amplifikation ist ebenfalls umgekehrt:
mittlerer |beta| der JPY-Paare (OOS) = 0.000126 vs. EUR/USD = 0.000224 -- ein Verhaeltnis
von **0.56x statt der behaupteten ~3.8x**.
"""
        )

    st.warning(
        "**Methodische Einschraenkung, transparent offengelegt:** das Paper nennt den "
        "exakten Exit-Zeitpunkt nicht (\"the selected intraday exit within the "
        "London-New York session\"). Standard hier: Halten bis zum Ende der UTC-22:00-"
        "Session (Repo-eigene, bereits an anderer Stelle verwendete Konvention). Als "
        "Robustheits-Check zusaetzlich mit einem festen 4-Stunden- und 2-Stunden-Exit "
        "nachgerechnet (naeher an klassischen \"Intraday-Momentum\"-Studien, die typischerweise "
        "kuerzere Fenster testen) -- **das Ergebnis wird dadurch nicht besser, tendenziell "
        "eher schwaecher** (z.B. USD/JPY OOS Win-Rate faellt von 47.9% auf 43.8% bei 2h-Exit). "
        "Der Nicht-Befund ist also robust gegenueber dieser Modellierungsentscheidung, nicht "
        "nur ein Artefakt der Exit-Wahl.",
        icon=":material/priority_high:",
    )
    st.caption(
        "Fazit: entweder repliziert der eigene Befund des Papers nicht auf einem unabhaengig "
        "gezogenen Datensatz (selbst vom selben Anbieter Dukascopy), oder es steckt eine nicht "
        "offengelegte methodische Feinheit dahinter, die sich aus dem Papertext allein nicht "
        "rekonstruieren liess. In beiden Faellen: **kein Grund, dieses Signal in diesem Repo "
        "weiterzuverfolgen ohne einen neuen, konkreten Ansatzpunkt.** Code bleibt reproduzierbar "
        "(`intraday_momentum/`, `scripts/research_intraday_momentum.py`), nicht committet."
    )

# =============================================================================
# Tab 4: Evans -- Forex Trading and the WMR Fix
# =============================================================================
with tab4:
    st.markdown("### Martin D.D. Evans (2017) -- Forex Trading and the WMR Fix")
    st.caption(
        "Georgetown University, *Journal of Banking and Finance* (peer-reviewed, published) -- "
        "SSRN 2487991. Daten: Gain Capital Tick-Daten + EBS-Interdealer-Daten, 21 Waehrungspaare, "
        "2004-2013."
    )

    st.markdown("**Kernaussage**")
    st.markdown(
        """
Baut ein mikrostrukturelles Wettbewerbsmodell (Erweiterung des Portfolio-Shifts-Modells von
Lyons/Evans) fuer den 4pm-WMR-Fix und leitet daraus zwei scharfe Vorhersagen ab: (1) Fix-Orders
sollten nur die **Volatilitaet NACH** dem Fix erhoehen (weil Dealer die aggregierte Fix-
Order-Imbalance erst beim gegenseitigen Ausgleich NACH dem Fix erfahren), nicht davor; (2)
Preisveraenderungen vor und nach dem Fix sollten **leicht positiv** korreliert sein (aus einer
kleinen Intraday-Risikopraemie), nicht negativ.

**Die Empirie widerspricht dem Modell auf beiden Achsen, drastisch:**
- **Pre-Fix-Volatilitaet ist extrem atypisch** -- ueber alle 21 Paare und die volle Dekade
  treten Kursspruenge in der Minute vor 16:00 mit dem 3-12-fachen der normalen Rate auf
  (verglichen mit einer Bootstrap-Verteilung aus zufaelligen Zeitfenstern), am Monatsende noch
  ausgepraegter (z.B. JPY/USD und USD/GBP: >10x normal).
- **Signifikant NEGATIVE Autokorrelation zwischen Pre- und Post-Fix-Preisaenderungen bei 18 von
  21 Waehrungen** -- oekonomisch gross genug, um eine mechanische End-of-Month-Handelsstrategie
  (long/short je nach Vorzeichen der Pre-Fix-Bewegung) mit Sharpe-Ratios teils deutlich ueber 1
  (einige Paare 2-5) profitabel zu machen, selbst nach realistischen Transaktionskosten (halber
  EBS-Inside-Spread).

**Die Autoren-eigene Erklaerung ist die zentrale Einordnung fuer dieses Repo:** die Ergebnisse
passen exakt zum Muster, das die FCA/DOJ-Ermittlungen (2013-2015) dokumentierten -- Dealer
teilten sich gegenseitig ihre Fix-Order-Informationen kurz vor 16:00 mit und "front-runnten"
kollusiv die aggregierte Imbalance (Positionsaufbau vor dem Fix, aggressive Order-Platzierung
in den ersten Sekunden des Fix-Fensters, Positionsabbau danach). Banken haben das **explizit
eingeraeumt** (Bussen >5.6 Mrd. USD). Die WMR-Reform (Methodik-Aenderung Okt. 2014, Fix-Fenster
von 1 auf 5 Minuten verlaengert 2015) zielte direkt darauf.
"""
    )

    st.markdown("**Kritische Einordnung -- warum das mehr ist als nur ein weiteres Paper**")
    st.warning(
        "**Der Stichprobenzeitraum (2004-2013) endet genau VOR der 2015er Reform, die das "
        "dokumentierte Kollusions-Verhalten spezifisch abstellen sollte.** Ein profitabler "
        "Pre/Post-Fix-Reversal-Effekt in dieser Periode ist damit sehr plausibel ein "
        "kollusionsgetriebenes Artefakt, kein struktureller Marktmechanismus -- und genau "
        "dieses Artefakt sollte nach 2015 NICHT mehr replizierbar sein.",
        icon=":material/gavel:",
    )
    st.markdown(
        """
Das liefert eine direkte, bisher fehlende **theoretische Erklaerung fuer bereits im Repo
vorhandene Negativ-Befunde**: `strategy/cls_squeeze.py` (CLS-Settlement-Fenster-Fade auf
EUR/USD, 06:00-09:00 UTC) und `strategy/cls_advanced.py` (mehrstufiges CLS-Framework) wurden
beide bereits ueber mehrjaehrige Zeitraeume getestet, die ueberwiegend NACH 2015 liegen, und
zeigten **keine robuste Kante** (siehe Projekt-Memory: Reversion Sharpe -0.84, Momentum nicht
robust; gepoolte CLS-Advanced-Regeln Profit Factor <1 ueber 10 Jahre). Evans' Befund macht
plausibel, **warum**: falls der WMR-Fix vor 2015 tatsaechlich eine kollusiv erzeugte, temporaere
Preisverzerrung war, dann ist genau dieser Mechanismus seit der Reform strukturell nicht mehr
vorhanden -- die spaeteren CLS-Strategien testen unbeabsichtigt eine Periode, in der die
zugrundeliegende Anomalie bereits regulatorisch geschlossen war.
"""
    )

    st.warning(
        "**Update 2026-08-09, getestet: gemischtes Ergebnis -- die Kollusions-Hypothese wird "
        "weder sauber bestaetigt noch sauber widerlegt.** Neues Modul "
        "`intraday_momentum/wmr_fix.py` + `scripts/research_wmr_fix_check.py`, wiederverwendet "
        "denselben M5-Cache wie Tab 3 (keine neue Datenquelle). Reformdatum: 15.02.2015 "
        "(Fix-Fenster-Verbreiterung 1min->5min). Aufloesungsgrenze offengelegt: minimal "
        "messbarer Horizont ist 5 Minuten (M5-Bars) -- Evans' dramatischste Zahlen basieren "
        "auf 1-Minuten-Tick-Daten, die uns nicht vorliegen.",
        icon=":material/balance:",
    )
    with st.expander("Korrelationstabelle: Pre-/Post-Fix-Rendite, 30-Min-Horizont", icon=":material/table_chart:"):
        st.markdown(
            """
| Paar | Vor Reform (n) | Nach Reform (n) | Vor Reform, Monatsende (n=37) | Nach Reform, Monatsende (n=138) |
|---|---|---|---|---|
| EUR/USD | +0.033 | -0.007 | -0.055 | **-0.137** |
| GBP/USD | -0.044 | -0.036 | **-0.569** | -0.251 |
| AUD/JPY | -0.005 | -0.012 | **-0.371** | -0.252 |
| GBP/JPY | -0.097 | -0.004 | **-0.537** | -0.070 |
| USD/JPY | -0.003 | +0.060 | -0.092 | -0.072 |
"""
        )
        st.markdown(
            """
**Was robust repliziert (Evans' Kernaussage, unabhaengig von der Kollusionsfrage):** die
Monatsende-Korrelation ist in beiden Epochen deutlich negativer als der volle Zeitraum --
der institutionelle End-of-Month-Hedging-Mechanismus (Melvin/Prins 2015, von Evans zitiert)
ist real und in diesem Datensatz sichtbar, das ist keine Kollusions-spezifische Beobachtung.

**Was die Reform-schliesst-es-Hypothese betrifft:** 3 von 5 Paaren (AUD/JPY, GBP/JPY,
GBP/USD) zeigen das erwartete Muster -- Monatsende-Korrelation wird nach der Reform
schwaecher (bei GBP/JPY dramatisch: -0.537 -> -0.070). **Aber EUR/USD zeigt das GENAUE
GEGENTEIL** (-0.055 -> -0.137, staerker statt schwaecher), und USD/JPY ist praktisch
unveraendert. Die Vor-Reform-Monatsende-Stichprobe ist mit n=37 zudem duenn (nur ~3 Jahre
Monatsenden) -- zu wenig, um einer einzelnen Zahl viel Gewicht zu geben.
"""
        )
    st.markdown(
        "**Einordnung:** die Kollusions-Erklaerung fuer die bereits bekannten "
        "`cls_squeeze.py`/`cls_advanced.py`-Negativbefunde bleibt **plausibel, aber nicht "
        "durch diesen Sanity-Check bewiesen** -- 3/5 Paare stuetzen sie, 1/5 widerspricht "
        "klar, 1/5 ist neutral, und die duenne Vor-Reform-Stichprobe macht jede einzelne "
        "Zahl unsicher. Was zusaetzlich zur ursprünglichen Kollusions-Frage sauber "
        "bestaetigt wird: der Monatsende-Effekt selbst ist real und robust -- relevant, "
        "falls je wieder eine End-of-Month-Hedging-Idee aufkommt, unabhaengig davon, ob "
        "sie mit dem WMR-Fix speziell zusammenhaengt."
    )
    st.caption(
        "Code bleibt reproduzierbar (`intraday_momentum/wmr_fix.py`, "
        "`scripts/research_wmr_fix_check.py`), nicht committet."
    )

# =============================================================================
# Tab 5: Bhatti / Osmanoglu -- ADX-Conditioned VWAP (probable source)
# =============================================================================
with tab5:
    st.markdown(
        "### Amaanullah Bhatti (Hafzan Osmanoglu) (2026) -- Momentum Exhaustion and "
        "Fair Value Reversion: An ADX-Conditioned VWAP Strategy in FX Markets"
    )
    st.caption("Symbiosis International University, SSRN Working Paper (6454659), 22. Maerz 2026.")

    st.success(
        "**Wahrscheinlich die bisher im Repo nicht attributierte Quelle von "
        "`strategy/adx_vwap.py`.** `app_pages/adx_vwap_writeup.py` vermerkt explizit: "
        "\"Referenz/Autoren sind nicht im Repo hinterlegt (die PDF-Quelle liegt [nicht im "
        "Repo])\" -- dieses Paper schliesst genau diese Luecke. Die Uebereinstimmung ist zu "
        "praezise fuer Zufall, siehe Beleg unten.",
        icon=":material/manage_search:",
    )

    st.markdown("**Kernaussage des Papers**")
    st.markdown(
        """
Ein reines **Theorie-/Spezifikations-Paper** (Abstract: "No empirical results are reported in
this draft; the paper is limited to theoretical development and model specification") --
entwickelt ein regime-konditioniertes Mean-Reversion-Framework fuer FX, das drei Dimensionen
kombiniert: (1) Preislage relativ zu den Extremen der Vortages-Session (Liquiditaets-Knoten aus
Stop-/Limit-Order-Clustering, Osler 2001/2003), (2) Abweichung vom Volume-Weighted-Average-Price
als institutioneller Fair-Value-Anker (Madhavan 2002, Butz/Oomen 2019), (3) Wilder's Average
Directional Index als Regime-Filter -- Short/Long nur wenn Preis am Vortages-Hoch/-Tief steht
UND die VWAP-Abweichung ueberdehnt ist UND ADX erhoeht, aber nicht mehr steigend ist
("Momentum-Erschoepfung", nicht "Momentum-Beginn").
"""
    )

    st.error(
        "**Staerkster Einzelbeleg:** der Modul-Docstring am Kopf von `strategy/indicators.py` "
        "lautet woertlich: *\"Core indicator layer: session VWAP (Eq. 1-3), previous-session "
        "extremes (Sec. 4.3), Wilder's ADX (Eq. 4-10), and the regime filter (Eq. 11-13).\"* -- "
        "das sind exakt die Gleichungs-/Abschnittsnummern dieses Papers (VWAP-Definition Eq. 1-3, "
        "Vortages-Extreme Abschnitt 4.3, Wilder-ADX Eq. 4-10, Regimefilter Eq. 11-13). Kein Zufall "
        "denkbar -- der urspruengliche Autor des Repo-Codes hat direkt gegen dieses (oder ein "
        "praktisch identisches) Paper implementiert, nur ohne die Quelle im Repo zu vermerken.",
        icon=":material/priority_high:",
    )

    st.markdown("**Konkreter formaler Abgleich mit dem bestehenden Code**")
    with st.expander("Formel-fuer-Formel-Beleg (Paper-Gleichungen vs. Repo-Code)", icon=":material/checklist_rtl:"):
        st.markdown(
            r"""
| Paper (Abschnitt/Gleichung) | Repo-Code | Uebereinstimmung |
|---|---|---|
| VWAP mit Typical Price $\hat P_t=(H_t+L_t+C_t)/3$ (Eq. 2) | `strategy/indicators.py::compute_vwap_and_deviation`: `typical_price = (high+low+close)/3.0` | exakt identisch |
| Deviation $D_t=(P_t-\text{VWAP}_t)/\text{VWAP}_t$ (Eq. 3) | `deviation = (close - vwap) / vwap` | exakt identisch |
| $\theta$-Kalibrierung: "one intraday standard deviation of $D_t$" (Sec. 6.2) | `strategy/indicators.py::compute_adaptive_theta` -- rollierende Std. von `deviation` | exakt dieselbe Idee, als adaptiver statt fixer Wert umgesetzt |
| Regime: $\text{ADX}_t>\overline{\text{ADX}}_t$ UND $\Delta\text{ADX}_t\le 0$ (Eq. 12/13, "weak" Ungleichung) | `strategy/signals.py` -- Repo-Memory dokumentiert einen expliziten Test genau von "strict $\Delta ADX_t<0$ vs. paper's weak $\Delta ADX_t\le 0$" (**Remark 1 im Paper heisst wortwoertlich so**) | Test-Frage UND Namensgebung stimmen exakt mit Paper-Remark 1 ueberein |
| Exit: VWAP-Kreuzung ODER Session-Ende, je nachdem was zuerst eintritt (Sec. 5.3) | `strategy/backtest.py` Kommentar: "VWAP-cross target (Sec 5.3)" -- referenziert dieselbe Abschnittsnummer | Abschnittsnummer im Code-Kommentar identisch zum Paper |
| Stop: bestaetigter Schlusskurs jenseits des Trigger-Extrems, Vielfaches des ATR (Sec. 5.3) | `strategy/backtest.py` Kommentar: "confirmed-close stop beyond the trigger extreme by a multiple of ATR (Sec 5.3)" | wortnahe Uebernahme derselben Formulierung |
| Composite-Signal $S_t\in\{-1,0,+1\}$ (Eq. 14) | `strategy/signals.py::generate_signal` (4 UND-Bedingungen: Preislage, VWAP-Deviation, ADX-Level, ADX-Richtung) | strukturell identisch |
"""
        )
        st.caption(
            "Die Abschnittsnummern (\"Sec 5.3\", \"Sec 6.1\", \"Sec 6.2\") stehen bereits als "
            "Kommentare im bestehenden Code (`strategy/backtest.py`) -- sie referenzierten "
            "bislang eine unbekannte Quelle. Sie passen exakt auf die Abschnittsstruktur dieses "
            "Papers (5.3 \"Target and Risk Management\", 6.1 \"Data and Session Definition\", "
            "6.2 \"Parameter Calibration\")."
        )

    st.markdown("**Was das Paper NICHT liefert (und warum das fuer dieses Repo unproblematisch ist)**")
    st.markdown(
        """
Da das Paper explizit **keine eigenen Backtest-Zahlen** enthaelt ("Formal backtesting and
performance attribution are left to future work"), gibt es nichts, wogegen die im Repo bereits
durchgefuehrten Backtests (negativer Sharpe auf dem woertlichen Eq.-14-Signal ueber 10 Jahre
echte Dukascopy-Daten; die verfeinerte Konfiguration mit `adx_ceiling=25`, H1-Timeframe, `theta`
x1.5 als bestbekannter, aber duenn belegter Kandidat) abgeglichen werden muessten. **Das
gesamte empirische Fundament dieser Strategie im Repo ist eigene, originaere Arbeit** -- keine
Reproduktion behaupteter Paper-Ergebnisse, weil keine existieren.
"""
    )

    st.info(
        "**Python-Referenzimplementierung im Anhang.** Das Paper enthaelt (Appendix A) eine "
        "vollstaendige, lauffaehige Pandas/NumPy-Referenzimplementierung (VWAP, "
        "Vortages-Extreme, Wilder-ADX inkl. korrekter Wilder-Smoothing-Seed-Konvention, "
        "Regime-Filter, Composite-Signal) -- nuetzlich als unabhaengiger Cross-Check-Kandidat, "
        "falls die Repo-eigene ADX-Implementierung nochmal verifiziert werden soll (aehnlich "
        "dem bereits dokumentierten Wilder-Seed-Bugfix beim GoldASB-MT5-Bridge-Portieren, siehe "
        "Projekt-Memory).",
        icon=":material/code:",
    )

    st.markdown("**Empfohlene naechste Schritte (Dokumentation, kein neuer Code-Pfad noetig)**")
    st.markdown(
        """
1. `app_pages/adx_vwap_writeup.py` und `strategy/backtest.py`/`strategy/indicators.py` mit
   diesem Fund attribuieren (Autoren, SSRN-ID, Titel) -- schliesst die bisher offene
   Quellenluecke.
2. Optionaler Cross-Check: Paper-Appendix-Python gegen `strategy/indicators.py::wilder_smooth`
   auf identischen Testdaten laufen lassen (analog zum bereits erfolgreich durchgefuehrten
   Cross-Check beim GoldASB-Bot-Portieren) -- rein zur Verifikation, kein erwarteter Fund.
3. Session-Definition ist bereits aufgeloest, nicht mehr offen: das Paper nennt in Sec. 6.1 drei
   moegliche Konventionen (London 07:00-17:00 GMT / NY 13:00-22:00 GMT / 24h-rollierend, Reset um
   Mitternacht NY-Zeit) -- der Repo-Code implementiert mit `reset_hour=22` (UTC) exakt Option
   (iii), plus zusaetzlich (nicht im Paper vorgegeben) `filter_session_window` fuer die ersten
   beiden benannten Fenster. Nur noch im Writeup explizit als "Paper-Option (iii)" benennen,
   kein offener Rechercheschritt mehr.
"""
    )

# =============================================================================
# Tab 6: Unabhaengige Erkenntnisse -- our own verdict per paper, separate
# from each paper's own claims (Tabs 1-5 above)
# =============================================================================
with tab6:
    st.markdown("### Unabhängige Erkenntnisse -- eigener Verdikt je Paper")
    st.caption(
        "Nicht die Behauptungen der Papers (die stehen in Tabs 1-5), sondern das, was "
        "dieses Repo selbst unabhängig geprüft/verifiziert/gebaut hat -- pro Paper einzeln, "
        "mit klarer Trennung zwischen \"getestet\" und \"nicht testbar/kein Test nötig\"."
    )
    st.space("small")

    with st.container(border=True):
        st.markdown("**1. Chaboud, Rime, Sushko -- FX-Marktstruktur**")
        st.caption("Kein eigener Test möglich oder nötig -- Survey-Paper, keine Behauptung zu prüfen.")
        st.info(
            "Unabhängig bestätigt: der WMR-Reform-Zeitstrahl (Methodik-Änderung Okt. 2014, "
            "Fenster-Verbreiterung Feb. 2015) deckt sich mit dem in Tab 4 verwendeten "
            "Reform-Cutoff -- zwei unabhängige Quellen, ein Datum.",
            icon=":material/menu_book:",
        )

    with st.container(border=True):
        st.markdown("**2. Lu Jialong -- Fibonacci = gewichtete Mittelwerte**")
        st.caption("Kein eigener Test möglich -- reine Mathematik, keine empirische Behauptung im Paper.")
        st.info(
            "Unabhängige Einordnung: liefert eine plausible *nachträgliche* theoretische "
            "Begründung für den bereits vor diesem Paper empirisch gefundenen "
            "`adx_ceiling=25`-Fix in `strategy/adx_vwap.py` -- Theorie bestätigt Praxis, "
            "keine neue, selbst prüfbare Vorhersage.",
            icon=":material/functions:",
        )

    with st.container(border=True):
        st.markdown("**3. Seeck -- Intraday Momentum in Spot FX**")
        st.caption(
            "Eigener Backtest: `intraday_momentum/`, `scripts/research_intraday_momentum.py` -- "
            "14,5 Jahre M5, 5 Paare, exakter Paper-IS/OOS-Split + Holdout, plus 2h-/4h-Exit-"
            "Robustheitscheck."
        )
        st.error(
            "**Unabhängiges Ergebnis: repliziert NICHT.** Kein Paar erreicht robuste "
            "Signifikanz, JPY-Amplifikation ist umgekehrt (0.56x statt ~3.8x), und das "
            "Vorzeigepaar USD/JPY dreht von behauptet +0.748 auf gemessen -0.434 Sortino (OOS). "
            "Robust gegenüber der Exit-Horizont-Wahl -- kein Artefakt der eigenen Methodik.",
            icon=":material/block:",
        )

    with st.container(border=True):
        st.markdown("**4. Evans -- Forex Trading and the WMR Fix**")
        st.caption(
            "Eigener Sanity-Check: `intraday_momentum/wmr_fix.py`, "
            "`scripts/research_wmr_fix_check.py` -- 5 Paare, Pre-/Post-2015-Reform-Split, "
            "Monatsende- vs. Rest-des-Monats-Split."
        )
        st.warning(
            "**Unabhängiges Ergebnis: gemischt.** Der Monatsende-Effekt selbst ist robust "
            "real (beide Epochen, alle 5 Paare). Die Kollusions-/Reform-Erklärung wird nur "
            "bei 3 von 5 Paaren bestätigt (AUD/JPY, GBP/JPY, GBP/USD); EUR/USD widerspricht "
            "klar, USD/JPY ist neutral. Vor-Reform-Stichprobe dünn (n=37 Monatsenden).",
            icon=":material/balance:",
        )

    with st.container(border=True):
        st.markdown("**5. Bhatti / Osmanoglu -- ADX-Conditioned VWAP**")
        st.caption("Kein Backtest nötig -- das Paper selbst liefert keine eigenen Zahlen zum Prüfen.")
        st.success(
            "**Unabhängige Erkenntnis: Quelle identifiziert, nicht nur behauptet.** "
            "Formel-für-Formel-, Abschnittsnummer- und Docstring-Abgleich mit "
            "`strategy/indicators.py`/`strategy/backtest.py` -- inzwischen in "
            "`app_pages/adx_vwap_writeup.py` attribuiert (Docstring + sichtbare Info-Box).",
            icon=":material/manage_search:",
        )

    st.space("small")
    st.caption(
        "Zusammengefasst: von fünf Papers wurden zwei mit eigenen Backtests geprüft (3, 4) -- "
        "beide überwiegend negativ/gemischt, keine neue Handelskante. Eines liefert einen "
        "verifizierten Quellenfund (5) statt eines Tests. Zwei sind nicht empirisch prüfbar "
        "(1, 2) und bleiben Kontext bzw. theoretische Einordnung."
    )

st.space("medium")
st.success(
    "**Gesamtfazit ueber alle fuenf Papers (Update 2026-08-09, Paper 3+4 jetzt getestet):** "
    "Paper 1 ist reiner Marktstruktur-Kontext (kein Baustein, aber unabhaengige Bestaetigung "
    "fuer die WMR-Fix-Vorsicht aus Tab 4). Paper 2 ist reine Mathematik ohne eigenen "
    "Handelsbaustein, liefert aber eine plausible theoretische Begruendung fuer den bereits "
    "empirisch gefundenen `adx_ceiling`-Fix. **Paper 3 repliziert NICHT** auf eigener "
    "14,5-Jahre-Dukascopy-M5-Historie -- weder Signifikanz noch JPY-Amplifikation noch der "
    "behauptete USD/JPY-Netto-Edge (der sich sogar ins Gegenteil verkehrt, Sortino -0.434 "
    "statt +0.748), robust gegenueber der Exit-Horizont-Wahl. **Paper 4's Kollusions-"
    "Erklaerung fuer die CLS-Negativbefunde ist gemischt bestaetigt:** der Monatsende-Effekt "
    "selbst ist robust real, aber das erwartete Vor-/Nach-Reform-Schwaechemuster zeigt sich "
    "nur bei 3 von 5 Paaren (EUR/USD widerspricht klar). **Paper 5 bleibt der wichtigste "
    "Einzelfund: mit sehr hoher Sicherheit die bisher unattribuierte Quelle von "
    "`strategy/adx_vwap.py`** -- schliesst eine seit Projektbeginn offene Dokumentationsluecke. "
    "**Nettoertrag dieses Batches: eine Quellenzuordnung (Paper 5) plus zwei sauber "
    "durchgefuehrte, ueberwiegend negative/gemischte Tests (Paper 3, 4) -- kein neuer "
    "produktiver Handelsbaustein, aber mehr Klarheit als vorher.**",
    icon=":material/summarize:",
)
