"""Portfolio-Konstruktion -- EK/FK (2026-08-18).

Kombiniert alle validierten Einzelstrategien zu drei Portfolios:
- **Kombinierter Backtest**: alle 7 validierten Strategien gleichgewichtet,
  Sharpe/Sortino/Calmar/MaxDD/CAGR + Korrelationsmatrix -- die Ausgangsfrage
  "was passiert, wenn wir alles parallel auf einem Konto traden".
- **EK-Portfolio**: alle 7 Strategien, Mean-Variance/Max-Sharpe-optimiert,
  einzige Grenze 30% Gesamt-Drawdown (rein psychologisch, kein hartes Limit).
- **FK-Portfolio**: nur die 5 Strategien, die realistisch auf einem
  Prop-Firm-Konto handelbar sind (siehe Vorbehalte-Abschnitt), optimiert
  nicht auf Rendite sondern auf schnellstes Erreichen des Gewinnziels bei
  minimaler Bruch-Wahrscheinlichkeit der jeweiligen Firmenregeln (TTP und
  IQ Markets unterscheiden sich: Tageslimit vs. Positionslimit, 7% vs. 6%
  Gesamt-DD, 10% vs. 8% Ziel). FK-Werte stammen aus einer Monte-Carlo-
  Block-Bootstrap-Simulation (3000 Pfade x 500 Handelstage) der
  historischen Tagesrenditen -- keine Garantie, eine Wahrscheinlichkeits-
  aussage.

Liest ausschliesslich vorab berechnete Ergebnisse aus
portfolio_construction/results/ (Equity-Kurven je Strategie als CSV,
Metriken/Gewichte/Monte-Carlo-Resultate als JSON). Die eigentliche
Berechnung (7 Einzel-Backtests mit den jeweils gesperrten Live-Konfigu-
rationen, Mean-Variance-Optimierung, Monte-Carlo-Simulation) lief einmalig
lokal -- die Seite selbst rechnet nur noch leichte Kombinationen
(gewichtete Summen/Renditen aus den bereits geladenen Kurven), keine neuen
Backtests. Architektur folgt der bereits getroffenen Entscheidung
"Kapital-Allokation statt Risiko-Verwebung" (siehe
section_portfolio_management.py / knowledge/resources/
trend-following-momentum.md, Nachtrag 2026-08-15): jede Strategie behaelt
ihre eigene, unveraenderte validierte Logik auf einem festen Kapitalanteil,
die $-Kurven werden kombiniert, kein Eingriff in die live laufenden Bots.

FK-Roster-Begruendung (2026-08-17/18, siehe Vorbehalte-Tab): ORB und die
rohe Gold-Bitcoin-Dual-Momentum-Variante sind NICHT im FK-Portfolio, weil
(a) keine Evidenz, dass TTP/IQ Markets die noetigen Instrumente ueberhaupt
anbieten (ORB) bzw. (b) der Drawdown der validierten Version jede
Prop-Firm-Grenze klar sprengt (Gold-Bitcoin). OU-Modell ist im FK-Track nur
mit der TTP-handelbaren Ticker-Teilmenge (58/147 SP500, 8/16 Nasdaq, DAX
komplett raus) enthalten, Trend Pullback mit FK1's tatsaechlichem
0.10%-Risiko statt der im EK-Track genutzten 1%-Referenz."""

import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd

import streamlit as st

