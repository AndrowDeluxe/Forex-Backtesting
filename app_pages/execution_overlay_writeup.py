"""Strategie Bestandteile -- Execution-Overlay (Fast Alpha als Timing-Filter).

Wissens-/Referenzseite zum Paper Zarattini & Pagani (2026), "Improving
Performance with Fast Alphas -- A Tactical Overlay for Intraday Trend
Trading", Concretum Research, QuanTips #2, PLUS der eigene Backtest
(execution_overlay/ + scripts/research_execution_overlay.py): SPY-Schnellblick
(yfinance, nur ~60 Tage) und ein voll gepowerter EUR/USD-Test (Dukascopy,
2016-2026). Befund: auf EUR/USD hat schon die Basisstrategie keine Kante --
der Overlay hat dort nichts zu verfeinern. Siehe Befund-Sektion unten.
"""

import streamlit as st

st.set_page_config(page_title="Execution-Overlay -- Strategiebestandteile", page_icon=":material/timer:", layout="wide")

st.markdown("## :material/timer: Execution-Overlay: Fast Alpha als Timing-Filter -- Strategiebestandteile")
st.caption(
    "Quelle: Carlo Zarattini & Alberto Pagani (2026). \"Improving Performance with Fast "
    "Alphas -- A Tactical Overlay for Intraday Trend Trading.\" Concretum Research, "
    "QuanTips #2. Datenbasis: SPY, 5-Minuten-Bars, Januar 2007 - Januar 2026."
)

st.markdown(
    "Die Kernidee: ein Signal, das als eigenstaendige Strategie an den Kosten stirbt, "
    "kann trotzdem echte Information ueber die nahe Zukunft des Preises enthalten -- "
    "wenn man es nicht direkt handelt, sondern nur nutzt, um den **Ausfuehrungszeitpunkt** "
    "einer anderen, bereits profitablen Strategie zu verfeinern."
)

st.markdown("### Das Konzept: informationelles vs. monetarisierbares Alpha")
col_mon, col_info = st.columns(2)
with col_mon:
    st.info(
        "**Monetarisierbares Alpha**\n\nUebersteht realistische Handelskosten als "
        "eigenstaendige Strategie. Kann direkt gehandelt werden.",
        icon=":material/payments:",
    )
with col_info:
    st.success(
        "**Informationelles Alpha**\n\nStirbt als Solo-Strategie an den Kosten, enthaelt "
        "aber echte Richtungsinformation -- nutzbar als Filter, der *wann* eine andere "
        "Strategie ausloest, ohne selbst gehandelt zu werden.",
        icon=":material/insights:",
    )

st.markdown("### Der Beweis im Original: SPY, 5-Min-Streak-Reversal")
st.markdown(
    "Das Fast-Alpha-Signal ist bewusst extrem gewaehlt: nach jedem 5-Minuten-Bar wird "
    "gegen dessen Richtung gewettet (\"Streak-Reversal\", $S_t = -\\text{sign}(R_t)$). Je "
    "laenger die vorangegangene Serie gleichgerichteter Bars, desto staerker die "
    "Gegenbewegung im naechsten Bar -- aber desto seltener tritt sie auf:"
)
st.markdown(
    """
| Serie >= N | Richtung | Trades/Tag | Rendite naechster Bar (bps) | Turnover/Tag |
|---|---|---|---|---|
| 1 | nach Down | 39,32 | +0,18 | 39,3x |
| 2 | nach Down | 18,35 | +0,30 | 18,4x |
| 4 | nach Down | 3,65 | +0,42 | 3,7x |
| 1 | nach Up | 39,45 | -0,13 | 39,5x |
| 2 | nach Up | 19,27 | -0,24 | 19,3x |
| 4 | nach Up | 4,19 | -0,33 | 4,2x |
"""
)

