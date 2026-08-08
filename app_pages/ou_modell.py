"""Live Logs -- OU-Modell: read-only view of the live OU-Modell signal-bot's
daily performance, collected by scripts/collect_ou_modell_daily_log.py and
committed to ou_modell_logs/daily_log.csv (the bot itself, its local logs,
state DBs and the MT5 terminals live outside this repo on the user's
machine and aren't reachable from Streamlit Cloud - this page only ever
reads the committed CSV/raw logs, never connects to MT5 or touches an
order).

First live trading day: 2026-07-29 (Konto 1 only at the time).
Multi-account since 2026-07-31: Konto 1 (TTP, real money), Konto 2 (TTP,
DEMO - not real money), Konto 3 (Tickmill, real money) - see an
account-selector below, all charts/tables are scoped to one account at a
time since risk config and equity differ per account. Pre-2026-07-31 CSV
rows have no "account" column; the collector backfills those as "Konto 1
(TTP)" since that was the only account back then.

Intentionally no performance verdict here while any account's sample is
this small - the point is to accumulate ~a month of daily rows before
drawing any conclusion, same discipline as every backtest finding in this
project.

Since 2026-08-04: second tab "NAS-Migration" - a static write-up of the
planned move from the current Windows-PC-hosted bot to a Windows VM on the
user's UGREEN NASync DXP2800, discussed but NOT yet started/decided in
detail (RAM upgrade + Windows license still open as of writing). Purely
informational, no interactivity - kept here (not a separate page) since
it's operational context for this same bot, not a new strategy."""

import json
from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="OU-Modell -- Live Logs", page_icon=":material/monitoring:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_DIR / "ou_modell_logs" / "daily_log.csv"
RAW_DIR = REPO_DIR / "ou_modell_logs" / "raw"

# Mirrort config.ACCOUNTS im Bot-Repo, nur um state_id -> Anzeigename
# aufzulösen (für den Pfad zu den rohen Logs je Konto).
ACCOUNT_STATE_IDS = {
    "Konto 1 (TTP)": "konto1_ttp",
    "Konto 2 (TTP, Demo)": "konto2_ttp",
    "Konto 3 (Tickmill)": "konto3_tickmill",
}

st.markdown("## :material/monitoring: OU-Modell -- Live-Trading-Log")

tab_log, tab_migration = st.tabs([":material/monitoring: Live-Trading-Log", ":material/dns: NAS-Migration"])

