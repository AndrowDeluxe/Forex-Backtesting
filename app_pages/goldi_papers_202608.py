"""Fuenf neue Papers (User-Upload, 2026-08-08) -- Wissens-Sammelseite, kein
Backtest-Dashboard, gleiches Muster wie paper151.py: eigenstaendig aus jedem
Paper destillierte Strategiebestandteile/Filter/Modelle, ein Tab pro Paper,
mit ehrlicher Machbarkeits-Einschaetzung fuer dieses Repo (vorhandene
Datenquellen: Dukascopy FX/Metalle/Indizes, yfinance, Binance -- keine
Optionsdaten, keine Korea-Marktdaten).

Quellen (SSRN):
1. ssrn-7244128 -- An & Ryu (2026), Short-selling feasibility and the price
   impact of foreign investor trading (Korean Aktienmarkt)
2. ssrn-7098358 -- Sen (2026), Gamma Exposure (GEX) Without the Paywall
   (Dealer-Gamma fuer Gold-/S&P500-Futures-Optionen)
3. ssrn-7200580 -- Sulistyardi (2026), Regime-Conditional Framework for
   Rolling Correlation and Lead-Lag Analysis among XAUUSD, XAGUSD, BTCUSD
4. ssrn-7114978 -- Mouynes (2026), Grading the Graders (institutionelle
   Jahres-Ausblicke, Prognosequalitaet)
5. ssrn-2382299 -- Zhang & Laws (2013), Investor Sentiment and Forecasting
   Ability: Evidence from COT Reports in Precious Metal Futures Markets
"""

import streamlit as st

st.set_page_config(page_title="Neue Papers (Aug. 2026)", page_icon=":material/library_books:", layout="wide")

st.markdown("## :material/library_books: Fuenf neue Papers -- Bausteine & Machbarkeit")
st.info(
    "**Sammelseite, kein Backtest.** Fuenf vom User hochgeladene SSRN-Papers, eigenstaendig "
    "destilliert -- ein Tab pro Paper, mit konkret extrahierten Strategiebestandteilen/Filtern/"
    "Modellen und einer ehrlichen Machbarkeits-Einschaetzung fuer dieses Repo (vorhandene "
    "Datenquellen: Dukascopy FX/Metalle/Indizes, yfinance, Binance -- **keine** Optionsdaten, "
    "**keine** Korea-Marktdaten). Was tatsaechlich mit vorhandenen Daten testbar ist, wird direkt "
    "danach umgesetzt und gegen den Gold Asian-Range Breakout getestet (siehe dortiges Dashboard).",
    icon=":material/inventory_2:",
)

st.space("medium")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "1. Foreign Flow & Leerverkauf",
        "2. Gamma Exposure (GEX)",
        "3. Gold-Silber-BTC Lead-Lag",
        "4. Grading the Graders",
        "5. COT-Sentiment (Praezisionsmetalle)",
    ]
)

