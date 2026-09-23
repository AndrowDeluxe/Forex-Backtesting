"""Soll/Ist-Vergleich je Bridge -- was das Portfolio im Fenster gehandelt
HAETTE gegen das, was es tatsaechlich gehandelt hat.

Hintergrund (knowledge/areas/bein-matrix-ist-soll-paper.md): die Bridges
platzieren nur einen Bruchteil ihrer Signale. Ohne Vergleichsmassstab laesst
sich nicht unterscheiden, ob ein schwaches Live-Ergebnis von der Strategie,
den Kosten oder der Ausfuehrung kommt. Paper-Zwillinge wurden als Massstab
verworfen (Nutzerentscheid 2026-09-14) -- stattdessen dieser Backtest ueber
dasselbe Kalenderfenster.

Die Differenz wird in drei Ursachen zerlegt:
  (a) nie_gesehen      -- Backtest kennt den Trade, die Bridge hat ihn nie
                          in den State geschrieben (Scan-Ausfall/Timeout)
  (b) nicht_platziert  -- Bridge hat ihn gesehen, aber kein Ticket erzeugt
                          (Gates: Alter/Restlaufzeit/R-Detektor/Risikodeckel)
  (c) platziert        -- Ticket vorhanden, Ergebnis vergleichbar

GRUNDREGEL: dieses Modul ruft die ECHTEN _scan_*()-Funktionen der drei
paper_bot.py auf und implementiert keine Strategie-Formel ein zweites Mal
(die Duplikation war die Ursache des EK-CAPITAL_WEIGHT-Bugs, siehe
knowledge/areas/paper-bot-zu-live-bridge.md). Es SCHREIBT nichts in die
paper_bot.py oder in Bridge-Dateien -- challenge_portfolio/paper_bot.py
haengt zur Laufzeit an echtem Geld.

WICHTIGSTER VORBEHALT BEIM LESEN DER ZAHLEN: das Soll rechnet mit der HEUTE
gueltigen Konfiguration, nicht mit der, die im Fenster live war. Ein seither
eingebauter Filter verwirft rueckwirkend Trades, die damals real gehandelt
wurden. Realbeispiel KW37: Funded hat am 2026-09-09 einen cls_practical-Trade
mit 3,6 Pips Stop genommen (-1.441,72 USD ueber drei Konten); der am
2026-09-10 eingefuehrte 5-Pip-Boden verwirft ihn heute, das Soll zeigt fuer
dieses Bein deshalb "kein Signal". Die Differenz ist dort also kein
Ausfuehrungsfehler, sondern der BELEG, dass der Filter wirkt. Bei jeder
Soll-Ist-Luecke zuerst pruefen, ob zwischen Fenster und Auswertung eine
Konfigurationsaenderung lag (knowledge/CHANGELOG.md).

Aufruf:
    python scripts/reports/soll_ist.py --week 2026-W37
    python scripts/reports/soll_ist.py --week 2026-W37 --bridge fk
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "scripts" / "reports"
FUNDED_BRIDGE = Path(r"C:\Users\andre\Funded-Portfolio-Bridge")
FK_BRIDGE = Path(r"C:\Users\andre\FKInstantFunding-MT5-Bridge")
EK_BRIDGE = Path(r"C:\Users\andre\EK-Portfolio-Bridge")


# --------------------------------------------------------------- Kostenmodell
# Round-Trip-Gesamtkosten je Broker in Pips, gemessen 2026-09-09 ueber
# scripts/measure_broker_spreads.py. Quelle und Vorbehalte:
# knowledge/resources/broker-kostenmodell-eurusd.md
#
# ZWEI EHRLICHKEITSREGELN, die im Output mitlaufen:
# 1. Die Messwerte gelten NUR fuer EUR/USD im CLS-Handelsfenster. Sie werden
#    deshalb ausschliesslich auf cls_practical angewandt; alle anderen Beine
#    behalten die Kostenannahme ihrer Engine und werden als "Annahme" markiert.
# 2. Abgezogen wird nur die RESTKOSTEN ueber den Spread hinaus, den die Engine
#    bereits berechnet hat (cls_practical/engine.py: spread_bps=0.3, je zur
#    Haelfte auf Entry und Exit) -- sonst wird doppelt belastet.
COST_ROUNDTRIP_PIPS = {
    "funded": 2.05,   # TTPMarkets-Server, gemessen
    "fk": 1.30,       # BeyondIQCapital-Server, gemessen
    "ek": 0.50,       # Tickmill -- GESCHAETZT, Messung vom Nutzer abgelehnt (2026-09-13)
}
COST_PROVENANCE = {"funded": "gemessen", "fk": "gemessen", "ek": "geschaetzt"}
CLS_ENGINE_SPREAD_BPS = 0.3  # cls_practical/engine.py::simulate_cls_practical Default
EURUSD_PIP = 0.0001

# ISO-Zeitstempel innerhalb eines State-Keys (leg_markt_ZEIT_richtung)
_ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


@dataclass
class BridgeSpec:
    key: str
    label: str
    module: str
    live_legs: set[str] | None      # None = alle Beine senden Orders
    state_files: list[Path]          # bridge_state_*.json bzw. [] fuer EK (SQLite)
    uses_magic: bool


def _funded_state_files() -> list[Path]:
    """Nur die Konten, die aktuell in ACCOUNTS stehen -- bridge_state_iqmarkets2.json
    liegt als Historie herum, wird aber seit 2026-09-07 nicht mehr befuellt."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("funded_cfg_si", FUNDED_BRIDGE / "config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [FUNDED_BRIDGE / f"bridge_state_{a.state_id}.json" for a in mod.ACCOUNTS]


