"""NY-Open Opening-Range-Breakout -- 3-Instrumente-Portfolio (SP500 + US30 +
NASDAQ), Ergebnis der Forschungsreihe in knowledge/projects/ny-open-orb-sp500.md
(Stage 1-5 + Phase 6). Ersetzt die alte app_pages/orb_strategy.py (Tages-ATR-
Schwellen-ORB): dieselbe Grundidee (erste Kerze nach Handelsstart als Range),
aber auf dem NY-Open (09:30 America/New_York) statt einer Tages-Open-ATR-
Schwelle, mit je Instrument eigener, IS/OOS-validierter Config statt einem
uebertragenen Filter. Verworfen wurde die alte Strategie, weil sie weder
solo noch risiko-gewichtet kombiniert einen Mehrwert gegenueber dieser
brachte (Stage 5a: Risk-Parity-Blend schlaegt ny_open_orb allein nicht, OOS).

Jedes Instrument hat seine EIGENE Config (nicht blind uebertragen -
NASDAQ generalisiert den SP500-Filter nachweislich nicht, siehe Stage 4e):
  - SP500 / US30: long-only + EMA-Ribbon-Bias neutral (strategy/mtf_ema_ribbon.py)
  - NASDAQ: long+short + ohne Mittwoch
Alle drei: 15-Min-Range (range_bars=1), ATR-Stop 0.6x, M5-Ausfuehrung, PLUS
(Stage 6, seit 2026-08-27 Standard) Teil-Ausstieg: ein Teil der Position
wird frueh realisiert, der Rest laeuft mit Stop auf Breakeven weiter -
verbessert Sharpe/Win-Rate/MaxDD bei SP500/US30 auf praktisch jeder
Kennzahl. SP500/US30 laesst die Restposition weiter zum 4R-Ziel laufen;
NASDAQ (Stage 8/9, seit 2026-09-01 Standard) laesst die Restposition
stattdessen bis zum Handelsschluss laufen (EOD-Exit statt 4R-Cap) - schlaegt
das 4R-Cap auf Sharpe, CAGR und Walk-Forward-Konsistenz gleichzeitig, per
Phase 6 bestaetigt. Siehe knowledge/projects/ny-open-orb-sp500.md Stage 6/8/9.

WICHTIG: dies ist die Backtest-/Research-Dashboardseite, KEIN Live-Bot. Der
Live-Bot mit ORB-Bein (challenge_portfolio/paper_bot.py, live importiert von
Funded-Portfolio-Bridge/run_once.py) hat eine EIGENE, unabhaengige
ORB_EXIT_CFG (aktuell noch ohne Teilausstieg ueberhaupt) - eine Aenderung
hier wirkt sich NICHT automatisch auf das Live-System aus, siehe
knowledge/projects/ny-open-orb-sp500.md, Abschnitt "Live-Bridge-Abgleich".
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import altair as alt
import streamlit as st
from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import annualized_sharpe, calmar_ratio, cagr as cagr_fn, equity_curve, max_drawdown, summarize

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "ou_paper_backtest"))
from monte_carlo import run_monte_carlo  # noqa: E402

st.set_page_config(page_title="NY-Open ORB Portfolio", page_icon=":material/bolt:", layout="wide")

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"
STARTING_EQUITY = 10_000.0

# Stage 6 (2026-08-27): partial-exit standardized per instrument - SP500/US30
# bank 50% at 2R (genuine improvement on every metric), rest runs to a 4R cap.
# NASDAQ (Stage 8/9, 2026-09-01): banks 50% at 1.5R, but the remainder now
# rides to session close (target_mode=None) instead of a 4R cap - Phase 6
# confirmed this beats the old 4R-cap version on Sharpe (median MC 1.42->1.55),
# CAGR (2.7%->3.8% full-history), and walk-forward consistency, while keeping
# P(MaxDD>5%) low (0.7%, vs. 29.1% for a pure EOD-exit without the partial
# leg) - see knowledge/projects/ny-open-orb-sp500.md Stage 8/9.
EXIT_CFG_BY_INSTRUMENT = {
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode=None, partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
}

INSTRUMENT_CONFIG = {
    "SP500": "Long-only + EMA-Ribbon neutral + 2R/50%-Teilausstieg",
    "US30": "Long-only + EMA-Ribbon neutral + 2R/50%-Teilausstieg",
    "NASDAQ": "Long+Short + ohne Mittwoch + 1.5R/50%-Teilausstieg + EOD-Exit (statt 4R-Cap)",
}


@st.cache_data(ttl="1h", show_spinner="Berechne Trades...", max_entries=3)
def run_backtest(instrument: str):
    """Fetches, builds the execution frame, and simulates - all internal to
    one cached call. Returns only (index, trades), NOT the full M5 execution
    frame: the page never plots raw candles, only equity curves derived from
    `trades`, so keeping the whole frame (ATR/ADX/RVOL/fractal columns across
    ~650k M5 bars per instrument) cached would multiply memory for nothing -
    a real contributor to Streamlit Cloud's recurring resource-limit hits."""
    m15 = fetch_m15(instrument, START, END)
    m5 = fetch_m5(instrument, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")

    if instrument == "NASDAQ":
        entries = filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
    else:
        long_entries = filters.filter_by_direction(all_entries, 1)
        bias = regime.ema_trend_bias(m15, frame["session"].unique())
        bias_vals = filters.values_at(long_entries, bias)
        entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))

    trades = simulate(frame, entries, **EXIT_CFG_BY_INSTRUMENT[instrument])
    return frame.index, trades