# =============================================================================
# Tab 1: Short-selling feasibility & foreign investor trading (Korea)
# =============================================================================
with tab1:
    st.markdown("### An & Ryu (2026) -- Short-selling feasibility and the price impact of foreign investor trading")
    st.caption("SSRN 7244128 -- Koreanischer Aktienmarkt (KOSPI), 2017-2024, unveroeffentlicht/Preprint")

    st.markdown(
        "**Kernaussage:** Der Ruecklauf auf Netto-Auslaenderkaeufe (aenderung der Netto-Kaufquote) "
        "haengt vom *Marktdesign-Umfeld* ab, nicht nur von der Kauf-Aktivitaet selbst. Waehrend "
        "eines vollstaendigen Leerverkaufsverbots (COVID-Periode) wirkt Auslaender-Kaufdruck nur "
        "kurzfristig (verpufft nach ~5-10 Handelstagen). Waehrend der partiellen Lockerung "
        "(Leerverkauf nur fuer KOSPI200-Werte erlaubt) ist die Rendite-Antwort **persistenter und "
        "~30-40% groesser**, konsistent mit echter Informationsverarbeitung statt reinem "
        "Nachfragedruck. Placebo-Test (falsche Lockerungs-Periode) bestaetigt: der Effekt ist "
        "spezifisch fuer die tatsaechliche Leerverkaufs-Freigabe, kein allgemeiner Zeittrend."
    )

    st.markdown("**Extrahierter Baustein:** \"Arbitrage-Constraint-Regime\" als Kontextfilter")
    st.markdown(
        """
Die uebertragbare Idee (nicht die Korea-spezifischen Zahlen): **wie schnell/persistent ein
Orderflow-Signal in den Preis einpreist haengt davon ab, wie leicht Marktteilnehmer dagegen
arbitrieren koennen.** Wenn Arbitrage-Constraints binden (z.B. Leerverkaufsverbot, geringe
Liquiditaet, hohe Finanzierungskosten), sind Preisreaktionen eher temporaerer Druck; wenn
Arbitrage frei ist, sind sie eher persistente Informationsverarbeitung. Ein genereller
Baustein: **Orderflow-/Momentum-Signale nur in "arbitrage-freien" Regimen vertrauen** (hohe
Liquiditaet, keine strukturellen Handelsbeschraenkungen).
"""
    )
    st.error(
        "**Machbarkeit: nicht direkt umsetzbar.** Das Paper braucht koreanische Netto-"
        "Auslaenderkaufquoten (FnGuide-Daten) und ein Leerverkaufsverbots-Regime -- beides "
        "existiert fuer unsere Instrumente (FX-Majors, Gold, Indizes) nicht in vergleichbarer "
        "Form (kein zentraler Leerverkaufsverbots-Datenpunkt bei FX/CFDs, keine Auslaender-"
        "Orderflow-Daten verfuegbar). Die uebertragbare Idee (\"Arbitrage-Constraint als "
        "Kontextfilter\") ist konzeptionell interessant, aber ohne konkrete, bei uns verfuegbare "
        "Proxy-Variable nicht direkt in einen Filter uebersetzbar. **Kein neuer Baustein, "
        "nur als Konzept dokumentiert.**",
        icon=":material/block:",
    )

