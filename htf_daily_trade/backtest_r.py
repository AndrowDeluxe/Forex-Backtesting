"""Edge Card „Dayli Trade“, Typ R (Reversal) -- IS-Test 2016-2021, ohne Makro-Filter.

    python -m htf_daily_trade.backtest_r

Regeln: [[htf-daily-trade-edge-card]] Felder 02/02b/05 (Nutzer bestaetigt 02.11.2026).
Signal (Long; Short spiegelbildlich): bestaetigtes Daily-Fractal-Tief, RSI Multi Length <= 30 in
den 20 Handelstagen bis zum Fractal. Confis 3-9 am Einstieg (Makro = Confi 10 folgt mit dem
Makro-Agenten). Gate = mind. 3 aus 3-9 (+ Kern 1-2 = mind. 5).

Varianten (alle gezaehlt, Lock `htf_daily_trade_r`):
  Einstieg E1 Schluss ueber dem Hoch der Fractal-Kerze (bis 10 Tage) | E2 Eroeffnung nach
  Fractal-Bestaetigung (00:01-Logik)
  Stop     S1 Fractal-Tief | S2 2x ATR(20)
  Gate     alle Signale | mind. 3 Confis
  Ausstieg X1 2 R | X2 3 R | X3 Ziel 3x ATR | X4 Nachziehen: Schluss unter Vortagestief
  X1-X3 mit Zeit-Exit nach 15 Handelstagen, X4 nach 30.
Ausfuehrung auf Tageskerzen: Stop und Ziel intrabar ueber Hoch/Tief; trifft eine Kerze beides,
zaehlt der Stop (konservativ). Kosten: Spread+Kommission je Markt, Swap nicht modelliert.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade.ipda_cycles import load_daily
from htf_daily_trade.rules import indicators, rsi
from research_lock import Lock, deflated_sharpe

MARKETS = {  # Dateien, Runde-Marken-Raster, Round-Trip-Kosten in Preis
    "EURUSD": (["EURUSD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00010),
    "GBPUSD": (["GBPUSD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00014),
    "AUDUSD": (["AUDUSD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00013),
    "USDJPY": (["USDJPY_D1_2003-01-01_2026-10-10.parquet"], 0.5, 0.012),
    "XAUUSD": (["GOLD_D1_2010-01-01_2026-08-13.parquet"], 10.0, 0.30),
    "XAGUSD": (["SILVER_D1_2009-01-01_2016-01-01.parquet", "SILVER_D1_2016-01-01_2026-08-01.parquet"], 0.5, 0.03),
}
RSI_LOOKBACK, RSI_LOW, RSI_HIGH = 20, 30, 70
CROSS_WINDOW, MAX_WAIT = 5, 10
NEAR_ATR = 0.25
LOCK = "htf_daily_trade_r"
VARIANTS = list(itertools.product(("E1", "E2"), ("S1", "S2"), ("alle", "gate"), ("X1", "X2", "X3", "X4")))


def load_market(name: str) -> pd.DataFrame:
    import htf_daily_trade.ipda_cycles as ic
    parts = []
    for f in MARKETS[name][0]:
        ic.FILES[name] = f
        parts.append(load_daily(name))
    d = pd.concat(parts)
    return d[~d.index.duplicated(keep="last")].sort_index()


def features(df: pd.DataFrame, grid: float) -> pd.DataFrame:
    x = indicators(df)
    pc = x["Close"].shift(1)
    tr = pd.concat([x["High"] - x["Low"], (x["High"] - pc).abs(), (x["Low"] - pc).abs()], axis=1).max(axis=1)
    x["atr"] = tr.rolling(20).mean()
    r14 = rsi(x["Close"], 14)
    x["rsi14"], x["rsi14_ma"] = r14, r14.rolling(14).mean()
    mid = x["Close"].rolling(20).mean()
    sd = x["Close"].rolling(20).std()
    x["bb_lo"], x["bb_hi"] = mid - 2 * sd, mid + 2 * sd
    # Weekly SMA 20/50 (abgeschlossene Wochen, ab der Folgewoche bekannt)
    wk = x["Close"].resample("W-FRI").last()
    wtrend = (wk.rolling(20).mean() - wk.rolling(50).mean()).shift(1)
    x["w_trend"] = wtrend.reindex(x.index, method="ffill")
    # Wochen-Pivots der Vorwoche
    wh, wl, wc = x["High"].resample("W-FRI").max(), x["Low"].resample("W-FRI").min(), wk
    p = (wh + wl + wc) / 3
    piv = pd.DataFrame({"P": p, "R1": 2 * p - wl, "S1": 2 * p - wh, "R2": p + (wh - wl), "S2": p - (wh - wl)}).shift(1)
    piv = piv.reindex(x.index, method="ffill")
    for k in piv:
        x["piv_" + k] = piv[k]
    x["grid"] = grid
    return x


def open_fvgs(x: pd.DataFrame, i: int, side: str, lookback: int = 60) -> list[tuple[float, float]]:
    """Noch nicht angetestete Daily-FVGs (vor i entstanden), long: bullische FVG unter dem Kurs."""
    h, l = x["High"].to_numpy(), x["Low"].to_numpy()
    zones = []
    for k in range(max(2, i - lookback), i - 1):
        if side == "long" and l[k] > h[k - 2]:
            lo_, hi_ = h[k - 2], l[k]
            if (l[k + 1:i] > lo_).all() if k + 1 < i else True:  # unten nicht durchstossen
                if (l[k + 1:i] > hi_).all() if k + 1 < i else True:  # noch nicht angetestet
                    zones.append((lo_, hi_))
        if side == "short" and h[k] < l[k - 2]:
            lo_, hi_ = h[k], l[k - 2]
            if (h[k + 1:i] < lo_).all() if k + 1 < i else True:
                zones.append((lo_, hi_))
    return zones


def confis(x: pd.DataFrame, i: int, e: int, side: str, ext_day: int, cross_dn, cross_up,
           rsi_dn, rsi_up, macd_dn, macd_up) -> dict:
    """Confis 3-9 fuer Fractal i, Einstieg e (Werte nur bis e)."""
    lo = side == "long"
    lvl = x["Low"].iat[i] if lo else x["High"].iat[i]
    atr_i = x["atr"].iat[i]
    grid = x["grid"].iat[i]
    c = {}
    c["ma_cross"] = bool((cross_up if lo else cross_dn).iloc[i:min(e, i + CROSS_WINDOW) + 1].any())
    c["rsi_cross"] = bool((rsi_up if lo else rsi_dn).iloc[i:e + 1].any())
    c["macd_cross"] = bool((macd_up if lo else macd_dn).iloc[ext_day:e + 1].any())
    c["bb"] = bool(lvl < x["bb_lo"].iat[i]) if lo else bool(lvl > x["bb_hi"].iat[i])
    c["whole_level"] = bool(abs(lvl - round(lvl / grid) * grid) <= NEAR_ATR * atr_i)
    near = [abs(lvl - x["piv_" + k].iat[i]) <= NEAR_ATR * atr_i for k in ("P", "R1", "S1", "R2", "S2")
            if pd.notna(x["piv_" + k].iat[i])]
    for zlo, zhi in open_fvgs(x, i, side):
        near.append(zlo - NEAR_ATR * atr_i <= lvl <= zhi + NEAR_ATR * atr_i)
    c["poi"] = bool(any(near))
    wt = x["w_trend"].iat[e]
    c["weekly"] = bool(pd.notna(wt) and ((wt > 0) if lo else (wt < 0)))
    return c


def signals(x: pd.DataFrame) -> list[dict]:
    diff = x["ma_fast"] - x["ma_slow"]
    cross_dn, cross_up = (diff < 0) & (diff.shift(1) >= 0), (diff > 0) & (diff.shift(1) <= 0)
    rd = x["rsi14"] - x["rsi14_ma"]
    rsi_dn, rsi_up = (rd < 0) & (rd.shift(1) >= 0), (rd > 0) & (rd.shift(1) <= 0)
    md = x["macd"] - x["macd_sig"]
    macd_dn, macd_up = (md < 0) & (md.shift(1) >= 0), (md > 0) & (md.shift(1) <= 0)
    out = []
    n = len(x)
    for i in range(60, n - 3):
        for side in ("long", "short"):
            if not x["frac_lo" if side == "long" else "frac_hi"].iat[i]:
                continue
            r = x["rsi_ml"].iloc[i - RSI_LOOKBACK:i + 1]
            ext = (r <= RSI_LOW) if side == "long" else (r >= RSI_HIGH)
            if not ext.any():
                continue
            ext_day = i - RSI_LOOKBACK + int(np.flatnonzero(ext.to_numpy())[-1])
            frac_lvl = x["Low"].iat[i] if side == "long" else x["High"].iat[i]
            trig = x["High"].iat[i] if side == "long" else x["Low"].iat[i]
            # E1: Schluss jenseits der Fractal-Kerze, ab Bestaetigung (i+2) bis i+MAX_WAIT
            e1 = None
            for e in range(i + 2, min(n, i + MAX_WAIT + 1)):
                cl = x["Close"].iat[e]
                if (side == "long" and cl <= frac_lvl) or (side == "short" and cl >= frac_lvl):
                    break  # Fractal vorher gebrochen -> kein Einstieg
                if (side == "long" and cl > trig) or (side == "short" and cl < trig):
                    e1 = e
                    break
            for etype, e, price in (("E1", e1, None if e1 is None else x["Close"].iat[e1]),
                                    ("E2", i + 3 if i + 3 < n else None,
                                     x["Open"].iat[i + 3] if i + 3 < n else None)):
                if e is None:
                    continue
                if (side == "long" and price <= frac_lvl) or (side == "short" and price >= frac_lvl):
                    continue
                ce = e if etype == "E1" else e - 1   # E2: nur Wissen bis zum Vortagesschluss
                c = confis(x, i, ce, side, ext_day, cross_dn, cross_up, rsi_dn, rsi_up, macd_dn, macd_up)
                out.append({"i": i, "e": e, "etype": etype, "side": side, "entry": price,
                            "frac_lvl": frac_lvl, "atr": x["atr"].iat[ce], "n_confis": sum(c.values()), **c})
    return out


def simulate(x: pd.DataFrame, s: dict, stop_kind: str, exit_kind: str, cost: float, end_idx: int):
    sign = 1 if s["side"] == "long" else -1
    entry = s["entry"]
    stop = s["frac_lvl"] if stop_kind == "S1" else entry - sign * 2 * s["atr"]
    risk = sign * (entry - stop)
    if not (risk > 0):
        return None
    if exit_kind == "X1":
        target = entry + sign * 2 * risk
    elif exit_kind == "X2":
        target = entry + sign * 3 * risk
    elif exit_kind == "X3":
        target = entry + sign * 3 * s["atr"]
    else:
        target = None
    max_hold = 30 if exit_kind == "X4" else 15
    h, l, c = x["High"].to_numpy(), x["Low"].to_numpy(), x["Close"].to_numpy()
    start = s["e"] if s["etype"] == "E2" else s["e"] + 1
    last = min(end_idx, s["e"] + max_hold)
    exit_px, k = None, start
    for k in range(start, last + 1):
        if (sign == 1 and l[k] <= stop) or (sign == -1 and h[k] >= stop):
            exit_px = stop
            break
        if target is not None and ((sign == 1 and h[k] >= target) or (sign == -1 and l[k] <= target)):
            exit_px = target
            break
        if exit_kind == "X4" and k > s["e"] and ((sign == 1 and c[k] < l[k - 1]) or (sign == -1 and c[k] > h[k - 1])):
            exit_px = c[k]
            break
    if exit_px is None:
        k = last
        exit_px = c[k]
    return {"r": (sign * (exit_px - entry) - cost) / risk, "exit_k": k}


def run_variant(market_data: dict, var: tuple, is_end: pd.Timestamp, is_start: pd.Timestamp) -> pd.DataFrame:
    etype, stop_kind, gate, exit_kind = var
    rows = []
    for name, (x, sigs, cost) in market_data.items():
        end_idx = int(np.searchsorted(x.index, is_end, side="right")) - 1
        busy_until = {"long": -1, "short": -1}
        for s in sorted((s for s in sigs if s["etype"] == etype), key=lambda s: s["e"]):
            t = x.index[s["e"]]
            if t < is_start or t > is_end or s["e"] > end_idx:
                continue
            if gate == "gate" and s["n_confis"] < 3:
                continue
            if s["e"] <= busy_until[s["side"]]:
                continue  # eine Position je Markt und Richtung
            res = simulate(x, s, stop_kind, exit_kind, cost, end_idx)
            if res is None:
                continue
            busy_until[s["side"]] = res["exit_k"]
            rows.append({"markt": name, "datum": t.date(), "seite": s["side"], "r": res["r"],
                         "n_confis": s["n_confis"]})
    return pd.DataFrame(rows)


def stats(r: pd.Series) -> dict:
    n = len(r)
    if n < 2:
        return {"n": n}
    m, sd = r.mean(), r.std(ddof=1)
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": n, "mean_r": m, "t": m / (sd / np.sqrt(n)), "treffer": (r > 0).mean(),
            "pf": wins / losses if losses > 0 else np.nan, "summe_r": r.sum()}


def main() -> None:
    lock = Lock(LOCK)
    lock.register_split("2016-01-01", "2021-12-31", "2024-12-31")
    lock.register_blind("2010-01-01", "2015-12-31")
    if lock.trials == 0:
        lock.log_trials(len(VARIANTS), "Typ R ohne Makro: E1/E2 x S1/S2 x alle/gate x X1-X4 (02.11.)")
    split = lock.split
    is_start, is_end = pd.Timestamp(split["is_start"]), pd.Timestamp(split["is_end"])
    data = {}
    for name, (_, grid, cost) in MARKETS.items():
        df = load_market(name).loc[:is_end]          # nichts nach dem IS-Ende
        df = df.loc[pd.Timestamp("2015-01-01"):]     # 1 Jahr Vorlauf fuer Indikatoren
        x = features(df, grid)
        data[name] = (x, signals(x), cost)
        print(f"{name}: {sum(1 for s in data[name][1] if s['etype'] == 'E1')} E1- / "
              f"{sum(1 for s in data[name][1] if s['etype'] == 'E2')} E2-Signale (inkl. Vorlauf)", flush=True)
    rows, trades = [], {}
    for var in VARIANTS:
        t = run_variant(data, var, is_end, is_start)
        trades[var] = t
        rows.append({"variante": " ".join(var), **(stats(t["r"]) if len(t) else {"n": 0})})
    res = pd.DataFrame(rows).sort_values("t", ascending=False)
    pd.set_option("display.width", 180)
    print(res.round(3).to_string(index=False))
    res.to_csv("htf_daily_trade/backtest_r_is.csv", index=False)
    best = res.iloc[0]
    tb = trades[tuple(best["variante"].split())]
    sr = tb["r"].mean() / tb["r"].std(ddof=1)
    print(f"\nBeste Variante {best['variante']}: Sharpe je Trade {sr:.3f}, n {len(tb)}, "
          f"Deflated Sharpe (32 Versuche) {deflated_sharpe(sr, len(tb), lock.trials):.3f}")
    print(tb.groupby("markt")["r"].agg(["size", "mean", "sum"]).round(2).to_string())
    print(tb.groupby(pd.to_datetime(tb["datum"]).dt.year)["r"].agg(["size", "mean", "sum"]).round(2).to_string())
    # Gegenprobe Gate: alle vs. gate je gleicher Restvariante
    print("\nGate-Wirkung (mittleres R, gleiche Einstieg/Stop/Ausstieg):")
    for e, s, x_ in itertools.product(("E1", "E2"), ("S1", "S2"), ("X1", "X2", "X3", "X4")):
        a, g = trades[(e, s, "alle", x_)], trades[(e, s, "gate", x_)]
        if len(a) and len(g):
            print(f"  {e} {s} {x_}: alle {a.r.mean():+.3f} (n {len(a)})  gate {g.r.mean():+.3f} (n {len(g)})")


if __name__ == "__main__":
    main()
