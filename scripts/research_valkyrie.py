"""Quantum Valkyrie: Klon unter der Overfitting-Sperre, Blindtest auf den vom EA gesperrten Jahren.

Plan: ~/.claude/plans/bubbly-coalescing-pumpkin.md. Regeln wurden nur auf Uebereinstimmung
mit den MT5-Berichten kalibriert, nie auf Gewinn. Diese Berichte decken 2020-2026 ab und
zeigen auch die Ergebnisse des EA. OOS und Tresor sind deshalb nicht blind gegenueber der
Regelherleitung; wirklich unberuehrt ist nur der Blindtest 2018-01-01 .. 2020-01-16.

KLON (fest): Momentum-Ausloeser (Koerper > 0, 4-Kerzen-Bewegung > 1 ATR), je Pivot eine Order,
Level = max(Pivot 12/6, Ask + 0,30), SL = clamp(3,5 x ATR100, 15, 60), TP 50, Ablauf 29,75 h,
Trailing 0,22 x SL / 0,50 $, Max-Spread 0,30. Der Ausloeser feuert rund 5x zu oft.
KONTROLLE: gleiche Pivots und Orderzahl, aber Zufallskerze statt Ausloeser (Seed fest).

BESTEHEN (vor dem ersten Lauf festgelegt): in Blindtest, OOS und Tresor je Oe R > 0 und t >= 2
nach 0,30 $ Kosten je Trade. Kontrolle wird nur berichtet.

  python scripts/research_valkyrie.py --stage is     # IS auswerten, nichts oeffnen
  python scripts/research_valkyrie.py --stage open   # einfrieren, Blindtest/OOS/Tresor je einmal
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mt5_valkyrie.data import bars, load_m1  # noqa: E402
from mt5_valkyrie.engine import EXPIRY, Ticks, fill, manage  # noqa: E402
from mt5_valkyrie.ohlc_ticks import ticks  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "valkyrie_klon_20261030"
IS_START, IS_END, OOS_END, TRESOR_END = "2020-01-17", "2023-12-31", "2025-10-27", "2026-10-16"
BLIND_START, BLIND_END = "2018-01-01", "2020-01-16"
CONFIG = dict(trigger="body>0,ret4>1ATR", pivot=(12, 6), min_dist=0.30, sl=(3.5, 100, 15, 60), tp=50,
              trail=(0.22, 0.5, 0.1), max_spread=0.30, expiry_h=29.75)
COSTS = (0.0, 0.10, 0.30)
RES = ROOT / "mt5_valkyrie" / "results"


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    lk.register_blind(BLIND_START, BLIND_END)
    return lk


def pivots(e: np.ndarray, kl: int = 12, kr: int = 6) -> np.ndarray:
    p = [i for i in range(kl, len(e) - kr) if e[i] >= e[i - kl:i].max() and e[i] > e[i + 1:i + kr + 1].max()]
    return np.array(p, dtype=int)


class Market:
    def __init__(self):
        m1 = load_m1("2018-01-01")
        self.tk = Ticks.from_frame(ticks(m1))
        b = bars(m1)
        self.T = b.index.to_numpy()
        self.H, self.L, self.C, self.O = (b[k].to_numpy() for k in ("high", "low", "close", "open"))
        pc = np.r_[np.nan, self.C[:-1]]
        tr = np.maximum(self.H, pc) - np.minimum(self.L, pc)
        self.atr = pd.Series(tr).rolling(100).mean().to_numpy()
        self.sp = m1["spread"].reindex(b.index).fillna(10).to_numpy() / 100
        self.piv = {1: pivots(self.H), -1: pivots(-self.L)}


def _order(mk: Market, J: int, s: int, i: int):
    """Order zur Eroeffnung der Kerze J auf Pivot i; None bei zu hohem Spread."""
    if mk.sp[J] > CONFIG["max_spread"] or not np.isfinite(mk.atr[J - 1]):
        return None
    ask = mk.O[J] + mk.sp[J]
    if s > 0:
        level = max(mk.H[i], ask + CONFIG["min_dist"])
    else:
        level = min(mk.L[i], mk.O[J] - CONFIG["min_dist"])
    sl_d = float(np.clip(3.5 * mk.atr[J - 1], 15, 60))
    return dict(J=J, s=s, level=level, sl=level - s * sl_d, tp=level + s * CONFIG["tp"], sl_d=sl_d)


def signals(mk: Market, start: str, end: str, control: bool = False, seed: int = 7) -> list[dict]:
    """Je Pivot hoechstens eine Order; Fenster von Bestaetigung bis naechstem Pivot."""
    rng = np.random.default_rng(seed)
    t0, t1 = np.datetime64(start), np.datetime64(end) + np.timedelta64(1, "D")
    out = []
    for s in (1, -1):
        cond = ((mk.C - mk.O) * s > 0) & (np.r_[np.full(4, np.nan), (mk.C[4:] - mk.C[:-4]) * s] > mk.atr)
        piv = mk.piv[s]
        for a, i in enumerate(piv):
            st, en = i + 7, (piv[a + 1] + 7 if a + 1 < len(piv) else len(mk.T) - 1)
            if en <= st or not (t0 <= mk.T[st] < t1):
                continue
            w = np.nonzero(cond[st - 1:en - 1])[0]
            if not len(w):
                continue
            J = int(rng.integers(st, en)) if control else st + int(w[0])
            if t0 <= mk.T[J] < t1 and (o := _order(mk, J, s, i)):
                out.append(o)
    return out


def simulate(mk: Market, orders: list[dict]) -> pd.DataFrame:
    rows = []
    for o in orders:
        i0 = fill(mk.tk, o["s"], o["level"], mk.T[o["J"]], EXPIRY)
        if i0 is None:
            continue
        i, px = manage(mk.tk, i0, o["s"], o["level"], o["sl"], o["tp"])
        rows.append(dict(t_in=pd.Timestamp(mk.tk.t[i0]), t_out=pd.Timestamp(mk.tk.t[i]), s=o["s"], sl_d=o["sl_d"],
                         usd=(px - o["level"]) * o["s"]))
    return pd.DataFrame(rows).sort_values("t_in").reset_index(drop=True)


def stats(tr: pd.DataFrame, n_trials: int = 1, seed: int = 11) -> dict:
    out = dict(n=len(tr), win=round((tr.usd > 0).mean(), 3))
    for c in COSTS:
        r = (tr.usd - c) / tr.sl_d
        t = r.mean() / r.std(ddof=1) * np.sqrt(len(r))
        pf = r[r > 0].sum() / -r[r < 0].sum()
        out[f"c{c:.2f}"] = dict(avg_r=round(r.mean(), 4), sum_r=round(r.sum(), 1), t=round(t, 2), pf=round(pf, 2))
    r = (tr.usd - 0.30) / tr.sl_d
    out["dsr_c0.30"] = round(deflated_sharpe(r.mean() / r.std(ddof=1), len(r), n_trials, r.skew(), r.kurt() + 3), 3)
    rng = np.random.default_rng(seed)
    boot = rng.choice(r.to_numpy(), size=(2000, len(r)))
    eq = boot.cumsum(axis=1)
    dd = (np.maximum.accumulate(eq, axis=1) - eq).max(axis=1)
    out["mc"] = dict(p_loss=round((eq[:, -1] <= 0).mean(), 3), dd95_r=round(np.quantile(dd, 0.95), 1))
    out["years"] = r.groupby(tr.t_in.dt.year).sum().round(1).to_dict()
    return out


def run_stage(mk: Market, name: str, start: str, end: str, n_trials: int) -> None:
    clone = simulate(mk, signals(mk, start, end))
    ctrl = simulate(mk, signals(mk, start, end, control=True))
    clone.to_parquet(RES / f"klon_{name}.parquet")
    ctrl.to_parquet(RES / f"kontrolle_{name}.parquet")
    print(name, start, end)
    print("  Klon     ", stats(clone, n_trials), flush=True)
    print("  Kontrolle", stats(ctrl, n_trials), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("is", "open"), required=True)
    stage = ap.parse_args().stage
    lk = lock()
    if lk.trials == 0:
        lk.log_trials(1, "Klon ohne Gewinn-Auswahl; Regeln nur auf Uebereinstimmung mit den MT5-Berichten")
    mk = Market()
    if stage == "is":
        run_stage(mk, "is", IS_START, IS_END, lk.trials)
        return
    h = lk.freeze(CONFIG)
    for name in ("blind", "oos", "tresor"):
        start, end = lk.unseal(name, h)
        run_stage(mk, name, start, end, lk.trials)


if __name__ == "__main__":
    main()
