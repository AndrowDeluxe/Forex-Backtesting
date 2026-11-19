"""Paper-Simulation auf Lake-Kursen (M5/M15) -- fuer JEDES Signal zum Signalkurs ("was waere gewesen")
und fuer bestaetigte Signale zusaetzlich zum Kurs bei Bestaetigung.

Regeln = beste Ausstiegs-Familie aus Test 4: Stop am Docht der Signalkerze, Ziel 3R, BE nach 1R, max. 10 Tage.
Kosten Round-Trip je Markt (filter_matrix.MARKETS) + TTP-Swap (twin_trade.swap_r). Stop vor Ziel in jeder Kerze.
"""

from __future__ import annotations

import functools

import numpy as np
import pandas as pd

from signal_hub import config


@functools.lru_cache(maxsize=None)
def lake_bars(markt: str) -> pd.DataFrame | None:
    from data_lake.storage import read_bars
    key, tf = config.LAKE_BARS[markt]
    b = read_bars("dukascopy", key, tf)
    if b is None or b.empty:
        return None
    b = b[["Open", "High", "Low", "Close"]].copy()
    b.index = b.index.tz_localize("UTC") if b.index.tz is None else b.index.tz_convert("UTC")
    return b.sort_index()


def simulate(bars: pd.DataFrame, side: str, t0: pd.Timestamp, stop: float, cost: float, markt: str,
             entry: float | None = None) -> dict:
    """Simuliert ab der ersten Kerze >= t0. entry=None -> Eroeffnung dieser Kerze."""
    sign = 1 if side == "long" else -1
    seg = bars[bars.index >= t0.tz_convert("UTC")]
    if seg.empty:
        return {"status": "wartet"}
    e = float(seg["Open"].iat[0]) if entry is None else entry
    risk = sign * (e - stop)
    if not (risk > 0):
        return {"status": "ungueltig", "einstieg": e, "einstieg_t": seg.index[0]}
    tgt, one_r = e + sign * config.PAPER_TARGET_R * risk, e + sign * config.PAPER_BE_R * risk
    limit_t = seg.index[0] + pd.Timedelta(days=config.PAPER_MAX_DAYS)
    cur, px, t_exit = stop, None, None
    h, l, idx = seg["High"].to_numpy(), seg["Low"].to_numpy(), seg.index
    for i in range(len(seg)):
        if idx[i] > limit_t:
            px, t_exit = float(seg["Open"].iat[i]), idx[i]
            break
        if (sign == 1 and l[i] <= cur) or (sign == -1 and h[i] >= cur):
            px, t_exit = cur, idx[i]
            break
        if (sign == 1 and h[i] >= tgt) or (sign == -1 and l[i] <= tgt):
            px, t_exit = tgt, idx[i]
            break
        if (sign == 1 and h[i] >= one_r) or (sign == -1 and l[i] <= one_r):
            cur = e
    out = {"einstieg": e, "einstieg_t": seg.index[0], "be": bool(cur == e)}
    last = float(seg["Close"].iat[-1])
    if px is None:
        out.update({"status": "offen", "r": sign * (last - e) / risk})
        return out
    from htf_daily_trade.twin_trade import swap_r
    sw = swap_r(markt, side, e, risk, seg.index[0].tz_localize(None), t_exit.tz_localize(None))
    out.update({"status": "geschlossen", "r": sign * (px - e) / risk - cost / risk - sw, "exit_t": t_exit, "exit": px})
    return out


def update(j: pd.DataFrame, notify=None) -> pd.DataFrame:
    """Aktualisiert p_sig_* (alle Signale) und p_conf_* (bestaetigte). notify(text) bei Schluss eines bestaetigten Trades."""
    from htf_daily_trade.filter_matrix import MARKETS
    for i, r in j.iterrows():
        bars = lake_bars(r["markt"])
        if bars is None:
            continue
        cost = MARKETS[r["markt"]][2]
        if r.get("p_sig_status") != "geschlossen":
            s = simulate(bars, r["seite"], r["einstieg"], float(r["stop"]), cost, r["markt"])
            for k in ("status", "r", "einstieg", "einstieg_t", "exit_t"):
                if k in s:
                    j.loc[i, f"p_sig_{k}"] = s[k]
        if r.get("status") == "ja" and r.get("p_conf_status") != "geschlossen" and pd.notna(r.get("entschieden_um")):
            s = simulate(bars, r["seite"], r["entschieden_um"], float(r["stop"]), cost, r["markt"])
            for k in ("status", "r", "einstieg", "einstieg_t", "exit_t"):
                if k in s:
                    j.loc[i, f"p_conf_{k}"] = s[k]
            if s.get("status") == "geschlossen" and notify:
                icon = "✅" if s["r"] > 0.05 else ("➖" if s["r"] > -0.2 else "❌")
                notify(f"{icon} Paper geschlossen: {r['markt']} {r['seite'].upper()} {s['r']:+.2f} R "
                       f"(Einstieg {s['einstieg']:.5g}, Ausstieg {s['exit']:.5g})")
    return j
