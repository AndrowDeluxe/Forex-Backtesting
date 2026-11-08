"""IPDA nach Nutzer-Definition (02.11.2026): Nullpunkt am Quartals-/Halbjahreswechsel.

    python -m htf_daily_trade.ipda_nullpunkt

Nullpunkt: relevantes Hoch/Tief in +-10 Kalendertagen um 01.01., 01.04., 01.06. (Bankenhalbjahr),
01.07., 01.10. (V: relevant = mindestens 40-Handelstage-Extrem; sind Hoch und Tief relevant,
gilt das spaetere). Bestaetigung (V): Nullpunkt haelt 22 Kalendertage, Schluss an Tag 22 liegt
in Richtung weg vom Nullpunkt-Schlusskurs.

A -- Quartalsrichtung: ATR-normierte Bewegung vom Bestaetigungs-Schluss (Tag 22) bis Tag 90.
B -- Zyklus ab Nullpunkt: Fractal-ZigZag-Wendepunkt an Tag 7-9 / 13-15 / 18-22.

Kontrolle: identische Rechnung an Nicht-Wechsel-Ankern (1. der uebrigen Monate, 15. jedes
Monats). Nur IS 2016-2021, Lock `htf_ipda_zyklen` (2 weitere Versuche).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from htf_daily_trade.ipda_cycles import FILES, fractal_pivots, load_daily
from research_lock import Lock

QUARTER = [(1, 1), (4, 1), (6, 1), (7, 1), (10, 1)]
CONTROL = [(m, 1) for m in (2, 3, 5, 8, 9, 11, 12)] + [(m, 15) for m in range(1, 13)]
B_WINDOWS = {"Tag 8": (7, 9), "Tag 14": (13, 15), "Zyklus 18-22": (18, 22)}


def atr(df: pd.DataFrame, n: int = 20) -> pd.Series:
    pc = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def nullpunkt(df: pd.DataFrame, anchor: pd.Timestamp, lookback: int = 40):
    win = df.loc[anchor - pd.Timedelta(days=10): anchor + pd.Timedelta(days=10)]
    if len(win) < 10:
        return None
    cands = []
    for kind, col, fn in (("tief", "Low", "idxmin"), ("hoch", "High", "idxmax")):
        t = getattr(win[col], fn)()
        pos = df.index.get_loc(t)
        hist = df[col].iloc[max(0, pos - lookback):pos + 1]
        if (kind == "tief" and df[col].iat[pos] <= hist.min()) or (kind == "hoch" and df[col].iat[pos] >= hist.max()):
            cands.append((t, kind))
    if not cands:
        return None
    return max(cands)  # spaeteres Extrem


def evaluate(df: pd.DataFrame, anchors: list[pd.Timestamp], pivots_dates: pd.DatetimeIndex, a: pd.Series):
    rows = []
    for anc in anchors:
        npkt = nullpunkt(df, anc)
        if npkt is None:
            continue
        t, kind = npkt
        sign = 1 if kind == "tief" else -1
        # B: Wendepunkte nach dem Nullpunkt
        off = np.array([(p - t).days for p in pivots_dates if 0 < (p - t).days <= 30])
        b = {k: bool(((off >= lo) & (off <= hi)).any()) for k, (lo, hi) in B_WINDOWS.items()}
        # Bestaetigung + A
        after = df.loc[t:]
        d22 = after.loc[t + pd.Timedelta(days=22):]
        d90 = after.loc[t + pd.Timedelta(days=90):]
        if d22.empty or d90.empty:
            continue
        t22 = d22.index[0]
        seg = df.loc[t + pd.Timedelta(days=1): t22]
        held = (seg["Low"].min() > df.at[t, "Low"]) if sign == 1 else (seg["High"].max() < df.at[t, "High"])
        moved = sign * (df.at[t22, "Close"] - df.at[t, "Close"]) > 0
        confirmed = bool(held and moved)
        ret = sign * (d90["Close"].iat[0] - df.at[t22, "Close"]) / a.at[t22]
        rows.append({"anker": anc.date(), "nullpunkt": t.date(), "art": kind, "bestaetigt": confirmed,
                     "a_atr": float(ret), **b})
    return pd.DataFrame(rows)


def anchors_for(years, spec):
    return [pd.Timestamp(y, m, d) for y in years for (m, d) in spec]


def main() -> None:
    lock = Lock("htf_ipda_zyklen")
    lock.register_split("2016-01-01", "2021-12-31", "2024-12-31")
    if lock.trials < 3:
        lock.log_trials(2, "IPDA Nullpunkt (Nutzer-Def. 02.11.): A Quartalsrichtung ab bestaetigtem "
                           "Nullpunkt, B Wendepunkte Tag 8/14/18-22 ab Nullpunkt; Kontrolle Nicht-Wechsel-Anker")
    years = range(2016, 2022)
    res = []
    for name in FILES:
        df = lock.is_only(load_daily(name))
        a = atr(df)
        piv = pd.DatetimeIndex([df.index[i] for i, _ in fractal_pivots(df["High"].to_numpy(), df["Low"].to_numpy())])
        for grp, spec in (("Wechsel", QUARTER), ("Kontrolle", CONTROL)):
            r = evaluate(df, anchors_for(years, spec), piv, a)
            r["markt"], r["gruppe"] = name, grp
            res.append(r)
    res = pd.concat(res, ignore_index=True)
    res.to_csv("htf_daily_trade/ipda_nullpunkt_is.csv", index=False)
    pd.set_option("display.width", 160)

    print("== A: Quartalsrichtung ab bestaetigtem Nullpunkt (Tag 22 -> Tag 90, in ATR) ==")
    conf = res[res.bestaetigt]
    rng = np.random.default_rng(20261102)
    for grp in ("Wechsel", "Kontrolle"):
        g = conf[conf.gruppe == grp]
        print(f"{grp:10s} n={len(g):4d}  Mittel {g.a_atr.mean():+.2f} ATR  Treffer {(g.a_atr > 0).mean():.1%}  "
              f"(Nullpunkte gesamt {int((res.gruppe == grp).sum())}, bestaetigt {len(g)})")
    w, k = conf[conf.gruppe == "Wechsel"].a_atr.to_numpy(), conf[conf.gruppe == "Kontrolle"].a_atr.to_numpy()
    diff = w.mean() - k.mean()
    pool = np.r_[w, k]
    perm = [rng.permutation(pool) for _ in range(5000)]
    p = float(np.mean([pp[:len(w)].mean() - pp[len(w):].mean() >= diff for pp in perm]))
    print(f"Differenz Wechsel - Kontrolle {diff:+.2f} ATR, Permutations-p (einseitig) {p:.3f}")
    print(f"Wechsel-Anker allein gegen 0: t = {w.mean() / (w.std(ddof=1) / np.sqrt(len(w))):.2f}")
    print(conf.groupby(["gruppe", "markt"]).a_atr.agg(["size", "mean"]).round(2).unstack(0).to_string())

    print("\n== B: Wendepunkt an Tag x nach dem Nullpunkt (Anteil der Nullpunkte) ==")
    tab = res.groupby("gruppe")[list(B_WINDOWS)].mean()
    print(tab.round(3).to_string())
    for kcol in B_WINDOWS:
        x1 = res.loc[res.gruppe == "Wechsel", kcol].to_numpy(dtype=float)
        x0 = res.loc[res.gruppe == "Kontrolle", kcol].to_numpy(dtype=float)
        pool = np.r_[x1, x0]
        d = x1.mean() - x0.mean()
        pp = float(np.mean([(q := rng.permutation(pool))[:len(x1)].mean() - q[len(x1):].mean() >= d
                            for _ in range(5000)]))
        print(f"{kcol:14s} Wechsel {x1.mean():.1%} vs Kontrolle {x0.mean():.1%}  p {pp:.3f}")


if __name__ == "__main__":
    main()
