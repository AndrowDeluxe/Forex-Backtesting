"""Mehrfach-Limit-Leiter fuer den Daily-Kandidaten + Gegenprobe Tagesschluss NY 17:00 (Nutzerauftrag 11.11.2026).

    python -m htf_daily_trade.c2_ladder            # Leiter-Varianten, IS 2016-2021 + OOS 2022-2024 (2025/Tresor zu)
    python -m htf_daily_trade.c2_ladder --ny       # eingefrorener Kandidat auf UTC- vs. NY-17:00-Tageskerzen

Leiter: nur Limits (keine Market-Order; Twin-Test 11.11.: Daily direkt ~0 R). Ideen = ltf_entry.daily_ideas().
Punkte (long tiefer, short hoeher):
  Z38/Z50/Z62/Z79  38,2/50/61,8/78,6 % der Zone Ausloese-Schluss -> Strukturstop (Z50 = eingefrorenes EL)
  W50              50 % der Vorwochen-Range (Twin P4)
Gueltigkeit V3 = 3 Tage (eingefroren) | V10 = bis Ideen-Ende. Stop S1 Struktur | SA Struktur + 0,5 ATR.
Jedes Bein wie der eingefrorene Trade: Stop ab Fuellkerze, Ausstieg 10 Handelstage nach Fuellung, Kosten + TTP-Swap.
Risiko RA = 1 % gesamt gleich auf die geplanten Limits | RB = jedes Limit 1 %.
Sperre `htf_daily_twin` (Fortsetzung des Twin-Tests), alle Varianten gezaehlt.

NY-Gegenprobe: Tageskerzen aus H1 (Metalle vor 2016 M15) neu gebuendelt, Tag = 17:00 New York bis 17:00
(= Broker-Server NY+7, siehe Memory broker_serverzeit_ny_plus_7). Regeln unveraendert (c2_blind.trades).
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.backtest_varianten import simulate
from htf_daily_trade.c2_exit_varianten import konto
from htf_daily_trade.filter_matrix import MARKETS, WARMUP, load_market
from htf_daily_trade.ltf_entry import IS_END, RUN_END, daily_ideas
from htf_daily_trade.twin_trade import LOCK, swap_r
from research_lock import Lock, deflated_sharpe

LADDERS = {
    "Z38": ["Z38"], "Z50": ["Z50"], "Z62": ["Z62"], "Z79": ["Z79"], "W50": ["W50"],
    "Z38+Z50": ["Z38", "Z50"], "Z50+Z62": ["Z50", "Z62"], "Z50+Z79": ["Z50", "Z79"],
    "Z38+Z50+Z62": ["Z38", "Z50", "Z62"], "Z50+Z62+Z79": ["Z50", "Z62", "Z79"],
    "Z38+Z50+Z62+Z79": ["Z38", "Z50", "Z62", "Z79"], "Z50+W50": ["Z50", "W50"], "Z50+W50+Z79": ["Z50", "W50", "Z79"],
}
FRAC = {"Z38": 0.382, "Z50": 0.5, "Z62": 0.618, "Z79": 0.786, "W50": 0.5}
VALID = {"V3": 3, "V10": 10}
STOPS = ("S1", "SA")
RISKS = ("RA", "RB")
POINTS = sorted(FRAC)


def point_legs(x, idea, t, cost, end_idx) -> dict:
    """{(punkt, gueltigkeit, stop): (r, fuell_datum, exit_datum) | None}."""
    h, l, o, c = (x[k].to_numpy() for k in ("High", "Low", "Open", "Close"))
    sign = 1 if idea.seite == "long" else -1
    wk = x[["High", "Low"]].resample("W-FRI").agg({"High": "max", "Low": "min"})
    prev_w = wk[wk.index < x.index[t + 1] - pd.Timedelta(days=x.index[t + 1].dayofweek)]
    wh, wl = (prev_w["High"].iat[-1], prev_w["Low"].iat[-1]) if len(prev_w) else (np.nan, np.nan)
    out = {}
    for p in POINTS:
        if p.startswith("Z"):
            lvl = c[t] + FRAC[p] * (idea.daily_stop - c[t])
        else:
            lvl = wh - FRAC[p] * (wh - wl) if sign == 1 else wl + FRAC[p] * (wh - wl)
        for vk, vd in VALID.items():
            for sk in STOPS:
                stop = idea.daily_stop - (sign * 0.5 * idea.atr if sk == "SA" else 0.0)
                key = (p, vk, sk)
                out[key] = None
                if not np.isfinite(lvl) or sign * (c[t] - lvl) <= 0 or sign * (lvl - stop) <= 0:
                    continue
                k = next((k for k in range(t + 1, min(end_idx, t + vd) + 1)
                          if (sign == 1 and l[k] <= lvl) or (sign == -1 and h[k] >= lvl)), None)
                if k is None:
                    continue
                px = min(o[k], lvl) if sign == 1 else max(o[k], lvl)
                en = dict(side=idea.seite, fill=k, price=px, struct=stop, atr=idea.atr, start=k, limit=True)
                res = simulate(x, en, "S1", "T8", cost, end_idx)
                if res is None:
                    continue
                risk = sign * (px - stop)
                r = res["r"] - swap_r(idea.markt, idea.seite, px, risk, x.index[k], x.index[res["exit_k"]])
                out[key] = (r, x.index[k], x.index[res["exit_k"]])
    return out


def ladder_rows(ideas: pd.DataFrame, pl: dict) -> pd.DataFrame:
    rows = []
    for ii, idea in ideas.iterrows():
        if ii not in pl:
            continue
        for ln, pts in LADDERS.items():
            for vk in VALID:
                for sk in STOPS:
                    legs = [pl[ii][(p, vk, sk)] for p in pts]
                    filled = [g for g in legs if g is not None]
                    if not filled:
                        continue
                    for rk in RISKS:
                        w = 1 / len(pts) if rk == "RA" else 1.0
                        rows.append({"variante": f"{ln} {vk} {sk} {rk}", "markt": idea.markt, "seite": idea.seite,
                                     "datum": min(g[1] for g in filled), "exit_datum": max(g[2] for g in filled),
                                     "r": w * sum(g[0] for g in filled), "n_beine": len(filled),
                                     "bein_r": np.mean([g[0] for g in filled]),
                                     "periode": "IS" if idea.datum <= pd.Timestamp(IS_END) else "OOS"})
    return pd.DataFrame(rows)


def run_ladder() -> None:
    lock = Lock(LOCK)
    n_var = len(LADDERS) * len(VALID) * len(STOPS) * len(RISKS)
    if lock.trials < 228 + n_var:
        lock.log_trials(n_var, f"Limit-Leiter: {len(LADDERS)} Leitern x Gueltigkeit 3/10 T x Stop S1/SA x Risiko RA/RB (11.11.)")
    ideas = daily_ideas()
    n_is = (ideas["datum"] <= pd.Timestamp(IS_END)).sum()
    print(f"Ideen: {len(ideas)} (IS {n_is}, OOS {len(ideas) - n_is}); Lock {LOCK}: {lock.trials} Versuche", flush=True)
    pl = {}
    for name, (_, grid, cost) in MARKETS.items():
        im = ideas[ideas["markt"] == name]
        if im.empty:
            continue
        x = features(load_market(name).loc[pd.Timestamp(WARMUP):RUN_END.normalize()], grid)
        end_idx = len(x) - 1
        for ii, idea in im.iterrows():
            t = int(x.index.searchsorted(idea.signal))
            if t + 1 <= end_idx:
                pl[ii] = point_legs(x, idea, t, cost, end_idx)
    t = ladder_rows(ideas, pl)
    t.to_csv("htf_daily_trade/c2_ladder_ideen.csv", index=False)
    n_ideas = {"IS": n_is, "OOS": len(ideas) - n_is}
    rows = []
    for v, g in t.groupby("variante"):
        row = {"variante": v}
        for per in ("IS", "OOS"):
            r = g.loc[g["periode"] == per, "r"]
            st = stats(r)
            row.update({f"{per}_n": st.get("n"), f"{per}_mean": st.get("mean_r"), f"{per}_t": st.get("t"),
                        f"{per}_sum": r.sum(), f"{per}_fuell": len(r) / n_ideas[per]})
        row["bein_r"] = g["bein_r"].mean()
        row["beine"] = g["n_beine"].mean()
        k = konto(g[["datum", "exit_datum", "r"]], lambda x: 0.01)
        row.update({"cagr": k["cagr"], "dd": k["max_dd"], "calmar": k["cagr"] / abs(k["max_dd"])})
        rows.append(row)
    res = pd.DataFrame(rows)
    res["dsr"] = [deflated_sharpe(r.IS_t / np.sqrt(r.IS_n), int(r.IS_n), lock.trials) for r in res.itertuples()]
    res = res.sort_values("IS_t", ascending=False)
    res.to_csv("htf_daily_trade/c2_ladder_varianten.csv", index=False)
    pd.set_option("display.width", 260)
    cols = ["variante", "IS_n", "IS_mean", "IS_t", "IS_sum", "OOS_n", "OOS_mean", "OOS_t", "OOS_sum",
            "IS_fuell", "beine", "bein_r", "cagr", "dd", "calmar", "dsr"]
    ref = res[res["variante"] == "Z50 V3 S1 RB"]
    print("\nReferenz eingefroren (Z50 V3 S1):\n" + ref[cols].round(3).to_string(index=False))
    print(f"\n== Top 25 nach IS-t (von {len(res)}) ==\n" + res[cols].head(25).round(3).to_string(index=False))
    print("\n== Top 15 nach Konto-Calmar (1 % je Einheit) ==\n"
          + res.sort_values("calmar", ascending=False)[cols].head(15).round(3).to_string(index=False))
    parts = res["variante"].str.split(expand=True)
    for i, dim in enumerate(("Leiter", "Gueltigkeit", "Stop", "Risiko")):
        g = res.groupby(parts[i])[["IS_mean", "OOS_mean", "IS_sum", "OOS_sum", "cagr", "dd", "calmar"]].mean()
        print(f"\nØ je {dim}:\n{g.round(3).to_string()}")


# --------------------------------------------------------------------------- NY-17:00-Tageskerzen
NY_SRC = {"XAUUSD": [("GOLD_M15_2009-01-01_2016-01-01.parquet", None), ("GOLD_H1_2016-01-01_2026-10-29.parquet", None)],
          "XAGUSD": [("SILVER_M15_2009-01-01_2016-01-01.parquet", None), ("SILVER_H1_2016-01-01_2026-08-01.parquet", None)]}


def ny_daily(name: str) -> pd.DataFrame:
    files = [f for f, _ in NY_SRC.get(name, [(f"{name}_H1_2007-01-01_2026-11-10.parquet", None)])]
    b = pd.concat(pd.read_parquet(f"data_cache/combined/{f}")[["Open", "High", "Low", "Close"]] for f in files)
    b = b[~b.index.duplicated(keep="last")].sort_index()
    srv = b.index.tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=7)   # Broker-Server NY+7
    key = srv.normalize()
    dow = key.dayofweek
    key = key.where(dow != 6, key + pd.Timedelta(days=1))
    key = key.where(dow != 5, key - pd.Timedelta(days=1))
    g = b.set_axis(srv).groupby(key)
    d = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(), "Low": g["Low"].min(), "Close": g["Close"].last()})
    return d[d.index.dayofweek < 5]


def run_ny() -> None:
    import htf_daily_trade.c2_blind as cb
    from htf_daily_trade.c2_kandidat_report import r_block

    # Kein Versuch: Sperre ist eingefroren; reine Datentreue-Probe (Kerzengrenze des Brokers), keine Auswahl.
    out = {}
    for label, loader in (("UTC (bisher)", cb.load_market), ("NY 17:00", ny_daily)):
        cb.load_market = loader
        t = cb.trades("2016-01-01", "2024-12-31")
        t["periode"] = np.where(t["einstieg"] <= pd.Timestamp(IS_END), "IS", "OOS")
        out[label] = t
        print(f"{label}: {len(t)} Trades", flush=True)
    rows = []
    for label, t in out.items():
        for per in ("IS", "OOS"):
            rows.append({"Kerzen": label, "Periode": per, **r_block(t.loc[t["periode"] == per, "r_TTP"])})
        kt = pd.DataFrame({"datum": t["einstieg"], "exit_datum": t["ausstieg"], "r": t["r_TTP"]})
        k = konto(kt, lambda x: 0.01)
        rows.append({"Kerzen": label, "Periode": "Konto 1 %", "n": len(t), "Ø R": k["cagr"], "t": k["max_dd"]})
    tab = pd.DataFrame(rows)
    pd.set_option("display.width", 240)
    print(tab.round(3).to_string(index=False))
    k = lambda d: set(zip(d["markt"], d["einstieg"].dt.normalize(), d["seite"]))
    a, b = k(out["UTC (bisher)"]), k(out["NY 17:00"])
    print(f"\nGleiche Trades (Markt, Tag, Seite): {len(a & b)} | nur UTC {len(a - b)} | nur NY {len(b - a)}")
    for per in ("IS", "OOS"):
        g = out["NY 17:00"]
        print(per, "je Markt NY:", g[g.periode == per].groupby("markt")["r_TTP"].mean().round(2).to_dict())
    tab.to_csv("htf_daily_trade/c2_ny_kerzen_vergleich.csv", index=False)
    out["NY 17:00"].to_csv("htf_daily_trade/c2_ny_kerzen_trades.csv", index=False)


if __name__ == "__main__":
    run_ny() if "--ny" in sys.argv else run_ladder()
