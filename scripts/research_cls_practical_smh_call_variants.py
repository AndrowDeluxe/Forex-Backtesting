"""Drei Ideen aus dem SMH-CLS-Praxis-Call (2026-10-21) gegen die LIVE-
Konfiguration von cls_practical. Abgleich und Herleitung:
knowledge/resources/smh-cls-praxis-call.md.

Varianten (je genau eine Aenderung gegen die Basis, 3 gezaehlte Versuche):
  V1 limit_0600  Entry als ruhende Limit-Order am 06:00-Eroeffnungskurs, sobald
                 das Setup um 09:15 feststeht (Order ab 09:30 aktiv, bis 12:00).
                 SL = Extrem zwischen 06:00 und Order-Platzierung. Kein Live-
                 Versatz, weil die Order beim Broker liegt. Liegt der Kurs bei
                 Platzierung schon auf der falschen Seite, kein Trade.
  V2 exit_1200   Basis + Zeitausstieg 12:00 Berlin (Schlusskurs der 11:55-Bar).
  V3 tp_liq      Basis, TP = Range-Gegenseite (Reversal) bzw. Vortages-Hoch/-Tief
                 (Continuation, "externe Liquiditaet"); liegt das Ziel schon
                 hinter dem Einstieg, bleibt das ADR-Ziel.

Basis = Live-Pfad laut research_cls_practical_final_config.py: Pip-Boden 5
(drop), Ausfuehrung 1 M5-Bar nach Signal, Gates "SL schon beruehrt" und
R-Detektor <= 0,50, TTP-Kosten 2,05 Pips Round-Trip.

Ausstiegs-Konvention fuer Basis/V2/V3: Pruefung ab der Bar NACH dem Live-
Einstieg (die Engine prueft ab der Signalbar -- ein TP, der zwischen Signal und
Live-Einstieg lag, zaehlte dort als Gewinn). Zum Vergleich wird die Basis
zusaetzlich in der alten Konvention ausgewiesen. V1 laeuft durch die Engine
selbst (Fuell-Bar zaehlt mit, Stop vor TP = konservativ).

Overfitting-Sperre (knowledge/areas/overfitting-sperre.md): eigener Lock
"cls_practical_smh_call", IS 2018-12-01..2022-05-31, OOS bis 2026-10-20
(Nutzerauftrag: OOS bis heute; kein Tresor). Vorab festgelegte Regel: Gewinner
ist die Variante mit dem hoechsten Oe R auf IS, sofern sie die Basis auf IS
schlaegt UND P(Oe R < 0) < 5 %; sonst wird die Basis eingefroren. OOS zeigt
alle Varianten, entschieden wird nur ueber die eingefrorene.

Aufruf (zwei getrennte Laeufe):
    python scripts/research_cls_practical_smh_call_variants.py --stage is
    python scripts/research_cls_practical_smh_call_variants.py --stage oos
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import challenge_portfolio.paper_bot as pb
import cls_practical.engine as eng
from cls_practical.data import (
    fetch_eurusd_entry_tf_berlin,
    fetch_major_m15_berlin,
    fetch_rate_instrument_m5_berlin,
)
from research_cls_practical_entry_gate import simulate_live_entries
from research_cls_practical_sl_optimization import (
    COSTS_PIPS,
    DEFAULT_END,
    DEFAULT_START,
    OTHER_MAJORS,
    pips_to_bps,
)
from research_lock import Lock, deflated_sharpe

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)

STRATEGY = "cls_practical_smh_call"
IS_START, IS_END, OOS_END = "2018-12-01", "2022-05-31", "2026-10-20"
EXT_START, EXT_END = "2026-09-08", "2026-10-21"
PIP = 0.0001
LAG = 1
MIN_SL_PIPS = 5
GATE_R = 0.50
COST = COSTS_PIPS["TTP"]
HALF = COST * PIP / 2.0
LIVE_RISK_PCT = pb.CAPITAL_WEIGHT * pb.LEG_RISK_PCT["cls_practical"]
TIME_EXIT_MIN = 12 * 60
VARIANTS = ("V1 limit_0600", "V2 exit_1200", "V3 tp_liq")


def load(fn, *args) -> pd.DataFrame:
    """Gecachte Historie bis DEFAULT_END plus kurzer Nachzug bis heute --
    spart den kompletten Neu-Download, den ein neues Enddatum sonst ausloest."""
    a = fn(*args, DEFAULT_START, DEFAULT_END)
    b = fn(*args, EXT_START, EXT_END)
    df = pd.concat([a, b])
    return df[~df.index.duplicated(keep="last")].sort_index()


class Data:
    def __init__(self):
        print(f"Lade Daten {DEFAULT_START}..{EXT_END} ...")
        self.e = load(fetch_eurusd_entry_tf_berlin, "M5")
        self.o = {p: load(fetch_major_m15_berlin, p) for p in OTHER_MAJORS}
        self.b = load(fetch_rate_instrument_m5_berlin, "BUND")
        self.u = load(fetch_rate_instrument_m5_berlin, "USTBOND")
        e = self.e
        self.open = e["open"].to_numpy()
        self.high = e["high"].to_numpy()
        self.low = e["low"].to_numpy()
        self.close = e["close"].to_numpy()
        self.minutes = (e.index.hour * 60 + e.index.minute).to_numpy()
        self.dates = e.index.date
        self.n = len(e)
        self.pos = {t: i for i, t in enumerate(e.index)}
        day = e.groupby(self.dates)
        asia = e[self.minutes < 360].groupby(self.dates[self.minutes < 360])
        self.asia_high, self.asia_low = asia["high"].max(), asia["low"].min()
        dh, dl = day["high"].max(), day["low"].min()
        self.prev_high, self.prev_low = dh.shift(1), dl.shift(1)
        print(f"  EURUSD M5 {e.index[0]} .. {e.index[-1]}, {self.n:,} Bars")

    def engine(self):
        return eng.simulate_cls_practical(
            self.e, self.o, self.b, self.u, risk_pct=LIVE_RISK_PCT,
            spread_bps=pips_to_bps(COST, float(self.e["close"].mean())), slippage_bps=0.0,
            min_sl_pips=MIN_SL_PIPS)


def walk(D: Data, ie: int, d: int, sl: float, tp: float, time_exit: bool):
    """Ausstieg ab der Bar nach dem Live-Einstieg (Bar ie). Stop vor TP."""
    day = D.dates[ie]
    k = ie + 1
    while k < D.n:
        if time_exit and (D.dates[k] != day or D.minutes[k] >= TIME_EXIT_MIN):
            j = max(k - 1, ie)
            return D.close[j] - d * HALF, "time"
        if (D.low[k] <= sl) if d == 1 else (D.high[k] >= sl):
            return sl - d * HALF, "stop"
        if (D.high[k] >= tp) if d == 1 else (D.low[k] <= tp):
            return tp - d * HALF, "take_profit"
        k += 1
    return D.close[D.n - 1] - d * HALF, "data_end"


def live_variant(D: Data, raw: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Basis/V2/V3 auf dem Live-Pfad (Versatz + Gates), Ausstieg neu gerechnet."""
    rows, fallback = [], 0
    for _, t in raw.iterrows():
        i = D.pos.get(t["entry_time"])
        if i is None or i + LAG >= D.n:
            continue
        ie = i + LAG
        d = 1 if t["direction"] == "long" else -1
        sl, tp = float(t["sl"]), float(t["tp"])
        sl_dist = float(t["sl_distance"])
        entry = D.close[ie] + d * HALF
        eff = (entry - sl) * d
        consumed = (sl_dist - eff) / sl_dist
        seg_lo, seg_hi = D.low[i:ie + 1].min(), D.high[i:ie + 1].max()
        touched = (seg_lo <= sl) if d == 1 else (seg_hi >= sl)
        if touched or consumed > GATE_R or eff <= 0:
            continue
        if mode == "V3 tp_liq":
            day = t["date"]
            if t["setup"] == "reversal":
                cand = D.asia_high.get(day) if d == 1 else D.asia_low.get(day)
            else:
                cand = D.prev_high.get(day) if d == 1 else D.prev_low.get(day)
            if cand is not None and np.isfinite(cand) and (cand - entry) * d > 0:
                tp = float(cand)
            else:
                fallback += 1
        exit_px, reason = walk(D, ie, d, sl, tp, time_exit=(mode == "V2 exit_1200"))
        rows.append({"date": t["date"], "setup": t["setup"], "entry_time": D.e.index[ie],
                     "r": d * (exit_px - entry) / eff, "exit_reason": reason})
    out = pd.DataFrame(rows)
    out.attrs["tp_fallback"] = fallback
    return out


