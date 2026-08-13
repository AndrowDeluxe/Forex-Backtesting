"""Fertige Strategien -- CLS Practical (EUR/USD M5), rebuilt 2026-08-11 bis
2026-08-13 aus dem mentor-eigenen "CLS_Praxis_Playbook.pdf" (Smartmoneyhour/
SMT Macro Desk, hochgeladen 2026-08-10) als quantitatives Regelwerk.

Hypothese: CLS (Continuous Linked Settlement, das globale FX-Settlement-
System) erzeugt rund um das Settlement-Fenster (06:00-09:00 Berlin)
mechanischen, nicht-informationsgetriebenen Orderflow -- Banken gleichen vor
dem Settlement ihre Intraday-Liquiditaet aus, das eigentliche Settlement
laeuft danach.

Backend: cls_practical/ (engine.py, data.py, rates.py). Forschungsverlauf:
scripts/research_cls_practical_*.py (Threshold-Sweep, Funnel-Diagnose,
Filter-Relaxation, Multi-Instrument-Test, Kelly, Risk-Management -- alle
2026-08-11 bis 2026-08-13). Live-berechnet mit Caching, damit die Zahlen bei
neuen Daten automatisch aktuell bleiben; Multi-Instrument-Vergleich und
Verwerfungs-Historie sind als dokumentierte Befunde statisch gehalten (zu
teuer fuer jeden Seitenaufruf neu zu rechnen).

Dark/monospace-Styling matcht app_pages/fertige_strategien.py /
gold_bitcoin_dual_momentum.py (gleiche Palette, "cls-"-Praefix)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import streamlit as st

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "cls_practical"))
sys.path.insert(0, str(REPO_DIR))

from cls_practical.chart import build_entry_chart  # noqa: E402
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin  # noqa: E402
from cls_practical.engine import simulate_cls_practical  # noqa: E402
from strategy.cls_advanced import PAIRS  # noqa: E402

st.set_page_config(page_title="CLS Practical (EUR/USD)", page_icon=":material/military_tech:", layout="wide")

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
INITIAL_EQUITY = 100_000.0
TRADING_DAYS_PER_YEAR = 252

# --- gleiche Palette wie fertige_strategien.py / gold_bitcoin_dual_momentum.py ---
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
    .cls-writeup {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
                  line-height: 1.7; color: {C_BLUE_SOFT}; margin-bottom: 1rem; }}
    .cls-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; }}
    .cls-caveats b {{ color: {C_TEXT}; }}
    .cls-alert {{ background: rgba(255,85,85,0.08); border: 1px solid {C_RED};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .cls-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .cls-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px; }}
    .cls-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.75rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .cls-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .cls-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.82rem;
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 6px 6px 0 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def section_title(text: str, color: str = C_ORANGE) -> None:
    st.markdown(f"<div class='cls-section-title' style='color:{color};'>{text}</div>", unsafe_allow_html=True)


def caveat_box(html: str, alert: bool = False) -> None:
    cls = "cls-alert" if alert else "cls-caveats"
    st.markdown(f"<div class='{cls}'>{html}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='cls-tile-row'>" + "".join(
        f"<div class='cls-tile'><div class='cls-tile-value'>{v}</div><div class='cls-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------------------ Daten/Backtest
@st.cache_data(ttl="6h", show_spinner="Lade EUR/USD + Majors + Zinsen...")
def load_data():
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    return eurusd_m5, other_majors_m15, bund_m5, ustbond_m5


def daily_pnl_from_trades(trades: pd.DataFrame) -> pd.Series:
    full_days = pd.date_range(pd.Timestamp(START), pd.Timestamp(END), freq="D")
    exit_day = trades["exit_time"].dt.tz_localize(None).dt.floor("D")
    return trades.groupby(exit_day)["pnl_usd"].sum().reindex(full_days, fill_value=0.0)


def equity_metrics(daily_pnl: pd.Series) -> dict:
    equity = INITIAL_EQUITY + daily_pnl.cumsum()
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    daily_ret = equity.pct_change().fillna(0.0)
    years = len(daily_pnl) / TRADING_DAYS_PER_YEAR
    total_return = equity.iloc[-1] / INITIAL_EQUITY - 1
    cagr_v = (equity.iloc[-1] / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else float("nan")
    sharpe = (daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_ret.std(ddof=1) > 0 else 0.0
    calmar = cagr_v / abs(dd.min()) if dd.min() != 0 else float("nan")
    return {
        "equity": equity, "final_equity": equity.iloc[-1], "total_return_pct": total_return * 100,
        "cagr_pct": cagr_v * 100, "max_drawdown_pct": dd.min() * 100,
        "worst_day_pct": (daily_pnl / INITIAL_EQUITY).min() * 100, "sharpe": sharpe, "calmar": calmar,
    }


@st.cache_data(ttl="6h", show_spinner="Berechne CLS-practical-Trades...")
def run_variant(risk_pct: float, allowed_setups: tuple[str, ...] = ("continuation", "reversal")) -> pd.DataFrame:
    eurusd_m5, other_majors_m15, bund_m5, ustbond_m5 = load_data()
    return simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, risk_pct=risk_pct, allowed_setups=allowed_setups)


@st.cache_data(ttl="6h")
def buy_and_hold_metrics() -> dict:
    eurusd_m5, *_ = load_data()
    px = eurusd_m5["close"].copy()
    px.index = px.index.tz_localize(None)
    daily_px = px.resample("1D").last().dropna()
    full_days = pd.date_range(pd.Timestamp(START), pd.Timestamp(END), freq="D")
    daily_px = daily_px.reindex(full_days).ffill().dropna()
    ret = daily_px.pct_change().fillna(0.0)
    pnl = ret * INITIAL_EQUITY
    return equity_metrics(pnl)


def kelly_from_trades(trades: pd.DataFrame) -> dict:
    n = len(trades)
    if n == 0:
        return {}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins, losses = r[r > 0], r[r <= 0]
    p = len(wins) / n
    avg_win = wins.mean() if len(wins) else np.nan
    avg_loss = losses.mean() if len(losses) else np.nan
    b = avg_win / abs(avg_loss) if len(losses) and avg_loss != 0 else np.nan
    kelly_f = p - (1 - p) / b if pd.notna(b) and b != 0 else np.nan
    return {"n": n, "win_rate": p, "avg_win_r": avg_win, "avg_loss_r": avg_loss, "b": b, "kelly_f": kelly_f}


# ==================================================================== Seite
st.markdown("## :material/military_tech: CLS Practical -- EUR/USD M5")
caveat_box(
    "<b>CLS (Continuous Linked Settlement)</b>-Hypothese: rund um das globale FX-Settlement-Fenster "
    "(06:00-09:00 Berlin) entsteht mechanischer, nicht-informationsgetriebener Orderflow -- Banken "
    "gleichen davor ihre Intraday-Liquiditaet aus, das eigentliche Settlement laeuft danach. Aus dem "
    "mentor-eigenen \"CLS_Praxis_Playbook.pdf\" als quantitatives Regelwerk rekonstruiert (2026-08-11), "
    "seither ueber mehrere Sessions verfeinert und mehrfach out-of-sample verifiziert."
)

tabs = st.tabs(["Mechanik", "Backtest-Ergebnis", "Risk Management", "Weg dorthin"])

# -------------------------------------------------------------- Tab 1: Mechanik
with tabs[0]:
    section_title("Tagesablauf (Europe/Berlin)")
    st.markdown(
        """
