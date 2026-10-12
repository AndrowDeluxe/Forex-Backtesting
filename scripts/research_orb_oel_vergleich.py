"""ORB-Gegenprobe mit Oel (WTI): Welchen Mechanismus verfolgt Oel gegenueber
S&P 500 und Nasdaq 100?

Hinweis aus der Gruppenarbeit (Mentor, 11.10.2026): die ORB-Daten mit Oel
abgleichen. Oel ist eine natuerliche Kontrollgruppe fuer die Mechanismus-
Felder der Kriterien-PDF (Seite 7):
  - Kein SPX-/0DTE-Dealer-Gamma, keine gehebelten Index-ETFs, keine
    Eroeffnungsauktion um 09:30 (Oel handelt fast 24 h, NYMEX-Pit-Open 09:00,
    Settlement 14:28-14:30 NY).
  - Eigene Zwangs-/News-Fluesse: EIA-Lagerdaten Mi 10:30 NY, OPEC,
    Erzeuger-Hedging, CTA-Trendfolger (Zeitreihen-Momentum in Rohstoffen
    stark, Moskowitz/Ooi/Pedersen 2012).
  -> Kippt der Trendfilter in Oel im selben Tresor wie bei den Indizes, ist
     die Ursache eher makro-/regimeweit. Kippt er nicht, eher index-
     spezifisch (Optionen/Struktur).

KEINE Optimierung. Getestet werden nur vorab feste Konfigurationen
(8 Versuche auf OIL, im Lock gezaehlt):
  4 Konfigurationen  x  2 Uhren
  - "SP500-Gewinner": beide Richtungen, nur neutrale Tage, Stop 1,0 ATR, 8R
  - "NASDAQ-Gewinner": nur long, nur neutrale Tage, Stop 1,0 ATR, 8R
  - "ungefiltert": beide Richtungen, kein Ribbon
  - "mit Trend": beide Richtungen, nur in Ribbon-Richtung
  - Index-Uhr: Range 09:30-09:45, Ausstieg 16:00 (1:1 wie Indizes)
  - Oel-Uhr:   Range 09:00-09:15, Ausstieg 14:30 (NYMEX-Pit/Settlement)
Gleicher Simulator wie die IS-only-ORB (M1, Stop vor Ziel, Kosten in bps).
Kosten OIL: Spread 4,0 bps (Annahme ~3 Cent bei 70-80 $, fusion_lab nutzt
5 bps Rundturn) + dieselbe Slippage wie bei den Indizes; dazu Kosten x2.

Dazu beschreibende Mechanismus-Diagnosen je Instrument und Jahr:
  a) Ribbon-Spread: Oe R "nur neutral" minus "mit Trend" (der Tresor-Kipp)
  b) Folgequote: Anteil Tage, an denen der 1. Ausbruch zum Sitzungsende
     jenseits des Ausbruchslevels schliesst
  c) Intraday-Momentum (Gao 2018): Steigung/t von r(letzte 30 Min.) auf
     r(Vortagesschluss -> 30 Min. nach Open)
  d) Mehrtages-Trend: Steigung/t von r(heute, Sitzung) auf r(Vortag, Sitzung)
  e) Range-Breite in ATR, Anteil neutraler Tage
  f) Oel: EIA-Mittwoch gegen andere Tage; Tageskorrelation Oel/SP500

  python scripts/research_orb_oel_vergleich.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
import ny_open_orb.range as orb_range  # noqa: E402
from ny_open_orb import regime  # noqa: E402
from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402
from research_lock import Lock, config_hash  # noqa: E402
from research_orb_cancel_at_sl_and_hold import SPREAD_BPS  # noqa: E402
from research_orb_is_only_reopt import IS_END, IS_START, OOS_END, TRESOR_END, metrics, run_config  # noqa: E402

SPREAD_BPS.setdefault("OIL", 4.0)  # gleiches dict-Objekt wie in sim() -> wirkt dort mit

STRATEGY = "orb_oel_vergleich_20261011"
RES = ROOT / "ny_open_orb" / "results"
PERIODS = [("IS", IS_START, "2023-01-01"), ("OOS", "2023-01-01", "2025-10-01"), ("Tresor", "2025-10-01", "2026-10-01")]
CLOCKS = {"index": dict(open=(9, 30), close=(16, 0)), "oel": dict(open=(9, 0), close=(14, 30))}
BASE = dict(weekday=None, rule="none", stop=1.0, target=8.0, partial=None, range_bars=1)
CONFIGS = {
    "SP500-Gewinner": dict(BASE, dirs="beide", ribbon="neutral"),
    "NASDAQ-Gewinner": dict(BASE, dirs="long", ribbon="neutral"),
    "ungefiltert": dict(BASE, dirs="beide", ribbon="kein"),
    "mit Trend": dict(BASE, dirs="beide", ribbon="mit_trend"),
}
MIN_PRICE = 10.0  # April 2020: WTI-Kontrakt nahe/unter null -> bps-Kosten und R sinnlos


def set_clock(clock: str):
    c = CLOCKS[clock]
    orb_range.NY_OPEN_HOUR, orb_range.NY_OPEN_MINUTE = c["open"]
    orb_range.NY_CLOSE_HOUR, orb_range.NY_CLOSE_MINUTE = c["close"]


def load(instrument: str, clock: str):
    set_clock(clock)
    m15 = pb._retry(lambda: fetch_m15(instrument, IS_START, TRESOR_END), attempts=3, delay_seconds=5, timeout_seconds=600)
    m1 = pb._retry(lambda: fetch_m1(instrument, IS_START, TRESOR_END), attempts=3, delay_seconds=5, timeout_seconds=3600)
    frame = build_frame(m15, m1, range_bars=1)
    if instrument == "OIL":
        bad = frame.groupby("session")["low"].min()
        bad = bad[bad < MIN_PRICE].index
        frame = frame[~frame["session"].isin(bad)]
    sessions = pd.DatetimeIndex(frame["session"].dropna().unique())
    bias = regime.ema_trend_bias(m15, sessions)
    return {1: frame}, sessions, bias, m1


def by_period(r: pd.Series, c: pd.Series) -> dict:
    out = {}
    for name, a, b in PERIODS:
        m = (r.index >= a) & (r.index < b)
        out[name] = metrics(r[m], c[m])
    return out


# ---------------------------------------------------------------- Diagnosen
def session_points(m1: pd.DataFrame, clock: str) -> pd.DataFrame:
    """Je Sitzung: Vortagesschluss, Open, Open+30, Close-30, Close (M1-Schluss)."""
    c = CLOCKS[clock]
    o_min, x_min = c["open"][0] * 60 + c["open"][1], c["close"][0] * 60 + c["close"][1]
    cl = m1["close"]
    mins = m1.index.hour * 60 + m1.index.minute
    day = m1.index.normalize()

    def at(minute):  # Schluss der letzten M1-Bar VOR minute
        s = cl[(mins < minute) & (mins >= minute - 15)]
        return s.groupby(day[(mins < minute) & (mins >= minute - 15)]).last()

    first = cl[mins == o_min].groupby(day[mins == o_min]).first()  # Schluss der 1. Minute
    df = pd.DataFrame({"open": first, "p30": at(o_min + 30), "c30": at(x_min - 30), "close": at(x_min)})
    df = df.dropna()
    df["prev_close"] = df["close"].shift(1)
    return df.dropna()


def ols_t(y: pd.Series, x: pd.Series) -> tuple[float, float, int]:
    d = pd.concat([y, x], axis=1).dropna()
    if len(d) < 30:
        return np.nan, np.nan, len(d)
    d = d.clip(d.quantile(0.01), d.quantile(0.99), axis=1)  # 1/99-%-Winsorisierung: Crash-Tage (04/2025) dominieren sonst
    yv, xv = d.iloc[:, 0].to_numpy(), d.iloc[:, 1].to_numpy()
    xv = xv - xv.mean()
    beta = (xv * (yv - yv.mean())).sum() / (xv ** 2).sum()
    res = yv - yv.mean() - beta * xv
    se = np.sqrt((res ** 2).sum() / (len(d) - 2) / (xv ** 2).sum())
    return beta, beta / se, len(d)


def follow_through(frame: pd.DataFrame) -> pd.Series:
    """1 = 1. Ausbruch schliesst die Sitzung jenseits des Levels, 0 = nicht."""
    tw = frame[(frame.index >= frame["range_end"]) & (frame.index < frame["session_close"])]
    out = {}
    for s, day in tw.groupby("session"):
        hi, lo = day["orb_high"].iloc[0], day["orb_low"].iloc[0]
        if pd.isna(hi):
            continue
        up, dn = day["high"].to_numpy() >= hi, day["low"].to_numpy() <= lo
        iu = np.argmax(up) if up.any() else 10**9
        idn = np.argmax(dn) if dn.any() else 10**9
        if iu == idn:
            continue  # kein Ausbruch oder beide in derselben Bar
        last = day["close"].iloc[-1]
        out[s] = float(last > hi) if iu < idn else float(last < lo)
    return pd.Series(out)


def diagnostics(inst: str, frame: pd.DataFrame, bias: pd.Series, m1: pd.DataFrame, clock: str,
                r_neutral: pd.Series, r_trend: pd.Series) -> pd.DataFrame:
    pts = session_points(m1, clock)
    if inst == "OIL":
        pts = pts[pts[["open", "close", "prev_close"]].min(axis=1) >= MIN_PRICE]
    r_first = pts["p30"] / pts["prev_close"] - 1
    r_last = pts["close"] / pts["c30"] - 1
    r_sess = pts["close"] / pts["open"] - 1
    ft = follow_through(frame)
    sess = frame.groupby("session")[["orb_width", "atr"]].last()  # vor range_end ist orb_width NaN
    width = (sess["orb_width"] / sess["atr"]).replace([np.inf, -np.inf], np.nan)
    neutral = (bias == 0).astype(float)

    rows = []
    for (name, a, b) in [(str(y), f"{y}-01-01", f"{y + 1}-01-01") for y in range(2016, 2026)] + \
            [("2026 bis 09", "2026-01-01", "2026-10-01")] + [(f"Periode {p[0]}", p[1], p[2]) for p in PERIODS]:
        sl = lambda s: s[(s.index >= a) & (s.index < b)]  # noqa: E731
        im_b, im_t, im_n = ols_t(sl(r_last), sl(r_first))
        tr_b, tr_t, _ = ols_t(sl(r_sess), sl(r_sess.shift(1)))
        rn, rt = sl(r_neutral), sl(r_trend)
        rows.append({"instrument": inst, "uhr": clock, "zeitraum": name,
                     "ribbon_spread": rn.mean() - rt.mean() if len(rn) and len(rt) else np.nan,
                     "r_neutral": rn.mean(), "n_neutral": len(rn), "r_trend": rt.mean(), "n_trend": len(rt),
                     "folgequote": sl(ft).mean(), "im_beta": im_b, "im_t": im_t, "tage": im_n,
                     "trend_beta": tr_b, "trend_t": tr_t,
                     "range_atr": sl(width).median(), "anteil_neutral": sl(neutral).mean()})
    return pd.DataFrame(rows)


def main() -> int:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    plan = [("OIL", "index"), ("OIL", "oel"), ("SP500", "index"), ("NASDAQ", "index")]

    perf_rows, diag, trades, daily = [], [], {}, {}
    for inst, clock in plan:
        print(f"lade {inst} ({clock}-Uhr) ...", flush=True)
        frames, sessions, bias, m1 = load(inst, clock)
        res = {}
        for cname, cfg in CONFIGS.items():
            set_clock(clock)
            r, c = run_config(frames, sessions, bias, inst, cfg)
            res[cname] = (r, c)
            trades[(inst, clock, cname)] = r
            for per, m in by_period(r, c).items():
                perf_rows.append({"instrument": inst, "uhr": clock, "konfig": cname, "periode": per, **m})
        diag.append(diagnostics(inst, frames[1], bias, m1, clock, res["SP500-Gewinner"][0], res["mit Trend"][0]))
        if clock == "index":
            daily[inst] = session_points(m1, "index").pipe(lambda p: p["close"] / p["open"] - 1)

    perf = pd.DataFrame(perf_rows)
    diag = pd.concat(diag, ignore_index=True)

    # Oel-spezifisch: EIA-Mittwoch (10:30 NY) gegen andere Tage, Oel-Uhr, ungefiltert
    r = trades[("OIL", "oel", "ungefiltert")]
    wed = r.index.dayofweek == 2
    eia = pd.DataFrame([{"tag": "Mittwoch (EIA)" if wd else "andere Tage", "periode": per,
                         **metrics(r[(r.index >= a) & (r.index < b) & (wed == wd)])}
                        for wd in (True, False) for per, a, b in PERIODS])

    # Gleichlauf: Tageskorrelation der Sitzungsrenditen und der ORB-Ergebnisse
    corr_rows = []
    for name, a, b in PERIODS:
        sl = lambda s: s[(s.index >= a) & (s.index < b)]  # noqa: E731
        d = pd.concat([sl(daily["OIL"]), sl(daily["SP500"]), sl(daily["NASDAQ"])], axis=1, keys=["OIL", "SP500", "NASDAQ"]).dropna()
        o = trades[("OIL", "index", "ungefiltert")].groupby(lambda t: t.normalize()).sum()
        s = trades[("SP500", "index", "ungefiltert")].groupby(lambda t: t.normalize()).sum()
        j = pd.concat([sl(o), sl(s)], axis=1, keys=["o", "s"]).dropna()
        corr_rows.append({"periode": name, "korr_sitzung_oil_sp500": d["OIL"].corr(d["SP500"]),
                          "korr_sitzung_oil_nasdaq": d["OIL"].corr(d["NASDAQ"]),
                          "korr_orb_r_oil_sp500": j["o"].corr(j["s"]), "gemeinsame_orb_tage": len(j)})
    corr = pd.DataFrame(corr_rows)

    # Lock: Konfigurationen waren vorab fest; zaehlen, einfrieren, OOS + Tresor oeffnen
    frozen = {"configs": CONFIGS, "clocks": CLOCKS, "spread_bps_oil": SPREAD_BPS["OIL"], "min_price": MIN_PRICE}
    if lk.trials == 0:
        lk.log_trials(len(CONFIGS) * len(CLOCKS), note="OIL: 4 feste ORB-Konfigs x 2 Uhren, keine Auswahl (Kontrollgruppe)")
    h = config_hash(frozen)
    lk.freeze(frozen)
    for stage in ("oos", "tresor"):
        lk.unseal(stage, h)

    perf.to_csv(RES / "oel_vergleich_perf.csv", index=False)
    diag.to_csv(RES / "oel_vergleich_mechanik.csv", index=False)
    eia.to_csv(RES / "oel_vergleich_eia.csv", index=False)
    corr.to_csv(RES / "oel_vergleich_korrelation.csv", index=False)
    with open(RES / "oel_vergleich_meta.json", "w", encoding="utf-8") as f:
        json.dump({"lock": STRATEGY, "hash": h, **frozen}, f, indent=2, ensure_ascii=False)

    pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 300)
    cols = ["instrument", "uhr", "konfig", "periode", "n", "pf", "avg", "t", "sum", "avg_cost_x2", "cost_r", "win"]
    print("\n=== ORB-Ergebnis (R, nach Kosten) ===")
    print(perf[cols].round(3).to_string(index=False))
    print("\n=== Mechanik je Jahr ===")
    print(diag.round(3).to_string(index=False))
    print("\n=== Oel: EIA-Mittwoch (Oel-Uhr, ungefiltert) ===")
    print(eia[["tag", "periode", "n", "avg", "t", "pf"]].round(3).to_string(index=False))
    print("\n=== Gleichlauf ===")
    print(corr.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
