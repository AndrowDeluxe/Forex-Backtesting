"""Makro-Filter aus dem C2-Test (F1-F4) einzeln auf ORB und CTNL (Nutzerauftrag 10./11.11.2026).

    python -m skill_test.makro_filter_orb_ctnl            # Trades aus Cache, sonst neu simulieren
    python -m skill_test.makro_filter_orb_ctnl --neu      # Trades neu simulieren (dauert)

Trades: Live-Konfiguration TTP (scripts/research_fk_gesamtportfolio_2026 orb_trades/ctnl_trades,
jetzt mit Richtung). IS/OOS laut den Skill-Filter-Sperren vom 28.10. (ORB IS 2019-22, OOS bis 09/2025;
CTNL IS 2019-07/2024, OOS bis 09/2026). OOS ist seit 10.11. frei. ORB und CTNL laufen live:
Ergebnis ist Diagnose, eine Live-Aenderung braucht Forward-Daten (Overfitting-Sperre Punkt 5).

Filter je Trade, nur Daten bis zum Vortag:
  F1 Zins-Momentum  US-2y faellt ueber 20 T -> long (Gold-Regel aus fusion_lab.filters.zins_fx)
  F2 Carry          US-Realzins (10y - Breakeven) faellt ueber 20 T -> long
  F3 Regime-Matrix  Gold: Gold-Zeile; Indizes: Zeile „Industrie“ (Goldilocks/Reflation long,
                    Inflation/Deflation short), Regime 5 T bestaetigt
  F4 Regimekarte    Landi g×π, Linse signs; Richtung je Regime aus der IS-Tagesrendite des Markts
Indizes wie Gold bzw. Industrie zu behandeln ist eine Annahme (Matrix hat keine Aktienzeile).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from fusion_lab.filters.zins_fx import ZinsFxFilter  # noqa: E402
from fusion_lab.filters.zinskurve_regime import confirmed, regime_series  # noqa: E402
from fusion_lab.macro_regime.model import daily_labels  # noqa: E402
from htf_daily_trade.backtest_r import stats  # noqa: E402
from htf_daily_trade.macro import REGIME_DIR  # noqa: E402

CACHE = ROOT / "skill_test" / "results" / "orb_ctnl_ttp_mit_richtung.csv"
OUT = ROOT / "skill_test" / "results" / "makro_filter_orb_ctnl.csv"
FILTERS = ("F1", "F2", "F3", "F4")
NAMES = {"F1": "Zins-Momentum", "F2": "Carry/Realzins", "F3": "Regime-Matrix", "F4": "Regimekarte"}
SPLITS = {"orb": ("2019-01-01", "2022-12-31", "2025-09-30"), "ctnl": ("2019-01-01", "2024-07-31", "2026-09-30")}
MARKT = {"orb_sp500": "SPX", "orb_nasdaq": "NDX", "orb_us30": "DJI", "ctnl_reversal": "Gold"}
MATRIX_ZEILE = {"SPX": "industrie", "NDX": "industrie", "DJI": "industrie", "Gold": "gold"}


def trades(neu: bool) -> pd.DataFrame:
    if CACHE.exists() and not neu:
        return pd.read_csv(CACHE, parse_dates=["entry_time", "exit_time"])
    import research_live_legs as rl
    rl._chunked_dukascopy_fetch()
    rl.END = (pd.Timestamp.today().normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    rl._set_broker("ttp")
    t = pd.concat([rl.fk.orb_trades(), rl.fk.ctnl_trades()], ignore_index=True).sort_values("entry_time")
    t.to_csv(CACHE, index=False)
    return t


def preise() -> pd.DataFrame:
    a = pd.read_parquet(ROOT / "data_cache/macro_regime/yf_prices.parquet")
    b = pd.read_parquet(ROOT / "data_cache/macro_regime/yf_prices_extra.parquet")
    return a.join(b, how="outer")[list(set(MARKT.values()))]


def _prev(s: pd.Series, date):
    i = s.index.searchsorted(pd.Timestamp(date), side="left") - 1
    return None if i < 0 else s.iloc[i]


def label(t: pd.DataFrame) -> pd.DataFrame:
    zf = ZinsFxFilter(20)
    regime = confirmed(regime_series(20), 5)
    px = preise()
    labels = daily_labels(pd.bdate_range("2015-01-01", pd.Timestamp.today()))
    lens = labels["signs"]
    # F4: Richtung je Markt und Regime aus der Tagesrendite im IS der jeweiligen Strategie
    ldir = {}
    for leg, m in MARKT.items():
        strat = "ctnl" if leg.startswith("ctnl") else "orb"
        s, e, _ = SPLITS[strat]
        ret = np.log(px[m].dropna()).diff().loc[s:e]
        df = pd.DataFrame({"ret": ret}).join(lens, how="inner")
        for reg, mu in df.groupby("signs")["ret"].mean().items():
            ldir[(m, reg)] = int(np.sign(mu))
    rows = []
    for _, x in t.iterrows():
        d = pd.Timestamp(x["entry_time"]).normalize()
        m, side = MARKT[x["leg"]], "long" if x["direction"] > 0 else "short"
        r = _prev(regime, d)
        pref = None if r is None or pd.isna(r) else REGIME_DIR[r][MATRIX_ZEILE[m]]
        reg = _prev(lens, d)
        dirs = {"F1": zf.momentum_dir("XAUUSD", d), "F2": zf.carry_dir("XAUUSD", d),
                "F3": 0 if pref is None else (1 if pref == "long" else -1),
                "F4": ldir.get((m, reg), 0) if reg is not None else 0}
        rows.append({"markt": m, "seite": side, **{k: ZinsFxFilter.state(v, side) for k, v in dirs.items()}})
    return pd.concat([t.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def fmt(r: pd.Series) -> str:
    st = stats(r)
    if st.get("n", 0) < 2:
        return f"n {st.get('n', 0):>4}"
    return f"n {st['n']:>4} Ø {st['mean_r']:+.3f} t {st['t']:+.2f}"


def auswertung(t: pd.DataFrame, strat: str) -> None:
    s, e, o = SPLITS[strat]
    legs = [l for l in MARKT if l.startswith(strat)]
    x = t[t["leg"].isin(legs)]
    for stufe, a, b in (("IS", s, e), ("OOS", pd.Timestamp(e) + pd.Timedelta(days=1), o)):
        y = x[(x["entry_time"] >= pd.Timestamp(a)) & (x["entry_time"] <= pd.Timestamp(b) + pd.Timedelta(days=1))]
        print(f"\n== {strat.upper()} {stufe} {pd.Timestamp(a).date()}..{pd.Timestamp(b).date()}  Basis: {fmt(y['r'])}")
        for f in FILTERS:
            mit, geg = y.loc[y[f] == "dafuer", "r"], y.loc[y[f] == "dagegen", "r"]
            ohne_geg = y.loc[y[f] != "dagegen", "r"]
            wirkt = len(mit) > 1 and len(geg) > 1 and mit.mean() > y["r"].mean() > geg.mean()
            print(f"  {f} {NAMES[f]:<15} dafuer {fmt(mit)} | dagegen {fmt(geg)} | gefiltert {fmt(ohne_geg)}"
                  f" | {'WIRKT' if wirkt else '-'}")
        if strat == "orb":
            for leg in legs:
                z = y[y["leg"] == leg]
                print(f"    {leg:<12} Basis {fmt(z['r'])} | " + " | ".join(
                    f"{f} gefiltert {fmt(z.loc[z[f] != 'dagegen', 'r'])}" for f in FILTERS))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--neu", action="store_true")
    t = trades(ap.parse_args().neu)
    t = label(t[t["leg"].isin(MARKT)].copy())
    t.to_csv(OUT, index=False)
    print("Long-Anteil je Bein:", t.groupby("leg")["seite"].apply(lambda s: round((s == "long").mean(), 2)).to_dict())
    for strat in ("orb", "ctnl"):
        auswertung(t, strat)


if __name__ == "__main__":
    main()
