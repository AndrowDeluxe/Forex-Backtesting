"""Welche Wirkketten funktionieren? Rangliste aller Ketten aus fusion_lab/macro_agent/chains.py
(Nutzerauftrag 24.11.2026: "mit den Daten aus dem Fact Sheet in die Recherche der am besten
funktionierenden Wirkketten").

Vorab festgelegt (24.11.2026, vor dem ersten Lauf):
  Split IS 2007-01-01 .. 2016-12-31, OOS .. 2026-05-24, Tresor 25.05.-24.11.2026 (bleibt zu).
  Ketten-Logik unveraendert aus chains.py (gleiche Schritte und Schwellen wie live), Messwerte als
  Tagesreihen point-in-time nachgebaut (Veroeffentlichungsverzug siehe LAG). Zwei Arme je Kette:
  "aktiv" (alle Schritte erfuellt, Stopp nicht) und "umgekehrt" (alle Umkehr-Schritte erfuellt).
  Je Arm und Asset:
    Vorlauf:    Log-Rendite vom Schluss t+1 bis t+1+h (h = 5, 20), mit der erwarteten Richtung
                multipliziert; y = a + b*Zustand, b = Abstand zu allen anderen Tagen (nimmt Drift raus),
                HAC (Newey-West, Lags = h).
    Gleichlauf: dieselbe Regression mit der Rendite der letzten 20 Tage bis t (beschreibt, ob die Kette
                die Bewegung erklaert; kein Signal).
  Urteil je Arm (Mehrheit der Assets):
    "traegt (Vorlauf)"         b(20) > 0 mit t >= 2 im IS und b(20) > 0 mit t >= 1 im OOS
    "Gleichlauf, kein Vorlauf"  sonst, wenn Gleichlauf b > 0 mit t >= 2 im IS und OOS
    "traegt nicht"              sonst
    "zu wenig Daten"           < 40 Zustandstage im IS oder OOS
  Nicht historisch testbar: Ketten mit Schlagzeilen-Schritt (News erst seit 12.11.2026) -> nur Ledger.
  Abweichungen vom Live-Messwert (dokumentiert in der Ausgabe): GDPNow -> letztes BIP-Q/Q (ALFRED-frei,
  mit Verzug), Fed-Kanal -> rollierendes 26-W-Beta 2J auf Brent >= 1,5x Median der Vorjahre,
  CA-Pricing -> entfaellt (oel_cad nur mit Brent), OAT-Bund -> OECD-Monatswerte.
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_lock import Lock  # noqa: E402
from fusion_lab.g8.data import fetch_fred  # noqa: E402
from fusion_lab.macro_agent import chains, geo_framework, panels  # noqa: E402
from fusion_lab.macro_data import sources  # noqa: E402

OUT = ROOT / "fusion_lab" / "data" / "macro_agent" / "wirkketten_ranking.csv"
LOCK = Lock("wirkketten_ranking_v1")
LOCK.register_split("2007-01-01", "2016-12-31", "2026-05-24", "2026-11-24")
HOR = [5, 20]
MIN_DAYS = 40
NEWS_CHAINS = {c.id for c in chains.CHAINS
               if any(s.zeigt.startswith("lage_") for s in c.schritte)}
# Tage zwischen Stichtag der Reihe und Bekanntwerden
LAG = {"WALCL": 1, "WTREGEN": 1, "RRPONTSYD": 1, "ICSA": 5, "SAHMREALTIME": 35, "GDPC1": 120,
       "IRLTLT01FRM156N": 45, "IRLTLT01DEM156N": 45, "monthly_geo": 45, "IOER": 1, "IORB": 1, "SOFR": 1}


def fred(series: str) -> pd.Series:
    s = fetch_fred(series).dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None) + pd.Timedelta(days=LAG.get(series, 0))
    return s


def on_days(s: pd.Series, days: pd.DatetimeIndex) -> pd.Series:
    return s.reindex(s.index.union(days)).ffill().reindex(days)


def acm() -> pd.DataFrame:
    r = requests.get(sources.ACM_URL, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    d = pd.read_excel(io.BytesIO(r.content), sheet_name="ACM Daily")
    d.index = pd.to_datetime(d["DATE"], format="%d-%b-%Y")
    return d[["ACMTP10", "ACMRNY10"]]


def jgb10() -> pd.Series:
    sources.START = "2002-01-01"
    df = sources.fetch_yields_mof()
    s = df[df["key"] == "JP.10y"].set_index("date")["value"]
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def move() -> pd.Series:
    import yfinance as yf
    c = yf.download("^MOVE", start="2002-01-01", progress=False, auto_adjust=True)["Close"]
    c = (c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c).dropna()
    c.index = pd.to_datetime(c.index).tz_localize(None)
    return c


def chg(s: pd.Series, n: int, scale: float = 100.0) -> pd.Series:
    return (s - s.shift(n)) * scale


def ret(s: pd.Series, n: int) -> pd.Series:
    return (s / s.shift(n) - 1) * 100


def fed_channel(h: pd.DataFrame) -> pd.Series:
    """Rollierendes 26-W-Beta d2J (bp) auf Brent (%) gegen den Median der Betas bis vor einem Jahr."""
    w = h[["brent", "us_2y"]].resample("W-FRI").last()
    x, y = np.log(w["brent"]).diff() * 100, w["us_2y"].diff() * 100
    beta = x.rolling(26).cov(y) / x.rolling(26).var()
    ref = beta.shift(52).expanding(104).median()
    return ((beta >= 1.5 * ref) & (beta > 0)).where(beta.notna() & ref.notna())


def build_measures() -> tuple[pd.DataFrame, pd.DataFrame]:
    h = geo_framework.history().loc["2003-01-01":]
    days = pd.bdate_range("2004-01-01", "2026-11-24")
    d = h.reindex(days).ffill(limit=5)
    m = pd.DataFrame(index=days)
    m["brent_20d"] = ret(d["brent"], 20)
    m["brent_vs_20d"] = (d["brent"] / d["brent"].rolling(20).mean() - 1) * 100
    m["us_2y_20d_bp"] = chg(d["us_2y"], 20)
    m["breakeven_20d_bp"] = chg(d["breakeven_10y"], 20)
    m["vix"], m["vix_20d"] = d["vix"], chg(d["vix"], 20, 1)
    m["spx_5d"], m["spx_20d"], m["ndx_20d"] = ret(d["spx"], 5), ret(d["spx"], 20), ret(d["ndx"], 20)
    m["kupfer_20d"], m["kospi_20d"] = ret(d["kupfer"], 20), ret(d["kospi"], 20)
    m["hyg_ief_20d"] = ret(d["hyg"] / d["ief"], 20)
    hy = fred("BAMLH0A0HYM2")
    m["hy_20d_bp"] = chg(on_days(hy, days), 20)
    m["fwd_5y5y_1w_bp"] = chg(on_days(fred("T5YIFR"), days), 5)
    for name in ("korea_exporte", "china_importpreise"):
        mon = h[name].dropna()
        yoy = (100 * (mon / mon.shift(12) - 1)).dropna()
        yoy.index = yoy.index + pd.Timedelta(days=LAG["monthly_geo"])
        m[f"{name}_yoy"] = on_days(yoy, days)
        m[f"{name}_yoy_3m"] = on_days(yoy - yoy.shift(3), days)
    spread = (fred("IRLTLT01FRM156N") - fred("IRLTLT01DEM156N")).dropna() * 100
    m["oat_bund_bp"] = on_days(spread, days)
    m["oat_bund_20d_bp"] = on_days(spread - spread.shift(1), days)  # Monatsaenderung als Naeherung
    fk = fed_channel(h)
    m["fed_kanal"] = on_days(fk.dropna().astype(float), days).map({1.0: True, 0.0: False})
    # Education-Ketten
    m["real_10y"] = d["real_10y"]
    m["real_10y_20d_bp"] = chg(d["real_10y"], 20)
    m["usdjpy_20d"] = ret(d["USDJPY"], 20)
    us10 = on_days(fred("DGS10"), days)
    m["us_kurve_20d_bp"] = chg(us10 - d["us_2y"], 20)
    m["ust_jgb_20d_bp"] = chg(us10 - on_days(jgb10(), days), 20)
    a = acm().reindex(days).ffill(limit=5)
    m["praemie_20d_bp"] = chg(a["ACMTP10"], 20)
    m["praemie_minus_erwartung_bp"] = m["praemie_20d_bp"] - chg(a["ACMRNY10"], 20)
    walcl, tga, rrp = fred("WALCL") / 1000, fred("WTREGEN") / 1000, fred("RRPONTSYD")
    net = (walcl - on_days(tga, walcl.index) - on_days(rrp, walcl.index).fillna(0)).dropna()
    m["net_liq_13w"] = on_days(net - net.shift(13), days)
    iorb = pd.concat([fred("IOER").loc[:"2021-07-28"], fred("IORB")])
    m["sofr_iorb_bp"] = (on_days(fred("SOFR"), days) - on_days(iorb, days)) * 100
    m["move"] = on_days(move(), days)
    claims = fred("ICSA") / 1000
    c4 = claims.rolling(4).mean()
    m["erstantraege_vs_tief_pct"] = on_days(100 * (c4 / claims.rolling(52).min() - 1), days)
    m["sahm"] = on_days(fred("SAHMREALTIME"), days)
    gdp = fetch_fred("GDPC1").dropna()
    gq = ((gdp / gdp.shift(1)) ** 4 - 1) * 100
    gq.index = pd.to_datetime(gq.index) + pd.Timedelta(days=LAG["GDPC1"])
    m["gdpnow"] = on_days(gq, days)
    ev = panels.surprise_events(pd.read_parquet(panels.FF_HISTORY))
    us = ev[ev["land"] == "US"].groupby("date")["z"].sum()
    us = us.reindex(us.index.union(days)).fillna(0.0).rolling("60D").sum().reindex(days)
    m["usd_ueberraschung"] = us.where(days >= ev.loc[ev["land"] == "US", "date"].min() + pd.Timedelta(days=60))
    return m, d


# Historisch nicht nachbaubare Schritte (vorab festgelegt, siehe Kopf): werden ausgelassen
SKIP = {"oel_cad": {"ca_pricing_1w_bp"}}


def states(m: pd.DataFrame) -> dict[str, pd.DataFrame]:
    rows = m.to_dict("index")
    out = {}
    for c in chains.CHAINS:
        act, rev = [], []
        steps_c = [s for s in c.schritte if s.zeigt not in SKIP.get(c.id, set())]
        umk_c = [s for s in c.umkehr or [] if s.zeigt not in SKIP.get(c.id, set())]
        for day, r in rows.items():
            r = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()}
            st = [s.check(r) for s in steps_c]
            stop = c.stopp.check(r)
            known = all(v is not None for v in st)
            act.append(float(all(st) and not stop) if known else np.nan)
            if umk_c:
                rv = [s.check(r) for s in umk_c]
                rev.append(float(all(rv)) if all(v is not None for v in rv) else np.nan)
        out[c.id] = pd.DataFrame({"aktiv": act, **({"umgekehrt": rev} if c.umkehr else {})}, index=m.index)
    return out


def reg(y: pd.Series, s: pd.Series, lags: int) -> tuple[float, float, int]:
    d = pd.concat([y.rename("y"), s.rename("s")], axis=1).dropna()
    n = int(d["s"].sum())
    if n < MIN_DAYS or n == len(d):
        return np.nan, np.nan, n
    fit = sm.OLS(d["y"], sm.add_constant(d["s"])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.params["s"]), float(fit.tvalues["s"]), n


def verdict(rows: list[dict]) -> str:
    if not rows or any(r["n_is"] < MIN_DAYS or r["n_oos"] < MIN_DAYS for r in rows):
        return "zu wenig Daten"
    half = len(rows) / 2  # Mehrheit = mehr als die Haelfte (vorab festgelegt)
    lead = sum(r["b20_is"] > 0 and r["t20_is"] >= 2 and r["b20_oos"] > 0 and r["t20_oos"] >= 1 for r in rows)
    if lead > half:
        return "trägt (Vorlauf)"
    co = sum(r["bg_is"] > 0 and r["tg_is"] >= 2 and r["bg_oos"] > 0 and r["tg_oos"] >= 2 for r in rows)
    return "Gleichlauf, kein Vorlauf" if co > half else "trägt nicht"


def main() -> None:
    m, d = build_measures()
    st = states(m)
    logp = np.log(d)
    res, trials = [], 0
    for c in chains.CHAINS:
        if c.id in NEWS_CHAINS:
            res.append({"kette": c.id, "arm": "–", "asset": "–", "urteil": "nur vorwärts (Schlagzeilen)"})
            continue
        for arm, sign_arm in (("aktiv", 1), ("umgekehrt", -1)):
            if arm not in st[c.id]:
                continue
            state = st[c.id][arm]
            arm_rows = []
            for asset, sign in c.assets.items():
                col = asset if asset in logp else None
                if col is None:
                    continue
                s = sign * sign_arm
                row = {"kette": c.id, "arm": arm, "asset": asset, "richtung": s}
                for h in HOR:
                    y = s * (logp[col].shift(-(1 + h)) - logp[col].shift(-1)) * 100
                    for name, sub in (("is", LOCK.is_only), ("oos", LOCK.oos_only)):
                        b, t, n = reg(sub(y), sub(state), h)
                        row[f"b{h}_{name}"], row[f"t{h}_{name}"], row[f"n_{name}"] = b, t, n
                    trials += 1
                yg = s * (logp[col] - logp[col].shift(20)) * 100
                for name, sub in (("is", LOCK.is_only), ("oos", LOCK.oos_only)):
                    row[f"bg_{name}"], row[f"tg_{name}"], _ = reg(sub(yg), sub(state), 20)
                arm_rows.append(row)
            v = verdict(arm_rows)
            for r in arm_rows:
                r["urteil"] = v
            res += arm_rows
    LOCK.log_trials(trials, "je Kette/Arm/Asset Vorlauf 5 und 20 T (Gleichlauf beschreibend, nicht gezaehlt)")
    df = pd.DataFrame(res)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.round(3).to_csv(OUT, index=False)
    pd.set_option("display.width", 250, "display.max_rows", 300)
    cols = ["kette", "arm", "asset", "n_is", "n_oos", "b20_is", "t20_is", "b20_oos", "t20_oos",
            "bg_is", "tg_is", "bg_oos", "tg_oos", "urteil"]
    print(df.reindex(columns=cols).round(2).to_string(index=False))
    print("\nUrteil je Kette und Arm:")
    print(df.groupby(["kette", "arm"])["urteil"].first().to_string())
    print(f"\nVersuche gezaehlt: {trials}")


if __name__ == "__main__":
    main()
