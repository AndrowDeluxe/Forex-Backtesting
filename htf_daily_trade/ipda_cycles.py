"""IPDA-Zyklen: Drehen Daily-Bewegungen bevorzugt nach ~8 / 14 / 21 Kalendertagen?

    python -m htf_daily_trade.ipda_cycles

Edge Card [[htf-daily-trade-edge-card]] (Nutzer-Lesart 02.11.2026): Die Bewegungen
zwischen zwei Fractal-Wendepunkten (ZigZag wie im Nutzer-Indikator) dauern meist
~8, ~14 oder ~20-22 Kalendertage. Geprueft wird, ob diese Dauern haeufiger sind als in
Zufallsreihen aus denselben, durchgemischten Tageskerzen (gleiche Schwankung, gleiche
Wochenenden, aber keine zeitliche Ordnung).

Nur IS (2016-2021) unter der Overfitting-Sperre `htf_ipda_zyklen`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research_lock import Lock

DATA = "data_cache/combined/{}"
FILES = {
    "EURUSD": "EURUSD_D1_2003-01-01_2026-10-10.parquet",
    "GBPUSD": "GBPUSD_D1_2003-01-01_2026-10-10.parquet",
    "USDJPY": "USDJPY_D1_2003-01-01_2026-10-10.parquet",
    "AUDUSD": "AUDUSD_D1_2003-01-01_2026-10-10.parquet",
    "XAUUSD": "GOLD_D1_2010-01-01_2026-08-13.parquet",
    "XAGUSD": "SILVER_D1_2016-01-01_2026-08-01.parquet",
}
WINDOWS = {"8": (7, 9), "14": (13, 15), "21": (20, 22)}
N_NULL = 300
SEED = 20261102


def load_daily(name: str) -> pd.DataFrame:
    """UTC-Tageskerzen ohne Wochenend-Stummel: Sonntag in den Montag, Samstag in
    den Freitag legen (naeher an OANDA-Daily ohne Sonntagskerze)."""
    d = pd.read_parquet(DATA.format(FILES[name]))[["Open", "High", "Low", "Close"]].sort_index()
    d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
    key = d.index.normalize()
    dow = d.index.dayofweek
    key = key.where(dow != 6, key + pd.Timedelta(days=1))   # So -> Mo
    key = key.where(dow != 5, key - pd.Timedelta(days=1))   # Sa -> Fr
    g = d.groupby(key)
    out = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(),
                        "Low": g["Low"].min(), "Close": g["Close"].last()})
    return out[out.index.dayofweek < 5]


def fractal_pivots(h: np.ndarray, l: np.ndarray) -> list[tuple[int, int]]:
    """5-Kerzen-Fractals (2 links, 2 rechts, strikt) -> alternierender ZigZag.
    Rueckgabe: Liste (bar_index, +1 Hoch / -1 Tief)."""
    n = len(h)
    raw = []
    for i in range(2, n - 2):
        if h[i] > max(h[i - 1], h[i - 2], h[i + 1], h[i + 2]):
            raw.append((i, 1))
        if l[i] < min(l[i - 1], l[i - 2], l[i + 1], l[i + 2]):
            raw.append((i, -1))
    zz: list[tuple[int, int]] = []
    for i, k in raw:
        if zz and zz[-1][1] == k:
            j = zz[-1][0]
            better = h[i] > h[j] if k == 1 else l[i] < l[j]
            if better:
                zz[-1] = (i, k)
        elif zz and zz[-1][0] == i:
            continue  # Hoch und Tief auf derselben Kerze: erstes behalten
        else:
            zz.append((i, k))
    return zz


def leg_days(df: pd.DataFrame) -> np.ndarray:
    zz = fractal_pivots(df["High"].to_numpy(), df["Low"].to_numpy())
    idx = df.index
    return np.array([(idx[b] - idx[a]).days for (a, _), (b, _) in zip(zz, zz[1:])])


def shuffled(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Tageskerzen relativ (Gap, Hoch, Tief, Schluss zum Open) durchmischen, Daten behalten."""
    o, h, l, c = (df[x].to_numpy() for x in ("Open", "High", "Low", "Close"))
    gap = np.r_[1.0, o[1:] / c[:-1]]
    rel = np.c_[gap, h / o, l / o, c / o][1:]
    rel = rel[rng.permutation(len(rel))]
    oo = np.empty(len(df)); cc = np.empty(len(df)); hh = np.empty(len(df)); ll = np.empty(len(df))
    oo[0], hh[0], ll[0], cc[0] = o[0], h[0], l[0], c[0]
    for t in range(1, len(df)):
        g, rh, rl, rc = rel[t - 1]
        oo[t] = cc[t - 1] * g
        hh[t], ll[t], cc[t] = oo[t] * rh, oo[t] * rl, oo[t] * rc
    return pd.DataFrame({"Open": oo, "High": hh, "Low": ll, "Close": cc}, index=df.index)


def shares(days: np.ndarray) -> dict[str, float]:
    return {k: float(((days >= a) & (days <= b)).mean()) for k, (a, b) in WINDOWS.items()}


def main() -> None:
    lock = Lock("htf_ipda_zyklen")
    lock.register_split("2016-01-01", "2021-12-31", "2024-12-31")
    if lock.trials == 0:
        lock.log_trials(1, "IPDA-Zyklen: Fractal-ZigZag-Dauer 8/14/21 +-1 Kalendertage vs. "
                           "300 durchgemischte Tageskerzen-Reihen, 6 Maerkte, nur IS")
    rng = np.random.default_rng(SEED)
    rows, hist_real, hist_null = [], [], []
    for name in FILES:
        df = lock.is_only(load_daily(name))
        real = leg_days(df)
        s_real = shares(real)
        null = [shares(leg_days(shuffled(df, rng))) for _ in range(N_NULL)]
        hist_real.append(np.bincount(real, minlength=60)[:60])
        for k in WINDOWS:
            nv = np.array([x[k] for x in null])
            rows.append({"markt": name, "fenster": k, "beine": len(real),
                         "anteil_echt": s_real[k], "anteil_zufall": nv.mean(),
                         "verhaeltnis": s_real[k] / nv.mean(),
                         "p_einseitig": float((nv >= s_real[k]).mean())})
        print(f"{name}: {len(real)} Bewegungen, Median {np.median(real):.0f} Tage", flush=True)
    res = pd.DataFrame(rows)
    pd.set_option("display.width", 160)
    print(res.round(3).to_string(index=False))
    pooled = res.groupby("fenster").apply(
        lambda g: pd.Series({"anteil_echt": np.average(g.anteil_echt, weights=g.beine),
                             "anteil_zufall": np.average(g.anteil_zufall, weights=g.beine),
                             "maerkte_p<0,05": int((g.p_einseitig < 0.05).sum())}))
    pooled["verhaeltnis"] = pooled.anteil_echt / pooled.anteil_zufall
    print("\nGepoolt (gewichtet nach Bewegungen):")
    print(pooled.round(3).to_string())
    h = np.sum(hist_real, axis=0)
    print("\nVerteilung echte Dauern (Kalendertage: Anzahl):")
    print(", ".join(f"{d}:{h[d]}" for d in range(2, 36) if h[d]))
    res.to_csv("htf_daily_trade/ipda_cycles_is.csv", index=False)


if __name__ == "__main__":
    main()
