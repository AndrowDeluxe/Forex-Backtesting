"""Live Log -- Gold Asian-Range Breakout (XAUUSD), 2026-08-17. Gleiches
"Collector laeuft lokal, Seite liest nur committete Daten"-Muster wie
app_pages/cls_practical_live_log.py: scripts/collect_gold_asb_daily_log.py
laeuft lokal und committet gold_asb_logs/daily_log.csv. Anders als bei CLS
liest der Collector direkt den SQLite-State des laufenden Live-Bots
(GoldASB-MT5-Bridge, separates Projekt, DRY_RUN=False -- echtes Pruef-Konto)
statt die Signal-Logik ein zweites Mal nachzubauen (siehe Collector-Docstring)
-- diese Seite zeigt also die tatsaechliche Bot-Wahrheit, kein unabhaengiger
Re-Scan.

Enthaelt ein eingebettetes TradingView-Live-Chart (Standard-Embed-Widget,
kein Login noetig) mit Entry/SL-Overlay fuer das zuletzt scharfgeschaltete
Fenster -- gleiches Prinzip wie app_pages/btc_ema_cross_live_log.py. KEIN
Take-Profit (die Strategie nutzt bewusst nur einen Zeit-Exit statt TP/BE,
siehe GoldASB-MT5-Bridge/config.py-Docstring), daher nur Entry+SL-Linien."""

from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="Gold ASB -- Live Log", page_icon=":material/rss_feed:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_DIR / "gold_asb_logs" / "daily_log.csv"

