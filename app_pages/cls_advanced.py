"""CLS Advanced -- interactive dashboard for strategy/cls_advanced.py.

Operationalises the user's "CLS Advanced" call notes (Smartmoneyhour/SMT
Macro Desk, 2026-07-27): a multi-window settlement-day decision tree
(Pre-Settle 06:00-07:00 -> Settle 07:00-09:00 -> Test 08:45-09:30 "does the
break hold?" -> Post-Settle/Funding 09:00-12:00, all Berlin local time),
distinct from cls_squeeze.py's single 06:00-07:00 cutoff hypothesis.

See MEMORY (fx-vwap-adx-strategy-project) for the full honest finding.
"""

import altair as alt
import numpy as np
import pandas as pd

import streamlit as st
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.cls_advanced import PAIRS, build_backtest_frame, compute_cross_confirmation, compute_daily_features
from strategy.metrics import equity_curve, trade_stats
from strategy.real_data import fetch_pair_history

st.set_page_config(
    page_title="CLS Advanced",
    page_icon=":material/timeline:",
    layout="wide",
)

LONG_START, LONG_END = "2016-07-28", "2026-07-28"
MODE_CONTINUATION = "Continuation (Break haelt + Crosses bestaetigen)"
MODE_REVERSAL = "Reversal (Break haelt nicht -> Fade)"


@st.cache_data(ttl="1h", show_spinner="Lade Dukascopy-Historie (M15)...")
def load_raw(pair: str) -> pd.DataFrame:
    return fetch_pair_history(pair, LONG_START, LONG_END)


@st.cache_data(ttl="1h", show_spinner="Klassifiziere Settlement-Tage (alle 6 Paare)...")
def load_all_daily() -> dict:
    return {pair: compute_daily_features(load_raw(pair)) for pair in PAIRS}


@st.cache_data(ttl="1h", show_spinner="Pruefe Cross-Pair-Bestaetigung...")
def load_all_confirm() -> dict:
    return compute_cross_confirmation(load_all_daily())


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_trades(pair: str, mode: str, spread_bps: float, stop_atr_mult: float) -> pd.DataFrame:
    mode_key = "continuation" if mode == MODE_CONTINUATION else "reversal"
    daily_all, confirm_all = load_all_daily(), load_all_confirm()
    signaled = build_backtest_frame(load_raw(pair), daily_all[pair], confirm_all[pair], mode=mode_key)
    cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=stop_atr_mult, max_hold_bars=10, use_vwap_target=False)
    return simulate_trades(signaled, cfg)


@st.cache_data(ttl="1h", show_spinner="Baue Klassifikations-Uebersicht (10 Jahre, alle Paare)...")
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


@st.cache_data(ttl="1h", show_spinner="Backteste alle 6 Paare (10 Jahre)...")
def load_pooled_backtest_overview() -> pd.DataFrame:
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


with st.sidebar:
    st.markdown("### Konfiguration (Tab \"Backtest\")")
    pair = st.selectbox("Pair", PAIRS)
    mode = st.radio("Modell", [MODE_CONTINUATION, MODE_REVERSAL])
    date_range = st.date_input(
        "Zeitraum",
        value=(pd.Timestamp(LONG_END) - pd.Timedelta(days=365), pd.Timestamp(LONG_END)),
        min_value=pd.Timestamp(LONG_START), max_value=pd.Timestamp(LONG_END),
        help="Filtert die auf 10 Jahren berechneten Trades auf diesen Ausschnitt. Fuer den "
        "urspruenglichen 4-Wochen-Test: Start auf 2026-07-01 setzen.",
    )
    spread_bps = st.slider("Round-trip Spread (bps)", 0.0, 3.0, 0.3, 0.1)
    stop_atr_mult = st.slider("Stop-Distanz (x ATR, ueber/unter Asia-Range)", 0.1, 2.0, 0.5, 0.1)
    st.caption(
        "Datenquelle: echte Dukascopy-Historie (M15), 2016-2026, auf Festplatte gecacht. "
        "Alle Uhrzeiten in Europe/Berlin (deutsche Zeit, wie in der Quelle)."
    )

