"""LTF-Einstieg fuer den eingefrorenen Daily-Kandidaten (Hash 6c55e525) -- Nutzerauftrag 11.11.2026, Plan freigegeben.

    python -m htf_daily_trade.ltf_entry          # IS 2016-2021 + OOS 2022-2024; 2025/26 bleibt zu (Tresor 01-07/2026)

Daily-Idee: C2-Ausloeser (Schluss jenseits der 3 Vorkerzen nach Sweep, MA 12/20) mit Faber 10M GEGEN, COT-Fluss MIT,
Rohstoff-Veto, Stand Schluss des Signaltags. Gueltig ab Folgetag 00:00 UTC fuer 10 Handelstage; je Markt und
Richtung nur eine aktive Idee.
LTF H1 bzw. M15 (NZDUSD nur H1). Trigger (nur abgeschlossene Kerzen, Struktur aus gold_smc_htf_ltf.structure, k=2):
  L1 Sweep + CHoCH  Docht unter (ueber) das letzte Swing-Tief (-Hoch) ohne Schluss darunter, danach CHoCH in
                    Ideen-Richtung innerhalb von 10 Kerzen; Einstieg Schluss CHoCH, Stop Extrem seit dem Sweep
  L2 Doppel-BOS     zweiter Bruch in Ideen-Richtung seit dem letzten Richtungswechsel; Einstieg Schluss,
                    Stop letztes Swing-Extrem (ERL)
  L3 FVG-Limit      LTF-FVG in Ideen-Richtung bei passender Struktur-Bias; Limit FVG-Mitte (20 Kerzen gueltig,
                    verfaellt bei Bias-Wechsel), Stop Extrem der FVG-Startkerze
  L5 CRT (Tim)      fusion_lab.patterns.crt auf H4 (fuer H1) bzw. H1 (fuer M15), Typ CRT in Ideen-Richtung;
                    Einstieg Schluss C2, Stop Sweep-Extrem
  +S                Session-Fenster: Einstieg nur London 08-11 / NY 14:30-17 Berlin (auf L1, L2, L3, L5)
Stop mindestens 0,1 x Daily-ATR. Ziele: Z1 Ideen-Ende | Z2 Vortageshoch/-tief, sonst naechstes Daily-Fractal,
sonst 3 R, spaetestens Ideen-Ende | Z3 Tagesoeffnung +/- ADR20 (erreicht -> ADR ab Einstieg), Schluss 22:00 UTC.
Versuche je Idee: 1 oder 3. Kein BE, keine Teilgewinne. Stop vor Ziel in derselben Kerze; in der Fuellkerze
eines Limits nur der Stop. Kosten: Spread+Kommission je Markt + Swap-Modell TTP (c2_kandidat_report).
Sperre `htf_daily_ltf_entry`, alle Varianten gezaehlt.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from fusion_lab.filters.cot_flow import CotFlowFilter
from fusion_lab.patterns import crt
from gold_smc_htf_ltf.structure import compute_market_structure
from htf_daily_trade.backtest_macro import c_signals
from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.c2_exit_varianten import konto
from htf_daily_trade.c2_kandidat_report import AUFSCHLAG, CCY, rates
from htf_daily_trade.c2_veto_combos import commodity_state
from htf_daily_trade.filter_matrix import MARKETS, WARMUP, load_market, trend_dirs
from research_lock import Lock, deflated_sharpe

LOCK = "htf_daily_ltf_entry"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2021-12-31", "2025-12-31", "2026-07-28"
RUN_END = pd.Timestamp("2024-12-31 23:59")      # 2025 + Tresor bleiben zu
IDEA_DAYS = 10
LTF_FILES = {"M15": "{m}_M15_2016-01-01_2026-07-29.parquet", "H1": "{m}_H1_2007-01-01_2026-11-10.parquet"}
METAL_FILES = {"M15": {"XAUUSD": ["GOLD_M15_2009-01-01_2016-01-01.parquet", "GOLD_M15_2016-01-01_2026-06-02.parquet"],
                       "XAGUSD": ["SILVER_M15_2009-01-01_2016-01-01.parquet", "SILVER_M15_2016-01-01_2026-06-02.parquet"]},
               "H1": {"XAUUSD": ["GOLD_H1_2016-01-01_2026-10-29.parquet"],
                      "XAGUSD": ["SILVER_H1_2016-01-01_2026-08-01.parquet"]}}
TRIGGERS = ("L1", "L2", "L3", "L5")
TARGETS = ("Z1", "Z2", "Z3")
VARIANTS = [(tf, trg, sess, z, att) for tf in ("H1", "M15") for trg in TRIGGERS for sess in (False, True)
            for z in TARGETS for att in (1, 3)]
SWEEP_BARS, FVG_BARS, MIN_STOP_ATR = 10, 20, 0.1


# --------------------------------------------------------------------------- Daily-Ideen
def daily_ideas() -> pd.DataFrame:
    cot = CotFlowFilter(4)
    rows = []
    for name, (_, grid, _) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp(WARMUP):RUN_END.normalize()], grid)
        td = trend_dirs(x)
        n, last_end = len(x), {"long": -1, "short": -1}
        for s in sorted((s for s in c_signals(x) if s["kind"] == "C2"), key=lambda s: s["i"]):
            t, side = s["i"], s["side"]
            if t + 1 >= n or t <= last_end[side] or x.index[t + 1] < pd.Timestamp(IS_START):
                continue
            sign = 1 if side == "long" else -1
            if td["T6"].iat[t] * sign >= 0:                      # Faber muss GEGEN die Richtung stehen
                continue
            if cot.direction(name, x.index[t + 1]) * sign <= 0:  # COT-Fluss MIT
                continue
            end_i = min(n - 1, t + IDEA_DAYS)
            last_end[side] = end_i
            rows.append({"markt": name, "seite": side, "signal": x.index[t], "datum": x.index[t + 1],
                         "start": x.index[t] + pd.Timedelta(days=1), "ende": x.index[end_i] + pd.Timedelta(days=1),
                         "daily_stop": s["frac_lvl"], "atr": s["atr"],
                         "frac_lvls": _fractal_levels(x, t, side)})
    ideas = pd.DataFrame(rows)
    ideas["RS"] = commodity_state(ideas)
    return ideas[ideas["RS"] != "gegen"].reset_index(drop=True)


def _fractal_levels(x: pd.DataFrame, t: int, side: str) -> list[float]:
    """Bestaetigte Daily-Fractals bis t (in Ziel-Richtung), juengste zuerst."""
    col, px = ("frac_hi", "High") if side == "long" else ("frac_lo", "Low")
    k = np.flatnonzero(x[col].to_numpy()[: t - 1])
    return [float(x[px].iat[i]) for i in k[::-1][:20]]


# --------------------------------------------------------------------------- LTF-Daten + Trigger
def load_ltf(name: str, tf: str) -> pd.DataFrame | None:
    files = METAL_FILES[tf].get(name) or [LTF_FILES[tf].format(m=name)]
    parts = []
    for f in files:
        try:
            parts.append(pd.read_parquet(f"data_cache/combined/{f}")[["Open", "High", "Low", "Close"]])
        except FileNotFoundError:
            return None
    d = pd.concat(parts).sort_index()
    d = d[~d.index.duplicated(keep="last")]
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    return d.loc[:RUN_END.tz_localize("UTC")]


def trigger_events(d: pd.DataFrame, htf: pd.DataFrame) -> dict:
    """Je Trigger und Richtung: Liste (bar, entry, stop, limit) ueber die ganze Reihe (kausal)."""
    s = compute_market_structure(d.rename(columns=str.lower), k=2)
    h, l, c = s["high"].to_numpy(), s["low"].to_numpy(), s["close"].to_numpy()
    bias, choch, bos = s["bias"].to_numpy(), s["is_choch"].to_numpy(), s["is_bos"].to_numpy()
    erl_h, erl_l = s["erl_high"].to_numpy(), s["erl_low"].to_numpy()
    n = len(s)
    ev = {(t, side): [] for t in TRIGGERS for side in ("long", "short")}
    prev_l, prev_h = np.r_[np.nan, erl_l[:-1]], np.r_[np.nan, erl_h[:-1]]
    sweep_lo = (l < prev_l) & (c >= prev_l)
    sweep_hi = (h > prev_h) & (c <= prev_h)
    breaks = 0
    for i in range(1, n):
        if choch[i]:
            breaks = 1
        elif bos[i]:
            breaks += 1
        for side, b, sw, ext in (("long", 1, sweep_lo, l), ("short", -1, sweep_hi, h)):
            if bias[i] != b:
                continue
            if choch[i]:
                j0 = max(0, i - SWEEP_BARS)
                ks = np.flatnonzero(sw[j0:i])
                if len(ks):
                    k = j0 + ks[0]
                    stop = ext[k:i + 1].min() if b == 1 else ext[k:i + 1].max()
                    ev[("L1", side)].append((i, c[i], stop, False))
            if (choch[i] or bos[i]) and breaks == 2:
                stop = erl_l[i] if b == 1 else erl_h[i]
                if np.isfinite(stop):
                    ev[("L2", side)].append((i, c[i], stop, False))
            if i >= 2 and ((b == 1 and l[i] > h[i - 2]) or (b == -1 and h[i] < l[i - 2])):
                lim = (l[i] + h[i - 2]) / 2 if b == 1 else (h[i] + l[i - 2]) / 2
                stop = l[i - 1] if b == 1 else h[i - 1]
                ev[("L3", side)].append((i, lim, stop, True))
    # CRT auf der hoeheren Ebene, Einstieg am Schluss der C2-Kerze -> erste LTF-Kerze ab deren Ende
    cr = crt.detect(htf)
    if len(cr):
        cr = cr[cr["typ"] == "CRT"]
        dur = htf.index.to_series().diff().median()
        pos = d.index.searchsorted(cr["t"] + dur, side="left") - 1    # letzte LTF-Kerze innerhalb von C2
        for (_, r), p in zip(cr.iterrows(), pos):
            if 0 <= p < n:
                ev[("L5", r["side"])].append((int(p), r["entry"], r["stop"], False))
    return {k: np.array(v, dtype=float).reshape(-1, 4) for k, v in ev.items()}, bias


def in_session(idx: pd.DatetimeIndex) -> np.ndarray:
    b = idx.tz_convert("Europe/Berlin")
    m = b.hour * 60 + b.minute
    return ((m >= 8 * 60) & (m < 11 * 60)) | ((m >= 14 * 60 + 30) & (m < 17 * 60))


# --------------------------------------------------------------------------- Simulation
def first_hit(arr: np.ndarray, cond) -> int:
    k = np.flatnonzero(cond(arr))
    return int(k[0]) if len(k) else -1


def sim_one(d_h, d_l, d_c, i0, entry, stop, target, last, sign, limit):
    """Ab Kerze i0 (Markt: i0+1). Gibt (exit_idx, exit_px). Stop vor Ziel; Fuellkerze eines Limits nur Stop."""
    a = i0 if limit else i0 + 1
    if a > last:
        return last, d_c[last]
    hs, ls = d_h[a:last + 1], d_l[a:last + 1]
    st = np.flatnonzero(ls <= stop) if sign == 1 else np.flatnonzero(hs >= stop)
    if target is None:
        tg = np.array([], int)
    else:
        tg = np.flatnonzero(hs >= target) if sign == 1 else np.flatnonzero(ls <= target)
        if limit:
            tg = tg[tg > 0]
    s0 = st[0] if len(st) else 10 ** 9
    t0 = tg[0] if len(tg) else 10 ** 9
    if s0 == t0 == 10 ** 9:
        return last, d_c[last]
    if s0 <= t0:
        return a + s0, stop
    return a + t0, target


def run_market(name: str, tf: str, ideas: pd.DataFrame, rt: pd.DataFrame) -> list[dict]:
    d = load_ltf(name, tf)
    if d is None or ideas.empty:
        return []
    htf = crt.resample_server(d, "H4" if tf == "H1" else "H1")
    ev, _ = trigger_events(d, htf)
    idx = d.index
    sess = in_session(idx)
    dh, dl, dc, do = (d[k].to_numpy() for k in ("High", "Low", "Close", "Open"))
    day_key = idx.tz_convert("UTC").tz_localize(None).normalize()
    cost = MARKETS[name][2]
    out = []
    for idea in ideas.itertuples():
        sign = 1 if idea.seite == "long" else -1
        a = idx.searchsorted(pd.Timestamp(idea.start).tz_localize("UTC"))
        b = idx.searchsorted(pd.Timestamp(idea.ende).tz_localize("UTC")) - 1
        if b <= a:
            continue
        min_stop = MIN_STOP_ATR * idea.atr
        for trg in TRIGGERS:
            arr = ev[(trg, idea.seite)]
            cand = arr[(arr[:, 0] >= a) & (arr[:, 0] <= b)] if len(arr) else arr
            for use_sess in (False, True):
                cs = cand[sess[cand[:, 0].astype(int)]] if use_sess and len(cand) else cand
                for z in TARGETS:
                    for att in (1, 3):
                        busy_until, n_tr = -1, 0
                        for i0, entry, stop, lim in cs:
                            i0 = int(i0)
                            if n_tr >= att or i0 <= busy_until:
                                continue
                            lim = bool(lim)
                            if lim:   # Limit: Fuellung innerhalb FVG_BARS, sonst verfallen
                                w = (dl[i0 + 1:min(b, i0 + FVG_BARS) + 1] <= entry) if sign == 1 else \
                                    (dh[i0 + 1:min(b, i0 + FVG_BARS) + 1] >= entry)
                                k = np.flatnonzero(w)
                                if not len(k):
                                    continue
                                i0 = i0 + 1 + int(k[0])
                                if i0 <= busy_until:
                                    continue
                            if sign * (entry - stop) < min_stop:
                                stop = entry - sign * min_stop
                            risk = sign * (entry - stop)
                            if not (risk > 0):
                                continue
                            day = day_key[i0]
                            last = b
                            if z == "Z1":
                                target = None
                            elif z == "Z2":
                                di = ideas_daily[name]
                                pd_i = di.index.searchsorted(day) - 1
                                lvl = di["High"].iat[pd_i] if sign == 1 else di["Low"].iat[pd_i]
                                target = lvl
                                if sign * (lvl - entry) < risk:
                                    target = next((f for f in idea.frac_lvls if sign * (f - entry) >= risk),
                                                  entry + sign * 3 * risk)
                            else:
                                di = ideas_daily[name]
                                pd_i = di.index.searchsorted(day)
                                if pd_i >= len(di):
                                    continue
                                adr = di["adr"].iat[pd_i]
                                target = di["Open"].iat[pd_i] + sign * adr
                                if sign * (target - entry) <= 0:
                                    target = entry + sign * adr
                                eod = idx.searchsorted((day + pd.Timedelta(hours=22)).tz_localize("UTC")) - 1
                                last = max(i0 + (0 if lim else 1), min(b, eod))
                            ex_i, ex_px = sim_one(dh, dl, dc, i0, entry, stop, target, last, sign, lim)
                            days = (day_key[ex_i] - day).days
                            base, quote = CCY[name]
                            row_rt = rt.loc[:day].iloc[-1]
                            diff = row_rt[quote] - (row_rt[base] if base else 0.0)
                            mk = AUFSCHLAG["TTP"][1 if base is None else 0]
                            swap = ((diff if sign == 1 else -diff) + mk) / 365 * days * entry
                            r = (sign * (ex_px - entry) - cost - swap) / risk
                            out.append({"tf": tf, "trigger": trg, "session": use_sess, "ziel": z, "versuche": att,
                                        "markt": name, "seite": idea.seite, "idee": idea.datum,
                                        "datum": idx[i0].tz_convert("UTC").tz_localize(None),
                                        "exit_datum": idx[ex_i].tz_convert("UTC").tz_localize(None),
                                        "r": r, "r_stress": r - cost / risk,
                                        "stop_rel": risk / idea.datum_stop_dist if idea.datum_stop_dist else np.nan})
                            busy_until, n_tr = ex_i, n_tr + 1
    return out


ideas_daily: dict[str, pd.DataFrame] = {}


def main() -> None:
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    if lock.trials == 0:
        lock.log_trials(len(VARIANTS), "LTF-Einstieg: H1/M15 x L1/L2/L3/L5 x Session x Z1-Z3 x 1/3 Versuche (11.11.)")
    ideas = daily_ideas()
    for name in MARKETS:
        x = load_market(name).loc[pd.Timestamp(WARMUP):RUN_END.normalize()]
        tr = (x["High"] - x["Low"])
        ideas_daily[name] = x.assign(adr=tr.rolling(20).mean().shift(1))
    ideas["datum_stop_dist"] = [abs(ideas_daily[r.markt]["Close"].asof(r.signal) - r.daily_stop)
                                for r in ideas.itertuples()]
    print(f"Daily-Ideen: {len(ideas)} (IS {(ideas['datum'] <= IS_END).sum()}, OOS {(ideas['datum'] > IS_END).sum()})")
    rt = rates()
    rows = []
    for tf in ("H1", "M15"):
        for name in MARKETS:
            rows += run_market(name, tf, ideas[ideas["markt"] == name], rt)
            print(f"  {tf} {name}: fertig", flush=True)
    t = pd.DataFrame(rows)
    t["periode"] = np.where(t["datum"] <= pd.Timestamp(IS_END), "IS", "OOS")
    t.to_csv("htf_daily_trade/ltf_entry_trades.csv", index=False)
    report(t, ideas, lock.trials)


def report(t: pd.DataFrame, ideas: pd.DataFrame, n_trials: int) -> None:
    ref = pd.read_csv("htf_daily_trade/c2_kandidat_trades.csv", parse_dates=["einstieg", "ausstieg"])
    rows = []
    for v, g in t.groupby(["tf", "trigger", "session", "ziel", "versuche"]):
        tf = v[0]
        mk = g["markt"].unique()
        row = {"variante": f"{v[0]} {v[1]}{'+S' if v[2] else ''} {v[3]} x{v[4]}"}
        for per in ("IS", "OOS"):
            st = stats(g.loc[g["periode"] == per, "r"])
            row.update({f"{per}_n": st.get("n"), f"{per}_mean": st.get("mean_r"), f"{per}_t": st.get("t"),
                        f"{per}_pf": st.get("pf")})
        row["stop_rel"] = g["stop_rel"].median()
        row["ideen_mit_einstieg"] = g["idee"].nunique() / len(ideas[ideas["markt"].isin(mk)])
        k = konto(g[["datum", "exit_datum", "r"]], lambda x: 0.01)
        row.update({"cagr_1pct": k["cagr"], "dd_1pct": k["max_dd"]})
        rows.append(row)
    res = pd.DataFrame(rows)
    res["dsr"] = [deflated_sharpe(r.IS_t / np.sqrt(r.IS_n), int(r.IS_n), n_trials) if (r.IS_n or 0) > 2 else np.nan
                  for r in res.itertuples()]
    res = res.sort_values("IS_t", ascending=False)
    res.to_csv("htf_daily_trade/ltf_entry_is_oos.csv", index=False)
    pd.set_option("display.width", 240)
    print(f"\n== Top 20 nach IS-t (von {len(res)}), Lock {n_trials} Versuche ==")
    print(res.head(20).round(3).to_string(index=False))
    for dim in ("tf", "trigger", "session", "ziel", "versuche"):
        g = t.groupby([dim, "periode"])["r"].mean().unstack()
        print(f"\nØ R je {dim}:\n{g.round(3).to_string()}")
    for label, mk in (("alle 9 Maerkte (H1-Vergleich)", list(MARKETS)), ("ohne NZD (M15-Vergleich)",
                                                                        [m for m in MARKETS if m != "NZDUSD"])):
        r = ref[ref["markt"].isin(mk)]
        k = konto(r.rename(columns={"einstieg": "datum", "ausstieg": "exit_datum", "r_TTP": "r"}), lambda x: 0.01)
        print(f"\nDaily-Referenz {label}: IS {stats(r.loc[r.periode == 'IS', 'r_TTP'])['mean_r']:+.3f} R, "
              f"OOS {stats(r.loc[r.periode == 'OOS', 'r_TTP'])['mean_r']:+.3f} R, n {len(r)}; Konto 1 %: "
              f"CAGR {k['cagr']:+.1%}, DD {k['max_dd']:.1%}")


if __name__ == "__main__":
    main()
