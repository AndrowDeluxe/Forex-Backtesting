"""Live Log -- EK-Portfolio Paper-Forward-Test, 2026-08-27. Gleiches
"Collector laeuft lokal (Windows Task Scheduler, stuendlich), Seite liest
nur committete Daten"-Muster wie app_pages/btc_ema_cross_live_log.py:
scripts/ek_portfolio_task.ps1 laeuft stuendlich und committet
ek_portfolio_logs/. Diese Seite ruft nie selbst eine Datenquelle auf.

PAPIER-Konto (7 der 8 Beine): $100k Start, Equal-Weight-Kapitalanteil je
Bein (1/8), moderat-aggressive Risikostufen je Trade -- siehe
ek_portfolio/paper_bot.py. OU-Modell ist die Ausnahme: sein Beitrag kommt
aus den ECHTEN taeglichen Kontostaenden zweier live laufender MT5-Konten
(ou_modell_logs/daily_log.csv), keine Simulation."""

import json
from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="EK-Portfolio -- Live Log", page_icon=":material/rss_feed:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_DIR / "ek_portfolio_logs"
STATE_PATH = LOG_DIR / "paper_state.json"
HEARTBEAT_CSV = LOG_DIR / "heartbeat.csv"

LEG_LABELS = {
    "gold_asb": "Gold ASB", "trend_pullback": "Trend Pullback", "btc_ema_cross": "BTC EMA9/21",
    "gold_silver": "Gold-Silber-Divergenz", "cls_practical": "CLS Practical",
    "ctnl_continuation": "CTNL Continuation", "ctnl_reversal": "CTNL Reversal",
    "orb_sp500": "NY-Open ORB (SP500)", "orb_us30": "NY-Open ORB (US30)", "orb_nasdaq": "NY-Open ORB (NASDAQ)",
}
STARTING_EQUITY = 100_000.0

st.page_link("app_pages/portfolio_construction.py", label="Zurueck zu Portfolio-Konstruktion -- EK/FK", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/rss_feed: EK-Portfolio -- Paper-Forward-Test Live Log")
st.warning(
    "**Reines Papier-Konto fuer 7 der 8 Beine -- keine echten Orders.** Gold ASB, Trend Pullback, "
    "BTC EMA9/21, Gold-Silber-Divergenz, CLS Practical, CTNL Edge und NY-Open ORB lassen ihre echten, "
    "bereits validierten Signal-Engines stuendlich auf einem Trailing-Fenster laufen (Windows Task "
    "Scheduler, \"EK-Portfolio-Paper\"). **OU-Modell ist die Ausnahme:** es traegt seine ECHTEN "
    "Tages-Renditen (Konto 1 TTP + Konto 3 Tickmill) bei, da es bereits live mit echtem Kapital handelt "
    "-- siehe ek_portfolio/paper_bot.py fuer die vollstaendige Architektur.",
    icon=":material/science:",
)

if not STATE_PATH.exists():
    st.info("Noch kein Scan gelaufen.", icon=":material/hourglass_empty:")
    st.stop()

state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
heartbeat = pd.read_csv(HEARTBEAT_CSV) if HEARTBEAT_CSV.exists() else pd.DataFrame()

current_equity = float(heartbeat["equity"].iloc[-1]) if not heartbeat.empty else STARTING_EQUITY
current_dd = float(heartbeat["current_dd"].iloc[-1]) if not heartbeat.empty else 0.0
total_return_pct = (current_equity / STARTING_EQUITY - 1) * 100

st.markdown("### Aktueller Status")
cols = st.columns(5)
cols[0].metric("Equity", f"${current_equity:,.0f}", f"{total_return_pct:+.2f}%")
cols[1].metric("Trailing-DD", f"{current_dd:.2%}", help="EOD-Floor: 20% unter dem bisherigen Hoechststand -- Kill-Switch pausiert neue Entries bei Bruch.")
cols[2].metric("Kill-Switch", "AKTIV" if state.get("kill_switch_active") else "ok",
               delta_color="inverse" if state.get("kill_switch_active") else "normal")
cols[3].metric("Trades (7 Beine)", len(state.get("trades", {})))
account_start = state.get("account_start")
cols[4].metric("Konto-Start", pd.Timestamp(account_start).strftime("%Y-%m-%d %H:%M") if account_start else "--")

st.divider()
st.markdown("### :material/timeline: Equity-Kurve (stuendliche Heartbeats)")
if not heartbeat.empty:
    hb = heartbeat.copy()
    hb["date"] = pd.to_datetime(hb["date"])
    st.line_chart(hb.set_index("date")["equity"])
else:
    st.caption("Noch keine Heartbeats vorhanden.")

st.divider()
st.markdown("### Trades je Bein")
trades = state.get("trades", {})
if trades:
    rows = []
    for key, t in trades.items():
        rows.append({
            "Bein": LEG_LABELS.get(t["leg"], t["leg"]),
            "Entry": t["entry_time"],
            "Exit": t["exit_time"],
            "Status": "offen (Mark-to-Market)" if t["exit_reason"] == "data_end" else t["exit_reason"],
            "R-Multiple": round(t["r_multiple"], 2),
        })
    trades_df = pd.DataFrame(rows).sort_values("Entry", ascending=False)
    st.dataframe(trades_df, hide_index=True, width="stretch")

    st.markdown("#### Trades je Bein (Anzahl)")
    per_leg = trades_df["Bein"].value_counts()
    st.bar_chart(per_leg)
else:
    st.caption("Noch keine Trades seit Konto-Start -- die 7 Papier-Beine brauchen erst neue Entries nach dem Start-Zeitpunkt oben.")

st.divider()
st.markdown("### OU-Modell -- echte Tagesrenditen (8. Bein)")
st.caption(
    "Kein Papier-Trade, sondern der taegliche Durchschnitt der ECHTEN Kontostaende von Konto 1 (TTP) "
    "und Konto 3 (Tickmill) -- siehe ou_modell_logs/daily_log.csv, befuellt von "
    "scripts/collect_ou_modell_daily_log.py. Konto 2 (Demo) zaehlt bewusst nicht mit."
)
ou_dates = state.get("ou_notified_dates", [])
if ou_dates:
    st.write(f"Zuletzt eingerechnete Tage: {', '.join(sorted(ou_dates, reverse=True)[:10])}")
else:
    st.caption("Noch kein OU-Modell-Tag eingerechnet.")

st.caption(
    "Reproduzierbar/Logik: `ek_portfolio/paper_bot.py`. Scheduled Task: \"EK-Portfolio-Paper\" "
    "(stuendlich, `scripts/ek_portfolio_task.ps1`)."
)
