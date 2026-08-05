"""Backtest -- OU-Modell Paper-Replikation: Jashnani, "Analysis of the Bollinger
bands and Ornstein-Uhlenbeck Model Mean Reversion Trading Strategy" (siehe
ou_paper_backtest/ im Repo-Root für den vollen Code).

Reproduziert die Paper-Methodik (OU-Parameter per rollierender OLS-Regression auf
Log-Preisen, 60/120/252-Tage-Fenster; In-Sample-Selektion 2010-2017; Bollinger-Band
Out-of-Sample-Backtest 2018-2024) auf zwei Universen:
- S&P 500 (Zufalls-Sample, 90 Ticker -- das Paper selbst nutzte 424/503)
- Nasdaq-100 (alle ~103 aktuellen Konstituenten)

Alles hier wird NUR aus vorab lokal berechneten CSVs unter ou_paper_backtest/results/
gelesen (kein Live-yfinance-Call aus Streamlit Cloud heraus -- gleiches Muster wie die
OU-Modell Live-Logs-Seite: die schwere Berechnung (OU-Schaetzung ueber tausende Tage x
100+ Ticker) laeuft lokal, siehe ou_paper_backtest/run.py, und wird committed).

Zusaetzlich zum Paper-eigenen %-Vergleich zeigt diese Seite eine $100k-Konto-
Equity-Kurve mit Risk-basiertem Positions-Sizing (1% Equity-Risiko/Trade, 15%
Gesamt-Risiko-Cap) -- das Paper selbst spezifiziert kein Sizing/Kapital, das ist
eine explizite eigene Annahme, angelehnt an das Risk-Management-Muster des
tatsaechlich live laufenden OU-Modell-Bots (OU-Modell-MT5-Bridge)."""

from pathlib import Path

import altair as alt
import pandas as pd

import streamlit as st

