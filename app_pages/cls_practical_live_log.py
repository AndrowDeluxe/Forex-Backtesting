"""Live Logs -- CLS Practical (EUR/USD), 2026-08-13. Signal-tracking-Vorstufe
VOR dem eigentlichen Live-/Paper-Bot ("wie haette die Strategie heute
entschieden") -- gleiches "Collector laeuft lokal, Seite liest nur committete
Daten"-Muster wie app_pages/ou_scanner.py: scripts/collect_cls_practical_daily_log.py
laeuft lokal (geplant: stuendlich/taeglich waehrend 09:30-12:00 Berlin per
Windows Task Scheduler, Task selbst noch NICHT eingerichtet) und committet
cls_practical_logs/daily_log.csv.

Enthaelt zusaetzlich ein eingebettetes TradingView-Live-Chart (Standard-
Embed-Widget, kein Login noetig -- oeffentliche EUR/USD-Kursdaten), damit die
taeglichen Scan-Ergebnisse direkt visuell gegen den echten Chart geprueft
werden koennen (User-Wunsch 2026-08-13: "ein visuelles Fenster mit Live Chart
an dem ich taeglich die Entries nachvollziehen kann"). Bewusst das simple
Standard-Widget statt eines Screenshot-Workflows (tradingview/screenshot.py) --
das braucht das isolierte, manuell eingeloggte Edge-Profil und laeuft nicht
in Streamlit Cloud, waehrend das Embed-Widget ueberall funktioniert und
tatsaechlich LIVE ist statt eines Snapshots."""

from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="CLS Practical -- Live Log", page_icon=":material/rss_feed:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_DIR / "cls_practical_logs" / "daily_log.csv"

