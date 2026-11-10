"""Remy-King A1: Kurs gegen den "Fair Value" der 2J-Zinsdifferenz.

    python -m scripts.research_remy_a1_fairvalue

Je Paar (EURUSD, GBPUSD, USDJPY, USDCAD): d = 2J-Differenz so gepolt, dass ein Anstieg
das Paar stuetzt (Ausland - USA bei XXXUSD, USA - Ausland bei USDXXX). Rollende OLS
(250 Handelstage, nur Vergangenheit inkl. heute) log-Kurs ~ d, Residuum als z-Wert.
Einstieg zum Schluss nach dem Signaltag: z >= +Z und d in 20 Tagen nicht gestiegen -> short
(Kurs zu hoch, Zinsen tragen ihn nicht); spiegelbildlich long. Ausstieg bei z-Vorzeichenwechsel
oder nach H Tagen. Eine Position je Paar, 1 Einheit. Kosten: Spread je Ein-/Ausstieg,
Leitzins-Carry der Position, 1 % p.a. Swap-Aufschlag.

Overfitting-Sperre `remy_a1_fairvalue`: nur IS-Zahlen, 9 gezaehlte Varianten (Z x H).
"""

from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd

from research_lock import Lock, config_hash, deflated_sharpe
from scripts.remy_common import CCY, HALF_SPREAD, SWAP_MARKUP, fx_closes, rates, stats

LOCK = Lock("remy_a1_fairvalue")
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD"]
WINDOW, CONFIRM = 250, 20
VARIANTS = list(itertools.product((1.5, 2.0, 2.5), (10, 20, 40)))


def rolling_z(y: pd.Series, d: pd.Series, window: int) -> pd.Series:
    """Residuum von y_t gegen die OLS-Gerade aus den letzten `window` Tagen (inkl. t)."""
    my, md = y.rolling(window).mean(), d.rolling(window).mean()
    cov = (y * d).rolling(window).mean() - my * md
    var = (d * d).rolling(window).mean() - md * md
    beta = cov / var
    alpha = my - beta * md
    resid = y - (alpha + beta * d)
    # Streuung der Residuen im Fenster: Var(y) - beta^2 Var(d)
    vy = (y * y).rolling(window).mean() - my * my
    sd = np.sqrt((vy - beta ** 2 * var).clip(lower=1e-12))
    return resid / sd


def pair_inputs(closes: pd.DataFrame, y2: pd.DataFrame, pr: pd.DataFrame, pair: str, lag: int = 0):
    c = CCY[pair]
    sign = 1.0 if pair.endswith("USD") else -1.0
    d = sign * (y2[c] - y2["US"])
    price = closes[pair]
    ok = d.notna() & price.notna()
    d, price = d[ok], price[ok]
    z = rolling_z(np.log(price), d, WINDOW)
    dd = d.diff(CONFIRM)
    carry = sign * (pr[c] - pr["US"]).reindex(price.index) / 100 / 252  # Ertrag long Paar je Tag
    if lag:
        z, dd = z.shift(lag), dd.shift(lag)
    return price, z, dd, carry


def simulate(price, z, dd, carry, pair: str, zin: float, hold: int):
    """Tagesrendite-Reihe und Trade-Liste. Signal am Schluss t, Position ab t+1."""
    lr = np.log(price).diff().fillna(0.0).values
    zv, ddv, cv = z.values, dd.values, carry.fillna(0.0).values
    n = len(price)
    pos = np.zeros(n)
    cost = np.zeros(n)
    trades = []
    side, entry_i = 0, None
    for t in range(n - 1):
        if side != 0:
            age = t - entry_i
            if np.sign(zv[t]) == side or age >= hold or np.isnan(zv[t]):  # z hat Fair Value gekreuzt
                cost[t + 1] += HALF_SPREAD[pair]
                held = slice(entry_i + 1, t + 1)
                tret = side * (lr[held] + cv[held]).sum() - (t - entry_i) * SWAP_MARKUP / 252 - 2 * HALF_SPREAD[pair]
                trades.append((price.index[entry_i], price.index[t], side, tret))
                side = 0
        if side == 0 and not np.isnan(zv[t]) and not np.isnan(ddv[t]):
            if zv[t] >= zin and ddv[t] <= 0:
                side = -1
            elif zv[t] <= -zin and ddv[t] >= 0:
                side = 1
            if side != 0:
                entry_i = t
                cost[t + 1] += HALF_SPREAD[pair]
        pos[t + 1] = side
    ret = pos * (lr + cv) - np.abs(pos) * SWAP_MARKUP / 252 - cost
    daily = pd.Series(ret, index=price.index)
    tr = pd.DataFrame(trades, columns=["entry", "exit", "side", "ret"]).assign(pair=pair)
    return daily, tr


