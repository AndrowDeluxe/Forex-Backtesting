"""Gold ASB -- Optimierung von Einstieg, Order-Logik, Filtern und Ausstieg (2026-10-01).

Folgt auf scripts/research_gold_asb_execution_costs.py (Proben p6_5-p6_8: Bein
kostenrobust, Lag im realen Bereich Rauschen). Alle Varianten hier laufen auf
einer M5-Engine mit ECHTEN Kosten (TTP 2,08 bps RT, teuerster Broker) und
werden gegen dieselbe Basis gestellt.

Basis = realistische Version des Produktions-Backtests: ruhende OCO-Stop-Order
ab Range-Schluss 01:00 NY, storniert um 02:00 NY (= Delay-Filter <=3 M15-Bars),
Fill am Level (bzw. am Open, wenn die Bar schon jenseits eroeffnet), fester SL
1x Range, Zeit-Exit 11:15 NY (= Close der 11:00-M15-Bar wie die Engine), alle
anderen 4 Filter. Unterschied zur M15-Engine: die Bar 01:00-01:15 ist nicht
ausgeschlossen (die Engine beginnt die Fill-Suche erst bei window_end+1 und
fuellt dann zum Level, auch wenn die Bar schon jenseits eroeffnet hat).

Schutz gegen Data-Mining (Methodenregel aus realkosten-und-ausfuehrungs-probe.md):
jede Variante mit IS 2016-2021 / OOS 2022-2026, gepaartem Bootstrap gegen die
Basis (nur Tage, die beide handeln, plus Effekt der unterschiedlichen
Trade-Menge ueber den Summen-Bootstrap), Plateau statt Einzelwert.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.filters import attach_series_change, attach_series_level, rolling_liquidity_threshold
from strategy.indicators import compute_adx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_gold_asb_execution_costs import load_all  # noqa: E402

TTP_BPS = 2.08
IS_END = pd.Timestamp("2022-01-01", tz="America/New_York")


def day_table(m15, m5, daily_close, daily_close_silver, friction) -> pd.DataFrame:
    """Ein Eintrag je Asien-Fenster: Range aus M5 (21:00-01:00 NY), Filter-Merkmale
    zum Range-Schluss (alle ohne Lookahead, gleiche Ausrichtung wie filters.py)."""
    idx = m5.index
    mins = idx.hour * 60 + idx.minute
    ends = idx[(mins == 60)]  # 01:00-Bars = window_end
    rows = []
    hi, lo = m5["high"].to_numpy(), m5["low"].to_numpy()
    for we in ends:
        ws = we - pd.Timedelta(hours=4)
        a, b = idx.searchsorted(ws), idx.searchsorted(we)
        if b - a < 24:  # unvollstaendiges Fenster (Wochenstart, Feiertag)
            continue
        rows.append({"window_end": we, "r_hi": hi[a:b].max(), "r_lo": lo[a:b].min()})
    days = pd.DataFrame(rows)
    adx = compute_adx(m15)["adx"]
    days["adx"] = adx.reindex(days["window_end"]).to_numpy()
    tmp = days.assign(entry_time=days["window_end"])
    tmp = attach_series_level(tmp, daily_close, "gold_close_prior")
    tmp = attach_series_level(tmp, daily_close.rolling(200).mean(), "gold_sma_prior")
    tmp = attach_series_change(tmp, daily_close_silver, "silver_chg", window=5)
    tmp = attach_series_level(tmp, friction, "friction_prior")
    tmp = attach_series_level(tmp, rolling_liquidity_threshold(friction, 2 / 3, 250), "friction_thr")
    days = tmp.drop(columns="entry_time")
    days["trend_up"] = days["gold_close_prior"] > days["gold_sma_prior"]
    days["liq_ok"] = days["friction_prior"] <= days["friction_thr"]
    return days.dropna(subset=["adx", "gold_sma_prior", "silver_chg", "friction_thr"]).reset_index(drop=True)


def simulate(days, m5, *, fill_from="01:00", cancel="02:00", entry="stop", lag_min=0,
             stop_frac=1.0, be_r=None, tp_r=None, trail_start=None, trail_dist=None,
             partial_r=None, partial_frac=0.5, exit_time="11:15", bps=TTP_BPS,
             range_end_shift_min=0):
    """entry: "stop"      ruhende OCO-Stop-Order (Fill am Level / Open bei Gap)
              "close5"    Einstieg zum Close der ersten M5-Bar, die jenseits SCHLIESST
              "market"    Market-Order lag_min Minuten nach der Beruehrung
              "retest"    nach Beruehrung Limit am Level, gilt bis cancel
    Rueckgabe: ein Trade je Tag mit Richtung, R (gegen geplantes Risiko sd), Exit-Grund."""
    o, h, l, c = (m5[x].to_numpy() for x in ("open", "high", "low", "close"))
    idx = m5.index
    ff_h, ff_m = map(int, fill_from.split(":"))
    ca_h, ca_m = map(int, cancel.split(":"))
    ex_h, ex_m = map(int, exit_time.split(":"))
    out = []
    for d in days.itertuples():
        day = d.window_end.normalize()
        t_from = day + pd.Timedelta(hours=ff_h, minutes=ff_m)
        t_cancel = day + pd.Timedelta(hours=ca_h, minutes=ca_m)
        t_exit = day + pd.Timedelta(hours=ex_h, minutes=ex_m)
        rh, rl = d.r_hi, d.r_lo
        sd = stop_frac * (rh - rl)
        if sd <= 0:
            continue
        i = idx.searchsorted(t_from)
        i_cancel = idx.searchsorted(t_cancel)
        i_exit = idx.searchsorted(t_exit)
        if i_exit >= len(idx):
            break
        # --- Trigger (erste eindeutige Beruehrung) ---
        trig, dirn = None, 0
        for j in range(i, i_cancel):
            up, dn = h[j] >= rh, l[j] <= rl
            if up and not dn:
                trig, dirn = j, 1; break
            if dn and not up:
                trig, dirn = j, -1; break
            if up and dn:
                break  # mehrdeutig -> Tag verwerfen (Engine-Konvention: weiter warten waere OCO-widrig)
        if trig is None:
            continue
        L = rh if dirn == 1 else rl
        # --- Einstieg ---
        e_i, P = None, None
        if entry == "stop":
            e_i = trig
            P = max(L, o[trig]) if dirn == 1 else min(L, o[trig])
        elif entry == "close5":
            for j in range(trig, i_cancel):
                if (c[j] > L) if dirn == 1 else (c[j] < L):
                    e_i, P = j + 1, o[j + 1]; break  # Fill zum Open der Folgebar (Close-Signal)
        elif entry == "market":
            e_i = idx.searchsorted(idx[trig] + pd.Timedelta(minutes=lag_min))
            P = o[e_i]
        elif entry == "retest":
            for j in range(trig + 1, i_cancel):
                if (l[j] <= L) if dirn == 1 else (h[j] >= L):
                    e_i = j
                    P = min(L, o[j]) if dirn == 1 else max(L, o[j]); break
        if e_i is None or e_i >= i_exit:
            continue
        sl = L - dirn * sd  # SL strukturell am Level verankert (wie Engine)
        if (dirn * (P - sl)) <= 0:
            continue
        # Pre-Entry-Stop (nur bei verzoegerten Varianten relevant): SL schon beruehrt -> kein Trade
        if e_i > trig:
            seg = slice(trig, e_i)
            if (l[seg] <= sl).any() if dirn == 1 else (h[seg] >= sl).any():
                continue
        risk = dirn * (P - sl)  # tatsaechliche Distanz (Funded sizet darauf)
        cur_sl, be_done, best = sl, False, P
        part_done, part_pnl, rem = False, 0.0, 1.0
        X, why = None, None
        for k in range(e_i, i_exit):
            fav = h[k] if dirn == 1 else l[k]
            if be_r is not None and not be_done and dirn * (fav - P) >= be_r * sd:
                cur_sl, be_done = max(cur_sl, P) if dirn == 1 else min(cur_sl, P), True
            if (l[k] <= cur_sl) if dirn == 1 else (h[k] >= cur_sl):
                X = min(cur_sl, o[k]) if dirn == 1 else max(cur_sl, o[k])
                why = "be" if (be_done and abs(cur_sl - P) < 1e-9) else ("trail" if cur_sl != sl else "stop")
                break
            if partial_r is not None and not part_done and dirn * (fav - P) >= partial_r * sd:
                part_pnl += partial_frac * partial_r * sd
                rem, part_done = 1 - partial_frac, True
            if tp_r is not None and dirn * (fav - P) >= tp_r * sd:
                X, why = P + dirn * tp_r * sd, "tp"; break
            best = max(best, h[k]) if dirn == 1 else min(best, l[k])
            if trail_start is not None and dirn * (best - P) >= trail_start * sd:
                new = best - dirn * trail_dist * sd
                cur_sl = max(cur_sl, new) if dirn == 1 else min(cur_sl, new)
        if X is None:
            X, why = o[i_exit], "time"
        pnl = part_pnl + rem * dirn * (X - P) - bps / 1e4 * P
        out.append({"window_end": d.window_end, "dir": dirn, "R": pnl / risk, "why": why,
                    "adx": d.adx, "trend_up": d.trend_up, "silver_chg": d.silver_chg, "liq_ok": d.liq_ok,
                    "entry_min": (idx[e_i] - d.window_end).total_seconds() / 60, "sd": sd, "P": P})
    t = pd.DataFrame(out)
    t["trend_al"] = np.where(t["dir"] == 1, t["trend_up"], ~t["trend_up"].astype(bool))
    t["silver_al"] = np.where(t["dir"] == 1, t["silver_chg"] > 0, t["silver_chg"] < 0)
    return t


def apply_filters(t, skip=(), adx_min=15.0):
    m = pd.Series(True, index=t.index)
    if "adx" not in skip:
        m &= t["adx"] >= adx_min
    if "trend" not in skip:
        m &= t["trend_al"].astype(bool)
    if "silver" not in skip:
        m &= t["silver_al"].astype(bool)
    if "liquidity" not in skip:
        m &= t["liq_ok"].astype(bool)
    return t[m]


def summarize(t, base=None, n_boot=2000, seed=7):
    r = t["R"]
    isr, oos = r[t.window_end < IS_END], r[t.window_end >= IS_END]
    eq = r.cumsum()
    pf = r[r > 0].sum() / -r[r < 0].sum()
    yrs = t.groupby(t.window_end.dt.year)["R"].sum()
    s = {"n": len(r), "avgR": r.mean(), "PF": pf, "sumR": r.sum(), "DD": (eq - eq.cummax()).min(),
         "IS": isr.mean(), "OOS": oos.mean(), "yrs+": f"{(yrs > 0).sum()}/{len(yrs)}"}
    if base is not None:
        # Summen-Bootstrap: Tage beider Mengen vereinigen, Differenz der R-Summen je Tag
        a = base.set_index("window_end")["R"]
        b = t.set_index("window_end")["R"]
        u = a.index.union(b.index)
        diff = (b.reindex(u).fillna(0) - a.reindex(u).fillna(0)).to_numpy()
        rng = np.random.default_rng(seed)
        bs = np.array([rng.choice(diff, len(diff)).sum() for _ in range(n_boot)])
        s["dSumR"] = diff.sum()
        s["P(d>0)"] = (bs > 0).mean()
    return s


def line(name, s):
    txt = (f"{name:34s} n={s['n']:4d} avgR={s['avgR']:+.3f} PF={s['PF']:.2f} sumR={s['sumR']:+6.1f} "
           f"DD={s['DD']:5.1f} IS={s['IS']:+.3f} OOS={s['OOS']:+.3f} yrs+={s['yrs+']}")
    if "dSumR" in s:
        txt += f"  dSumR={s['dSumR']:+6.1f} P(>0)={s['P(d>0)']:.2f}"
    print(txt)


if __name__ == "__main__":
    m15, m5, dc, dcs, fr = load_all()
    days = day_table(m15, m5, dc, dcs, fr)
    print("Tage:", len(days), days.window_end.min(), days.window_end.max())

    base_all = simulate(days, m5)
    base = apply_filters(base_all)
    print("\n=== Basis ===")
    line("ungefiltert (OCO 01-02, TTP)", summarize(base_all))
    line("BASIS: OCO 01:00-02:00 + 4 Filter", summarize(base))

    print("\n=== Teil 2a: Einstiegsfenster (OCO-Stop, Storno-Zeit) ===")
    for ff, ca in [("01:15", "02:00"), ("01:00", "01:15"), ("01:00", "01:30"), ("01:00", "01:45"),
                   ("01:00", "02:00"), ("01:00", "02:30"), ("01:00", "03:00"), ("01:00", "04:00"),
                   ("01:00", "06:00"), ("01:00", "11:00")]:
        t = apply_filters(simulate(days, m5, fill_from=ff, cancel=ca))
        line(f"fill {ff}-{ca}", summarize(t, base))

    print("\n=== Teil 2b: Order-Logik (Fenster 01:00-02:00) ===")
    for name, kw in [("stop (Basis)", {}), ("close5 (M5-Schluss jenseits)", {"entry": "close5"}),
                     ("market +5 Min", {"entry": "market", "lag_min": 5}),
                     ("market +15 Min", {"entry": "market", "lag_min": 15}),
                     ("market +30 Min", {"entry": "market", "lag_min": 30}),
                     ("market +45 Min (~Live)", {"entry": "market", "lag_min": 45}),
                     ("retest-Limit bis 02:00", {"entry": "retest"}),
                     ("retest-Limit bis 04:00", {"entry": "retest", "cancel": "04:00"})]:
        t = apply_filters(simulate(days, m5, **kw))
        line(name, summarize(t, base))

    print("\n=== Teil 2c: Filter (Leave-one-out + ADX-Gitter) ===")
    for sk in ["adx", "trend", "silver", "liquidity"]:
        line(f"ohne {sk}", summarize(apply_filters(base_all, skip=(sk,)), base))
    line("nur ADX", summarize(apply_filters(base_all, skip=("trend", "silver", "liquidity")), base))
    line("nur Liquiditaet", summarize(apply_filters(base_all, skip=("trend", "silver", "adx")), base))
    for a in [10, 12.5, 15, 17.5, 20, 25, 30]:
        line(f"adx_min {a}", summarize(apply_filters(base_all, adx_min=a), base))

    print("\n=== Teil 3a: Break-even ===")
    for be in [0.5, 1.0, 1.5, 2.0, 3.0]:
        line(f"BE bei {be}R", summarize(apply_filters(simulate(days, m5, be_r=be)), base))
    print("\n=== Teil 3b: Take-Profit ===")
    for tp in [1.0, 1.5, 2.0, 3.0, 4.0, 6.0]:
        line(f"TP {tp}R", summarize(apply_filters(simulate(days, m5, tp_r=tp)), base))
    print("\n=== Teil 3c: Trailing (Start / Abstand in R) ===")
    for ts, td in [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (2.0, 1.5), (3.0, 1.5), (3.0, 2.0)]:
        line(f"Trail ab {ts}R, Abstand {td}R", summarize(apply_filters(simulate(days, m5, trail_start=ts, trail_dist=td)), base))
    print("\n=== Teil 3d: Teilausstieg 50 % ===")
    for pr in [1.0, 1.5, 2.0, 3.0]:
        line(f"50 % bei {pr}R", summarize(apply_filters(simulate(days, m5, partial_r=pr)), base))
    print("\n=== Teil 3e: Zeit-Exit (NY) ===")
    for ex in ["08:15", "09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:45"]:
        line(f"Exit {ex}", summarize(apply_filters(simulate(days, m5, exit_time=ex)), base))
    print("\n=== Teil 3f: Stop-Faktor (x Range) ===")
    for sf in [0.5, 0.75, 1.0, 1.25, 1.5]:
        line(f"stop_frac {sf}", summarize(apply_filters(simulate(days, m5, stop_frac=sf)), base))
