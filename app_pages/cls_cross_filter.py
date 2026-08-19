"""Strategie Bestandteile -- Cross-Filter (Waehrungspaar-Mehrheitsvotum),
2026-08-19. User-Wunsch: den Cross-Filter separat von der Haupt-CLS-
Practical-Seite sichtbar machen, damit sich taeglich nachvollziehen laesst,
was das Filter-Ergebnis fuer EUR/USD gerade ist und WARUM (welche
Referenzpaare stimmen zu/dagegen), nicht nur das Endergebnis.

WICHTIG (siehe Modul-Docstring von cls_practical/currency_strength.py und
scripts/collect_cls_cross_filter_daily_log.py): das hier ist NICHT der
aktuell live gehandelte Cross-Confirmation-Mechanismus (das bleibt
strategy.cls_advanced.compute_cross_confirmation, USD-only, in
cls_practical/engine.py per Default aktiv). Es ist der 2026-08-18/19 als
Alternative getestete, gleichgewichtete Mehrheits-Cross-Vote
(compute_cross_vote_confirmation), der im Fenster/Schwellen-Sweep auf
EUR/USD KEINEN klaren Mehrwert gegenueber der Baseline zeigte und deshalb
NICHT in den Live-Pfad uebernommen wurde. Diese Seite ist Monitoring/
Research, keine Live-Signal-Quelle -- daher deutlich als solches markiert.

Gleiches "Collector laeuft lokal, Seite liest nur committete Daten"-Muster
wie app_pages/cls_practical_live_log.py: scripts/collect_cls_cross_filter_daily_log.py
laeuft lokal und committet cls_practical_logs/cross_filter_daily_log.csv +
cross_filter_breakdown_log.csv."""

from pathlib import Path

import altair as alt
import pandas as pd

import streamlit as st

