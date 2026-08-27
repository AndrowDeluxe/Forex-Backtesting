"""CLS Advanced -- static findings page for strategy/cls_advanced.py.

Operationalises the user's "CLS Advanced" call notes (Smartmoneyhour/SMT
Macro Desk, 2026-07-27): a multi-window settlement-day decision tree
(Pre-Settle 06:00-07:00 -> Settle 07:00-09:00 -> Test 08:45-09:30 "does the
break hold?" -> Post-Settle/Funding 09:00-12:00, all Berlin local time),
distinct from cls_squeeze.py's single 06:00-07:00 cutoff hypothesis.

VERWORFEN (2026-08-20): kein Edge nach Kosten (PF 0.96/0.91 gepoolt ueber
alle 6 Paare, 10 Jahre) - als Baustein deshalb auf eine statische
Erkenntnis-Seite reduziert (Streamlit-Cloud-Memory-Aufraeumung). Der frueher
hier vorhandene interaktive Backtest-Tab (Pair/Modus/Datumsbereich/Spread/
Stop-Regler, je Kombination ein frischer, ungebundener Cache-Eintrag) ist
entfernt - er machte nur das bereits verworfene Ergebnis explorierbar, ohne
neue Erkenntnis. Fuer die volle interaktive Version samt Trade-Log/Entry-
Chart: `git log -- app_pages/cls_advanced.py` vor diesem Commit.

See MEMORY (fx-vwap-adx-strategy-project) for the full honest finding.
"""

import numpy as np
import pandas as pd

import streamlit as st
from strategy.cls_advanced import PAIRS, build_backtest_frame, compute_cross_confirmation, compute_daily_features
from strategy.metrics import trade_stats
from strategy.real_data import fetch_pair_history

st.set_page_config(
    page_title="CLS Strategie",
    page_icon=":material/timeline:",
    layout="wide",
)

LONG_START, LONG_END = "2016-07-28", "2026-07-28"


@st.cache_data(ttl="10m", show_spinner="Lade Dukascopy-Historie (M15)...")
def load_raw(pair: str) -> pd.DataFrame:
    # Short TTL on purpose (unlike the 6h caches below): every consumer
    # reduces this raw 10-year M15 frame (x6 pairs) to a small derived result
    # (daily features / a backtest summary row) that stays cached at 6h on
    # its own - keeping all 6 raw frames resident for 6h too just duplicates
    # memory once consumed (a Streamlit Cloud resource-limit contributor).
    return fetch_pair_history(pair, LONG_START, LONG_END)


@st.cache_data(ttl="6h", show_spinner="Klassifiziere Settlement-Tage (alle 6 Paare)...")
def load_all_daily() -> dict:
    return {pair: compute_daily_features(load_raw(pair)) for pair in PAIRS}


@st.cache_data(ttl="6h", show_spinner="Pruefe Cross-Pair-Bestaetigung...")
def load_all_confirm() -> dict:
    return compute_cross_confirmation(load_all_daily())


@st.cache_data(ttl="6h", show_spinner="Baue Klassifikations-Uebersicht (10 Jahre, alle Paare)...")
def load_classification_overview() -> pd.DataFrame:
    daily_all, confirm_all = load_all_daily(), load_all_confirm()
    rows = []
    for pair in PAIRS:
        d = daily_all[pair].copy()
        d["confirmed"] = confirm_all[pair].reindex(d.index)
        broke = d[d["direction"] != 0]
        n_confirmed = int(broke["confirmed"].sum())
        n_unconfirmed = len(broke) - n_confirmed
        rows.append(
            {
                "Pair": pair, "Tage": len(d), "Breakouts": len(broke),
                "davon confirmed": n_confirmed, "davon unconfirmed": n_unconfirmed,
                "Hold-Rate gesamt": broke["holds_0915"].mean(),
                "Hold-Rate confirmed": broke.loc[broke["confirmed"] == True, "holds_0915"].mean() if n_confirmed else np.nan,  # noqa: E712
                "Hold-Rate unconfirmed": broke.loc[broke["confirmed"] == False, "holds_0915"].mean() if n_unconfirmed else np.nan,  # noqa: E712
                "Continuation-Rate (09-12)": broke["realized_continuation"].mean(),
            }
        )
    return pd.DataFrame(rows).set_index("Pair")