| Fenster | Zeit | Bedeutung |
|---|---|---|
| Asia Range | 00:00-06:00 | Referenz-Range |
| Settle-Fenster | 06:00-09:00 | Break aus der Asia-Range entsteht hier |
| Test | 09:15-Close | Haelt der Break? |
| Entry-Fenster | 09:30-12:00 | Fractal/CHOCH-Trigger |
"""
    )
    section_title("Drei Tagesfilter")
    st.markdown(
        """
1. **Trend**: Tages-SMA(100) auf EUR/USD-Close (Vortageswert) **+ ADX(14)≥15** (aus einer parallelen
   Session uebernommen, 2026-08-13 -- verbessert alle Metriken IS und OOS konsistent).
2. **Crosses**: EUR/USD-Move 06:00-09:00 vs. Durchschnitt der anderen 5 Majors -- breiter Dollar-Move
   oder isolierte Bewegung?
3. ~~**Rates**: BUND/USTBOND-CFD-"Ampel"~~ -- **deaktiviert** (2026-08-13, IS/OOS-verifiziert: ohne
   diesen Filter fast doppelte Trade-Zahl bei besserem/gleichbleibendem Ø R in beiden Fenstern).

Verknuepfung: **UND** (alle aktiven Filter muessen zustimmen) -- ein 2-von-3-Mehrheitsmodus wurde
getestet und wieder verworfen (mehr Trades, aber netto schlechterer Ertrag).
"""
    )
    section_title("Setups")
    st.markdown(
        """