@st.cache_data(ttl="1h", show_spinner="Baue Portfolio...")
def build_portfolio():
    daily = {}
    for instrument in INSTRUMENT_CONFIG:
        index, trades = run_backtest(instrument)
        d = trades_to_daily_returns(trades, index)
        d.index = d.index.tz_localize(None)
        daily[instrument] = d

    common = daily["SP500"].index
    for s in daily.values():
        common = common.union(s.index)
    for k in daily:
        daily[k] = daily[k].reindex(common, fill_value=0.0)

    split_ts = pd.Timestamp(SPLIT_DATE)
    is_mask = common < split_ts
    df = pd.DataFrame(daily)
    corr = df.corr()

    equal = df.mean(axis=1)
    vols_is = df[is_mask].std()
    inv_vol = 1 / vols_is
    weights = (inv_vol / inv_vol.sum()).to_dict()
    riskpar = sum(weights[k] * df[k] for k in df.columns)

    return df, corr, equal, riskpar, weights, split_ts


def fmt_pct(x: float) -> str:
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt_num(x: float) -> str:
    return f"{x:.2f}" if pd.notna(x) else "n/a"


def stats_row(label: str, daily: pd.Series) -> dict:
    return {
        "Variante": label, "Sharpe": fmt_num(annualized_sharpe(daily)), "Calmar": fmt_num(calmar_ratio(daily)),
        "CAGR": fmt_pct(cagr_fn(daily)), "MaxDD": fmt_pct(max_drawdown(daily)),
    }


def equity_chart(series_dict: dict[str, pd.Series]) -> alt.Chart:
    rows = []
    for label, daily in series_dict.items():
        eq = equity_curve(daily) * STARTING_EQUITY
        for ts, v in eq.items():
            rows.append({"Datum": ts, "Kapital": v, "Serie": label})
    chart_df = pd.DataFrame(rows)
    return (
        alt.Chart(chart_df)
        .mark_line()
        .encode(x="Datum:T", y=alt.Y("Kapital:Q", scale=alt.Scale(zero=False)), color="Serie:N")
        .properties(height=380)
    )


# ==================================================================== Seite
st.markdown("## :material/bolt: NY-Open ORB -- SP500 + US30 + NASDAQ Portfolio")
st.success(
    "Ersetzt die alte Tages-ATR-Schwellen-ORB-Strategie (verworfen: brachte weder solo noch "
    "risiko-gewichtet kombiniert einen Mehrwert). Jedes Instrument hat seine eigene, "
    "IS/OOS-validierte Config -- Details siehe Tab \"Weg dorthin\".",
    icon=":material/check_circle:",
)

