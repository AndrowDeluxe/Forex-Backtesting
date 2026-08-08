"""Strategie Bestandteile -- Gap-Fade EUR/USD & GBP/USD.

Reine Wissens-/Referenzseite zum Paper Caporale & Plastun (2016), "Price
Gaps: Another Market Anomaly?", Brunel University London / Sumy State
University, Working Paper 16-16 (SSRN 2850057). Noch KEIN Backtest -- das
ist bewusst ein separater, spaeterer Schritt (siehe Info-Box unten), gleiches
Muster wie orb_writeup.py.
"""

import streamlit as st

st.set_page_config(page_title="Gap-Fade EUR/USD -- Strategiebestandteile", page_icon=":material/south_east:", layout="wide")

st.markdown("## :material/south_east: Gap-Fade EUR/USD & GBP/USD -- Strategiebestandteile")
st.caption(
    "Quelle: Guglielmo Maria Caporale & Alex Plastun (2016). \"Price Gaps: Another "
    "Market Anomaly?\" Brunel University London / Sumy State University, Working "
    "Paper 16-16 (SSRN 2850057). Datenbasis: EUR/USD, GBP/USD, USD/RUB, Oel, Gold, "
    "Dow Jones, IBM, MICEX, Sberbank -- Tagesdaten 2000-2015."
)

st.markdown(
    "Von sechs getesteten Gap-Hypothesen ueber FX, Rohstoffe und Aktienmaerkte bleibt "
    "in fast allen Maerkten nichts Anomales uebrig -- ausser in **Forex**. In EUR/USD "
    "und GBP/USD ist die Reaktion auf positive Kursluecken statistisch signifikant und "
    "mechanisch handelbar."
)

st.markdown("### Testrahmen: sechs Hypothesen, ein Ueberlebender")
st.markdown(
    """
- **H1/H2** -- Folgt der Kurs nach dem Gap seiner Richtung weiter? -> ueberwiegend nein.
- **H3/H4** -- Kuendigt sich das Gap durch Kursverhalten davor an? -> ueberwiegend nein (Ausnahme USD/RUB).
- **H5** -- "Der Markt verabscheut ein Vakuum, Gaps werden gefuellt"? -> bis zu 80% der Gaps bleiben nach 5 Tagen ungefuellt.
- **H6** -- Unterscheidet sich die Renditeverteilung am Gap-Tag von normalen Tagen? -> **ja, signifikant -- aber nur EUR/USD und GBP/USD.**
"""
)
st.caption(
    "9 von 10 getesteten Marktkombinationen zeigen keine handelbare Anomalie -- FX ist "
    "die Ausnahme, und genau dort liegt bereits der Fokus dieses Repos."
)

st.markdown("### Die Handelsregel")
st.markdown(
    "FX-Gaps entstehen fast ausschliesslich am Montag (95-96% aller Faelle in "
    "EUR/USD, GBP/USD, USD/RUB) -- reines Wochenend-Artefakt. Die Regression mit "
    "Dummy-Variable zeigt: der Effekt sitzt spezifisch bei **positiven** Gaps, mit "
    "negativem Vorzeichen -- der Markt gibt einen Teil der Luecke wieder ab."
)
st.code(
    "WENN Eroeffnungskurs > Vortagesschluss UM >= Schwellenwert:\n"
    "    -> Short zur Eroeffnung\n"
    "    -> Glattstellen zum Handelsschluss (EOD)\n"
    "SONST: kein Trade",
    language="text",
)

st.markdown(
    "Der Schwellenwert wurde ueber ein Gap-Groessen-Raster (0,05%-0,25%) optimiert -- "
    "mit explizitem Profit/Drawdown-Trade-off, nicht nur nach Maximalprofit:"
)
st.markdown(
    """
| Gap-Groesse | EUR/USD Profit | Trades | DD % | GBP/USD Profit | Trades | DD % |
|---|---|---|---|---|---|---|
| 0,05% | 1.927 | 92 | 5,1 | 4.820 | 221 | 5,6 |
| **0,10%** | **1.835** | **58** | **2,8** | 2.191 | 113 | 6,8 |
| 0,15% | 1.741 | 40 | 2,8 | 2.065 | 69 | 5,9 |
| 0,20% | 1.397 | 29 | 2,8 | 1.692 | 41 | 5,6 |
| 0,25% | 1.504 | 23 | 2,8 | **1.704** | **27** | **4,9** |
"""
)
st.caption(
    "Gewaehlt: 0,10% fuer EUR/USD (halbes Drawdown bei nur leicht geringerem Profit "
    "als 0,05%), 0,05% fuer GBP/USD (hoechster Profit, GBP/USD toleriert das "
    "Drawdown-Niveau)."
)