st.set_page_config(page_title="Portfolio-Konstruktion -- EK/FK", page_icon=":material/account_balance_wallet:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_DIR / "portfolio_construction" / "results"
LEGS_DIR = RESULTS_DIR / "legs"

# --- gleiche Palette wie fertige_strategien.py / cls_practical_live_log.py ---
C_BG = "#0a0e14"
C_CARD = "#11151c"
C_BORDER = "#232936"
C_GRID = "#1c2128"
C_TEXT = "#f0f6fc"
C_MUTED = "#8b949e"
C_BODY = "#c9d1d9"
C_ORANGE = "#ff8c42"
C_BLUE = "#5ec8f8"
C_GREEN = "#5ecb8c"
C_RED = "#ff5555"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {C_BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1280px; }}
    .pc-lede {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
              line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; max-width: 92ch; }}
    .pc-lede b {{ color: {C_TEXT}; }}
    .pc-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 1.4rem 0 0.7rem 0; font-weight: 600; }}
    .pc-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 0.6rem 0 1.2rem; }}
    .pc-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px; }}
    .pc-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.5rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .pc-tile-value.good {{ color: {C_GREEN}; }}
    .pc-tile-value.bad {{ color: {C_RED}; }}
    .pc-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .pc-weight-row {{ display: grid; grid-template-columns: 190px 1fr 46px; align-items: center;
                     gap: 0.6rem; margin-bottom: 0.5rem; font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.8rem; }}
    .pc-weight-name {{ color: {C_BODY}; font-size: 0.78rem; }}
    .pc-weight-track {{ background: {C_BG}; border-radius: 4px; height: 10px; overflow: hidden; border: 1px solid {C_BORDER}; }}
    .pc-weight-fill {{ height: 100%; border-radius: 4px; }}
    .pc-weight-pct {{ text-align: right; color: {C_TEXT}; font-weight: 700; }}
    .pc-outcome-bar {{ display: flex; height: 26px; border-radius: 6px; overflow: hidden; margin: 0.5rem 0 0.5rem; }}
    .pc-outcome-seg {{ display: flex; align-items: center; justify-content: center; font-size: 0.68rem;
                      color: white; font-weight: 700; font-family: 'JetBrains Mono',Consolas,monospace; }}
    .pc-outcome-legend {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.72rem; color: {C_MUTED};
                         display: flex; gap: 1.1rem; flex-wrap: wrap; margin-bottom: 0.8rem; }}
    .pc-rule-badge {{ display: inline-flex; font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.72rem;
                     background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 999px;
                     padding: 0.25rem 0.7rem; color: {C_BODY}; margin: 0 0.4rem 0.4rem 0; }}
    .pc-rule-badge b {{ color: {C_TEXT}; }}
    .pc-table {{ width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono',Consolas,monospace;
               font-size: 0.82rem; margin: 0.5rem 0 1.2rem 0; }}
    .pc-table th {{ text-align: right; color: {C_MUTED}; font-size: 0.66rem; letter-spacing: 0.05em;
                  text-transform: uppercase; padding: 0.55rem 0.8rem; border-bottom: 1px solid {C_BORDER}; }}
    .pc-table th:first-child, .pc-table td:first-child {{ text-align: left; }}
    .pc-table td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid {C_BORDER}; color: {C_TEXT}; text-align: right; }}
    .pc-table tr.total td {{ border-top: 2px solid {C_ORANGE}; font-weight: 700; background: {C_CARD}; }}
    .pc-table td.pos {{ color: {C_GREEN}; }}
    .pc-table td.neg {{ color: {C_RED}; }}
    .pc-flag {{ display: inline-block; font-size: 0.6rem; padding: 0.1rem 0.4rem; border-radius: 4px;
              background: rgba(255,85,85,0.12); color: {C_RED}; margin-left: 0.4rem; }}
    .pc-candidate {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 10px; padding: 1.1rem 1.2rem; }}
    .pc-candidate-head {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.3rem;
                         font-family: 'JetBrains Mono',Consolas,monospace; }}
    .pc-candidate-title {{ font-size: 0.9rem; font-weight: 700; color: {C_TEXT}; }}
    .pc-candidate-tag {{ font-size: 0.64rem; padding: 0.12rem 0.55rem; border-radius: 999px; font-family: 'JetBrains Mono',Consolas,monospace; }}
    .pc-candidate-tag.safe {{ background: rgba(94,203,140,0.15); color: {C_GREEN}; }}
    .pc-candidate-tag.fast {{ background: rgba(255,140,66,0.18); color: {C_ORANGE}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def section_title(text: str) -> None:
    st.markdown(f"<div class='pc-section-title'>{text}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str, str]]) -> None:
    """tiles: list of (label, value, css_class ('' | 'good' | 'bad'))"""
    html = "<div class='pc-tile-row'>" + "".join(
        f"<div class='pc-tile'><div class='pc-tile-value {cls}'>{v}</div><div class='pc-tile-label'>{l}</div></div>"
        for l, v, cls in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def weight_bars(weights: dict[str, float], labels: dict[str, str], color: str = C_BLUE) -> None:
    rows = sorted(weights.items(), key=lambda kv: -kv[1])
    html = ""
    for key, w in rows:
        if w < 0.005:
            continue
        html += (
            f"<div class='pc-weight-row'><div class='pc-weight-name'>{labels.get(key, key)}</div>"
            f"<div class='pc-weight-track'><div class='pc-weight-fill' style='width:{w*100:.1f}%; background:{color};'></div></div>"
            f"<div class='pc-weight-pct'>{w*100:.1f}%</div></div>"
        )
    st.markdown(html, unsafe_allow_html=True)


def outcome_bar(p_target: float, p_neither: float, p_breach: float) -> None:
    def seg(pct, color):
        label = f"{pct*100:.1f}%" if pct > 0.08 else ""
        return f"<div class='pc-outcome-seg' style='width:{pct*100:.2f}%; background:{color};'>{label}</div>"
    html = f"<div class='pc-outcome-bar'>{seg(p_target, C_GREEN)}{seg(p_neither, C_MUTED)}{seg(p_breach, C_RED)}</div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(
        f"<div class='pc-outcome-legend'>"
        f"<span>&#9632; <span style='color:{C_GREEN};'>Ziel erreicht {p_target*100:.1f}%</span></span>"
        f"<span>&#9632; <span style='color:{C_MUTED};'>weder/noch {p_neither*100:.1f}%</span></span>"
        f"<span>&#9632; <span style='color:{C_RED};'>Regel gebrochen {p_breach*100:.1f}%</span></span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def line_chart(df_long: pd.DataFrame, series_colors: dict[str, tuple[str, tuple[int, int] | None]], height: int = 340) -> alt.LayerChart:
    base = alt.Chart(df_long).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        y=alt.Y("value:Q", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER, format="$,.0f")),
        tooltip=["date:T", "Serie:N", alt.Tooltip("value:Q", format="$,.0f")],
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


# ------------------------------------------------------------------ data
@st.cache_data
def load_json(name: str) -> dict:
    return json.loads((RESULTS_DIR / name).read_text(encoding="utf-8"))


@st.cache_data
def load_leg(key: str) -> pd.Series:
    df = pd.read_csv(LEGS_DIR / f"{key}.csv", parse_dates=["date"]).drop_duplicates("date").set_index("date").sort_index()
    return df["equity"].astype(float)


@st.cache_data
def combine_dollarsum(leg_keys: tuple[str, ...], window: str) -> pd.Series:
    """Matches combine_portfolio.py: sum of $100k-per-leg curves / n, no rebalancing."""
    sers = {k: load_leg(k) for k in leg_keys}
    starts = {k: s.index.min() for k, s in sers.items()}
    ends = {k: s.index.max() for k, s in sers.items()}
    if window == "common":
        idx = pd.date_range(max(starts.values()), min(ends.values()), freq="D")
        aligned = {k: s.reindex(idx).ffill() for k, s in sers.items()}
    else:
        idx = pd.date_range(min(starts.values()), max(ends.values()), freq="D")
        aligned = {k: s.reindex(idx).ffill().bfill() for k, s in sers.items()}
    return pd.DataFrame(aligned).sum(axis=1) / len(leg_keys)


@st.cache_data
def combine_rebalanced(weights: dict[str, float], leg_keys: tuple[str, ...]) -> pd.Series:
    """Matches ek_optimize.py/fk_optimize.py: daily-rebalanced weighted returns, constant weights."""
    sers = {k: load_leg(k) for k in leg_keys}
    common_start = max(s.index.min() for s in sers.values())
    common_end = min(s.index.max() for s in sers.values())
    idx = pd.date_range(common_start, common_end, freq="D")
    rets = pd.DataFrame({k: sers[k].reindex(idx).ffill().pct_change() for k in leg_keys}).dropna()
    w = np.array([weights[k] for k in leg_keys])
    port_daily = rets.values @ w
    return pd.Series(100000 * (1 + port_daily).cumprod(), index=rets.index)


metrics = load_json("portfolio_metrics.json")
ek = load_json("ek_optimization.json")
fk = load_json("fk_optimization.json")

st.markdown("## :material/account_balance_wallet: Portfolio-Konstruktion -- EK/FK")
st.markdown(
    "<div class='pc-lede'>Aus allen bisher validierten Strategien werden mehrere Portfolios gebaut: "
    "<b>EK</b> (Eigenkapital, alle 7 Strategien, Rendite-optimiert), <b>FK</b> (Fremdkapital/Prop-Firm, nur "
    "die 5 realistisch handelbaren Strategien, auf Regelkonformitaet statt Rendite optimiert) und ein "
    "<b>EK-Schnellkonto</b>-Sonderfall (kleines Konto, Ziel +7% so schnell wie moeglich bei max. 7% Drawdown). "
    "Unten zuerst der Ausgangspunkt -- der kombinierte Backtest aller 7 -- dann eine Trade-Overlap-Analyse, "
    "danach die drei abgeleiteten Portfolios.</div>",
    unsafe_allow_html=True,
)

tab_combined, tab_overlap, tab_ek, tab_fk, tab_ekfast, tab_caveats = st.tabs([
    ":material/query_stats: Kombinierter Backtest",
    ":material/calendar_view_week: Trade-Overlap",
    ":material/savings: EK-Portfolio",
    ":material/shield: FK-Portfolio",
    ":material/bolt: EK-Schnellkonto",
    ":material/report: Einordnung & Vorbehalte",
])

EK_KEYS = tuple(ek["ek_leg_labels"].keys())
FK_KEYS = tuple(fk["fk_leg_labels"].keys())

# ============================================================ Tab: Kombinierter Backtest
with tab_combined:
    cw = metrics["combined_common_window"]
    st.caption(
        f"Alle 7 Strategien gleichgewichtet (1/7), Zeitraum in dem wirklich alle aktiv liefen: "
        f"{cw['start']} bis {cw['end']} ({cw['years']} Jahre). $100.000 Start."
    )
    tile_row([
        ("CAGR", f"{cw['cagr_pct']:+.1f}%", "good" if cw["cagr_pct"] >= 0 else "bad"),
        ("Sharpe", f"{cw['sharpe']:.2f}", ""),
        ("Sortino", f"{cw['sortino']:.2f}", ""),
        ("Calmar", f"{cw['calmar']:.2f}", ""),
        ("Max Drawdown", f"{cw['max_dd_pct']:.1f}%", "bad"),
        ("Endkapital", f"${cw['final_equity']:,.0f}", "good"),
    ])

    section_title("Kombinierte Equity-Kurve (volle Historie, gestaffelter Start)")
    union_curve = combine_dollarsum(EK_KEYS, "union").resample("W-FRI").last().dropna()
    df_union = union_curve.rename("value").rename_axis("date").reset_index()
    df_union["Serie"] = "Portfolio"
    st.altair_chart(line_chart(df_union, {"Portfolio": (C_BLUE, None)}), use_container_width=True)

    section_title("Die 7 Strategien einzeln")
    per_leg = {m["label"]: m for m in metrics["per_leg"]}
    leg_label_map = {
        "ou_modell": "OU-Modell (SP500 only)", "cls_practical": "CLS Practical (EURUSD)",
        "btc_ema_cross": "BTC EMA9/21", "gold_asb": "Gold Asian-Range Breakout",
        "trend_pullback": "Trend Pullback (5 Maerkte)", "gold_bitcoin_dual_momentum": "Gold-Bitcoin Dual Momentum",
        "orb_strategy": "ORB (long+ADX, NDX/SP500)",
    }
    cols = st.columns(4)
    for i, (key, full_label) in enumerate(leg_label_map.items()):
        m = per_leg[full_label]
        with cols[i % 4]:
            with st.container(border=True):
                flag = " :material/warning:" if key in ("ou_modell", "trend_pullback") else ""
                st.markdown(f"**{ek['ek_leg_labels'][key]}**{flag}")
                leg_curve = load_leg(key).resample("W-FRI").last().dropna()
                df_leg = leg_curve.rename("value").rename_axis("date").reset_index()
                df_leg["Serie"] = key
                st.altair_chart(
                    line_chart(df_leg, {key: (C_BLUE, None)}, height=100).properties(width="container"),
                    use_container_width=True,
                )
                st.caption(f"CAGR {m['cagr_pct']:+.1f}% &middot; Sharpe {m['sharpe']:.2f} &middot; MaxDD {m['max_dd_pct']:.1f}%")

    section_title("Korrelation der Tagesrenditen (gemeinsamer Zeitraum)")
    corr = metrics["correlation_matrix"]
    corr_rows = []
    for a in EK_KEYS:
        for b in EK_KEYS:
            corr_rows.append({"Strategie A": ek["ek_leg_labels"][a], "Strategie B": ek["ek_leg_labels"][b], "Korrelation": corr[a][b]})
    corr_df = pd.DataFrame(corr_rows)
    heatmap = alt.Chart(corr_df).mark_rect().encode(
        x=alt.X("Strategie A:N", title=None, axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER, labelAngle=-40)),
        y=alt.Y("Strategie B:N", title=None, axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER)),
        color=alt.Color("Korrelation:Q", scale=alt.Scale(scheme="redblue", domainMid=0, reverse=True), legend=None),
        tooltip=["Strategie A", "Strategie B", alt.Tooltip("Korrelation:Q", format=".3f")],
    )
    text = alt.Chart(corr_df).mark_text(fontSize=10).encode(
        x="Strategie A:N", y="Strategie B:N", text=alt.Text("Korrelation:Q", format=".2f"),
        color=alt.condition("abs(datum.Korrelation) > 0.1", alt.value("white"), alt.value(C_MUTED)),
    )
    st.altair_chart(
        (heatmap + text).properties(height=340, background=C_BG).configure_view(strokeWidth=0),
        use_container_width=True,
    )
    st.caption("Alle Korrelationen liegen nahe Null (hoechste: BTC/Gold-Bitcoin 0.15) -- der Grund, warum der Portfolio-Drawdown so viel kleiner ausfaellt als jede Einzelstrategie.")

    section_title("Kennzahlen im Detail")
    rows_html = ""
    for key, full_label in leg_label_map.items():
        m = per_leg[full_label]
        rows_html += (
            f"<tr><td>{ek['ek_leg_labels'][key]}</td><td>{m['start']} &ndash; {m['end']}</td><td>{m['years']}</td>"
            f"<td class='{'pos' if m['cagr_pct']>=0 else 'neg'}'>{m['cagr_pct']:+.1f}%</td>"
            f"<td>{m['sharpe']:.2f}</td><td>{m['sortino']:.2f}</td>"
            f"<td class='neg'>{m['max_dd_pct']:.1f}%</td><td>{m['calmar']:.2f}</td><td>${m['final_equity']:,.0f}</td></tr>"
        )
    rows_html += (
        f"<tr class='total'><td>PORTFOLIO (alle 7, gleichgewichtet)</td><td>{cw['start']} &ndash; {cw['end']}</td><td>{cw['years']}</td>"
        f"<td class='pos'>{cw['cagr_pct']:+.1f}%</td><td>{cw['sharpe']:.2f}</td><td>{cw['sortino']:.2f}</td>"
        f"<td class='neg'>{cw['max_dd_pct']:.1f}%</td><td>{cw['calmar']:.2f}</td><td>${cw['final_equity']:,.0f}</td></tr>"
    )
    st.markdown(
        f"<table class='pc-table'><thead><tr><th>Strategie</th><th>Zeitraum</th><th>Jahre</th><th>CAGR</th>"
        f"<th>Sharpe</th><th>Sortino</th><th>MaxDD</th><th>Calmar</th><th>Endkapital</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>",
        unsafe_allow_html=True,
    )

# ============================================================ Tab: Trade-Overlap
with tab_overlap:
    ov = load_json("overlap_analysis.json")
    st.caption(
        "Zeigt, wie oft welche Strategien wirklich gleichzeitig eine Position offen haben -- "
        "Grundlage fuer die These, dass selten tradende Strategien sich kaum ueberschneiden."
    )
    tile_row([
        ("Ø gleichzeitig aktiv (FK-5)", f"{ov['avg_simultaneous_fk5']:.2f} / 5", ""),
        ("Tage mit 0 aktiv (FK-5)", f"{ov['dist_simultaneous_fk5'].get('0', 0) / sum(ov['dist_simultaneous_fk5'].values()) * 100:.1f}%", ""),
        ("Ø aktiv an Verlust-Tagen", f"{ov['loss_day_avg_active_fk5']:.2f}", ""),
        ("Ø aktiv an Gewinn-Tagen", f"{ov['nonloss_day_avg_active_fk5']:.2f}", ""),
        ("Korr. Aktivitaet<->Verlusthoehe", f"{ov['corr_activity_vs_loss_magnitude']:.3f}", ""),
    ])
    st.info(
        "**Ehrlicher Befund:** die Korrelation zwischen \"Anzahl gleichzeitig aktiver Strategien\" und der "
        "Verlusthoehe an einem Tag liegt praktisch bei Null. Mehr gleichzeitige Aktivitaet allein macht einen "
        "Tag NICHT verlusttraechtiger -- was zaehlt, ist die (bereits an anderer Stelle gezeigte) fast "
        "nicht vorhandene *Korrelation der Renditen* zwischen den Strategien, nicht wie oft sie gleichzeitig "
        "im Markt sind. Die geringe Ueberschneidungshaeufigkeit (Ø nur 1,5 von 5 FK-Strategien gleichzeitig "
        "aktiv, 17% der Tage komplett flach) ist trotzdem ein Grund, warum das Portfolio insgesamt ruhiger "
        "wirkt als jede Einzelstrategie -- nur eben nicht der Hauptgrund fuer den kleineren Drawdown.",
        icon=":material/lightbulb:",
    )

    section_title("Wie viele Strategien sind gleichzeitig aktiv? (woechentlich)")
    weekly_counts_df = pd.DataFrame(ov["weekly_counts"])
    weekly_counts_df["date"] = pd.to_datetime(weekly_counts_df["date"])
    area = alt.Chart(weekly_counts_df).mark_area(color=C_BLUE, opacity=0.35, line={"color": C_BLUE, "strokeWidth": 1.5}).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        y=alt.Y("n_active_fk:Q", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        tooltip=["date:T", "n_active_fk:Q", "n_active_all:Q"],
    ).properties(height=220, background=C_BG).configure_view(strokeWidth=0)
    st.altair_chart(area, use_container_width=True)
    st.caption("Anzahl der 5 FK-Strategien mit gleichzeitig offener Position, pro Kalenderwoche (Maximalwert der Woche).")

    section_title("Aktivitaets-Zeitleiste je Strategie (woechentlich)")
    ribbon_df = pd.read_csv(RESULTS_DIR / "weekly_activity_ribbon.csv", parse_dates=["date"])
    ribbon_df["Strategie"] = ribbon_df["strategy"].map(ek["ek_leg_labels"])
    ribbon_df["Aktiv"] = ribbon_df["active"].map({True: "aktiv", False: "inaktiv"})
    ribbon_chart = alt.Chart(ribbon_df).mark_rect().encode(
        x=alt.X("date:T", title=None, timeUnit="yearmonth", axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER)),
        y=alt.Y("Strategie:N", title=None, axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER)),
        color=alt.Color("active:Q", scale=alt.Scale(range=[C_BG, C_BLUE]), legend=None),
        tooltip=["date:T", "Strategie:N", "Aktiv:N"],
    ).properties(height=220, background=C_BG).configure_view(strokeWidth=0)
    st.altair_chart(ribbon_chart, use_container_width=True)
    st.caption("Blau = mindestens eine offene Position irgendwo in dieser Strategie in diesem Monat.")

    section_title("Paarweise Ueberschneidung (% der Tage, an denen Zeile UND Spalte aktiv sind, bezogen auf die Zeile)")
    overlap_matrix = ov["overlap_pct_matrix"]
    ov_rows = []
    for a in ek["ek_leg_labels"]:
        for b in ek["ek_leg_labels"]:
            ov_rows.append({"A": ek["ek_leg_labels"][a], "B": ek["ek_leg_labels"][b], "pct": overlap_matrix[a][b]})
    ov_df = pd.DataFrame(ov_rows)
    ov_heat = alt.Chart(ov_df).mark_rect().encode(
        x=alt.X("B:N", title=None, axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER, labelAngle=-40)),
        y=alt.Y("A:N", title=None, axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER)),
        color=alt.Color("pct:Q", scale=alt.Scale(scheme="blues"), legend=None),
        tooltip=["A", "B", alt.Tooltip("pct:Q", format=".1f")],
    )
    ov_text = alt.Chart(ov_df).mark_text(fontSize=9).encode(
        x="B:N", y="A:N", text=alt.Text("pct:Q", format=".0f"),
        color=alt.condition("datum.pct > 40", alt.value("white"), alt.value(C_MUTED)),
    )
    st.altair_chart((ov_heat + ov_text).properties(height=340, background=C_BG).configure_view(strokeWidth=0), use_container_width=True)
    st.caption(
        "Zeile lesen: \"An X% der Tage, an denen [Zeile] aktiv ist, ist auch [Spalte] aktiv.\" Nicht "
        "symmetrisch -- eine selten aktive Strategie (z.B. Gold ASB, 2,8% der Tage) hat niedrige Werte in "
        "beide Richtungen einfach weil sie so selten laeuft."
    )

    section_title("Aktivitaets-Anteil je Strategie")
    act_rows = ""
    for key, label in ek["ek_leg_labels"].items():
        pct = ov["active_day_pct"][key]
        n_trades = ov["trade_counts"][key]
        flag = " &#9733; FK" if key in fk["fk_leg_labels"] else ""
        act_rows += f"<tr><td>{label}{flag}</td><td>{n_trades}</td><td>{pct:.1f}%</td></tr>"
    st.markdown(
        f"<table class='pc-table'><thead><tr><th>Strategie</th><th>Trades</th><th>% der Tage aktiv</th></tr></thead>"
        f"<tbody>{act_rows}</tbody></table>",
        unsafe_allow_html=True,
    )
    st.caption("Zeitraum 2016-01-01 bis 2026-08-17 (voller Datenbereich aller Strategien).")


