"""2b: Kontext-Skills als Filter auf IS (Plan 28.10.2026). Jede Variante = ein gezaehlter Versuch.

Schwellen sind die Standardwerte der Skills, vorab festgelegt, nicht getunt. Kontext immer
vom letzten Handelstag VOR dem Entry-Tag (kein Lookahead).

Aufruf: python skill_test/filters.py orb|ctnl
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
from research_lock import deflated_sharpe  # noqa: E402

CACHE = c.RESULTS / "cache"
INDEX_OF_LEG = {"orb_sp500": "SPX", "orb_nasdaq": "NDX", "orb_us30": "DJI", "ctnl_reversal": "Gold"}


# --- Kontextdaten --------------------------------------------------------------
def closes() -> pd.DataFrame:
    d = c.ROOT / "data_cache" / "macro_regime"
    px = pd.read_parquet(d / "yf_prices.parquet").join(pd.read_parquet(d / "yf_prices_extra.parquet"))
    px.index = pd.to_datetime(px.index).normalize()
    return px


def prior_value(series: pd.Series, day: pd.Timestamp):
    s = series.dropna()
    i = s.index.searchsorted(day) - 1
    return s.iloc[i] if i >= 0 else np.nan


def breadth_scores(days: pd.DatetimeIndex) -> pd.Series:
    """market-breadth-analyzer Composite je Stichtag, OHNE cycle_position (Is_Peak/Is_Trough sind
    nachtraeglich bestimmt) und OHNE historical_percentile (Gesamt-Historie) -- beide als nicht
    verfuegbar markiert, der Skill-Scorer verteilt deren Gewicht um."""
    sd = c.SKILLS / "market-breadth-analyzer" / "scripts"
    sys.path.insert(0, str(sd))
    import csv_client  # noqa: E402
    from calculators.bearish_signal_calculator import calculate_bearish_signal
    from calculators.divergence_calculator import calculate_divergence
    from calculators.ma_crossover_calculator import calculate_ma_crossover
    from calculators.trend_level_calculator import calculate_breadth_level_trend
    from scorer import calculate_composite_score

    path = CACHE / "market_breadth_data.csv"
    if not path.exists():
        import requests
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(requests.get(csv_client.DEFAULT_DETAIL_URL, timeout=60).text, encoding="utf-8")
    _, raw = csv_client._read_csv(path.read_text(encoding="utf-8"), "market_breadth_data.csv")
    rows = sorted((csv_client._parse_detail_row(r) for r in raw), key=lambda r: r["Date"])
    dates = pd.to_datetime([r["Date"] for r in rows])
    out = {}
    for day in days:
        k = dates.searchsorted(day)  # Zeilen strikt vor dem Entry-Tag
        if k < 220:
            continue
        sub = rows[:k]
        with redirect_stdout(io.StringIO()):
            comps = {
                "breadth_level_trend": calculate_breadth_level_trend(sub)["score"],
                "ma_crossover": calculate_ma_crossover(sub)["score"],
                "cycle_position": 50,
                "bearish_signal": calculate_bearish_signal(sub)["score"],
                "historical_percentile": 50,
                "divergence": calculate_divergence(sub)["score"],
            }
            avail = {k2: k2 not in ("cycle_position", "historical_percentile") for k2 in comps}
            out[day] = calculate_composite_score(comps, avail)["composite_score"]
    return pd.Series(out)


def ibd_risk(days: pd.DatetimeIndex) -> pd.Series:
    """ibd-distribution-day-monitor: Gesamtrisiko (QQQ + SPY) zum letzten Handelstag vor dem Entry."""
    sd = c.SKILLS / "ibd-distribution-day-monitor" / "scripts"
    sys.path.insert(0, str(sd))
    import ibd_monitor as m  # noqa: E402
    from risk_classifier import combine_index_risks

    cfg = m.load_config(None)
    rule, thr = m._build_rule(cfg), m._build_thresholds(cfg)
    hist = {}
    for sym in ("QQQ", "SPY"):
        p = CACHE / f"{sym}_daily.csv"
        if not p.exists():
            import yfinance as yf
            CACHE.mkdir(parents=True, exist_ok=True)
            df = yf.download(sym, start="2018-01-01", end="2026-10-01", auto_adjust=False, progress=False)
            df.columns = [x[0] if isinstance(x, tuple) else x for x in df.columns]
            df.reset_index().to_csv(p, index=False)
        df = pd.read_csv(p, parse_dates=["Date"])
        rows = [{"date": d.strftime("%Y-%m-%d"), "open": o, "high": h, "low": lo, "close": cl, "volume": float(v)}
                for d, o, h, lo, cl, v in zip(df.Date, df.Open, df.High, df.Low, df.Close, df.Volume)]
        hist[sym] = (pd.to_datetime(df.Date), rows[::-1])  # neueste zuerst
    out = {}
    for day in days:
        risks = []
        for sym, (dts, rows_desc) in hist.items():
            k = dts.searchsorted(day) - 1
            if k < 100:
                break
            asof = dts.iloc[k].strftime("%Y-%m-%d")
            with redirect_stdout(io.StringIO()):
                res, _ = m.analyze_index(sym, sym, rows_desc, cfg, rule, thr, asof)
            risks.append(res)
        if len(risks) == 2:
            out[day] = combine_index_risks(risks)
    return pd.Series(out)


def us_news_days(start: str, end: str) -> set:
    sys.path.insert(0, str(c.ROOT))
    from news_calendar.fred_releases import fetch_all_us_release_dates
    return set(fetch_all_us_release_dates(start, end))


def circuit_breaker_mask(t: pd.DataFrame) -> pd.Series:
    """drawdown-circuit-breaker Standardregeln 1:1 nachgebildet: Tagesverlust 2 %, 2 Verluste in Folge
    -> 24 h Pause, Woche 5 %, Monat 8 % (Risiko RISK_PCT je Trade). Realisiert zum Exit-Zeitpunkt."""
    t = t.sort_values("entry_time")
    keep = []
    closed: list[tuple[pd.Timestamp, float]] = []  # nur genommene Trades
    for _, row in t.iterrows():
        now = row.entry_time
        done = [(x, p) for x, p in closed if x <= now]
        pnl = pd.Series([p for _, p in done], index=pd.DatetimeIndex([x for x, _ in done]), dtype=float)
        day_loss = -pnl[pnl.index.normalize() == now.normalize()].sum()
        week_loss = -pnl[pnl.index >= (now.normalize() - pd.Timedelta(days=now.weekday()))].sum()
        month_loss = -pnl[pnl.index >= now.normalize().replace(day=1)].sum()
        last = sorted(done)[-2:]
        streak = len(last) == 2 and all(p < 0 for _, p in last) and now < last[-1][0] + pd.Timedelta(hours=24)
        ok = not (day_loss >= 2.0 or week_loss >= 5.0 or month_loss >= 8.0 or streak)
        keep.append(ok)
        if ok:
            closed.append((row.exit_time, row.r * c.RISK_PCT))
    return pd.Series(keep, index=t.index).reindex(t.index)


# --- Bewertung -----------------------------------------------------------------
def evaluate(strategy: str, t: pd.DataFrame, masks: dict[str, pd.Series]) -> pd.DataFrame:
    lk = c.lock(strategy)
    base = c.stats(t.sort_values("entry_time").r)
    rows = [{"variante": "ungefiltert (Referenz)", **base}]
    for name, keep in masks.items():
        lk.log_trials(1, note=f"skill_test 2b: {name}")
        rows.append({"variante": name, **c.stats(t[keep.reindex(t.index).fillna(True).astype(bool)].sort_values("entry_time").r)})
    df = pd.DataFrame(rows)
    n_trials = lk.trials
    srs = df["sharpe_trade"].iloc[1:].astype(float)
    var = float(srs.var(ddof=1)) if len(srs) > 1 else None
    df["dsr"] = [round(deflated_sharpe(sr, int(n), max(n_trials, 1), sr_var_trials=var), 3) if n > 2 else np.nan
                 for sr, n in zip(df.sharpe_trade, df.n)]
    df["delta_avg_r"] = (df.avg_r - base["avg_r"]).round(3)
    df.attrs["n_trials"] = n_trials
    return df


def orb() -> pd.DataFrame:
    t = c.is_trades("orb")
    days = pd.DatetimeIndex(sorted(t.entry_date.unique()))
    px = closes()
    br = breadth_scores(days)
    ibd = ibd_risk(days)
    news = us_news_days("2018-12-01", "2023-01-31")
    ret20 = [prior_value(px[INDEX_OF_LEG[leg]], d) / prior_value(px[INDEX_OF_LEG[leg]], d - pd.Timedelta(days=28)) - 1
             for leg, d in zip(t.leg, t.entry_date)]
    ctx = pd.DataFrame({"breadth": t.entry_date.map(br), "ibd": t.entry_date.map(ibd),
                        "news": t.entry_date.isin(news), "ret20": ret20}, index=t.index)
    ctx.to_csv(c.RESULTS / "context_orb.csv")
    masks = {
        "market-breadth-analyzer: Score < 40 -> aussetzen": ~(ctx.breadth < 40),
        "ibd-distribution-day-monitor: HIGH/SEVERE -> aussetzen": ~ctx.ibd.isin(["HIGH", "SEVERE"]),
        "Wirtschaftskalender (FRED lokal): US-Release-Tag -> aussetzen": ~ctx.news,
        "drawdown-circuit-breaker Standardregeln": circuit_breaker_mask(t),
        "ORB-H1: nur nach negativem 20-Tage-Index": ctx.ret20 <= 0,
    }
    print("Kontext-Abdeckung:", ctx.notna().mean().round(3).to_dict(),
          "| IBD-Risiko:", ctx.ibd.value_counts().to_dict(),
          "| Breadth<40:", int((ctx.breadth < 40).sum()))
    return evaluate("orb", t, masks)


def cot_state(days: pd.DatetimeIndex) -> pd.Series:
    """cot-contrarian-detector: Gold (CFTC 088691, Legacy futures-only, CFTC statt FMP -- FMP-COT ist
    im Free-Tier gesperrt). Skill-Formeln compute_cot_index(156 Wochen) + classify_extreme(90/10).
    Bericht (Stand Dienstag) gilt erst ab Veroeffentlichung am Freitag -> Datum + 3 Tage."""
    sys.path.insert(0, str(c.SKILLS / "cot-contrarian-detector" / "scripts"))
    from cot_index import classify_extreme, compute_cot_index

    cot = pd.read_csv(CACHE / "gold_cot.csv", parse_dates=["date"]).sort_values("date")
    cot["net"] = cot.nc_long - cot.nc_short
    avail = cot.date + pd.Timedelta(days=3)
    out = {}
    for day in days:
        k = avail.searchsorted(day)  # nur Berichte, die vor dem Entry-Tag veroeffentlicht waren
        out[day] = classify_extreme(compute_cot_index(cot.net.iloc[:k].tolist(), 156))
    return pd.Series(out)


def macro_regime(days: pd.DatetimeIndex) -> pd.Series:
    """macro-regime-detector: Regime je Monatsende aus den 9 ETFs (yfinance), 600 Tage Historie,
    ohne FMP-Treasury (Skill faellt auf SHY/TLT zurueck). Entry nutzt den letzten Monat VOR dem Entry-Monat."""
    sd = c.SKILLS / "macro-regime-detector" / "scripts"
    sys.path.insert(0, str(sd))
    import macro_regime_detector as mr  # noqa: E402
    from scorer import classify_regime

    p = CACHE / "macro_etfs.csv"
    if not p.exists():
        import yfinance as yf
        df = yf.download(mr.REQUIRED_ETFS, start="2016-06-01", end="2024-08-01", auto_adjust=True, progress=False)["Close"]
        df.to_csv(p)
    px = pd.read_csv(p, index_col=0, parse_dates=True)
    month_ends = px.groupby(px.index.to_period("M")).tail(1).index
    regimes = {}
    for me in month_ends[month_ends >= "2018-11-01"]:
        sub = px.loc[me - pd.Timedelta(days=600):me]
        hist = {e: [{"date": d.strftime("%Y-%m-%d"), "close": float(v), "adjClose": float(v)}
                    for d, v in sub[e].dropna()[::-1].items()] for e in mr.REQUIRED_ETFS}
        with redirect_stdout(io.StringIO()):
            comps = {
                "concentration": mr.calculate_concentration(rsp_history=hist["RSP"], spy_history=hist["SPY"]),
                "yield_curve": mr.calculate_yield_curve(treasury_rates=None, shy_history=hist["SHY"], tlt_history=hist["TLT"]),
                "credit_conditions": mr.calculate_credit_conditions(hyg_history=hist["HYG"], lqd_history=hist["LQD"]),
                "size_factor": mr.calculate_size_factor(iwm_history=hist["IWM"], spy_history=hist["SPY"]),
                "equity_bond": mr.calculate_equity_bond(spy_history=hist["SPY"], tlt_history=hist["TLT"]),
                "sector_rotation": mr.calculate_sector_rotation(xly_history=hist["XLY"], xlp_history=hist["XLP"]),
            }
            regimes[me.to_period("M")] = classify_regime(comps)["current_regime"]
    reg = pd.Series(regimes)
    return pd.Series({d: reg.get(d.to_period("M") - 1, np.nan) for d in days})


def ctnl() -> pd.DataFrame:
    t = c.is_trades("ctnl")
    dirs = pd.read_csv(CACHE / "ctnl_directions.csv", parse_dates=["entry_time"])
    t = t.merge(dirs, on="entry_time", how="left")
    days = pd.DatetimeIndex(sorted(t.entry_date.unique()))
    lab = pd.read_parquet(c.ROOT / "fusion_lab/data/macro_regime/labels.parquet")["joint"]
    lab.index = pd.to_datetime(lab.index).normalize()
    cot = cot_state(days)
    mreg = macro_regime(days)
    news = us_news_days("2018-12-01", "2024-08-31")
    ctx = pd.DataFrame({"cot": t.entry_date.map(cot), "macro_regime": t.entry_date.map(mreg),
                        "news": t.entry_date.isin(news), "direction": t.direction,
                        "joint": [prior_value(lab, d) for d in t.entry_date],
                        "weekday": t.entry_time.dt.dayofweek}, index=t.index)
    ctx.to_csv(c.RESULTS / "context_ctnl.csv")
    against = ((ctx.cot == "CROWDED_LONG") & (ctx.direction > 0)) | ((ctx.cot == "CROWDED_SHORT") & (ctx.direction < 0))
    masks = {
        "cot-contrarian-detector: Gold crowded in Trade-Richtung -> aussetzen": ~against,
        "macro-regime-detector: Contraction -> aussetzen": ctx.macro_regime.str.lower() != "contraction",
        "Wirtschaftskalender (FRED lokal): US-Release-Tag -> aussetzen": ~ctx.news,
        "drawdown-circuit-breaker Standardregeln": circuit_breaker_mask(t),
        "CTNL-H1: Regime Wachstum+Inflation beschleunigt -> aussetzen": ctx.joint != "g↑·accel × π↑·accel",
        "CTNL-H2: kein Entry am Freitag": ctx.weekday != 4,
    }
    print("COT:", ctx.cot.value_counts().to_dict(), "| Makro:", ctx.macro_regime.value_counts(dropna=False).to_dict(),
          "| News-Tage:", int(ctx.news.sum()), "| Richtung:", ctx.direction.value_counts().to_dict())
    return evaluate("ctnl", t, masks)


if __name__ == "__main__":
    strategy = sys.argv[1]
    df = {"orb": orb}[strategy]() if strategy == "orb" else globals()[strategy]()
    df.to_csv(c.RESULTS / f"filters_{strategy}.csv", index=False)
    print(f"Versuche in der Sperre: {df.attrs['n_trials']}")
    print(df[["variante", "n", "sum_r", "avg_r", "delta_avg_r", "pf", "win_rate", "sharpe_trade", "max_dd_pct", "dsr"]]
          .to_string(index=False))
