"""Faber-Monatstrend fuer EK (Tickmill) + Funded TTP: SL, Positionsclose, Filter,
Cross-Asset. Plan: ~/.claude/plans/binary-enchanting-breeze.md (freigegeben 2026-10-04).

Zwei Phasen, strikt getrennt:
  python scripts/research_faber_trend_funded.py is   -> Auswahl nur auf <= 2012,
       schreibt alle Varianten + Finalisten nach Claude outputs/faber_trend_funded_is.json
  python scripts/research_faber_trend_funded.py oos  -> liest NUR die geloggten
       Finalisten und rechnet sie einmal auf 2013-01..letzter abgeschl. Monat.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faber_trend import data as D, engine as E, signals as S  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_IS = os.path.join(ROOT, "Claude outputs", "faber_trend_funded_is.json")
OUT_OOS = os.path.join(ROOT, "Claude outputs", "faber_trend_funded_oos.json")

IS_START, IS_END = "2001-01-01", "2012-12-31"
OOS_START, END = "2013-01-01", "2026-09-30"
UNIV = [k for k in D.INSTRUMENTS if k != "BTC"]
TTP = E.Account("TTP", 200_000, True)
EK = E.Account("EK", 3_300, True)
MITTEL = E.Costs(0.0005, 0.025)
COST_TIERS = {"ohne": E.Costs(0, 0), "mittel": MITTEL, "hoch": E.Costs(0.0005, 0.05)}
# Fehlerhafte Bars (von Hand geprueft 2026-10-04): einzelner Phantom-Balken
REPAIR = {"EURUSD": ["2008-12-08"], "USDJPY": ["2008-12-08"]}


def load_all(with_btc=False):
    out = {}
    for k in UNIV + (["BTC"] if with_btc else []):
        df = D.load(k)
        for day in REPAIR.get(k, []):
            t = pd.Timestamp(day)
            if t in df.index:
                pc = df["close"].shift(1).loc[t]
                df.loc[t, ["open", "high", "low", "close"]] = pc
        if k == "SP500":
            gspc = pd.read_csv(D._frozen_path("SP500"), index_col="date", parse_dates=True)["close"]
            df["ref"] = gspc.reindex(df.index).ffill()
        out[k] = df
    return E.prepare(out)


# ---------------------------------------------------------------- Ziele
def tgt_sma(prep, inst, n=10, short=False):
    s, _ = S.sma_signal(prep[inst]["me"], n, allow_short=short)
    return S.by_month(s).map(lambda v: (inst, int(v)) if v != 0 else (None, 0))


def tgt_tsmom(prep, inst, short=False):
    s = S.tsmom_signal(prep[inst]["me"], 12, allow_short=short)
    return S.by_month(s).map(lambda v: (inst, int(v)) if v != 0 else (None, 0))


def tgt_always(prep, inst):
    s, _ = S.sma_signal(prep[inst]["me"], 10)
    return S.by_month(s).map(lambda v: (inst, 1))


def with_alt(tgt, alt_tgts):
    """Variante D: Cash-Monate gehen ins erste Ersatz-Asset, das selbst long ist."""
    out = {}
    for m, t in tgt.items():
        if t[0] is None:
            for a in alt_tgts:
                at = a.get(m)
                if at is not None and at[0] is not None and at[1] == 1:
                    t = at
                    break
        out[m] = t
    return pd.Series(out)


def sleeves_for(prep, insts, mode="sma10", shorts=(), alts=None):
    sl = []
    alt_t = [tgt_sma(prep, a) for a in (alts or [])]
    for k in insts:
        sh = k in shorts
        if mode == "sma10":
            parts = [(tgt_sma(prep, k, 10, sh), 1.0)]
        elif mode == "ens":   # C1
            parts = [(tgt_sma(prep, k, n, sh), 0.2) for n in (8, 9, 10, 11, 12)]
        elif mode == "conf":  # C2
            parts = [(tgt_sma(prep, k, 10, sh), 0.5), (tgt_tsmom(prep, k, sh), 0.5)]
        elif mode == "always":
            parts = [(tgt_always(prep, k), 1.0)]
        for j, (t, w) in enumerate(parts):
            if alts:
                t = with_alt(t, [a for a, an in zip(alt_t, alts) if an != k])
            sl.append(E.Sleeve(f"{k}#{j}", t, w))
    return sl


# ---------------------------------------------------------------- Monte Carlo
def mc_breach(eqs, days=252, paths=2000, block=20, seed=7):
    dr = eqs[eqs.index.dayofweek < 5].pct_change().dropna().values
    rng = np.random.default_rng(seed)
    n = len(dr)
    tr, dl = 0, 0
    for _ in range(paths):
        idx = np.concatenate([np.arange(s, s + block) % n for s in rng.integers(0, n, days // block + 1)])[:days]
        r = dr[idx]
        eq = np.cumprod(1 + r)
        peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
        tr += (eq <= peak * 0.93).any()
        dl += (r <= -0.03).any()
    return {"p_trailing7_pa": round(tr / paths, 4), "p_tag3_pa": round(dl / paths, 4)}


def evaluate(prep, sleeves, stop, sizing, costs=MITTEL, account=TTP, start=IS_START, end=IS_END, mc=False):
    r = E.run(prep, sleeves, stop, sizing, costs, account, start=start, end=end)
    m = E.metrics(r["equity"])
    t = r["trades"]
    m.update({"trades": int((t.reason != "rebalance").sum()) if len(t) else 0,
              "sl_exits": int((t.reason == "sl").sum()) if len(t) else 0,
              "skipped": r["skipped"]})
    if mc:
        m.update(mc_breach(r["equity"]))
    return m, r


# ---------------------------------------------------------------- Stopp-Varianten
def stop_grid(mae_params):
    g = {"A0_none": E.StopRule("none")}
    for p in (0.05, 0.08, 0.12, 0.20):
        g[f"A1_pct{int(p*100)}"] = E.StopRule("pct", p)
    for k in (2, 3, 4, 6):
        g[f"A2_atr{k}"] = E.StopRule("atr", k)
        g[f"A3_trail{k}"] = E.StopRule("trail", k)
    g["A4_dailysma_atr6"] = E.StopRule("atr", 6, daily_sma_exit=True)
    for q in (80, 90, 95):
        g[f"A5_mae_pct_q{q}"] = E.StopRule("mae_pct", mae_params[f"pct_q{q}"])
        g[f"A5_mae_atr_q{q}"] = E.StopRule("mae_atr", mae_params[f"atr_q{q}"])
    return g


# ---------------------------------------------------------------- Phase IS
def phase_is():
    prep = load_all()
    res = {"konvention": {"is": [IS_START, IS_END], "repair": REPAIR,
                          "konten": {"TTP": TTP.equity0, "EK": EK.equity0},
                          "kontrakte_annahme": E.CONTRACT, "min_lot": E.MIN_LOT}}

    # Schritt 0: Machbarkeit (Mindestlot-Nominal vs. erlaubtes Nominal auf EK)
    feas = {}
    for k in UNIV:
        d = prep[k]["df"]
        min_notional = E.MIN_LOT * E.CONTRACT[k] * (1 if k == "USDJPY" else d["ref"].iloc[-1])
        feas[k] = {"mindestlot_nominal": round(float(min_notional), 0)}
        for risk in (0.005, 0.01, 0.02):
            for slp in (0.05, 0.10, 0.20):
                feas[k][f"ek_r{risk*100:g}_sl{int(slp*100)}"] = bool(risk * EK.equity0 / slp >= min_notional)
    res["schritt0_machbarkeit"] = feas

    # Regressionstest
    r = E.run(prep, [E.Sleeve("SP500", tgt_sma(prep, "SP500"))], E.StopRule("none", sizing_pct_if_none=1.0),
              E.Sizing(risk_pct=1.0), E.Costs(0, 0), E.Account("x", 1.0, False), end=END)
    eq = r["equity"][r["trades"].entry_day.min():]
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    res["regression_sp500tr"] = {"cagr": round(((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100, 2),
                                 "maxdd": round(float((eq / eq.cummax() - 1).min() * 100), 2),
                                 "soll": "9.31 / -27.43"}

    # A5 + Mechanismus je Instrument (nur bis IS_END)
    mae_pct, mae_atr, mech, a5 = {}, {}, {}, {}
    for k in UNIV:
        rr = E.run(prep, [E.Sleeve(k, tgt_sma(prep, k))], E.StopRule("none"),
                   E.Sizing(0.005, rebalance=False), E.Costs(0, 0), E.Account("x", 1e6, False), end=IS_END)
        t = rr["trades"]
        d = prep[k]["df"]
        if t.empty:
            continue
        hold = (t.exit_day - t.entry_day).dt.days
        n_days = int(round(t.apply(lambda x: len(d.loc[x.entry_day:x.exit_day]) - 1, axis=1).mean()))
        rows = []
        for _, x in t.iterrows():
            seg = d.loc[x.entry_day:].iloc[1:n_days + 1]
            mae_n = max(0.0, (x.entry_px - seg["low"].min()) / x.entry_px) if len(seg) else 0.0
            atr0 = d.loc[x.entry_day, "atr"]
            rows.append({"jahr": x.entry_day.year, "mae_n": mae_n, "mae_trade": x.mae_pct,
                         "mae_n_atr": mae_n * x.entry_px / atr0 if atr0 > 0 else np.nan})
        m = pd.DataFrame(rows)
        per_year = m.groupby("jahr").agg(n=("mae_n", "size"), max_mae_n=("mae_n", "max"),
                                         q90_mae_n=("mae_n", lambda s: s.quantile(0.9)),
                                         max_mae_trade=("mae_trade", "max"))
        mae_pct[k] = {f"pct_q{q}": float(m.mae_n.quantile(q / 100)) for q in (80, 90, 95)}
        mae_atr[k] = {f"atr_q{q}": float(m.mae_n_atr.quantile(q / 100)) for q in (80, 90, 95)}
        a5[k] = {"trades": len(t), "haltedauer_handelstage_mittel": n_days,
                 "haltedauer_kalendertage_median": int(hold.median()),
                 "sl_pct": {q: round(v * 100, 2) for q, v in mae_pct[k].items()},
                 "sl_atr": {q: round(v, 2) for q, v in mae_atr[k].items()},
                 "je_jahr": (per_year * [1, 100, 100, 100]).round(2).reset_index().to_dict(orient="records")}
        # Mechanismus (C4): Folgemonat ueber/unter SMA10
        me = prep[k]["me"]
        mr = me.pct_change().shift(-1)
        _, sma = S.sma_signal(me, 10)
        above = me > sma
        sel = (me.index <= IS_END) & sma.notna()
        up, dn = mr[sel & above].dropna(), mr[sel & ~above].dropna()
        mech[k] = {"ret_ueber_pa": round(up.mean() * 1200, 2), "ret_unter_pa": round(dn.mean() * 1200, 2),
                   "vol_ueber": round(up.std() * np.sqrt(12) * 100, 2), "vol_unter": round(dn.std() * np.sqrt(12) * 100, 2),
                   "n_unter": int(len(dn)), "von": str(me.index[sma.notna()][0].date())}
        mech[k]["A_rendite"] = mech[k]["ret_unter_pa"] < mech[k]["ret_ueber_pa"]
        mech[k]["B_vola"] = mech[k]["vol_unter"] > mech[k]["vol_ueber"] * 1.1
    res["a5_mae"] = a5
    res["c4_mechanismus"] = mech
    mae_params = {f"pct_q{q}": {k: mae_pct[k][f"pct_q{q}"] for k in mae_pct} for q in (80, 90, 95)}
    mae_params.update({f"atr_q{q}": {k: mae_atr[k][f"atr_q{q}"] for k in mae_atr} for q in (80, 90, 95)})

    # Stufe 1: Stopp-Regel je Instrument (TTP, 0,5 %, mittel, Rebalancing)
    grid = stop_grid(mae_params)
    st1 = {}
    for name, rule in grid.items():
        st1[name] = {}
        for k in UNIV:
            m, _ = evaluate(prep, [E.Sleeve(k, tgt_sma(prep, k))], rule, E.Sizing(0.005), start=None)
            st1[name][k] = m
        st1[name]["median_ratio"] = float(np.nanmedian([st1[name][k].get("ratio", np.nan) for k in UNIV]))
    res["stufe1_stopps"] = st1
    best_stop = max(grid, key=lambda n: st1[n]["median_ratio"])
    res["stufe1_gewaehlt"] = best_stop
    stop = grid[best_stop]
    print("Stufe 1 gewaehlt:", best_stop, st1[best_stop]["median_ratio"])

    # Stufe 2: Portfolio-Varianten (IS 2001-2012)
    c4 = [k for k in UNIV if mech[k]["A_rendite"] or mech[k]["B_vola"]]
    shorts = [k for k in UNIV if D.INSTRUMENTS[k][1] in ("commodity", "fx") and mech[k]["A_rendite"]]
    res["c4_auswahl"], res["c5_short_erlaubt"] = c4, shorts
    base_sz = E.Sizing(0.005)
    variants = {
        "P_alle_sma10": (UNIV, "sma10", (), None, base_sz),
        "P_c4_sma10": (c4, "sma10", (), None, base_sz),
        "P_c4_ohne_rebal": (c4, "sma10", (), None, E.Sizing(0.005, rebalance=False)),
        "P_c4_C1_ensemble": (c4, "ens", (), None, base_sz),
        "P_c4_C2_tsmom": (c4, "conf", (), None, base_sz),
        "P_c4_C3_volfilter": (c4, "sma10", (), None, E.Sizing(0.005, vol_filter_half=True)),
        "P_c4_C5_short": (c4, "sma10", shorts, None, base_sz),
        "P_c4_D_gold": (c4, "sma10", (), ["GOLD"], base_sz),
        "P_c4_D_bond": (c4, "sma10", (), ["TNOTE10"], base_sz),
        "P_c4_D_gold_bond": (c4, "sma10", (), ["GOLD", "TNOTE10"], base_sz),
        "P_c4_B2_cap25": (c4, "sma10", (), None, E.Sizing(0.005, open_risk_cap=0.025)),
        "P_c4_B3_vt": (c4, "sma10", (), None, E.Sizing(0.005, vol_target=0.02)),
        "K_always_long": (c4, "always", (), None, base_sz),
    }
    st2 = {}
    for name, (insts, mode, sh, alts, sz) in variants.items():
        m, _ = evaluate(prep, sleeves_for(prep, insts, mode, sh, alts), stop, sz, mc=True)
        st2[name] = m
        print(name, m)
    res["stufe2_portfolio"] = st2

    # Stufe 3: Kombination der Bausteine, die einzeln gegen P_c4_sma10 halfen + Risiko-Stufen
    base = st2["P_c4_sma10"]["ratio"]
    helps = [n for n in ("P_c4_C1_ensemble", "P_c4_C2_tsmom", "P_c4_C3_volfilter", "P_c4_C5_short",
                         "P_c4_D_gold", "P_c4_D_bond", "P_c4_D_gold_bond", "P_c4_B2_cap25", "P_c4_B3_vt")
             if st2[n]["ratio"] > base]
    res["stufe3_helfer"] = helps
    mode = "ens" if "P_c4_C1_ensemble" in helps else ("conf" if "P_c4_C2_tsmom" in helps else "sma10")
    sh = shorts if "P_c4_C5_short" in helps else ()
    dvar = [n for n in ("P_c4_D_gold_bond", "P_c4_D_gold", "P_c4_D_bond") if n in helps]
    alts = {"P_c4_D_gold_bond": ["GOLD", "TNOTE10"], "P_c4_D_gold": ["GOLD"], "P_c4_D_bond": ["TNOTE10"]}[
        max(dvar, key=lambda n: st2[n]["ratio"])] if dvar else None
    st3 = {}
    for risk in (0.0025, 0.005, 0.01):
        sz = E.Sizing(risk, vol_filter_half="P_c4_C3_volfilter" in helps,
                      open_risk_cap=0.025 if "P_c4_B2_cap25" in helps else None,
                      vol_target=0.02 * risk / 0.005 if "P_c4_B3_vt" in helps else None)
        for label, insts in (("kombi", c4), ("kombi_alle", UNIV)):
            name = f"{label}_r{risk*100:g}"
            m, _ = evaluate(prep, sleeves_for(prep, insts, mode, sh, alts), stop, sz, mc=True)
            m["spec"] = {"insts": insts, "mode": mode, "shorts": list(sh), "alts": alts, "risk": risk,
                         "vol_filter_half": sz.vol_filter_half, "open_risk_cap": sz.open_risk_cap,
                         "vol_target": sz.vol_target}
            st3[name] = m
            print(name, {k: v for k, v in m.items() if k != "spec"})
    # einfache Basis ebenfalls als Kandidat (Gleichstand -> einfacher)
    for risk in (0.0025, 0.005, 0.01):
        name = f"basis_c4_r{risk*100:g}"
        m, _ = evaluate(prep, sleeves_for(prep, c4), stop, E.Sizing(risk), mc=True)
        m["spec"] = {"insts": c4, "mode": "sma10", "shorts": [], "alts": None, "risk": risk,
                     "vol_filter_half": False, "open_risk_cap": None, "vol_target": None}
        st3[name] = m
    res["stufe3_kandidaten"] = st3

    ok = {n: m for n, m in st3.items() if m["p_trailing7_pa"] < 0.10 and m["worst_day_pct"] > -3.0 and not np.isnan(m["ratio"])}
    ranked = sorted(ok, key=lambda n: (-round(ok[n]["ratio"], 2), 0 if n.startswith("basis") else 1))
    res["finalisten"] = ranked[:3]
    res["finalisten_stopp"] = best_stop
    res["mae_params"] = mae_params
    with open(OUT_IS, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=float)
    print("FINALISTEN:", res["finalisten"])


# ---------------------------------------------------------------- Phase OOS
def phase_oos():
    with open(OUT_IS, encoding="utf-8") as f:
        isr = json.load(f)
    prep = load_all(with_btc=True)
    grid = stop_grid(isr["mae_params"])
    stop = grid[isr["finalisten_stopp"]]
    res = {"stopp": isr["finalisten_stopp"], "fenster": [OOS_START, END], "finalisten": {}}

    def sz_of(sp, risk=None):
        return E.Sizing(risk or sp["risk"], open_risk_cap=sp["open_risk_cap"],
                        vol_target=sp["vol_target"], vol_filter_half=sp["vol_filter_half"])

    for name in isr["finalisten"]:
        sp = isr["stufe3_kandidaten"][name]["spec"]
        sl = sleeves_for(prep, sp["insts"], sp["mode"], sp["shorts"], sp["alts"])
        out = {}
        for tier, c in COST_TIERS.items():
            m, r = evaluate(prep, sl, stop, sz_of(sp), costs=c, start=OOS_START, end=END, mc=(tier == "mittel"))
            out[f"ttp_{tier}"] = m
            if tier == "mittel":
                eq_main, tr_main = r["equity"], r["trades"]
        # Kontrolle: gleiche Instrumente/Stopps/Sizing, aber immer long
        m, _ = evaluate(prep, sleeves_for(prep, sp["insts"], "always"), stop, sz_of(sp), start=OOS_START, end=END, mc=True)
        out["kontrolle_immer_long"] = m
        # Lag +1 Tag
        r = E.run(prep, sl, stop, sz_of(sp), MITTEL, TTP, start=OOS_START, end=END, lag_days=1)
        out["lag_1tag"] = E.metrics(r["equity"])
        # EK-Konto (Mindestlot)
        m, r_ek = evaluate(prep, sl, stop, sz_of(sp), account=EK, start=OOS_START, end=END)
        out["ek"] = m
        # Jahre
        e = eq_main[eq_main.index.dayofweek < 5]
        out["jahre_pct"] = {int(y): round(float(v) * 100, 2) for y, v in
                            e.groupby(e.index.year).last().pct_change().fillna(e.groupby(e.index.year).last().iloc[0] / e.iloc[0] - 1).items()}
        # Zufall: Monatsziele je Sleeve mischen (gleiche Zeit im Markt)
        rng = np.random.default_rng(42)
        dds, ratios = [], []
        n_rand = int(os.environ.get("FABER_RAND", "300"))
        for _ in range(n_rand):
            rs = []
            for s in sl:
                t = s.targets[(s.targets.index >= pd.Period("2012-12")) & (s.targets.index <= pd.Period("2026-09"))]
                vals = list(t.values)
                perm = [vals[i] for i in rng.permutation(len(vals))]
                tt = s.targets.copy()
                tt.loc[t.index] = pd.Series(perm, index=t.index, dtype=object)
                rs.append(E.Sleeve(s.name, tt, s.weight))
            rr = E.run(prep, rs, stop, sz_of(sp), MITTEL, TTP, start=OOS_START, end=END)
            mm = E.metrics(rr["equity"])
            dds.append(mm["maxdd_pct"]); ratios.append(mm["ratio"])
        out["zufall"] = {"laeufe": n_rand, "seed": 42,
                         "anteil_dd_gleich_oder_kleiner": round(float(np.mean(np.array(dds) >= out["ttp_mittel"]["maxdd_pct"])), 4),
                         "anteil_ratio_gleich_oder_besser": round(float(np.mean(np.array(ratios) >= out["ttp_mittel"]["ratio"])), 4),
                         "median_dd": float(np.median(dds)), "median_ratio": float(np.nanmedian(ratios))}
        # Korrelation zu bestehenden Beinen (taegliche P&L)
        try:
            fk = pd.read_csv(os.path.join(ROOT, "portfolio_construction/results/fk_trades_2019_2026_live.csv"),
                             parse_dates=["exit_time"])
            leg_daily = fk.groupby(fk.exit_time.dt.normalize()).r.sum()
            ft = e.pct_change().reindex(leg_daily.index).dropna()
            out["korrelation_fk_beine_taeglich"] = round(float(ft.corr(leg_daily.reindex(ft.index))), 3)
        except Exception as ex:  # pragma: no cover
            out["korrelation_fk_beine_taeglich"] = str(ex)
        # A5 haelt? (nur wenn A5-Stopp gewaehlt): SL-Quote je Jahr vs. Erwartung
        if isr["finalisten_stopp"].startswith("A5"):
            q = int(isr["finalisten_stopp"][-2:])
            t = tr_main[tr_main.reason != "rebalance"]
            out["a5_sl_quote_je_jahr"] = {int(y): round(float(g.eq("sl").mean()), 3)
                                         for y, g in t.groupby(t.exit_day.dt.year).reason}
            out["a5_erwartet"] = round(1 - q / 100, 2)
        res["finalisten"][name] = out
        print(name, json.dumps({k: v for k, v in out.items() if k not in ("jahre_pct",)}, default=float)[:1500])

    # D mit BTC: nur OOS, markiert (keine Auswahl moeglich)
    sp = isr["stufe3_kandidaten"][isr["finalisten"][0]]["spec"]
    for alts in (["BTC"], ["GOLD", "BTC"]):
        m, _ = evaluate(prep, sleeves_for(prep, sp["insts"], sp["mode"], sp["shorts"], alts), stop, sz_of(sp),
                        start=OOS_START, end=END, mc=True)
        res[f"D_nur_oos_{'_'.join(alts)}"] = m
        print("D", alts, m)
    # Gegencheck letzter Monat je Instrument
    chk = {}
    for k in UNIV + ["BTC"]:
        me = prep[k]["me"]
        s, sma = S.sma_signal(me, 10)
        chk[k] = {"monat": str(me.index[-1].to_period("M")), "schluss": round(float(me.iloc[-1]), 4),
                  "sma10": round(float(sma.iloc[-1]), 4), "signal": "long" if s.iloc[-1] == 1 else "cash"}
    res["gegencheck"] = chk
    with open(OUT_OOS, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=float)


if __name__ == "__main__":
    {"is": phase_is, "oos": phase_oos}[sys.argv[1]]()
