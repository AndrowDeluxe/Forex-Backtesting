"""ORB (Opening Range Breakout) -- interactive dashboard for orb_strategy/.

See app_pages/orb_writeup.py for the source paper (Holmberg, Loennbark &
Lundstroem, 2013) and MEMORY (fx-vwap-adx-strategy-project) for the full
honest finding history: baseline (long+short) is flat-to-noise everywhere;
long-only + ADX>=25 at entry turns into a real, OOS-surviving edge
specifically on Nasdaq and SP500 (not on EUR/USD/Oil/Gold) - a
trend-continuation effect on US equity indices, not a universal
breakout edge.
"""

import altair as alt
import pandas as pd

import streamlit as st
from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import breakeven_spread_bps, equity_curve, summarize
from strategy.real_data import fetch_pair_history

st.set_page_config(page_title="ORB Strategie", page_icon=":material/bolt:", layout="wide")

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"
ASSETS = ["NASDAQ", "SP500", "EURUSD", "GOLD", "OIL"]
CONFIRMED_ASSETS = {"NASDAQ", "SP500"}


@st.cache_data(ttl="1h", show_spinner="Lade Historie (M15)...")
def load_raw(asset: str) -> pd.DataFrame:
    if asset == "EURUSD":
        return fetch_pair_history("EURUSD", START, END)
    df = fetch_timeframe(asset, "M15", START, END)
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


@st.cache_data(ttl="1h", show_spinner="Berechne ORB-Schwellen & Signale...")
def load_signaled(asset: str, atr_mult: float, long_only: bool, adx_min: float | None) -> pd.DataFrame:
    df = load_raw(asset)
    return run_orb_pipeline(df, atr_n=14, atr_mult=atr_mult, long_only=long_only, adx_min=adx_min)


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_trades(asset: str, atr_mult: float, long_only: bool, adx_min: float | None, spread_bps: float, stop_atr_mult: float) -> pd.DataFrame:
    signaled = load_signaled(asset, atr_mult, long_only, adx_min)
    cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=stop_atr_mult, use_vwap_target=False)
    return simulate_trades(signaled, cfg)


@st.cache_data(ttl="1h", show_spinner="Berechne Breakeven-Spread...")
def load_breakeven_spread(asset: str, atr_mult: float, long_only: bool, adx_min: float | None, stop_atr_mult: float) -> float:
    signaled = load_signaled(asset, atr_mult, long_only, adx_min)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=stop_atr_mult, use_vwap_target=False)
    return breakeven_spread_bps(signaled, cfg, lo=0.0, hi=30.0)


with st.sidebar:
    st.markdown("### Konfiguration")
    asset = st.selectbox("Asset", ASSETS, help="Nasdaq/SP500: bestaetigter Effekt. EUR/USD/Gold/Oel: Filter bringt hier nichts (siehe Warnbox).")
    long_only = st.checkbox("Nur Long", value=True)
    use_adx_filter = st.checkbox("ADX-Filter (>=25 bei Entry)", value=True)
    adx_min = 25.0 if use_adx_filter else None
    atr_mult = st.slider("Schwellen-Distanz (x Vortages-ATR)", 0.25, 3.0, 1.0, 0.25)
    stop_atr_mult = st.slider("Stop-Distanz (x M15-ATR)", 0.5, 5.0, 2.0, 0.5)
    spread_bps = st.slider("Round-trip Spread (bps)", 0.0, 5.0, 0.3, 0.1)
    st.caption(
        "Datenquelle: echte Dukascopy-Historie (M15), 2016-2026, auf Festplatte gecacht. "
        "Schwelle = Tages-Open +/- atr_mult x Vortages-ATR(14); Stop sitzt "
        "stop_atr_mult x M15-ATR(14) jenseits der durchbrochenen Schwelle; Exit "
        "sonst am Tagesschluss (session_end)."
    )

