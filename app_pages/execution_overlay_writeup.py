"""Strategie Bestandteile -- Execution-Overlay (Fast Alpha als Timing-Filter).

Reine Wissens-/Referenzseite zum Paper Zarattini & Pagani (2026),
"Improving Performance with Fast Alphas -- A Tactical Overlay for Intraday
Trend Trading", Concretum Research, QuanTips #2. Noch KEIN Backtest -- das
ist bewusst ein separater, spaeterer Schritt (siehe Info-Box unten), gleiches
Muster wie orb_writeup.py.
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

st.markdown("### Was das fuer unser Projekt bedeuten koennte")
st.markdown(
    "Als Timing-Layer denkbar ueber jede bereits unabhaengig getestete Trend-/"
    "Breakout-Komponente in diesem Repo (z. B. `strategy/adx_vwap.py`'s Refined-"
    "Konfiguration, `auction_playbook/`, `asian_range_breakout/`) -- veraendert "
    "explizit NICHT das Signal, nur den Ausfuehrungszeitpunkt, und ist damit ein "
    "risikoarmer Zusatz statt eines Ersatzes fuer eine bestehende Strategie. "
    "Noch nicht gegen irgendeine dieser Komponenten getestet."
)

st.info(
    "**Naechster Schritt:** noch kein Backtest -- das ist bewusst ein separater, "
    "spaeterer Schritt. Diese Seite haelt nur die Erkenntnisse aus dem Paper fest.",
    icon=":material/hourglass_empty:",
)
