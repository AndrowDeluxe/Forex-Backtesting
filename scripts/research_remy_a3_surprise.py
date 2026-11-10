"""Remy-King A3: Drift nach einer Konsens-Ueberraschung.

    python -m scripts.research_remy_a3_surprise

High-Impact-Termine der G8 (ForexFactory-Historie, scripts/remy_ff_history.py).
Ueberraschung je Indikator: (Ist - Konsens) / Streuung der Ueberraschungen im IS,
gepolt "gut fuer die Waehrung" (Arbeitslosigkeit/Anträge umgedreht). Gleichzeitige
Termine einer Waehrung (NFP + Quote + Loehne) werden zu einem Mittelwert zusammengefasst.
Einstieg zur Eroeffnung der H1-Kerze 1 h nach dem Termin (die erste Reaktion ist vorbei),
Richtung = Ueberraschung, Ausstieg nach H Stunden zum Schluss. Paar = Waehrung gegen USD,
USD-Termine auf EURUSD gespiegelt. Kosten: anderthalbfacher halber Spread je Seite
(Spreads sind nach Terminen weiter).

Overfitting-Sperre `remy_a3_surprise`: nur IS-Zahlen, 6 gezaehlte Varianten (|z| x H).
"""

from __future__ import annotations

import itertools
import re

import numpy as np
import pandas as pd

from research_lock import Lock, config_hash, deflated_sharpe
from scripts.remy_common import HALF_SPREAD

LOCK = Lock("remy_a3_surprise")
FF = "data_cache/remy/ff_calendar.parquet"
H1 = "data_cache/combined/{}_H1_2007-01-01_2026-11-10.parquet"
PAIR = {"EUR": "EURUSD", "GBP": "GBPUSD", "AUD": "AUDUSD", "NZD": "NZDUSD",
        "CAD": "USDCAD", "CHF": "USDCHF", "JPY": "USDJPY", "USD": "EURUSD"}
INVERT = re.compile(r"unemployment|claimant|jobless|claims", re.I)
MIN_IS_EVENTS = 20
COST_MULT = 1.5
DELAY_H = 1
VARIANTS = list(itertools.product((1.0, 1.5, 2.0), (4, 24)))
UNITS = {"%": 1.0, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def parse_value(text) -> tuple[float, str] | None:
    """'0.4%' -> (0.4, '%'), '-2.1B' -> (-2.1e9, 'B'); leer/unlesbar -> None."""
    if text is None:
        return None
    t = str(text).strip().replace(",", "").lstrip("<>")
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)([%KMBT]?)", t)
    if not m:
        return None
    unit = m.group(2)
    return float(m.group(1)) * (UNITS[unit] if unit in "KMBT" and unit else 1.0), unit


def surprises(ev: pd.DataFrame, is_end: str) -> pd.DataFrame:
    ev = ev[ev["impact"] == "high"].copy()
    a = ev["actual"].map(parse_value)
    f = ev["forecast"].map(parse_value)
    ok = a.notna() & f.notna()
    ev, a, f = ev[ok], a[ok], f[ok]
    same_unit = [x[1] == y[1] for x, y in zip(a, f)]
    ev = ev[same_unit].assign(raw=[x[0] - y[0] for x, y in zip(a[same_unit], f[same_unit])])
    ev["key"] = ev["currency"] + "|" + ev["name"]
    is_ev = ev[ev["time"] <= pd.Timestamp(is_end, tz="UTC") + pd.Timedelta(days=1)]
    scale = is_ev.groupby("key")["raw"].agg(["std", "size"])
    scale = scale[(scale["size"] >= MIN_IS_EVENTS) & (scale["std"] > 0)]["std"]
    ev = ev[ev["key"].isin(scale.index)]
    sign = np.where(ev["name"].str.contains(INVERT), -1.0, 1.0)
    ev["z"] = sign * ev["raw"] / ev["key"].map(scale)
    # gleichzeitige Termine einer Waehrung -> ein Signal
    return ev.groupby(["time", "currency"], as_index=False).agg(z=("z", "mean"), n=("z", "size"),
                                                               names=("name", " + ".join))


def load_h1() -> dict[str, pd.DataFrame]:
    out = {}
    for p in set(PAIR.values()):
        d = pd.read_parquet(H1.format(p))[["Open", "Close"]].sort_index()
        out[p] = d[~d.index.duplicated(keep="last")]
    return out