# =============================================================================
# Tab 2: Gamma Exposure (GEX)
# =============================================================================
with tab2:
    st.markdown("### Sen (2026) -- Gamma Exposure (GEX) Without the Paywall")
    st.caption(
        "Eigenpublikation (nicht peer-reviewed), Methodik-Paper -- Dealer-Gamma-Engine fuer "
        "Gold- (COMEX GC) und S&P-500- (CME ES) Futures-Optionen"
    )

    st.markdown(
        "**Kernaussage:** Optionshaendler (Dealer) muessen ihr Gamma-Exposure kontinuierlich "
        "delta-hedgen. Ist das aggregierte Dealer-Gamma positiv, daempft ihr Hedging Bewegungen "
        "(Pinning, Range-Verhalten); ist es negativ, verstaerkt es Bewegungen (Trending). Das "
        "Paper beschreibt eine vollstaendig offengelegte Methodik, um daraus handelbare Level "
        "abzuleiten -- Zero-Gamma-Flip (Regime-Grenze), Call-/Put-Walls (Widerstand/"
        "Unterstuetzung), Pins (Magnet-Level nahe am Geld), sowie Vanna-/Charm-Overlays "
        "(Sekundaereffekte aus Vola-Aenderung bzw. Zeitablauf)."
    )

    st.markdown("**Extrahierte Bausteine (Level-Taxonomie)**")
    with st.expander("Alle Bausteine im Detail", icon=":material/list:"):
        st.markdown(
            """
- **Zero-Gamma-Flip:** die Kursschwelle, an der Netto-Dealer-Gamma das Vorzeichen wechselt --
  oberhalb daempfende, unterhalb verstaerkende Hedging-Dynamik. Der wichtigste einzelne Level
  im Rahmenwerk.
- **Call-/Put-Wall:** Strike mit dem groessten Call- bzw. Put-seitigen Gamma, mit einem
  Dominanz-Qualifizierer (1.5x der Gegenseite), um gemischte At-the-money-Strikes
  auszuschliessen -- wirkt empirisch als Widerstand/Unterstuetzung, am zuverlaessigsten im
  positiven Gamma-Regime.
- **Pins:** nahe-am-Geld-Strikes mit Call-dominantem Gamma, ziehen den Kurs im positiven
  Regime zurueck (Pinning-Effekt, staerker Richtung Verfall).
- **Vanna/Charm-Overlays:** Sekundaer-Hedgingfluesse aus Vola-Aenderung (Vanna) bzw.
  Zeitablauf (Charm), nur aktiv (\"gated\") wenn ihre Vorbedingung erfuellt ist (echte Vola-"
  Bewegung bzw. Naehe zum Verfall) -- sonst \"still\", um Rauschen zu vermeiden.
- **Regime x Lage:** die eigentliche Handelsaussage kombiniert das Gamma-Regime (Range/Trend)
  mit der Kurslage relativ zu den Leveln (an einer Wall, am Flip, im freien Raum) -- kein
  isoliertes Kauf-/Verkaufssignal aus dem Regime allein.
"""
        )

    st.error(
        "**Machbarkeit: nicht umsetzbar mit aktuellem Datenbestand.** Die Engine braucht "
        "Strike-fuer-Strike Open Interest UND Echtzeit-Optionsquotes fuer COMEX-Gold-Optionen "
        "(im Paper: Sierra Chart + lizenzierter CME/COMEX-Denali-Feed, ~43 USD/Monat, "
        "**zusaetzlich** ein verifiziertes, finanziertes Handelskonto bei einem unterstuetzten "
        "Broker). Dieses Repo hat aktuell **keine Optionsdaten-Quelle** (Dukascopy liefert nur "
        "Kassa-/CFD-artige OHLC-Reihen, kein Open Interest, keine Optionsketten). Eine "
        "Nachimplementierung waere ein komplettes neues Daten-Beschaffungsprojekt (neuer "
        "kostenpflichtiger Feed + eigener Options-Pricing-Layer), kein einfacher Filter-Baustein. "
        "**Dokumentiert als potenziell wertvoller, aber aktuell nicht machbarer Kontext-Layer** -- "
        "relevant, falls irgendwann eine Optionsdaten-Quelle angebunden wird.",
        icon=":material/block:",
    )
    st.caption(
        "Hinweis zur Quelle: Eigenpublikation eines Einzelautors (kein Peer-Review, kommerzieller "
        "Unterton \"$42.80/Monat statt $1999\") -- die Methodik selbst (Black-76, Dealer-Sign-"
        "Konvention, Repriced-Root-Zero-Crossing) ist Standard-Marktmikrostruktur-Literatur "
        "(Ni/Pearson/Poteshman 2005; Avellaneda/Lipkin 2003) und plausibel, aber die konkrete "
        "Engine selbst ist nicht unabhaengig geprueft/backtested (\"No backtested P&L claim is "
        "made\", explizit vom Autor selbst so benannt)."
    )

