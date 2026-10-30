"""Stufe 2: A2 nackt gegen A2 mit Dennis' Nachfass-Anweisungen (Edge Card Regel 17,
Nutzerentscheid 28.10.2026). Dieselben Einstiege, drei Varianten:
  nackt  = eingefrorenes A2 (oos.FROZEN), ohne Anweisungen
  fest   = nur verbindliche Anweisungen ("BE ziehen", "raus", "ich zieh BE")
  alle   = auch weiche ("koennte", "bei Bedarf", "muss man aber nicht")
Die Differenz fest/alle minus nackt misst allein Dennis' Management.

Zuordnung (instructions.jsonl -> Trades): gleiches Symbol, Call vor der Anweisung gepostet,
Zeitbezug aus "scope". Wirksam ab Postzeit + 5 Min. (sim.LAG).
  be       -> Stop auf Entry; steht der Kurs unter dem Entry: schliessen (exits.run)
  close    -> Ausstieg zum Kurs; wartende Order wird gestrichen
  invalide -> wartende Order gestrichen; laufender Trade laeuft weiter (Regel 7)
  partial  -> Teilschluss, Anteil laut Text, sonst 50 % (ANNAHME)
  risk_split k -> Gewicht 1/k (geteiltes Risiko)
  reentry_hint -> nur protokolliert (ohne Level nicht kopierbar)

    python -m fusion_lab.copy_trading.stage2 --is        # Vorab-Blick IS (beschreibend)
    python -m fusion_lab.copy_trading.stage2 --freeze    # Varianten + Lesung einfrieren
    python -m fusion_lab.copy_trading.stage2 --forward   # Forward-Ledger fortschreiben
"""

import argparse
import json
import sys

import numpy as np
import pandas as pd

from fusion_lab.copy_trading import data, grid, instructions, oos, sim
from research_lock import Lock

LOCK = Lock("copy_trading_stufe2_20261028")
BASE_HASH = "71a02c43ead6f09d907f3d2640d1374adea64b391254b275591c0a60f3a46633"   # A2, Lock 20261020
VARIANTS = ("nackt", "fest", "alle")
PARTIAL_DEFAULT = 0.5
FWD_EVAL, FWD_MIN = "2027-03-31", 100
# Alter des Calls bei der Anweisung je Zeitbezug (ANNAHME 28.10.2026; Wochenende eingerechnet)
SCOPE_AGE = {"today": (pd.Timedelta(0), pd.Timedelta(hours=24)),
             "yesterday": (pd.Timedelta(hours=6), pd.Timedelta(days=4)),
             "last_week": (pd.Timedelta(days=2), pd.Timedelta(days=14)),
             "any": (pd.Timedelta(0), pd.Timedelta(days=30))}


def setup_lock() -> None:
    s = grid.LOCK.split
    LOCK.register_split(s["is_start"], s["is_end"], s["oos_end"], s["tresor_end"])
    LOCK.register_forward(instructions.FWD_START, FWD_EVAL, FWD_MIN)
    LOCK.skip_oos("OOS 01.04.-16.10.2026 durch A2 (Lock copy_trading_daily_update_20261020) "
                  "am 27.10.2026 verbraucht; Stufe 2 nur IS-Vorab + Forward")
    if LOCK.trials == 0 and LOCK._load()["frozen"] is None:
        LOCK.log_trials(2, "Stufe 2: Anweisungen fest / alle (nackt = eingefrorenes A2, kein Versuch)")


def items() -> list[dict]:
    out = []
    for r in instructions.load():
        t = pd.Timestamp(r["date"]).tz_convert("UTC")
        for k, x in enumerate((r["read"] or {}).get("instructions") or []):
            syms = {data.norm_symbol(s) for s in x.get("symbols") or []} - {None}
            out.append({"msg_id": r["msg_id"], "k": k, "t": t, "t_eff": t + sim.LAG,
                        "action": x.get("action"), "strength": x.get("strength"), "syms": syms,
                        "scope": x.get("scope") if x.get("scope") in SCOPE_AGE else "any",
                        "split": x.get("split"), "fraction": x.get("fraction")})
    return out


def matches(it: dict, c) -> bool:
    lo, hi = SCOPE_AGE[it["scope"]]
    age = it["t"] - c.t_post
    return c.sym in it["syms"] and lo <= age <= hi


def make_hook(its: list[dict], variant: str, used: dict):
    its = [i for i in its if variant == "alle" or i["strength"] == "fest"]

    def hook(e: dict) -> dict:
        c = e["c"]
        ev, cancel, w, notes = [], None, 1.0, []
        for it in its:
            if not matches(it, c):
                continue
            a, tn = it["action"], it["t_eff"].value
            if a in ("be", "close"):
                ev.append((tn, a, None))
                if a == "close":
                    cancel = tn if cancel is None else min(cancel, tn)
            elif a == "invalide":
                cancel = tn if cancel is None else min(cancel, tn)
            elif a == "partial":
                ev.append((tn, "partial", float(it["fraction"] or PARTIAL_DEFAULT)))
            elif a == "risk_split" and it["split"]:
                w = min(w, 1 / float(it["split"]))
            else:
                continue
            notes.append(f"{a}@{it['msg_id']}")
            used.setdefault((it["msg_id"], it["k"]), set()).add(c.msg_id)
        return {"events": ev, "cancel": cancel, "weight": w, "notes": " ".join(notes)}

    return hook


def run_all(cs: list, its: list[dict]) -> tuple[dict, dict]:
    markets: dict = {}
    ents = grid.entries(cs, oos.FROZEN["etype"], markets)
    cfg = {k: v for k, v in oos.FROZEN.items() if k != "etype"}
    out, used = {"nackt": grid.evaluate(ents, cfg, markets)}, {}
    for v in VARIANTS[1:]:
        out[v] = grid.evaluate(ents, cfg, markets, hook=make_hook(its, v, used if v == "alle" else {}))
    return out, used


