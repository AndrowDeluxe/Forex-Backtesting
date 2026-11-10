"""Daily-Edge × alle Filter, mit und gegen den Trend (Nutzerauftrag 10.11.2026, Plan freigegeben).

    python -m htf_daily_trade.filter_matrix          # IS 2016-2021 + OOS 2022-2024 (OOS frei seit 10.11.)

Basis-Setups unveraendert (keine neuen Einstiegsregeln):
  R   Typ R, beste IS-Variante E3 S1 T7 (varianten_r_is.csv): Limit 50 % der Fractal-Kerze,
      Stop Struktur, Ausstieg gegenlaeufiges Fractal (max. 30 Tage)
  C2  Typ C2 EL S1 T8 wie eingefroren (c2_goldfilter.CONFIG), hier OHNE Gold-Filter, damit alle
      Filter dieselbe Basis haben
Maerkte: 6 bisherige + NZDUSD, USDCAD, USDCHF (D1 ab 2003).

Jeder Trade bekommt je Filter eine Trend-Richtung (+1/−1/0, nur Wissen bis zum Schluss vor dem
Fuelltag) und damit den Zustand mit / gegen / neutral. Die vier Nutzer-Gruppen sind:
  R-gegen = R & gegen   R-mit = R & mit   C-mit = C2 & mit   C-gegen-HTF = C2 & gegen

Filter
  T1 MA 12/20 · T2 Weekly SMA 20/50 · T3 SMA 200 · T4 ADX(14) >= 20, Richtung +DI/−DI ·
  T5 Ribbon (Schluss ueber/unter EMA 50 D, EMA 200 D, EMA 50 W) · T6 Faber (Monatsschluss vs.
  10-Monats-SMA) · T7 Weekly EMA 9/21
  M1 Zins-Momentum · M2 Carry · M3 Regime-Matrix · M4 Regimekarte g×π · M5 Gold-Zinskurve (nur Gold)
  · M6 G8-Staerke · M7 COT-Fluss (Non-Commercials, 4 Berichte)
Stufe 1 = Einzelfilter. Kombinationen (Stufe 2) erst nach Sichtung; finale Version max. 9 Parameter.
Sperre `htf_daily_filter_matrix`: alle Zellen gezaehlt.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import htf_daily_trade.ipda_cycles as ic
from fusion_lab.filters.cot_flow import CotFlowFilter
from fusion_lab.filters.zins_fx import ZinsFxFilter
from fusion_lab.filters.zinskurve_regime import GoldZinskurvenFilter, confirmed, regime_series
from fusion_lab.macro_regime.model import daily_labels
from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.backtest_varianten import entries, simulate
from htf_daily_trade.c2_filter_overlap import matrix_dir
from htf_daily_trade.macro import G8_BASE, g8_scores
from research_lock import Lock, deflated_sharpe

MARKETS = {  # Dateien, Runde-Marken-Raster, Round-Trip-Kosten in Preis (alte 6 wie backtest_r)
    "EURUSD": (["EURUSD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00010),
    "GBPUSD": (["GBPUSD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00014),
    "AUDUSD": (["AUDUSD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00013),
    "NZDUSD": (["NZDUSD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00016),
    "USDJPY": (["USDJPY_D1_2003-01-01_2026-10-10.parquet"], 0.5, 0.012),
    "USDCAD": (["USDCAD_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00016),
    "USDCHF": (["USDCHF_D1_2003-01-01_2026-10-10.parquet"], 0.005, 0.00016),
    "XAUUSD": (["GOLD_D1_2010-01-01_2026-08-13.parquet"], 10.0, 0.30),
    "XAGUSD": (["SILVER_D1_2009-01-01_2016-01-01.parquet", "SILVER_D1_2016-01-01_2026-08-01.parquet"], 0.5, 0.03),
}
METALS = ("XAUUSD", "XAGUSD")
SETUPS = {"R": ("R", "E3", "S1", "T7"), "C2": ("C", "C2 EL", "S1", "T8")}
TECH = {"T1": "MA 12/20", "T2": "Weekly SMA 20/50", "T3": "SMA 200", "T4": "ADX>=20 DI",
        "T5": "Ribbon D50/D200/W50", "T6": "Faber 10M", "T7": "Weekly EMA 9/21"}
MACRO = {"M1": "Zins-Momentum", "M2": "Carry", "M3": "Regime-Matrix", "M4": "Regimekarte g×π",
         "M5": "Gold-Zinskurve", "M6": "G8-Staerke", "M7": "COT-Fluss"}
FILTERS = {**TECH, **MACRO}
# Stufe 1b (Nutzerauftrag 10.11.): uebrige Repo-Filter, auf Daily uebertragen
EXTRA_DIR = {"X2": "DXY synth. 20T", "X3": "US-Realzins 20T", "X4": "COT-Index konträr", "X5": "Kalman-Trend",
             "X6": "Triple-MA 10/20/50", "X9": "Cross-Pair USD breit", "X10": "Partner-Momentum 5T",
             "X11": "Volumenprofil-POC 20T"}
EXTRA_REG = {"X1": "VIX-Regime", "X7": "Vol-Regime ATR", "X8": "Jump-Regime H1", "X12": "News-Tag US/EUR"}
DIRECTIONAL = {**FILTERS, **EXTRA_DIR}
ALL_FILTERS = {**DIRECTIONAL, **EXTRA_REG}
USD_ORIENT = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1, "USDJPY": 1, "USDCAD": 1, "USDCHF": 1,
              "XAUUSD": -1, "XAGUSD": -1}   # Markt-Richtung bei steigendem USD
PARTNER = {"XAUUSD": ("XAGUSD", 1), "XAGUSD": ("XAUUSD", 1), "EURUSD": ("GBPUSD", 1), "GBPUSD": ("EURUSD", 1),
           "AUDUSD": ("NZDUSD", 1), "NZDUSD": ("AUDUSD", 1), "USDCAD": ("AUDUSD", -1), "USDCHF": ("EURUSD", -1),
           "USDJPY": ("USDCHF", 1)}
H1_FILES = {"XAUUSD": "GOLD_H1_2016-01-01_2026-10-29.parquet", "XAGUSD": "SILVER_H1_2016-01-01_2026-08-01.parquet"}
IS_START, IS_END, OOS_END = "2016-01-01", "2021-12-31", "2024-12-31"
WARMUP = "2014-01-01"   # SMA 200 / Faber / Weekly 50 brauchen Vorlauf
LOCK = "htf_daily_filter_matrix"
MIN_N = 30


def load_market(name: str) -> pd.DataFrame:
    parts = []
    for f in MARKETS[name][0]:
        ic.FILES[name] = f
        parts.append(ic.load_daily(name))
    d = pd.concat(parts)
    return d[~d.index.duplicated(keep="last")].sort_index()


def _adx(x: pd.DataFrame, n: int = 14) -> tuple[pd.Series, pd.Series]:
    h, l, c = x["High"], x["Low"], x["Close"]
    up, dn = h.diff(), -l.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    ndm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    w = lambda s: s.ewm(alpha=1 / n, adjust=False).mean()
    atr = w(tr)
    pdi, ndi = 100 * w(pdm) / atr, 100 * w(ndm) / atr
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    return w(dx), np.sign(pdi - ndi)


def _htf(close: pd.Series, rule: str) -> pd.Series:
    """Abgeschlossene HTF-Schlusskurse, erst ab dem Folgetag bekannt."""
    return close.resample(rule).last().dropna()


def trend_dirs(x: pd.DataFrame) -> pd.DataFrame:
    """Richtung je Tag und technischem Filter, Stand Tagesschluss (ohne Vorgriff)."""
    c = x["Close"]
    sgn = lambda s: np.sign(s).fillna(0).astype(int)
    out = pd.DataFrame(index=x.index)
    out["T1"] = sgn(x["ma_fast"] - x["ma_slow"])
    out["T2"] = sgn(x["w_trend"])
    out["T3"] = sgn(c - c.rolling(200).mean())
    adx, di = _adx(x)
    out["T4"] = (di * (adx >= 20)).fillna(0).astype(int)
    wk = _htf(c, "W-FRI")
    w50 = wk.ewm(span=50, adjust=False).mean().shift(1).reindex(x.index, method="ffill")
    e50, e200 = c.ewm(span=50, adjust=False).mean(), c.ewm(span=200, adjust=False).mean()
    above = (c > e50) & (c > e200) & (c > w50)
    below = (c < e50) & (c < e200) & (c < w50)
    out["T5"] = above.astype(int) - below.astype(int)
    mo = _htf(c, "ME")
    out["T6"] = sgn((mo - mo.rolling(10).mean()).shift(1).reindex(x.index, method="ffill"))
    out["T7"] = sgn((wk.ewm(span=9, adjust=False).mean() - wk.ewm(span=21, adjust=False).mean())
                    .shift(1).reindex(x.index, method="ffill"))
    out.loc[x.index < x.index[0] + pd.Timedelta(days=300), ["T3", "T6"]] = 0
    return out


_CLOSES: dict[str, pd.Series] = {}


def closes() -> dict[str, pd.Series]:
    if not _CLOSES:
        for name in MARKETS:
            _CLOSES[name] = load_market(name)["Close"]
    return _CLOSES


def _h1_daily(name: str) -> pd.DataFrame:
    """H1-Kerzen mit Handelstag-Schluessel wie load_daily (So -> Mo, Sa -> Fr)."""
    f = H1_FILES.get(name, f"{name}_H1_2007-01-01_2026-11-10.parquet")
    d = pd.read_parquet(f"data_cache/combined/{f}")[["Close", "Volume"]].sort_index()
    d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
    key = d.index.normalize()
    dow = d.index.dayofweek
    key = key.where(dow != 6, key + pd.Timedelta(days=1)).where(dow != 5, key - pd.Timedelta(days=1))
    d["day"] = key
    return d


def h1_features(name: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    """X8 Jump-Anteil je Tag (RV vs. Bipower), X11 Lage zum 20-Tage-Volumen-POC (Stand Tagesschluss)."""
    d = _h1_daily(name)
    r = np.log(d["Close"]).diff()
    rows = {}
    for day, g in r.groupby(d["day"]):
        a = g.dropna().abs().to_numpy()
        if len(a) < 5:
            continue
        rv = (a ** 2).sum()
        bv = (np.pi / 2) * (a[1:] * a[:-1]).sum()
        rows[day] = max(0.0, (rv - bv) / rv) if rv > 0 else np.nan
    rj = pd.Series(rows).sort_index()
    lo, hi = rj.rolling(250, min_periods=120).quantile(1 / 3), rj.rolling(250, min_periods=120).quantile(2 / 3)
    jump = pd.Series(np.select([rj <= lo, rj >= hi], ["ruhig", "sprunghaft"], "mittel"), index=rj.index)
    jump[lo.isna()] = "neutral"
    days = d["day"].to_numpy()
    uniq = pd.DatetimeIndex(sorted(set(days)))
    px, vol = d["Close"].to_numpy(), d["Volume"].to_numpy(dtype=float)
    starts = np.searchsorted(days.astype("datetime64[ns]"), uniq.to_numpy().astype("datetime64[ns]"))
    poc = {}
    for j in range(20, len(uniq)):
        a, b = starts[j - 19], (starts[j + 1] if j + 1 < len(uniq) else len(px))
        p, v = px[a:b], vol[a:b]
        if len(p) < 50 or v.sum() <= 0:
            continue
        hist, edges = np.histogram(p, bins=30, weights=v)
        k = int(np.argmax(hist))
        poc[uniq[j]] = (np.sign(p[-1] - (edges[k] + edges[k + 1]) / 2))
    out = pd.DataFrame({"X8": jump.reindex(index), "X11": pd.Series(poc).reindex(index)})
    out["X8"] = out["X8"].fillna("neutral")
    out["X11"] = out["X11"].fillna(0).astype(int)
    return out


def extra_dirs(name: str, x: pd.DataFrame) -> pd.DataFrame:
    """Stufe-1b-Filter aus Kursdaten, Stand Tagesschluss je Tag von x (ohne Vorgriff)."""
    from strategy.kalman_filter import estimate_kalman_params, kalman_smooth
    cl = {k: v.reindex(x.index).ffill() for k, v in closes().items()}
    c = x["Close"]
    sgn = lambda s: np.sign(s).fillna(0).astype(int)
    out = pd.DataFrame(index=x.index)
    # X2: synthetischer DXY (ICE-Gewichte ohne SEK), 20-Tage-Veraenderung
    ldxy = (-0.576 * np.log(cl["EURUSD"]) + 0.136 * np.log(cl["USDJPY"]) - 0.119 * np.log(cl["GBPUSD"])
            + 0.091 * np.log(cl["USDCAD"]) + 0.036 * np.log(cl["USDCHF"]))
    out["X2"] = sgn(ldxy.diff(20)) * USD_ORIENT[name]
    # X5: Kalman-Trend (Q/R nur aus Daten vor dem IS, starke Glaettung), Steigung 5 Tage
    q, r = estimate_kalman_params(c.loc[:"2015-12-31"], 0.9)
    k = kalman_smooth(c, q, r)
    out["X5"] = sgn(k - k.shift(5))
    # X6: Triple-MA 10/20/50 ausgerichtet
    m10, m20, m50 = c.rolling(10).mean(), c.rolling(20).mean(), c.rolling(50).mean()
    out["X6"] = ((m10 > m20) & (m20 > m50)).astype(int) - ((m10 < m20) & (m20 < m50)).astype(int)
    # X7: Vol-Regime ATR20 / ATR250
    ratio = x["atr"] / x["atr"].rolling(250, min_periods=120).mean()
    out["X7"] = np.select([ratio < 0.85, ratio > 1.15], ["ruhig", "nervoes"], "normal")
    out.loc[ratio.isna(), "X7"] = "neutral"
    # X9: breite USD-Bewegung ueber 5 Tage (>= 5 von 7 Paaren)
    usd_up = sum((np.log(cl[p]).diff(5) * USD_ORIENT[p] > 0).astype(int) for p in USD_ORIENT if p not in METALS)
    usd = np.select([usd_up >= 5, usd_up <= 2], [1, -1], 0)
    out["X9"] = usd * USD_ORIENT[name]
    # X10: Partner-Momentum 5 Tage
    p, s = PARTNER[name]
    out["X10"] = sgn(np.log(cl[p]).diff(5)) * s
    return out.join(h1_features(name, x.index))


def lock_events(lock: Lock) -> list[dict]:
    import json
    if not lock.log_path.exists():
        return []
    return [json.loads(l) for l in lock.log_path.read_text(encoding="utf-8").splitlines() if l.strip()]


class MacroDirs:
    @classmethod
    def full(cls) -> "MacroDirs":
        md = cls()
        md.init_extra()
        return md

    def __init__(self):
        self.zf = ZinsFxFilter(20)
        self.regime = confirmed(regime_series(20), 5)
        self.gold = GoldZinskurvenFilter(20, 5)
        self.g8 = g8_scores()
        self.cot = CotFlowFilter(4)
        labels = daily_labels(pd.bdate_range("2009-01-01", pd.Timestamp.today()))
        self.lens = labels["signs"]
        self.landi = {}
        for name in MARKETS:  # M4: Richtung je (Markt, Regime) aus der IS-Tagesrendite
            ret = np.log(load_market(name)["Close"]).diff().loc[IS_START:IS_END]
            df = pd.DataFrame({"ret": ret}).join(self.lens.rename("reg"), how="inner")
            for reg, m in df.groupby("reg")["ret"].mean().items():
                self.landi[(name, reg)] = int(np.sign(m))

    @staticmethod
    def _prev(s, d):
        i = s.index.searchsorted(pd.Timestamp(d), side="left") - 1
        return None if i < 0 else s.iloc[i]

    def g8_dir(self, m: str, d) -> int:
        row = self._prev(self.g8, d)
        if row is None or row.isna().any():
            return 0
        if m in G8_BASE:
            b, q = G8_BASE[m]
            return int(np.sign(row[b] - row[q]))
        return -int(np.sign(row["USD"]))

    def init_extra(self) -> None:
        from fusion_lab.macro_data import store
        from news_calendar.filter import get_news_dates
        w = self.zf.wide
        self.real_chg = (w["US.10y"] - w["US.breakeven_10y"]).dropna().diff(20)
        self.vix = w["MKT.vix"].dropna()
        self.vix_med = self.vix.rolling(252, min_periods=120).median()
        self.news = set(get_news_dates("2014-01-01", OOS_END))

    def cot_index(self, m: str, d, weeks: int = 156) -> int:
        from fusion_lab.filters.cot_flow import CODES
        code, orient = CODES[m]
        cot = self.cot.cot
        s = cot[(cot["cftc_contract_market_code"] == code) & (cot["avail"] < pd.Timestamp(d))]["nc"].tail(weeks)
        if len(s) < weeks // 2 or s.max() == s.min():
            return 0
        idx = 100 * (s.iloc[-1] - s.min()) / (s.max() - s.min())
        base = -1 if idx > 80 else (1 if idx < 20 else 0)   # konträr: Crowding gegen sich handeln
        return base * orient

    def extra(self, m: str, d) -> dict:
        rc = self._prev(self.real_chg, d)
        v, vm = self._prev(self.vix, d), self._prev(self.vix_med, d)
        return {"X1": "neutral" if v is None or vm is None or pd.isna(vm) else ("hoch" if v > vm else "tief"),
                "X3": 0 if rc is None or pd.isna(rc) else int(np.sign(rc)) * USD_ORIENT[m],
                "X4": self.cot_index(m, d),
                "X12": "news" if pd.Timestamp(d).normalize() in self.news else "ruhig"}

    def dirs(self, m: str, d) -> dict:
        reg = self._prev(self.lens, d)
        return {"M1": self.zf.momentum_dir(m, d), "M2": self.zf.carry_dir(m, d),
                "M3": matrix_dir(self.regime, m, d),
                "M4": self.landi.get((m, reg), 0) if reg is not None and not pd.isna(reg) else 0,
                "M5": self.gold.direction(d) if m == "XAUUSD" else 0,
                "M6": self.g8_dir(m, d), "M7": self.cot.direction(m, d)}


def trades(setup: str, end: str) -> pd.DataFrame:
    typ, var, stop, tgt = SETUPS[setup]
    e = pd.Timestamp(end)
    rows = []
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp(WARMUP):e], grid)
        td = trend_dirs(x).join(extra_dirs(name, x))
        end_idx = int(np.searchsorted(x.index, e, side="right")) - 1
        busy = {"long": -1, "short": -1}
        for en in sorted((z for z in entries(x, typ) if z["v"] == var), key=lambda z: z["fill"]):
            t = x.index[en["fill"]]
            if t < pd.Timestamp(IS_START) or en["fill"] > end_idx or en["fill"] <= busy[en["side"]]:
                continue
            res = simulate(x, en, stop, tgt, cost, end_idx)
            if res is None:
                continue
            busy[en["side"]] = res["exit_k"]
            known = en["fill"] - 1   # letzter abgeschlossener Tag vor dem Fuelltag
            rows.append({"setup": setup, "markt": name, "datum": t, "seite": en["side"], "r": res["r"],
                         **td.iloc[known].to_dict()})
    return pd.DataFrame(rows)


def label(t: pd.DataFrame, md: MacroDirs) -> pd.DataFrame:
    mac = pd.DataFrame([{**md.dirs(r.markt, r.datum), **md.extra(r.markt, r.datum)} for r in t.itertuples()],
                       index=t.index)
    t = pd.concat([t, mac], axis=1)
    sign = np.where(t["seite"] == "long", 1, -1)
    for f in DIRECTIONAL:
        d = t[f].to_numpy().astype(int) * sign
        t[f] = np.select([d > 0, d < 0], ["mit", "gegen"], "neutral")
    t["periode"] = np.where(t["datum"] <= pd.Timestamp(IS_END), "IS", "OOS")
    t["klasse"] = np.where(t["markt"].isin(METALS), "Metalle", "FX")
    return t


def cell(r: pd.Series) -> dict:
    st = stats(r)
    return {"n": st.get("n", 0), "mean_r": st.get("mean_r", np.nan), "t": st.get("t", np.nan),
            "pf": st.get("pf", np.nan)}


def matrix(t: pd.DataFrame, filters: dict = FILTERS) -> pd.DataFrame:
    rows = []
    for setup in SETUPS:
        s = t[t["setup"] == setup]
        for f, name in {"--": "Basis ohne Filter", **filters}.items():
            states = ("alle",) if f == "--" else (
                ("mit", "gegen", "neutral") if f in DIRECTIONAL else tuple(sorted(s[f].dropna().unique())))
            for st in states:
                sel = s if f == "--" else s[s[f] == st]
                row = {"setup": setup, "filter": f, "name": name, "zustand": st}
                for per in ("IS", "OOS"):
                    for k, v in cell(sel.loc[sel["periode"] == per, "r"]).items():
                        row[f"{per}_{k}"] = v
                for kl in ("FX", "Metalle"):
                    c = cell(sel.loc[(sel["periode"] == "IS") & (sel["klasse"] == kl), "r"])
                    row[f"IS_{kl}_n"], row[f"IS_{kl}_mean"] = c["n"], c["mean_r"]
                rows.append(row)
    return pd.DataFrame(rows)


def report(m: pd.DataFrame, n_trials: int) -> None:
    pd.set_option("display.width", 220)
    group = {("R", "gegen"): "R-gegen", ("R", "mit"): "R-mit", ("C2", "mit"): "C-mit", ("C2", "gegen"): "C-gegen-HTF"}
    for setup in SETUPS:
        s = m[m["setup"] == setup].copy()
        s["gruppe"] = [group.get((setup, z), z) for z in s["zustand"]]
        cols = ["filter", "name", "gruppe", "IS_n", "IS_mean_r", "IS_t", "IS_pf", "OOS_n", "OOS_mean_r", "OOS_t",
                "IS_FX_mean", "IS_Metalle_mean"]
        print(f"\n===== {setup}: Einzelfilter (IS 2016-21 | OOS 2022-24) =====")
        print(s[cols].round(3).to_string(index=False))
    m2 = m[(m["filter"] != "--") & (m["zustand"] != "neutral") & (m["IS_n"] >= MIN_N)]
    top = m2.sort_values("IS_t", ascending=False).head(10)
    print(f"\n===== Top 10 nach IS-t (n >= {MIN_N}), Lock {n_trials} Versuche =====")
    for _, r in top.iterrows():
        sr_n = r["IS_t"] / np.sqrt(r["IS_n"])
        print(f"{r['setup']:>2} {r['filter']} {r['name']:<20} {r['zustand']:<6} IS n {r['IS_n']:>3} "
              f"Ø {r['IS_mean_r']:+.3f} t {r['IS_t']:+.2f} | OOS n {r['OOS_n']:>3} Ø {r['OOS_mean_r']:+.3f} "
              f"t {r['OOS_t']:+.2f} | DSR {deflated_sharpe(sr_n, int(r['IS_n']), n_trials):.2f}")


# Stufe 2: Kandidaten = Einzelfilter, deren IS-Zustand besser als die Basis war (Sichtung Stufe 1, 10.11.).
# Ein Trade bleibt, wenn JEDER Filter der Kombination im genannten Zustand ist (UND).
STAGE2 = {
    "C2": [("T2", "gegen"), ("T3", "gegen"), ("T6", "gegen"), ("T7", "gegen"), ("T4", "mit"), ("T5", "neutral"),
           ("M1", "mit"), ("M2", "mit"), ("M3", "mit"), ("M6", "mit"), ("M7", "mit")],
    "R": [("T1", "gegen"), ("T3", "gegen"), ("T5", "gegen"), ("T7", "gegen"), ("M2", "gegen"), ("M3", "gegen"),
          ("M4", "mit"), ("M7", "gegen")],
}
MAX_K = 3


def stage2(t: pd.DataFrame, n_trials: int) -> pd.DataFrame:
    from itertools import combinations
    rows = []
    for setup, cands in STAGE2.items():
        s = t[t["setup"] == setup]
        for k in range(1, MAX_K + 1):
            for kombi in combinations(cands, k):
                sel = s
                for f, z in kombi:
                    sel = sel[sel[f] == z]
                row = {"setup": setup, "kombi": " + ".join(f"{f}:{z}" for f, z in kombi), "k": k}
                for per in ("IS", "OOS"):
                    for kk, v in cell(sel.loc[sel["periode"] == per, "r"]).items():
                        row[f"{per}_{kk}"] = v
                rows.append(row)
    df = pd.DataFrame(rows)
    df["dsr"] = [deflated_sharpe(r.IS_t / np.sqrt(r.IS_n), int(r.IS_n), n_trials) if r.IS_n >= 2 else np.nan
                 for r in df.itertuples()]
    df.to_csv("htf_daily_trade/filter_matrix_stufe2.csv", index=False)
    pd.set_option("display.width", 220)
    for setup in STAGE2:
        d = df[(df["setup"] == setup) & (df["IS_n"] >= MIN_N)].sort_values("IS_t", ascending=False)
        print(f"\n===== Stufe 2 {setup}: Top 15 nach IS-t (n >= {MIN_N}), Lock {n_trials} Versuche =====")
        print(d.head(15).round(3).to_string(index=False))
        print(f"IS t > 2 und OOS Ø > 0: {((d.IS_t > 2) & (d.OOS_mean_r > 0)).sum()} von {len(d)} | "
              f"OOS Ø > 0 bei allen: {(d.OOS_mean_r > 0).mean():.0%}")
    return df


def main() -> None:
    import sys
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, OOS_END)
    lock.register_blind("2010-01-01", "2015-12-31")
    n_cells = len(SETUPS) * len(FILTERS) * 2
    if lock.trials == 0:
        lock.log_trials(n_cells, "Stufe 1: R/C2 x 14 Filter x mit/gegen, 9 Maerkte (10.11.)")
    if "--stufe1b" in sys.argv:
        n1b = len(SETUPS) * (2 * len(EXTRA_DIR) + 2 + 3 + 3 + 2)
        if not any("Stufe 1b" in (e.get("note") or "") for e in lock_events(lock)):
            lock.log_trials(n1b, "Stufe 1b: 12 uebrige Repo-Filter (VIX, DXY, Realzins, COT-Index, Kalman, Triple-MA, "
                                 "Vol, Jump, Cross-Pair, Partner, Volumenprofil, News) (10.11.)")
        t = label(pd.concat([trades(s, OOS_END) for s in SETUPS], ignore_index=True), MacroDirs.full())
        t.to_csv("htf_daily_trade/filter_matrix_trades.csv", index=False)
        m = matrix(t, {**EXTRA_DIR, **EXTRA_REG})
        m.to_csv("htf_daily_trade/filter_matrix_1b.csv", index=False)
        report(m, lock.trials)
        return
    if "--stufe2" in sys.argv:
        from math import comb
        n2 = sum(comb(len(c), k) for c in STAGE2.values() for k in range(1, MAX_K + 1))
        if lock.trials == n_cells:
            lock.log_trials(n2, f"Stufe 2: UND-Kombinationen bis {MAX_K} Filter aus Stufe-1-Kandidaten (10.11.)")
        stage2(pd.read_csv("htf_daily_trade/filter_matrix_trades.csv", parse_dates=["datum"]), lock.trials)
        return
    md = MacroDirs()
    md.init_extra()
    t = pd.concat([trades(s, OOS_END) for s in SETUPS], ignore_index=True)
    t = label(t, md)
    t.to_csv("htf_daily_trade/filter_matrix_trades.csv", index=False)
    m = matrix(t)
    m.to_csv("htf_daily_trade/filter_matrix.csv", index=False)
    report(m, lock.trials)


if __name__ == "__main__":
    main()