# =============================================================================
# Tab 3: Gold-Silver-BTC Lead-Lag
# =============================================================================
with tab3:
    st.markdown("### Sulistyardi (2026) -- Regime-Conditional Rolling Correlation & Lead-Lag: XAUUSD, XAGUSD, BTCUSD")
    st.caption("SSRN 7200580 -- Literatursynthese + vorgeschlagenes Rahmenwerk (nicht selbst empirisch getestet)")

    st.markdown(
        "**Kernaussage:** Gold-Silber-Korrelation ist historisch stark (0.68-0.95, im Schnitt "
        "~0.80-0.92 ueber mehrere unabhaengige Quellen), aber nicht perfekt stabil -- kurzfristige "
        "Fuehrungswechsel kommen vor. Gold-Bitcoin-Korrelation ist deutlich schwaecher (~0.62, "
        "2018-2023) und instabiler ('Bitcoin ist nicht das neue Gold'). These: **Silber fuehrt in "
        "Momentum-/Breakout-Phasen** (hoeheres Beta, spekulativerer Orderflow), **Gold fuehrt in "
        "reinen Safe-Haven-Schocks** (tiefere institutionelle Liquiditaet) -- illustriert an der "
        "Dezember-2025-Divergenz (Gold Rekordjahr, Silber verstaerkt beide Richtungen, Bitcoin "
        "-30% vom Oktoberhoch). **Das Paper selbst liefert keine eigene empirische Validierung** -- "
        "es ist explizit als Rahmenwerk-Vorschlag fuer kuenftige Tests formuliert."
    )

    st.markdown("**Extrahierte Bausteine -- alle mit vorhandenen Daten umsetzbar**")
    st.success(
        "Anders als Tab 1/2/4: **diese Idee ist direkt mit unserem bestehenden Datenbestand "
        "testbar** -- Gold/Silber via Dukascopy (bereits genutzt), Bitcoin via Binance (bereits "
        "in `auction_playbook` genutzt), DXY bereits als eigenes Modul vorhanden "
        "(`asian_range_breakout/dxy.py`, aus dem 151-Strategies-Test). Kein neuer Datenzugang "
        "noetig.",
        icon=":material/check_circle:",
    )
    with st.expander("Die drei Bausteine im Detail", icon=":material/list:"):
        st.markdown(
            """
1. **Rolling-Correlation (mehrere Fenster):** Pearson-Korrelation der Log-Returns ueber
   mehrere Fenstergroessen gleichzeitig (z.B. 20/60/90/252 Tage), um kurz- und langfristige
   Dynamik gemeinsam zu erfassen -- statt einer einzelnen statischen Korrelationszahl.
2. **Cross-Correlation-Function (CCF) Lead-Lag:** Korrelation zwischen Asset A heute und
   Asset B in k Tagen (k = -10 bis +10) -- der Lag mit der staerksten Korrelation zeigt, wer
   wen fuehrt.
3. **Regime-Klassifikation:** Handelstage in "Momentum/Rally" (Gold-Silber-Ratio verengt sich
   schnell) vs. "Safe-Haven-Schock" (DXY schwaecht sich stark ab + Vola-Spike) einteilen, dann
   die CCF-Analyse GETRENNT pro Regime wiederholen -- testet, ob die Fuehrungsrolle
   regimeabhaengig wechselt, statt eine fixe Beziehung anzunehmen.
"""
        )
    st.success(
        "**Update 2026-08-08, getestet: implementiert, jetzt Standard.** Einfachste testbare "
        "Uebersetzung -- Long-Breakouts nur in Richtung von Silbers eigener 5-Tage-Kursbewegung, "
        "Short umgekehrt -- haelt Fenster-Sweep, IS/OOS UND Walk-Forward stand "
        "(`scripts/research_gold_silver_leadlag_filter.py`): Profit Factor 1.24 → 1.43, Sharpe "
        "0.49 → 0.61, Max Drawdown -5.0% → -4.0%, **Win-Rate steigt sogar mit** (43.1% → 46.5%, "
        "anders als bei den meisten anderen Filtern hier). Walk-Forward bestaetigt 5/6 Testjahre "
        "und rettet insbesondere das zuvor schwache 2023. Der erste getestete Baustein aus "
        "diesen fuenf Papers, der auf Anhieb robust ist. Details: "
        "`app_pages/asian_range_breakout.py` (Tab \"Strategiebestandteile\").",
        icon=":material/check_circle:",
    )

