"""Spielt die echten MT5-Orders durch die Engine und vergleicht mit dem Bericht.

Prueft nur den Ausstieg: Einstiegszeitpunkt, Level, SL und TP kommen aus dem
Bericht. Aufruf: python -m mt5_valkyrie.replay
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_m1
from .engine import Ticks, manage, trail_params
from .ohlc_ticks import ticks

RES = Path(__file__).parent / "results"


def replay(run: str, tk: Ticks) -> pd.DataFrame:
    o = pd.read_parquet(RES / "orders.parquet")
    p = pd.read_parquet(RES / "positions.parquet")
    o, p = o[o.run == run], p[p.run == run]
    p = p.merge(o[["order", "sl", "tp", "t_set", "price"]], on="order", how="inner",
                suffixes=("", "_o")).sort_values("t_in")
    rows = []
    for x in p.itertuples():
        i0 = int(np.searchsorted(tk.t, np.datetime64(x.t_in)))
        if i0 >= len(tk.t) or tk.t[i0] != np.datetime64(x.t_in):
            continue
        start, dist = trail_params(abs(x.tp - x.p_in), abs(x.p_in - x.sl))
        i, px = manage(tk, i0, x.s, x.p_in, x.sl, x.tp, start=start, dist=dist)
        pnl = (px - x.p_in) * x.s * x.lot * 100
        rows.append(dict(t_in=x.t_in, t_out=x.t_out, t_sim=pd.Timestamp(tk.t[i]), s=x.s, lot=x.lot,
                         pnl_mt5=x.pnl, pnl_sim=pnl, r_mt5=x.pnl / (abs(x.p_in - x.sl) * x.lot * 100),
                         r_sim=pnl / (abs(x.p_in - x.sl) * x.lot * 100)))
    return pd.DataFrame(rows)


def report(df: pd.DataFrame) -> dict:
    dt = (df.t_sim - df.t_out).abs().dt.total_seconds()
    eq_m, eq_s = df.pnl_mt5.cumsum(), df.pnl_sim.cumsum()
    r_m, r_s = df.r_mt5.cumsum(), df.r_sim.cumsum()
    return dict(n=len(df), exit_1min=round((dt <= 60).mean(), 3), pnl_mt5=round(df.pnl_mt5.sum()),
                pnl_sim=round(df.pnl_sim.sum()), r_mt5=round(df.r_mt5.sum(), 1), r_sim=round(df.r_sim.sum(), 1),
                eq_corr=round(eq_m.corr(eq_s), 4), r_corr=round(r_m.corr(r_s), 4),
                trade_corr=round(df.r_mt5.corr(df.r_sim), 3))


if __name__ == "__main__":
    tk = Ticks.from_frame(ticks(load_m1("2019-12-01")))
    for run in ("ohlc_2020_2023", "ohlc_2023_2026"):
        print(run, report(replay(run, tk)), flush=True)