st.error(
    "**N=1-Reversal als Solo-Strategie, IBKR-Kommission $0,0035/Aktie:** "
    "brutto CAGR 31,9% / Sharpe 2,09 -> **netto CAGR -0,7% / Sharpe 0,02**. "
    "Tot als eigenstaendige Strategie.",
    icon=":material/trending_down:",
)
st.success(
    "**Als Timing-Filter fuer eine ATR-Breakout-Trendstrategie (netto):** "
    "ohne Overlay CAGR 13,2% / Sharpe 0,86 -> **mit Overlay CAGR 15,3% / Sharpe 0,99** "
    "(+200 bps CAGR, +0,13 Sharpe).",
    icon=":material/trending_up:",
)

st.markdown("### Mechanismus im Detail")
st.markdown("**Basisstrategie (der Traeger)**")
st.markdown(
    """
1. ATR(14)-Baender um den Session-Open: obere Bande = Open + 0,5*ATR, untere = Open - 0,5*ATR.
2. Long bei Schlusskurs ueber der oberen Bande, Short bei Schlusskurs unter der unteren Bande.
3. Ausfuehrung nur zu festen 15-Minuten-Marken (HH:00/:15/:30/:45) -- reduziert Overtrading durch Mikro-Rauschen.
4. Stop = Session-Open (Rueckkehr zum Eroeffnungsniveau gilt als gescheiterter Breakout).
5. Positionsgroesse ueber 14-Tage-Vol-Targeting (2% Ziel-Tagesvolatilitaet), einmal pro Session fixiert.
6. Glattstellung zum Handelsschluss -- keine Overnight-Exposure.
"""
)
st.markdown("**Der Overlay (die Verfeinerung)**")
st.markdown(
    "Entry und Exit werden nicht sofort ausgefuehrt, sondern erst, wenn das "
    "Fast-Alpha-Signal einen kurzfristigen Gegenimpuls anzeigt: Breakout erkannt -> "
    "warten auf den ersten 5-Min-Bar mit Gegenrichtung -> Entry zur naechsten "
    "15-Min-Marke. Symmetrisch fuer den Exit am Stop -- gleiche Logik, umgekehrte Richtung. "
    "Das Signal wird nie direkt gehandelt, nur zur Konditionierung des "
    "Ausfuehrungszeitpunkts genutzt."
)

st.info(
    "**Warum das funktioniert (Intuition):** klassische Trendfolge ist "
    "liquiditaetskonsumierend -- sie kauft in beschleunigende Bewegungen hinein und "
    "bezahlt den vollen Spread. Der Overlay verschiebt das Verhalten in Richtung "
    "Liquiditaetsbereitstellung: er wartet auf eine kurze Gegenbewegung, statt der "
    "Bewegung sofort hinterherzulaufen.",
    icon=":material/lightbulb:",
)

st.markdown("### Adaptions-Vorschlag fuer EUR/USD")
st.markdown(
    """
1. **Session-Konzept neu definieren** -- EUR/USD handelt 24 Stunden, "Session-Open" "
   braucht eine explizite Wahl (Tagesbeginn 00:00 UTC, London-Open 08:00 UTC oder
   NY-Open 13:00 UTC), konsistent mit der bereits vorhandenen Session-Logik in
   `strategy/`.
2. **Fast-Alpha-Signal neu kalibrieren** -- Streak-Laenge N und Sampling-Frequenz
   (5 Min im Original) auf EUR/USD-Volatilitaetsstruktur pruefen, bevor sie als
   Filter eingesetzt wird -- eine eigene Version der Streak-Tabelle oben rechnen.
3. **Kostenmodell FX-spezifisch ansetzen** -- statt $0,0035/Aktie realistischen
   Spread (typ. 0,5-1,5 Pip ECN) plus ggf. Kommission ansetzen.
4. **Ausfuehrungsraster pruefen** -- ob 5-, 15- oder 30-Minuten-Raster fuer EUR/USD
   optimal ist, muss die vorhandene Backtesting-Infrastruktur separat austesten.
"""
)