# =============================================================================
# Tab 4: Grading the Graders
# =============================================================================
with tab4:
    st.markdown("### Mouynes (2026) -- Grading the Graders: institutionelle Jahres-Ausblicke")
    st.caption("Working Paper -- Bewertung von 15 Institutionen (Banken, Political-Risk-Häuser, IWF, Einzelpersonen), 2016-2026")

    st.markdown(
        "**Kernaussage (kein Strategie-Paper, sondern eine Meta-Studie):** Jaehrliche "
        "institutionelle Markt-/Geopolitik-Ausblicke (Goldman, JPMorgan, Eurasia Group, IWF "
        "usw.) werden systematisch gegen ein striktes Bewertungsraster geprueft (nur konkrete, "
        "ueberpruefbare Aussagen zaehlen). Ergebnis: die 15 Institutionen erreichen zusammen nur "
        "**~1 von 45 moeglichen Punkten (2024), ~7.5/45 (2025), ~2/45 (2026 H1)**. Drei "
        "wiederkehrende Muster: (1) der Konsens ist ein **nachlaufender Indikator** -- er "
        "extrapoliert im Wesentlichen das Vorjahr; (2) **vage, thematische Aussagen ueberleben, "
        "konkrete Zahlen-Prognosen scheitern** (z.B. S&P-500-Jahresziele lagen 2022 und 2023 in "
        "**entgegengesetzte** Richtungen falsch); (3) das eigentliche **Transmissions-Instrument "
        "eines Marktereignisses steht nie auf einer Liste** (z.B. japanischer Leitzins vor dem "
        "Carry-Trade-Crash 2024, Strait of Hormuz vor dem Ölschock 2026)."
    )

    st.warning(
        "**Kein extrahierbarer Filter oder Backtest-Baustein -- eine methodische Warnung, kein "
        "Strategie-Rezept.** Das Paper liefert keine Handelsregel, sondern einen empirisch "
        "fundierten Grund, **Analysten-Konsens/Bank-Kursziele/institutionelle Jahresausblicke "
        "grundsaetzlich NICHT als Signal fuer eine Strategie zu verwenden** -- sie sind laut "
        "dieser Auswertung strukturell nachlaufend, nicht vorlaufend. Relevanter Seiteneffekt: "
        "bestaetigt indirekt, warum wir in diesem Repo konsequent auf Preis-/Positionsdaten "
        "statt auf Analysten-Meinungen setzen.",
        icon=":material/fact_check:",
    )
    st.caption(
        "Falls je eine \"Sentiment aus Nachrichtenüberschriften/Analysten-Kurszielen\"-Idee "
        "aufkommt: dieses Paper ist der Grund, sie ohne sehr starke Gegenevidenz nicht zu "
        "verfolgen."
    )

