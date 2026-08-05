"""Fertige Strategien -- polished, presentation-style view of the FINAL, LOCKED-IN
OU-Modell configuration (no tuning sliders here -- see "OU-Modell Paper-Backtest" ->
"Bracket-Exit (interaktiv)" for that): long-only, OU-selected universe, 3.0-sigma
stop-loss, no fixed take-profit, 0.25R breakeven-move, market-wide EMA200 regime
filter (see ou-paper-backtest-project memory / commit history for the full sweep
that found this combo on S&P 500 + Nasdaq-100).

The OU-selection step is deliberately kept ON here even though it wasn't clearly
necessary on the two US universes (2026-08-05 findings) -- adding DAX as a third,
untouched-by-any-sweep market as a robustness check showed the full-universe variant
turns slightly loss-making on DAX, while the OU-filtered 13/33-ticker DAX subset
stays solidly profitable. Keeping OU-selection on uniformly costs some absolute
return on the (already strong) US legs in exchange for not failing on DAX -- an
explicit robustness-over-optimality choice, not an oversight.

Dark/monospace presentation styling per user request (loosely modeled on a
reference screenshot from an unrelated site -- visual language only, no content
copied)."""

import sys
from pathlib import Path

import altair as alt
import pandas as pd

import streamlit as st

st.set_page_config(page_title="Fertige Strategien", page_icon=":material/military_tech:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_DIR / "ou_paper_backtest" / "results"
sys.path.insert(0, str(REPO_DIR / "ou_paper_backtest"))
import config as bt_config  # noqa: E402
import metrics as bt_metrics  # noqa: E402
import portfolio  # noqa: E402

BENCHMARK_FILE = {"sp500": "IDX_GSPC.parquet", "nasdaq100": "IDX_NDX.parquet", "dax": "IDX_GDAXI.parquet"}
PANEL_FILE = {"sp500": "_panel.parquet", "nasdaq100": "_panel_nasdaq100.parquet", "dax": "_panel_dax.parquet"}
MARKET_LABEL = {"sp500": "S&P 500", "nasdaq100": "Nasdaq-100", "dax": "DAX"}

VIEWS = {
    "sp500": ["sp500"],
    "nasdaq100": ["nasdaq100"],
    "dax": ["dax"],
    "sp500_dax": ["sp500", "dax"],
    "nasdaq100_dax": ["nasdaq100", "dax"],
}
VIEW_LABELS = {
    "sp500": "S&P 500",
    "nasdaq100": "Nasdaq-100",
    "dax": "DAX",
    "sp500_dax": "S&P 500 + DAX (50/50 Diversifikation)",
    "nasdaq100_dax": "Nasdaq-100 + DAX (50/50 Diversifikation)",
}

# --- dark / monospace terminal styling (this page only -- Streamlit re-renders the
# whole DOM per page nav, so this doesn't leak onto other pages) ---
st.markdown(
    """
    <style>
    .stApp { background-color: #0a0e14; }
    .block-container { padding-top: 2rem; }
    .fs-writeup { font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
                  line-height: 1.7; color: #9db4e8; margin-bottom: 1.2rem; }
    .fs-caveats { font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: #c9d1d9; margin-bottom: 1.5rem; }
    .fs-caveats b { color: #f0f6fc; }
    .fs-tile-row { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.5rem 0; }
    .fs-tile { background: #11151c; border: 1px solid #232936; border-radius: 6px;
               padding: 1rem 1.4rem; text-align: center; flex: 1; min-width: 150px; }
    .fs-tile-value { font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.9rem;
                     font-weight: 700; color: #f0f6fc; }
    .fs-tile-label { font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.68rem;
                     letter-spacing: 0.08em; color: #8b949e; margin-top: 0.35rem; text-transform: uppercase; }
    .fs-chart-title { font-family: 'JetBrains Mono',Consolas,monospace; color: #ff8c42;
                      letter-spacing: 0.05em; font-size: 0.82rem; text-transform: uppercase;
                      margin: 1.6rem 0 0.6rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl="6h")
def load_panel_and_benchmark(market_key: str) -> tuple[pd.DataFrame, pd.Series] | None:
    panel_path = bt_config.DATA_CACHE / PANEL_FILE[market_key]
    bench_path = bt_config.DATA_CACHE / BENCHMARK_FILE[market_key]
    if not panel_path.exists() or not bench_path.exists():
        return None
    panel = pd.read_parquet(panel_path)
    benchmark = pd.read_parquet(bench_path).iloc[:, 0]
    return panel, benchmark


@st.cache_data(ttl="6h", show_spinner="Berechne finale Strategie...")
def run_final_leg(market_key: str, initial_equity: float) -> tuple[pd.Series, list[dict], pd.Series] | None:
    """The single locked-in recipe: long-only, OU-selected universe, 3.0-sigma SL,
    no TP, 0.25R breakeven, market-wide EMA200 regime filter."""
    loaded = load_panel_and_benchmark(market_key)
    if loaded is None:
        return None
    panel, benchmark = loaded
    ou_table = pd.read_csv(RESULTS_DIR / market_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > bt_config.THETA_MIN) & (ou_table["p_value"] < bt_config.PVALUE_MAX)
        & (ou_table["half_life"].between(bt_config.HALFLIFE_MIN, bt_config.HALFLIFE_MAX))
    ]
    tickers = sel.index.tolist()
    regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).fillna(False)

    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, bt_config.OUT_SAMPLE_START, bt_config.OUT_SAMPLE_END,
        initial_equity=initial_equity, risk_pct=0.01, max_hold=10,
        stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
        allowed_directions=(1,), regime_filter=regime,
    )
    bench_window = benchmark.loc[bt_config.OUT_SAMPLE_START:bt_config.OUT_SAMPLE_END]
    equity_bench = initial_equity * (bench_window / bench_window.iloc[0])
    return eq, trades, equity_bench


@st.cache_data(ttl="6h", show_spinner="Kombiniere Buecher...")
def run_view(view_key: str) -> dict | None:
    markets = VIEWS[view_key]
    per_market_equity = initial_each = 100_000.0 / len(markets)
    legs = [run_final_leg(m, per_market_equity) for m in markets]
    if any(leg is None for leg in legs):
        return None

    common_idx = legs[0][0].index
    for eq, _, _ in legs[1:]:
        common_idx = common_idx.union(eq.index)

    total_eq = pd.Series(0.0, index=common_idx)
    total_bench = pd.Series(0.0, index=common_idx)
    all_trades: list[dict] = []
    for eq, trades, bench in legs:
        total_eq = total_eq.add(eq.reindex(common_idx).ffill().fillna(initial_each), fill_value=0.0)
        total_bench = total_bench.add(bench.reindex(common_idx).ffill().fillna(initial_each), fill_value=0.0)
        all_trades.extend(trades)

    m = bt_metrics.summarize(total_eq.pct_change().fillna(0.0), all_trades)
    bench_label = " + ".join(MARKET_LABEL[mk] for mk in markets)
    return {"equity": total_eq, "benchmark": total_bench, "metrics": m, "bench_label": bench_label}


st.markdown("## :material/military_tech: Fertige Strategien")
st.caption(
    "Final validierte OU-Modell-Konfiguration -- keine Regler, keine Tuning-Optionen. "
    "Fuer interaktives Parameter-Tuning siehe *Backtests -> OU-Modell Paper-Backtest -> "
    "Bracket-Exit (interaktiv)*."
)

view_key = st.selectbox("Markt / Ansicht", list(VIEWS.keys()), format_func=lambda k: VIEW_LABELS[k])

st.markdown(
    """
    <div class="fs-writeup">
    Die finale OU-Modell-Konfiguration (Long-only, 3,0-Sigma-Stop, kein festes
    Take-Profit, 0,25R-Breakeven, marktweiter EMA-200-Regimefilter auf dem Index
    selbst) wurde ausschliesslich auf US-Aktien (S&P 500- und Nasdaq-100-Sample)
    gesucht und optimiert. Als unabhaengiger Robustheits-Check haben wir dieselbe,
    unveraenderte Konfiguration auf ein drittes, komplett separates Universum
    losgelassen: den DAX. Ergebnis: mit dem vollen 33-Ticker-DAX-Universum -- der
    Einstellung, die auf S&P/Nasdaq am staerksten performte -- waere die Strategie
    leicht defizitaer gewesen. Der Ornstein-Uhlenbeck-Selektionsfilter, der auf den
    US-Maerkten kaum noch Mehrwert brachte, erwies sich auf dem kleineren,
    konzentrierteren DAX als notwendig statt optional: erst mit OU-Selektion (13 von
    33 Titeln) wird der DAX-Zweig klar profitabel. Deshalb bleibt der OU-Filter Teil
    der finalen, marktuebergreifend <b>einheitlichen</b> Konfiguration -- auf den
    US-Maerkten kostet das etwas absolute Rendite (die dort auch ohne Filter
    funktioniert haette), auf dem DAX macht er den Unterschied zwischen Gewinn und
    Verlust.
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="fs-caveats">
    <b>Ehrliche Einschraenkungen:</b> Alle Zahlen unten sind brutto, ohne
    Handelskosten, Spread oder Slippage. Das Aktienuniversum ist in allen drei
    Maerkten ein reduziertes Sample (S&P: 90 von 503 Tickern; Nasdaq und DAX: alle
    aktuellen Konstituenten, nicht die historische Zusammensetzung ueber die Zeit).
    SL/TP/Breakeven/Regimefilter wurden iterativ gegen das 2018-2024-Testfenster auf
    S&P und Nasdaq gesucht -- der DAX-Test validiert die Robustheit auf einem
    unabhaengigen dritten Markt, ersetzt aber keinen echten Walk-Forward-Test ueber
    wechselnde Zeitfenster (naechster Schritt). Die "50/50"-Ansichten sind ein simpler
    fixer Kapitalsplit zwischen zwei unabhaengig laufenden Teilbuechern, keine
    gemeinsame Risikosteuerung -- das reduziert hier spuerbar den Drawdown, aber
    <b>nicht</b> automatisch den Calmar oder die absolute Rendite, weil der
    DAX-Zweig fuer sich genommen deutlich schwaecher ist als beide US-Maerkte. Und:
    Entscheidungen fallen nur einmal taeglich am Schlusskurs -- ein echter
    untertaegiger Schock oder ein Overnight-Gap wird vom Modell nicht abgefangen.
    </div>
    """,
    unsafe_allow_html=True,
)

result = run_view(view_key)
if result is None:
    st.error(
        f"Kursdaten fuer '{VIEW_LABELS[view_key]}' nicht vollstaendig committed unter "
        f"ou_paper_backtest/data_cache/ bzw. ou_paper_backtest/results/.",
        icon=":material/error:",
    )
    st.stop()

m = result["metrics"]
tiles = [
    ("SHARPE", f"{m['sharpe']:.2f}"),
    ("SORTINO", f"{m['sortino']:.2f}"),
    ("CALMAR", f"{m['calmar']:.2f}"),
    ("MAX DRAWDOWN", f"{m['max_drawdown_pct']:.1f}%"),
    ("WIN-RATE", f"{m['win_rate_pct']:.1f}%"),
    ("GESAMT-RETURN", f"{m['total_return_pct']:+.1f}%"),
]
tiles_html = "<div class='fs-tile-row'>" + "".join(
    f"<div class='fs-tile'><div class='fs-tile-value'>{v}</div><div class='fs-tile-label'>{l}</div></div>"
    for l, v in tiles
) + "</div>"
st.markdown(tiles_html, unsafe_allow_html=True)

bench_label = result["bench_label"]
st.markdown(
    f"<div class='fs-chart-title'>Equity Curve -- {VIEW_LABELS[view_key]} OU-Modell vs. {bench_label} (Buy&Hold)</div>",
    unsafe_allow_html=True,
)

start_val = result["equity"].iloc[0]
curve_df = pd.DataFrame({
    "date": result["equity"].index,
    "OU-Modell": result["equity"].values / start_val,
    f"{bench_label} (Buy&Hold)": result["benchmark"].values / start_val,
})
curve_long = curve_df.melt("date", var_name="Serie", value_name="Multiple")

base = alt.Chart(curve_long).encode(
    x=alt.X("date:T", title=None, axis=alt.Axis(labelColor="#8b949e", gridColor="#1c2128", domainColor="#232936")),
    y=alt.Y("Multiple:Q", title=None, axis=alt.Axis(labelColor="#8b949e", gridColor="#1c2128", domainColor="#232936")),
    tooltip=["date:T", "Serie:N", alt.Tooltip("Multiple:Q", format=".2f")],
)
strat_line = base.transform_filter(alt.datum.Serie == "OU-Modell").mark_line(color="#ff8c42", size=2.2)
bench_line = base.transform_filter(alt.datum.Serie != "OU-Modell").mark_line(
    color="#8b949e", strokeDash=[5, 4], size=1.5
)
chart = (
    (strat_line + bench_line)
    .properties(height=440, background="#0a0e14")
    .configure_view(strokeWidth=0)
)
st.altair_chart(chart)
st.markdown(
    f"<span style='font-family:monospace;color:#ff8c42;'>--- OU-Modell</span> "
    f"&nbsp;&nbsp; <span style='font-family:monospace;color:#8b949e;'>-·-·- {bench_label} (Buy&Hold)</span>",
    unsafe_allow_html=True,
)
