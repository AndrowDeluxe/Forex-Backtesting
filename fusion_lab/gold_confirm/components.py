"""Bausteine des Gold-Confirmation-Scores. Jede Funktion liefert eine Tagesreihe (Handelstage des
XAUUSD-Spots), deren Wert am Tag t nur aus Informationen besteht, die bis Tagesende t veroeffentlicht
waren. Ein Signal vom Tag t wird fruehestens am Tag t+1 gehandelt (das macht der Backtest).

Rohwert: bullisch = positiv. `normalize` macht daraus 0..1 per gleitendem Perzentil (3 Jahre,
mind. 1 Jahr Historie), nur Vergangenheit. Bereits begrenzte Bausteine (`BOUNDED`) werden linear
von [-1, 1] auf [0, 1] gebracht.

Veroeffentlichungs-Lags:
  CFTC   Stichtag Dienstag, Veroeffentlichung Freitag 15:30 ET -> gilt ab Freitag (report + 3 T)
  GLD    Bestand Tag t erscheint abends/naechster Morgen -> +1 Handelstag
  FRED   DFII10/T10YIE/DGS2/EPU/DEXCHUS erscheinen am Folgetag -> +1 Handelstag
  GVZ    Indexschluss Tag t (Marktdaten) -> kein Lag
  IMF    Monatswert erscheint mit ~4-8 Wochen Verzug -> gilt ab Monatsende + 2 Monate
  SGE    PM-Benchmark 14:15 Peking (06:15 UTC) -> am selben Tag bekannt
  yf     Schlusskurse US-Handelstag t -> kein Lag
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from fusion_lab.gold_confirm.data import load

WINDOW, MIN_OBS = 756, 252
BOUNDED = {"f_oi"}
OZ_PER_G = 1 / 31.1034768

# Baustein -> (Block, Beschreibung, PDF-Bezug)
CATALOG = {
    "f_oi":       ("FLOW", "COMEX Preis x OI x Volumen (woechentlich, CFTC-OI)", "2 COMEX Preis+OI+Volumen"),
    "f_options":  ("FLOW", "GVZ-Aenderung in Preisrichtung (Skew-Proxy)", "3 Gold Options"),
    "f_etf":      ("FLOW", "GLD-Bestand Aenderung 20 T in %", "4 ETF Flows"),
    "f_mm":       ("FLOW", "Managed Money netto, Aenderung 4 Berichte / OI", "5 CFTC Managed Money"),
    "f_other":    ("FLOW", "Other Reportables netto, Aenderung 4 Berichte / OI", "5 weitere Tradergruppen"),
    "p_china":    ("PHYSICAL", "SGE-PM gegen XAUUSD in %, Mittel 10 T", "6 Shanghai-London Premium"),
    "p_cb":       ("PHYSICAL", "Zentralbanken netto, 12 Monate, Lag 2 Monate", "8 Zentralbankkaeufe"),
    "r_absorb":   ("PRICE", "Gold-Rendite minus USD/Realzins-Erwartung, 5 T", "1 Absorption"),
    "r_relstr":   ("PRICE", "dito ueber 20 T (relative Staerke)", "1 Relative Strength"),
    "r_shock":    ("PRICE", "Reaktion an Zins-Schocktagen gegen die Erwartung", "1 News Reaction"),
    "x_gdx":      ("PRICE", "GDX/GLD 20 T (Miner bestaetigen)", "10 GDX"),
    "x_silver":   ("PRICE", "Silber/Gold 20 T (Ratio faellt = bullisch)", "10 Silver / Gold-Silver-Ratio"),
    "x_copper":   ("PRICE", "Gold/Kupfer 20 T (defensiver Shift)", "10 Gold/Copper"),
    "m_real":     ("MACRO", "Realzins 10J, minus Aenderung 20 T", "Macro Real Yields"),
    "m_usd":      ("MACRO", "DXY, minus Rendite 20 T", "Macro USD"),
    "m_infl":     ("MACRO", "Breakeven 10J, Aenderung 20 T", "Macro Inflation"),
    "m_geo":      ("MACRO", "EPU-Index 20 T gegen 120 T", "Macro Geopolitik/Unsicherheit"),
}
DROPPED = {
    "Options-Skew / Risk Reversals / Strike-OI": "keine freie Historie (CME/CVOL kostenpflichtig) -> GVZ-Proxy",
    "COMEX-OI und -Volumen taeglich": "OI nur woechentlich frei (CFTC); Tagesvolumen GC=F nur als Verstaerker",
    "India Premium": "keine freie Zeitreihe",
    "COMEX Warehouse Stocks / Deliveries": "CME veroeffentlicht nur den aktuellen Tag, keine freie Historie",
    "Futures Basis / Term Structure": "Yahoo nur Endloskontrakt, Schlusszeiten passen nicht zum Spot; GOFO seit 2015 eingestellt",
    "SGE Withdrawals, LBMA Vaults, Lease Rates, GLD-Optionen": "keine freie Historie",
}


def _days(spot: pd.DataFrame) -> pd.DatetimeIndex:
    """Handelstage = Spot-Index, verlaengert um Werktage bis zum juengsten FRED/yfinance-Wert.
    Grund (15.11.2026): der Dukascopy-D1-Cache endet am Dateinamen-Stichtag, der MACRO-Block
    braucht aber nur FRED + yfinance und soll live taeglich weiterlaufen."""
    ends = [spot.index.max()]
    for name in ("fred", "yf"):
        try:
            ends.append(load(name).dropna(how="all").index.max())
        except Exception:  # noqa: BLE001 -- fehlende Quelle: nur nicht verlaengern
            pass
    last = max(ends)
    if last <= spot.index.max():
        return spot.index
    return spot.index.append(pd.bdate_range(spot.index.max() + pd.Timedelta(days=1), last))


def _on(series: pd.Series, days: pd.DatetimeIndex, lag_days: int = 0) -> pd.Series:
    """Reihe auf Handelstage legen: letzter bekannter Wert, optional `lag_days` Handelstage spaeter."""
    s = series.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    out = s.reindex(days.union(s.index)).ffill().reindex(days)
    return out.shift(lag_days) if lag_days else out


def _avail(series: pd.Series, avail_dates: pd.Series, days: pd.DatetimeIndex) -> pd.Series:
    """Werte gelten ab ihrem Veroeffentlichungstag (inklusive)."""
    s = pd.Series(series.values, index=pd.DatetimeIndex(avail_dates)).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(days.union(s.index)).ffill().reindex(days)


def normalize(raw: pd.Series, bounded: bool = False) -> pd.Series:
    if bounded:
        return ((raw.clip(-1, 1) + 1) / 2).where(raw.notna())
    def pct(w: np.ndarray) -> float:
        return (w[:-1] < w[-1]).mean() + 0.5 * (w[:-1] == w[-1]).mean()
    valid = raw.dropna()
    out = valid.rolling(WINDOW, min_periods=MIN_OBS).apply(pct, raw=True)
    return out.reindex(raw.index)


# ---------------------------------------------------------------- Rohwerte

def _cftc(days: pd.DatetimeIndex, market: str = "GOLD") -> pd.DataFrame:
    c = load("cftc")
    c = c[c["market"] == market].sort_values("report").drop_duplicates("report")
    c["avail"] = c["report"] + pd.Timedelta(days=3)
    c["mm"] = c["m_money_positions_long_all"] - c["m_money_positions_short_all"]
    c["other"] = c["other_rept_positions_long"] - c["other_rept_positions_short"]
    c["oi"] = c["open_interest_all"]
    return c.set_index("avail")[["report", "mm", "other", "oi"]]


def raw_components(market: str = "GOLD") -> pd.DataFrame:
    """Alle Rohwerte fuer Gold (market='SILVER' nur fuer den Uebertragbarkeits-Check der CFTC-Bausteine)."""
    spot = load("spot")
    days = _days(spot)
    yf, fred = load("yf"), load("fred")
    out = pd.DataFrame(index=days)

    # --- FLOW
    c = _cftc(days, market)
    gc = yf["gc_close"].dropna()
    px_report = gc.reindex(gc.index.union(c["report"])).ffill().reindex(c["report"]).values
    wk = pd.DataFrame({"px": px_report, "oi": c["oi"].values}, index=c.index)
    dpx, doi = np.sign(wk["px"].diff()), np.sign(wk["oi"].diff())
    # PDF-Tabelle: P+ OI+ = neue Longs (+1), P- OI+ = neue Shorts (-1), P+ OI- = Short-Covering (+0,5),
    # P- OI- = Long-Liquidation (-0,5)
    cls = np.where(doi > 0, dpx, 0.5 * dpx)
    vol = yf["gc_volume"].replace(0, np.nan)
    vol_z = (np.log(vol) - np.log(vol).rolling(60).mean()) / np.log(vol).rolling(60).std()
    vol_w = _on(vol_z.rolling(5).mean(), pd.DatetimeIndex(c["report"]))  # Volumen der Berichtswoche
    amp = np.where(vol_w.values > 0, 1.0, 0.6)  # Volumen bestaetigt -> volles Gewicht
    out["f_oi"] = _on(pd.Series(cls * amp, index=c.index), days)
    gvz = fred["gvz"]
    ret20_us = np.log(gc).diff(20)
    out["f_options"] = _on(np.sign(ret20_us).reindex(gvz.index).ffill() * gvz.diff(20) / gvz.shift(20), days)
    gld = load("gld")["tonnes"]
    out["f_etf"] = _on(gld.pct_change(20), days, lag_days=1)
    out["f_mm"] = _on(c["mm"].diff(4) / c["oi"], days)
    out["f_other"] = _on(c["other"].diff(4) / c["oi"], days)

    # --- PHYSICAL
    sge = load("sge")["pm"]
    cny = _on(fred["usdcny"], sge.index, lag_days=0).shift(1)  # Vortageskurs, am SGE-Tag bekannt
    spot_close = spot["Close"]
    sge_usd = sge * (1 / OZ_PER_G) / cny  # CNY/g -> USD/oz
    # Spot-Vergleich: Vortagesschluss + halber Tag ist nicht verfuegbar; Tagesschluss Vortag als Referenz,
    # Premium = Niveauabweichung, Tagesbewegung mittelt sich ueber 10 T heraus
    prem = (sge_usd / spot_close.reindex(sge.index).ffill().shift(1) - 1)
    out["p_china"] = _on(prem.rolling(10, min_periods=5).mean(), days)
    imf = load("imf")
    piv = imf.pivot_table(index="month", columns="country", values="moz").sort_index()
    piv = piv.drop(columns=[c_ for c_ in piv.columns if not re.fullmatch(r"[A-Z]{3}", str(c_))], errors="ignore")
    chg = piv.diff()  # nur Laender mit beiden Monaten -> NaN faellt in der Summe weg
    chg = chg.clip(-5, 5)  # Umbuchungen/Datenbrueche (> 155 t in einem Monat) daempfen
    net12 = chg.sum(axis=1, min_count=1).rolling(12, min_periods=9).sum()
    avail = net12.index + pd.offsets.MonthEnd(0) + pd.offsets.MonthEnd(2)
    out["p_cb"] = _avail(net12, avail, days)

    # --- PRICE RESPONSE
    g = np.log(spot_close)
    dxy = np.log(_on(yf["dxy_close"], days))
    real = _on(fred["real10"], days, lag_days=1)
    rg, rd, rr = g.diff(), dxy.diff(), real.diff()
    X = pd.concat([rd, rr], axis=1, keys=["d", "r"])
    beta = _rolling_beta(rg, X, 250)
    resid = rg - (beta * X).sum(axis=1, min_count=2)
    out["r_absorb"] = resid.rolling(5).sum()
    out["r_relstr"] = resid.rolling(20).sum()
    us2 = _on(fred["us2y"], days, lag_days=0)  # 2J-Rendite Tag t: Schlusswert, nur fuer die Schockerkennung
    d2 = us2.diff()
    shock = d2.abs() > 2.0 * d2.abs().rolling(250).median().shift(1).clip(lower=0.01)
    # Erwartung: Rendite rauf -> Gold runter. Reaktion gegen die Erwartung (Gold steigt trotz Renditeanstieg)
    react = (-np.sign(d2) * np.sign(rg)).where(shock)  # +1 erwartet, -1 dagegen
    surprise = (np.sign(rg) * (react < 0)).where(shock)  # +1 bullishe Absorption, -1 bearishe Schwaeche
    out["r_shock"] = surprise.ewm(halflife=10, ignore_na=True).mean().where(shock.cumsum() > 0)
    # FRED-2J kommt am Folgetag -> Baustein erst einen Tag spaeter nutzbar
    out["r_shock"] = out["r_shock"].shift(1)
    gdx, gldp = _on(yf["gdx_close"], days), _on(yf["gld_close"], days)
    out["x_gdx"] = np.log(gdx / gldp).diff(20)
    si, hg, gcd = _on(yf["si_close"], days), _on(yf["hg_close"], days), _on(gc, days)
    out["x_silver"] = np.log(si / gcd).diff(20)
    out["x_copper"] = np.log(gcd / hg).diff(20)

    # --- MACRO
    out["m_real"] = -real.diff(20)
    out["m_usd"] = -dxy.diff(20)
    out["m_infl"] = _on(fred["be10"], days, lag_days=1).diff(20)
    epu = _on(fred["epu"], days, lag_days=1)
    out["m_geo"] = epu.rolling(20).mean() / epu.rolling(120).mean() - 1
    return out


def _rolling_beta(y: pd.Series, X: pd.DataFrame, n: int) -> pd.DataFrame:
    """OLS-Betas aus den n Tagen VOR t (t selbst nicht in der Schaetzung)."""
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    cols = list(X.columns)
    betas = np.full((len(df), len(cols)), np.nan)
    v = df.values
    for i in range(n, len(df)):
        w = v[i - n:i]
        xx = np.column_stack([np.ones(n), w[:, 1:]])
        coef, *_ = np.linalg.lstsq(xx, w[:, 0], rcond=None)
        betas[i] = coef[1:]
    return pd.DataFrame(betas, index=df.index, columns=cols).reindex(y.index).ffill()



def components(market: str = "GOLD") -> pd.DataFrame:
    raw = raw_components(market)
    return pd.DataFrame({k: normalize(raw[k], k in BOUNDED) for k in raw.columns}, index=raw.index)