st.markdown("### Ergebnis: 16 Jahre, 3 Verlustjahre")
st.success(
    "**EUR/USD (Gap >= 0,10%):** 148 Trades, 63,5% Trefferquote, +2.659 Punkte, z = 2,43.\n\n"
    "**GBP/USD (Gap >= 0,05%):** 221 Trades, 60,0% Trefferquote, +4.775 Punkte, z = 3,15.\n\n"
    "z-kritisch (95%) = 1,96 -> beide Nullhypothesen verworfen.",
    icon=":material/query_stats:",
)

with st.expander("Jahr-fuer-Jahr-Ergebnis, 2000-2015", icon=":material/calendar_month:"):
    st.markdown(
        """
| Jahr | EUR/USD Pkt. | Treffer % | Trades | GBP/USD Pkt. | Treffer % | Trades |
|---|---|---|---|---|---|---|
| 2000 | 172 | 60 | 10 | 467 | 63 | 19 |
| 2001 | -5 | 60 | 5 | 398 | 62 | 13 |
| 2002 | -284 | 40 | 5 | -294 | 33 | 9 |
| 2003 | 112 | 50 | 10 | 299 | 53 | 17 |
| 2004 | 73 | 50 | 12 | 25 | 64 | 11 |
| 2005 | -40 | 50 | 4 | 150 | 56 | 9 |
| 2006 | 215 | 100 | 4 | 423 | 69 | 13 |
| 2007 | 393 | 67 | 9 | 218 | 64 | 14 |
| 2008 | -56 | 63 | 19 | 1.137 | 65 | 20 |
| 2009 | 218 | 50 | 16 | 867 | 54 | 13 |
| 2010 | 770 | 71 | 14 | 357 | 63 | 16 |
| 2011 | 302 | 80 | 10 | 185 | 64 | 11 |
| 2012 | 362 | 80 | 10 | 159 | 69 | 16 |
| 2013 | 175 | 63 | 8 | -323 | 20 | 10 |
| 2014 | 98 | 100 | 4 | 191 | 63 | 16 |
| 2015 | 137 | 63 | 8 | 383 | 75 | 12 |
| **Gesamt** | **2.659** | **63,5** | **148** | **4.775** | **60,0** | **221** |
"""
    )
    st.caption(
        "Nur 3 von 16 Jahren (EUR/USD) bzw. 2 von 16 (GBP/USD) negativ -- kein "
        "Ergebnis, das von einem einzelnen Ausreisserjahr getragen wird."
    )

st.markdown("### Was das fuer unser Projekt bedeuten koennte")
st.markdown(
    """
1. **Eigenstaendig statt Filter** -- anders als der Execution-Overlay ist dies eine
   vollstaendige, univariate Strategie -- sinnvoller Kandidat fuer einen eigenen,
   separaten Backtest-Strang statt einer Ergaenzung zum bestehenden ADX-VWAP-Sweep.
2. **Schwellenwert neu ableiten** -- 0,10%/0,05% stammen aus 2000-2015-Daten. Auf
   der bereits vorhandenen Dukascopy-EUR/USD-Historie (`strategy/real_data.py`) das
   Raster selbst neu rechnen, statt die alten Werte zu uebernehmen.
3. **Gap-Definition am eigenen Datenfeed verifizieren** -- pruefen, wie Dukascopy
   "Wochenend-Gap" tatsaechlich abbildet (Freitagsschluss vs. Sonntagabend-Reopen).
4. **Stop definieren** -- das Paper nennt ausser dem EOD-Exit keinen expliziten
   Stop-Loss. Fuer den eigenen Test einen Schutz-Stop ergaenzen.
"""
)

st.warning(
    "**Ehrlicher Vorbehalt:** der 0,05-0,25%-Raster oben wurde in-sample optimiert, "
    "bevor der finale Test lief -- ein kleines, aber reales Data-Snooping-Element, "
    "gleiches Grundmuster wie schon mehrfach in diesem Projekt gefunden (z. B. "
    "checklist_strategy's \"best hours\"-Filter, der OOS scheiterte, oder der "
    "1-von-135-Combo-\"Gewinner\" bei `strategy/cls_london_breakout.py`). Fuenf "
    "getestete Werte sind harmlos im Vergleich zu einem 135-Combo-Sweep, aber die "
    "eigene Nachrechnung sollte den Schwellenwert entweder auf einem Trainingsfenster "
    "fixieren und out-of-sample pruefen, oder die Sensitivitaet ueber das ganze "
    "Raster zeigen statt nur den Gewinner.",
    icon=":material/warning:",
)

st.info(
    "**Naechster Schritt:** noch kein Backtest -- das ist bewusst ein separater, "
    "spaeterer Schritt. Diese Seite haelt nur die Erkenntnisse aus dem Paper fest.",
    icon=":material/hourglass_empty:",
)