st.set_page_config(page_title="Cross-Filter -- Strategiebestandteile", page_icon=":material/hub:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
DAILY_CSV = REPO_DIR / "cls_practical_logs" / "cross_filter_daily_log.csv"
BREAKDOWN_CSV = REPO_DIR / "cls_practical_logs" / "cross_filter_breakdown_log.csv"

# --- gleiche Palette wie cls_practical_live_log.py / cls_practical_strategy.py ---
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


st.markdown("## :material/hub: Cross-Filter -- Waehrungspaar-Mehrheitsvotum")
st.markdown(
    "<div class='cls-caveats'>Fuer EUR/USD: stimmen die anderen Referenzpaare, die EUR oder USD "
    "enthalten, mit der heutigen Break-Richtung ueberein? Jedes Referenzpaar prueft seine eigene "
    "Kursbewegung <b>seit Tagesbeginn (00:00 Berlin)</b> bis zum Halte-Test-Checkpoint (09:00) -- "
    "gleichgewichtete Mehrheitsabstimmung (1 Paar = 1 Stimme), <b>&ge;50% Zustimmung = bestaetigt</b>. "
    "Quelle: <code>cls_practical/currency_strength.py::compute_cross_vote_confirmation</code>.</div>",
    unsafe_allow_html=True,
)
st.warning(
    "**Research/Monitoring, kein Live-Signal.** Dies ist NICHT der aktuell live gehandelte "
    "Cross-Confirmation-Filter (der bleibt USD-only, `strategy.cls_advanced.compute_cross_confirmation`, "
    "unveraendert Teil der Live-Strategie). Dieses Mehrheitsvotum wurde als Alternative getestet "
    "(Fenster Asia/Settle/Tagesbeginn x Schwelle 40/50/60%) und zeigte auf EUR/USD **keinen klaren "
    "Mehrwert** gegenueber der bestehenden Baseline (IS +0.200R -> OOS +0.185R vs. Baseline "
    "IS +0.155R -> OOS +0.397R) -- deshalb nicht in den Live-Pfad uebernommen. Diese Seite dient nur "
    "dazu, das Verhalten des Mechanismus taeglich nachvollziehen zu koennen.",
    icon=":material/science:",
)
st.page_link("app_pages/cls_practical_strategy.py", label="Zur CLS Practical Strategie-Seite (Backtest)", icon=":material/military_tech:")
st.page_link("app_pages/cls_practical_live_log.py", label="Zum eigentlichen Live-Log (echter Live-Filter-Status)", icon=":material/rss_feed:")

if not DAILY_CSV.exists() or not BREAKDOWN_CSV.exists():
    st.error(
        "Noch kein Scan committed. Lokal `python scripts/collect_cls_cross_filter_daily_log.py` "
        "ausfuehren und die beiden `cls_practical_logs/cross_filter_*.csv` committen.",
        icon=":material/error:",
    )
    st.stop()

daily_log = pd.read_csv(DAILY_CSV)
breakdown_log = pd.read_csv(BREAKDOWN_CSV)
if daily_log.empty:
    st.warning("Log-Datei ist leer.", icon=":material/warning:")
    st.stop()

daily_log = daily_log.sort_values("date")
latest = daily_log.iloc[-1]
latest_date = latest["date"]
days_old = (pd.Timestamp.today().date() - pd.Timestamp(latest_date).date()).days
freshness_color = C_GREEN if days_old <= 1 else (C_ORANGE if days_old <= 4 else C_RED)
st.markdown(
    f"<span style='font-family:monospace; color:{freshness_color};'>&#9679;</span> "
    f"<span style='font-family:monospace; color:{C_MUTED};'>Letzter Scan: "
    f"<b style='color:{C_TEXT};'>{latest_date}</b> ({days_old} Tag(e) alt) -- {len(daily_log)} Tag(e) geloggt.</span>",
    unsafe_allow_html=True,
)
if days_old > 4:
    st.markdown(
        "<div class='cls-alert'>&#9888; Scan ist mehr als 4 Tage alt -- lokal neu ausfuehren "
        "(<code>python scripts/collect_cls_cross_filter_daily_log.py</code>) fuer den aktuellen Stand.</div>",
        unsafe_allow_html=True,
    )

section_title(f"Heutiger Status ({latest_date})")
confirmed_val = str(latest.get("confirmed"))
tiles = [
    ("BREAK-RICHTUNG", str(latest.get("break_direction", "n/a"))),
    ("CONFIRM-RATIO", f"{float(latest['confirm_ratio']) * 100:.0f}%" if pd.notna(latest.get("confirm_ratio")) else "n/a"),
    ("ZUSTIMMUNG", f"{int(latest['n_confirm'])}/{int(latest['n_total'])}" if pd.notna(latest.get("n_confirm")) else "n/a"),
    ("BESTAETIGT", "JA" if confirmed_val == "True" else ("nein" if confirmed_val == "False" else "n/a")),
]
tile_row(tiles)

section_title("Referenzpaare heute -- wer stimmt zu, wer dagegen")
today_detail = breakdown_log[breakdown_log["date"] == latest_date].copy()
if today_detail.empty:
    st.caption("Keine Referenzpaar-Details fuer diesen Tag geloggt.")
else:
    today_detail = today_detail.sort_values("checked_currency")
    rows_html = []
    for _, r in today_detail.iterrows():
        agree = str(r["vote_agrees"]) == "True"
        badge = (
            f"<span class='cls-badge' style='background:rgba(94,203,140,0.15);color:{C_GREEN};'>stimmt zu</span>"
            if agree
            else f"<span class='cls-badge' style='background:rgba(255,85,85,0.15);color:{C_RED};'>dagegen</span>"
        )
        move_pct = float(r["move_pct"]) * 100
        move_color = C_GREEN if move_pct > 0 else (C_RED if move_pct < 0 else C_MUTED)
        rows_html.append(
            f"<tr><td>{r['ref_pair']}</td><td>{r['checked_currency']}</td>"
            f"<td style='color:{move_color};'>{move_pct:+.3f}%</td><td>{badge}</td></tr>"
        )
    table_html = f"""
    <table class="cls-table">
      <thead><tr><th>Referenzpaar</th><th>Geprueft fuer</th><th>Move seit 00:00</th><th>Votum</th></tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)
    st.caption(
        "\"Move seit 00:00\" ist die vorzeichenbereinigte Bewegung des Referenzpaars seit Tagesbeginn "
        "(Berlin), positiv = die geprueften Waehrung staerkt sich. \"Votum\" prueft, ob das zur "
        "heutigen EUR/USD-Break-Richtung passt (EUR staerker bei Long, USD schwaecher bei Long, "
        "jeweils umgekehrt bei Short)."
    )

section_title("Historie -- Confirm-Ratio pro Tag")
hist = daily_log.copy()
hist["date"] = pd.to_datetime(hist["date"])
hist["confirm_ratio_pct"] = hist["confirm_ratio"] * 100
hist["confirmed_label"] = hist["confirmed"].map({True: "bestaetigt", "True": "bestaetigt", False: "nicht bestaetigt", "False": "nicht bestaetigt"}).fillna("n/a")

with st.container(border=True):
    chart = (
        alt.Chart(hist)
        .mark_bar()
        .encode(
            x=alt.X("date:T", title="Datum"),
            y=alt.Y("confirm_ratio_pct:Q", title="Confirm-Ratio (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color(
                "confirmed_label:N", title="Status",
                scale=alt.Scale(domain=["bestaetigt", "nicht bestaetigt"], range=[C_GREEN, C_RED]),
            ),
            tooltip=["date:T", "break_direction:N", alt.Tooltip("confirm_ratio_pct:Q", format=".0f"), "n_confirm:Q", "n_total:Q"],
        )
        .properties(height=280)
    )
    rule = alt.Chart(pd.DataFrame({"y": [50]})).mark_rule(color=C_MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart(chart + rule, width="stretch")
    st.caption("Gestrichelte Linie = 50%-Schwelle (aktuell genutzte Bestaetigungs-Grenze).")

section_title("Tages-Tabelle")
display_log = daily_log.sort_values("date", ascending=False).copy()
rows_html = []
for _, r in display_log.iterrows():
    confirmed = str(r.get("confirmed")) == "True"
    badge = (
        f"<span class='cls-badge' style='background:rgba(94,203,140,0.15);color:{C_GREEN};'>bestaetigt</span>"
        if confirmed
        else f"<span class='cls-badge' style='background:rgba(139,148,158,0.15);color:{C_MUTED};'>nicht bestaetigt</span>"
    )
    ratio = f"{float(r['confirm_ratio']) * 100:.0f}%" if pd.notna(r.get("confirm_ratio")) else "n/a"
    rows_html.append(
        f"<tr><td>{r.get('date', '')}</td><td>{r.get('break_direction', '')}</td>"
        f"<td>{r.get('n_confirm', '')}/{r.get('n_total', '')}</td><td>{ratio}</td><td>{badge}</td></tr>"
    )
table_html = f"""
<table class="cls-table">
  <thead><tr><th>Datum</th><th>Break</th><th>Zustimmung</th><th>Ratio</th><th>Status</th></tr></thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
"""
st.markdown(table_html, unsafe_allow_html=True)

section_title("Wie diesen Baustein in eigenem Code nutzen")
st.code(
    "from cls_practical.currency_strength import compute_cross_vote_confirmation, cross_vote_breakdown\n\n"
    "conf = compute_cross_vote_confirmation(\n"
    "    'EURUSD', direction, ref_price_data,\n"
    "    checkpoint_hour=9.0, window='day_start', confirm_threshold=0.5,\n"
    ")\n"
    "# conf['confirmed'] als cross_confirm_override an simulate_cls_practical() geben\n\n"
    "detail = cross_vote_breakdown('EURUSD', direction, ref_price_data, checkpoint_hour=9.0)\n"
    "# Pro-Tag/Pro-Referenzpaar-Aufschluesselung, wie auf dieser Seite gezeigt",
    language="python",
)
