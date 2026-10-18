"""Gold ASB: Filter aus Gold-Intraday-Papers, Auswahl 2016-2026, Blindtest 2010-2015.

Nutzerauftrag 2026-10-18 (Plan ~/.claude/plans/stateful-popping-lampson.md, Hypothesen
vom Nutzer vorab bestaetigt). OOS und Tresor der IS-only-Konfiguration sind seit dem
15.10. geoeffnet (Lock gold_asb_is_reopt_20261015) -- deshalb:

  Auswahl   02.11.2016 .. 30.09.2026  (alles schon Gesehene, = "IS" dieses Locks)
  Blindtest 01.01.2010 .. 31.12.2015  (nie fuer Gold ASB benutzt, Lock-Stufe "blind")
  OOS       01.10.2026 .. 31.03.2027  (= Forward-Test, erst am Stichtag oeffnen)

BASIS = eingefrorene IS-only-Konfiguration (Stop 2,0x, Storno 02:30, Exit 11:00,
ADX 15, kein SMA, Silber 5T, Liquiditaet q0,5, beide Richtungen).

HYPOTHESEN (vorab fest, 9 Varianten, alle gezaehlt):
  H1 Range-Kompression (Crabel NR, Feld 4): nur Range / Median der 20 Vor-Ranges <= 0,8 / 1,0 / 1,2
  H2 NFP-Tage (Sobti 2024/25, Feld 5):      an NFP-Tagen nicht handeln / vor 08:30 schliessen
     (FOMC gestrichen: Entscheidung 14:00 NY liegt nach dem Exit, kein Effekt moeglich)
  H3 PM-Fix 10:00 NY (Caminschi & Heaney 2014, CBS 2019, Feld 1): Exit 09:55 alle / nur Longs
  H4 Asien-Drift 21:00->01:00 (Wei 2026, Jin et al. 2018, Feld 5): in / gegen Ausbruchsrichtung

VOR DER AUSWAHL FESTGELEGT (18.10., nach --stage quality, ohne Strategie-Zahlen vor 2016):
  Datenqualitaet 2009-2015 ok (Asien-Fenster vollstaendig, Range-Breite wie 2016+), kein Jahr
  ausgeschlossen. Silber im Blindtest durchgehend Ersatz SI=F (siehe silver_proxy); Messlatte
  fuer die Basis ist deren Ersatz-Silber-Wert 2016-2026 (Ø +0,229 R), nicht +0,271.

AUSWAHLREGEL (vor dem Lauf festgelegt): Variante ist zulaessig, wenn Ø R je Trade in
mind. 2 von 3 Teilzeitraeumen (2016-19, 2020-22, 2023-26) ueber der Basis liegt und
mind. 60 % der Basis-Trades bleiben. Gewinner = hoechster t-Wert unter den zulaessigen,
und nur wenn er den t-Wert der Basis schlaegt; sonst wird KEIN Filter uebernommen.

  python scripts/research_gold_asb_paper_filters.py --stage quality   # nur Datenqualitaet vor 2016
  python scripts/research_gold_asb_paper_filters.py --stage select    # Auswahl + freeze (kein Blick vor 2016)
  python scripts/research_gold_asb_paper_filters.py --stage blind     # Blindtest einmal oeffnen
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import research_gold_asb_is_only_reopt as ro  # noqa: E402
from asian_range_breakout.filters import attach_series_change, attach_series_level, rolling_liquidity_threshold  # noqa: E402
from research_gold_asb_execution_costs import CACHE, load_ohlc  # noqa: E402
from research_gold_asb_optimization import TTP_BPS, day_table, simulate  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "gold_asb_paper_filters_20261018"
SEL_START, SEL_END, FWD_END = "2016-11-02", "2026-09-30", "2027-03-31"
BLIND_START, BLIND_END = "2010-01-01", "2015-12-31"
RES = ROOT / "asian_range_breakout" / "results"
NY = "America/New_York"
SUBS = (("2016-19", "2016-01-01", "2019-12-31"), ("2020-22", "2020-01-01", "2022-12-31"),
        ("2023-26", "2023-01-01", "2026-12-31"))
BASE = json.loads((RES / "is_reopt_selection.json").read_text(encoding="utf-8"))["winner"]
VARIANTS = [("H1 Range <= 0,8x Median", "h1", 0.8), ("H1 Range <= 1,0x Median", "h1", 1.0),
            ("H1 Range <= 1,2x Median", "h1", 1.2),
            ("H2 NFP-Tage aussetzen", "h2_skip", None), ("H2 NFP-Tage vor 08:30 schliessen", "h2_exit", None),
            ("H3 Exit 09:55 (vor PM-Fix)", "h3_all", None), ("H3 nur Longs 09:55", "h3_long", None),
            ("H4 Asien-Drift in Richtung", "h4_with", None), ("H4 Asien-Drift gegen Richtung", "h4_against", None)]


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(SEL_START, SEL_END, FWD_END)
    lk.register_blind(BLIND_START, BLIND_END)
    return lk


# ------------------------------------------------------------------ Daten
def load_pre2016():
    from bond_yield_indicator.friction import corwin_schultz_spread
    m15 = load_ohlc("GOLD_M15_2009-01-01_2016-01-01.parquet")
    m5 = load_ohlc("GOLD_M5_2009-01-01_2016-01-01.parquet")
    d1 = pd.read_parquet(CACHE / "GOLD_D1_2009-01-01_2016-01-01.parquet")
    friction = corwin_schultz_spread(d1["High"], d1["Low"])
    friction.index = friction.index.tz_localize(None)
    dc = m15["close"].tz_localize(None).resample("D").last().dropna()
    return m15, m5, dc, silver_proxy(dc.index), friction


def silver_proxy(cal: pd.DatetimeIndex) -> pd.Series:
    """Dukascopy hat XAG/USD erst ab 07/2014. Ersatz (vorab festgelegt, 18.10.): COMEX-Silber-
    Futures (yfinance SI=F), Schluss auf den Gold-Tageskalender vorgetragen. Probe 2016-2026:
    5-Tage-Richtung zu 92,9 % gleich (98,1 % bei Bewegung > 1 %); Basis damit 305 statt 325
    Trades, Ø +0,229 statt +0,271 R -> Messlatte im Blindtest ist +0,229."""
    si = pd.read_parquet(CACHE / "SILVER_SIF_D1_2008-06-01_2026-10-01.parquet")["Close"]
    return si.reindex(cal.union(si.index)).ffill().reindex(cal)


def build_days(m15, m5, dc, dcs, fr):
    """Wie ro.load_days, aber mit uebergebenen Daten (Blindtest rechnet seine Merkmale nur
    aus 2009-2015, kausal, unabhaengig von 2016+)."""
    days = day_table(m15, m5, dc, dcs, fr)
    tmp = days[["window_end"]].assign(entry_time=days["window_end"])
    for w in (100, 200):
        tmp = attach_series_level(tmp, dc.rolling(w).mean(), f"sma{w}")
    for w in (3, 5, 10):
        tmp = attach_series_change(tmp, dcs, f"silver{w}", window=w)
    for q in ro.LIQ[1:]:
        tmp = attach_series_level(tmp, rolling_liquidity_threshold(fr, q, 250), f"thr{q:.3f}")
    days = days.merge(tmp.drop(columns="entry_time"), on="window_end", how="left")
    days = days.dropna(subset=["sma100", "sma200", "silver3", "silver10"]).reset_index(drop=True)
    return days.set_index("window_end", drop=False), m5


def add_features(days, m5):
    """H1: Range-Breite / Median der 20 vorigen Ranges. H4: Asien-Drift 21:00->01:00 (Open der
    ersten, Close der letzten M5-Bar im Fenster). Alles bis 01:00 bekannt, kein Lookahead."""
    width = (days["r_hi"] - days["r_lo"])
    days = days.assign(range_ratio=(width / width.shift(1).rolling(20, min_periods=20).median()).to_numpy())
    idx, o, c = m5.index, m5["open"].to_numpy(), m5["close"].to_numpy()
    drift = []
    for we in days["window_end"]:
        a, b = idx.searchsorted(we - pd.Timedelta(hours=4)), idx.searchsorted(we)
        drift.append(c[b - 1] - o[a] if b > a else np.nan)
    days["asia_drift"] = drift
    return days


def nfp_dates(start: int, end: int) -> set:
    """BLS-Regel: dritter Freitag nach der Woche (So-Sa), die den 12. enthaelt."""
    out = set()
    for y in range(start, end + 1):
        for mth in range(1, 13):
            d12 = pd.Timestamp(y, mth, 12)
            week_sat = d12 + pd.Timedelta(days=(5 - d12.weekday()) % 7)   # Samstag der 12.-Woche
            out.add((week_sat + pd.Timedelta(days=6 + 14)).date())         # Freitag, 3 Wochen danach
    return out


def trades_for(days, m5, exit_time=None):
    t = simulate(days.reset_index(drop=True), m5, cancel=BASE["cancel"], stop_frac=BASE["stop"],
                 exit_time=exit_time or ro.EXITS[BASE["exit"]], bps=TTP_BPS)
    f = days.set_index("window_end")
    for col in ("gold_close_prior", "sma100", "sma200", "silver3", "silver5", "silver10", "friction_prior",
                *[f"thr{q:.3f}" for q in ro.LIQ[1:]], "range_ratio", "asia_drift"):
        t[col] = f[col].reindex(t["window_end"]).to_numpy()
    t = t[ro.mask(t, BASE)].sort_values("window_end").reset_index(drop=True)
    return t


def variant_series(days, m5, nfp) -> dict:
    """R-Serie je Variante (Index = window_end NY). Exit-Varianten rechnen eigene Simulationen."""
    base = trades_for(days, m5)
    ex = {"09:55": trades_for(days, m5, "09:55"), "08:25": trades_for(days, m5, "08:25")}
    to_s = lambda t: pd.Series(t["R"].to_numpy(), index=pd.DatetimeIndex(t["window_end"]))  # noqa: E731
    is_nfp = base["window_end"].dt.date.isin(nfp).to_numpy()
    out = {"Basis": to_s(base)}
    for name, kind, k in VARIANTS:
        if kind == "h1":
            out[name] = to_s(base[base["range_ratio"].to_numpy() <= k])
        elif kind == "h2_skip":
            out[name] = to_s(base[~is_nfp])
        elif kind == "h2_exit":
            early = to_s(ex["08:25"]).reindex(out["Basis"].index)
            s = out["Basis"].copy()
            s[is_nfp] = early[is_nfp].fillna(s[is_nfp])   # Trade, der erst nach 08:25 startet, bleibt
            out[name] = s
        elif kind in ("h3_all", "h3_long"):
            e = to_s(ex["09:55"]).reindex(out["Basis"].index)
            s = out["Basis"].copy()
            sel = np.ones(len(s), bool) if kind == "h3_all" else (base["dir"].to_numpy() == 1)
            s[sel] = e[sel].fillna(s[sel])
            out[name] = s
        else:
            same = np.sign(base["asia_drift"].to_numpy()) == base["dir"].to_numpy()
            out[name] = to_s(base[same if kind == "h4_with" else ~same])
    return out


def metrics(r: pd.Series) -> dict:
    if len(r) < 3:
        return {"n": len(r)}
    loss = -r[r < 0].sum()
    return {"n": len(r), "avg": r.mean(), "std": r.std(ddof=1), "t": r.mean() / r.std(ddof=1) * np.sqrt(len(r)),
            "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "sum": r.sum(),
            "dd": (r.cumsum() - r.cumsum().cummax().clip(lower=0)).min(), "win": (r > 0).mean(),
            "skew": r.skew(), "kurt": r.kurt() + 3}


def sub(r, a, b):
    return r[(r.index >= pd.Timestamp(a, tz=NY)) & (r.index < pd.Timestamp(b, tz=NY) + pd.Timedelta(days=1))]


# ------------------------------------------------------------------ Stufen
def stage_quality() -> int:
    """Nur Datenqualitaet, keine Strategie: Bars je Jahr, leere Asien-Fenster, Range-Breite, Spread."""
    m15, m5, dc, dcs, fr = load_pre2016()
    m5_new = load_ohlc("GOLD_M5_2016-01-01_2026-10-01.parquet")
    rows = []
    for src, df in (("vor 2016", m5), ("ab 2016", m5_new[m5_new.index < pd.Timestamp("2020-01-01", tz=NY)])):
        for y, g in df.groupby(df.index.year):
            wd = g[g.index.dayofweek < 5]
            asia = g[(g.index.hour >= 21) | (g.index.hour < 1)]
            per_win = asia.groupby((asia.index - pd.Timedelta(hours=3)).date).size()
            full = per_win[per_win >= 24]
            hl = asia.groupby((asia.index - pd.Timedelta(hours=3)).date).apply(
                lambda x: (x["high"].max() - x["low"].min()) / x["close"].iloc[-1] * 1e4)
            flat = (g["high"] == g["low"]).mean()
            rows.append({"quelle": src, "jahr": y, "m5_bars": len(g), "bars_je_werktag": len(wd) / max(wd.index.normalize().nunique(), 1),
                         "asien_fenster": len(per_win), "davon_voll_(>=24)": len(full),
                         "anteil_voll_%": 100 * len(full) / max(len(per_win), 1),
                         "asien_range_bps_median": hl.median(), "flache_bars_%": 100 * flat})
    q = pd.DataFrame(rows)
    fr_y = fr.groupby(fr.index.year).median().rename("cs_spread_median")
    q.to_csv(RES / "paper_filters_data_quality.csv", index=False)
    pd.set_option("display.width", 220)
    print(q.round(2).to_string(index=False))
    print("\nCorwin-Schultz-Spread (Median je Jahr, vor 2016):")
    print(fr_y.round(5).to_string())
    return 0


def stage_select() -> int:
    lk = lock()
    days, m5 = ro.load_days()
    days = days[days.index < pd.Timestamp(SEL_END, tz=days.index.tz) + pd.Timedelta(days=1)]
    days = add_features(days, m5)
    S = {k: lk.is_only(v) for k, v in variant_series(days, m5, nfp_dates(2016, 2026)).items()}
    b = metrics(S["Basis"])
    assert b["n"] == 325 and abs(b["sum"] - 88.23) < 0.01, f"Basis weicht ab: {b['n']} / {b['sum']:.2f}"
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    if st["trials"] == 0:
        lk.log_trials(len(VARIANTS), "9 Paper-Varianten, vorab festgelegt (H1 3, H2 2, H3 2, H4 2)")
    rows = []
    for name, r in S.items():
        m = metrics(r)
        subs = {lab: metrics(sub(r, a, e)).get("avg", np.nan) for lab, a, e in SUBS}
        bsubs = {lab: metrics(sub(S["Basis"], a, e))["avg"] for lab, a, e in SUBS}
        better = sum(subs[k] > bsubs[k] for k in subs)
        ok = name != "Basis" and better >= 2 and m["n"] >= 0.6 * b["n"]
        rows.append({"variante": name, **{k: m[k] for k in ("n", "avg", "t", "pf", "sum", "dd", "win")},
                     **{f"avg_{k}": v for k, v in subs.items()}, "besser_in": better, "zulaessig": ok})
    rep = pd.DataFrame(rows)
    cand = rep[rep["zulaessig"] & (rep["t"] > b["t"])].sort_values("t", ascending=False)
    winner = cand.iloc[0]["variante"] if len(cand) else "Basis"
    srs = [metrics(S[v])["avg"] / metrics(S[v])["std"] for v in S if v != "Basis"]
    w = metrics(S[winner])
    dsr = deflated_sharpe(w["avg"] / w["std"], w["n"], len(VARIANTS), w["skew"], w["kurt"], float(np.var(srs)))
    h = lk.freeze({"base": BASE, "filter": winner})
    rep.to_csv(RES / "paper_filters_selection.csv", index=False)
    (RES / "paper_filters_winner.json").write_text(json.dumps(
        {"winner": winner, "hash": h, "dsr": dsr, "n_trials": len(VARIANTS), "sr_var": float(np.var(srs))},
        indent=2, ensure_ascii=False), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))
    print(f"\nGewinner: {winner}  | Deflated Sharpe (9 Versuche): {dsr:.3f}  | eingefroren {h[:12]}")
    return 0


def stage_blind() -> int:
    lk = lock()
    win = json.loads((RES / "paper_filters_winner.json").read_text(encoding="utf-8"))
    print("Blindtest geoeffnet:", lk.unseal("blind", win["hash"]))
    days, m5 = build_days(*load_pre2016())
    days = add_features(days, m5)
    # Nur Basis und eingefrorener Gewinner -- die uebrigen Varianten bleiben ungesehen (sonst
    # waere der Blindtest eine zweite Auswahlrunde).
    keep = {"Basis", win["winner"]}
    S = {k: lk.stage_slice(v, "blind") for k, v in variant_series(days, m5, nfp_dates(2009, 2015)).items() if k in keep}
    rows = []
    for name, r in S.items():
        m = metrics(r)
        yrs = r.groupby(r.index.year).sum()
        rows.append({"variante": name, "gewinner": name == win["winner"], **{k: m.get(k) for k in ("n", "avg", "t", "pf", "sum", "dd", "win")},
                     "jahre_pos": int((yrs > 0).sum()), "jahre": len(yrs), "erster_trade": r.index.min()})
    rep = pd.DataFrame(rows)
    rep.to_csv(RES / "paper_filters_blind.csv", index=False)
    yr = pd.DataFrame({k: v.groupby(v.index.year).sum() for k, v in S.items()})
    yr.to_csv(RES / "paper_filters_blind_years.csv")
    pd.concat({k: v for k, v in S.items()}, names=["variante", "time"]).rename("r").to_csv(RES / "paper_filters_blind_trades.csv")
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))
    print("\nJahre (Summe R):")
    print(yr.round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "select"
    sys.exit({"quality": stage_quality, "select": stage_select, "blind": stage_blind}[stage]())
