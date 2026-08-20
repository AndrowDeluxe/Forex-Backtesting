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

import sys
from pathlib import Path

import altair as alt
import pandas as pd

import streamlit as st

st.set_page_config(page_title="OU-Modell -- Paper-Backtest", page_icon=":material/science:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_DIR / "ou_paper_backtest" / "results"

# ou_paper_backtest/ is a flat script module (no __init__.py, siblings import each
# other as bare `import config`/`import portfolio`) -- put it on sys.path so the
# "Bracket-Exit (interaktiv)" tab below can reuse portfolio.simulate_bracket_portfolio
# directly instead of duplicating the simulation logic here.
sys.path.insert(0, str(REPO_DIR / "ou_paper_backtest"))
import config as bt_config  # noqa: E402
import metrics as bt_metrics  # noqa: E402
import portfolio  # noqa: E402
from kalman import kalman_smooth  # noqa: E402

BENCHMARK_FILE = {"sp500": "IDX_GSPC.parquet", "nasdaq100": "IDX_NDX.parquet", "dax": "IDX_GDAXI.parquet"}
PANEL_FILE = {"sp500": "_panel.parquet", "nasdaq100": "_panel_nasdaq100.parquet", "dax": "_panel_dax.parquet"}
VOLUME_FILE = {
    "sp500": "IDX_GSPC_VOLUME.parquet", "nasdaq100": "IDX_NDX_VOLUME.parquet", "dax": "IDX_GDAXI_VOLUME.parquet"
}

REGIME_FILTER_TYPES = {
    "ema200": "EMA 200 (empfohlen)",
    "sma200": "SMA 200",
    "vwap100": "VWAP 100 (Volumen-gewichtet)",
    "kalman": "Kalman-Trend",
    "off": "Kein Regime-Filter",
}

UNIVERSES = {
    "sp500": {"label": "S&P 500 (Sample, 90 Ticker)", "bench_label": "S&P 500"},
    "nasdaq100": {"label": "Nasdaq-100 (alle ~103 Ticker)", "bench_label": "Nasdaq-100"},
    "dax": {"label": "DAX (alle 40 Ticker)", "bench_label": "DAX"},
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


@st.cache_data(ttl="6h", show_spinner="Lade Kursdaten...")
def load_panel_and_benchmark(universe_key: str) -> tuple[pd.DataFrame, pd.Series] | None:
    panel_path = bt_config.DATA_CACHE / PANEL_FILE[universe_key]
    bench_path = bt_config.DATA_CACHE / BENCHMARK_FILE[universe_key]
    if not panel_path.exists() or not bench_path.exists():
        return None
    panel = pd.read_parquet(panel_path)
    benchmark = pd.read_parquet(bench_path).iloc[:, 0]
    return panel, benchmark


@st.cache_data(ttl="6h")
def load_volume(universe_key: str) -> pd.Series | None:
    vol_path = bt_config.DATA_CACHE / VOLUME_FILE[universe_key]
    if not vol_path.exists():
        return None
    return pd.read_parquet(vol_path).iloc[:, 0]


def _build_regime_filter(regime_type: str, universe_key: str, benchmark: pd.Series, panel_index) -> pd.Series | None:
    """All candidates tested market-wide on the benchmark index itself (2026-08-05
    sweep) -- a per-stock version of any of these was tried first and found to hurt
    more than it helps (chops out good idiosyncratic dip-buys), see the page's
    warning banner. EMA200 was the most robust winner across both universes;
    SMA200/VWAP100/Kalman are kept selectable for comparison, not because they beat it."""
    if regime_type == "off":
        return None
    if regime_type == "sma200":
        signal = benchmark > benchmark.rolling(200).mean()
    elif regime_type == "ema200":
        signal = benchmark > benchmark.ewm(span=200).mean()
    elif regime_type == "kalman":
        signal = benchmark > kalman_smooth(benchmark)
    elif regime_type == "vwap100":
        volume = load_volume(universe_key)
        if volume is None:
            return None
        pv = benchmark * volume
        vwap = pv.rolling(100).sum() / volume.rolling(100).sum()
        signal = benchmark > vwap
    else:
        raise ValueError(f"unknown regime_type {regime_type!r}")
    return signal.reindex(panel_index).fillna(False)


@st.cache_data(ttl="6h", show_spinner="Simuliere Bracket-Exit-Strategie...")
def run_bracket_sim(
    universe_key: str, universe_variant: str, stop_sigma: float, rr_ratio: float | None,
    be_trigger_r: float, max_hold: int, risk_pct: float, initial_equity: float, long_only: bool,
    regime_type: str,
):
    panel, benchmark = load_panel_and_benchmark(universe_key)
    ou_table = pd.read_csv(RESULTS_DIR / universe_key / "ou_parameters_in_sample.csv", index_col=0)
    if universe_variant == "ou":
        sel = ou_table[
            (ou_table["theta"] > bt_config.THETA_MIN) & (ou_table["p_value"] < bt_config.PVALUE_MAX)
            & (ou_table["half_life"].between(bt_config.HALFLIFE_MIN, bt_config.HALFLIFE_MAX))
        ]
        tickers = sel.index.tolist()
    else:
        tickers = ou_table.index.tolist()

    regime_filter = _build_regime_filter(regime_type, universe_key, benchmark, panel.index)

    directions = (1,) if long_only else (1, -1)
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, bt_config.OUT_SAMPLE_START, bt_config.OUT_SAMPLE_END,
        initial_equity=initial_equity, risk_pct=risk_pct, max_hold=max_hold,
        stop_sigma=stop_sigma, rr_ratio=rr_ratio, be_trigger_r=be_trigger_r,
        allowed_directions=directions, regime_filter=regime_filter,
    )
    m = bt_metrics.summarize(eq.pct_change().fillna(0.0), trades)
    bench_window = benchmark.loc[bt_config.OUT_SAMPLE_START:bt_config.OUT_SAMPLE_END]
    equity_bench = initial_equity * (bench_window / bench_window.iloc[0])
    return eq, trades, m, equity_bench


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
    "System. (3) Alle Ergebnisse **vor Transaktionskosten** (wie im Paper selbst). "
    "Fuer den tatsaechlichen Fixed-CRV-Exit-Mechanismus des Live-Bots (statt des "
    "Paper-eigenen MA-Exits) und interaktives SL/TP/Breakeven/Laufzeit/Risk-Tuning "
    "siehe den Tab **\"Bracket-Exit (interaktiv)\"** unten.",
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

tab_equity, tab_metrics, tab_ou, tab_trades, tab_bracket = st.tabs(
    [":material/show_chart: $100k Equity-Kurve", ":material/query_stats: Kennzahlen",
     ":material/functions: OU-Parameter", ":material/list_alt: Trade-Log",
     ":material/tune: Bracket-Exit (interaktiv)"]
, on_change="rerun")

def _render_tab_tab_equity():
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

def _render_tab_tab_metrics():
    with st.container(border=True):
        st.markdown("#### $100k-Konto (Risk-basiertes Sizing)")
        st.dataframe(perf_100k.round(2))
    with st.container(border=True):
        st.markdown("#### %-Return-Portfolio (paper-naeher: Equal-Weight ueber aktive Positionen)")
        st.dataframe(data["perf_pct"].round(3))

def _render_tab_tab_ou():
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

def _render_tab_tab_trades():
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

def _render_tab_tab_bracket():
    st.info(
        "Bildet den **tatsaechlichen** Exit-Mechanismus des Live-Bots (OU-Modell-MT5-Bridge) "
        "nach -- fixer Stop-Loss + fixes Take-Profit-CRV + Breakeven-Move, statt des "
        "Paper-eigenen \"Exit am gleitenden Durchschnitt\" in den anderen Tabs. Alles hier "
        "wird **live im Browser neu simuliert** (nicht vorab aus CSV geladen) -- ein "
        "Parameterwechsel dauert daher ein paar Sekunden. Voreinstellungen entsprechen dem "
        "robustesten in einem Parameter-Sweep gefundenen Wert (auf beiden Universen "
        "unabhaengig getestet): 3.0-Sigma-Stop, **kein festes Take-Profit** (Exit nur ueber "
        "SL/Breakeven/Laufzeit-Ende), 0.25R-Breakeven-Trigger -- statt der Live-Werte "
        "2.0-Sigma / 1:1.5-CRV / 0.5R.",
        icon=":material/tune:",
    )

    panel_available = load_panel_and_benchmark(universe_key) is not None
    if not panel_available:
        st.error(
            f"Kursdaten-Panel fuer '{UNIVERSES[universe_key]['label']}' nicht committed "
            f"({PANEL_FILE[universe_key]} / {BENCHMARK_FILE[universe_key]} fehlen unter "
            f"ou_paper_backtest/data_cache/). Live-Simulation hier nicht moeglich.",
            icon=":material/error:",
        )
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            variant_label = st.radio(
                "Universum-Variante", ["full", "ou"], horizontal=True,
                format_func=lambda v: "Volles Universum" if v == "full" else "OU-gefiltert",
            )
            long_only = st.toggle("Nur Long (empfohlen -- siehe Warnhinweis oben)", value=True)
            regime_type = st.selectbox(
                "Markt-Regime-Filter", list(REGIME_FILTER_TYPES.keys()),
                format_func=lambda k: REGIME_FILTER_TYPES[k],
                help="Sperrt ALLE Einstiege marktweit an Tagen, an denen der Benchmark-Index "
                     "unter seinem eigenen Trendmass notiert -- EMA200 war im Sweep "
                     "(2026-08-05) auf beiden Universen robust am staerksten, deutlich vor "
                     "SMA200/VWAP/Kalman. Ein Pro-Aktie-Trendfilter (statt marktweit) wurde "
                     "separat getestet und hat mehr geschadet als geholfen -- deshalb hier "
                     "bewusst nicht angeboten.",
            )
        with col2:
            stop_sigma = st.slider("Stop-Loss (x Rolling-Sigma)", 1.0, 3.5, 3.0, 0.25)
            tp_choice = st.select_slider(
                "Take-Profit (CRV)", options=[1.5, 2.0, 2.5, 3.0, 4.0, "Kein TP"], value="Kein TP"
            )
            rr_ratio = None if tp_choice == "Kein TP" else float(tp_choice)
            be_trigger_r = st.slider("Breakeven-Trigger (R)", 0.0, 1.5, 0.25, 0.05)
        with col3:
            max_hold = st.slider("Laufzeit (max. Handelstage)", 3, 20, 10)
            risk_pct = st.slider("Risiko pro Trade (%)", 0.25, 3.0, 1.0, 0.25) / 100
            initial_equity = st.number_input(
                "Start-Kapital ($)", min_value=1_000, value=100_000, step=10_000
            )

        eq_live, trades_live, m_live, eq_bench_live = run_bracket_sim(
            universe_key, variant_label, stop_sigma, rr_ratio, be_trigger_r,
            max_hold, risk_pct, float(initial_equity), long_only, regime_type,
        )

        with st.container(horizontal=True):
            st.metric("Endkapital", f"${eq_live.iloc[-1]:,.0f}", border=True)
            st.metric("Sharpe", f"{m_live['sharpe']:.2f}", border=True)
            st.metric("Calmar", f"{m_live['calmar']:.2f}", border=True)
            st.metric("Max Drawdown", f"{m_live['max_drawdown_pct']:.1f}%", border=True)
            st.metric("Trades", f"{m_live['n_trades']:.0f}", border=True)
            st.metric("Trefferquote", f"{m_live['win_rate_pct']:.1f}%", border=True)

        curve = pd.DataFrame({"Strategie": eq_live, bench_label: eq_bench_live}).reset_index(names="date")
        curve = curve.melt("date", var_name="Serie", value_name="Equity")
        chart = (
            alt.Chart(curve)
            .mark_line()
            .encode(
                x=alt.X("date:T", title="Datum"),
                y=alt.Y("Equity:Q", title="Kontostand ($)", scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "Serie:N", scale=alt.Scale(domain=["Strategie", bench_label], range=["#e45756", "#f58518"])
                ),
                tooltip=["date:T", "Serie:N", alt.Tooltip("Equity:Q", format=",.0f")],
            )
            .properties(height=420)
        )
        with st.container(border=True):
            st.altair_chart(chart)

        trades_df = pd.DataFrame(trades_live)
        if not trades_df.empty:
            with st.container(border=True):
                st.markdown("#### Exit-Gruende")
                st.dataframe(
                    trades_df.groupby("reason").agg(
                        n=("pnl_dollars", "size"),
                        win_rate_pct=("pnl_dollars", lambda x: (x > 0).mean() * 100),
                        avg_pnl=("pnl_dollars", "mean"),
                        total_pnl=("pnl_dollars", "sum"),
                    ).round(1),
                )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
for _tab, _render in [(tab_equity, _render_tab_tab_equity), (tab_metrics, _render_tab_tab_metrics), (tab_ou, _render_tab_tab_ou), (tab_trades, _render_tab_tab_trades), (tab_bracket, _render_tab_tab_bracket)]:
    if _tab.open:
        with _tab:
            _render()