@st.cache_data(ttl="6h", show_spinner="Backteste alle 6 Paare (10 Jahre)...")
def load_pooled_backtest_overview() -> pd.DataFrame:
    from strategy.backtest import BacktestConfig, simulate_trades

    daily_all, confirm_all = load_all_daily(), load_all_confirm()
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5, max_hold_bars=10, use_vwap_target=False)
    rows = []
    for mode_key, label in [("continuation", "Continuation"), ("reversal", "Reversal")]:
        all_trades = []
        for pair in PAIRS:
            signaled = build_backtest_frame(load_raw(pair), daily_all[pair], confirm_all[pair], mode=mode_key)
            trades = simulate_trades(signaled, cfg)
            if not trades.empty:
                all_trades.append(trades)
        pooled = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        stats = trade_stats(pooled)
        stats.pop("exit_reason_counts", None)
        stats["avg_return_bps"] = stats.pop("avg_return_pct") * 1e4
        rows.append({"Modell": label, **stats})
    return pd.DataFrame(rows).set_index("Modell")


st.markdown("## :material/timeline: CLS Strategie -- Strategiebestandteile")
st.caption("Quelle: \"CLS Advanced\" Call-Notizen, Smartmoneyhour / SMT Macro Desk, 27.07.2026")
st.warning(
    "**Verworfen** -- als mechanische Handelsregel kein Edge nach Kosten (siehe Befund unten). "
    "Seite dient nur noch als Erkenntnis-Referenz, kein interaktiver Backtest mehr.",
    icon=":material/block:",
)

st.markdown(
    "Die These: CLS-Settlement (Payment-versus-Payment) laeuft **07:00-09:00 Uhr** "
    "(deutsche Zeit) und ist das Fenster mit dem hoechsten Liquiditaets-/Relevanzdruck "
    "des Tages. Banken schliessen davor (**06:00-07:00**) ihre Nettopositionen, was "
    "erste, teils noch richtungslose Impulse erzeugt. Ob die Bewegung danach **haelt** "
    "(echter Flow) oder **zurueckfaellt** (nur mechanischer Fundingdruck) entscheidet "
    "sich am **08:45-09:30-Testfenster** -- kein automatischer Wendepunkt, sondern ein "
    "Qualitaetscheck."
)

st.markdown("### Die Intraday-Fenster")
windows = [
    (":material/nightlight: Asia-Range", "00:00-06:00", "Referenzbereich (High/Low). Annahme dieser Umsetzung -- in der Quelle nicht exakt definiert, aber der Zeitraum direkt vor Pre-Settle."),
    (":material/hourglass_top: Pre-Settle", "06:00-07:00", "Liquiditaetsplanung der Banken. Erste Impulse moeglich, noch keine saubere Richtung."),
    (":material/swap_horiz: Settle", "07:00-09:00", "Hoechstes CLS-Relevanzfenster. Die eigentliche Bewegung (\"Move 06:00-09:00\") entsteht hier."),
    (":material/rule: Test", "08:45-09:30", "09:15 = \"Akzeptanz?\"-Checkpoint (hier gemessen: haelt der Preis jenseits der Asia-Range?). 09:30 = Entscheidung -> Einstieg."),
    (":material/account_balance_wallet: Post-Settle / Funding", "09:00-12:00", "Restfunding, Liquiditaetsrueckfuehrung. Ziel-Exit dieser Umsetzung: 12:00 Uhr."),
]
cols = st.columns(len(windows))
for col, (title, time, desc) in zip(cols, windows):
    with col:
        with st.container(border=True, height=210):
            st.markdown(f"**{title}**")
            st.caption(time)
            st.markdown(desc)

st.markdown("### Entscheidungsbaum")
st.markdown(
    "Move 06:00-09:00 sichtbar → **Check 1/2**: bestaetigen Rates/andere Crosses die "
    "Richtung (kein isolierter Move)? → **Check 3**: haelt der Break nach 09:00 (Test "
    "um 09:15)?"
)
col_ja, col_nein = st.columns(2)
with col_ja:
    st.success(
        "**Ja -- Continuation**\n\nBreak akzeptiert, Pullback haelt, Crosses bestaetigen "
        "-> Fortsetzung in Ausbruchsrichtung suchen.",
        icon=":material/trending_up:",
    )
