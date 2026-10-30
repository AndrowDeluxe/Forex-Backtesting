"""Stufe 3: Gueltigkeit, SL, TP, Break-even und Trailing auf Basis der Calls (Nutzerauftrag
21.10.2026). NUR IS (Calls bis 31.03.2026, Lock copy_trading_daily_update_20261020), jede
gerechnete Kombination wird gezaehlt.

Suche schrittweise je Einstiegstyp (A1, A2, B1, B2), Reihenfolge fest:
  Gueltigkeit -> SL -> TP -> Break-even -> Trailing.
Je Schritt bleibt der Wert mit dem hoechsten t-Wert des Ø R (mind. MIN_N Trades) stehen.
Abbruchregel und Reihenfolge sind vor dem ersten Lauf festgelegt.

Re-Entry (Nutzer 21.10.): Postet jemand einen Call erneut (gleiches Symbol, gleiche Richtung,
Level innerhalb 0,15 %), waehrend der Trade daraus noch laeuft, ist das KEIN neuer Call. Ist
der fruehere Trade schon geschlossen, zaehlt er als Re-Entry (Spalte re_entry).

    python -m fusion_lab.copy_trading.grid
"""

import json
import sys

import numpy as np
import pandas as pd

from fusion_lab.copy_trading import data, exits, sim
from fusion_lab.copy_trading.extract import CALLS, OUT_DIR
from research_lock import Lock

LOCK = Lock("copy_trading_daily_update_20261020")
RES = OUT_DIR / "results"
MIN_N = 30
SAME_LEVEL = 0.0015

VALIDITY = ["update", 1, 2, 3, 5]                      # Handelstage
SL = ["struct", "swing", "atr1", "atr1.5", "atr2"]      # struct: A = SL-Label, B = Zonenrand
TP = ["struct", "1R", "2R", "3R", "none"]               # struct: A = TP-Label, B = Pfadende
BE = [None, 0.5, 1.0]
TRAIL = [None, ("atr", 1.5, 1.0), ("atr", 2.5, 1.0), ("swing",)]
ENTRY_TYPES = ["A1", "A2", "B1", "B2", "P1"]   # P1: Pfad-Trade zum Markt (Lesart 1, 21.10.)
BASE = {"validity": "update", "sl": "struct", "tp": "struct", "be": None, "trail": None}


# ----------------------------------------------------------------------------- Vorbereitung
def is_calls() -> list:
    split = LOCK.split
    lo = pd.Timestamp(split["is_start"], tz="UTC")
    hi = pd.Timestamp(split["is_end"], tz="UTC") + pd.Timedelta(days=1)
    calls, _ = sim.load_calls(CALLS)
    return [c for c in calls if lo <= c.t_post < hi]


def with_validity(calls: list, validity) -> list:
    import copy
    cs = [copy.copy(c) for c in calls]
    end = pd.Timestamp(LOCK.split["is_end"], tz="UTC") + pd.Timedelta(days=120)  # Trades duerfen auslaufen
    sim.assign_validity(cs, end)
    if validity != "update":
        for c in cs:
            t_fix = c.t_post + pd.offsets.BDay(int(validity))
            same = [o.t_post for o in cs if o.sym == c.sym and o.t_post > c.t_post and o.drop is None]
            c.t_valid = min([t_fix] + same)
    return cs


class Arrays:
    def __init__(self, mk: sim.Market):
        m = mk.m1
        self.mk = mk
        # Parquet liefert ms; die Arrays rechnen in ns
        self.a = {"t": m.index.as_unit("ns").asi8, "o": m["open"].to_numpy(), "h": m["high"].to_numpy(),
                  "l": m["low"].to_numpy(), "c": m["close"].to_numpy()}
        self._sw = {}

    def swings(self, tf: str, side: str):
        if (tf, side) not in self._sw:
            df = self.mk.tf(tf)
            col = "swing_low" if side == "low" else "swing_high"
            m = df[f"{col}_confirmed"].to_numpy()
            self._sw[(tf, side)] = (pd.DatetimeIndex(df["t_close"]).as_unit("ns").asi8[m],
                                    df[f"{col}_price"].to_numpy()[m])
        return self._sw[(tf, side)]


