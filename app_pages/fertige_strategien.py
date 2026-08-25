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

CRITICAL: a genuine out-of-sample holdout (2025-today, never touched by any
parameter sweep) shows Sharpe collapsing to near-zero/negative on all three
markets, far below buy&hold -- see the "Out-of-Sample-Test" tab. Lead with that
finding, don't just present the 2018-2024 numbers as validated.

Dark/monospace presentation styling per user request (loosely modeled on a
reference screenshot from an unrelated site -- visual language only, no content
copied). Refactored 2026-08-05 into tabs + shared render helpers to cut down the
single long scroll and repeated HTML/Altair boilerplate the page had accumulated.
"""

import json
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
SIZING_METHODS = {
    "risk_based": "Risk-based (1% Equity/Trade, Standard)",
    "concentrated": "Konzentriert (1/N Tages-Setups, gedeckelt 1/8)",
}

# --- color palette (single source of truth -- keep chart colors in sync with CSS) ---
C_BG = "#0a0e14"
C_CARD = "#11151c"
C_BORDER = "#232936"
C_GRID = "#1c2128"
C_TEXT = "#f0f6fc"
C_MUTED = "#8b949e"
C_BODY = "#c9d1d9"
C_ORANGE = "#ff8c42"
C_ORANGE_SOFT = "#ffb37a"
C_BLUE = "#5ec8f8"
C_BLUE_SOFT = "#9db4e8"
C_RED = "#ff5555"

# --- dark / monospace terminal styling (this page only -- Streamlit re-renders the
# whole DOM per page nav, so this doesn't leak onto other pages) ---
st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {C_BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1200px; }}
    .fs-writeup {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
                  line-height: 1.7; color: {C_BLUE_SOFT}; margin-bottom: 1rem; }}
    .fs-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; }}
    .fs-caveats b {{ color: {C_TEXT}; }}
    .fs-alert {{ background: rgba(255,85,85,0.08); border: 1px solid {C_RED};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem; }}
    .fs-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .fs-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px;
               transition: border-color 0.15s ease; }}
    .fs-tile:hover {{ border-color: {C_ORANGE}; }}
    .fs-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.75rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .fs-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .fs-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .fs-legend {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.78rem; margin-top: 0.4rem; }}
    .fs-legend span {{ margin-right: 1.4rem; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.82rem;
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 6px 6px 0 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ render helpers
def section_title(text: str, color: str = C_ORANGE) -> None:
    st.markdown(f"<div class='fs-section-title' style='color:{color};'>{text}</div>", unsafe_allow_html=True)


def caveat_box(html: str, alert: bool = False) -> None:
    cls = "fs-alert" if alert else "fs-caveats"
    st.markdown(f"<div class='{cls}'>{html}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='fs-tile-row'>" + "".join(
        f"<div class='fs-tile'><div class='fs-tile-value'>{v}</div><div class='fs-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def legend(items: list[tuple[str, str]]) -> None:
    """items: list of (label, color) -- always rendered as a solid dash marker."""
    spans = "".join(
        f"<span style='color:{color};'>&#9644;&#9644; {label}</span>" for label, color in items
    )
    st.markdown(f"<div class='fs-legend'>{spans}</div>", unsafe_allow_html=True)


def line_chart(
    df_long: pd.DataFrame, series_colors: dict[str, tuple[str, tuple[int, int] | None]], height: int = 380
) -> alt.LayerChart:
    """df_long must have columns date, Serie, value. series_colors maps Serie name ->
    (hex color, dash pattern or None for solid)."""
    base = alt.Chart(df_long).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        y=alt.Y("value:Q", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        tooltip=["date:T", "Serie:N", alt.Tooltip("value:Q", format=".2f")],
    )
    layers = []
    for serie, (color, dash) in series_colors.items():
        mark_kwargs = {"color": color, "size": 2 if dash is None else 1.5}
        if dash:
            mark_kwargs["strokeDash"] = list(dash)
        layers.append(base.transform_filter(alt.datum.Serie == serie).mark_line(**mark_kwargs))
    chart = layers[0]
    for l in layers[1:]:
        chart = chart + l
    return chart.properties(height=height, background=C_BG).configure_view(strokeWidth=0)


def normalize(series: pd.Series, name: str) -> pd.DataFrame:
    df = (series / series.iloc[0]).reset_index()
    df.columns = ["date", "value"]
    df["Serie"] = name
    return df


# ------------------------------------------------------------------ data / simulation
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
def run_final_leg(
    market_key: str, initial_equity: float, sizing_method: str = "risk_based"
) -> tuple[pd.Series, list[dict], pd.Series] | None:
    """The single locked-in recipe: long-only, OU-selected universe, 3.0-sigma SL,
    no TP, 0.25R breakeven, market-wide EMA200 regime filter. `sizing_method`
    switches only the position-sizing mechanism (see portfolio.py) -- entry/exit
    rules never change."""
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

    if sizing_method == "concentrated":
        eq, trades = portfolio.simulate_concentrated_book(
            panel, tickers, bt_config.OUT_SAMPLE_START, bt_config.OUT_SAMPLE_END,
            book_equity=initial_equity, regime_filter=regime,
        )
    else:
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
def run_view(view_key: str, sizing_method: str = "risk_based") -> dict | None:
    markets = VIEWS[view_key]
    per_market_equity = initial_each = 100_000.0 / len(markets)
    legs = [run_final_leg(m, per_market_equity, sizing_method) for m in markets]
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


# ------------------------------------------------------------------ header + controls
st.markdown("## :material/military_tech: Fertige Strategien")
st.caption(
    "Final validierte OU-Modell-Konfiguration -- keine Regler, keine Tuning-Optionen. "
    "Fuer interaktives Parameter-Tuning siehe *Backtests -> OU-Modell Paper-Backtest -> "
    "Bracket-Exit (interaktiv)*."
)

sel_col1, sel_col2 = st.columns([2, 1])
with sel_col1:
    view_key = st.selectbox("Markt / Ansicht", list(VIEWS.keys()), format_func=lambda k: VIEW_LABELS[k])
with sel_col2:
    sizing_method = st.selectbox(
        "Sizing-Methode", list(SIZING_METHODS.keys()), format_func=lambda k: SIZING_METHODS[k],
        help="Konzentriert (1/N heutiger Setups je Markt, gedeckelt auf 1/8) schlug Risk-based "
             "im 2018-2024-Test auf S&P/Nasdaq/kombiniert deutlich, auf DAX solo leicht schlechter. "
             "Siehe Tab \"Out-of-Sample-Test\", bevor du dich auf eine Methode festlegst.",
    )

_oos_markets = VIEWS[view_key]
if "sp500" in _oos_markets and len(_oos_markets) == 1:
    _oos_text = (
        "<b>&#8505; Update (2026-08-06) -- echter Out-of-Sample-Test (siehe Tab unten):</b> "
        "Nach Skalierung des S&amp;P-Universums von 90 auf alle 420 verfuegbaren Ticker "
        "(OU-Selektion jetzt 147 statt 26 Ticker) hat sich der fruehere Alarmbefund fuer S&amp;P "
        "umgekehrt: auf echt ungesehenen Daten (2025-heute) liegt der Sharpe jetzt bei "
        "<b>1.59 und schlaegt Buy&amp;Hold (1.12)</b> -- statt vorher nahe Null. Der urspruengliche "
        "Kollaps war vermutlich groesstenteils ein Artefakt der zu kleinen, verrauschten "
        "26-Ticker-Stichprobe (nur 175 Trades), nicht zwingend echtes Overfitting. Sauber "
        "bewiesen ist das nicht -- zwei Dinge aenderten sich gleichzeitig (Universumsgroesse "
        "UND welche Ticker). Nasdaq-100/DAX sind bereits volle Indizes und zeigen weiterhin "
        "die schwachen alten OOS-Werte, siehe Tab."
    )
elif "sp500" in _oos_markets:
    _oos_text = (
        "<b>&#9888; WICHTIG -- echter Out-of-Sample-Test (siehe Tab unten):</b> Fuer den "
        "S&amp;P-Zweig (seit 2026-08-06 volles 420-Ticker-Universum statt 90) schlaegt der "
        "OOS-Sharpe (2025-heute) inzwischen sogar Buy&amp;Hold. Der DAX-Zweig ist bereits "
        "der volle offizielle Index und zeigt weiterhin einen schwachen OOS-Sharpe nahe Null "
        "-- die Kombi-Ansicht mischt also einen jetzt starken mit einem weiterhin schwachen Zweig."
    )
else:
    _oos_text = (
        "<b>&#9888; WICHTIG -- echter Out-of-Sample-Test (siehe Tab unten):</b> "
        f"{VIEW_LABELS[view_key]} ist bereits das volle offizielle Universum (kann nicht wie "
        "S&amp;P weiter skaliert werden). Auf echt ungesehenen Daten (2025-heute, in keinem "
        "Sweep verwendet) faellt der Sharpe hier weiterhin auf nahe Null bis leicht negativ, "
        "weit unter Buy&amp;Hold -- anders als beim S&amp;P-Zweig (siehe dort) ist das (noch) "
        "nicht durch eine Stichproben-Vergroesserung erklaerbar. Details im Tab."
    )
caveat_box(_oos_text, alert=True)

with st.expander(":material/menu_book: Methodik & weitere Einschraenkungen", expanded=False):
    st.markdown(
        """
        <div class="fs-writeup">
        Die finale OU-Modell-Konfiguration (Long-only, 3,0-Sigma-Stop, kein festes
        Take-Profit, 0,25R-Breakeven, marktweiter EMA-200-Regimefilter auf dem Index
        selbst) wurde auf US-Aktien gesucht und optimiert, dann auf DAX als unabhaengigem
        drittem Markt validiert. <b>Update 2026-08-06:</b> nach Skalierung des S&amp;P-Universums
        auf alle 420 verfuegbaren Ticker zeigt sich ein konsistentes Bild ueber ZWEI
        unabhaengige Zeitfenster (2018-2024 und der echte 2025-heute-Holdout): der
        Ornstein-Uhlenbeck-Selektionsfilter <b>hilft klar bei S&amp;P</b> (OOS-Sharpe 1.59 mit
        Filter vs. 0.50 ohne) <b>und bei DAX</b> (ohne Filter leicht defizitaer), <b>schadet aber
        bei Nasdaq-100</b> (OOS-Sharpe -0.10 mit Filter vs. +0.49 ohne, auf beiden Fenstern
        konsistent). Der Filter bleibt trotzdem markuebergreifend <b>einheitlich aktiv</b> --
        eine bewusste Robustheit-vor-Optimalitaet-Entscheidung, kein Versehen. Fuer den reinen
        Nasdaq-Ertrag waere ein Verzicht auf den Filter nachweislich besser.
        </div>
        <div class="fs-caveats">
        <b>Weitere ehrliche Einschraenkungen:</b> Alle Zahlen sind brutto, ohne
        Handelskosten, Spread oder Slippage. Das Aktienuniversum ist in allen drei
        Maerkten ein reduziertes Sample (S&P: 90 von 503 Tickern; Nasdaq und DAX: alle
        aktuellen Konstituenten, nicht die historische Zusammensetzung ueber die Zeit).
        Ein Walk-Forward-Test (rollierende OU-Neuauswahl) zeigte KEINEN Vorteil
        gegenueber der statischen Auswahl (siehe Tab "Walk-Forward"). Die
        "50/50"-Ansichten sind ein simpler fixer Kapitalsplit zwischen zwei unabhaengig
        laufenden Teilbuechern, keine gemeinsame Risikosteuerung -- das reduziert
        spuerbar den Drawdown, aber <b>nicht</b> automatisch den Calmar oder die
        absolute Rendite. Und: Entscheidungen fallen nur einmal taeglich am
        Schlusskurs -- ein echter untertaegiger Schock oder ein Overnight-Gap wird vom
        Modell nicht abgefangen.
        </div>
        """,
        unsafe_allow_html=True,
    )

result = run_view(view_key, sizing_method)
if result is None:
    st.error(
        f"Kursdaten fuer '{VIEW_LABELS[view_key]}' nicht vollstaendig committed unter "
        f"ou_paper_backtest/data_cache/ bzw. ou_paper_backtest/results/.",
        icon=":material/error:",
    )
    st.stop()

markets_in_view = VIEWS[view_key]
is_solo = len(markets_in_view) == 1
solo_market = markets_in_view[0] if is_solo else None

tab_equity, tab_oos, tab_mc, tab_wf, tab_cost = st.tabs([
    ":material/show_chart: Equity-Kurve",
    ":material/warning: Out-of-Sample-Test",
    ":material/casino: Monte Carlo",
    ":material/history: Walk-Forward",
    ":material/payments: Kosten-Sensitivitaet",
], on_change="rerun")

# ------------------------------------------------------------------ Tab: Equity curve
def _render_tab_equity():
    m = result["metrics"]
    tile_row([
        ("SHARPE", f"{m['sharpe']:.2f}"),
        ("SORTINO", f"{m['sortino']:.2f}"),
        ("CALMAR", f"{m['calmar']:.2f}"),
        ("MAX DRAWDOWN", f"{m['max_drawdown_pct']:.1f}%"),
        ("WIN-RATE", f"{m['win_rate_pct']:.1f}%"),
        ("GESAMT-RETURN", f"{m['total_return_pct']:+.1f}%"),
    ])

    bench_label = result["bench_label"]
    section_title(f"Equity Curve -- {VIEW_LABELS[view_key]} OU-Modell vs. {bench_label} (Buy&Hold)")

    curve_long = pd.concat([
        normalize(result["equity"], "OU-Modell"),
        normalize(result["benchmark"], bench_label),
    ])
    st.altair_chart(line_chart(curve_long, {
        "OU-Modell": (C_ORANGE, None),
        bench_label: (C_MUTED, (5, 4)),
    }))
    legend([("OU-Modell", C_ORANGE), (f"{bench_label} (Buy&Hold)", C_MUTED)])

# ------------------------------------------------------------------ Tab: Out-of-Sample
def _render_tab_oos():
    if not is_solo:
        st.info(
            "Out-of-Sample-Test ist aktuell nur fuer Einzelmaerkte verfuegbar, nicht "
            "fuer die 50/50-Kombi-Ansichten.",
            icon=":material/info:",
        )
    else:
        oos_rb_path = RESULTS_DIR / solo_market / "holdout_2025_equity_riskbased.csv"
        oos_c_path = RESULTS_DIR / solo_market / "holdout_2025_equity_concentrated.csv"
        oos_bench_path = RESULTS_DIR / solo_market / "holdout_2025_benchmark.csv"
        if oos_rb_path.exists() and oos_c_path.exists() and oos_bench_path.exists():
            caveat_box(
                "Alle Tests in den anderen Tabs (Equity-Kurve, Monte Carlo, Walk-Forward) "
                "liefen auf 2018-2024 -- demselben Fenster, gegen das SL/TP/Breakeven/"
                "Regimefilter/Sizing gesucht wurden. Hier: frisch heruntergeladene Daten "
                "bis heute, getestet NUR auf 2025 bis jetzt -- ein Zeitraum, der in keinem "
                "einzigen Parameter-Sweep dieser gesamten Recherche vorkam. Das ist der "
                "ehrlichste verfuegbare Overfitting-Check."
            )
            if solo_market == "sp500":
                caveat_box(
                    "<b>Update 2026-08-06:</b> dieser Test lief urspruenglich mit nur 26 "
                    "OU-selektierten Tickern (aus einem 90er-Zufalls-Sample) und zeigte einen "
                    "Sharpe nahe Null -- ein Alarmsignal. Nach Skalierung auf das volle "
                    "S&amp;P-Universum (147 OU-selektierte Ticker) und Neuberechnung mit frischen "
                    "Daten zeigt sich ein deutlich anderes Bild (siehe Kacheln/Kurve unten). "
                    "Mehr Ticker heisst mehr Trades (519 statt 175) und damit weniger "
                    "Stichproben-Rauschen -- ob der fruehere schwache Wert also echtes "
                    "Overfitting oder ueberwiegend Stichprobengroesse war, ist damit "
                    "wahrscheinlicher (aber nicht bewiesen) Letzteres."
                )

            oos_rb = pd.read_csv(oos_rb_path, index_col=0, parse_dates=True).iloc[:, 0]
            oos_c = pd.read_csv(oos_c_path, index_col=0, parse_dates=True).iloc[:, 0]
            oos_bench = pd.read_csv(oos_bench_path, index_col=0, parse_dates=True).iloc[:, 0]
            oos_bench_eq = 100_000.0 * (oos_bench / oos_bench.iloc[0])

            oos_m_rb = bt_metrics.summarize(oos_rb.pct_change().fillna(0.0))
            oos_m_c = bt_metrics.summarize(oos_c.pct_change().fillna(0.0))
            oos_m_bench = bt_metrics.summarize(oos_bench_eq.pct_change().fillna(0.0))

            tile_row([
                ("SHARPE RISK-BASED", f"{oos_m_rb['sharpe']:.2f}"),
                ("SHARPE KONZENTRIERT", f"{oos_m_c['sharpe']:.2f}"),
                ("SHARPE BUY&HOLD", f"{oos_m_bench['sharpe']:.2f}"),
                ("RETURN RISK-BASED", f"{oos_m_rb['total_return_pct']:+.1f}%"),
                ("RETURN KONZENTRIERT", f"{oos_m_c['total_return_pct']:+.1f}%"),
                ("RETURN BUY&HOLD", f"{oos_m_bench['total_return_pct']:+.1f}%"),
            ])

            section_title("2025 - heute (nie in einem Sweep verwendet)", color=C_RED)
            oos_curve = pd.concat([
                normalize(oos_rb, "Risk-based"),
                normalize(oos_c, "Konzentriert"),
                normalize(oos_bench_eq, "Buy&Hold"),
            ])
            st.altair_chart(line_chart(oos_curve, {
                "Risk-based": (C_ORANGE, None),
                "Konzentriert": (C_BLUE, None),
                "Buy&Hold": (C_MUTED, (5, 4)),
            }))
            legend([("Risk-based", C_ORANGE), ("Konzentriert", C_BLUE), ("Buy&Hold", C_MUTED)])
        else:
            st.info(f"OOS-Holdout-Daten fuer {MARKET_LABEL[solo_market]} noch nicht committed.", icon=":material/info:")

# ------------------------------------------------------------------ Tab: Monte Carlo
def _render_tab_mc():
    if not is_solo:
        st.info(
            "Monte-Carlo-Robustheitsanalyse ist aktuell nur fuer Einzelmaerkte verfuegbar, "
            "nicht fuer die 50/50-Kombi-Ansichten.",
            icon=":material/info:",
        )
    else:
        bands_path = RESULTS_DIR / solo_market / "monte_carlo_bands.csv"
        sims_path = RESULTS_DIR / solo_market / "monte_carlo_sims.csv"
        if bands_path.exists() and sims_path.exists():
            caveat_box(
                "Block-Bootstrap (20-Tage-Bloecke, zirkulaer) auf der REALISIERTEN taeglichen "
                "Return-Serie derselben Konfiguration -- misst also <b>Sequenz-Risiko</b> (wie "
                "stark haengt das Ergebnis davon ab, WANN gute/schlechte Phasen zufaellig "
                "aufgetreten sind), nicht \"wuerde das in einem komplett anderen, ungesehenen "
                "Marktregime funktionieren\" -- dieselbe Historie wird neu gemischt, nicht neu "
                "erfunden."
            )

            sims = pd.read_csv(sims_path)
            bands = pd.read_csv(bands_path, index_col=0, parse_dates=True)
            p_loss = (sims["final_equity"] < 100_000.0).mean() * 100

            tile_row([
                ("P(VERLUST)", f"{p_loss:.1f}%"),
                ("SHARPE P5", f"{sims['sharpe'].quantile(0.05):.2f}"),
                ("SHARPE P50", f"{sims['sharpe'].quantile(0.50):.2f}"),
                ("SHARPE P95", f"{sims['sharpe'].quantile(0.95):.2f}"),
                ("MAX-DD P5 (WORST)", f"{sims['max_drawdown_pct'].quantile(0.05):.1f}%"),
                ("MAX-DD P95 (BEST)", f"{sims['max_drawdown_pct'].quantile(0.95):.1f}%"),
            ])

            section_title("2.000 Block-Bootstrap-Pfade")
            bands_norm = bands / 100_000.0
            band_df = bands_norm.reset_index(names="date")
            fan_df = pd.concat([
                band_df[["date", "p5", "p95"]].rename(columns={"p5": "lo", "p95": "hi"}).assign(band="p5-p95"),
                band_df[["date", "p25", "p75"]].rename(columns={"p25": "lo", "p75": "hi"}).assign(band="p25-p75"),
            ])
            area = (
                alt.Chart(fan_df)
                .mark_area(opacity=0.18)
                .encode(
                    x=alt.X("date:T", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID)),
                    y=alt.Y("lo:Q", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID)),
                    y2="hi:Q",
                    color=alt.Color("band:N", scale=alt.Scale(range=[C_ORANGE, C_ORANGE_SOFT]), legend=None),
                )
            )
            median_line = (
                alt.Chart(band_df)
                .mark_line(color=C_MUTED, strokeDash=[3, 3], size=1)
                .encode(x="date:T", y=alt.Y("p50:Q", title=None))
            )
            realized_norm = result["equity"] / result["equity"].iloc[0]
            realized_df = realized_norm.reset_index()
            realized_df.columns = ["date", "value"]
            realized_line = (
                alt.Chart(realized_df)
                .mark_line(color=C_TEXT, size=1.8)
                .encode(x="date:T", y=alt.Y("value:Q", title=None))
            )
            mc_chart = (
                (area + median_line + realized_line)
                .properties(height=380, background=C_BG)
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(mc_chart)
            legend([("Realisierter Pfad", C_TEXT), ("25-75. Perzentil", C_ORANGE), ("5-95. Perzentil", C_ORANGE_SOFT)])
        else:
            st.info(f"Monte-Carlo-Daten fuer {MARKET_LABEL[solo_market]} noch nicht committed.", icon=":material/info:")

# ------------------------------------------------------------------ Tab: Walk-Forward
def _render_tab_wf():
    if not is_solo:
        st.info(
            "Walk-Forward-Vergleich ist aktuell nur fuer Einzelmaerkte verfuegbar, nicht "
            "fuer die 50/50-Kombi-Ansichten.",
            icon=":material/info:",
        )
    else:
        wf_path = RESULTS_DIR / solo_market / "walk_forward_equity.csv"
        static_path = RESULTS_DIR / solo_market / "walk_forward_static_equity.csv"
        steps_path = RESULTS_DIR / solo_market / "walk_forward_steps.csv"
        if wf_path.exists() and static_path.exists() and steps_path.exists():
            caveat_box(
                "Statt die OU-Selektion einmalig auf 2010-2017 zu fixieren (Standard in den "
                "anderen Tabs), wird hier jaehrlich neu geschaetzt: rollierendes 8-Jahres-Fenster, "
                "Universum neu selektiert, jeweils nur das FOLGEJAHR ungesehen gehandelt -- "
                "SL/TP/Breakeven/Regimefilter bleiben unveraendert, nur das gehandelte "
                "Ticker-Set aendert sich pro Jahr. <b>Befund:</b> die rollierende Neuauswahl "
                "performt hier NICHT besser als die statische -- auf S&P und Nasdaq sogar "
                "spuerbar schlechter, auf DAX in etwa gleichauf."
            )

            wf_equity = pd.read_csv(wf_path, index_col=0, parse_dates=True).iloc[:, 0]
            static_equity = pd.read_csv(static_path, index_col=0, parse_dates=True).iloc[:, 0]
            steps = pd.read_csv(steps_path)

            tile_row([
                ("STATISCH: ENDKAPITAL", f"${static_equity.iloc[-1]:,.0f}"),
                ("WALK-FORWARD: ENDKAPITAL", f"${wf_equity.iloc[-1]:,.0f}"),
                ("TICKER JAHR 1", f"{int(steps.iloc[0]['n_selected'])}"),
                ("TICKER LETZTES JAHR", f"{int(steps.iloc[-1]['n_selected'])}"),
            ])

            section_title("Walk-Forward (rollierend) vs. statische Auswahl")
            wf_curve = pd.concat([
                normalize(wf_equity, "Walk-Forward"),
                normalize(static_equity, "Statisch (2010-2017)"),
            ])
            st.altair_chart(line_chart(wf_curve, {
                "Walk-Forward": (C_BLUE, None),
                "Statisch (2010-2017)": (C_MUTED, (5, 4)),
            }))
            legend([("Walk-Forward (rollierend)", C_BLUE), ("Statisch (2010-2017 fix)", C_MUTED)])

            with st.expander("Universum-Groesse pro Jahr"):
                st.dataframe(
                    steps[["trade_year", "in_sample_start", "in_sample_end", "n_selected", "end_equity"]],
                    hide_index=True,
                    column_config={
                        "trade_year": st.column_config.NumberColumn("Handelsjahr"),
                        "in_sample_start": st.column_config.TextColumn("In-Sample ab"),
                        "in_sample_end": st.column_config.TextColumn("In-Sample bis"),
                        "n_selected": st.column_config.NumberColumn("Ticker selektiert"),
                        "end_equity": st.column_config.NumberColumn("Equity Jahresende", format="%.0f"),
                    },
                )
        else:
            st.info(f"Walk-Forward-Daten fuer {MARKET_LABEL[solo_market]} noch nicht committed.", icon=":material/info:")

# ------------------------------------------------------------------ Tab: Kosten-Sensitivitaet
def _render_tab_cost():
    if not is_solo:
        st.info(
            "Kosten-Sensitivitaet ist aktuell nur fuer Einzelmaerkte verfuegbar, nicht "
            "fuer die 50/50-Kombi-Ansichten.",
            icon=":material/info:",
        )
        return
    cost_path = RESULTS_DIR / solo_market / "cost_sensitivity.json"
    if not cost_path.exists():
        st.info(f"Kosten-Sensitivitaet fuer {MARKET_LABEL[solo_market]} noch nicht committed.", icon=":material/info:")
        return

    data = json.loads(cost_path.read_text(encoding="utf-8"))
    base = data["baseline_zero_cost"]

    st.error(
        "**Phase-6-Audit-Fund (2026-08-22):** bis zu diesem Nachtrag liefen ALLE OU-Modell-"
        "Zahlen auf dieser Seite (und im Live-Bot auf zwei Echtgeld-Konten, TTP + Tickmill, "
        "seit 2026-07-29) komplett kostenfrei -- keine Spread/Slippage/Kommission irgendwo im "
        "Backtest-Motor. Nachgeholt: ein optionaler `cost_bps`-Parameter in "
        "`portfolio.simulate_bracket_portfolio` (Default 0, byte-identisch zum bisherigen "
        "Verhalten, per Regressionstest verifiziert), der einen pauschalen Round-Trip-"
        "Transaktionskosten-Satz je Trade abzieht.",
        icon=":material/report:",
    )

    tile_row([
        ("CAGR (0bps)", f"{base['cagr_pct']:+.1f}%"),
        ("MaxDD (0bps)", f"{base['max_dd_pct']:.1f}%"),
        ("N Trades", f"{base['n_trades']:,}"),
        ("Breakeven-Kosten", f"~{data['breakeven_bps']:.0f} bps"),
    ])

    section_title("CAGR/MaxDD gegen Round-Trip-Kosten (Basispunkte vom Notional)")
    sweep_df = pd.DataFrame(data["sweep"])[["cost_bps", "final_equity", "cagr_pct", "max_dd_pct"]]
    st.dataframe(
        sweep_df.rename(columns={"cost_bps": "Kosten (bps, Round-Trip)", "final_equity": "Endkapital",
                                  "cagr_pct": "CAGR %", "max_dd_pct": "MaxDD %"}),
        hide_index=True, use_container_width=True, height=(len(sweep_df) + 1) * 36,
        column_config={"Endkapital": st.column_config.NumberColumn(format="$%.0f")},
    )
    st.success(
        f"**Bestanden mit ordentlichem, aber nicht riesigem Puffer:** Breakeven liegt bei "
        f"ca. {data['breakeven_bps']:.0f}bps Round-Trip-Kosten -- bei 30bps ist die Strategie "
        "noch klar profitabel (+70% Gesamtrendite ueber die 7 OOS-Jahre), bei 50bps praktisch "
        "bei Null. Realistische Kosten fuer ein $100k-Konto auf liquiden S&P500-Large-Caps "
        "(Spread + Slippage, kaum Kommission bei den meisten Brokern) duerften im "
        "einstelligen bis niedrigen zweistelligen Bereich liegen -- ein 3-10x-Puffer, "
        "spuerbar knapper als bei Gold ASB/ORB/CTNL, aber ein klarer Bestanden-Befund. "
        "Wichtig: MaxDD verschlechtert sich mit steigenden Kosten deutlich schneller als "
        "CAGR (-37,6% bei 0bps -> -44,2% bereits bei 20bps) -- auch bei weiterhin positiver "
        "Rendite lohnt es, die tatsaechlich beim Broker gezahlten Kosten im Blick zu behalten.",
        icon=":material/verified:",
    )
    st.caption(
        f"Konfiguration: risk_pct={data['config']['risk_pct']*100:.0f}%, "
        f"stop_sigma={data['config']['stop_sigma']}, max_hold={data['config']['max_hold']} Tage, "
        f"{data['config']['n_tickers']} Ticker, OOS {data['config']['oos_start']} bis "
        f"{data['config']['oos_end']} -- identische Konfiguration wie im Live-Bot "
        "(Fixed-CRV-Bracket-Exit)."
    )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
# result/markets_in_view/is_solo/solo_market are computed above, outside any
# tab, so all four render functions can read them regardless of which tab is open.
for _tab, _render in [
    (tab_equity, _render_tab_equity),
    (tab_oos, _render_tab_oos),
    (tab_mc, _render_tab_mc),
    (tab_wf, _render_tab_wf),
    (tab_cost, _render_tab_cost),
]:
    if _tab.open:
        with _tab:
            _render()