st.warning(
    "**Offene Risiken:** der Overlay reduziert die Handelsfrequenz gegenueber der "
    "reinen Trendstrategie -- das veraendert die statistische Power jedes "
    "nachfolgenden Parameter-Sweeps (weniger Trades -> breitere Konfidenzintervalle). "
    "Zudem kann er in sehr starken, pullback-freien Trends Einstiege verpassen; das "
    "Paper haelt das fuer selten (die Pullback-Anforderung ist bewusst milde), fuer "
    "EUR/USD aber unabhaengig zu verifizieren. Backtest-Basis ist SPY, nicht FX -- "
    "der Mechanismus ist instrumentunabhaengig, die Kalibrierung nicht.",
    icon=":material/warning:",
)

st.markdown("### Eigener Backtest")
st.caption(
    "Code: `execution_overlay/data.py`, `execution_overlay/engine.py`, "
    "`scripts/research_execution_overlay.py`. Basisstrategie 1:1 wie oben "
    "spezifiziert (kein Vol-Targeting, feste 1-Stueck-/1-Lot-Positionsgroesse -- "
    "vereinfacht, da CAGR/Sharpe bei den hier verfuegbaren Stichprobengroessen "
    "ohnehin verrauscht sind; der direkte Baseline-vs-Overlay-Vergleich bei "
    "identischer Groesse ist aussagekraeftiger als die absolute Rendite). "
    "EUR/USD hat keinen Session-Open im SPY-Cash-Sinne (24h-Markt) -- als "
    "\"Session\" dient ein Dukascopy-Kalendertag, der duenne Sonntags-Reopen-"
    "Splitter wird vorher verworfen (gleicher Fund/Fix wie bei `gap_fade/`)."
)

st.markdown(
    "**Teil 1 -- SPY (yfinance, ~60 Tage, bewusst nur ein Schnellblick, keine "
    "gepowerte Replikation):**"
)
st.markdown(
    """
| | Baseline | Overlay |
|---|---|---|
| Trades | 34 | 32 |
| Profit Factor | 0,72 | 0,97 |
| Total P&L (1 Pip) | -2,22% | -0,20% |
| p-Wert (einseitig) | 0,76 | 0,53 |
"""
)
st.warning(
    "Richtung stimmt mit dem Paper ueberein (Overlay reduziert den Verlust "
    "deutlich) -- aber bei nur 60 Tagen sind beide Werte statistisch "
    "bedeutungslos (p >> 0,05). Weder Bestaetigung noch Widerlegung moeglich, "
    "das ist die direkte Konsequenz aus der bewusst gewaehlten yfinance-"
    "Datenquelle (siehe Adaptions-Punkt oben) -- braucht die tiefere SPY-"
    "Historie fuer ein belastbares Urteil.",
    icon=":material/hourglass_top:",
)