def entries(calls: list, etype: str, markets: dict) -> list[dict]:
    """Einstiege eines Typs (unabhaengig vom Ausstieg). BOS: Setup tot, wenn vor dem Einstieg
    die strukturelle Invalidierung (A: SL-Label, B: ferner Zonenrand) erreicht wird."""
    typ, mode = etype[0], etype[1]
    out = []
    for c in calls:
        if c.drop or c.typ != typ:
            continue
        if c.sym not in markets:
            markets[c.sym] = Arrays(sim.Market(c.sym))
        mk = markets[c.sym].mk
        px = mk.price_at(c.t_post)
        if px is None or abs(c.level / px - 1) > sim.MAX_DIST:
            continue
        t_act = c.t_post + sim.LAG
        if typ == "P":
            # Ziel muss vor uns liegen und darf zwischen Chart und Post nicht erreicht sein
            if (c.tp - px) * c.d <= 0:
                continue
            t_chart = c.t_chart if c.t_chart is not None and c.t_chart <= c.t_post else c.t_post - pd.Timedelta(minutes=30)
            if sim.first_touch(mk.m1, t_chart, t_act, c.tp, -c.d) is not None:
                continue
            i = mk.m1.index.searchsorted(t_act)
            if i >= len(mk.m1):
                continue
            out.append({"c": c, "t_in": mk.m1.index[i], "p_in": float(mk.m1["open"].iat[i]),
                        "fill_bar": False})
            continue
        if typ == "B" and (px - c.level) * c.d <= 0:
            continue  # Zone nicht auf der Ruecksetzer-Seite
        t_chart = c.t_chart if c.t_chart is not None and c.t_chart <= c.t_post else c.t_post - pd.Timedelta(minutes=30)
        if sim.first_touch(mk.m1, t_chart, c.t_post, c.touch, c.d) is not None:
            continue
        e = (sim.static_entry if mode == "1" else sim.bos_entry)(mk, c, t_act)
        if e is None:
            continue
        t_in, p_in = e
        inval = c.sl if typ == "A" else (c.z_lo if c.d > 0 else c.z_hi)
        if mode == "2" and sim.first_touch(mk.m1, t_act, t_in, inval, c.d) is not None:
            continue
        out.append({"c": c, "t_in": t_in, "p_in": p_in, "fill_bar": mode == "1"})
    return out


def stop_target(e: dict, cfg: dict, arr: Arrays):
    c, p_in, t_in = e["c"], e["p_in"], e["t_in"]
    mk = arr.mk
    atr = sim.atr_at(mk, c.tf, t_in)
    s = cfg["sl"]
    if s == "struct":
        if c.typ == "P":
            return None
        sl = c.sl if c.typ == "A" else (c.z_lo if c.d > 0 else c.z_hi)
    elif s == "swing":
        sl = sim.htf_level(mk, c.tf, t_in, p_in, "low" if c.d > 0 else "high")
    else:
        sl = p_in - c.d * float(s[3:]) * atr if atr else None
    if sl is None or (p_in - sl) * c.d <= 0:
        return None
    risk = abs(p_in - sl)
    t = cfg["tp"]
    if t == "struct":
        tp = c.tp if c.typ in ("A", "P") else c.path_end
        if tp is None or (tp - p_in) * c.d <= 0:
            return None
    elif t == "none":
        tp = None
    else:
        tp = p_in + c.d * float(t[0]) * risk
    return sl, tp, atr