with tab_log:
    st.info(
        "Ein gehosteter OU-Modell-Signal-Scanner sendet Long-Setups automatisch an "
        "MT5-Konten (Windows Task Scheduler, stündliche Scans 15:35-21:35, Mo-Fr). Seit "
        "**29.07.2026** laufen echte Orders auf Konto 1 (davor nur Dry-Run-Tests); "
        "seit **31.07.2026** zusätzlich Konto 2 (TTP, **Demo - kein echtes Geld**) "
        "und Konto 3 (Tickmill, echtes Geld). "
        "Diese Seite zeigt nur committete Tageswerte -- kein Live-Zugriff auf MT5 von "
        "hier aus. **Noch keine Auswertung/Verdict**: das kommt erst nach ~einem Monat "
        "gesammelter Tage, dieselbe Disziplin wie bei jedem Backtest in diesem Projekt.",
        icon=":material/warning:",
    )

    if not CSV_PATH.exists():
        st.warning(
            "Noch keine Tages-Logs vorhanden. Der erste Eintrag wird nach dem "
            "letzten täglichen Scan (21:30 Uhr) über "
            "`scripts/collect_ou_modell_daily_log.py` ergänzt.",
            icon=":material/hourglass_empty:",
        )
        st.stop()

    df_all = pd.read_csv(CSV_PATH, parse_dates=["date"])
    if "account" not in df_all.columns:
        df_all["account"] = "Konto 1 (TTP)"
    df_all["account"] = df_all["account"].fillna("Konto 1 (TTP)")

    accounts_present = [a for a in ACCOUNT_STATE_IDS if a in df_all["account"].unique()]
    accounts_present += [a for a in df_all["account"].unique() if a not in accounts_present]
    selected_account = st.selectbox("Konto", accounts_present)
    if "Demo" in selected_account:
        st.caption(":material/info: Demo-Konto -- kein echtes Geld betroffen.")

    df = df_all[df_all["account"] == selected_account].sort_values("date")

    n_days = len(df)
    st.caption(f"{n_days} Tag{'e' if n_days != 1 else ''} erfasst seit {df['date'].min().date()}." if n_days else "Noch keine Tage für dieses Konto erfasst.")
    if df.empty:
        st.stop()

    latest = df.iloc[-1]
    with st.container(horizontal=True):
        st.metric("Letzter Kontostand (Equity)", f"{latest['current_equity']:,.2f}" if pd.notna(latest["current_equity"]) else "n/a", border=True)
        pnl = latest["daily_pnl_pct"]
        st.metric("Tagesergebnis", f"{pnl:+.2%}" if pd.notna(pnl) else "n/a", border=True)
        st.metric("Signale heute gescannt", int(latest["signals_scanned"]) if pd.notna(latest["signals_scanned"]) else "n/a", border=True)
        st.metric("Orders gesendet", int(latest["orders_sent"]) if pd.notna(latest["orders_sent"]) else "n/a", border=True)
        st.metric("Übersprungen", int(latest["orders_skipped"]) if pd.notna(latest["orders_skipped"]) else "n/a", border=True)

    if bool(latest.get("drawdown_halted")):
        st.error("Tages-Drawdown-Stopp hat am letzten erfassten Tag gegriffen -- keine neuen Orders mehr in diesem Lauf.", icon=":material/dangerous:")

    if isinstance(latest.get("connection_error"), str) and latest["connection_error"]:
        st.warning(f"MT5-Verbindung beim Erfassen dieses Tages fehlgeschlagen: {latest['connection_error']} -- Equity-Werte ggf. unvollständig.", icon=":material/link_off:")

    st.space("medium")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Equity über die Zeit**")
            if df["current_equity"].notna().sum() >= 2:
                st.line_chart(df.set_index("date")["current_equity"])
            else:
                st.info("Braucht mindestens 2 Tage mit gültiger Equity für einen Verlauf.", icon=":material/info:")

    with col2:
        with st.container(border=True):
            st.markdown("**Orders pro Tag**")
            if not df.empty:
                st.bar_chart(df.set_index("date")[["orders_sent", "orders_skipped", "orders_error"]])

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Tages-Log**")
        display = df.copy()
        display["date"] = display["date"].dt.date
        st.dataframe(
            display.sort_values("date", ascending=False),
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Datum"),
                "signals_scanned": st.column_config.NumberColumn("Gescannt"),
                "orders_sent": st.column_config.NumberColumn("Gesendet"),
                "orders_skipped": st.column_config.NumberColumn("Übersprungen"),
                "orders_error": st.column_config.NumberColumn("Fehler"),
                "symbols_sent": st.column_config.TextColumn("Symbole (gesendet)"),
                "baseline_equity": st.column_config.NumberColumn("Baseline-Equity", format="%.2f"),
                "current_equity": st.column_config.NumberColumn("Equity", format="%.2f"),
                "floating_pnl": st.column_config.NumberColumn("Floating P&L", format="%.2f"),
                "daily_pnl_pct": st.column_config.NumberColumn("Tagesergebnis", format="%.2%%"),
                "open_positions": st.column_config.TextColumn("Offene Positionen"),
                "drawdown_halted": st.column_config.CheckboxColumn("DD-Stopp"),
                "connection_error": st.column_config.TextColumn("MT5-Fehler"),
            },
        )

    st.space("medium")

    with st.container(border=True):
        st.markdown(f"**Stündliche Scans -- {latest['date'].date()}**")
        breakdown_raw = latest.get("hourly_breakdown")
        runs = []
        if isinstance(breakdown_raw, str) and breakdown_raw.strip():
            try:
                runs = json.loads(breakdown_raw)
            except json.JSONDecodeError:
                runs = []

        if not runs:
            st.info(
                "Für diesen Tag liegt noch keine stündliche Aufschlüsselung vor "
                "(älterer Log-Eintrag, vor Einführung dieser Spalte am 2026-07-30).",
                icon=":material/info:",
            )
        else:
            breakdown_df = pd.DataFrame(runs)
            breakdown_df["sent_symbols"] = breakdown_df["sent_symbols"].apply(lambda s: ", ".join(s) if s else "")
            breakdown_df["pending_symbols"] = breakdown_df["pending_symbols"].apply(lambda s: ", ".join(s) if s else "")
            st.dataframe(
                breakdown_df,
                hide_index=True,
                column_order=[
                    "time", "signals_scanned", "sent", "sent_symbols", "pending_placed",
                    "pending_symbols", "pending_cancelled", "be_moved", "skipped", "error",
                    "drawdown_halted", "scan_failed",
                ],
                column_config={
                    "time": st.column_config.TextColumn("Uhrzeit"),
                    "signals_scanned": st.column_config.NumberColumn("Gescannt"),
                    "sent": st.column_config.NumberColumn("Market-Entry"),
                    "sent_symbols": st.column_config.TextColumn("Symbole (Market)"),
                    "pending_placed": st.column_config.NumberColumn("Pending angelegt"),
                    "pending_symbols": st.column_config.TextColumn("Symbole (Pending)"),
                    "pending_cancelled": st.column_config.NumberColumn("Pending storniert"),
                    "be_moved": st.column_config.NumberColumn("BE verschoben"),
                    "skipped": st.column_config.NumberColumn("Übersprungen"),
                    "error": st.column_config.NumberColumn("Fehler"),
                    "drawdown_halted": st.column_config.CheckboxColumn("DD-Stopp"),
                    "scan_failed": st.column_config.CheckboxColumn("Scan fehlgeschlagen"),
                },
            )

    _raw_state_id = ACCOUNT_STATE_IDS.get(selected_account)
    _raw_candidates = [RAW_DIR / f"{latest['date'].date()}.log"]  # Altdaten vor Multi-Konto, flache Struktur
    if _raw_state_id:
        _raw_candidates.insert(0, RAW_DIR / _raw_state_id / f"{latest['date'].date()}.log")
    latest_raw = next((p for p in _raw_candidates if p.exists()), _raw_candidates[0])
    if latest_raw.exists():
        with st.expander(f"Rohes Bot-Log vom {latest['date'].date()}"):
            st.code(latest_raw.read_text(encoding="utf-8"), language="text")

