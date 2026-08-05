"""Live-Signale (Scanner) -- reads the committed snapshot from
ou_paper_backtest/scanner.py (run locally, NOT from Streamlit Cloud -- same
"collector runs locally, page only reads committed data" pattern as the OU-Modell
Live-Logs page). Shows which OU-selected tickers, across all three validated
markets (S&P 500, Nasdaq-100, DAX), currently sit below their lower Bollinger band
with the market-wide EMA200 regime filter open -- i.e. would trigger an entry under
the final locked strategy (see "Fertige Strategien" page) as of the last scan.

Point-in-time snapshot only: does not track positions a user might already be
holding from an earlier scan, and position sizing here assumes each signal is the
ONLY open position (the 15%-total-portfolio-risk cap from the backtest isn't
applied, since that requires knowing all other concurrently open positions).

Dark/monospace styling matches app_pages/fertige_strategien.py (same palette, same
"Fertige Strategien" nav section) -- redesigned 2026-08-05 from a plain st.dataframe
to a styled HTML table + summary tiles for visual consistency across the section."""

import datetime as dt
from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="OU-Modell -- Live-Signale", page_icon=":material/radar:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
SIGNALS_PATH = REPO_DIR / "ou_paper_backtest" / "results" / "scanner_signals.csv"

# --- same palette as fertige_strategien.py ---
C_BG = "#0a0e14"
C_CARD = "#11151c"
C_BORDER = "#232936"
C_TEXT = "#f0f6fc"
C_MUTED = "#8b949e"
C_ORANGE = "#ff8c42"
C_BLUE = "#5ec8f8"
C_GREEN = "#5ecb8c"
C_RED = "#ff5555"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {C_BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1200px; }}
    .sc-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .sc-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px; }}
    .sc-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.75rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .sc-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .sc-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: #c9d1d9; margin-bottom: 1.2rem; }}
    .sc-caveats b {{ color: {C_TEXT}; }}
    .sc-alert {{ background: rgba(255,85,85,0.08); border: 1px solid {C_RED};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: #c9d1d9; }}
    .sc-table {{ width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono',Consolas,monospace;
                font-size: 0.85rem; margin: 0.5rem 0 1.2rem 0; }}
    .sc-table th {{ text-align: left; color: {C_MUTED}; font-size: 0.7rem; letter-spacing: 0.06em;
                   text-transform: uppercase; padding: 0.6rem 0.9rem; border-bottom: 1px solid {C_BORDER}; }}
    .sc-table td {{ padding: 0.65rem 0.9rem; border-bottom: 1px solid {C_BORDER}; color: {C_TEXT}; }}
    .sc-table tr:hover td {{ background: {C_CARD}; }}
    .sc-badge {{ display: inline-block; padding: 0.15rem 0.55rem; border-radius: 4px;
                font-size: 0.72rem; font-weight: 600; }}
    .sc-badge-market {{ background: rgba(94,200,248,0.15); color: {C_BLUE}; }}
    .sc-mono-muted {{ color: {C_MUTED}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("## :material/radar: Live-Signale (Scanner)")
st.caption(
    "Alle drei validierten Maerkte (S&P 500, Nasdaq-100, DAX), OU-selektiertes Universum, "
    "finale gesperrte Konfiguration -- kein Tuning hier."
)

caveat_html = (
    "Zeigt, welche OU-selektierten Ticker beim letzten lokalen Scan unter ihrem unteren "
    "Bollinger-Band lagen UND der marktweite EMA200-Regimefilter offen war -- also unter "
    "der finalen Konfiguration einen Long-Einstieg ausgeloest haetten. <b>Kein "
    "Live-Datenabruf aus Streamlit Cloud</b> -- dieser Scan laeuft lokal "
    "(<code>python ou_paper_backtest/scanner.py</code>) und wird committed, exakt wie die "
    "OU-Modell Live-Logs-Seite. Momentaufnahme: verfolgt keine bereits offenen Positionen "
    "aus frueheren Scans; Positionsgroesse geht davon aus, dass jedes Signal die EINZIGE "
    "offene Position ist (das 15%-Gesamtrisiko-Cap aus dem Backtest wird hier nicht angewendet)."
)
st.markdown(f"<div class='sc-caveats'>{caveat_html}</div>", unsafe_allow_html=True)

if not SIGNALS_PATH.exists():
    st.error(
        "Noch kein Scan committed. Lokal `python ou_paper_backtest/scanner.py` "
        "ausfuehren und `ou_paper_backtest/results/scanner_signals.csv` committen.",
        icon=":material/error:",
    )
    st.stop()

signals = pd.read_csv(SIGNALS_PATH)

if signals.empty:
    st.success(
        "Keine aktiven Setups beim letzten Scan -- entweder kein Ticker unter dem "
        "unteren Band, oder der Regimefilter war auf mindestens einem Markt geschlossen.",
        icon=":material/check_circle:",
    )
    st.stop()

scan_date = signals["scan_date"].iloc[0]
days_old = (dt.date.today() - dt.date.fromisoformat(scan_date)).days
freshness_color = C_GREEN if days_old <= 1 else (C_ORANGE if days_old <= 4 else C_RED)
st.markdown(
    f"<span style='font-family:monospace; color:{freshness_color};'>&#9679;</span> "
    f"<span style='font-family:monospace; color:{C_MUTED};'>Letzter Scan: <b style='color:{C_TEXT};'>{scan_date}</b>"
    f" ({days_old} Tag(e) alt) -- {len(signals)} Setup(s) ueber {signals['market'].nunique()} Markt/Maerkte.</span>",
    unsafe_allow_html=True,
)
if days_old > 4:
    st.markdown(
        "<div class='sc-alert'>&#9888; Scan ist mehr als 4 Tage alt -- lokal neu ausfuehren "
        "(<code>python ou_paper_backtest/scanner.py</code>) fuer aktuelle Signale.</div>",
        unsafe_allow_html=True,
    )

tiles = [("SETUPS GESAMT", str(len(signals)))] + [
    (market.split(" ")[0].upper(), str(int((signals["market"] == market).sum())))
    for market in signals["market"].unique()
]
tiles_html = "<div class='sc-tile-row'>" + "".join(
    f"<div class='sc-tile'><div class='sc-tile-value'>{v}</div><div class='sc-tile-label'>{l}</div></div>"
    for l, v in tiles
) + "</div>"
st.markdown(tiles_html, unsafe_allow_html=True)

rows_html = []
for _, r in signals.sort_values(["market", "ticker"]).iterrows():
    regime_badge = (
        f"<span class='sc-badge' style='background:rgba(94,203,140,0.15);color:{C_GREEN};'>offen</span>"
        if r.get("regime_ok", True)
        else f"<span class='sc-badge' style='background:rgba(255,85,85,0.15);color:{C_RED};'>zu</span>"
    )
    conc = r.get("position_size_concentrated_pct", None)
    conc_str = f"{conc:.2f}%" if pd.notna(conc) else "--"
    rows_html.append(
        f"<tr>"
        f"<td><span class='sc-badge sc-badge-market'>{r['market'].split(' ')[0]}</span></td>"
        f"<td><b>{r['ticker']}</b></td>"
        f"<td>{r['close']:.2f}</td>"
        f"<td style='color:{C_ORANGE};'>{r['entry']:.2f}</td>"
        f"<td style='color:{C_RED};'>{r['sl']:.2f}</td>"
        f"<td class='sc-mono-muted'>{r['tp']}</td>"
        f"<td>{r['risk_pct_price']:.2f}%</td>"
        f"<td>{r['position_size_pct']:.2f}%</td>"
        f"<td>{conc_str}</td>"
        f"<td>{regime_badge}</td>"
        f"</tr>"
    )

table_html = f"""
<table class="sc-table">
  <thead><tr>
    <th>Markt</th><th>Ticker</th><th>Kurs</th><th>Entry</th><th>Stop</th><th>Ziel</th>
    <th>SL-Abstand</th><th>Groesse (Risk-based)</th><th>Groesse (Konzentriert)</th><th>Regime</th>
  </tr></thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
"""
st.markdown(table_html, unsafe_allow_html=True)

st.markdown(
    """
    <div class="sc-caveats">
    <b>Groesse (Risk-based)</b> = 1% Equity-Risiko / SL-Abstand, gedeckelt auf 20% Notional.
    <b>Groesse (Konzentriert)</b> = 1/(Anzahl heutiger Setups in diesem Markt), gedeckelt auf
    1/8 -- beide exakt wie im Backtest (<code>portfolio.simulate_bracket_portfolio</code> bzw.
    <code>simulate_concentrated_book</code>).
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='sc-alert'>&#9888; Im echten Out-of-Sample-Test (2025-heute, siehe "
    "<i>Fertige Strategien</i>) lagen BEIDE Sizing-Methoden weit unter Buy&amp;Hold -- "
    "vor blindem Vertrauen in diese Signale erst den OOS-Abschnitt dort lesen.</div>",
    unsafe_allow_html=True,
)