def run(closes, y2, pr, zin, hold, lag=0):
    days, trades = [], []
    for p in PAIRS:
        daily, tr = simulate(*pair_inputs(closes, y2, pr, p, lag), p, zin, hold)
        days.append(daily.rename(p))
        trades.append(tr)
    port = pd.concat(days, axis=1).fillna(0.0).sum(axis=1)
    return port, pd.concat(trades, ignore_index=True)


def main() -> None:
    closes = fx_closes()
    y2 = rates(closes.index, "2y")
    pr = rates(closes.index, "policy_rate")
    print("2J-Daten ab:", {c: str(y2[c].first_valid_index())[:10] for c in y2.columns})
    rows, series, tlists = {}, {}, {}
    for zin, hold in VARIANTS:
        port, tr = run(closes, y2, pr, zin, hold)
        s = LOCK.is_only(port)
        tr = tr[(tr["entry"] >= LOCK.split["is_start"]) & (tr["exit"] <= LOCK.split["is_end"])]
        st = stats(s)
        st.update(trades=len(tr), avg_bp=tr["ret"].mean() * 1e4,
                  t_trades=tr["ret"].mean() / tr["ret"].std() * np.sqrt(len(tr)) if len(tr) > 1 else np.nan,
                  hit=(tr["ret"] > 0).mean())
        key = f"Z={zin} H={hold}"
        rows[key], series[key], tlists[key] = st, s, tr
    LOCK.log_trials(len(VARIANTS), "A1 IS-Sweep Z x H")
    tab = pd.DataFrame(rows).T
    print(f"IS {LOCK.split['is_start']} .. {LOCK.split['is_end']} (Portfolio 4 Paare, 1 Einheit je Paar)")
    print(tab[["trades", "avg_bp", "hit", "t_trades", "sharpe", "t", "maxdd"]].astype(float).round(3).to_string())

    best = tab["sharpe"].astype(float).idxmax()
    b = rows[best]
    dsr = deflated_sharpe(b["sr_d"], b["n"], LOCK.trials, b["skew"], b["kurt"],
                          sr_var_trials=float(tab["sr_d"].astype(float).var()))
    print(f"\nBeste: {best}  Sharpe {b['sharpe']:.2f}  t {b['t']:.2f}  DSR {dsr:.2f} (Versuche {LOCK.trials})")

    tr = tlists[best]
    print("\nJe Paar (IS):")
    print(tr.groupby("pair")["ret"].agg(n="size", avg_bp=lambda r: r.mean() * 1e4, hit=lambda r: (r > 0).mean()).round(2))
    print("\nJe Seite (IS):")
    print(tr.groupby("side")["ret"].agg(n="size", avg_bp=lambda r: r.mean() * 1e4).round(2))
    print("\nJahre (IS):")
    print(tr.groupby(tr["exit"].dt.year)["ret"].agg(n="size", sum_bp=lambda r: r.sum() * 1e4).round(1).to_string())

    zin, hold = float(best.split()[0][2:]), int(best.split()[1][2:])
    lagged, _ = run(closes, y2, pr, zin, hold, lag=1)
    print(f"\nVorgriffsprobe (Signal 1 Tag spaeter): Sharpe {stats(LOCK.is_only(lagged))['sharpe']:.2f} "
          f"vs. {b['sharpe']:.2f}")
    print("Konfig-Hash (noch nicht eingefroren):", config_hash({"z": zin, "hold": hold, "window": WINDOW,
                                                                 "confirm": CONFIRM}))


if __name__ == "__main__":
    sys.exit(main())