# ============================================================ Tab: EK
with tab_ek:
    st.caption("Alle 7 Strategien, Mean-Variance/Max-Sharpe-optimiert (long-only, Gewichte summieren zu 100%). Einzige Grenze: 30% Gesamt-Drawdown (psychologisch, kein hartes Limit).")
    msh = ek["results"]["maxsharpe"]
    tile_row([
        ("CAGR", f"{msh['cagr_pct']:+.1f}%", "good"),
        ("Sharpe", f"{msh['sharpe']:.2f}", ""),
        ("Sortino", f"{msh['sortino']:.2f}", ""),
        ("Calmar", f"{msh['calmar']:.2f}", ""),
        ("Max Drawdown", f"{msh['max_dd_pct']:.1f}%", "bad"),
        ("Endkapital", f"${msh['final_equity']:,.0f}", "good"),
    ])

    col1, col2 = st.columns([3, 2])
    with col1:
        section_title("Max-Sharpe vs. Equal-Weight")
        eq_curve = combine_rebalanced(ek["results"]["equal"]["weights"], EK_KEYS).resample("W-FRI").last().dropna()
        msh_curve = combine_rebalanced(msh["weights"], EK_KEYS).resample("W-FRI").last().dropna()
        df1 = msh_curve.rename("value").rename_axis("date").reset_index(); df1["Serie"] = "Max-Sharpe"
        df2 = eq_curve.rename("value").rename_axis("date").reset_index(); df2["Serie"] = "Equal-Weight"
        df_ek = pd.concat([df1, df2])
        st.altair_chart(line_chart(df_ek, {"Max-Sharpe": (C_BLUE, None), "Equal-Weight": (C_MUTED, (4, 3))}), use_container_width=True)
    with col2:
        section_title("Kapitalverteilung (Max-Sharpe)")
        weight_bars(msh["weights"], ek["ek_leg_labels"], color=C_BLUE)

    section_title("Alternative Gewichtungen im Vergleich")
    alt_rows = ""
    for key in ["equal", "riskparity", "minvar", "maxsharpe"]:
        r = ek["results"][key]
        marker = " &#9733;" if key == "maxsharpe" else ""
        alt_rows += (
            f"<tr><td>{r['label']}{marker}</td><td class='pos'>{r['cagr_pct']:+.1f}%</td><td>{r['sharpe']:.2f}</td>"
            f"<td>{r['sortino']:.2f}</td><td class='neg'>{r['max_dd_pct']:.1f}%</td><td>{r['calmar']:.2f}</td>"
            f"<td>${r['final_equity']:,.0f}</td></tr>"
        )
    st.markdown(
        f"<table class='pc-table'><thead><tr><th>Gewichtung</th><th>CAGR</th><th>Sharpe</th><th>Sortino</th>"
        f"<th>MaxDD</th><th>Calmar</th><th>Endkapital</th></tr></thead><tbody>{alt_rows}</tbody></table>",
        unsafe_allow_html=True,
    )