with tab_migration:
    st.markdown("### Geplante Migration: Windows-PC -> Windows-VM auf NAS")
    st.caption(
        "Stand 2026-08-04 -- Diskussionsstand, NICHT umgesetzt. RAM-Upgrade und "
        "Windows-Lizenz sind noch offen. Rein informativ, keine Live-Daten."
    )

    st.info(
        "Leitplanke für den ganzen Plan: **nie eine Phase, in der beide Systeme "
        "gleichzeitig live Orders platzieren könnten, und nie eine Lücke, in der "
        "gar keins läuft** -- 2 von 3 Konten sind echtes Geld.",
        icon=":material/gpp_maybe:",
    )

    st.markdown("#### Ziel-Hardware")
    hw_col1, hw_col2 = st.columns(2)
    with hw_col1:
        with st.container(border=True):
            st.markdown("**UGREEN NASync DXP2800**")
            st.markdown(
                "- CPU: Intel N100, 4 Kerne, bis 3.4 GHz (kein Hyperthreading, "
                "reiner Effizienzchip, x86 mit VT-x)\n"
                "- RAM: 8 GB DDR5 verbaut, **auf 16 GB erweiterbar** (bestätigt)\n"
                "- OS: UGOS Pro mit Virtual-Machine-Manager"
            )
    with hw_col2:
        with st.container(border=True):
            st.markdown("**Windows-Lizenz (offen)**")
            st.markdown(
                "- Windows 11 Home: ca. 145€ (offiziell)\n"
                "- Windows 11 Pro: ca. 259€ (offiziell) -- **nötig für eingehendes RDP**\n"
                "- Günstiger über Reseller möglich (~20-40€), rechtliche Grauzone bei "
                "sehr billigen Keys\n"
                "- Alternative: alte ungenutzte Lizenz wiederverwenden -- **wird noch "
                "erfragt**"
            )

    st.warning(
        "Vor jeder Anschaffung offen zu klären: unterstützt UGOS Pro's VM-Manager "
        "Windows 11 inkl. virtuellem TPM 2.0? Ohne das bräuchte es einen "
        "TPM-Bypass oder Windows 10 (Support seit Okt. 2025 ausgelaufen, für einen "
        "Dauerläufer nicht ideal).",
        icon=":material/help:",
    )

    st.markdown("#### Alternativen im Vergleich")
    st.caption(
        "NAS-VM (dieser Plan) vs. zwei Alternativen, die dieselbe Bot-Software "
        "unverändert nutzen würden, nur auf anderer Hardware/Infrastruktur."
    )
    comparison_df = pd.DataFrame(
        [
            {
                "Kriterium": "Einmalkosten",
                "NAS-VM (DXP2800)": "~40-60€ RAM-Upgrade + Windows-Lizenz (145-259€, ggf. 0€ mit alter Lizenz)",
                "Windows-VPS (z.B. Strato)": "keine",
                "Mini-PC (dediziert)": "~150-300€ Hardware + Windows-Lizenz (145-259€, ggf. 0€ mit alter Lizenz)",
            },
            {
                "Kriterium": "Laufende Kosten",
                "NAS-VM (DXP2800)": "nur Strom (NAS läuft ohnehin)",
                "Windows-VPS (z.B. Strato)": "~37-43€/Monat (Plan \"L\", 6 vCores/8GB RAM, Windows Server 2022/2025 Datacenter INKLUSIVE lizenziert)",
                "Mini-PC (dediziert)": "nur Strom",
            },
            {
                "Kriterium": "Setup-Aufwand",
                "NAS-VM (DXP2800)": "mittel-hoch (VM, vTPM-Unsicherheit, Terminal-Migration)",
                "Windows-VPS (z.B. Strato)": "niedrig (Windows Server vorinstalliert, RDP nativ dabei - kein \"Pro vs. Home\"-Thema)",
                "Mini-PC (dediziert)": "niedrig-mittel (natives Windows, kein Virtualisierungs-Thema)",
            },
            {
                "Kriterium": "Zuverlässigkeit/Uptime",
                "NAS-VM (DXP2800)": "N100 evtl. unter Last (3 Terminals+Chromium) knapp",
                "Windows-VPS (z.B. Strato)": "hoch (Rechenzentrum, redundante Strom/Internet, dedizierte 8GB statt mit NAS-OS geteilt)",
                "Mini-PC (dediziert)": "gut, aber an Heimstrom/-internet gebunden",
            },
            {
                "Kriterium": "Broker-Latenz",
                "NAS-VM (DXP2800)": "wie bisher (Heimanschluss)",
                "Windows-VPS (z.B. Strato)": "irrelevant bei stündlichem Scan-Rhythmus (kein HFT)",
                "Mini-PC (dediziert)": "wie bisher (Heimanschluss)",
            },
            {
                "Kriterium": "Hauptrisiko",
                "NAS-VM (DXP2800)": "TPM/Virtualisierungs-Kompatibilität ungeklärt, RAM knapp",
                "Windows-VPS (z.B. Strato)": "Konto-Zugangsdaten auf fremdem Server, Anbieterabhängigkeit, Kosten laufen dauerhaft",
                "Mini-PC (dediziert)": "am wenigsten technische Unsicherheit, aber ein Gerät mehr zu pflegen",
            },
            {
                "Kriterium": "Datenhoheit/Kontrolle",
                "NAS-VM (DXP2800)": "voll (eigenes Gerät)",
                "Windows-VPS (z.B. Strato)": "eingeschränkt (Drittanbieter-Server)",
                "Mini-PC (dediziert)": "voll (eigenes Gerät)",
            },
        ]
    )
    st.dataframe(comparison_df, hide_index=True, width="stretch")
    st.info(
        "**Update 2026-08-04, konkretes Angebot geprüft (strato.de):** Strato "
        "bietet Windows-Server-VPS mit **inkludierter Windows-Lizenz** an - Plan "
        "\"L\" (6 vCores, 8GB RAM, ~37-43€/Monat) wäre für 3 MT5-Terminals + "
        "Playwright ausreichend dimensioniert, RDP ist bei Windows Server nativ "
        "dabei (kein Pro/Home-Thema). Das macht die VPS-Option aktuell am "
        "attraktivsten: kein offener Lizenz-Kostenpunkt mehr, dedizierte "
        "Ressourcen statt Sharing mit einem NAS-Betriebssystem, kein "
        "TPM/Virtualisierungs-Risiko. Trade-off bleibt die dauerhafte "
        "monatliche Kostenlast und dass Live-Konto-Zugangsdaten auf einem "
        "Server eines Drittanbieters liegen würden. Mini-PC bleibt die Option "
        "mit den wenigsten technischen Unsicherheiten bei nur einmaligen "
        "Kosten. Die NAS-VM hat von den dreien weiterhin die meisten offenen "
        "Fragezeichen (TPM, N100-Leistung unter Last).",
        icon=":material/lightbulb:",
    )

    st.markdown("#### Phasenplan (NAS-VM)")

    with st.expander("Phase 0 -- Vorabklärungen", expanded=True):
        st.markdown(
            "- RAM-Upgrade auf 16 GB bestellen/einbauen\n"
            "- UGOS-Pro-VM-Support für Windows 11 + vTPM verifizieren\n"
            "- Windows-Lizenz besorgen (Pro empfohlen, wegen RDP)"
        )

    with st.expander("Phase 1 -- Basis-VM aufsetzen"):
        st.markdown(
            "- Windows-11-Pro-VM in UGOS Pro anlegen, aktivieren, RDP einrichten, "
            "unnötige Windows-Dienste deaktivieren (RAM sparen)\n"
            "- Python (gleiche Version wie aktuell), `MetaTrader5`-Paket, Playwright "
            "(`playwright install chromium`), `requests` installieren\n"
            "- Alle 3 Broker-Terminals (TTP x2, Tickmill) frisch installieren"
        )

    with st.expander("Phase 2 -- Code + State migrieren"):
        st.markdown(
            "- Kompletten `OU-Modell-MT5-Bridge`-Ordner rüberkopieren -- "
            "**inklusive** `state/*.sqlite3` (Dedupe/BE-Metadaten/Baselines) und "
            "`logs/`, damit keine Handelshistorie/Dedupe-Kontinuität verloren geht\n"
            "- `config.py`-Terminal-Pfade an neue Windows-Installationspfade anpassen\n"
            "- Alle 3 Konten einloggen, AutoTrading manuell aktivieren (jedes "
            "Terminal bleibt dauerhaft bei einem Login, wie bisher)"
        )

    with st.expander("Phase 3 -- Automatisierung nachbauen"):
        st.markdown(
            "- Denselben Windows-Task-Scheduler-Task (Mo-Fr, stündlich 15:35-21:35) "
            "innerhalb der VM neu anlegen\n"
            "- VM darf nie in den Ruhezustand gehen (Windows-Energieoptionen in der "
            "VM), UGOS Pro so konfigurieren, dass die VM bei NAS-Neustart automatisch "
            "mitstartet -- Verlässlichkeits-Verbesserung ggü. dem PC (siehe Ausfall "
            "vom 2026-08-03)"
        )

    with st.expander("Phase 4 -- Parallelbetrieb zur Absicherung (kritisch)"):
        st.markdown(
            "- Alten Task auf dem PC weiterlaufen lassen, neue VM zunächst mit "
            "`DRY_RUN=True` ein paar Tage im Schatten mitlaufen lassen, Ergebnisse "
            "vergleichen\n"
            "- Erst wenn das sauber aussieht: alten Task exakt an einer "
            "Scan-Grenze deaktivieren, neuen Task aktivieren, `DRY_RUN=False` nur "
            "auf der VM setzen"
        )

    with st.expander("Phase 5 -- Cutover + Rückfallebene"):
        st.markdown(
            "- Alten PC-Task deaktivieren (nicht sofort löschen)\n"
            "- Erste echte Läufe auf der VM eng über Telegram beobachten\n"
            "- Alten Ordner als Kaltreserve eine Weile behalten"
        )

    st.caption(
        "Nächster Schritt laut letztem Gespräch: User klärt Windows-Lizenz "
        "(ggf. vorhandene alte Lizenz wiederverwenden) -- danach Phase 0 starten."
    )