# --- gleiche Palette wie cls_practical_strategy.py ---
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
    .cls-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.5rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .cls-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .cls-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .cls-table {{ width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono',Consolas,monospace;
                font-size: 0.85rem; margin: 0.5rem 0 1.2rem 0; }}
    .cls-table th {{ text-align: left; color: {C_MUTED}; font-size: 0.7rem; letter-spacing: 0.06em;
                   text-transform: uppercase; padding: 0.6rem 0.9rem; border-bottom: 1px solid {C_BORDER}; }}
    .cls-table td {{ padding: 0.55rem 0.9rem; border-bottom: 1px solid {C_BORDER}; color: {C_TEXT}; }}
    .cls-table tr:hover td {{ background: {C_CARD}; }}
    .cls-badge {{ display: inline-block; padding: 0.15rem 0.55rem; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def section_title(text: str) -> None:
    st.markdown(f"<div class='cls-section-title'>{text}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='cls-tile-row'>" + "".join(
        f"<div class='cls-tile'><div class='cls-tile-value'>{v}</div><div class='cls-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


st.markdown("## :material/rss_feed: CLS Practical -- Live Log")
st.markdown(
    "<div class='cls-caveats'>Taegliches Signal-Tracking (\"wie haette die Strategie heute "
    "entschieden\") -- <b>noch kein eigener Live-/Paper-Bot</b>, das ist die Vorstufe dazu. "
    "Zeigt pro Tag den Status der drei Tagesfilter (Break-Richtung, Haelt-09:15-Test, "
    "Cross-Confirmation) und ob der Fractal/CHOCH-Entry-Trigger bereits gefeuert hat. "
    "Kein Live-Datenabruf aus Streamlit Cloud -- der Scan laeuft lokal "
    "(<code>python scripts/collect_cls_practical_daily_log.py</code>) und wird committed, "
    "exakt wie die OU-Modell-Live-Logs-Seite.</div>",
    unsafe_allow_html=True,
)
st.page_link("app_pages/cls_practical_strategy.py", label="Zur CLS Practical Strategie-Seite (Backtest)", icon=":material/military_tech:")

if not LOG_PATH.exists():
    st.error(
        "Noch kein Scan committed. Lokal `python scripts/collect_cls_practical_daily_log.py` "
        "ausfuehren und `cls_practical_logs/daily_log.csv` committen.",
        icon=":material/error:",
    )
    st.stop()

log = pd.read_csv(LOG_PATH)
if log.empty:
    st.warning("Log-Datei ist leer.", icon=":material/warning:")
    st.stop()

log = log.sort_values("date")
latest = log.iloc[-1]
latest_date = pd.Timestamp(latest["date"]).date()
days_old = (pd.Timestamp.today().date() - latest_date).days
freshness_color = C_GREEN if days_old <= 1 else (C_ORANGE if days_old <= 4 else C_RED)
st.markdown(
    f"<span style='font-family:monospace; color:{freshness_color};'>&#9679;</span> "
    f"<span style='font-family:monospace; color:{C_MUTED};'>Letzter Scan: "
    f"<b style='color:{C_TEXT};'>{latest_date}</b> ({days_old} Tag(e) alt) -- {len(log)} Tag(e) insgesamt geloggt.</span>",
    unsafe_allow_html=True,
)
if days_old > 4:
    st.markdown(
        "<div class='cls-alert'>&#9888; Scan ist mehr als 4 Tage alt -- lokal neu ausfuehren "
        "(<code>python scripts/collect_cls_practical_daily_log.py</code>) fuer den aktuellen Stand.</div>",
        unsafe_allow_html=True,
    )

section_title(f"Heutiger Status ({latest_date})")
if latest.get("status") and pd.notna(latest.get("status")) and str(latest.get("status")).strip():
    st.markdown(f"<div class='cls-alert'>{latest['status']}</div>", unsafe_allow_html=True)
else:
    def _mult_label(field: str) -> str:
        v = latest.get(field)
        return f"{float(v):.2f}x" if pd.notna(v) and str(v) != "" else "n/a"

    tiles = [
        ("BREAK-RICHTUNG", str(latest.get("break_direction", "n/a"))),
        ("HAELT 09:15", "ja" if latest.get("holds_0915") in (True, "True") else ("nein" if latest.get("holds_0915") in (False, "False") else "n/a")),
        ("CROSS-CONFIRMED", "ja" if latest.get("cross_confirmed") in (True, "True") else ("nein" if latest.get("cross_confirmed") in (False, "False") else "n/a")),
        ("ZINS-RISIKO (Long-End)", _mult_label("rate_risk_multiplier")),
        ("ZINS-RISIKO (2Y)", _mult_label("rate_risk_multiplier_2y")),
        ("ZINS-RISIKO (kombiniert)", _mult_label("rate_risk_multiplier_combined")),
        ("GETRIGGERT", "JA" if latest.get("triggered") in (True, "True") else "nein"),
    ]
    tile_row(tiles)
    st.caption(
        "ZINS-RISIKO: empfohlene Positionsgroessen-Skalierung relativ zum Standard-Risiko (1.0x = "
        "normal). Zwei unabhaengige Signale: Long-End (BUND/USTBOND-CFD-Tageskerzen der letzten 2 "
        "Handelstage, siehe cls_practical.rates.compute_daily_rate_risk_multiplier) und das seit "
        "2026-08-21 echte Front-End-2Y-Signal (TVC:DE02Y/US02Y-Renditen des letzten Handelstags, "
        "compute_frontend_2y_risk_multiplier). Kombiniert = Produkt beider Multiplikatoren, in "
        "Tests staerker als jedes Signal allein. Rein informativ, aendert nichts an Entry/SL/TP "
        "oben, nur an der empfohlenen Groesse."
    )

    if latest.get("triggered") in (True, "True"):
        st.markdown(
            f"<div class='cls-alert' style='border-color:{C_GREEN};'>&#128204; "
            f"<b>Signal heute ausgeloest:</b> {latest.get('setup', '?')} {str(latest.get('direction', '?')).upper()} -- "
            f"Entry {latest.get('entry_price', '?')} um {latest.get('entry_time', '?')}, "
            f"SL {latest.get('sl', '?')}, TP {latest.get('tp', '?')}.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("Kein Trigger heute (entweder Tagesfilter nicht erfuellt, oder Fractal/CHOCH noch nicht gefeuert).")

section_title(":material/candlestick_chart: Live-Chart (EUR/USD, M5) -- zum taeglichen Abgleich der Entries")
st.caption(
    "Oeffentliches TradingView-Standard-Widget, kein Login noetig -- zeigt den echten Live-Kurs. "
    "Dient dem visuellen Abgleich: passt der obige Scan-Status (Break-Richtung, Fractal-Trigger) "
    "zu dem, was gerade tatsaechlich auf dem Chart passiert? Ist heute ein Signal getriggert, "
    "werden Entry/SL/TP als horizontale Linien direkt im Chart eingezeichnet."
)

_today_triggered = latest.get("triggered") in (True, "True")
_lines_js = ""
if _today_triggered:
    _entry = latest.get("entry_price")
    _sl = latest.get("sl")
    _tp = latest.get("tp")
    _levels = []
    if pd.notna(_entry):
        _levels.append((float(_entry), C_GREEN, f"Entry {float(_entry):.5f}"))
    if pd.notna(_sl):
        _levels.append((float(_sl), C_RED, f"SL {float(_sl):.5f}"))
    if pd.notna(_tp):
        _levels.append((float(_tp), C_BLUE, f"TP {float(_tp):.5f}"))
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
      <div id="cls_live_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      var chart = new TradingView.widget({{
        "width": "100%",
        "height": 610,
        "symbol": "OANDA:EURUSD",
        "interval": "5",
        "timezone": "Europe/Berlin",
        "theme": "dark",
        "style": "1",
        "locale": "de_DE",
        "toolbar_bg": "#0a0e14",
        "enable_publishing": false,
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": false,
        "container_id": "cls_live_chart"
      }});
      {_lines_js}
      </script>
    </div>
    """,
    height=630,
)
if _today_triggered:
    st.caption(
        "Hinweis: die eingezeichneten Linien werden bei jedem Seiten-Reload neu (auf 'jetzt') "
        "gesetzt, da das kostenlose TradingView-Widget keine feste Zeitachsen-Verankerung fuer "
        "Zeichnungen unterstuetzt -- Preis-Level sind exakt, die horizontale Position/Laenge der "
        "Linie ist rein optisch."
    )

section_title("Historie")
display_log = log.sort_values("date", ascending=False).copy()
rows_html = []
for _, r in display_log.iterrows():
    triggered = r.get("triggered") in (True, "True")
    badge = (
        f"<span class='cls-badge' style='background:rgba(94,203,140,0.15);color:{C_GREEN};'>Signal</span>"
        if triggered
        else f"<span class='cls-badge' style='background:rgba(139,148,158,0.15);color:{C_MUTED};'>kein Trigger</span>"
    )
    detail = f"{r.get('setup', '')} {r.get('direction', '')}".strip() if triggered else (str(r.get("status", "")) if pd.notna(r.get("status")) else "")
    rows_html.append(
        f"<tr><td>{r.get('date', '')}</td><td>{r.get('break_direction', '')}</td>"
        f"<td>{r.get('holds_0915', '')}</td><td>{r.get('cross_confirmed', '')}</td>"
        f"<td>{badge}</td><td>{detail}</td>"
        f"<td>{r.get('entry_price', '')}</td><td>{r.get('sl', '')}</td><td>{r.get('tp', '')}</td></tr>"
    )
table_html = f"""
<table class="cls-table">
  <thead><tr>
    <th>Datum</th><th>Break</th><th>Haelt 09:15</th><th>Cross</th><th>Status</th><th>Setup/Richtung</th>
    <th>Entry</th><th>SL</th><th>TP</th>
  </tr></thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
"""
st.markdown(table_html, unsafe_allow_html=True)