st.set_page_config(page_title="OU-Modell -- Paper-Backtest", page_icon=":material/science:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_DIR / "ou_paper_backtest" / "results"

UNIVERSES = {
    "sp500": {"label": "S&P 500 (Sample, 90 Ticker)", "bench_label": "S&P 500"},
    "nasdaq100": {"label": "Nasdaq-100 (alle ~103 Ticker)", "bench_label": "Nasdaq-100"},
}


@st.cache_data(ttl="1h")
def load_universe_results(universe_key: str) -> dict | None:
    d = RESULTS_DIR / universe_key
    if not (d / "equity_curve_100k.csv").exists():
        return None
    equity = pd.read_csv(d / "equity_curve_100k.csv", index_col=0, parse_dates=True)
    perf_100k = pd.read_csv(d / "performance_summary_100k.csv", index_col=0)
    perf_pct = pd.read_csv(d / "performance_summary.csv", index_col=0)
    ou_params = pd.read_csv(d / "ou_parameters_in_sample.csv", index_col=0)
    trades_full = pd.read_csv(d / "trades_100k_BBfull.csv", parse_dates=["entry_date", "exit_date"])
    trades_ou = pd.read_csv(d / "trades_100k_BBOU.csv", parse_dates=["entry_date", "exit_date"])
    return {
        "equity": equity, "perf_100k": perf_100k, "perf_pct": perf_pct,
        "ou_params": ou_params, "trades_full": trades_full, "trades_ou": trades_ou,
    }


st.markdown("## :material/science: OU-Modell -- Paper-Backtest (Bollinger Bands + Ornstein-Uhlenbeck)")

st.info(
    "Nachbau von Jashnani, *\"Analysis of the Bollinger bands and Ornstein-Uhlenbeck "
    "Model Mean Reversion Trading Strategy in S&P 500 Equities\"*: OU-Parameter "
    "(Reversionsgeschwindigkeit theta, Half-Life, p-Wert) werden In-Sample "
    "(2010-2017) je Ticker per rollierender OLS-Regression auf Log-Preisen (60/120/252 "
    "Handelstage) geschaetzt; Ticker mit theta > 0.03, p < 0.2 und Half-Life in [5, 200] "
    "Tagen bilden das \"OU-gefilterte\" Universum. Beide Varianten -- volles Universum "
    "(**BBfull**) und OU-gefiltert (**BBOU**) -- werden dann Out-of-Sample (2018-2024) "
    "mit derselben Bollinger-Band-Strategie (n=20, k=2, 2-Sigma-Stop, max. 10 "
    "Handelstage Haltedauer) gehandelt.",
    icon=":material/info:",
)
st.warning(
    "**Eigene Annahmen, da vom Paper nicht spezifiziert:** (1) reduziertes Sample "
    "statt des vollen Universums (S&P: 90 statt 424/503 Ticker; Nasdaq-100: alle "
    "~103 aktuellen Konstituenten statt einer historischen Zusammensetzung) -- "
    "Ergebnisse sind daher **nicht** direkt mit den im Paper berichteten Zahlen "
    "vergleichbar, nur die qualitative Aussage (OU-Filter verbessert die Bollinger-"
    "Strategie) wird getestet. (2) Positions-Sizing/Kapitalbindung fehlt im Paper "
    "komplett -- die $100k-Kurve unten nutzt Risk-basiertes Sizing (1% Equity-Risiko "
    "je Trade am 2-Sigma-Stop, 15% Gesamt-Risiko-Cap ueber alle offenen Positionen), "
    "analog zum Risk-Management-Muster des echten OU-Modell-Live-Bots auf diesem "
    "System. (3) Alle Ergebnisse **vor Transaktionskosten** (wie im Paper selbst).",
    icon=":material/warning:",
)

universe_key = st.selectbox(
    "Universum", list(UNIVERSES.keys()), format_func=lambda k: UNIVERSES[k]["label"]
)
data = load_universe_results(universe_key)

if data is None:
    st.error(
        f"Noch keine Ergebnisse fuer '{UNIVERSES[universe_key]['label']}' committed. "
        f"Lokal `python ou_paper_backtest/run.py {universe_key}` ausfuehren und "
        f"`ou_paper_backtest/results/{universe_key}/` committen.",
        icon=":material/error:",
    )
    st.stop()

bench_label = UNIVERSES[universe_key]["bench_label"]
equity = data["equity"]
perf_100k = data["perf_100k"]

with st.container(horizontal=True):
    st.metric("BBOU: Endkapital", f"${perf_100k.loc['BBOU', 'final_equity']:,.0f}", border=True)
    st.metric("BBOU: Sharpe", f"{perf_100k.loc['BBOU', 'sharpe']:.2f}", border=True)
    st.metric("BBOU: Max Drawdown", f"{perf_100k.loc['BBOU', 'max_drawdown_pct']:.1f}%", border=True)
    st.metric("BBOU: Trades", f"{int(perf_100k.loc['BBOU', 'n_trades'])}", border=True)
    st.metric("BBOU: Trefferquote", f"{perf_100k.loc['BBOU', 'win_rate_pct']:.1f}%", border=True)
    st.metric(f"{bench_label}: Endkapital", f"${perf_100k.loc[bench_label, 'final_equity']:,.0f}", border=True)

st.space("medium")

tab_equity, tab_metrics, tab_ou, tab_trades = st.tabs(
    [":material/show_chart: $100k Equity-Kurve", ":material/query_stats: Kennzahlen",
     ":material/functions: OU-Parameter", ":material/list_alt: Trade-Log"]
)

with tab_equity:
    with st.container(border=True):
        curve = equity.reset_index(names="date").melt("date", var_name="Strategie", value_name="Equity")
        chart = (
            alt.Chart(curve)
            .mark_line()
            .encode(
                x=alt.X("date:T", title="Datum"),
                y=alt.Y("Equity:Q", title="Kontostand ($)", scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "Strategie:N",
                    scale=alt.Scale(domain=["BBfull", "BBOU", bench_label],
                                     range=["#4c78a8", "#e45756", "#f58518"]),
                ),
                tooltip=["date:T", "Strategie:N", alt.Tooltip("Equity:Q", format=",.0f")],
            )
            .properties(height=460)
        )
        st.altair_chart(chart)
        st.caption(
            "Start: $100.000 (2018-01-01). BBfull/BBOU: Equity aendert sich nur an "
            "Tagen mit offenen Positionen (mark-to-market); ohne offene Position "
            "bleibt das Kapital unveraendert (kein Cash-Ertrag modelliert)."
        )

with tab_metrics:
    with st.container(border=True):
        st.markdown("#### $100k-Konto (Risk-basiertes Sizing)")
        st.dataframe(perf_100k.round(2))
    with st.container(border=True):
        st.markdown("#### %-Return-Portfolio (paper-naeher: Equal-Weight ueber aktive Positionen)")
        st.dataframe(data["perf_pct"].round(3))

with tab_ou:
    with st.container(border=True):
        ou_params = data["ou_params"]
        st.dataframe(
            ou_params.sort_values("theta", ascending=False).round(4),
            column_config={
                "theta": st.column_config.NumberColumn("theta (Reversionsgeschw.)"),
                "half_life": st.column_config.NumberColumn("Half-Life (Tage)", format="%.1f"),
                "p_value": st.column_config.NumberColumn("p-Wert"),
            },
        )
        n_selected = ((ou_params["theta"] > 0.03) & (ou_params["p_value"] < 0.2)
                      & (ou_params["half_life"].between(5, 200))).sum()
        st.caption(
            f"{n_selected} von {len(ou_params)} Tickern erfuellen die OU-Selektionskriterien "
            f"(theta > 0.03, p < 0.2, Half-Life in [5, 200] Tagen) -> bilden das BBOU-Universum."
        )

with tab_trades:
    variant = st.radio("Trades von", ["BBOU", "BBfull"], horizontal=True)
    trades = data["trades_ou"] if variant == "BBOU" else data["trades_full"]
    with st.container(border=True):
        if not trades.empty:
            st.dataframe(
                trades.sort_values("exit_date", ascending=False),
                hide_index=True,
                column_config={
                    "entry_date": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD"),
                    "exit_date": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD"),
                    "entry_price": st.column_config.NumberColumn("Entry", format="%.2f"),
                    "exit_price": st.column_config.NumberColumn("Exit", format="%.2f"),
                    "shares": st.column_config.NumberColumn("Stueck"),
                    "days_held": st.column_config.NumberColumn("Haltedauer (Tage)"),
                    "pnl_dollars": st.column_config.NumberColumn("PnL ($)", format="%.0f"),
                    "pnl_pct": st.column_config.NumberColumn("PnL (%)", format="%.2%"),
                },
            )
        else:
            st.info("Keine Trades in dieser Variante.", icon=":material/info:")