def evaluate(ents: list[dict], cfg: dict, markets: dict, hook=None) -> pd.DataFrame:
    """hook (Stufe 2): hook(e) -> {"cancel": t_ns | None, "events": [...], "weight": float,
    "notes": str}. cancel vor dem Einstieg streicht die Order; events gehen an exits.run;
    weight ist der Risikoanteil (z. B. 1/3 bei geteiltem Risiko)."""
    rows, running = [], []
    for e in sorted(ents, key=lambda e: e["t_in"]):
        c = e["c"]
        arr = markets[c.sym]
        # Re-Entry-Regel: Repost eines noch laufenden Trades ist kein neuer Call
        same = [r for r in running if r["sym"] == c.sym and r["dir"] == c.d
                and abs(r["level"] / c.level - 1) <= SAME_LEVEL and r["t_in"] < c.t_post]
        if any(r["t_out"] > c.t_post for r in same):
            continue
        st = stop_target(e, cfg, arr)
        if st is None:
            continue
        sl, tp, atr = st
        h = hook(e) if hook else {}
        if h.get("cancel") is not None and h["cancel"] <= e["t_in"].value:
            continue
        a = arr.a
        i0 = int(np.searchsorted(a["t"], e["t_in"].value, side="left"))
        side = "low" if c.d > 0 else "high"
        sw = arr.swings(c.tf, side)
        if cfg["trail"] is not None and cfg["trail"][0] == "swing":
            keep = sw[0] > e["t_in"].value
            sw = (sw[0][keep], sw[1][keep])
        i_out, p_out, why = exits.run(a, i0, c.d, e["p_in"], sl, tp, cfg["be"], cfg["trail"], atr, sw,
                                      e["fill_bar"], h.get("events"))
        risk = abs(e["p_in"] - sl)
        cost = data.roundtrip_cost(c.sym, e["p_in"])
        r_g = (p_out - e["p_in"]) * c.d / risk
        rec = {"msg_id": c.msg_id, "sym": c.sym, "tf": c.tf, "dir": c.d, "typ": c.typ,
               "t_post": c.t_post, "t_in": e["t_in"], "p_in": e["p_in"], "sl": sl, "tp": tp,
               "t_out": pd.Timestamp(a["t"][i_out], tz="UTC"), "p_out": p_out, "exit": why,
               "r_gross": r_g, "r": r_g - cost / risk, "re_entry": bool(same),
               "level": c.level}
        if hook:
            rec.update(weight=h.get("weight", 1.0), notes=h.get("notes", ""))
        rows.append(rec)
        running.append({"sym": c.sym, "dir": c.d, "level": c.level, "t_in": e["t_in"],
                        "t_out": rec["t_out"]})
    return pd.DataFrame(rows)


def stats(tr: pd.DataFrame) -> dict:
    n = len(tr)
    if n < 2:
        return {"n": n, "avg_r": np.nan, "t": np.nan, "sum_r": tr["r"].sum() if n else 0.0, "treffer": np.nan}
    r = tr["r"]
    sd = r.std(ddof=1)
    return {"n": n, "avg_r": r.mean(), "t": r.mean() / sd * np.sqrt(n) if sd > 0 else np.nan,
            "sum_r": r.sum(), "treffer": (r > 0).mean()}


# ----------------------------------------------------------------------------- Suche
def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    base_calls = is_calls()
    print(f"IS-Calls (Setups): {len(base_calls)}")
    markets: dict = {}
    log = []
    best_all = {}
    for etype in ENTRY_TYPES:
        cfg = dict(BASE)
        dims = [("validity", VALIDITY), ("sl", SL), ("tp", TP), ("be", BE), ("trail", TRAIL)]
        if etype == "P1":   # Markt-Einstieg: keine Gueltigkeit, kein struktureller SL
            cfg["sl"] = "atr1.5"
            dims = [("sl", [v for v in SL if v != "struct"]), ("tp", TP), ("be", BE), ("trail", TRAIL)]
        ent_cache = {}
        for dim, values in dims:
            results = []
            for v in values:
                trial = {**cfg, dim: v}
                key = trial["validity"]
                if key not in ent_cache:
                    ent_cache[key] = entries(with_validity(base_calls, key), etype, markets)
                tr = evaluate(ent_cache[key], trial, markets)
                st = stats(tr)
                results.append((v, st))
                log.append({"etype": etype, "dim": dim, **{k: str(x) for k, x in trial.items()}, **st})
            LOCK.log_trials(len(values), f"Stufe 3 {etype} {dim}: {values}")
            ok = [(v, s) for v, s in results if s["n"] >= MIN_N and pd.notna(s["t"])]
            if ok:
                cfg[dim] = max(ok, key=lambda vs: vs[1]["t"])[0]
            print(f"{etype} {dim:8s} -> {cfg[dim]}  " +
                  "  ".join(f"{v}: n={s['n']} R={s['avg_r']:+.3f} t={s['t']:+.2f}" for v, s in results))
        tr = evaluate(ent_cache[cfg["validity"]], cfg, markets)
        best_all[etype] = {"cfg": cfg, **stats(tr)}
        tr.to_csv(RES / f"stufe3_is_{etype}_best.csv", index=False)
    pd.DataFrame(log).to_csv(RES / "stufe3_is_suche.csv", index=False)
    (RES / "stufe3_is_beste.json").write_text(json.dumps(best_all, indent=2, default=str), encoding="utf-8")
    print(f"\nVersuche gesamt im Lock: {LOCK.trials}")
    for k, v in best_all.items():
        print(k, v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