# ============================================================ Tab: FK
with tab_fk:
    st.caption("Nur die 5 FK-tauglichen Strategien (siehe Vorbehalte). Zwei unterschiedliche Regelwerke, Monte-Carlo-simuliert.")
    rule_choice = st.radio("Zielfirma", ["TTP", "IQ Markets"], horizontal=True, label_visibility="collapsed")
    rule_key = "ttp" if rule_choice == "TTP" else "iqmarkets"
    rule = fk["rules"][rule_key]

    if rule_key == "ttp":
        st.markdown(
            "<span class='pc-rule-badge'>Tageslimit <b>3%</b></span>"
            "<span class='pc-rule-badge'>Gesamt-Drawdown <b>7%</b></span>"
            "<span class='pc-rule-badge'>Gewinnziel <b>10%</b></span> "
            "&mdash; einziges Regelwerk mit hartem Tageslimit, daher am empfindlichsten gegen Tage mit mehreren gleichzeitig negativen Strategien.",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span class='pc-rule-badge'>Pro Position <b>1%</b></span>"
            "<span class='pc-rule-badge'>Gesamt-Drawdown <b>6%</b></span>"
            "<span class='pc-rule-badge'>Gewinnziel <b>8%</b></span> "
            "&mdash; kein Tageslimit, dafuer straffere Gesamt-Grenze. Das 1%-Positionslimit ist durch die "
            "bestehende Einzelstrategie-Kalibrierung bereits automatisch erfuellt.",
            unsafe_allow_html=True,
        )

    fk_riskopt = load_json("fk_risk_optimized.json")
    CAND_TITLES = {"equal": "Equal-Weight", "equal_ex_trendpullback": "Ohne Trend Pullback", "riskopt": "Risiko-optimiert"}
    col1, col2, col3 = st.columns(3)
    for col, cand_key, tag, tag_label in [
        (col1, "equal", "safe", "sicher"), (col2, "equal_ex_trendpullback", "fast", "schnell"), (col3, "riskopt", "fast", "empfohlen"),
    ]:
        if cand_key == "riskopt":
            mc = fk_riskopt["monte_carlo"][rule_key]
            hist = fk_riskopt["historical_metrics"]
            weights_for_bars = fk_riskopt["combo"]
        else:
            mc = fk["monte_carlo"][rule_key][cand_key]
            hist = fk["historical_metrics"][cand_key]
            weights_for_bars = None
        with col:
            st.markdown(
                f"<div class='pc-candidate'><div class='pc-candidate-head'>"
                f"<span class='pc-candidate-title'>{CAND_TITLES[cand_key]}</span>"
                f"<span class='pc-candidate-tag {tag}'>{tag_label}</span></div></div>",
                unsafe_allow_html=True,
            )
            outcome_bar(mc["p_target"], mc["p_neither"], mc["p_breach"])
            c1, c2, c3m = st.columns(3)
            c1.metric("Median Tage bis Ziel", f"{mc['median_days_to_target']:.0f}" if mc["median_days_to_target"] else "—")
            c2.metric("Sharpe (historisch)", f"{hist['sharpe']:.2f}")
            c3m.metric("MaxDD (historisch)", f"{hist['max_dd_pct']:.1f}%")
            if cand_key == "riskopt":
                st.caption("Eigenes Risiko je Strategie hochgesetzt (siehe unten) statt Gewicht verschoben -- gleiche 20%-Kapitalverteilung wie Equal-Weight.")
                rows_html = ""
                for leg_key, risk_label in weights_for_bars.items():
                    rows_html += (
                        f"<div class='pc-weight-row' style='grid-template-columns:1fr 60px;'>"
                        f"<div class='pc-weight-name'>{fk['fk_leg_labels'][leg_key]}</div>"
                        f"<div class='pc-weight-pct'>{risk_label}</div></div>"
                    )
                st.markdown(rows_html, unsafe_allow_html=True)
                st.caption("Risiko/Trade je Strategie (nicht Kapitalanteil -- der ist bei allen 3 Kandidaten gleich 20%).")
            else:
                weight_bars(mc["weights"], fk["fk_leg_labels"], color=C_GREEN if tag == "safe" else C_ORANGE)

    section_title("Equity-Kurven der FK-Kandidaten (historischer Zeitraum)")
    eq_fk = combine_rebalanced(fk["monte_carlo"][rule_key]["equal"]["weights"], FK_KEYS).resample("W-FRI").last().dropna()
    gr_fk = combine_rebalanced(fk["monte_carlo"][rule_key]["equal_ex_trendpullback"]["weights"], FK_KEYS).resample("W-FRI").last().dropna()
    ro_fk = pd.Series(
        {pd.Timestamp(d): v for d, v in fk_riskopt["weekly_curve"]}
    ).rename("value").rename_axis("date").reset_index()
    df1 = eq_fk.rename("value").rename_axis("date").reset_index(); df1["Serie"] = "Equal-Weight"
    df2 = gr_fk.rename("value").rename_axis("date").reset_index(); df2["Serie"] = "Ohne Trend Pullback"
    ro_fk["Serie"] = "Risiko-optimiert"
    df_fk = pd.concat([df1, df2, ro_fk])
    st.altair_chart(
        line_chart(df_fk, {"Equal-Weight": (C_GREEN, None), "Ohne Trend Pullback": (C_ORANGE, None), "Risiko-optimiert": (C_BLUE, None)}),
        use_container_width=True,
    )
    st.caption(
        f"Historischer Verlauf {fk['common_window']['start']} bis {fk['common_window']['end']} (Zeitraum, in dem OU-Modell-FK-Daten "
        "vorliegen) -- die Monte-Carlo-Werte oben simulieren daraus 500 Handelstage in die Zukunft, nicht diesen Chart direkt."
    )