def wstats(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"n": 0}
    w = tr["weight"] if "weight" in tr else pd.Series(1.0, index=tr.index)
    r = tr["r"]
    st = grid.stats(tr)
    return {**st, "avg_r_gewichtet": float((w * r).sum() / w.sum()), "sum_r_gewichtet": float((w * r).sum()),
            "median_r": float(r.median()), "top5": float(r.nlargest(5).sum()),
            "long": grid.stats(tr[tr["dir"] > 0])["avg_r"], "short": grid.stats(tr[tr["dir"] < 0])["avg_r"],
            "exits": tr["exit"].value_counts().to_dict(),
            "mit_anweisung": int((tr["notes"] != "").sum()) if "notes" in tr else 0}


def audit(its: list[dict], used: dict, lo, hi) -> dict:
    inwin = [i for i in its if lo <= i["t"] < hi]
    acts = [i for i in inwin if i["action"] != "reentry_hint"]
    return {"anweisungen": len(acts),
            "fest": sum(i["strength"] == "fest" for i in acts),
            "ohne_symbol": sum(not i["syms"] for i in acts),
            "auf_trade_bezogen": sum((i["msg_id"], i["k"]) in used for i in acts),
            "je_aktion": pd.Series([i["action"] for i in inwin]).value_counts().to_dict()}


def is_run() -> int:
    setup_lock()
    s = LOCK.split
    lo, hi = pd.Timestamp(s["is_start"], tz="UTC"), pd.Timestamp(s["is_end"], tz="UTC") + pd.Timedelta(days=1)
    its = items()
    res, used = run_all(oos.calls_between(s["is_start"], s["is_end"]), its)
    rep = {v: wstats(tr) for v, tr in res.items()}
    rep["audit"] = audit(its, used, lo, hi)
    # Paarvergleich: gleiche Trades (nackt vs. Variante), nur dort, wo eine Anweisung griff
    key = ["msg_id", "t_in", "p_in", "sl", "dir"]
    nk = res["nackt"].assign(j=res["nackt"].groupby(key).cumcount())   # Doppel-Lesungen getrennt halten
    for v in VARIANTS[1:]:
        vk = res[v].assign(j=res[v].groupby(key).cumcount())
        m = nk[key + ["j", "r"]].merge(vk[key + ["j", "r", "notes"]], on=key + ["j"], suffixes=("_n", "_v"))
        d = m["r_v"] - m["r_n"]
        ch = d[d.abs() > 1e-9]
        top5 = m["r_n"].nlargest(5).index
        rep[f"paar_{v}"] = {"n_veraendert": len(ch), "delta_sum": float(ch.sum()),
                            "delta_median": float(ch.median()) if len(ch) else None,
                            "delta_ohne_top5_nackt": float(ch[~ch.index.isin(top5)].sum()),
                            "gestrichen": len(res["nackt"]) - len(m)}
        res[v].to_csv(grid.RES / f"stufe2_is_{v}.csv", index=False)
    print(json.dumps(rep, indent=1, default=lambda x: round(float(x), 3) if isinstance(x, (float, np.floating)) else str(x)))
    (grid.RES / "stufe2_is.json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    return 0


def freeze() -> int:
    setup_lock()
    h = LOCK.freeze({"basis_hash": BASE_HASH, "basis": oos.FROZEN, "varianten": list(VARIANTS[1:]),
                     "anweisungen_prompt_version": instructions.PROMPT_VERSION,
                     "scope_age": {k: [str(a), str(b)] for k, (a, b) in SCOPE_AGE.items()},
                     "partial_default": PARTIAL_DEFAULT})
    print(f"eingefroren: {h}")
    return 0


def forward() -> int:
    if LOCK._load()["frozen"] is None:
        print("Stufe 2 noch nicht eingefroren -- erst --freeze")
        return 1
    data.EXTEND = True
    today = pd.Timestamp.now("UTC").strftime("%Y-%m-%d")
    lo = pd.Timestamp(instructions.FWD_START, tz="UTC")
    its = items()
    res, used = run_all(oos.calls_between(instructions.FWD_START, today), its)
    frames = [tr.assign(variante=v) for v, tr in res.items() if not tr.empty]
    if frames:
        pd.concat(frames).to_csv(grid.RES / "forward_stufe2_trades.csv", index=False)
    n = {v: int(len(tr)) for v, tr in res.items()}
    closed = {v: int((tr["exit"] != "offen").sum()) if not tr.empty else 0 for v, tr in res.items()}
    stand = {"stand": today, "trades": n, "geschlossen": closed, "auswertung_ab": FWD_EVAL,
             "min_trades": FWD_MIN, "audit": audit(its, used, lo, pd.Timestamp(today, tz="UTC") + pd.Timedelta(days=1))}
    (grid.RES / "forward_stufe2_stand.json").write_text(json.dumps(stand, indent=2, default=str), encoding="utf-8")
    # Bewusst keine R-Zahlen ausgeben: Auswertung erst am Stichtag (Overfitting-Sperre)
    print(f"Forward Stufe 2 Stand {today}: Trades {n}, geschlossen {closed}, "
          f"Anweisungen {stand['audit']['anweisungen']} (zugeordnet {stand['audit']['auf_trade_bezogen']})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--is", dest="is_", action="store_true")
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--forward", action="store_true")
    a = ap.parse_args(argv)
    return is_run() if a.is_ else freeze() if a.freeze else forward()


if __name__ == "__main__":
    sys.exit(main())
