"""H4-Manipulation Test 3: Ursprungsregel + beschreibende IS-Statistik (Nutzerauftrag 15.11.2026).

    python -m htf_daily_trade.h4_v3            # IS 2016-2021, nur Beschreibung (keine Auswahl), Lock h4_manip
    python -m htf_daily_trade.h4_v3 --liste    # IS-Trades zum Handpruefen (EURUSD + Gold)

Grundsignal (Nutzerregel 15.11.): H4-Kerze sweept Hoch/Tief von >= 2 Vorkerzen, Koerper (Open+Close) schliesst wieder
innerhalb; Einstieg zur Eroeffnung der Folgekerze; Stop am Docht der Signalkerze; jede Uhrzeit. Signale unabhaengig
(keine Positions-Sperre), damit jedes Merkmal auf allen Signalen gemessen wird.
Gemessen je Signal: Kerzengroesse (Spanne/ATR H4, Spanne in bps), Vol-Regime (ATR H4 / Median 120), Docht (Anteil,
in ATR), Anzahl gesweepter Kerzen, unberuehrtes H4-Swing geholt, Sweep-Tiefe ueber die Marke (ATR), Schluss unter
der Marke (ATR), Abstand Schluss-Extrem (ATR), Einstiegsstunde Berlin, Trend (D/H4-Struktur, Daily-/H4-Swing-
Struktur LH+LL, T1-T7), Makro (M1-M7, X1 VIX, X3 Realzins, X4 COT-Index, Gold-Makro-Veto).
Ausstiege: Ziel R2/R3/TB (H4-Swing)/TC (Vortag-Vorwoche)/Z24/Z48 (Zeit) x BE ohne/0,5R/1R.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_r import features
from htf_daily_trade.filter_matrix import MARKETS, METALS, MacroDirs
from htf_daily_trade.h4_manip import IS_END, IS_START, LOCK, MAX_HOLD, OOS_END, Market, daily
from htf_daily_trade.h4_ny15 import h4_atr
from htf_daily_trade.twin_trade import swap_r
from gold_smc_htf_ltf.structure import detect_fractal_swings
from research_lock import Lock

TARGETS = ("R2", "R3", "TB", "TC", "Z24", "Z48")
BES = {"B0": None, "B05": 0.5, "B1": 1.0}
MAX_N = 20
TZ = "Europe/Berlin"
N_DESCR = 60   # gezaehlte Beschreibungs-Zellen (Merkmal-Quintile, Stunden, Trend-/Makrozustaende, Ausstiege)


def swing_structure(df: pd.DataFrame) -> np.ndarray:
    """+1 wenn die letzten zwei bestaetigten Swing-Hochs UND -Tiefs steigen, -1 wenn beide fallen, sonst 0 (kausal)."""
    s = detect_fractal_swings(df.rename(columns=str.lower), k=2)
    hc, hp = s["swing_high_confirmed"].to_numpy(), s["swing_high_price"].to_numpy()
    lc, lp = s["swing_low_confirmed"].to_numpy(), s["swing_low_price"].to_numpy()
    out = np.zeros(len(s), int)
    H, L = [], []
    for i in range(len(s)):
        if hc[i]:
            H.append(hp[i])
        if lc[i]:
            L.append(lp[i])
        if len(H) >= 2 and len(L) >= 2:
            out[i] = 1 if (H[-1] > H[-2] and L[-1] > L[-2]) else -1 if (H[-1] < H[-2] and L[-1] < L[-2]) else 0
    return out


def sim(m: Market, k: int, sign: int, stop: float, tgt_kind: str, be, end_idx: int, cost: float):
    f = k + 1
    entry = m.o[f]
    risk = sign * (entry - stop)
    if not (risk > 0):
        return None
    tgt = None
    if tgt_kind in ("R2", "R3"):
        tgt = entry + sign * int(tgt_kind[1]) * risk
    elif tgt_kind in ("TB", "TC"):
        tgt = m.target(tgt_kind, sign, entry, risk, k, f)
    last = min(end_idx, f + {"Z24": 6, "Z48": 12}.get(tgt_kind, MAX_HOLD) - 1)
    cur, px, j = stop, None, f
    for j in range(f, last + 1):
        if (sign == 1 and m.l[j] <= cur) or (sign == -1 and m.h[j] >= cur):
            px = cur
            break
        if tgt is not None and ((sign == 1 and m.h[j] >= tgt) or (sign == -1 and m.l[j] <= tgt)):
            px = tgt
            break
        if be is not None and ((sign == 1 and m.h[j] >= entry + be * risk) or (sign == -1 and m.l[j] <= entry - be * risk)):
            cur = entry
    if px is None:
        j, px = last, m.c[last]
    g = sign * (px - entry) / risk
    sw = swap_r(m.name, "long" if sign == 1 else "short", entry, risk, m.x.index[f].tz_localize(None), m.x.index[j].tz_localize(None))
    return g, g - cost / risk - sw, j


def run_market(name: str, md: MacroDirs, gold_veto) -> pd.DataFrame:
    m = Market(name, OOS_END)
    atr = h4_atr(m)
    atr_prev = np.r_[np.nan, atr[:-1]]
    vol_reg = atr_prev / pd.Series(atr_prev).rolling(120, min_periods=60).median().to_numpy()
    hs = swing_structure(m.x)
    d = daily(name).loc[:pd.Timestamp(OOS_END)]
    ds = swing_structure(d)
    pos = d.index.searchsorted(m.day) - 1
    end_idx = len(m.x) - 1
    start = int(m.x.index.searchsorted(pd.Timestamp(IS_START, tz="UTC")))
    rows = []
    o, h, l, c = m.o, m.h, m.l, m.c
    for k in range(max(start, MAX_N + 1), end_idx):
        rng = h[k] - l[k]
        if rng <= 0 or not np.isfinite(atr_prev[k]):
            continue
        for side, sign in (("long", 1), ("short", -1)):
            if sign == 1:
                ok = lambda n: l[k] < l[k - n:k].min() and min(o[k], c[k]) > l[k - n:k].min()
            else:
                ok = lambda n: h[k] > h[k - n:k].max() and max(o[k], c[k]) < h[k - n:k].max()
            if not ok(2):
                continue
            n_max = max(n for n in range(2, MAX_N + 1) if ok(n))
            lvl = l[k - 2:k].min() if sign == 1 else h[k - 2:k].max()
            ext = l[k] if sign == 1 else h[k]
            body = min(o[k], c[k]) if sign == 1 else max(o[k], c[k])
            # unberuehrtes, vor k bestaetigtes H4-Swing zwischen Koerper und Docht-Extrem geholt?
            sw = m.sw_lo if sign == 1 else m.sw_hi
            took = False
            for ci, bi, p in reversed(sw):
                if ci > k - 1:
                    continue
                if bi < k - 120:
                    break
                inside = (ext < p < body) if sign == 1 else (body < p < ext)
                if not inside:
                    continue
                seg = l[bi + 1:k] if sign == 1 else h[bi + 1:k]
                if len(seg) == 0 or (seg.min() > p if sign == 1 else seg.max() < p):
                    took = True
                    break
            base = {"markt": name, "klasse": "Metalle" if name in METALS else "FX", "seite": side,
                    "signal": m.x.index[k].tz_convert(TZ), "einstieg": m.x.index[k + 1].tz_convert(TZ),
                    "stunde": m.x.index[k + 1].tz_convert(TZ).hour, "kurs": o[k + 1], "stop": ext,
                    "spanne_atr": rng / atr_prev[k], "spanne_bps": rng / c[k] * 1e4, "vol_regime": vol_reg[k],
                    "docht_anteil": sign * (body - ext) / rng, "docht_atr": sign * (body - ext) / atr_prev[k],
                    "n_sweep": n_max, "swing_geholt": took, "sweep_tiefe_atr": sign * (lvl - ext) / atr_prev[k],
                    "schluss_unter_marke_atr": sign * (c[k] - lvl) / atr_prev[k],
                    "schluss_von_extrem_atr": sign * (c[k] - ext) / atr_prev[k]}
            for f, v in (("DS", ds[pos[k]] if pos[k] >= 0 else 0), ("HS", hs[k - 1])):
                base[f] = "mit" if v * sign > 0 else "gegen" if v * sign < 0 else "neutral"
            for f in ("D", "H4", "T1", "T2", "T3", "T4", "T5", "T6", "T7"):
                base[f] = m.state(f, k, sign)
            day = m.day[k]
            mac = md.dirs(name, day)
            ex = md.extra(name, day)
            mac.update({"X3": ex["X3"], "X4": ex["X4"]})
            if name == "XAUUSD" and gold_veto is not None:
                try:
                    mac["GV"] = gold_veto.direction(day)
                except Exception:
                    mac["GV"] = 0
            for f, v in mac.items():
                v = int(np.sign(v or 0)) * sign
                base[f] = "mit" if v > 0 else "gegen" if v < 0 else "neutral"
            base["X1"] = ex["X1"]
            for tk in TARGETS:
                for bk, be in BES.items():
                    if tk.startswith("Z") and bk != "B0":
                        continue
                    res = sim(m, k, sign, ext, tk, be, end_idx, m.cost)
                    if res is not None:
                        base[f"g_{tk}_{bk}"], base[f"r_{tk}_{bk}"] = res[0], res[1]
            rows.append(base)
    return pd.DataFrame(rows)


def load_all() -> pd.DataFrame:
    md = MacroDirs.full()
    try:
        from fusion_lab.filters.gold_macro_veto import GoldMacroVetoFilter
        gv = GoldMacroVetoFilter()
    except Exception as e:
        print("Gold-Makro-Veto nicht verfuegbar:", e)
        gv = None
    t = pd.concat([run_market(n, md, gv) for n in MARKETS], ignore_index=True)
    t["periode"] = np.where(t["signal"].dt.tz_localize(None) <= pd.Timestamp(IS_END) + pd.Timedelta(hours=23), "IS", "OOS")
    return t


def tab(g: pd.DataFrame, key, col: str = "R3_B0") -> pd.DataFrame:
    out = g.groupby([key, "klasse"], observed=True).agg(n=(f"r_{col}", "size"), netto=(f"r_{col}", "mean"),
                                                         brutto=(f"g_{col}", "mean"))
    return out.unstack("klasse").round(3)


def main() -> None:
    lock = Lock(LOCK)
    if "Test 3" not in lock.log_path.read_text(encoding="utf-8"):
        lock.log_trials(N_DESCR, "Test 3 (15.11.): Ursprungsregel, beschreibende IS-Statistik (Merkmale, Stunden, Trend, Makro, Ausstiege)")
    t = load_all()
    t.to_parquet("htf_daily_trade/h4_v3_signale.parquet", index=False)
    i = t[t["periode"] == "IS"].copy()
    pd.set_option("display.width", 250)
    print(f"Lock {LOCK}: {lock.trials} Versuche. IS-Signale: {len(i)} (FX {int((i.klasse == 'FX').sum())}, "
          f"Metalle {int((i.klasse == 'Metalle').sum())}); OOS nicht ausgewertet")
    print("\n== Grundsignal (Stop Docht, 3R, kein BE) ==")
    print(i.groupby("klasse").agg(n=("r_R3_B0", "size"), netto=("r_R3_B0", "mean"), brutto=("g_R3_B0", "mean")).round(3))
    print("\n== Einstiegsstunde (Berlin) ==\n" + tab(i, "stunde").to_string())
    for col in ("spanne_atr", "spanne_bps", "vol_regime", "docht_anteil", "docht_atr", "sweep_tiefe_atr",
                "schluss_unter_marke_atr", "schluss_von_extrem_atr"):
        q = pd.qcut(i[col], 5, duplicates="drop")
        print(f"\n== {col} (Quintile) ==\n" + tab(i.assign(q=q), "q").to_string())
    nb = pd.cut(i["n_sweep"], [1, 2, 3, 5, 9, 20], labels=["2", "3", "4-5", "6-9", "10-20"])
    print("\n== Anzahl gesweepter Kerzen ==\n" + tab(i.assign(nb=nb), "nb").to_string())
    print("\n== unberührtes H4-Swing geholt ==\n" + tab(i, "swing_geholt").to_string())
    print("\n== Trend/Makro: Ø R netto (brutto) je Zustand, 3R ohne BE ==")
    rows = []
    for f in ("DS", "HS", "D", "H4", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "M1", "M2", "M3", "M6", "M7", "X3", "X4", "GV", "X1"):
        if f not in i:
            continue
        for z, g in i.groupby(f):
            for kl, gg in g.groupby("klasse"):
                rows.append({"filter": f, "zustand": z, "klasse": kl, "n": len(gg), "netto": gg["r_R3_B0"].mean(),
                             "brutto": gg["g_R3_B0"].mean()})
    fr = pd.DataFrame(rows).pivot_table(index=["filter", "zustand"], columns="klasse", values=["n", "netto", "brutto"])
    print(fr.round(3).to_string())
    print("\n== Ausstiege (Ø R netto) ==")
    ex = {c[2:]: i.groupby("klasse")[c].mean() for c in i.columns if c.startswith("r_")}
    print(pd.DataFrame(ex).T.round(3).to_string())


def liste(n: int = 16, seed: int = 11) -> None:
    t = pd.read_parquet("htf_daily_trade/h4_v3_signale.parquet")
    i = t[(t["periode"] == "IS") & t["markt"].isin(["EURUSD", "XAUUSD"])]
    pick = i.sample(n, random_state=seed).sort_values("signal")
    cols = ["markt", "seite", "signal", "einstieg", "kurs", "stop", "n_sweep", "swing_geholt", "spanne_atr",
            "docht_anteil", "DS", "r_R3_B0"]
    pd.set_option("display.width", 250)
    print(pick[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    liste() if "--liste" in sys.argv else main()