def trades(sig: pd.DataFrame, h1: dict, zmin: float, hold: int) -> pd.DataFrame:
    rows = []
    for r in sig[sig["z"].abs() >= zmin].itertuples():
        pair = PAIR[r.currency]
        bars = h1[pair]
        entry_t = r.time.floor("h") + pd.Timedelta(hours=DELAY_H)
        i = bars.index.searchsorted(entry_t)
        j = i + hold - 1
        if i >= len(bars) or j >= len(bars) or bars.index[i] - entry_t > pd.Timedelta(hours=3):
            continue
        ccy_up = np.sign(r.z)
        # Paar-Richtung: Waehrung stark -> XXXUSD long / USDXXX short; USD stark -> EURUSD short
        if r.currency == "USD":
            side = -ccy_up
        else:
            side = ccy_up if pair.endswith("USD") else -ccy_up
        gross = side * np.log(bars["Close"].iloc[j] / bars["Open"].iloc[i])
        react = side * np.log(bars["Open"].iloc[i] / bars["Open"].iloc[max(i - DELAY_H, 0)])
        rows.append({"time": r.time, "currency": r.currency, "pair": pair, "z": r.z, "side": side,
                     "ret": gross - 2 * COST_MULT * HALF_SPREAD[pair], "react": react, "names": r.names})
    return pd.DataFrame(rows)


def summary(tr: pd.DataFrame) -> dict:
    r = tr["ret"]
    sr = r.mean() / r.std() if len(r) > 1 and r.std() > 0 else 0.0
    return {"n": len(r), "avg_bp": r.mean() * 1e4, "hit": (r > 0).mean(), "t": sr * np.sqrt(len(r)),
            "sr": sr, "skew": r.skew(), "kurt": r.kurt() + 3, "react_bp": tr["react"].mean() * 1e4}


def main() -> None:
    ev = pd.read_parquet(FF)
    split = LOCK.split
    sig = surprises(ev, split["is_end"])
    is_sig = sig[(sig["time"] >= pd.Timestamp(split["is_start"], tz="UTC"))
                 & (sig["time"] <= pd.Timestamp(split["is_end"], tz="UTC") + pd.Timedelta(days=1))]
    oos_sig = LOCK.oos_only(sig.set_index("time")).reset_index()  # Regel 10.11.: OOS frei
    print(f"IS-Signale: {len(is_sig)}, OOS-Signale: {len(oos_sig)} (Indikatoren mit >= {MIN_IS_EVENTS} IS-Terminen)")
    h1 = load_h1()
    rows, tl, orows = {}, {}, {}
    for zmin, hold in VARIANTS:
        tr = trades(is_sig, h1, zmin, hold)
        key = f"|z|>={zmin} H={hold}h"
        rows[key], tl[key] = summary(tr), tr
        o = summary(trades(oos_sig, h1, zmin, hold))
        orows[key] = {"OOS n": o["n"], "OOS react_bp": o["react_bp"], "OOS avg_bp": o["avg_bp"], "OOS t": o["t"]}
    LOCK.log_trials(len(VARIANTS), "A3 IS-Sweep |z| x Haltedauer")
    tab = pd.DataFrame(rows).T
    print(tab[["n", "react_bp", "avg_bp", "hit", "t"]].join(pd.DataFrame(orows).T).astype(float).round(3).to_string())
    best = tab["t"].astype(float).idxmax()
    b = rows[best]
    dsr = deflated_sharpe(b["sr"], int(b["n"]), LOCK.trials, b["skew"], b["kurt"],
                          sr_var_trials=float(tab["sr"].astype(float).var()))
    print(f"\nBeste: {best}  Ø {b['avg_bp']:.2f} bp  t {b['t']:.2f}  DSR {dsr:.2f} (Versuche {LOCK.trials})")
    tr = tl[best]
    print("\nJe Waehrung (IS):")
    print(tr.groupby("currency")["ret"].agg(n="size", avg_bp=lambda r: r.mean() * 1e4).round(2).to_string())
    print("\nJahre (IS):")
    print(tr.groupby(tr["time"].dt.year)["ret"].agg(n="size", avg_bp=lambda r: r.mean() * 1e4).round(2).to_string())
    print("\nGroesste Indikatoren (IS):")
    print(tr.groupby("names")["ret"].agg(n="size", avg_bp=lambda r: r.mean() * 1e4).sort_values("n").tail(10).round(2).to_string())
    zmin, hold = float(best.split()[0][5:]), int(best.split()[1][2:-1])
    print("Konfig-Hash (noch nicht eingefroren):", config_hash({"zmin": zmin, "hold": hold, "delay": DELAY_H}))


if __name__ == "__main__":
    main()
