"""CLI: python -m signal_hub scan | listen | status   (siehe signal_hub/__init__.py)."""

from __future__ import annotations

import json
import logging
import sys

import numpy as np
import pandas as pd

from signal_hub import alert, config, journal, paper, risk, telegram
from signal_hub.setups import h4_spike

log = logging.getLogger("signal_hub")
FEATURE_COLS = ["setup", "markt", "klasse", "seite", "signal", "einstieg", "stunde", "kurs", "stop", "marke", "ziel_3r",
                "ziel_swing", "stern", "ampel", "ampel_text", "spanne_atr", "docht_anteil", "koerper_anteil", "n_sweep",
                "swings_geholt", "schluss_unter_marke_atr", "akt12", "gegendruck6", "adx_h4", "adx_d", "rsi_h4",
                "rsiml_h4", "rsi_d", "rsiml_d", "stochrsi_h4", "bb_aussen", "lage_DS", "lage_20T", "lage_VW", "lage_VM",
                "range20_atr", "DS", "HS", "makro_gegen", "M1", "M2", "M3", "M6", "M7", "X3", "X4", "X1", "GV",
                "g8_abstand", "feiertag", "gueltig_bis"]


def _now() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC")


def _complete_end(name: str) -> pd.Timestamp | None:
    """Ende der juengsten H4-Kerze, die von den Intraday-Daten vollstaendig abgedeckt ist (UTC)."""
    from htf_daily_trade.h4_manip import intraday
    b = intraday(name)
    if b.empty:
        return None
    tail = b.index[-6:]
    tf = pd.Series(tail).diff().dropna().min() if len(tail) > 1 else pd.Timedelta(hours=1)
    covered = b.index.max() + tf
    return h4_spike.last_closed_bar_end(covered + pd.Timedelta(seconds=1))


# --------------------------------------------------------------------------- Scan
def scan(dry: bool = False) -> int:
    state = journal.load_state()
    done = state.setdefault("done", {})
    todo = {}
    for name in config.MARKETS:
        try:
            ce = _complete_end(name)
        except Exception as e:
            log.warning("%s: Daten nicht lesbar: %s", name, e)
            continue
        if ce is not None and ce < _now() - pd.Timedelta(hours=8):
            if not done.get(f"{name}_alt_gemeldet") == ce.isoformat():
                print(f"{name}: Daten veraltet (letzte volle H4-Kerze bis {ce.tz_convert(config.TZ):%d.%m. %H:%M}) – übersprungen")
                done[f"{name}_alt_gemeldet"] = ce.isoformat()
            continue
        if ce is not None and (name not in done or pd.Timestamp(done[name]) < ce):
            todo[name] = ce
    if not todo:
        print("Keine neue abgeschlossene H4-Kerze.")
        return 0
    from htf_daily_trade.filter_matrix import MacroDirs
    from htf_daily_trade.h4_v4 import blocked_days
    md = MacroDirs.full()
    try:
        from fusion_lab.filters.gold_macro_veto import GoldMacroVetoFilter
        gv = GoldMacroVetoFilter()
    except Exception as e:
        print("Gold-Makro-Veto nicht verfuegbar:", e)
        gv = None
    blocked = blocked_days()
    neu = 0
    with journal.locked():
        j = journal.load()
        for name, ce in todo.items():
            sigs, x, k = h4_spike.scan_market(name, ce, md, gv, blocked)
            if x is None:
                continue
            for r in sigs:
                _append_all(r)
                if not r["alarm"] or ("id" in j and (j["id"] == r["id"]).any()):
                    continue
                ok, grund = risk.check(j, name, _now())
                r["gesperrt_grund"] = "" if ok else grund
                r["sizing"] = risk.sizing_text(name, r["kurs"], r["stop"])
                cap = alert.caption(r)
                config.CHARTS.mkdir(parents=True, exist_ok=True)
                png = alert.chart(x, k, r, config.CHARTS / f"{r['id']}.png")
                mid = None if dry else telegram.send_photo(png, cap, alert.buttons(r["id"], gesperrt=not ok))
                row = {c: r.get(c) for c in FEATURE_COLS}
                row.update({"id": r["id"], "status": "offen" if ok else "gesperrt", "grund": grund or None,
                            "caption": cap, "message_id": mid, "erstellt": _now().tz_convert(config.TZ)})
                j = journal.upsert(j, row)
                neu += 1
                print(f"Alarm: {r['id']} {'⭐' if r['stern'] else ''} {'(gesperrt: ' + grund + ')' if not ok else ''}")
            done[name] = ce.isoformat()
            print(f"{name}: Kerze bis {ce.tz_convert(config.TZ):%d.%m. %H:%M} geprueft, {len(sigs)} Grundsignal(e)")
        journal.save(j)
        write_out(j)
    journal.save_state(state)
    return neu


def _append_all(r: dict) -> None:
    row = pd.DataFrame([{c: r.get(c) for c in FEATURE_COLS + ["id", "alarm", "q", "a"]}])
    p = config.ALL_SIGNALS
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        old = pd.read_csv(p, dtype={"id": str})
        if (old["id"] == r["id"]).any():
            return
    row.to_csv(p, mode="a", header=not p.exists(), index=False)


# --------------------------------------------------------------------------- Listener
def _cap(row, extra: str) -> str:
    return f"{row['caption']}\n{extra}" if isinstance(row.get("caption"), str) else extra