# =============================================================================
# Tab 5: COT Sentiment (Precious Metals)
# =============================================================================
with tab5:
    st.markdown("### Zhang & Laws (2013) -- Investor Sentiment and Forecasting Ability: Evidence from COT Reports in Precious Metal Futures Markets")
    st.caption("SSRN 2382299 -- Gold/Silber/Platin-Futures (CME), woechentliche CFTC-COT-Daten, Januar 1996 - Dezember 2012")

    st.success(
        "**Der ergiebigste Baustein dieser fuenf Papers -- akademisch rigoros, direkt mit "
        "vorhandenen (neuen, aber kostenlosen) Daten testbar.** CFTC Commitments-of-Traders-"
        "Berichte sind oeffentlich, woechentlich, kostenlos (seit 1996 als Volltext/CSV "
        "abrufbar) -- eine neue, aber leicht anbindbare Datenquelle.",
        icon=":material/check_circle:",
    )

    st.markdown("**Kernaussage**")
    st.markdown(
        """
- **Starke GLEICHZEITIGE Beziehung**, aber **keine Vorhersagekraft**: Commercial-Trader-
  Sentiment korreliert NEGATIV mit Renditen (sie sind Contrarians/Hedger -- verkaufen in
  steigende Maerkte, kaufen in fallende), Non-Commercial/Non-Reporting-Sentiment korreliert
  POSITIV (Trendfolger). Granger-Kausalitaet zeigt aber: **Renditen fuehren das Sentiment,
  nicht umgekehrt** -- Positionierung ist eine Reaktion auf Preisbewegung, kein Fruehindikator.
- **Extreme Positionen** (oberste/unterste 20%-Perzentil der letzten 3 Jahre) zeigen ebenfalls
  **kaum robuste Vorhersagekraft** -- nur vereinzelt signifikant (z.B. Gold, nicht konsistent
  ueber Silber/Platin).
- **Trotzdem profitabel als mechanisches mean-reversion/Trendfolge-Signal**: eine simple
  Handelsregel (Long wenn Commercial-Sentiment ueber dem 3-Jahres-Median -- da Commercials
  Contrarians sind, deutet das auf einen bereits erfolgten Ausverkauf hin; Short umgekehrt)
  schlaegt eine naive Buy-and-Hold-Strategie deutlich: **Information Ratio 1.17 vs. 0.69 bei
  Gold**, niedrigerer Max Drawdown (-8% vs. -16%). Wichtig: das ist NICHT dasselbe wie "COT
  sagt die Rendite voraus" -- es ist ein Positionierungs-Signal, das im Rueckblick (1999-2012)
  gut funktionierte, aber die Autoren selbst betonen, dass die Granger-Kausalitaet dafuer
  **keine** statistische Grundlage liefert (Vorsicht vor Overfitting/Data-Mining derselben
  Erkenntnis in eine Handelsregel).
"""
    )

    st.markdown("**Extrahierter Baustein: COT-Sentiment-Index (Wang 2001)**")
    with st.expander("Formel & Konstruktion", icon=":material/functions:"):
        st.markdown(
            r"""
Fuer jede Trader-Gruppe (Commercial / Non-Commercial / Non-Reporting) und jede Woche:

$$SI_t = \frac{S_t - \min(S_{t-156:t})}{\max(S_{t-156:t}) - \min(S_{t-156:t})}$$

wobei $S_t$ = Netto-Position (Long-Open-Interest minus Short-Open-Interest) und der Min/Max
ueber ein rollierendes 3-Jahres-Fenster (156 Wochen) berechnet wird -- ein Oszillator zwischen
0 (3-Jahres-Tief) und 1 (3-Jahres-Hoch), direkt vergleichbar ueber verschiedene Maerkte hinweg
(anders als die rohe Netto-Position, die je nach Marktgroesse stark variiert).

**Handelsregel aus dem Paper:** bullish (SI > rollierender Median) bei Commercials → Long;
bullish bei Non-Commercials/Non-Reporting → Short (da sie sich entgegengesetzt zu den
Commercials verhalten). Position wird gehalten, bis das Gegensignal kommt.
"""
        )

    st.error(
        "**Update 2026-08-08, getestet: keine robuste Kante, nicht implementiert.** COT-Daten "
        "kostenlos ueber die CFTC-Socrata-API angebunden (`asian_range_breakout/cot.py`, "
        "1996-2026 Historie, kein API-Key noetig). Als Richtungsfilter auf den Asian-Range-"
        "Breakout getestet (`scripts/research_gold_cot_sentiment_filter.py`): die "
        "Commercial-Konvention aus dem Paper sieht im vollen Zeitraum ueber alle drei getesteten "
        "Fenster (2/3/4 Jahre) konsistent aus, **bricht aber Out-of-Sample vollstaendig "
        "zusammen** (PF 1.24 vs. 1.25 -- ein Unentschieden; der gesamte scheinbare Vorteil steckt "
        "nur im In-Sample-Teil, PF 1.72 vs. 1.11). Die gespiegelte Non-Commercial-Konvention "
        "kippt das Vorzeichen schon im reinen Fenster-Sweep. Deckt sich mit dem eigenen ehrlichen "
        "Befund des Original-Papers (Granger-Kausalitaet zeigt dort keine echte Vorhersagekraft, "
        "nur eine gleichzeitige Korrelation) -- der historisch gezeigte Handelserfolg "
        "(1999-2012, andere Instrumente/Konstruktion) repliziert sich nicht auf unserem System. "
        "Details im Asian-Range-Breakout-Dashboard (Tab \"Strategiebestandteile\").",
        icon=":material/fact_check:",
    )

st.space("medium")
st.success(
    "**Gesamtfazit ueber alle fuenf Papers (Update 2026-08-08, final):** Von fuenf Papers "
    "waren zwei mit vorhandenen Daten direkt testbar (Tab 3, Tab 5) -- **einer davon liefert "
    "einen echten, walk-forward-bestaetigten neuen Filter** (Silber-Alignment, Tab 3: PF 1.24 → "
    "1.43, jetzt Standard im Asian-Range-Breakout-Dashboard). COT-Sentiment (Tab 5) bricht "
    "Out-of-Sample zusammen, nicht implementiert. Tab 1 (Korea-spezifisch) und Tab 2 (braucht "
    "Optionsdaten) sind konzeptionell dokumentiert, aber nicht umsetzbar. Tab 4 ist keine "
    "Strategie-Quelle, sondern eine methodische Warnung. **Trefferquote: 1 von 5 Papers liefert "
    "direkt einen produktiven Baustein** -- innerhalb der ueblichen Erfahrung dieses Repos mit "
    "extern uebernommenen Ideen.",
    icon=":material/summarize:",
)