df, corr, equal, riskpar, weights, split_ts = build_portfolio()
oos_mask = df.index >= split_ts

st.markdown("### Portfolio (gleichgewichtet), Out-of-Sample seit 2021-07-28")
with st.container(horizontal=True):
    s = {
        "sharpe": annualized_sharpe(equal[oos_mask]), "calmar": calmar_ratio(equal[oos_mask]),
        "cagr": cagr_fn(equal[oos_mask]), "maxdd": max_drawdown(equal[oos_mask]),
    }
    st.metric("Sharpe (ann.)", fmt_num(s["sharpe"]), border=True)
    st.metric("Calmar", fmt_num(s["calmar"]), border=True)
    st.metric("CAGR", fmt_pct(s["cagr"]), border=True)
    st.metric("Max Drawdown", fmt_pct(s["maxdd"]), border=True)

st.space("medium")

tab_portfolio, tab_sp500, tab_us30, tab_nasdaq, tab_history = st.tabs(
    [":material/pie_chart: Portfolio", ":material/candlestick_chart: SP500", ":material/candlestick_chart: US30",
     ":material/candlestick_chart: NASDAQ", ":material/history: Weg dorthin"],
    on_change="rerun",
)


def _render_portfolio():
    st.markdown("#### Korrelation der taeglichen Renditen (volle Historie)")
    st.dataframe(corr.round(3))
    st.caption(
        "NASDAQ korreliert nur schwach mit SP500/US30 (fahren eine strukturell andere Config: "
        "Long+Short statt Long-only) -- echtes Diversifikationspotential, kein Zufall."
    )

    st.markdown("#### Gleichgewichtet vs. Risk-Parity vs. NASDAQ allein (OOS)")
    rows = [
        stats_row("NASDAQ allein", df["NASDAQ"][oos_mask]),
        stats_row("SP500 allein", df["SP500"][oos_mask]),
        stats_row("US30 allein", df["US30"][oos_mask]),
        stats_row("3er gleichgewichtet", equal[oos_mask]),
        stats_row(f"3er Risk-Parity ({', '.join(f'{k}={v:.0%}' for k, v in weights.items())})", riskpar[oos_mask]),
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.markdown("#### Kapitalkurve (OOS, Start 10.000)")
    st.altair_chart(
        equity_chart({
            "NASDAQ allein": df["NASDAQ"][oos_mask], "3er gleichgewichtet": equal[oos_mask],
            "3er Risk-Parity": riskpar[oos_mask],
        }),
        width="stretch",
    )

    st.markdown("#### Monte Carlo (3er gleichgewichtet, OOS, block_size=20, n_sims=2000)")
    mc = run_monte_carlo(equal[oos_mask], initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"]
    with st.container(horizontal=True):
        st.metric("Median Sharpe (MC)", fmt_num(float(np.median(s["sharpe"]))), border=True)
        st.metric("P(MaxDD > 5%)", f"{(s['max_drawdown_pct'] < -5.0).mean():.1%}", border=True)
        st.metric("P(MaxDD > 10%)", f"{(s['max_drawdown_pct'] < -10.0).mean():.1%}", border=True)


def _render_instrument(instrument: str):
    index, trades = run_backtest(instrument)
    daily = df[instrument]
    oos_trades = trades[trades["entry_time"] >= pd.Timestamp(SPLIT_DATE, tz=index.tz)]
    oos_index = index[index >= pd.Timestamp(SPLIT_DATE, tz=index.tz)]
    oos_summary = summarize(oos_trades, oos_index)

    st.markdown(f"#### Config: {INSTRUMENT_CONFIG[instrument]}")
    with st.container(horizontal=True):
        st.metric("Sharpe (ann., OOS)", fmt_num(oos_summary["sharpe"]), border=True)
        st.metric("Profit Factor", fmt_num(oos_summary["profit_factor"]), border=True)
        st.metric("Win Rate", f"{oos_summary['win_rate']:.1%}" if oos_summary["n_trades"] else "-", border=True)
        st.metric("Max Drawdown", fmt_pct(oos_summary["max_drawdown"]), border=True)
        st.metric("Trades (OOS)", oos_summary["n_trades"], border=True)

    st.markdown("##### Jaehrliche OOS-Aufschluesselung")
    rows = []
    for year, group in oos_trades.groupby(oos_trades["entry_time"].dt.year):
        year_index = index[index.year == year]
        s = summarize(group, year_index)
        rows.append({"Jahr": year, "n": s["n_trades"], "Sharpe": fmt_num(s["sharpe"]), "PF": fmt_num(s["profit_factor"]), "Win-Rate": f"{s['win_rate']:.1%}", "CAGR": fmt_pct(s["cagr"])})
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.markdown("##### Kapitalkurve (OOS, Start 10.000)")
    st.altair_chart(equity_chart({instrument: daily[oos_mask]}), width="stretch")


def _render_history():
    st.markdown("#### Forschungsverlauf (Details: `knowledge/projects/ny-open-orb-sp500.md`)")
    st.markdown(
        """
| Stage | Kernbefund |
|---|---|
| 1 -- Range-Mechanik | Range bricht an ~99,9% der Tage irgendwann - "nie gebrochen" ist praktisch nicht existent |
| 2 -- Entry-Vergleich | `stop_breakout` gewinnt auf allen 3 Instrumenten |
| 3 -- Exit-Grid | 0,6x-1,0x ATR-Stop + 4R-Target, cross-asset bestaetigt |
| 4 -- Filter/Regime/Timeframes | SP500/US30: Long-only+EMA-neutral hilft stark; **NASDAQ generalisiert das NICHT** |
| Phase 6 | SP500: Edge regimeabhaengig (schwach 2016-2019); NASDAQ: konsistent stark in allen 3 Perioden |
| NASDAQ-Eigenkalibrierung | Long+Short + ohne Mittwoch schlaegt den uebertragenen SP500-Filter deutlich |
| 5a -- Risiko-gewichtete Kombination mit alter ORB-Strategie | Verbessert sich ggue. 50/50, schlaegt aber `ny_open_orb` allein nicht (OOS) - **alte Strategie verworfen** |
| 5b -- 3er-Portfolio vs. NASDAQ allein | Portfolio gewinnt klar: hoeherer Sharpe, MaxDD fast halbiert |
"""
    )
    st.warning(
        "**Wichtige Vorbehalte**: SP500s Edge ist regimeabhaengig (in der ruhigeren 2016-2019-Periode "
        "praktisch flach) - kein All-Wetter-System. Der 0,6x-ATR-Stop wurde auf demselben Datensatz "
        "gefunden, auf dem er hier validiert wird (kein komplett frischer Drittdatensatz). M15-Ausfuehrung "
        "sieht in Rohzahlen staerker aus, ist aber vermutlich ein Backtest-Artefakt (groebere "
        "Stop-Pruefung) - M5 bleibt die empfohlene Ausfuehrung.",
        icon=":material/warning:",
    )
    st.info(
        "Die alte `orb_strategy/`-Seite wurde aus dem Dashboard entfernt (Stage 5a: risiko-gewichtete "
        "Kombination schlaegt `ny_open_orb` allein nicht, OOS-Sharpe 1.05 solo vs. 0.86 im besten Blend). "
        "Der Code bleibt im Repo (`orb_strategy/pipeline.py`), da mehrere historische Research-Skripte "
        "ihn noch referenzieren.",
        icon=":material/info:",
    )


for _tab, _render in [
    (tab_portfolio, _render_portfolio),
    (tab_sp500, lambda: _render_instrument("SP500")),
    (tab_us30, lambda: _render_instrument("US30")),
    (tab_nasdaq, lambda: _render_instrument("NASDAQ")),
    (tab_history, _render_history),
]:
    if _tab.open:
        with _tab:
            _render()