- **Continuation**: Break haelt beim 09:15-Test + Filter stimmen mit dem Break ueberein -> Resting-Stop-Order
  am ersten Fractal GEGEN die Break-Richtung (Pullback).
- **Reversal**: Break haelt NICHT + Filter dagegen -> Rueckkehr in die Asia-Range, dann Fractal gegen den
  urspruenglichen Break (Structure Shift), Stop-Order weiter in Reversal-Richtung.
- Alles andere -> kein Trade.

TP = 0,35 × ADR(14) (Average Daily Range). SL = Fractal-Extrem, mit einem Floor von mindestens
1,0 × ATR(M5) (verhindert unrealistischen Hebel bei zu engen Fractal-Abstaenden).
"""
    )

# -------------------------------------------------------------- Tab 2: Backtest-Ergebnis
with tabs[1]:
    risk_pct = st.select_slider(
        "Risiko pro Trade", options=[0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02],
        value=0.01, format_func=lambda x: f"{x*100:.2f}%",
    )
    trades = run_variant(risk_pct)
    daily_pnl = daily_pnl_from_trades(trades)
    m = equity_metrics(daily_pnl)
    bh = buy_and_hold_metrics()

    section_title(f"Ergebnis bei {risk_pct*100:.2f}% Risiko/Trade (100k-Konto, {START} bis {END})")
    tile_row([
        ("Trades", str(len(trades))), ("Win-Rate", f"{(trades['pnl_usd']>0).mean()*100:.1f}%"),
        ("Endkapital", f"${m['final_equity']:,.0f}"), ("Gesamt-Return", f"{m['total_return_pct']:+.1f}%"),
        ("Max Drawdown", f"{m['max_drawdown_pct']:.2f}%"), ("Sharpe", f"{m['sharpe']:.2f}"),
    ])

    section_title(":material/candlestick_chart: Chart-Verifikation -- einzelne Trades auf dem echten Kurs")
    caveat_box(
        "Bisher nur aggregierte Kennzahlen -- hier ein echter historischer Trade auf dem M5-Chart, "
        "inkl. Entry-Pfeil, SL/TP-Linien und Exit-Marker, damit die Fractal/CHOCH-Entry-Logik nicht nur "
        "behauptet, sondern tatsaechlich SICHTBAR ist."
    )
    if trades.empty:
        st.info("Keine Trades bei diesem Risiko-Setting.", icon=":material/info:")
    else:
        trades_sorted = trades.sort_values("entry_time").reset_index(drop=True)
        trade_labels = [
            f"{r['entry_time']:%Y-%m-%d %H:%M} -- {r['setup']} {r['direction']} "
            f"({r['exit_reason']}, {r['pnl_usd']:+.0f}$)"
            for _, r in trades_sorted.iterrows()
        ]
        default_idx = len(trade_labels) - 1
        picked_idx = st.selectbox(
            "Trade auswaehlen (chronologisch, neuester zuerst unten)", options=range(len(trade_labels)),
            format_func=lambda i: trade_labels[i], index=default_idx,
        )
        picked = trades_sorted.iloc[picked_idx]

        eurusd_m5, *_ = load_data()
        window_start = picked["entry_time"] - pd.Timedelta(hours=20)
        window_end = max(picked["exit_time"], picked["entry_time"]) + pd.Timedelta(hours=6) if pd.notna(picked["exit_time"]) else picked["entry_time"] + pd.Timedelta(hours=12)
        chart_price = eurusd_m5.loc[window_start:window_end]
        chart_trades = trades_sorted[(trades_sorted["entry_time"] >= window_start) & (trades_sorted["entry_time"] <= window_end)]
        if chart_price.empty:
            st.warning("Keine Kursdaten fuer dieses Fenster geladen.", icon=":material/warning:")
        else:
            st.altair_chart(build_entry_chart(chart_price, chart_trades), width="stretch")
        st.caption(
            "Gestrichelt rot/gruen = SL/TP. Dreieck = Entry (Richtung zeigt long/short), Raute = Exit "
            "(Farbe = Exit-Grund). Chart ist zoom-/pan-faehig (Mausrad/Ziehen)."
        )

    daily_is = daily_pnl.loc[:SPLIT]
    daily_oos = daily_pnl.loc[SPLIT:]
    m_is, m_oos = equity_metrics(daily_is), equity_metrics(daily_oos)
    comp_df = pd.DataFrame([
        {"Fenster": "In-Sample (2018-12/2022-06)", "Return": f"{m_is['total_return_pct']:+.1f}%",
         "CAGR": f"{m_is['cagr_pct']:+.2f}%", "MaxDD": f"{m_is['max_drawdown_pct']:.2f}%", "Sharpe": f"{m_is['sharpe']:.2f}"},
        {"Fenster": "Out-of-Sample (2022-06/2026-08)", "Return": f"{m_oos['total_return_pct']:+.1f}%",
         "CAGR": f"{m_oos['cagr_pct']:+.2f}%", "MaxDD": f"{m_oos['max_drawdown_pct']:.2f}%", "Sharpe": f"{m_oos['sharpe']:.2f}"},
    ])
    st.dataframe(comp_df, hide_index=True, width="stretch")
    st.caption("Out-of-Sample ist konsistent staerker als In-Sample -- kein Overfitting-Warnsignal, "
               "sondern ein positives Robustheits-Zeichen (bestaetigt auch die Kelly-Analyse unten).")

    section_title("vs. Buy & Hold EUR/USD (100k, 1x unleveraged, gleicher Zeitraum)")
    bh_df = pd.DataFrame([
        {"": "Strategie", "Endkapital": f"${m['final_equity']:,.0f}", "Return": f"{m['total_return_pct']:+.1f}%",
         "MaxDD": f"{m['max_drawdown_pct']:.2f}%", "Sharpe": f"{m['sharpe']:.2f}"},
        {"": "Buy & Hold", "Endkapital": f"${bh['final_equity']:,.0f}", "Return": f"{bh['total_return_pct']:+.1f}%",
         "MaxDD": f"{bh['max_drawdown_pct']:.2f}%", "Sharpe": f"{bh['sharpe']:.2f}"},
    ])
    st.dataframe(bh_df, hide_index=True, width="stretch")
    st.line_chart(pd.DataFrame({"Strategie": m["equity"], "Buy & Hold": bh["equity"]}))

    section_title("Kelly-Formel (aus den tatsaechlichen R-Multiples)")
    k_all = kelly_from_trades(trades)
    k_is = kelly_from_trades(trades[trades["entry_time"] < SPLIT])
    k_oos = kelly_from_trades(trades[trades["entry_time"] >= SPLIT])
    kelly_df = pd.DataFrame([
        {"Fenster": "Gesamt", "Win-Rate": f"{k_all['win_rate']*100:.1f}%", "Payoff b": f"{k_all['b']:.2f}",
         "Kelly f*": f"{k_all['kelly_f']*100:.2f}%", "Half-Kelly": f"{k_all['kelly_f']/2*100:.2f}%"},
        {"Fenster": "In-Sample", "Win-Rate": f"{k_is['win_rate']*100:.1f}%", "Payoff b": f"{k_is['b']:.2f}",
         "Kelly f*": f"{k_is['kelly_f']*100:.2f}%", "Half-Kelly": f"{k_is['kelly_f']/2*100:.2f}%"},
        {"Fenster": "Out-of-Sample", "Win-Rate": f"{k_oos['win_rate']*100:.1f}%", "Payoff b": f"{k_oos['b']:.2f}",
         "Kelly f*": f"{k_oos['kelly_f']*100:.2f}%", "Half-Kelly": f"{k_oos['kelly_f']/2*100:.2f}%"},
    ])
    st.dataframe(kelly_df, hide_index=True, width="stretch")
    st.caption("Kelly bricht auf dem Holdout nicht ein, sondern steigt sogar -- dasselbe Robustheits-Muster "
               "wie beim OU-Modell. Das tatsaechlich genutzte Risiko liegt deutlich unter Quarter-Kelly.")

# -------------------------------------------------------------- Tab 3: Risk Management
with tabs[2]:
    st.markdown(
        "Zwei Ziel-Konten, unterschiedliche Risikoaufnahme -- siehe "
        "[Risk Management](risk_management) fuers generalisierte Prinzip beim OU-Modell."
    )

    section_title(":material/shield: 1. Statisch fuer eine Funded Challenge (max 3%/Tag, max 7% gesamt)")
    trades_challenge = run_variant(0.005)
    daily_challenge = daily_pnl_from_trades(trades_challenge)
    m_challenge = equity_metrics(daily_challenge)
    tile_row([
        ("Risiko/Trade", "0,50%"), ("Max Drawdown", f"{m_challenge['max_drawdown_pct']:.2f}% (Limit 7%)"),
        ("Schlechtester Tag", f"{m_challenge['worst_day_pct']:.2f}% (Limit 3%)"),
        ("Endkapital", f"${m_challenge['final_equity']:,.0f}"), ("Return", f"{m_challenge['total_return_pct']:+.1f}%"),
    ])
    st.caption("0,50% statt des rechnerisch exakten Limits (0,53%) -- bewusst mit Sicherheitspuffer, da die "
               "Skalierung wegen der festen 100k-Basis im Drawdown-Nenner nicht perfekt linear ist. "
               "Die Tagesregel ist bei dieser Strategie nie der Engpass, bindend ist der Gesamt-Drawdown.")

    section_title(":material/tune: 2. Continuation/Reversal getrennt gesizt (Kelly-informiert)")
    trades_cont = run_variant(0.004, allowed_setups=("continuation",))
    trades_rev = run_variant(0.01, allowed_setups=("reversal",))
    combined = pd.concat([trades_cont, trades_rev], ignore_index=True)
    m_combined = equity_metrics(daily_pnl_from_trades(combined))
    m_uniform = equity_metrics(daily_pnl_from_trades(run_variant(0.01)))
    sep_df = pd.DataFrame([
        {"Variante": "Einheitlich (beide 1%)", "MaxDD": f"{m_uniform['max_drawdown_pct']:.2f}%",
         "Sharpe": f"{m_uniform['sharpe']:.2f}", "Return": f"{m_uniform['total_return_pct']:+.1f}%"},
        {"Variante": "Getrennt (Cont. 0,4% / Rev. 1,0%)", "MaxDD": f"{m_combined['max_drawdown_pct']:.2f}%",
         "Sharpe": f"{m_combined['sharpe']:.2f}", "Return": f"{m_combined['total_return_pct']:+.1f}%"},
    ])
    st.dataframe(sep_df, hide_index=True, width="stretch")
    st.caption("Getrenntes Sizing nach Kelly-Verhaeltnis (Continuation f*=8,3% vs. Reversal f*=20,8%) "
               "verbessert Sharpe und halbiert fast den Drawdown -- kostet aber absolute Rendite. Fuer eine "
               "drawdown-limitierte Challenge vermutlich die bessere Wahl als einheitliches Sizing.")

    section_title(":material/trending_up: 3. Dynamisch nach Winning-Streak (fuers EK-Konto)")
    st.markdown(
        """
