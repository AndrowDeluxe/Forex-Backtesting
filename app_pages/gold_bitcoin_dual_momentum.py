"""Fertige Strategien -- Gold-Bitcoin Dual Momentum, per Vojtko & Dujava
(2026, Quantpedia): weekly (Wednesday-close) rotation between Gold and
Bitcoin, long whichever had the higher X-week return but only if that
return is also positive, otherwise cash. Structurally unrelated to the Gold
Asian-Range Breakout -- a completely separate weekly cross-asset rotation,
not an intraday single-asset strategy, and not combined with the ASB
anywhere.

Data deviation from the paper (disclosed): the paper trades GLD/IBIT ETFs;
this repo's data stack has no ETF price history, so Gold and Bitcoin are
represented by their own real spot prices instead -- Gold via the existing
Dukascopy XAUUSD feed (combined_strategy.data), Bitcoin via the existing
Binance BTCUSDT feed (auction_playbook.data) already used elsewhere in this
repo. See gold_bitcoin_dual_momentum/ for the backend package and
scripts/research_gold_bitcoin_dual_momentum*.py for the original research.

Dark/monospace styling matches app_pages/fertige_strategien.py (same
palette, same "Fertige Strategien" nav section, prefixed gb- instead of fs-
per that page's established per-page-CSS convention)."""

from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd

import streamlit as st
from gold_bitcoin_dual_momentum.data import fetch_daily_ohlc_gold_btc, fetch_weekly_gold_btc
from gold_bitcoin_dual_momentum.engine import simulate_dual_momentum
from gold_bitcoin_dual_momentum.risk_engine import composite_position, simulate_risk_based

st.set_page_config(page_title="Gold-Bitcoin Dual Momentum", page_icon=":material/currency_bitcoin:", layout="wide")

START, END = "2017-08-20", "2026-07-29"
LOOKBACKS = [1, 2, 3, 4, 6, 8, 12, 20, 24, 28]
COMPOSITE_SET = [4, 8, 12]
WARMUP_WEEKS = 40
VOL_CAP = 0.20
SPLIT_DATE = "2024-02-01"
COST_TIERS = {
    "Eng (institutionell)": {"gold": 5.0, "btc": 15.0},
    "Realistisch (Retail)": {"gold": 10.0, "btc": 30.0},
    "Teuer (App-Broker)": {"gold": 20.0, "btc": 60.0},
}
RECOMMENDED_COST = "Realistisch (Retail)"

TTP_MAX_DAILY_DD = 0.03
TTP_MAX_TOTAL_DD = 0.07
RISK_PCT_SWEEP = [0.0025, 0.005, 0.01, 0.015, 0.02, 0.025]
RECOMMENDED_RISK_PCT = 0.01
RECOMMENDED_ATR_MULT = 3.0
TP_FILTER_SCENARIOS = [
    {"label": "Basis: 3x ATR, Mehrheit, kein TP/BE", "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": None, "be_trigger_r": None},
    {"label": "+ Breakeven 0.5R", "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": None, "be_trigger_r": 0.5},
    {"label": "+ Take-Profit 1.5R", "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": 1.5, "be_trigger_r": None},
    {"label": "+ TP 1.5R + Breakeven 0.5R", "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": 1.5, "be_trigger_r": 0.5},
    {"label": "2x ATR (enger) + TP + BE", "min_agree": 2, "atr_mult": 2.0, "tp_r_mult": 1.5, "be_trigger_r": 0.5},
    {"label": "2x ATR + TP + BE + Unanimous-Filter", "min_agree": 3, "atr_mult": 2.0, "tp_r_mult": 1.5, "be_trigger_r": 0.5},
]

