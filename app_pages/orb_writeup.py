"""Strategie Bestandteile -- Opening Range Breakout (ORB).

Reine Wissens-/Referenzseite zum Paper Holmberg, Loennbark & Lundstroem
(2013), "Assessing the profitability of intraday opening range breakout
strategies", Finance Research Letters 10(1), 27-33. Noch KEIN Backtest --
das ist bewusst ein separater, spaeterer Schritt (siehe Info-Box unten).
"""

import streamlit as st

st.set_page_config(page_title="ORB -- Strategiebestandteile", page_icon=":material/bolt:", layout="wide")

st.markdown("## :material/bolt: Opening Range Breakout (ORB) -- Strategiebestandteile")
st.caption(
    "Quelle: Holmberg, U., Loennbark, C., Lundstroem, C. (2013). \"Assessing the "
    "profitability of intraday opening range breakout strategies.\" "
    "Finance Research Letters, 10(1), 27-33. DOI: 10.1016/j.frl.2012.09.001"
)

st.markdown(
    "Die Kernidee: die klassische **Opening Range Breakout**-Regel -- Einstieg, sobald "
    "der Kurs eine Schwelle ueber/unter dem Eroeffnungspreis durchbricht. Der eigentliche "
    "Beitrag des Papers ist aber methodisch: die Autoren zeigen, dass sich die "
    "Profitabilitaet einer *intraday* Regel allein aus **taeglichen OHLC-Daten** "
    "(Open/High/Low/Close) statistisch abschaetzen laesst, ganz ohne echte Intraday-"
    "Tickdaten."
)

st.markdown("### Die Theorie: Contraction-Expansion-Prinzip (Crabel, 1990)")
st.markdown(
    "Maerkte wechseln zwischen zwei Regimen. Die ORB-Regel versucht, gezielt "
    "**Expansion-Tage** zu erwischen -- der Test im Paper prueft, ob an genau diesen "
    "Tagen die Random-Walk-Annahme (Martingale-Eigenschaft) tatsaechlich bricht."
)
col_contraction, col_expansion = st.columns(2)
with col_contraction:
    st.info(
        "**Contraction (ruhig)**\n\nRenditen ~normalverteilt, Random Walk / EMH "
        "haelt naeherungsweise. Kein Trade-Signal.",
        icon=":material/compress:",
    )
with col_expansion:
    st.success(
        "**Expansion (Ausbruch)**\n\nGrosse Kursbewegung, Momentum, Non-Normalitaet -- "
        "genau hier soll die ORB-Regel Positionen aufbauen.",
        icon=":material/expand:",
    )

st.markdown("### Die Regel")
st.markdown(
    "Aus dem Eroeffnungspreis $P^o_t$ werden zwei Schwellen abgeleitet: $\\psi^u$ "
    "(oberhalb) und $\\psi^l$ (unterhalb). Durchbricht der Tages-High $\\psi^u$, wird "
    "eine **Long**-Position unterstellt; durchbricht der Tages-Low $\\psi^l$, eine "
    "**Short**-Position. Unter der Annahme normalverteilter Tagesrenditen lassen sich "
    "die Schwellen direkt aus der Volatilitaet kalibrieren, statt eine willkuerliche "
    "feste Prozentzahl zu waehlen."
)

st.markdown("### Methodischer Kniff")
st.markdown(
    "Statt echter Intraday-Daten reicht die Beobachtung \"High/Low haben die Schwelle "
    "an diesem Tag durchbrochen\" -- daraus wird auf eine Position an diesem Tag "
    "geschlossen. Die Signifikanz wird per Bootstrap (angelehnt an Brock et al., 1992) "
    "getestet."
)

st.markdown("### Empirischer Befund (US-Rohoel-Futures, 1983-2011)")
st.warning(
    "**Auf der Gesamtstichprobe:** \"bemerkenswerter Erfolg\" der ORB-Strategie -- "
    "signifikant positive Renditen, erhoehte Trefferquote gegenueber einem fairen "
    "Spiel.\n\n**Aber:** bei Aufteilung in drei Teilperioden ist der Effekt **nicht "
    "robust ueber die Zeit** und wird zu einem grossen Teil von der juengsten (und "
    "volatilsten) Teilperiode getragen. Die Autoren selbst warnen also vor genau dem "
    "Muster, das wir in diesem Projekt immer wieder gefunden haben: ein gepoolt gut "
    "aussehender Effekt, getragen von 1-2 Ausreisser-Perioden statt einem echten, "
    "stabilen Effekt.",
    icon=":material/warning:",
)

st.markdown("### Was das fuer unser Projekt bedeuten koennte")
st.markdown(
    """
1. **ORB als Entry-Mechanik** -- Referenz-Open (Tag oder Session) + Schwelle ±X% oder
   ±X·ATR, Long bei Bruch nach oben, Short nach unten. Konzeptionell verwandt mit dem
   Nadaraya-Watson-Envelope-Ausbruch in `checklist_strategy`, nur bezogen auf den
   Open statt auf ein Kernel-Regressions-Band.
2. **Statistisch kalibrierte statt fixe Schwelle** -- Schwelle = k × rollierende
   Volatilitaet (ATR) statt fixer Prozentsatz, direkt mit vorhandener Infrastruktur
   umsetzbar (`strategy.indicators.compute_atr`).
3. **Contraction-Expansion als Regime-Filter** -- spiegelbildlich zum
   "nicht stark trendend"-Filter in `checklist_strategy`: ORB *braucht* die
   Expansion-Phase, profitiert also von einem "Volatilitaet JETZT hoch"-Filter statt
   einem, der Trends ausschliesst.
4. **Asset-Wahl Rohoel ist kein Zufall** -- die Autoren finden den Effekt spezifisch
   bei Rohoel-Futures. In unserem eigenen Checklist-Test war Oel (M15) das Asset mit
   dem am wenigsten negativen Baseline-Ergebnis unter den Nicht-FX-Assets (Sharpe
   ~0.00) -- ein moeglicher Hinweis auf einen echten Momentum-Charakter bei Oel,
   den eine Mean-Reversion-Strategie gar nicht erst zu fassen versucht.
5. **Die eingebaute Warnung ernst nehmen** -- von Anfang an mit Jahres-Walk-Forward
   testen (wie bei jeder Strategie in diesem Projekt), nicht nur auf der
   Gesamtperiode urteilen.
"""
)

st.info(
    "**Naechster Schritt:** noch kein Backtest -- das ist bewusst ein separater, "
    "spaeterer Schritt. Diese Seite haelt nur die Erkenntnisse aus dem Paper fest.",
    icon=":material/hourglass_empty:",
)