def limit_variant(D: Data) -> pd.DataFrame:
    """V1: Engine-Trigger fuer diesen Lauf durch die 06:00-Limit-Logik ersetzt
    (nur im Prozess, engine.py bleibt unveraendert)."""
    skipped = {"falsche Seite": 0, "kein 06:00-Bar": 0}

    def limit(high, low, minutes, i_start, i_end_excl, cutoff_min, d):
        day = D.dates[i_start]
        j = i_start
        while j - 1 >= 0 and D.dates[j - 1] == day and minutes[j - 1] >= 360:
            j -= 1
        if minutes[j] < 360 or j >= i_start:
            skipped["kein 06:00-Bar"] += 1
            return None
        level = D.open[j]
        if (D.close[i_start - 1] - level) * d <= 0:
            skipped["falsche Seite"] += 1
            return None
        sl = low[j:i_start].min() if d == 1 else high[j:i_start].max()
        k = i_start
        while k < i_end_excl and minutes[k] < cutoff_min:
            if (low[k] <= level) if d == 1 else (high[k] >= level):
                return k, level, sl, j, None
            k += 1
        return None

    orig_c, orig_r = eng._continuation_trigger, eng._reversal_trigger
    eng._continuation_trigger = lambda h, l, m, s, e_, c, d, ah, al: limit(h, l, m, s, e_, c, d)
    eng._reversal_trigger = lambda h, l, cl, m, s, e_, c, od, ah, al, sw: limit(h, l, m, s, e_, c, -od)
    try:
        t = D.engine()
    finally:
        eng._continuation_trigger, eng._reversal_trigger = orig_c, orig_r
    t = t.assign(r=t["pnl_usd"] / t["risk_amount_usd"])
    out = t[["date", "setup", "entry_time", "r", "exit_reason"]].copy()
    out.attrs["skipped"] = skipped
    return out