# --- same palette as fertige_strategien.py / ou_scanner.py ---
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
C_GREEN = "#5ecb8c"
C_RED = "#ff5555"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {C_BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1200px; }}
    .gb-writeup {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
                  line-height: 1.7; color: {C_BLUE_SOFT}; margin-bottom: 1rem; }}
    .gb-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; }}
    .gb-caveats b {{ color: {C_TEXT}; }}
    .gb-alert {{ background: rgba(255,140,66,0.08); border: 1px solid {C_ORANGE};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .gb-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .gb-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px;
               transition: border-color 0.15s ease; }}
    .gb-tile:hover {{ border-color: {C_ORANGE}; }}
    .gb-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.75rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .gb-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .gb-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .gb-legend {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.78rem; margin-top: 0.4rem; }}
    .gb-legend span {{ margin-right: 1.4rem; }}
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
    st.markdown(f"<div class='gb-section-title' style='color:{color};'>{text}</div>", unsafe_allow_html=True)


def caveat_box(html: str, alert: bool = False) -> None:
    cls = "gb-alert" if alert else "gb-caveats"
    st.markdown(f"<div class='{cls}'>{html}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='gb-tile-row'>" + "".join(
        f"<div class='gb-tile'><div class='gb-tile-value'>{v}</div><div class='gb-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def legend(items: list[tuple[str, str]]) -> None:
    spans = "".join(f"<span style='color:{color};'>&#9644;&#9644; {label}</span>" for label, color in items)
    st.markdown(f"<div class='gb-legend'>{spans}</div>", unsafe_allow_html=True)


def line_chart(df_long: pd.DataFrame, series_colors: dict[str, tuple[str, tuple[int, int] | None]], height: int = 380):
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


def perf_metrics(weekly_returns: pd.Series) -> dict:
    r = weekly_returns.dropna()
    if len(r) == 0:
        return {"ann_return": np.nan, "ann_vol": np.nan, "sharpe": np.nan, "max_dd": np.nan, "calmar": np.nan, "hit_rate": np.nan, "n_weeks": 0}
    n_years = len(r) / 52
    growth = (1 + r).prod()
    ann_return = growth ** (1 / n_years) - 1
    ann_vol = r.std() * np.sqrt(52)
    sharpe = ann_return / ann_vol if ann_vol > 0 else np.nan
    equity = (1 + r).cumprod()
    max_dd = (equity / equity.cummax() - 1).min()
    calmar = ann_return / abs(max_dd) if max_dd < 0 else np.nan
    hit_rate = (r > 0).mean()
    return {"ann_return": ann_return, "ann_vol": ann_vol, "sharpe": sharpe, "max_dd": max_dd, "calmar": calmar, "hit_rate": hit_rate, "n_weeks": len(r)}


def count_switches(held_position: pd.Series) -> int:
    hp = held_position.dropna()
    return int((hp != hp.shift(1)).iloc[1:].sum())


# ------------------------------------------------------------------ cached data / simulation
@st.cache_data(ttl="6h", show_spinner="Lade Gold/Bitcoin-Wochendaten...")
def load_weekly() -> pd.DataFrame:
    return fetch_weekly_gold_btc(START, END)


@st.cache_data(ttl="6h", show_spinner="Berechne Dual-Momentum-Varianten...")
def run_sweep(_weekly: pd.DataFrame, vol_cap: float | None, cost_bps: dict | None) -> dict[int, pd.Series]:
    out = {}
    for lb in LOOKBACKS:
        sim = simulate_dual_momentum(_weekly, lookback_weeks=lb, vol_cap=vol_cap, switch_cost_bps=cost_bps)
        out[lb] = sim["strategy_return"].iloc[WARMUP_WEEKS:]
    return out


@st.cache_data(ttl="6h", show_spinner="Berechne Buy&Hold-Referenzen...")
def buy_hold_curves(_weekly: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    gold_ret = _weekly["gold"].pct_change().iloc[WARMUP_WEEKS:]
    btc_ret = _weekly["btc"].pct_change().iloc[WARMUP_WEEKS:]
    return gold_ret, btc_ret


def composite(returns_by_lb: dict[int, pd.Series]) -> pd.Series:
    return pd.concat([returns_by_lb[lb] for lb in COMPOSITE_SET], axis=1).mean(axis=1)


def fmt_pct(x: float) -> str:
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt_num(x: float) -> str:
    return f"{x:.2f}" if pd.notna(x) else "n/a"


# ------------------------------------------------------------------ cached: risk-based (TTP) engine
@st.cache_data(ttl="6h", show_spinner="Lade Gold/Bitcoin-Tagesdaten (ATR)...")
def load_daily() -> dict[str, pd.DataFrame]:
    return fetch_daily_ohlc_gold_btc(START, END)


def daily_metrics(daily_returns: pd.Series, equity: pd.Series) -> dict:
    r = daily_returns.dropna()
    if len(r) == 0:
        return {"ann_return": np.nan, "sharpe": np.nan, "max_total_dd": np.nan, "max_daily_loss": np.nan}
    n_years = len(r) / 252
    growth = (1 + r).prod()
    ann_return = growth ** (1 / n_years) - 1
    ann_vol = r.std() * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else np.nan
    dd = equity / equity.cummax() - 1
    return {"ann_return": ann_return, "sharpe": sharpe, "max_total_dd": dd.min(), "max_daily_loss": r.min()}


@st.cache_data(ttl="6h", show_spinner="Berechne TTP-Risiko-Sweep...")
def run_risk_pct_sweep(_weekly: pd.DataFrame, _daily: dict[str, pd.DataFrame]) -> pd.DataFrame:
    decision = composite_position(_weekly, lookbacks=tuple(COMPOSITE_SET), min_agree=2).iloc[WARMUP_WEEKS:]
    rows = []
    for risk_pct in RISK_PCT_SWEEP:
        sim = simulate_risk_based(_daily, decision, risk_pct=risk_pct, atr_mult=RECOMMENDED_ATR_MULT, starting_equity=100_000.0)
        m = daily_metrics(sim["daily_return"], sim["equity"])
        avg_notional = sim.loc[sim["asset"] != "cash", "notional_fraction"].mean()
        daily_ok = m["max_daily_loss"] > -TTP_MAX_DAILY_DD
        total_ok = m["max_total_dd"] > -TTP_MAX_TOTAL_DD
        rows.append({
            "Risiko/Trade": risk_pct, "Return p.a.": m["ann_return"], "Sharpe": m["sharpe"],
            "Max Gesamt-DD": m["max_total_dd"], "Schlechtester Tag": m["max_daily_loss"],
            "Oe. Positionsgroesse": avg_notional, "TTP-konform": "Ja" if (daily_ok and total_ok) else "NEIN",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl="6h", show_spinner="Berechne TP/Breakeven/Filter-Vergleich...")
def run_tp_filter_scenarios(_weekly: pd.DataFrame, _daily: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for sc in TP_FILTER_SCENARIOS:
        decision = composite_position(_weekly, lookbacks=tuple(COMPOSITE_SET), min_agree=sc["min_agree"]).iloc[WARMUP_WEEKS:]
        sim = simulate_risk_based(
            _daily, decision, risk_pct=RECOMMENDED_RISK_PCT, atr_mult=sc["atr_mult"],
            tp_r_mult=sc["tp_r_mult"], be_trigger_r=sc["be_trigger_r"], starting_equity=100_000.0,
        )
        m = daily_metrics(sim["daily_return"], sim["equity"])
        rows.append({
            "Variante": sc["label"], "Return p.a.": m["ann_return"], "Sharpe": m["sharpe"],
            "Max Gesamt-DD": m["max_total_dd"], "Schlechtester Tag": m["max_daily_loss"],
            "Stop-Outs": int(sim["stopped_out_today"].sum()), "TP-Treffer": int(sim["tp_hit_today"].sum()),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl="6h", show_spinner="Berechne empfohlene Risiko-Variante...")
def run_recommended_risk_equity(_weekly: pd.DataFrame, _daily: dict[str, pd.DataFrame]) -> pd.Series:
    decision = composite_position(_weekly, lookbacks=tuple(COMPOSITE_SET), min_agree=2).iloc[WARMUP_WEEKS:]
    sim = simulate_risk_based(_daily, decision, risk_pct=RECOMMENDED_RISK_PCT, atr_mult=RECOMMENDED_ATR_MULT, starting_equity=100_000.0)
    return sim["equity"]


# ------------------------------------------------------------------ header
st.markdown("## :material/currency_bitcoin: Gold-Bitcoin Dual Momentum")
st.caption(
    "Woechentliche (Mittwoch-Schluss) Momentum-Rotation zwischen Gold und Bitcoin -- "
    "Vojtko & Dujava (2026, Quantpedia), \"Dual Momentum Allocation Between Physical Gold "
    "and Bitcoin (Digital Gold)\". Eigenstaendiger Kandidat, strukturell unabhaengig von der "
    "Gold Asian-Range Breakout."
)

caveat_box(
    "<b>&#8505; Datenabweichung vom Original:</b> Das Paper handelt GLD/IBIT-ETFs. Dieser Daten-Stack "
    "hat keine ETF-Historie -- stattdessen echte Spotpreise: Gold ueber die bestehende Dukascopy-"
    "XAUUSD-Quelle, Bitcoin ueber die bestehende Binance-BTCUSDT-Quelle (beide bereits an anderer "
    "Stelle im Repo im Einsatz, kein yfinance). Ausserdem: <b>kein Live-Handel</b> -- diese Seite "
    "zeigt Backtest-Ergebnisse, keine automatisierte Ausfuehrung. Broker-/Exchange-Infrastruktur "
    "fuer beide Assets gleichzeitig ist noch nicht geklaert.",
)

with st.expander(":material/menu_book: Methodik", expanded=False):
    st.markdown(
        """
        <div class="gb-writeup">
        Jede Woche (Mittwoch-Schluss) wird entschieden, ob Gold, Bitcoin oder gar nichts (Cash)
        gehalten wird, basierend auf zwei kombinierten Bedingungen:
        </div>
        <div class="gb-caveats">
        <b>1. Relatives Momentum:</b> Welches der beiden Assets lief ueber die letzten X Wochen
        staerker?<br>
        <b>2. Absolutes Momentum:</b> Ist diese Rendite auch tatsaechlich positiv? (Verhindert,
        dass man "das bessere von zwei fallenden Assets" haelt)<br><br>
        Nur wenn beides zutrifft, wird das staerkere Asset gehalten -- sonst Cash (0% in dieser
        Woche). Die Entscheidung am Mittwoch-Schluss der Woche i nutzt nur Daten bis
        einschliesslich i und wird erst in der <b>folgenden</b> Woche (i&rarr;i+1) realisiert --
        kein Lookahead.<br><br>
        <b>Vol-Kappung:</b> Positionsgroesse = min(20% / realisierte 12-Wochen-Vol des gewaehlten
        Assets, 100%) -- nie Hebel, nur Reduktion in Bitcoin-Crash-Phasen.<br><br>
        <b>Composite:</b> Die empfohlene Variante mittelt die Ergebnisse dreier Lookback-Fenster
        (X=4/8/12 Wochen) statt sich auf einen einzelnen "besten" Wert festzulegen -- robuster
        gegen In-Sample-Ueberanpassung.<br><br>
        <b>Kosten:</b> Ein Round-Trip-Kostensatz pro Asset wird nur bei tatsaechlichem
        Assetwechsel (Cash&harr;Gold&harr;Bitcoin) angesetzt, skaliert mit der jeweiligen
        Positionsgroesse -- nicht bei jeder woechentlichen Vol-Cap-Neugewichtung derselben
        Position.
        </div>
        """,
        unsafe_allow_html=True,
    )

weekly = load_weekly()
sweep_no_cost = run_sweep(weekly, VOL_CAP, None)
sweep_pure = run_sweep(weekly, None, None)
recommended = composite(sweep_no_cost)
gold_bh, btc_bh = buy_hold_curves(weekly)

tab_equity, tab_sweep, tab_costs, tab_oos, tab_risk = st.tabs([
    ":material/show_chart: Equity-Kurve",
    ":material/tune: Parameter-Sweep",
    ":material/payments: Kosten-Sensitivitaet",
    ":material/warning: Out-of-Sample",
    ":material/shield: TTP-Risikomanagement",
])

# ------------------------------------------------------------------ Tab: Equity curve
with tab_equity:
    m = perf_metrics(recommended)
    m_gold = perf_metrics(gold_bh)
    m_btc = perf_metrics(btc_bh)
    tile_row([
        ("RETURN P.A.", fmt_pct(m["ann_return"])),
        ("SHARPE", fmt_num(m["sharpe"])),
        ("MAX DRAWDOWN", fmt_pct(m["max_dd"])),
        ("CALMAR", fmt_num(m["calmar"])),
        ("HIT-RATE", fmt_pct(m["hit_rate"])),
        ("WOCHEN", str(m["n_weeks"])),
    ])

    section_title("Empfohlene Variante: Vol-capped (20%) Composite (X=4/8/12 Wochen), ohne Handelskosten")
    equity_curve = (1 + recommended).cumprod()
    gold_curve = (1 + gold_bh).cumprod()
    btc_curve = (1 + btc_bh).cumprod()
    curve_long = pd.concat([
        normalize(equity_curve, "Dual Momentum"),
        normalize(gold_curve, "Gold Buy&Hold"),
        normalize(btc_curve, "Bitcoin Buy&Hold"),
    ])
    st.altair_chart(line_chart(curve_long, {
        "Dual Momentum": (C_ORANGE, None),
        "Gold Buy&Hold": (C_BLUE_SOFT, (5, 4)),
        "Bitcoin Buy&Hold": (C_MUTED, (2, 2)),
    }))
    legend([("Dual Momentum (vol-capped)", C_ORANGE), ("Gold Buy&Hold", C_BLUE_SOFT), ("Bitcoin Buy&Hold", C_MUTED)])

    st.caption(
        f"Referenz Buy&Hold Gold: Sharpe {fmt_num(m_gold['sharpe'])}, MaxDD {fmt_pct(m_gold['max_dd'])}. "
        f"Referenz Buy&Hold Bitcoin: Sharpe {fmt_num(m_btc['sharpe'])}, MaxDD {fmt_pct(m_btc['max_dd'])}."
    )

# ------------------------------------------------------------------ Tab: Parameter sweep
with tab_sweep:
    caveat_box(
        "X = Lookback-Fenster in Wochen fuer die Momentum-Berechnung. \"Pur\" = ohne Vol-Kappung, "
        "\"Vol-capped\" = mit 20%-Vol-Deckel. Composite (4/8/12w gemittelt) ist die empfohlene, "
        "weniger Hindsight-anfaellige Variante -- die Wahl eines einzelnen \"besten\" X waere "
        "In-Sample-Optimierung."
    )

    rows = []
    for lb in LOOKBACKS:
        mp, mv = perf_metrics(sweep_pure[lb]), perf_metrics(sweep_no_cost[lb])
        rows.append({
            "X (Wochen)": lb,
            "Return p.a. (pur)": mp["ann_return"], "Sharpe (pur)": mp["sharpe"], "MaxDD (pur)": mp["max_dd"],
            "Return p.a. (vol-capped)": mv["ann_return"], "Sharpe (vol-capped)": mv["sharpe"], "MaxDD (vol-capped)": mv["max_dd"],
        })
    m_comp_pure = perf_metrics(composite(sweep_pure))
    m_comp_vol = perf_metrics(recommended)
    rows.append({
        "X (Wochen)": "Composite 4/8/12",
        "Return p.a. (pur)": m_comp_pure["ann_return"], "Sharpe (pur)": m_comp_pure["sharpe"], "MaxDD (pur)": m_comp_pure["max_dd"],
        "Return p.a. (vol-capped)": m_comp_vol["ann_return"], "Sharpe (vol-capped)": m_comp_vol["sharpe"], "MaxDD (vol-capped)": m_comp_vol["max_dd"],
    })
    sweep_df = pd.DataFrame(rows)

    section_title("Sweep ueber alle Lookback-Fenster (ohne Handelskosten)")
    st.dataframe(
        sweep_df,
        hide_index=True,
        column_config={
            "Return p.a. (pur)": st.column_config.NumberColumn(format="+.1%"),
            "Sharpe (pur)": st.column_config.NumberColumn(format="%.2f"),
            "MaxDD (pur)": st.column_config.NumberColumn(format="+.1%"),
            "Return p.a. (vol-capped)": st.column_config.NumberColumn(format="+.1%"),
            "Sharpe (vol-capped)": st.column_config.NumberColumn(format="%.2f"),
            "MaxDD (vol-capped)": st.column_config.NumberColumn(format="+.1%"),
        },
    )

# ------------------------------------------------------------------ Tab: Cost sensitivity
with tab_costs:
    caveat_box(
        "Kosten werden nur bei tatsaechlichem Assetwechsel (Cash&harr;Gold&harr;Bitcoin) angesetzt, "
        "nicht bei jeder woechentlichen Vol-Cap-Neugewichtung. Schaetzwerte, keine konkreten "
        "Broker-Quotes -- die Empfehlung ist die Sensitivitaets-Richtung, nicht die exakte Zahl."
    )

    cost_rows = []
    m_no_cost = perf_metrics(recommended)
    switches_no_cost = sum(count_switches(simulate_dual_momentum(weekly, lb, vol_cap=VOL_CAP)["held_position"].iloc[WARMUP_WEEKS:]) for lb in COMPOSITE_SET)
    cost_rows.append({"Kostenstufe": "Ohne Kosten", "Gold bp": 0, "Bitcoin bp": 0, "Return p.a.": m_no_cost["ann_return"], "Sharpe": m_no_cost["sharpe"], "MaxDD": m_no_cost["max_dd"], "Switches": switches_no_cost})
    for tier_name, costs in COST_TIERS.items():
        sweep_costed = run_sweep(weekly, VOL_CAP, costs)
        ret = composite(sweep_costed)
        mc = perf_metrics(ret)
        n_switch = sum(count_switches(simulate_dual_momentum(weekly, lb, vol_cap=VOL_CAP, switch_cost_bps=costs)["held_position"].iloc[WARMUP_WEEKS:]) for lb in COMPOSITE_SET)
        cost_rows.append({"Kostenstufe": tier_name, "Gold bp": costs["gold"], "Bitcoin bp": costs["btc"], "Return p.a.": mc["ann_return"], "Sharpe": mc["sharpe"], "MaxDD": mc["max_dd"], "Switches": n_switch})
    cost_df = pd.DataFrame(cost_rows)

    section_title("Composite (X=4/8/12w) unter verschiedenen Kostenannahmen")
    st.dataframe(
        cost_df,
        hide_index=True,
        column_config={
            "Return p.a.": st.column_config.NumberColumn(format="+.1%"),
            "Sharpe": st.column_config.NumberColumn(format="%.2f"),
            "MaxDD": st.column_config.NumberColumn(format="+.1%"),
        },
    )
    st.caption(
        "Der Effekt ist klein, weil die Strategie selten handelt (~260 Assetwechsel ueber alle 3 "
        "Teil-Buecher zusammen in ueber 8 Jahren) -- selbst die teure Kostenstufe kostet nur "
        "wenige Sharpe-Punkte."
    )

# ------------------------------------------------------------------ Tab: Out-of-sample
with tab_oos:
    caveat_box(
        f"Split-Datum {SPLIT_DATE} (nicht im Original-Paper enthalten, sondern eine zusaetzliche "
        "Ehrlichkeits-Pruefung nach diesem Repo-Standard) -- IS = alles davor, OOS = alles danach. "
        "Getestet auf der Composite-Variante mit realistischen Kosten "
        f"(Gold {COST_TIERS[RECOMMENDED_COST]['gold']}bp / Bitcoin {COST_TIERS[RECOMMENDED_COST]['btc']}bp Round-Trip)."
    )

    sweep_realistic = run_sweep(weekly, VOL_CAP, COST_TIERS[RECOMMENDED_COST])
    ret_realistic = composite(sweep_realistic)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=weekly.index.tz)
    is_ret = ret_realistic[ret_realistic.index < split_ts]
    oos_ret = ret_realistic[ret_realistic.index >= split_ts]
    m_full, m_is, m_oos = perf_metrics(ret_realistic), perf_metrics(is_ret), perf_metrics(oos_ret)

    tile_row([
        ("SHARPE FULL", fmt_num(m_full["sharpe"])),
        ("SHARPE IS", fmt_num(m_is["sharpe"])),
        ("SHARPE OOS", fmt_num(m_oos["sharpe"])),
        ("RETURN IS", fmt_pct(m_is["ann_return"])),
        ("RETURN OOS", fmt_pct(m_oos["ann_return"])),
        ("MAXDD OOS", fmt_pct(m_oos["max_dd"])),
    ])

    section_title(f"In-Sample (bis {SPLIT_DATE}) vs. Out-of-Sample (ab {SPLIT_DATE})", color=C_GREEN)
    is_curve = (1 + is_ret).cumprod()
    oos_curve = (1 + oos_ret).cumprod()
    oos_long = pd.concat([normalize(is_curve, "In-Sample"), normalize(oos_curve, "Out-of-Sample")])
    st.altair_chart(line_chart(oos_long, {"In-Sample": (C_BLUE, None), "Out-of-Sample": (C_GREEN, None)}))
    legend([("In-Sample", C_BLUE), ("Out-of-Sample", C_GREEN)])

    st.caption(
        "OOS ist hier sogar staerker als IS -- kein klassisches Overfitting-Muster. Einschraenkung: "
        "Bitcoin lief in beiden Perioden strukturell nach oben, ein Teil der OOS-Staerke ist "
        "wahrscheinlich einfach \"mehr Bitcoin-Beta\", nicht nur die Switching-Regel selbst."
    )

# ------------------------------------------------------------------ Tab: TTP risk management
with tab_risk:
    caveat_box(
        "<b>&#9888; Die Vol-capped-Version (andere Tabs) hat KEINE untertaegige Risikokontrolle</b> -- "
        "wird die Position am Mittwoch gesetzt, reagiert sie bis zum naechsten Mittwoch auf nichts, "
        "egal wie stark Bitcoin zwischenzeitlich einbricht. Diese Variante hier ersetzt das durch <b>eine "
        "einzelne kombinierte Wochenentscheidung</b> (Mehrheitsvotum der 4/8/12-Wochen-Lookbacks statt drei "
        "Parallel-Buecher -- realistischer fuer ein echtes Konto), fixed-fractional Risiko auf einen "
        "ATR-Stop, taeglich ueberwacht -- und prueft das Ergebnis gegen echte TTP-Regeln "
        f"({TTP_MAX_DAILY_DD:.0%} max. Tages-Drawdown, {TTP_MAX_TOTAL_DD:.0%} max. Gesamt-Drawdown).",
        alert=True,
    )

    daily = load_daily()
    risk_sweep_df = run_risk_pct_sweep(weekly, daily)
    rec_row = risk_sweep_df[risk_sweep_df["Risiko/Trade"] == RECOMMENDED_RISK_PCT].iloc[0]
    tile_row([
        ("EMPF. RISIKO/TRADE", f"{RECOMMENDED_RISK_PCT:.1%}"),
        ("RETURN P.A.", fmt_pct(rec_row["Return p.a."])),
        ("SHARPE", fmt_num(rec_row["Sharpe"])),
        ("MAX GESAMT-DD", fmt_pct(rec_row["Max Gesamt-DD"])),
        ("SCHLECHTESTER TAG", fmt_pct(rec_row["Schlechtester Tag"])),
        ("TTP-KONFORM", rec_row["TTP-konform"]),
    ])

    section_title(f"Empfohlene Variante: {RECOMMENDED_RISK_PCT:.1%} Risiko/Trade, {RECOMMENDED_ATR_MULT:.0f}x ATR-Stop, kein TP/BE")
    rec_equity = run_recommended_risk_equity(weekly, daily)
    st.altair_chart(line_chart(normalize(rec_equity, "TTP-Risiko-Variante"), {"TTP-Risiko-Variante": (C_GREEN, None)}))

    section_title("Risiko-Sweep (0.25% - 2.5% pro Trade)")
    st.dataframe(
        risk_sweep_df,
        hide_index=True,
        column_config={
            "Risiko/Trade": st.column_config.NumberColumn(format=".2%"),
            "Return p.a.": st.column_config.NumberColumn(format="+.1%"),
            "Sharpe": st.column_config.NumberColumn(format="%.2f"),
            "Max Gesamt-DD": st.column_config.NumberColumn(format="+.1%"),
            "Schlechtester Tag": st.column_config.NumberColumn(format="+.1%"),
            "Oe. Positionsgroesse": st.column_config.NumberColumn(format=".1%"),
        },
    )
    st.caption(
        "Ab ca. 2% Risiko/Trade werden die 3%/7%-TTP-Limits gebrochen. 1.5% liegt noch knapp innerhalb, "
        "nutzt aber im Backtest schon fast den kompletten Spielraum aus -- 1.0% laesst spuerbaren "
        "Sicherheitsabstand fuer Verluste, die schlimmer sind als in der Historie."
    )

    section_title("Kann ein Take-Profit / Breakeven / Konfidenz-Filter den Stop verkleinern?", color=C_RED)
    tp_df = run_tp_filter_scenarios(weekly, daily)
    st.dataframe(
        tp_df,
        hide_index=True,
        column_config={
            "Return p.a.": st.column_config.NumberColumn(format="+.1%"),
            "Sharpe": st.column_config.NumberColumn(format="%.2f"),
            "Max Gesamt-DD": st.column_config.NumberColumn(format="+.1%"),
            "Schlechtester Tag": st.column_config.NumberColumn(format="+.1%"),
        },
    )
    caveat_box(
        "<b>Ehrlicher Befund -- gegen die Intuition:</b> Keine der getesteten Erweiterungen verbessert "
        "die Basis-Variante. Ein <b>Take-Profit schadet</b> (kappt die grossen Gewinnwochen, die den Edge "
        "dieser Momentum-Strategie ausmachen). Der <b>Unanimous-Filter</b> (nur handeln, wenn alle 3 "
        "Lookback-Fenster uebereinstimmen) reduziert nur die Trade-Zahl, ohne zwischen guten und "
        "schlechten Trades zu unterscheiden -- Sharpe faellt. Ein <b>engerer Stop</b> erlaubt zwar "
        "groessere Positionen, bringt aber mehr Whipsaws (deutlich mehr Stop-Outs), was den Zugewinn "
        "wieder auffrisst. Die einfache Basis-Variante (oben) bleibt die beste gefundene Konfiguration."
    )

    with st.expander(":material/info: Praktischer Ablauf auf einem Fremdkapitalkonto (z.B. TTP)", expanded=False):
        st.markdown(
            """
            <div class="gb-caveats">
            <b>Rhythmus:</b> Nur einmal pro Woche (Mittwoch-Schluss) wird das Signal berechnet. Bei einem
            noetigen Wechsel: eine Marktorder platzieren + direkt einen Stop-Loss-Order beim Broker
            anhaengen (kein TP, siehe Befund oben). Den Rest der Woche laeuft die Position automatisch auf
            dem Broker-Stop.<br><br>
            <b>Echte Broker-Stops sind sogar praeziser</b> als die Tagesschluss-Simulation hier, weil sie
            auf echten Kursbewegungen ausloesen -- ausser ueber Markt-Schliesszeiten (Wochenende bei
            Gold/FX), wo weiterhin eine echte Kurs-Luecke bleibt, die kein Stop verhindern kann.<br><br>
            <b>Vor dem Start zu pruefen (nicht im Repo verifizierbar):</b> Bietet der Anbieter Bitcoin
            ueberhaupt als handelbares Instrument an? Wochenend-Haltung erlaubt? Uebernacht-/Swap-Gebuehren
            fuer mehrtaegige CFD-Positionen (hier nicht modelliert, nur Spread-Kosten pro Wechsel)?
            Maximaler Hebel je Instrument (fuer die Umrechnung der Positionsgroesse in Lot-Groessen)?
            </div>
            """,
            unsafe_allow_html=True,
        )