def _fk_live_legs() -> set[str]:
    import importlib.util
    spec = importlib.util.spec_from_file_location("fk_cfg_si", FK_BRIDGE / "config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return set(mod.LIVE_LEGS)


def bridge_specs() -> dict[str, BridgeSpec]:
    return {
        "ek": BridgeSpec("ek", "EK-Portfolio-Bridge", "ek_portfolio.paper_bot",
                         None, [], uses_magic=True),
        "funded": BridgeSpec("funded", "Funded-Portfolio-Bridge", "challenge_portfolio.paper_bot",
                             None, _funded_state_files(), uses_magic=False),
        "fk": BridgeSpec("fk", "FKInstantFunding-MT5-Bridge", "fk_instant_funding.paper_bot",
                         _fk_live_legs(), [FK_BRIDGE / "bridge_state.json"], uses_magic=False),
    }


# ------------------------------------------------------------------- Fenster
def week_window(iso_week: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """'2026-W37' -> (Montag 00:00, Freitag 21:00) in UTC-naiv.

    Das Ende liegt bewusst auf FREITAG 21:00, nicht auf Sonntag oder "jetzt":
    ein `end` mitten im Wochenende laesst den "frische Daten seit gestern"-
    Teilfetch mehrerer _scan_*()-Funktionen eine genuin leere Dukascopy-
    Antwort liefern (Wochenende = kein Handel), deren Spalten object- statt
    float-dtype sind; validate_ohlc_numeric() haelt das faelschlich fuer
    korrupte Daten und _retry() erschoepft alle Versuche erfolglos. Fund vom
    2026-09-06, siehe scripts/research_fk_instant_funding_week_reconstruction.py.
    Der echte Bot trifft das nie, weil er am Wochenende gar nicht scannt.
    """
    year, week = iso_week.split("-W")
    monday = datetime.fromisocalendar(int(year), int(week), 1)
    return pd.Timestamp(monday), pd.Timestamp(monday) + pd.Timedelta(days=4, hours=21)


# --------------------------------------------------------------- Soll (Backtest)
def _scan_all(pb, end: pd.Timestamp) -> dict[str, pd.DataFrame]:
    """Ruft jede im jeweiligen paper_bot vorhandene _scan_*()-Funktion auf.

    Die drei Bots haben unterschiedliche Bein-Mengen (EK 8 + ORB, Challenge 6
    + ORB, FK 9) und leicht unterschiedliche Signaturen (manche kennen
    `source=`, manche nicht). Deshalb wird jede Funktion optional behandelt
    und die Signatur zur Laufzeit geprueft, statt drei Sonderfaelle zu pflegen.
    """
    import inspect
    out: dict[str, pd.DataFrame] = {}

    def call(fn_name: str):
        fn = getattr(pb, fn_name, None)
        if fn is None:
            return None
        kwargs = {}
        if "source" in inspect.signature(fn).parameters:
            kwargs["source"] = "lake"
        return pb._retry(lambda: fn(end, False, **kwargs))

    simple = {
        "gold_asb": "_scan_gold_asb",
        "cls_practical": "_scan_cls_practical",
        "trend_pullback": "_scan_trend_pullback",
        "gold_silver": "_scan_gold_silver",
        "btc_ema_cross": "_scan_btc_ema_cross",
    }
    for leg, fn_name in simple.items():
        try:
            df = call(fn_name)
        except Exception as exc:  # noqa: BLE001 -- ein kaputtes Bein darf den Lauf nicht killen
            print(f"    ! {leg}: {type(exc).__name__}: {exc}")
            continue
        if df is not None:
            out[leg] = df

    # ORB liefert alle drei Instrumente in EINEM DataFrame, Spalte "market".
    try:
        orb = call("_scan_orb")
        if orb is not None and not orb.empty:
            for market, sub in orb.groupby("market"):
                out[f"orb_{str(market).lower()}"] = sub
    except Exception as exc:  # noqa: BLE001
        print(f"    ! orb: {type(exc).__name__}: {exc}")

    # CTNL liefert ein Tupel (Continuation, Reversal).
    try:
        ctnl = call("_scan_ctnl")
        if ctnl is not None:
            cont, rev = ctnl
            out["ctnl_continuation"], out["ctnl_reversal"] = cont, rev
    except Exception as exc:  # noqa: BLE001
        print(f"    ! ctnl: {type(exc).__name__}: {exc}")

    # OU-Modell gibt es nur im Challenge-Bot; dort je Einzelaktie (Spalte "market").
    try:
        ou = call("_scan_ou_modell")
        if ou is not None and not ou.empty:
            out["ou_modell"] = ou
    except Exception as exc:  # noqa: BLE001
        print(f"    ! ou_modell: {type(exc).__name__}: {exc}")

    return out


def _cost_r_adjustment(trades: pd.DataFrame, bridge_key: str) -> pd.Series:
    """Restkosten je Trade in R -- nur cls_practical, siehe COST_ROUNDTRIP_PIPS.

    cost_R = (gemessene Round-Trip-Kosten - bereits berechneter Engine-Spread)
             / Stopdistanz. Ergebnis ist immer >= 0 (kein Bonus, wenn die
    Engine mehr angesetzt hat als gemessen -- dann ist der Abzug schlicht 0).
    """
    if "sl_distance" not in trades.columns:
        return pd.Series(0.0, index=trades.index)
    measured = COST_ROUNDTRIP_PIPS[bridge_key] * EURUSD_PIP
    # engine.py: half_spread = price * spread_bps / 10_000 / 2, auf Entry UND Exit
    already = trades["entry_price"].astype(float) * CLS_ENGINE_SPREAD_BPS / 10_000
    residual = (measured - already).clip(lower=0.0)
    return residual / trades["sl_distance"].astype(float)


def build_soll(spec: BridgeSpec, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Backtest-Trades im Fenster + Soll-Rendite nach der Sizing-Formel der Bridge."""
    pb = __import__(spec.module, fromlist=["*"])
    print(f"  Scans {spec.label} bis {end} ...")
    scans = _scan_all(pb, end)

    state = {"trades": {}}
    per_leg: dict[str, dict] = {}
    for leg, df in scans.items():
        if df is None or df.empty:
            continue
        df = df[(pb._utc_naive(df["entry_time"]) >= start) & (pb._utc_naive(df["entry_time"]) <= end)]
        if df.empty:
            continue
        # reset_index: mehrere Engines geben einen nicht-eindeutigen Index zurueck
        # (cls_practical indiziert nach Handelstag, mehrere Trades pro Tag moeglich).
        # Ohne das scheitert jede spaltenweise Rechnung mit "cannot reindex on an
        # axis with duplicate labels".
        df = df.copy().reset_index(drop=True)
        cost_r = _cost_r_adjustment(df, spec.key)
        df["r_multiple_brutto"] = df["r_multiple"].astype(float)
        df["r_multiple"] = df["r_multiple_brutto"] - cost_r
        pb._merge_trades(state, leg, df)
        per_leg[leg] = {
            "trades": int(len(df)),
            "sum_r_brutto": round(float(df["r_multiple_brutto"].sum()), 3),
            "sum_r_netto": round(float(df["r_multiple"].sum()), 3),
            "kosten_r": round(float(cost_r.sum()), 3),
            "kosten_quelle": (COST_PROVENANCE[spec.key] if cost_r.abs().sum() > 0
                              else "Engine-Annahme"),
            "live_bein": spec.live_legs is None or leg in spec.live_legs,
        }

    # Die Sizing-Formel ist rein multiplikativ (risk_dollars ist proportional
    # zur Equity), deshalb ist die RELATIVE Rendite unabhaengig vom Startwert.
    # So laesst sich compute_shared_equity() unveraendert verwenden und das
    # Ergebnis trotzdem auf die echte Kontoequity des Fensters beziehen.
    if spec.key == "ek":
        equity_df = pb.compute_shared_equity(state, pd.Series(dtype=float))
    else:
        equity_df = pb.compute_shared_equity(state)

    rel_return = 0.0
    if not equity_df.empty:
        rel_return = float(equity_df["equity"].iloc[-1]) / pb.STARTING_EQUITY - 1.0

    return {
        "trades": state["trades"],
        "per_leg": per_leg,
        "n_trades": len(state["trades"]),
        "rel_return": round(rel_return, 6),
    }


# --------------------------------------------------------------------- Ist
def _ek_leg_by_magic() -> dict[int, str]:
    import importlib.util
    spec = importlib.util.spec_from_file_location("ek_cfg_si", EK_BRIDGE / "config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {magic: leg for leg, magic in mod.LEG_MAGIC.items()}


def _ticket_to_leg(spec: BridgeSpec) -> dict[int, str]:
    """Funded und FK setzen KEIN Magic (nur EK tut das) -- die Zuordnung
    Live-Trade -> Bein laeuft deshalb ueber die Tickets, die die Bridge beim
    Order-Versand in bridge_state_*.json geschrieben hat.

    Schwaechere Kopplung als Magic: ein Trade, den die Bridge nicht selbst
    eroeffnet hat, ist nicht zuordenbar und wird als "fremd" ausgewiesen --
    genau richtig, denn auf FK lagen am 2026-09-14 zwei Positionen mit
    magic=0 und leerem Kommentar, die NICHT von der Bridge stammen.
    """
    mapping: dict[int, str] = {}
    for path in spec.state_files:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for pos in data.get("positions", {}).values():
            ticket = pos.get("ticket")
            if ticket:
                mapping[int(ticket)] = str(pos.get("leg", "")).split(" (")[0]
    return mapping


def build_ist(spec: BridgeSpec, mt5_data: dict) -> dict:
    """Realisierte P&L je Bein aus den MT5-Deals des Fensters."""
    leg_by_magic = _ek_leg_by_magic() if spec.uses_magic else {}
    leg_by_ticket = {} if spec.uses_magic else _ticket_to_leg(spec)

    per_leg: dict[str, dict] = {}
    unattributed = {"deals": 0, "pnl": 0.0}
    total_pnl = 0.0
    equity_now = 0.0  # Kontostand ZUM ABZUGSZEITPUNKT, nicht zu Fensterbeginn
    accounts_used = []

    for label, rec in mt5_data["accounts"].items():
        if rec.get("bridge") != spec.key or "error" in rec:
            continue
        accounts_used.append(label)
        acc = rec.get("account") or {}
        equity_now += float(acc.get("equity") or 0.0)

        for d in rec.get("deals", []):
            # entry==1 ist der schliessende Deal -- nur der traegt die
            # realisierte P&L. entry==0 (Eroeffnung) hat profit=0.
            if d.get("entry") != 1:
                continue
            pnl = float(d.get("profit") or 0.0) + float(d.get("swap") or 0.0) \
                + float(d.get("commission") or 0.0) + float(d.get("fee") or 0.0)
            total_pnl += pnl

            leg = None
            if spec.uses_magic:
                leg = leg_by_magic.get(int(d.get("magic") or 0))
            else:
                leg = leg_by_ticket.get(int(d.get("position_id") or 0))
                if leg is None:
                    comment = str(d.get("comment") or "")
                    for candidate in leg_by_ticket.values():
                        if candidate and candidate in comment:
                            leg = candidate
                            break
            if not leg:
                unattributed["deals"] += 1
                unattributed["pnl"] += pnl
                continue

            entry = per_leg.setdefault(leg, {"deals": 0, "pnl": 0.0})
            entry["deals"] += 1
            entry["pnl"] += pnl

    for v in per_leg.values():
        v["pnl"] = round(v["pnl"], 2)
    unattributed["pnl"] = round(unattributed["pnl"], 2)

    return {
        "per_leg": per_leg,
        "unattributed": unattributed,
        "total_pnl": round(total_pnl, 2),
        "equity_bei_abzug": round(equity_now, 2),
        # Naeherung: P&L des Fensters bezogen auf den Kontostand beim Abzug.
        # Exakt waere der Stand zu Fensterbeginn -- der steht in MT5 nicht ohne
        # Weiteres bereit; die Abweichung ist bei Wochenfenstern klein.
        "rel_return": round(total_pnl / equity_now, 6) if equity_now else 0.0,
        "accounts": accounts_used,
    }


# ------------------------------------------------------------- Zerlegung
def _decompose_ek(soll: dict) -> dict:
    """EK fuehrt seinen State in SQLite, nicht in bridge_state_*.json.

    Die beiden Tabellen decken nur ab, worauf die Bridge REAGIERT hat:
    `bracket_executions` (dedupe_key SYMBOL_ENTRYZEIT_RICHTUNG, plus status
    z.B. 'risk_cap') und `orb_positions` (nur tagesgenau, kein Signal-
    Zeitstempel). Ein Signal, das der Scan nie geliefert hat, und eines, das
    still uebersprungen wurde, sind hier NICHT unterscheidbar -- solche Faelle
    landen deshalb bewusst in `nicht_ermittelbar` statt faelschlich in
    `nie_gesehen`. Lieber eine ehrliche Luecke als eine falsche Zahl.
    """
    import sqlite3
    db = EK_BRIDGE / "state" / "ek_portfolio_55918977.sqlite3"
    placed_orb: set[tuple[str, str]] = set()
    bracket: dict[str, bool] = {}
    if db.exists():
        con = sqlite3.connect(db)
        try:
            for trade_date, leg, ticket in con.execute(
                    "select trade_date, leg, mt5_ticket from orb_positions"):
                if ticket:
                    placed_orb.add((str(leg), str(trade_date)))
            for leg, dedupe_key, ticket in con.execute(
                    "select leg, dedupe_key, mt5_ticket from bracket_executions"):
                match = _ISO_TS.search(str(dedupe_key) or "")
                if match:
                    bracket[f"{leg}|{match.group(0)[:16]}"] = bool(ticket)
        finally:
            con.close()

    buckets: dict[str, list] = {"nie_gesehen": [], "nicht_platziert": [],
                                "platziert": [], "nicht_ermittelbar": []}
    for t in soll["trades"].values():
        leg, entry = t["leg"], t["entry_time"]
        marker = f"{leg}|{entry[:16]}"
        if marker in bracket:
            bucket = "platziert" if bracket[marker] else "nicht_platziert"
        elif leg.startswith("orb_") and (leg, entry[:10]) in placed_orb:
            bucket = "platziert"
        else:
            bucket = "nicht_ermittelbar"
        buckets[bucket].append({"leg": leg, "entry_time": entry,
                                "r": round(float(t["r_multiple"]), 2),
                                "exit_reason": t.get("exit_reason")})
    return {name: {"n": len(rows), "sum_r": round(sum(r["r"] for r in rows), 2), "trades": rows}
            for name, rows in buckets.items()}


def decompose(spec: BridgeSpec, soll: dict, start: pd.Timestamp) -> dict:
    """Teilt die Soll-Trades in nie_gesehen / nicht_platziert / platziert.

    Bezugsgroesse ist der State der Bridge: was dort gar nicht auftaucht, hat
    der Scan nie geliefert; was mit status='missed' dort steht, hat ein Gate
    verworfen; was ein Ticket hat, wurde platziert.
    """
    # Die State-Keys der Bridges und die Keys aus _merge_trades() sind
    # baugleich aufgebaut (leg_markt_entryzeit_richtung) -- verifiziert am
    # 2026-09-16 gegen FK und Funded. Deshalb exakter Schluesselvergleich wie
    # in research_fk_instant_funding_week_reconstruction.py, mit einem
    # (leg, Entry-Minute)-Fallback fuer die Faelle, in denen eine Bridge einen
    # abweichenden Markt-/Richtungsschluessel schreibt (ou_modell fuehrt den
    # Markt im Bein-Namen statt im Markt-Feld).
    if not spec.state_files:
        return _decompose_ek(soll)

    by_key: dict[str, str] = {}
    by_leg_time: dict[str, str] = {}

    def _record(target: dict, marker: str, status: str) -> None:
        # platziert gewinnt: dasselbe Signal kann auf 3 Konten unterschiedlich enden
        if target.get(marker) != "platziert":
            target[marker] = status

    for path in spec.state_files:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, pos in data.get("positions", {}).items():
            leg = str(pos.get("leg", "")).split(" (")[0]
            status = "platziert" if pos.get("ticket") else "nicht_platziert"
            _record(by_key, key, status)
            match = _ISO_TS.search(key)
            if match:
                _record(by_leg_time, f"{leg}|{match.group(0)[:16]}", status)

    buckets = {"nie_gesehen": [], "nicht_platziert": [], "platziert": []}
    for key, t in soll["trades"].items():
        bucket = by_key.get(key)
        if bucket is None:
            bucket = by_leg_time.get(f"{t['leg']}|{t['entry_time'][:16]}", "nie_gesehen")
        buckets[bucket].append({"leg": t["leg"], "entry_time": t["entry_time"],
                                "r": round(float(t["r_multiple"]), 2),
                                "exit_reason": t.get("exit_reason")})

    return {
        name: {"n": len(rows), "sum_r": round(sum(r["r"] for r in rows), 2), "trades": rows}
        for name, rows in buckets.items()
    }


# -------------------------------------------------------------------- CLI
def run(iso_week: str, bridge_keys: list[str], mt5_path: Path | None) -> dict:
    start, end = week_window(iso_week)
    specs = bridge_specs()

    mt5_data = None
    if mt5_path and mt5_path.exists():
        mt5_data = json.loads(mt5_path.read_text(encoding="utf-8"))
        print(f"IST-Daten aus {mt5_path}")
    else:
        print("IST-Daten werden frisch aus MT5 gezogen ...")
        import mt5_pull
        frm, to = mt5_pull.week_bounds(iso_week)
        mt5_data = mt5_pull.pull(frm, to)

    result = {"week": iso_week, "window": [start.isoformat(), end.isoformat()], "bridges": {}}
    for key in bridge_keys:
        spec = specs[key]
        print(f"\n=== {spec.label} ===")
        soll = build_soll(spec, start, end)
        ist = build_ist(spec, mt5_data)
        result["bridges"][key] = {
            "label": spec.label,
            "soll": soll,
            "ist": ist,
            "zerlegung": decompose(spec, soll, start),
            "kosten_pips": COST_ROUNDTRIP_PIPS[key],
            "kosten_quelle": COST_PROVENANCE[key],
        }
    return result


def print_summary(result: dict) -> None:
    print("\n" + "=" * 72)
    print(f"SOLL/IST {result['week']}  (Fenster {result['window'][0]} bis {result['window'][1]})")
    print("=" * 72)
    for key, b in result["bridges"].items():
        soll, ist, z = b["soll"], b["ist"], b["zerlegung"]
        print(f"\n{b['label']}  [Kosten {b['kosten_pips']} Pips, {b['kosten_quelle']}]")
        print(f"  SOLL : {soll['n_trades']:>3} Trades   Rendite {soll['rel_return']:+.2%}")
        print(f"  IST  : {sum(v['deals'] for v in ist['per_leg'].values()):>3} Deals    "
              f"P&L {ist['total_pnl']:+,.2f}  ({ist['rel_return']:+.2%})")
        if ist["unattributed"]["deals"]:
            print(f"         + {ist['unattributed']['deals']} nicht zuordenbare Deals "
                  f"({ist['unattributed']['pnl']:+,.2f}) -- nicht von dieser Bridge")
        print("  ZERLEGUNG der Soll-Trades:")
        for name in ("platziert", "nicht_platziert", "nie_gesehen", "nicht_ermittelbar"):
            d = z.get(name)
            if d is None or (d["n"] == 0 and name == "nicht_ermittelbar"):
                continue
            print(f"    {name:<18} {d['n']:>3}  Summe R {d['sum_r']:+.2f}")
        if z.get("nicht_ermittelbar", {}).get("n"):
            print("      (EK fuehrt keinen Signal-Ledger je Scan -- 'nie gesehen' und")
            print("       'gesehen, still uebersprungen' sind dort nicht unterscheidbar.)")

        legs = sorted(set(soll["per_leg"]) | set(ist["per_leg"]))
        if legs:
            print("  je Bein:")
            for leg in legs:
                v = soll["per_leg"].get(leg)
                ist_leg = ist["per_leg"].get(leg, {})
                live = "" if (v is None or v["live_bein"]) else "  (nicht live)"
                if v is None:
                    print(f"    {leg:<20} Soll  - kein Signal              "
                          f"       Ist {ist_leg.get('deals', 0):>2} Deals  {ist_leg.get('pnl', 0.0):+9,.2f}")
                else:
                    print(f"    {leg:<20} Soll {v['trades']:>2} Trades  R {v['sum_r_netto']:+6.2f}"
                          f"  (brutto {v['sum_r_brutto']:+6.2f})   Ist {ist_leg.get('deals', 0):>2} Deals"
                          f"  {ist_leg.get('pnl', 0.0):+9,.2f}{live}")


def last_entries(days: int = 30) -> dict[str, dict]:
    """Letzter ECHTER Eroeffnungs-Deal je Bridge -- speist die Dashboard-Spalte
    "Letzter echter Entry".

    Grund fuer die Spalte: der Modus "LIVE" hat im September fuenf Tage lang
    verdeckt, dass FK ueberhaupt nichts ausfuehrte. "Laeuft" und "handelt" sind
    nicht dasselbe.

    Zugeordnet wie in build_ist(): EK ueber Magic, Funded/FK ueber die Tickets
    im bridge_state. Fremdpositionen (magic=0, kein Bridge-Ticket -- z.B. die
    manuellen FK-Positionen vom 2026-09-14) werden getrennt ausgewiesen, damit
    sie nicht als Bridge-Aktivitaet durchgehen. Zeiten sind Broker-Serverzeit.
    """
    import mt5_pull
    to = datetime.now() + pd.Timedelta(days=1)
    data = mt5_pull.pull(to - pd.Timedelta(days=days + 1), to)
    specs = bridge_specs()
    ek_magic = _ek_leg_by_magic()

    result: dict[str, dict] = {}
    for key, spec in specs.items():
        tickets = {} if spec.uses_magic else _ticket_to_leg(spec)
        bridge_last, foreign_last, errors = None, None, []
        for label, rec in data["accounts"].items():
            if rec.get("bridge") != key:
                continue
            if "error" in rec:
                errors.append(f"{label}: {rec['error']}")
                continue
            for d in rec.get("deals", []):
                # entry==0: Eroeffnung; type 0/1: Buy/Sell (Balance-/Kredit-Buchungen raus)
                if d.get("entry") != 0 or d.get("type") not in (0, 1):
                    continue
                if spec.uses_magic:
                    leg = ek_magic.get(int(d.get("magic") or 0))
                else:
                    leg = tickets.get(int(d.get("position_id") or 0))
                row = {"time": d["time_iso"], "leg": leg, "symbol": d["symbol"], "account": label}
                if leg:
                    if bridge_last is None or row["time"] > bridge_last["time"]:
                        bridge_last = row
                elif foreign_last is None or row["time"] > foreign_last["time"]:
                    foreign_last = row
        result[key] = {"label": spec.label, "bridge": bridge_last,
                       "fremd": foreign_last, "fehler": errors}
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Soll/Ist-Vergleich je Bridge.")
    ap.add_argument("--last-entries", action="store_true",
                    help="nur den letzten echten Entry je Bridge ausgeben (Dashboard-Spalte)")
    ap.add_argument("--week", help="ISO-Woche, z.B. 2026-W37")
    ap.add_argument("--bridge", action="append", choices=["ek", "funded", "fk"],
                    help="nur diese Bridge (mehrfach moeglich; Default: alle)")
    ap.add_argument("--mt5-json", help="vorhandener MT5-Abzug statt frischem Pull")
    ap.add_argument("--out", help="Zieldatei (Default: scripts/reports/soll_ist_<woche>.json)")
    args = ap.parse_args()

    if args.last_entries:
        for key, r in last_entries().items():
            b, f = r["bridge"], r["fremd"]
            print(f"{r['label']}")
            print(f"  letzter Bridge-Entry: "
                  + (f"{b['time']}  {b['leg']}  {b['symbol']}  [{b['account']}]" if b else "KEINER in 30 Tagen"))
            if f:
                print(f"  (Fremdposition, zaehlt nicht: {f['time']}  {f['symbol']}  [{f['account']}])")
            for e in r["fehler"]:
                print(f"  ! Konto nicht erreichbar -- {e}")
        return 0
    if not args.week:
        ap.error("--week ist Pflicht (ausser bei --last-entries)")

    bridges = args.bridge or ["ek", "funded", "fk"]
    mt5_path = Path(args.mt5_json) if args.mt5_json else OUT_DIR / f"mt5_{args.week}.json"

    result = run(args.week, bridges, mt5_path)
    print_summary(result)

    out_path = Path(args.out) if args.out else OUT_DIR / f"soll_ist_{args.week}.json"
    out_path.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(f"\nGespeichert: {out_path}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