if asset in CONFIRMED_ASSETS:
    st.success(
        f"**{asset}: bestaetigter Effekt (mit Einschraenkungen).** Long-only + ADX>=25 "
        "zeigt einen Out-of-Sample-ueberlebenden Edge -- aber schwaecher als im "
        "ersten Blick auf 2016-2021 allein. Details unten (In-Sample/Out-of-Sample-Tab).",
        icon=":material/check_circle:",
    )
else:
    st.warning(
        f"**{asset}: der Long-only/ADX-Filter bringt hier nichts.** Der Effekt wurde "
        "auf Nasdaq gefunden und ist spezifisch fuer US-Aktienindizes (Nasdaq, SP500) "
        "-- auf EUR/USD, Gold und Oel bleibt das Ergebnis flach oder wird durch den "
        "Filter sogar leicht schlechter. Zur Vergleich/Transparenz trotzdem waehlbar.",
        icon=":material/warning:",
    )

st.warning(
    "**Wichtige Einschraenkungen, unabhaengig vom Asset:** (1) Der Stop greift praktisch "
    "nie (<1% der Trades) -- die Strategie haelt de facto bis Tagesschluss durch, keine "
    "echte Intraday-Risikokontrolle. (2) Nasdaq 2025 ist ein Ausreisser-Jahr (Profit "
    "Factor 11 auf nur 27 Trades) und zieht den Durchschnitt nach oben. (3) Der "
    "Long-only/ADX-Filter wurde am selben Datensatz entdeckt, auf dem er hier gezeigt "
    "wird -- die Out-of-Sample-Haelfte (ab 2021) ist der ehrlichere Massstab. "
    "(4) Breakeven-Spread-Rechnung unten beruecksichtigt nur den Spread, keine "
    "Slippage -- bei einem echten Breakout-Fill ist Slippage realistisch.",
    icon=":material/report:",
)

trades = load_trades(asset, atr_mult, long_only, adx_min, spread_bps, stop_atr_mult)
signaled = load_signaled(asset, atr_mult, long_only, adx_min)
summary = summarize(trades, signaled.index)

st.markdown(f"## :material/bolt: {asset} -- ORB ({'Long-only' if long_only else 'Long+Short'}{' + ADX>=25' if use_adx_filter else ''})")

with st.container(horizontal=True):
    st.metric("Sharpe (ann.)", f"{summary['sharpe']:.2f}", border=True)
    st.metric("Profit Factor", f"{summary['profit_factor']:.2f}" if summary["n_trades"] else "-", border=True)
    st.metric("Max Drawdown", f"{summary['max_drawdown']:.2%}", border=True)
    st.metric("Win Rate", f"{summary['win_rate']:.1%}" if summary["n_trades"] else "-", border=True)
    st.metric("Trades", summary["n_trades"], border=True)
    avg_bps = summary["avg_return_pct"] * 1e4 if pd.notna(summary["avg_return_pct"]) else float("nan")
    st.metric("Ø Return/Trade", f"{avg_bps:.2f} bps", border=True)

if 0 < summary["n_trades"] < 100:
    st.info(f"Nur {summary['n_trades']} Trades bei dieser Konfiguration -- Kennzahlen sind bei so kleiner Stichprobe kaum von Zufall zu unterscheiden.", icon=":material/info:")

st.space("medium")

tab_overview, tab_robustness = st.tabs(["Uebersicht", "Robustheit (Jahre / IS-OOS / Kosten)"])