# --- gleiche Palette wie cls_practical_live_log.py/btc_ema_cross_live_log.py ---
C_BG = "#0a0e14"
C_CARD = "#11151c"
C_BORDER = "#232936"
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
    .block-container {{ padding-top: 2rem; max-width: 1200px; }}
    .gasb-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; }}
    .gasb-caveats b {{ color: {C_TEXT}; }}
    .gasb-alert {{ background: rgba(255,85,85,0.08); border: 1px solid {C_RED};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .gasb-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .gasb-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px; }}
    .gasb-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.5rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .gasb-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .gasb-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .gasb-table {{ width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono',Consolas,monospace;
                font-size: 0.85rem; margin: 0.5rem 0 1.2rem 0; }}
    .gasb-table th {{ text-align: left; color: {C_MUTED}; font-size: 0.7rem; letter-spacing: 0.06em;
                   text-transform: uppercase; padding: 0.6rem 0.9rem; border-bottom: 1px solid {C_BORDER}; }}
    .gasb-table td {{ padding: 0.55rem 0.9rem; border-bottom: 1px solid {C_BORDER}; color: {C_TEXT}; }}
    .gasb-table tr:hover td {{ background: {C_CARD}; }}
    .gasb-badge {{ display: inline-block; padding: 0.15rem 0.55rem; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def section_title(text: str) -> None:
    st.markdown(f"<div class='gasb-section-title'>{text}</div>", unsafe_allow_html=True)


def _fmt(v) -> str:
    return "" if pd.isna(v) else str(v)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='gasb-tile-row'>" + "".join(
        f"<div class='gasb-tile'><div class='gasb-tile-value'>{v}</div><div class='gasb-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


st.markdown("## :material/rss_feed: Gold ASB -- Live Log")
st.warning(
    "**Zeigt den State des echten Live-Bots** (GoldASB-MT5-Bridge, Prop-Firm-"
    "Pruef-Konto BeyondIQCapital, DRY_RUN=False) -- kein Backtest-Snapshot. "
    "Diese Seite liest nur, was der Bot selbst pro Asien-Range-Fenster "
    "entschieden hat (Fuenf-Filter-Kaskade: ADX, Trend-Bias, Silber-"
    "Alignment, Liquiditaet, Fuellverzoegerung).",
    icon=":material/science:",
)
st.page_link("app_pages/asian_range_breakout.py", label="Zur Gold Asian-Range Breakout Strategie-Seite (Backtest)", icon=":material/wb_twilight:")

if not LOG_PATH.exists():
    st.error(
        "Noch kein Scan committed. Lokal `python scripts/collect_gold_asb_daily_log.py` "
        "ausfuehren und `gold_asb_logs/daily_log.csv` committen.",
        icon=":material/error:",
    )
    st.stop()

log = pd.read_csv(LOG_PATH)
if log.empty:
    st.warning("Log-Datei ist leer.", icon=":material/warning:")
    st.stop()

log = log.sort_values("window_end")
latest = log.iloc[-1]
latest_date = pd.Timestamp(latest["window_end"]).date()
days_old = (pd.Timestamp.today().date() - latest_date).days
freshness_color = C_GREEN if days_old <= 1 else (C_ORANGE if days_old <= 4 else C_RED)
st.markdown(
    f"<span style='font-family:monospace; color:{freshness_color};'>&#9679;</span> "
    f"<span style='font-family:monospace; color:{C_MUTED};'>Letztes Fenster: "
    f"<b style='color:{C_TEXT};'>{latest['window_end']}</b> ({days_old} Tag(e) alt) -- {len(log)} Fenster insgesamt geloggt.</span>",
    unsafe_allow_html=True,
)
if days_old > 4:
    st.markdown(
        "<div class='gasb-alert'>&#9888; Scan ist mehr als 4 Tage alt -- lokal neu ausfuehren "
        "(<code>python scripts/collect_gold_asb_daily_log.py</code>) fuer den aktuellen Stand.</div>",
        unsafe_allow_html=True,
    )

section_title(f"Letztes Fenster ({latest['window_end']})")
armed = bool(latest.get("armed") in (True, "True"))
tiles = [
    ("RANGE HIGH", f"{latest.get('range_high', 'n/a')}"),
    ("RANGE LOW", f"{latest.get('range_low', 'n/a')}"),
    ("ADX @ CLOSE", f"{latest.get('adx_at_close', 'n/a')}"),
    ("SCHARFGESCHALTET", "JA" if armed else "nein"),
]
tile_row(tiles)

if armed:
    direction = str(latest.get("direction", "?")).upper()
    st.markdown(
        f"<div class='gasb-alert' style='border-color:{C_GREEN};'>&#128204; "
        f"<b>Setup scharfgeschaltet:</b> {direction} -- "
        f"Entry {latest.get('entry_price', '?')}, SL {latest.get('sl', '?')} "
        f"(Ticket {latest.get('buy_ticket') or latest.get('sell_ticket') or '?'}). "
        f"Kein Take-Profit -- Zeit-Exit 11:00 NY.</div>",
        unsafe_allow_html=True,
    )
else:
    st.caption(f"Kein Setup in diesem Fenster: {latest.get('status', '?')}")

section_title(":material/candlestick_chart: Live-Chart (XAUUSD, M15) -- zum Abgleich von Entry/SL")
st.caption(
    "Oeffentliches TradingView-Standard-Widget, kein Login noetig -- zeigt den echten Live-Kurs. "
    "Ist das letzte Fenster scharfgeschaltet, werden Entry/SL als horizontale Linien direkt im "
    "Chart eingezeichnet."
)

_lines_js = ""
if armed:
    _entry = latest.get("entry_price")
    _sl = latest.get("sl")
    _levels = []
    if pd.notna(_entry) and _entry != "":
        _levels.append((float(_entry), C_GREEN, f"Entry {float(_entry):.2f}"))
    if pd.notna(_sl) and _sl != "":
        _levels.append((float(_sl), C_RED, f"SL {float(_sl):.2f}"))
    _shapes_js = "\n".join(
        f"""
        w.createShape(
          {{ time: Math.floor(Date.now()/1000), price: {price} }},
          {{ shape: "horizontal_line", lock: true, disableSelection: true, disableSave: true,
             overrides: {{ linecolor: "{color}", linewidth: 2, linestyle: 2,
                          showLabel: true, textcolor: "{color}", fontsize: 12,
                          text: "{label}" }} }}
        );"""
        for price, color, label in _levels
    )
    if _shapes_js:
        _lines_js = f"""
      chart.onChartReady(function() {{
        var w = chart.chart();
        {_shapes_js}
      }});
        """

st.iframe(
    f"""
    <div class="tradingview-widget-container" style="height:610px;">
      <div id="gasb_live_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      var chart = new TradingView.widget({{
        "width": "100%",
        "height": 610,
        "symbol": "OANDA:XAUUSD",
        "interval": "15",
        "timezone": "America/New_York",
        "theme": "dark",
        "style": "1",
        "locale": "de_DE",
        "toolbar_bg": "#0a0e14",
        "enable_publishing": false,
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": false,
        "container_id": "gasb_live_chart"
      }});
      {_lines_js}
      </script>
    </div>
    """,
    height=630,
)
if armed:
    st.caption(
        "Hinweis: die eingezeichneten Linien werden bei jedem Seiten-Reload neu (auf 'jetzt') "
        "gesetzt, da das kostenlose TradingView-Widget keine feste Zeitachsen-Verankerung fuer "
        "Zeichnungen unterstuetzt -- Preis-Level sind exakt, die horizontale Position/Laenge der "
        "Linie ist rein optisch."
    )

section_title("Historie")
display_log = log.sort_values("window_end", ascending=False).copy()
rows_html = []
for _, r in display_log.iterrows():
    row_armed = r.get("armed") in (True, "True")
    badge = (
        f"<span class='gasb-badge' style='background:rgba(94,203,140,0.15);color:{C_GREEN};'>Scharf</span>"
        if row_armed
        else f"<span class='gasb-badge' style='background:rgba(139,148,158,0.15);color:{C_MUTED};'>uebersprungen</span>"
    )
    rows_html.append(
        f"<tr><td>{_fmt(r.get('date'))}</td><td>{_fmt(r.get('range_high'))}</td>"
        f"<td>{_fmt(r.get('range_low'))}</td><td>{_fmt(r.get('adx_at_close'))}</td>"
        f"<td>{badge}</td><td>{_fmt(r.get('direction')).upper()}</td>"
        f"<td>{_fmt(r.get('entry_price'))}</td><td>{_fmt(r.get('sl'))}</td>"
        f"<td>{_fmt(r.get('status'))}</td></tr>"
    )
table_html = f"""
<table class="gasb-table">
  <thead><tr>
    <th>Datum</th><th>Range High</th><th>Range Low</th><th>ADX</th><th>Status</th><th>Richtung</th>
    <th>Entry</th><th>SL</th><th>Detail</th>
  </tr></thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
"""
st.markdown(table_html, unsafe_allow_html=True)