st.markdown(
    "**Teil 1b -- SPY auf H1 statt M5 (yfinance, 730 Tage/~2 Jahre, 343 "
    "Baseline-Trades, gut gepowert):**"
)
st.caption(
    "yfinance deckelt 5m/15m/30m alle gleich bei 60 Tagen -- nur der Sprung "
    "auf H1 (60m) bringt kostenlos wirklich mehr Historie (730 Tage). Da "
    "H1-Bars beim Ausfuehrungsraster (:00/:15/:30/:45) ohnehin immer treffen, "
    "braucht die Engine dafuer keine Aenderung -- der H1-Bar steht dann aber "
    "fuer Signal UND Ausfuehrungsraster gleichzeitig, keine feinere Sub-"
    "Aufloesung mehr darunter."
)
st.markdown(
    """
| | Baseline | Overlay |
|---|---|---|
| Trades | 343 | 238 |
| Trefferquote (1 Pip) | 52,8% | 34,9% |
| Profit Factor (1 Pip) | 1,10 | 0,89 |
| Total P&L (1 Pip) | +6,24% | -3,14% |
| Total P&L (0 Kosten, brutto) | +9,67% | -0,76% |
"""
)
st.error(
    "**Bei H1 kippt der Mechanismus von neutral/leicht hilfreich (M5) auf "
    "eindeutig schaedlich.** Die Baseline selbst ist hier zum ersten Mal in "
    "diesem Projekt ein transplantiertes Setup mit positiver Richtung (PF "
    "1,10, +6,24% netto ueber 2 Jahre) -- statistisch noch nicht signifikant "
    "(p=0,28), aber deutlich besser als jede andere Uebertragung bisher. Der "
    "Overlay macht daraus PF 0,89 mit **18 Prozentpunkten niedrigerer "
    "Trefferquote** (52,8% -> 34,9%). Mechanistisch plausibel: eine Session "
    "hat bei H1 nur ~7 Bars -- \"warte auf einen Gegen-Bar\" kostet dort eine "
    "ganze Handelsstunde von einem knappen Kontingent, bei M5 (78 Bars/"
    "Session) ist derselbe Schritt fast kostenlos. Der Overlay ist also "
    "keine aufloesungs-neutrale Verfeinerung, sondern seine Wirkung haengt "
    "direkt daran, wie klein der \"Gegenimpuls\" im Verhaeltnis zur Session "
    "ist -- ein eigener, uebertragbarer Fund unabhaengig vom Instrument.",
    icon=":material/priority_high:",
)
st.info(
    "Wichtig fuer die Einordnung: dieser H1-Test widerlegt NICHT den Paper-"
    "Mechanismus bei M5-Aufloesung (Teil 1 oben) -- er testet eine andere, "
    "grobere Konstruktion. \"Mehr kostenlose Historie\" und \"dieselbe "
    "Konstruktion testen\" schliessen sich hier gegenseitig aus.",
    icon=":material/info:",
)

st.markdown(
    "**Teil 2 -- EUR/USD (Dukascopy, 2016-2026, 1.990 Trades, gut gepowert, "
    "Paper-Konfiguration unveraendert):**"
)
st.markdown(
    """
| | Baseline | Overlay |
|---|---|---|
| Trades | 1.990 | 1.986 |
| Profit Factor | 0,89 | 0,88 |
| Total P&L (1 Pip) | -27,74% | -28,76% |
| Total P&L (0 Kosten, brutto) | -7,84% | -8,90% |
| t-Stat / p-Wert | -1,91 / 0,972 | -2,06 / 0,980 |
"""
)

st.error(
    "**Der eigentliche Befund: die Basisstrategie hat auf EUR/USD schon fuer "
    "sich genommen keine Kante -- signifikant negativ, sogar VOR Kosten "
    "(brutto -7,84%, p=0,972 fuer H1: Mittelwert>0).** Damit ist die "
    "Overlay-Frage auf FX im Grunde hinfaellig: man kann das Timing einer "
    "Strategie nicht sinnvoll verbessern, die nichts zu timen hat. Der "
    "Overlay macht es hier auf jedem Kostenniveau minimal SCHLECHTER statt "
    "besser -- das direkte Gegenteil des Paper-Befunds. Gleiches Muster wie "
    "praktisch jeder andere aus einem Paper transplantierte Ansatz in diesem "
    "Repo: die Basisstrategie selbst (ATR-Baender um den Session-Open, "
    "Wilder-Stop) ist eine SPY-spezifische Konstruktion und ueberlebt den "
    "Transfer auf FX nicht.",
    icon=":material/trending_down:",
)

st.markdown(
    "**Wenn danach nochmal gefragt wird:** der Execution-Overlay-Mechanismus "
    "selbst bleibt unbewertet auf FX -- getestet wurde nur \"Overlay ueber "
    "genau diese eine Basisstrategie\", und die Basisstrategie ist das "
    "Problem, nicht (notwendigerweise) der Overlay. Um den Overlay-Mechanismus "
    "fair zu pruefen, braucht es entweder eine bereits validierte, "
    "eigenstaendig profitable FX-Strategie als Traeger (aktuell keine im "
    "Repo verfuegbar -- ADX-VWAP, Gap-Fade und die Checklist-Strategie sind "
    "alle ebenfalls ohne Kante) oder die tiefe SPY-Historie, auf der das "
    "Original-Paper tatsaechlich beweist."
)