with tab_overview:
    col1, col2 = st.columns([2, 1])
    with col1:
        with st.container(border=True):
            st.markdown("**Equity-Kurve (verkettete Tagesrenditen)**")
            if summary["n_trades"] > 0:
                daily = trades.groupby(trades["exit_time"].dt.floor("D"))["return_pct"].apply(lambda r: (1 + r).prod() - 1)
                days = pd.date_range(signaled.index.min().normalize(), signaled.index.max().normalize(), freq="D")
                daily = daily.reindex(days, fill_value=0.0)
                curve = equity_curve(daily).rename("equity")
                curve.index.name = "date"
                curve = curve.reset_index()
                st.altair_chart(
                    alt.Chart(curve).mark_line(color="#4c78a8").encode(
                        x=alt.X("date:T", title="Datum"),
                        y=alt.Y("equity:Q", title="Equity (Start = 1.0)", scale=alt.Scale(zero=False)),
                        tooltip=["date:T", alt.Tooltip("equity:Q", format=".4f")],
                    ).properties(height=340)
                )
            else:
                st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")
    with col2:
        with st.container(border=True):
            st.markdown("**Exit-Gruende**")
            if summary["n_trades"] > 0 and summary.get("exit_reason_counts"):
                reason_df = pd.Series(summary["exit_reason_counts"]).rename("count")
                reason_df.index.name = "reason"
                reason_df = reason_df.reset_index()
                st.altair_chart(
                    alt.Chart(reason_df).mark_arc().encode(
                        theta="count:Q", color=alt.Color("reason:N", title="Exit-Grund"), tooltip=["reason", "count"]
                    ).properties(height=340)
                )
            else:
                st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Preis, ORB-Schwellen & Einstiege (letzte Tage)**")
        n_days = st.slider("Anzahl Tage", 1, 30, 5, key=f"days_{asset}")
        last_days = pd.Series(signaled.index.date).drop_duplicates().tail(n_days)
        window = signaled[pd.Series(signaled.index.date, index=signaled.index).isin(last_days)].reset_index(names="time")

        base = alt.Chart(window)
        price_lines = (
            base.transform_fold(["close", "orb_upper", "orb_lower"], as_=["series", "value"])
            .mark_line()
            .encode(
                x=alt.X("time:T", title="Zeit"),
                y=alt.Y("value:Q", title="Preis", scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "series:N", title="Serie",
                    scale=alt.Scale(domain=["close", "orb_upper", "orb_lower"], range=["#333333", "#e45756", "#54a24b"]),
                ),
                strokeDash=alt.condition(
                    alt.FieldOneOfPredicate(field="series", oneOf=["orb_upper", "orb_lower"]),
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
                alt.Chart(marker_df).mark_point(size=120, filled=True).encode(
                    x=alt.X("entry_time:T"), y=alt.Y("entry_price:Q"),
                    shape=alt.Shape("label:N", scale=alt.Scale(domain=["Long-Einstieg", "Short-Einstieg"], range=["triangle-up", "triangle-down"])),
                    color=alt.Color("label:N", scale=alt.Scale(domain=["Long-Einstieg", "Short-Einstieg"], range=["#54a24b", "#e45756"]), legend=alt.Legend(title="Trades")),
                    tooltip=["entry_time:T", "label", alt.Tooltip("entry_price:Q", format=".4f"), "exit_reason"],
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
                    "entry_price": st.column_config.NumberColumn("Entry-Preis", format="%.4f"),
                    "exit_price": st.column_config.NumberColumn("Exit-Preis", format="%.4f"),
                    "return_bps": st.column_config.NumberColumn("Return (bps)", format="%.2f"),
                    "exit_reason": st.column_config.TextColumn("Exit-Grund"),
                    "hold_bars": st.column_config.NumberColumn("Haltedauer (Bars)"),
                    "adx_at_entry": st.column_config.NumberColumn("ADX @ Entry", format="%.1f"),
                    "atr_at_entry": st.column_config.NumberColumn("ATR @ Entry", format="%.4f"),
                },
            )
        else:
            st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

with tab_robustness:
    st.markdown("### Jahres-Walk-Forward")
    if not trades.empty:
        rows = []
        for year in range(2017, 2027):
            yr_df = signaled[signaled.index.year == year]
            if yr_df.empty:
                continue
            yr_trades = trades[trades["entry_time"].dt.year == year]
            if yr_trades.empty:
                rows.append({"Jahr": year, "Trades": 0})
                continue
            s = summarize(yr_trades, yr_df.index)
            rows.append({
                "Jahr": year, "Trades": s["n_trades"], "Win-Rate": s["win_rate"],
                "Ø Return (bps)": s["avg_return_pct"] * 1e4, "Sharpe": s["sharpe"], "Profit Factor": s["profit_factor"],
            })
        yearly = pd.DataFrame(rows).set_index("Jahr")
        st.dataframe(
            yearly,
            column_config={
                "Win-Rate": st.column_config.NumberColumn(format="percent"),
                "Ø Return (bps)": st.column_config.NumberColumn(format="%.2f"),
                "Sharpe": st.column_config.NumberColumn(format="%.2f"),
                "Profit Factor": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        active = yearly[yearly["Trades"] > 0]
        if not active.empty:
            st.caption(
                f"Mittlerer Jahres-Sharpe: {active['Sharpe'].mean():.2f} -- "
                f"{(active['Ø Return (bps)'] > 0).sum()}/{len(active)} Jahre im Schnitt positiv."
            )
    else:
        st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

    st.space("medium")

    st.markdown("### In-Sample (2016-2021) vs. Out-of-Sample (2021-2026)")
    st.caption(
        "Der Long-only/ADX-Filter wurde durch Betrachtung von Nasdaq-Daten aus genau "
        "diesem Zeitraum gefunden -- die Out-of-Sample-Haelfte ist deshalb der "
        "ehrlichere Massstab, nicht die In-Sample-Haelfte."
    )
    if not trades.empty:
        split_ts = pd.Timestamp(SPLIT_DATE, tz=signaled.index.tz)
        is_signaled, oos_signaled = signaled[signaled.index < split_ts], signaled[signaled.index >= split_ts]
        is_trades, oos_trades = trades[trades["entry_time"] < split_ts], trades[trades["entry_time"] >= split_ts]
        is_s, oos_s = summarize(is_trades, is_signaled.index), summarize(oos_trades, oos_signaled.index)
        iso_df = pd.DataFrame(
            [
                {"Zeitraum": "In-Sample (2016-2021)", "Trades": is_s["n_trades"], "Sharpe": is_s["sharpe"], "Profit Factor": is_s["profit_factor"], "Win-Rate": is_s["win_rate"], "Max DD": is_s["max_drawdown"]},
                {"Zeitraum": "Out-of-Sample (2021-2026)", "Trades": oos_s["n_trades"], "Sharpe": oos_s["sharpe"], "Profit Factor": oos_s["profit_factor"], "Win-Rate": oos_s["win_rate"], "Max DD": oos_s["max_drawdown"]},
            ]
        ).set_index("Zeitraum")
        st.dataframe(
            iso_df,
            column_config={
                "Sharpe": st.column_config.NumberColumn(format="%.2f"),
                "Profit Factor": st.column_config.NumberColumn(format="%.2f"),
                "Win-Rate": st.column_config.NumberColumn(format="percent"),
                "Max DD": st.column_config.NumberColumn(format="percent"),
            },
        )
    else:
        st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

    st.space("medium")

    st.markdown("### Kosten-Sensitivitaet")
    be_spread = load_breakeven_spread(asset, atr_mult, long_only, adx_min, stop_atr_mult)
    st.metric("Breakeven Round-trip-Spread", f"{be_spread:.2f} bps", help="Ab diesem Spread (nur Spread, keine Slippage) wird der Ø-Trade-Return null.")
    st.caption(
        f"Aktuell modelliert: {spread_bps} bps. Solange der reale Round-trip-Spread "
        f"(Spread + Slippage) darunter bleibt, hat die Strategie rechnerisch noch Luft "
        "-- bei einem echten Breakout-Fill ist aber Slippage realistisch, die hier "
        "nicht mit eingerechnet ist."
    )
