"""ORB NASDAQ: SL an der 15:30-Kerze (Range-Gegenseite) + Market-Einstieg mit Versatz
(Nutzerauftrag 2026-11-18, Anlass: verpasste Trades 13./16./17.11.).

Live-Regeln als Basis: long + short, OCO, ohne Mittwoch, kein Ziel, Exit 16:00 NY,
Range = M15-Kerze 09:30-09:45 NY (= 15:30 MEZ), Storno einer Seite, deren geplanter SL
vor dem Fill beruehrt wird.

Varianten (Gitter, alle gezaehlt):
  SL      atr   = Level -/+ 0,6 x M15-ATR (live)
          kerze = Hoch/Tief der 15:30-Kerze (Range-Gegenseite)
  Storno  an / aus
  Einstieg
          ideal   = Stop-Order ab 09:45:00 (bisheriger Backtest, live nicht erreichbar)
          live    = Order liegt erst nach der 09:45-M1-Bar; wurde ein Level in dieser Minute
                    beruehrt, ist der Tag verpasst ("breakout_passed", wie die Bridge)
          mX      = wie live, aber: steht der Kurs am Ende der 09:45-Minute hoechstens X x ATR
                    hinter dem Level -> Market-Einstieg zum Kurs (SL wie geplant); weiter weg ->
                    verpasst; zurueck in der Range -> Stop-Orders normal legen
  Ziel    keins (16:00) / 3R

Konservativ: Market-Kurs = Schluss der 09:45-M1-Bar (live liegt die Order nach ~5-40 s).
Stop-Fill bei Gap ueber das Level zum Eroeffnungskurs der Bar. Der SL wird ab der Bar NACH
dem Fill geprueft (Konvention aller ORB-Laeufe); Spalte `avg_pess` wertet jeden SL-Touch in
der Fuell-Bar als Stop-out (untere Grenze).

Split (Lock `nasdaq_orb_kerzen_sl_20261118`): IS 28.07.2016-31.12.2022, OOS bis 17.05.2026,
Tresor 18.05.-17.11.2026 (zu, wird hier nicht gerechnet).

  python scripts/research_orb_nasdaq_kerzen_sl_market.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS  # noqa: E402

STRATEGY = "nasdaq_orb_kerzen_sl_20261118"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-07-28", "2022-12-31", "2026-05-17", "2026-11-17"
OUT = ROOT / "ny_open_orb" / "results" / "kerzen_sl_market"
STOP_ATR = 0.6
SLS = ["atr", "kerze"]
STORNOS = [True, False]
ENTRIES = ["ideal", "live", "m0.05", "m0.1", "m0.2", "m_inf"]
TARGETS = [None, 3.0]
HALF = SPREAD_BPS["NASDAQ"] / 10_000 / 2
ES, XS = ENTRY_SLIPPAGE_BPS / 10_000, EXIT_SLIPPAGE_BPS / 10_000


def days(frame: pd.DataFrame):
    tw = frame[frame.index >= frame["range_end"]]
    for session, day in tw.groupby("session"):
        if pd.Timestamp(session).day_name() == "Wednesday":
            continue
        day = day[day.index < day["session_close"].iloc[0]]
        if len(day) < 3 or pd.isna(day["orb_high"].iloc[0]):
            continue
        atr = day["atr"].iloc[0]
        if pd.isna(atr) or atr <= 0:
            continue
        yield session, day


def trade_day(day: pd.DataFrame, sl_mode: str, storno: bool, entry_mode: str, target_r):
    """Ein Tag -> dict mit r, r_pess, typ (stop/market) oder None. status fuer Zaehlung."""
    o, h, l, c = (day[k].to_numpy() for k in ("open", "high", "low", "close"))
    hi, lo, atr = day["orb_high"].iloc[0], day["orb_low"].iloc[0], day["atr"].iloc[0]
    level = {1: hi, -1: lo}
    if sl_mode == "atr":
        sl = {d: level[d] - d * STOP_ATR * atr for d in (1, -1)}
    else:
        sl = {1: lo, -1: hi}
    pending = {1, -1}
    start, fill = 0, None   # fill = (bar, richtung, preis, typ)

    def touched(d, k):
        return h[k] >= level[d] if d == 1 else l[k] <= level[d]

    def sl_touched(d, k):
        return l[k] <= sl[d] if d == 1 else h[k] >= sl[d]

    if entry_mode != "ideal":
        t0 = [d for d in (1, -1) if touched(d, 0)]
        if storno:
            for d in (1, -1):
                if sl_touched(d, 0) and d not in t0:
                    pending.discard(d)
        if t0:
            if entry_mode == "live" or len(t0) == 2:
                return None, "verpasst"
            d = t0[0]
            beyond = d * (c[0] - level[d])
            if beyond >= 0:
                x = np.inf if entry_mode == "m_inf" else float(entry_mode[1:]) * atr
                if beyond > x:
                    return None, "verpasst"
                if storno and sl_touched(d, 0):
                    return None, "verpasst"
                if d * (c[0] - sl[d]) <= 0:
                    return None, "verpasst"
                fill = (0, d, c[0], "market")
            elif storno and sl_touched(d, 0):
                pending.discard(d)
        start = 1
    if fill is None:
        for k in range(start, len(day)):
            if not pending:
                break
            tk = [d for d in pending if touched(d, k)]
            if len(tk) == 2:
                return None, "beide"
            if tk:
                d = tk[0]
                px = max(level[d], o[k]) if d == 1 else min(level[d], o[k])
                fill = (k, d, px, "stop")
                break
            if storno:
                for d in [d for d in pending if sl_touched(d, k)]:
                    pending.discard(d)
        if fill is None:
            return None, "kein_fill"
    k, d, px, typ = fill
    entry = px * (1 + (HALF + ES) * d)
    stop = sl[d] * (1 + HALF * d)
    if (entry - stop) * d <= 0:
        return None, "kein_fill"
    risk = abs(entry - stop)
    hh, ll, cc = h[k + 1:], l[k + 1:], c[k + 1:]
    if hh.size == 0:
        return None, "kein_fill"
    adv = ll if d == 1 else -hh
    fav = hh if d == 1 else -ll
    s_i = np.flatnonzero(adv <= stop * d)
    s_i = s_i[0] if s_i.size else 10**9
    t_i = 10**9
    if target_r is not None:
        tp = entry + d * target_r * risk
        ti = np.flatnonzero(fav >= tp * d)
        t_i = ti[0] if ti.size else 10**9
    if s_i <= t_i and s_i < 10**9:
        xr = stop
    elif t_i < 10**9:
        xr = tp
    else:
        xr = cc[-1]
    xp = xr * (1 - (HALF + XS) * d)
    r = d * (xp - entry) / risk
    stop_r = d * (stop * (1 - (HALF + XS) * d) - entry) / risk
    fill_bar_sl = typ == "stop" and ((l[k] <= stop) if d == 1 else (h[k] >= stop))
    cost_r = px * (2 * HALF + ES + XS) / risk
    return {"r": r, "r_pess": stop_r if fill_bar_sl else r, "typ": typ, "dir": d,
            "risk_pts": risk, "cost_r": cost_r}, "trade"


def stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    r = df["r"]
    eq = r.cumsum().to_numpy()
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    yrs = max(0.5, (r.index.max() - r.index.min()).days / 365.25)
    loss = -r[r < 0].sum()
    return {"n": len(r), "je_jahr": len(r) / yrs, "avg": r.mean(), "t": r.mean() / r.std() * np.sqrt(len(r)),
            "sum": r.sum(), "pf": r[r > 0].sum() / loss if loss > 0 else np.nan, "win": (r > 0).mean(),
            "maxdd": dd, "avg_pess": df["r_pess"].mean(), "avg_kosten_x2": (r - df["cost_r"]).mean(),
            "anteil_market": (df["typ"] == "market").mean(), "risk_pts_median": df["risk_pts"].median()}


def main() -> int:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    m15, m1 = fetch_m15("NASDAQ", IS_START, OOS_END), fetch_m1("NASDAQ", IS_START, OOS_END)
    fr = build_frame(m15, m1, range_bars=1)
    all_days = list(days(fr))
    all_days = [(s, d) for s, d in all_days if pd.Timestamp(s).tz_localize(None) <= pd.Timestamp(OOS_END)]
    print(f"{len(all_days)} Handelstage (ohne Mittwoch) bis {OOS_END}")
    OUT.mkdir(parents=True, exist_ok=True)
    rows, counts, store = [], [], {}
    for sl_mode in SLS:
        for storno in STORNOS:
            for em in ENTRIES:
                for tg in TARGETS:
                    name = f"SL={sl_mode} | Storno={'an' if storno else 'aus'} | {em} | Ziel={'16:00' if tg is None else f'{tg:g}R'}"
                    recs, st = [], {}
                    for s, d in all_days:
                        res, status = trade_day(d, sl_mode, storno, em, tg)
                        st[status] = st.get(status, 0) + 1
                        if res:
                            res["session"] = pd.Timestamp(s).tz_localize(None)
                            recs.append(res)
                    df = pd.DataFrame(recs).set_index("session").sort_index()
                    store[name] = df
                    counts.append({"variante": name, **st})
                    for part, sub in (("IS", lk.is_only(df)), ("OOS", lk.oos_only(df))):
                        rows.append({"variante": name, "sl": sl_mode, "storno": storno, "einstieg": em,
                                     "ziel": "16:00" if tg is None else f"{tg:g}R", "teil": part, **stats(sub)})
    n_trials = len(SLS) * len(STORNOS) * len(ENTRIES) * len(TARGETS)
    total = lk.log_trials(n_trials, note="SL atr/kerze x Storno x Einstieg (ideal/live/market) x Ziel")
    tab = pd.DataFrame(rows)
    # Deflated Sharpe je Variante auf IS (Trade-Sharpe)
    dsr = {}
    for name, df in store.items():
        r = lk.is_only(df)["r"]
        if len(r) > 30:
            dsr[name] = deflated_sharpe(r.mean() / r.std(), len(r), total, float(r.skew()), float(r.kurt() + 3))
    tab["dsr_is"] = tab["variante"].map(dsr)
    tab.to_csv(OUT / "grid.csv", index=False)
    pd.DataFrame(counts).fillna(0).to_csv(OUT / "status.csv", index=False)
    yearly = pd.DataFrame({n: df["r"].groupby(df.index.year).sum() for n, df in store.items()})
    yearly.to_csv(OUT / "jahre.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 200)
    cols = ["sl", "storno", "einstieg", "ziel", "teil", "n", "je_jahr", "avg", "t", "sum", "pf", "maxdd",
            "avg_pess", "avg_kosten_x2", "anteil_market", "risk_pts_median", "dsr_is"]
    print(tab[cols].round(3).to_string(index=False))
    print("\nStatus je Variante (gesamt IS+OOS):")
    print(pd.DataFrame(counts).fillna(0).to_string(index=False))
    print(f"\nVersuche gesamt im Lock: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