with col_nein:
    st.error(
        "**Nein -- Reversal**\n\nMomentum stirbt, Range wird zurueckerobert, Crosses "
        "bestaetigen nicht -> Sweep/Rueckkehr/Structure-Shift in Gegenrichtung suchen.",
        icon=":material/trending_down:",
    )

st.markdown("### Was ist umgesetzt -- und was nicht")
st.warning(
    "**Der \"Rates\"-Check (z.B. US02Y-/Zinsbewegung) ist NICHT umgesetzt** -- dafuer "
    "gibt es keine angebundene freie Intraday-Datenquelle. Nur die **Crosses-"
    "Bestaetigung** ist real gemessen: ist die 06:00-09:00-Bewegung eines Paares Teil "
    "einer breiten Dollarbewegung (die anderen 5 Majors ziehen im selben implizierten "
    "USD-Sinn), oder ein isolierter Ausreisser? Jeder \"confirmed\"-Trade unten ist also "
    "**cross-confirmed**, nicht **rates-confirmed** -- der Rates-Check bleibt ein "
    "manueller Zusatzfilter fuer den Trader.",
    icon=":material/warning:",
)
st.caption(
    "Weitere Annahme dieser Umsetzung: Asia-Range = 00:00-06:00 Berlin (nicht explizit "
    "in der Quelle definiert). Alle Fenster beziehen sich auf Europe/Berlin, konvertiert "
    "aus UTC-indizierten Dukascopy-Daten."
)

st.markdown("### Ehrlicher Befund (6 Majors, 10 Jahre Dukascopy M15, 2016-2026)")

class_df = load_classification_overview()
st.markdown("**Wann haelt der Move, wann nicht? -- Klassifikation nach Cross-Bestaetigung**")
st.dataframe(
    class_df,
    column_config={
        "Hold-Rate gesamt": st.column_config.NumberColumn(format="percent"),
        "Hold-Rate confirmed": st.column_config.NumberColumn(format="percent"),
        "Hold-Rate unconfirmed": st.column_config.NumberColumn(format="percent"),
        "Continuation-Rate (09-12)": st.column_config.NumberColumn(format="percent"),
    },
)

overview = load_pooled_backtest_overview()
st.markdown("**Beide Handelsmodelle gepoolt ueber alle 6 Paare**")
st.dataframe(
    overview,
    column_config={
        "win_rate": st.column_config.NumberColumn("Win-Rate", format="percent"),
        "profit_factor": st.column_config.NumberColumn("Profit Factor", format="%.3f"),
        "avg_return_bps": st.column_config.NumberColumn("Ø Return/Trade (bps)", format="%.2f"),
        "avg_hold_bars": st.column_config.NumberColumn("Ø Haltedauer (Bars)", format="%.1f"),
    },
)

st.info(
    "**Die Kernthese ueberlebt einen Langzeit-Check, robust in allen 6 Paaren:** Tage, "
    "an denen die Crosses den Move bestaetigen, halten konsistent oefter (ca. "
    "53-59%) als unbestaetigte Tage (ca. 40-53%) -- ein durchgaengiger, wenn auch "
    "moderater Effekt, kein Zufallsmuster mehr wie im urspruenglichen 4-Wochen-Test "
    "(dort drehte EUR/USD das Vorzeichen um, aber auf nur 2 unbestaetigten Tagen). "
    "**Als mechanische Handelsregel bringt das trotzdem keinen Edge:** ueber 4909 "
    "(Continuation) bzw. 5668 (Reversal) Trades liegt der Profit Factor bei 0.96 bzw. "
    "0.91 -- nach Round-Trip-Kosten leicht negativ, Jahr fuer Jahr ohne klaren Trend "
    "(siehe `scripts/research_cls_advanced.py` fuer die Jahres-Aufschluesselung). Der "
    "urspruengliche 4-Wochen-Test zeigte einzelne Paare mit sehr guten Kennzahlen "
    "(AUD/USD, USD/CAD) -- das loest sich in der 10-Jahres-Sicht auf und war Rauschen, "
    "kein echter Paar-Effekt.",
    icon=":material/insights:",
)