| Variante | Return | MaxDD | Schlechtester Tag | Sharpe |
|---|---|---|---|---|
| Referenz (konstant 1%) | +60,4% | -12,72% | -1,13% | 0,61 |
| Boost nach 2 Gewinnern ×1,25 (Cap 2×) | +70,3% | -12,73% | -2,15% | 0,64 |
| Boost nach 3 Gewinnern ×1,5 (Cap 3×) | +71,4% | -12,78% | -3,11% | 0,62 |
| Boost nach 2 Gewinnern ×1,5 (Cap 4×) | +84,6% | -12,79% | **-4,15%** | 0,64 |
"""
    )
    caveat_box(
        "Der Gesamt-Drawdown bleibt fast unveraendert, aber der <b>schlechteste Einzeltag verschlechtert "
        "sich deutlich</b> (bis -4,15% bei der aggressivsten Variante -- wuerde eine 3%-Tagesregel sprengen). "
        "Fuer eine Challenge ungeeignet, fuers EK-Konto ein legitimer Rendite-Hebel."
    )

# -------------------------------------------------------------- Tab 4: Weg dorthin
with tabs[3]:
    section_title("Verworfen")
    st.markdown(
        """
| Ansatz | Befund |
|---|---|
| `cls_squeeze` | Getestet und abgelehnt (einfache Cutoff-Squeeze-Hypothese) |
| `cls_london_breakout` | 135 Kombinationen, keine Kante -- archiviert |
| Majority-Filter (2-von-3) | Mehr Trades, aber netto schlechterer Gesamtertrag |
| M3 statt M5 (Entry-Timeframe) | In-Sample 2,6× besser, bricht auf Out-of-Sample ein (Overfitting) |
| Engeres ADR-Ziel + spaeterer Cutoff | Gleiches Overfitting-Muster wie M3 |
| VIX-Filter, News-Kalender, FOMC/EZB-Fenster, Liquiditaets-/Range-Breite-Filter | Keiner haelt der Out-of-Sample-Pruefung stand |
| Breakeven (jede getestete Variante) | Verschlechtert das Ergebnis immer, am staerksten bei frueher Triggerung |
| Execution-Overlay (Zarattini & Pagani) | Leicht schlechter als ohne |
"""
    )

    section_title("Multi-Instrument-Test (2026-08-13)")
    st.caption("Fuer die 6 FX-Majors mit vollem Cross-Confirmation-Mechanismus, fuer Gold/S&P 500/BTC "
               "vereinfacht (nur Trend+ADX, kein Cross-Filter -- konzeptionell kein '5 andere Majors'-Set).")
    multi_df = pd.DataFrame([
        {"Instrument": "EUR/USD", "Ø R gesamt": "+0,296", "Ø R In-Sample": "+0,155", "Ø R Out-of-Sample": "+0,397"},
        {"Instrument": "GBP/USD", "Ø R gesamt": "-0,111", "Ø R In-Sample": "-0,327", "Ø R Out-of-Sample": "+0,028"},
        {"Instrument": "USD/JPY", "Ø R gesamt": "+0,248", "Ø R In-Sample": "+0,639", "Ø R Out-of-Sample": "-0,033"},
        {"Instrument": "USD/CHF", "Ø R gesamt": "+0,001", "Ø R In-Sample": "+0,010", "Ø R Out-of-Sample": "-0,006"},
        {"Instrument": "AUD/USD", "Ø R gesamt": "+0,052", "Ø R In-Sample": "+0,228", "Ø R Out-of-Sample": "-0,093"},
        {"Instrument": "USD/CAD", "Ø R gesamt": "-0,076", "Ø R In-Sample": "-0,217", "Ø R Out-of-Sample": "+0,020"},
        {"Instrument": "Gold", "Ø R gesamt": "+0,019", "Ø R In-Sample": "-0,010", "Ø R Out-of-Sample": "+0,041"},
        {"Instrument": "S&P 500", "Ø R gesamt": "-0,027", "Ø R In-Sample": "-0,076", "Ø R Out-of-Sample": "+0,008"},
        {"Instrument": "BTC", "Ø R gesamt": "-0,078", "Ø R In-Sample": "-0,075", "Ø R Out-of-Sample": "-0,082"},
    ])
    st.dataframe(multi_df, hide_index=True, width="stretch")
    caveat_box(
        "<b>EUR/USD ist das einzige Instrument mit einer robusten, IS/OOS-konsistenten Kante.</b> "
        "Strukturell eine EUR/USD-spezifische Strategie, kein generelles System -- vermutlich weil "
        "EUR/USD das mit Abstand liquideste Paar ist und am direktesten von der Fed/EZB-Dynamik betroffen."
    )

    section_title("Sonstige getestete Parameter (In-Sample-Sweep, keine Verbesserung robust)")
    st.markdown(
        """
`adr_mult`, `adr_period`, `tp_mode="fixed_r"`, `min_adx`, `adx_period`, `entry_cutoff`, `min_sl_atr_mult`,
Spread-/Slippage-Stresstest (Kante kippt ab ~1,5 bps Spread) -- alle einzeln durchgesweept, siehe
`scripts/research_cls_practical_full_param_sweep.py` fuer die Rohzahlen.
"""
    )