tab_components, tab_backtest = st.tabs(["Strategiebestandteile", "Backtest"])

# =============================================================================
# Tab: Strategiebestandteile
# =============================================================================
with tab_components:
    st.markdown("## :material/timeline: CLS Advanced -- Strategiebestandteile")
    st.caption("Quelle: \"CLS Advanced\" Call-Notizen, Smartmoneyhour / SMT Macro Desk, 27.07.2026")

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

# =============================================================================
# Tab: Backtest
# =============================================================================
with tab_backtest:
    st.markdown(f"## :material/timeline: {pair} — {mode}")

    trades_full = load_trades(pair, mode, spread_bps, stop_atr_mult)
    start_ts, end_ts = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
    trades = (
        trades_full[(trades_full["entry_time"] >= start_ts.tz_localize("UTC")) & (trades_full["entry_time"] < end_ts.tz_localize("UTC"))]
        if not trades_full.empty else trades_full
    )
    stats = trade_stats(trades)

    with st.container(horizontal=True):
        st.metric("Trades", stats["n_trades"], border=True)
        st.metric("Win-Rate", f"{stats['win_rate']:.1%}" if stats["n_trades"] else "–", border=True)
        st.metric("Profit Factor", f"{stats['profit_factor']:.3f}" if stats["n_trades"] else "–", border=True)
        avg_bps = stats["avg_return_pct"] * 1e4 if stats["n_trades"] and pd.notna(stats["avg_return_pct"]) else float("nan")
        st.metric("Ø Return/Trade", f"{avg_bps:.2f} bps" if stats["n_trades"] else "–", border=True)
        st.metric("Ø Haltedauer", f"{stats['avg_hold_bars']:.1f} Bars" if stats["n_trades"] else "–", border=True)

    st.space("medium")

    col1, col2 = st.columns([2, 1])
    with col1:
        with st.container(border=True):
            st.markdown("**Equity-Kurve (verkettete Tagesrenditen, gewaehlter Zeitraum)**")
            if stats["n_trades"] > 0:
                raw = load_raw(pair)
                sub_index = raw[(raw.index >= start_ts.tz_localize("UTC")) & (raw.index < end_ts.tz_localize("UTC"))].index
                daily = trades_to_daily_returns(trades, sub_index)
                curve = equity_curve(daily).rename("equity").reset_index(names="date")
                chart = (
                    alt.Chart(curve)
                    .mark_line(color="#4c78a8")
                    .encode(
                        x=alt.X("date:T", title="Datum"),
                        y=alt.Y("equity:Q", title="Equity (Start = 1.0)", scale=alt.Scale(zero=False)),
                        tooltip=["date:T", alt.Tooltip("equity:Q", format=".4f")],
                    )
                    .properties(height=340)
                )
                st.altair_chart(chart)
            else:
                st.info("Keine Trades in diesem Zeitraum/dieser Konfiguration.", icon=":material/info:")

    with col2:
        with st.container(border=True):
            st.markdown("**Exit-Gruende**")
            if stats["n_trades"] > 0 and stats.get("exit_reason_counts"):
                reason_df = pd.Series(stats["exit_reason_counts"]).rename("count").reset_index(names="reason")
                st.altair_chart(
                    alt.Chart(reason_df)
                    .mark_arc()
                    .encode(theta="count:Q", color=alt.Color("reason:N", title="Exit-Grund"), tooltip=["reason", "count"])
                    .properties(height=340)
                )
            else:
                st.info("Keine Trades in diesem Zeitraum/dieser Konfiguration.", icon=":material/info:")

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Preis, Asia-Range (06:00 Berlin) & Einstiege (letzte Tage im gewaehlten Zeitraum)**")
        n_days = st.slider("Anzahl Tage", 1, 20, 5, key=f"days_{pair}_{mode}")
        mode_key = "continuation" if mode == MODE_CONTINUATION else "reversal"
        signaled = build_backtest_frame(load_raw(pair), load_all_daily()[pair], load_all_confirm()[pair], mode=mode_key)
        signaled_in_range = signaled[(signaled.index >= start_ts.tz_localize("UTC")) & (signaled.index < end_ts.tz_localize("UTC"))]
        last_days = pd.Series(signaled_in_range.index.date).drop_duplicates().tail(n_days)
        window = signaled_in_range[pd.Series(signaled_in_range.index.date, index=signaled_in_range.index).isin(last_days)].reset_index(names="time")

        if window.empty:
            st.info("Keine Daten in diesem Zeitraum.", icon=":material/info:")
        else:
            base = alt.Chart(window)
            price_lines = (
                base.transform_fold(["close", "prev_high", "prev_low"], as_=["series", "value"])
                .mark_line()
                .encode(
                    x=alt.X("time:T", title="Zeit"),
                    y=alt.Y("value:Q", title="Preis", scale=alt.Scale(zero=False)),
                    color=alt.Color(
                        "series:N", title="Serie",
                        scale=alt.Scale(
                            domain=["close", "prev_high", "prev_low"],
                            range=["#333333", "#e45756", "#54a24b"],
                        ),
                    ),
                    strokeDash=alt.condition(
                        alt.FieldOneOfPredicate(field="series", oneOf=["prev_high", "prev_low"]),
                        alt.value([4, 3]), alt.value([1, 0]),
                    ),
                )
            )
            window_trades = (
                trades[(trades["entry_time"] >= window["time"].min()) & (trades["entry_time"] <= window["time"].max())]
                if not trades.empty else trades
            )
            layers = [price_lines]
            if not window_trades.empty:
                marker_df = window_trades.copy()
                marker_df["label"] = marker_df["direction"].map({1: "Long-Einstieg", -1: "Short-Einstieg"})
                layers.append(
                    alt.Chart(marker_df)
                    .mark_point(size=120, filled=True)
                    .encode(
                        x=alt.X("entry_time:T"),
                        y=alt.Y("entry_price:Q"),
                        shape=alt.Shape(
                            "label:N",
                            scale=alt.Scale(domain=["Long-Einstieg", "Short-Einstieg"], range=["triangle-up", "triangle-down"]),
                        ),
                        color=alt.Color(
                            "label:N",
                            scale=alt.Scale(domain=["Long-Einstieg", "Short-Einstieg"], range=["#54a24b", "#e45756"]),
                            legend=alt.Legend(title="Trades"),
                        ),
                        tooltip=["entry_time:T", "label", alt.Tooltip("entry_price:Q", format=".5f"), "exit_reason"],
                    )
                )
            st.altair_chart(alt.layer(*layers).properties(height=380).resolve_scale(color="independent"))

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Trade-Log**")
        if not trades.empty:
            display_trades = trades.copy()
            display_trades["direction"] = display_trades["direction"].map({1: "Long", -1: "Short"})
            display_trades["return_bps"] = display_trades["return_pct"] * 1e4
            st.dataframe(
                display_trades.sort_values("entry_time", ascending=False).drop(columns=["return_pct"]),
                hide_index=True,
                column_config={
                    "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD HH:mm"),
                    "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD HH:mm"),
                    "direction": st.column_config.TextColumn("Richtung"),
                    "entry_price": st.column_config.NumberColumn("Entry-Preis", format="%.5f"),
                    "exit_price": st.column_config.NumberColumn("Exit-Preis", format="%.5f"),
                    "return_bps": st.column_config.NumberColumn("Return (bps)", format="%.2f"),
                    "exit_reason": st.column_config.TextColumn("Exit-Grund"),
                    "hold_bars": st.column_config.NumberColumn("Haltedauer (Bars)"),
                    "adx_at_entry": st.column_config.NumberColumn("ADX @ Entry", format="%.1f"),
                    "atr_at_entry": st.column_config.NumberColumn("ATR @ Entry", format="%.5f"),
                },
            )
        else:
            st.info("Keine Trades in diesem Zeitraum/dieser Konfiguration.", icon=":material/info:")
