"""Gemeinsame Lade-/Darstellungshilfen fuer die Portfolio-Bridge-Status-Seiten
(2026-09-02). Liest NUR die committete `bridge_status/snapshot.json` -- diese
Seiten rufen nie selbst eine lokale Bridge oder MT5 auf (dieselbe Trennung wie
jede andere Live-Log-Seite in diesem Projekt: Collector laeuft lokal
(Bridge-Watchdog, alle 30 Min, ausserhalb des Repos), Seite liest nur
committete Daten). Siehe C:\\Users\\andre\\Bridge-Watchdog\\watchdog.py fuer
den Collector."""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "bridge_status" / "snapshot.json"

STATUS_META = {
    "ok": ("Läuft normal", ":material/check_circle:"),
    "stale": ("Kein aktueller Lauf", ":material/warning:"),
    "log_missing": ("Log-Datei fehlt", ":material/error:"),
    "not_expected_today": ("Heute nicht erwartet (Wochenende)", ":material/weekend:"),
}


def load_snapshot() -> dict | None:
    if not SNAPSHOT_PATH.exists():
        return None
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def render_generated_at(snapshot: dict) -> None:
    generated = datetime.fromisoformat(snapshot["generated_at"])
    age_min = (datetime.now() - generated).total_seconds() / 60
    st.caption(
        f"Snapshot vom Bridge-Watchdog (lokal, alle 30 Min., committet ins Repo): "
        f"{generated.strftime('%Y-%m-%d %H:%M')} ({age_min:.0f} Min. alt)"
    )


def status_pill(status: str) -> str:
    label, icon = STATUS_META.get(status, (status, ":material/help:"))
    return f"{icon} {label}"


def render_account_card(label: str, acc: dict) -> None:
    """EINE Kachel fuer ein Konto (oder ein ganzes Bein ohne Unterkonten):
    letzte Equity-Zeile, letzter Fehler, juengste Ereignisse."""
    with st.container(border=True):
        st.markdown(f"**{label}**")
        eq = acc.get("last_equity_line")
        if eq:
            st.caption(f":material/account_balance_wallet: {eq}")
        else:
            st.caption("Noch keine Equity-Zeile im Log gefunden.")

        err = acc.get("last_error_line")
        if err:
            st.warning(err, icon=":material/error:")

        events = acc.get("recent_events", [])
        if events:
            with st.expander(f"Letzte Ereignisse ({len(events)})", expanded=False):
                for line in events:
                    st.code(line, language=None, wrap_lines=True)
        else:
            st.caption("Keine Entries/Exits/Fehler im geprüften Log-Fenster.")


def render_bridge_section(name: str, entry: dict) -> None:
    """Ein ganzer Bridge-Block: Status-Header + eine Kachel je Konto (oder
    eine einzelne Kachel, falls die Bridge nur ein Konto hat)."""
    status = entry.get("status", "unknown")
    cols = st.columns([2, 1, 1])
    cols[0].markdown(f"### {name}")
    cols[1].metric("Status", status_pill(status).split(" ", 1)[-1], border=False)
    minutes = entry.get("minutes_since_last_run")
    cols[2].metric("Letzter Lauf", f"vor {minutes:.0f} Min." if minutes is not None else "unbekannt")

    if status in ("stale", "log_missing"):
        st.error(
            f"{status_pill(status)} — siehe Telegram-Alarm des Bridge-Watchdogs für Details.",
            icon=":material/report:",
        )

    if "accounts" in entry:
        acc_cols = st.columns(len(entry["accounts"]))
        for col, (acc_name, acc) in zip(acc_cols, entry["accounts"].items()):
            with col:
                render_account_card(acc_name, acc)
    else:
        render_account_card(name, entry)