def handle_callback(j: pd.DataFrame, cb: dict, now: pd.Timestamp) -> pd.DataFrame:
    data = cb.get("data", "")
    parts = data.split("|")
    if len(parts) < 3 or parts[0] != "sh":
        return j
    sid, action = parts[1], parts[2]
    hit = j[j["id"] == sid] if "id" in j else j.iloc[0:0]
    if hit.empty:
        telegram.answer(cb["id"], "Signal unbekannt")
        return j
    row = hit.iloc[0]
    mid = int(row["message_id"]) if pd.notna(row.get("message_id")) else None
    loc = now.tz_convert(config.TZ)
    if row["status"] not in ("offen", "gesperrt"):
        telegram.answer(cb["id"], f"Schon erledigt: {row['status']}")
        return j
    if action == "yes" and row["status"] == "offen":
        ok, grund = risk.check(j[j["id"] != sid], row["markt"], now)
        if not ok:
            j = journal.update(j, sid, status="gesperrt", grund=grund)
            telegram.answer(cb["id"], f"Gesperrt: {grund}")
            if mid:
                telegram.edit_caption(mid, _cap(row, f"🔒 Gesperrt beim Klick: {grund}"), None)
            return j
        j = journal.update(j, sid, status="ja", entschieden_um=loc)
        telegram.answer(cb["id"], "Bestätigt – Paper-Order aktiv")
        if mid:
            telegram.edit_caption(mid, _cap(row, f"✅ Bestätigt {loc:%H:%M} – Paper-Order zum nächsten Kurs"), None)
    elif action == "no":
        if len(parts) >= 4:
            j = journal.update(j, sid, status="nein", grund=parts[3], entschieden_um=loc)
            telegram.answer(cb["id"], "Abgelehnt")
            if mid:
                telegram.edit_caption(mid, _cap(row, f"❌ Abgelehnt {loc:%H:%M} ({parts[3]})"), None)
        else:
            telegram.answer(cb["id"], "Grund?")
            if mid:
                telegram.edit_markup(mid, alert.reason_buttons(sid))
    elif action == "back":
        telegram.answer(cb["id"])
        if mid:
            telegram.edit_markup(mid, alert.buttons(sid, gesperrt=row["status"] == "gesperrt"))
    elif action == "later":
        j = journal.update(j, sid, erinnern_um=loc + pd.Timedelta(minutes=config.REMIND_AFTER_MIN))
        telegram.answer(cb["id"], f"Erinnerung in {config.REMIND_AFTER_MIN} Min.")
    elif action == "seen":
        j = journal.update(j, sid, entschieden_um=loc)
        telegram.answer(cb["id"], "Gesehen")
        if mid:
            telegram.edit_markup(mid, None)
    return j


def maintenance(j: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    if "status" not in j or j.empty:
        return j
    loc = now.tz_convert(config.TZ)
    for _, r in j[j["status"] == "offen"].iterrows():
        mid = int(r["message_id"]) if pd.notna(r.get("message_id")) else None
        if pd.notna(r.get("gueltig_bis")) and loc > r["gueltig_bis"]:
            j = journal.update(j, r["id"], status="verfallen")
            if mid:
                telegram.edit_caption(mid, _cap(r, "⌛ Verfallen ohne Entscheidung"), None)
        elif pd.notna(r.get("erinnern_um")) and loc >= r["erinnern_um"]:
            telegram.send_text(f"⏰ Noch offen: {r['markt']} {r['seite'].upper()} bis {r['gueltig_bis']:%H:%M}",
                               alert.buttons(r["id"]), reply_to=mid)
            j = journal.update(j, r["id"], erinnern_um=pd.NaT)
    return j


def listen() -> None:
    now = _now()
    state = journal.load_state()
    with journal.locked():
        j = journal.load()
        ups = telegram.get_updates(state.get("offset"))
        for u in ups:
            state["offset"] = u["update_id"] + 1
            if "callback_query" in u:
                j = handle_callback(j, u["callback_query"], now)
        j = maintenance(j, now)
        if not j.empty and "markt" in j:
            j = paper.update(j, notify=lambda t: telegram.send_text(t))
        journal.save(j)
        write_out(j)
    journal.save_state(state)


# --------------------------------------------------------------------------- Ausgabe fuer die App
def write_out(j: pd.DataFrame) -> None:
    config.OUT.parent.mkdir(parents=True, exist_ok=True)
    if j.empty or "status" not in j:
        config.OUT.write_text(json.dumps({"signale": [], "stand": str(_now())}), encoding="utf-8")
        return
    cols = [c for c in ("id", "setup", "markt", "seite", "einstieg", "kurs", "stop", "ziel_3r", "stern", "ampel",
                        "status", "grund", "entschieden_um", "p_sig_status", "p_sig_r", "p_conf_status", "p_conf_r")
            if c in j]
    recent = j.sort_values("erstellt").tail(50)[cols]
    ja = j[j["status"] == "ja"]
    stats = {"signale": int(len(j)), "ja": int(len(ja)), "nein": int((j["status"] == "nein").sum()),
             "verfallen": int((j["status"] == "verfallen").sum()),
             "r_bestaetigt": float(ja.get("p_conf_r", pd.Series(dtype=float)).fillna(0).astype(float).sum()) if len(ja) else 0.0,
             "r_alle_signale": float(j.get("p_sig_r", pd.Series(dtype=float)).fillna(0).astype(float).sum())}
    out = {"stand": str(_now()), "statistik": stats,
           "signale": json.loads(recent.to_json(orient="records", date_format="iso", default_handler=str))}
    config.OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


def status() -> None:
    j = journal.load()
    if j.empty or "status" not in j:
        print("Journal leer.")
        return
    pd.set_option("display.width", 220)
    cols = [c for c in ("id", "stern", "ampel", "status", "grund", "p_sig_status", "p_sig_r", "p_conf_status", "p_conf_r")
            if c in j]
    print(j[cols].tail(30).to_string(index=False))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "scan":
        scan(dry="--dry" in sys.argv)
    elif cmd == "listen":
        listen()
    else:
        status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