def stats(df: pd.DataFrame, label: str) -> dict:
    r = df["r"].dropna().to_numpy()
    if len(r) < 2:
        return {"Variante": label, "Trades": len(r)}
    gl = -r[r < 0].sum()
    rng = np.random.default_rng(11)
    boot = r[rng.integers(0, len(r), size=(20000, len(r)))].mean(axis=1)
    return {"Variante": label, "Trades": len(r), "Treffer%": 100 * (r > 0).mean(),
            "PF": r[r > 0].sum() / gl if gl else np.inf, "Ø R": r.mean(), "Σ R": r.sum(),
            "Sharpe/Trade": r.mean() / r.std(ddof=1), "P(ØR<0)%": 100 * (boot < 0).mean()}


def window(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    dd = pd.to_datetime(df["date"])
    return df[(dd >= pd.Timestamp(start)) & (dd <= pd.Timestamp(end))]


def build_all(D: Data) -> dict:
    raw = D.engine()
    res = {"Basis (alte Konvention)": simulate_live_entries(
        raw, D.e, LAG, COST, risk_dollars=1.0)}
    old = res["Basis (alte Konvention)"]
    old = old[(~old["sl_touched"]) & (old["consumed_r"] <= GATE_R)].dropna(subset=["r"])
    res["Basis (alte Konvention)"] = old.assign(date=old["entry_time"].dt.date)
    res["Basis"] = live_variant(D, raw, "base")
    res["V2 exit_1200"] = live_variant(D, raw, "V2 exit_1200")
    res["V3 tp_liq"] = live_variant(D, raw, "V3 tp_liq")
    res["V1 limit_0600"] = limit_variant(D)
    return res


def table(res: dict, start: str, end: str) -> pd.DataFrame:
    return pd.DataFrame([stats(window(df, start, end), k) for k, df in res.items()])


def fmt(df: pd.DataFrame) -> str:
    return df.to_string(index=False, float_format=lambda v: f"{v:,.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("is", "oos"), required=True)
    stage = ap.parse_args().stage
    lock = Lock(STRATEGY)
    lock.register_split(IS_START, IS_END, OOS_END)

    D = Data()
    res = build_all(D)
    print(f"\nV1 uebersprungene Setups: {res['V1 limit_0600'].attrs['skipped']}")
    print(f"V3 Ziel-Fallback auf ADR: {res['V3 tp_liq'].attrs['tp_fallback']} Trades (gesamt)")

    print("\n" + "=" * 120)
    print(f"IS {IS_START}..{IS_END} -- TTP-Kosten {COST} Pips, Live-Versatz {LAG} Bar, Gates <= {GATE_R}R")
    print("=" * 120)
    is_tab = table(res, IS_START, IS_END)
    print(fmt(is_tab))

    if stage == "is":
        if lock.trials == 0:
            lock.log_trials(len(VARIANTS), note="SMH-Call: limit_0600, exit_1200, tp_liq")
        print(f"\nVersuche im Register: {lock.trials}")
        for v in VARIANTS:
            for setup in ("continuation", "reversal"):
                sub = window(res[v], IS_START, IS_END)
                sub = sub[sub["setup"] == setup]["r"]
                print(f"  {v:15s} {setup:12s} n={len(sub):3d}  Ø R {sub.mean():+.3f}")
        return

    # ---- OOS: Regel aus dem Docstring, dann genau einmal entsiegeln
    base = is_tab.set_index("Variante").loc["Basis"]
    cand = is_tab[is_tab["Variante"].isin(VARIANTS)].set_index("Variante")
    ok = cand[(cand["Ø R"] > base["Ø R"]) & (cand["P(ØR<0)%"] < 5.0)]
    winner = ok["Ø R"].idxmax() if len(ok) else "Basis"
    w = cand.loc[winner] if winner != "Basis" else base
    dsr = deflated_sharpe(float(w["Sharpe/Trade"]), int(w["Trades"]), max(lock.trials, 1))
    print(f"\nIS-Gewinner nach Vorab-Regel: {winner}  (DSR {dsr:.3f} bei {lock.trials} Versuchen)")
    h = lock.freeze({"winner": winner, "variants": list(VARIANTS), "cost_pips": COST,
                     "lag": LAG, "gate_r": GATE_R, "min_sl_pips": MIN_SL_PIPS})
    start, end = lock.unseal("oos", h)
    print("\n" + "=" * 120)
    print(f"OOS {start}..{end} (einmalig geoeffnet) -- entschieden wird nur ueber: {winner}")
    print("=" * 120)
    print(fmt(table(res, start, end)))
    live_start = "2026-09-07"
    print(f"\n  davon seit Livegang ({live_start}..{end}), einzig unverbrauchter Teil:")
    print(fmt(table(res, live_start, end)))
    yr = []
    for k, df in res.items():
        if k == "Basis (alte Konvention)":
            continue
        s = window(df, start, end)
        g = s.groupby(pd.to_datetime(s["date"]).dt.year)["r"].mean()
        yr.append(g.rename(k))
    print("\n  Ø R je Jahr (OOS):")
    print(pd.concat(yr, axis=1).to_string(float_format=lambda v: f"{v:+.3f}"))

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "smh_call_variants_trades.csv"
    pd.concat([df.assign(variante=k) for k, df in res.items()
               if k != "Basis (alte Konvention)"]).to_csv(out, index=False)
    print(f"\nGespeichert: {out}")


if __name__ == "__main__":
    main()