# ============================================================ Tab: EK-Schnellkonto
with tab_ekfast:
    ekfast = load_json("ek_fast_account.json")
    st.caption("Sonderfall: kleines EK-Konto, Ziel moeglichst schnell +7% bei max. 7% Gesamt-Drawdown -- alle 7 EK-Strategien, kein Tageslimit.")
    st.markdown(
        "<span class='pc-rule-badge'>Gesamt-Drawdown <b>7%</b></span>"
        "<span class='pc-rule-badge'>Gewinnziel <b>7%</b></span>"
        "<span class='pc-rule-badge'>Kein Tageslimit</span> "
        "&mdash; gleiche Monte-Carlo-Methodik wie beim FK-Portfolio, aber auf die volle 7-Strategien-EK-Palette angewandt.",
        unsafe_allow_html=True,
    )

    EKFAST_TITLES = {"maxsharpe": "Max-Sharpe (empfohlen)", "riskparity": "Risk-Parity (ultra-sicher)"}
    col1, col2 = st.columns(2)
    for col, cand_key, tag, tag_label in [(col1, "maxsharpe", "fast", "empfohlen"), (col2, "riskparity", "safe", "ultra-sicher")]:
        mc = ekfast["monte_carlo"][cand_key]
        hist = ekfast["historical_metrics"][cand_key]
        with col:
            st.markdown(
                f"<div class='pc-candidate'><div class='pc-candidate-head'>"
                f"<span class='pc-candidate-title'>{EKFAST_TITLES[cand_key]}</span>"
                f"<span class='pc-candidate-tag {tag}'>{tag_label}</span></div></div>",
                unsafe_allow_html=True,
            )
            outcome_bar(mc["p_target"], mc["p_neither"], mc["p_breach"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Median Tage bis Ziel", f"{mc['median_days_to_target']:.0f}" if mc["median_days_to_target"] else "—")
            c2.metric("Sharpe (historisch)", f"{hist['sharpe']:.2f}")
            c3.metric("MaxDD (historisch)", f"{hist['max_dd_pct']:.1f}%")
            weight_bars(mc["weights"], ekfast["ek_leg_labels"], color=C_ORANGE if tag == "fast" else C_GREEN)

    section_title("Equity-Kurven")
    ekfast_curves = {}
    for key in ["maxsharpe", "riskparity"]:
        if key == "riskparity":
            w = ekfast["monte_carlo"]["riskparity"]["weights"]
            curve = combine_rebalanced(w, EK_KEYS).resample("W-FRI").last().dropna()
        else:
            pts = load_json("ek_fast_maxsharpe_curve.json")
            curve = pd.Series({pd.Timestamp(d): v for d, v in pts})
        ekfast_curves[key] = curve
    df1 = ekfast_curves["maxsharpe"].rename("value").rename_axis("date").reset_index(); df1["Serie"] = "Max-Sharpe"
    df2 = ekfast_curves["riskparity"].rename("value").rename_axis("date").reset_index(); df2["Serie"] = "Risk-Parity"
    df_ekfast = pd.concat([df1, df2])
    st.altair_chart(line_chart(df_ekfast, {"Max-Sharpe": (C_BLUE, None), "Risk-Parity": (C_GREEN, None)}), use_container_width=True)
    st.caption(
        "Max-Sharpe erreicht bei diesem strengeren 7%/7%-Ziel eine hoehere Zielerreichungsrate (96,5% vs. 96,0%) "
        "und ist deutlich schneller (Median 187 vs. 200 Tage) bei nur minimal hoeherer Bruch-Wahrscheinlichkeit "
        "(0,33% vs. 0,33% -- praktisch identisch) -- klare Empfehlung fuer dieses Szenario."
    )

# ============================================================ Tab: Caveats
with tab_caveats:
    st.markdown(
        """
- **"Risiko-optimiert" (FK-Tab) erhoeht das Risiko/Trade JE STRATEGIE** (Gold ASB 1%->2%, BTC 1%->2%,
  OU-Modell 1%->1,5%, CLS Practical 1%->1,5%, Trend Pullback 0,10%->0,50%), nicht den Kapitalanteil --
  Ergebnis eines gemeinsamen Suchlaufs (Gewicht x Risikostufe je Strategie) ueber 32 Kombinationen mit
  geteiltem Monte-Carlo-Bootstrap. Bei praktisch gleicher Bruch-Wahrscheinlichkeit (TTP 3,5% vs. 3,4% Referenz)
  steigt die Zielerreichung von 77%->93% und die Zeit bis zum Ziel sinkt um ~30%. Bestaetigt die These, dass
  einzelne Strategien wegen der geringen Trade-Ueberschneidung (siehe Trade-Overlap-Tab) mehr Risiko vertragen
  als ihre jeweils fuer sich genommen "sichere" Kalibrierung nahelegt.
- **OU-Modell wird durchgaengig NUR mit S&P500 betrachtet** (Nasdaq-100/DAX raus, deren echter Out-of-Sample-
  Sharpe liegt nahe Null/negativ -- nur S&P500 hat einen echten OOS-Edge). Dadurch ist die Einzelkurve
  volatiler/drawdown-staerker als eine ueber 3 Maerkte diversifizierte Version waere (solo MaxDD -37,6% EK,
  -26,7% FK-Teilmenge) -- die Portfolio-Korrelation faengt das aber weitgehend auf. Im FK-Track zusaetzlich nur
  die TTP-handelbare Ticker-Teilmenge (58 von 147 OU-selektierten S&P500-Tickern).
- **Trend Pullback traegt bei FK1's tatsaechlichem 0,10%-Risiko kaum noch messbar zum Portfolio bei**
  (CAGR nur 0,71% solo) -- sein Diversifikations-Nutzen (sehr niedrige Korrelation) waere bei einer etwas
  hoeheren, aber immer noch FK-konformen Risikostufe vermutlich groesser. Deshalb schneidet "ohne Trend
  Pullback" (Kapital auf die uebrigen 4 verteilt) im FK-Vergleich sogar besser ab als eine reine
  Rendite-Kippung -- offene Stellschraube fuer die naechste Iteration.
- **BTC EMA9/21 ist im FK-Track enthalten, aber noch nie live ausgefuehrt** (Bot steht auf Dry-Run) -- Symbol-
  Verfuegbarkeit auf dem Prop-Konto ist verifiziert, echte Order-Ausfuehrung nicht.
- **Trend-Pullback-Bots (FK1/FK2) laufen aktuell auf einem generischen MetaQuotes-Demo-Server**, nicht auf der
  echten TTP-/IQ-Markets-Plattform -- Broker-Kompatibilitaet ist plausibel, aber nicht live verifiziert.
- **ORB und die rohe Gold-Bitcoin-Dual-Momentum-Variante bleiben komplett draussen** -- keine Evidenz, dass
  TTP/IQ Markets die noetigen Instrumente ueberhaupt anbieten (ORB), bzw. der Drawdown der validierten
  Gold-Bitcoin-Version sprengt jede Prop-Firm-Grenze klar (-18,4% MaxDD solo).
- **Methodik-Hinweis:** EK-/FK-Gewichtungen nutzen taeglich reinvestierte (rebalancierte) Renditen, nicht die
  reine Dollar-Summe der Einzelkurven wie im "Kombinierter Backtest"-Tab -- das entspricht eher, wie die Bots
  in der Praxis Positionsgroessen aus dem aktuellen Kontostand berechnen, ergibt aber leicht andere (meist
  etwas hoehere) Sharpe-Werte als im ersten Tab.
- **Monte-Carlo-Methodik:** Block-Bootstrap (Blockgroesse 20 Handelstage) der historischen Tagesrenditen,
  3.000 simulierte Pfade x 500 Handelstage je Gewichtung/Regelwerk -- keine Garantie fuer die Zukunft, nur
  eine Wahrscheinlichkeitsabschaetzung auf Basis der Vergangenheit.
- **Keine Kapitalkonflikte zwischen gleichzeitig offenen Positionen modelliert** -- jede Strategie simuliert
  mit eigenem $-Buch; ein reales Konto muesste Margin/Kapital zwischen Strategien teilen.
        """
    )
