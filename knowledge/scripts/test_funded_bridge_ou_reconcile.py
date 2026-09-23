"""Offline-Tests fuer _reconcile_ou_positions() (Funded-Portfolio-Bridge, 2026-09-17).
Gestubbtes MT5, gestubbter Executor, DRY_RUN erzwungen -- keine Order, kein State-Write.

Aufruf:  python test_funded_bridge_ou_reconcile.py            (synthetische Faelle)
         python test_funded_bridge_ou_reconcile.py --real     (+ Trockenlauf auf Kopie
                                                               des echten TTP-States mit echtem Scan)
"""
import copy
import json
import sys
import types
from pathlib import Path

BRIDGE = Path(r"C:\Users\andre\Funded-Portfolio-Bridge")
sys.path.insert(0, str(BRIDGE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # wie run_once.py main(), Emojis in den Meldungen

if "--real" not in sys.argv:
    sys.modules["MetaTrader5"] = types.ModuleType("MetaTrader5")  # _reconcile braucht MT5 nicht direkt

import pandas as pd  # noqa: E402
import run_once as slow  # noqa: E402

slow.DRY_RUN = True
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print("  PASS  " + name)
    else:
        fail += 1
        print("  FAIL  " + name + "   " + str(extra))


closed_calls = []


class FakeExec:
    fail_tickets = set()

    @staticmethod
    def close_position(ticket, symbol, dry_run=True):
        closed_calls.append(ticket)
        if ticket in FakeExec.fail_tickets:
            return {"status": "error", "reason": "retcode 10018"}
        return {"status": "closed", "ticket": ticket, "close_price": 100.0}


class Acct:
    rules = "ttp"


def row(market, day, reason):
    return {"entry_time": pd.Timestamp(day), "market": market, "direction": "long",
            "exit_reason": reason, "entry_price": 100.0, "sl": 90.0, "r_multiple": 0.0}


def key(market, day):
    return slow._signal_key(f"ou_modell ({market})", market, pd.Series(row(market, day, "data_end")))


def placed(market, day, ticket, opened):
    return key(market, day), {"leg": f"ou_modell ({market})", "symbol_broker": market, "direction": 1,
                              "status": "placed", "ticket": ticket, "opened_at": opened}


def run(state, rows, nyse=True):
    closed_calls.clear()
    slow.executor = FakeExec
    slow._nyse_is_open = lambda now_utc=None: nyse
    return slow._reconcile_ou_positions(Acct(), state, pd.DataFrame(rows))


if True:
    print("\n[1] Duplikat: Modell offen 09-08, live 09-08 + 09-11")
    k1, p1 = placed("AMGN", "2026-09-08", 1, "2026-09-08T14:00")
    k2, p2 = placed("AMGN", "2026-09-11", 2, "2026-09-11T14:00")
    st = {"positions": {k1: p1, k2: p2}}
    m = run(st, [row("AMGN", "2026-09-08", "data_end")])
    check("schliesst nur das Duplikat", closed_calls == [2], closed_calls)
    check("Original bleibt placed", st["positions"][k1]["status"] == "placed")
    check("Duplikat als closed markiert", st["positions"][k2]["status"] == "closed")
    check("Grund reconcile_duplicate", st["positions"][k2].get("close_reason") == "reconcile_duplicate")
    check("meldet ABGLEICH", any("ABGLEICH" in x for x in m), m)

    print("\n[2] Reine Drift: live nur 09-14, Modell offen 09-11 (dort 'missed')")
    k_new = key("APD", "2026-09-11")
    k_old, p_old = placed("APD", "2026-09-14", 3, "2026-09-15T19:37")
    st = {"positions": {k_old: p_old, k_new: {"leg": "ou_modell (APD)", "status": "missed", "ticket": None}}}
    run(st, [row("APD", "2026-09-11", "data_end")])
    check("nichts geschlossen", closed_calls == [], closed_calls)
    check("auf aktuellen Schluessel umgehaengt", st["positions"].get(k_new, {}).get("ticket") == 3, st["positions"])
    check("alter Schluessel entfernt", k_old not in st["positions"])
    check("Herkunft vermerkt", st["positions"][k_new].get("rekeyed_from") == k_old)

    print("\n[3] Modell draussen: live FAST 09-03, Scan FAST 08-31 max_holding")
    k, p = placed("FAST", "2026-09-03", 4, "2026-09-03T13:42")
    st = {"positions": {k: p}}
    run(st, [row("FAST", "2026-08-31", "max_holding")])
    check("wird geschlossen", closed_calls == [4], closed_calls)
    check("Grund reconcile_model_flat", st["positions"][k].get("close_reason") == "reconcile_model_flat")

    print("\n[4] Titel fehlt im Scan (Datenausfall) -> kein Schliessen")
    k, p = placed("XYZ", "2026-09-03", 5, "2026-09-03T13:42")
    st = {"positions": {k: p}}
    m1 = run(st, [row("FAST", "2026-08-31", "max_holding")])
    m2 = run(st, [row("FAST", "2026-08-31", "max_holding")])
    check("nicht geschlossen", closed_calls == [] and st["positions"][k]["status"] == "placed")
    check("warnt beim ersten Lauf", len(m1) == 1 and "NICHT automatisch" in m1[0], m1)
    check("warnt nicht erneut am selben Tag", m2 == [], m2)

    print("\n[5] NYSE zu: kein Schliessen, Umhaengen trotzdem")
    k1, p1 = placed("AMGN", "2026-09-08", 6, "2026-09-08T14:00")
    k2, p2 = placed("AMGN", "2026-09-11", 7, "2026-09-11T14:00")
    st = {"positions": {k1: p1, k2: p2}}
    run(st, [row("AMGN", "2026-09-10", "data_end")], nyse=False)
    k_now = key("AMGN", "2026-09-10")
    check("nichts geschlossen", closed_calls == [], closed_calls)
    check("aelteste auf aktuellen Schluessel umgehaengt", st["positions"].get(k_now, {}).get("ticket") == 6)
    check("Duplikat bleibt placed bis zur Session", st["positions"][k2]["status"] == "placed")
    run(st, [row("AMGN", "2026-09-10", "data_end")], nyse=True)
    check("in der Session: Duplikat geschlossen", closed_calls == [7], closed_calls)

    print("\n[6] Schliessen scheitert -> bleibt placed, eine Meldung")
    FakeExec.fail_tickets = {8}
    k, p = placed("ADI", "2026-09-03", 8, "2026-09-03T14:22")
    st = {"positions": {k: p}}
    m1 = run(st, [row("ADI", "2026-09-01", "max_holding")])
    m2 = run(st, [row("ADI", "2026-09-01", "max_holding")])
    FakeExec.fail_tickets = set()
    check("bleibt placed", st["positions"][k]["status"] == "placed")
    check("versucht es erneut", closed_calls == [8])
    check("genau eine Fehlermeldung", len(m1) == 1 and m2 == [], (m1, m2))

    print("\n[7] Nach dem Umhaengen loest _process_leg() keinen Neueinstieg aus")
    k_old, p_old = placed("DD", "2026-09-12", 9, "2026-09-15T19:43")
    st = {"positions": {k_old: p_old}, "account_start": "2026-09-01"}
    rows = [row("DD", "2026-09-14", "data_end")]
    run(st, rows)
    entries = []

    class NoEntryExec(FakeExec):
        @staticmethod
        def place_market_entry(*a, **k):
            entries.append(a)
            return {"status": "placed", "ticket": 99}
    slow.executor = NoEntryExec

    class A2:
        symbol_map, symbol_suffix, excluded_legs, capital_weight, rules, name = {}, "", (), 1 / 6, "ttp", "T"
    slow.resolve_symbol = lambda account, s: s
    slow._process_leg(A2(), st, 100000.0, "ou_modell (DD)", pd.DataFrame(rows), "DD", risk_pct=0.01)
    check("kein zweiter Einstieg", entries == [], entries)

    print("\n[8] Dispatch-Dedupe: zwei offene Zeilen je Titel -> eine")
    r = pd.DataFrame([row("AMGN", "2026-09-11", "data_end"), row("AMGN", "2026-09-08", "data_end"),
                      row("RL", "2026-08-27", "max_holding")]).sort_values("entry_time")
    r2 = pd.concat([r[r["exit_reason"] != "data_end"], r[r["exit_reason"] == "data_end"].drop_duplicates("market", keep="first")])
    check("eine AMGN-Zeile, die aelteste", list(r2[r2["market"] == "AMGN"]["entry_time"]) == [pd.Timestamp("2026-09-08")])
    check("geschlossene Zeilen bleiben", (r2["market"] == "RL").sum() == 1)

if "--real" in sys.argv:
    print("\n[REAL] Trockenlauf auf KOPIEN der echten TTP-States mit dem aktuellen Scan")
    end = pd.Timestamp.now(tz="UTC").tz_localize(None)
    scan = slow.pb._scan_ou_modell(end, force_refresh=True, source="lake")
    scan = scan.sort_values("entry_time")
    scan = pd.concat([scan[scan["exit_reason"] != "data_end"],
                      scan[scan["exit_reason"] == "data_end"].drop_duplicates("market", keep="first")])
    for f in ("bridge_state_ttp.json", "bridge_state_ttp1.json"):
        st = copy.deepcopy(json.load(open(BRIDGE / f)))
        msgs = run(st, scan.to_dict("records"), nyse=True)
        print(f"  == {f}: wuerde schliessen Tickets {closed_calls}")
        for x in msgs:
            print("     " + x)
        for kk, pp in st["positions"].items():
            if pp.get("rekeyed_from"):
                print(f"     umgehaengt: {pp['rekeyed_from']} -> {kk} (Ticket {pp['ticket']})")

print(f"\n==== {ok} PASS, {fail} FAIL ====")
sys.exit(1 if fail else 0)
