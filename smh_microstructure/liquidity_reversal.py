"""K3 -- Liquiditaets-Reversal (Nagel 2012; intraday: Grant/Wolf/Yu 2005,
Heston/Korajczyk/Sadka 2010).

Mechanismus: Wer sofort handeln will (Margin-Calls, Risikoabbau, grosse
Market-Orders), verschiebt den Kurs ueber seinen fairen Wert. Liquiditaets-
geber nehmen die Gegenseite nur gegen eine Praemie: der Kurs kehrt danach
teilweise zurueck. Die Praemie steigt, wenn Liquiditaet knapp ist (hohe
Volatilitaet, Nagel 2012). Ohne News ist die Bewegung eher Liquiditaets-
druck als Information -- deshalb News-Tage raus.
Wer verliert: der ungeduldige Grosshaendler, der Sofortigkeit kauft.

Regel: zu jeder halben Stunde 10:30-15:00 NY die Rendite der letzten 30 Min
gegen ihre eigene Streuung (letzte 20 Handelstage, gleiche Fenster) messen.
|z| >= 2 -> eine Minute spaeter gegen die Bewegung einsteigen, 30 Min halten.
Eroeffnung (Open-Print) und letzte halbe Stunde (MOC/Gamma) sind bewusst
ausgeschlossen. Kein US-Release-Tag (CPI, NFP, Retail, GDP), kein FOMC-Tag.
Variante high_vol: nur wenn die 20-Tage-Vola ueber ihrem 1-Jahres-Median liegt.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from smh_microstructure.costs import roundtrip_cost


@dataclass(frozen=True)
class Config:
    window_min: int = 30
    first_check: str = "10:30"
    last_check: str = "15:00"
    z: float = 2.0
    lookback_days: int = 20
    hold_min: int = 30
    high_vol_only: bool = False
    skip_news: bool = True
    cost_mult: float = 1.0

    def as_dict(self):
        return asdict(self)


def _news_days() -> set:
    from bond_yield_indicator.calendar import get_meetings
    from news_calendar.fred_releases import fetch_all_us_release_dates
    d = set(fetch_all_us_release_dates("2018-01-01", "2026-10-07").date)
    return d | set(get_meetings("FOMC").date)


def run(df: pd.DataFrame, sym: str, cfg: Config) -> pd.DataFrame:
    ny = df.tz_convert("America/New_York")
    ny = ny[ny.index.dayofweek < 5]
    opens = ny["open"]
    day = ny.index.normalize()
    # Pruefzeitpunkte je Tag
    h0, m0 = map(int, cfg.first_check.split(":"))
    h1, m1 = map(int, cfg.last_check.split(":"))
    checks = pd.timedelta_range(pd.Timedelta(hours=h0, minutes=m0), pd.Timedelta(hours=h1, minutes=m1),
                                freq=f"{cfg.window_min}min")
    w, hold = pd.Timedelta(minutes=cfg.window_min), pd.Timedelta(minutes=cfg.hold_min)
    one = pd.Timedelta(minutes=1)

    # Tagesrenditen (16:00-Schluss) fuer das Vola-Regime
    close16 = ny["close"].between_time("15:59", "15:59")
    close16.index = close16.index.normalize()
    dret = np.log(close16).diff()
    vol20 = dret.rolling(20).std()
    vol_med = vol20.rolling(250, min_periods=120).median()
    high_vol = (vol20 > vol_med).shift(1)  # Vortageswert -> kein Blick in die Zukunft

    news = _news_days() if cfg.skip_news else set()
    recs = []
    for d in pd.DatetimeIndex(day.unique()):
        for c in checks:
            t = d + c
            p_now, p_then = opens.get(t, np.nan), opens.get(t - w, np.nan)
            p_in, p_out = opens.get(t + one, np.nan), opens.get(t + one + hold, np.nan)
            recs.append((d, t, p_then, p_now, p_in, p_out))
    ev = pd.DataFrame(recs, columns=["day", "t", "p_then", "p_now", "p_in", "p_out"]).dropna()
    ev["r"] = np.log(ev["p_now"] / ev["p_then"])
    # Streuung aus den letzten `lookback_days` Tagen (ohne den aktuellen Tag)
    daily_sq = ev.groupby("day")["r"].agg(lambda x: float((x ** 2).sum())).rename("sq")
    daily_n = ev.groupby("day")["r"].size().rename("cnt")
    roll = (daily_sq.rolling(cfg.lookback_days).sum() / daily_n.rolling(cfg.lookback_days).sum()) ** 0.5
    ev["sigma"] = ev["day"].map(roll.shift(1))
    ev["z"] = ev["r"] / ev["sigma"]
    sig = ev[ev["z"].abs() >= cfg.z].copy()
    if cfg.skip_news:
        sig = sig[~sig["day"].dt.date.isin(news)]
    if cfg.high_vol_only:
        sig = sig[sig["day"].map(high_vol).fillna(False).astype(bool)]
    rows, busy_until = [], None
    for r in sig.itertuples():
        if busy_until is not None and r.t < busy_until:
            continue
        side = -np.sign(r.r)
        cost_bps = roundtrip_cost(sym, r.p_in, cfg.cost_mult) / r.p_in * 1e4
        pnl = side * (r.p_out - r.p_in) / r.p_in * 1e4 - cost_bps
        rows.append({"sym": sym, "entry_time": (r.t + one).tz_convert("UTC"), "z": r.z, "side": int(side),
                     "pnl_bps": pnl, "cost_bps": cost_bps})
        busy_until = r.t + one + hold
    out = pd.DataFrame(rows)
    if len(out):
        out["entry_time"] = pd.to_datetime(out["entry_time"], utc=True)
    return out


def run_all(data: dict[str, pd.DataFrame], cfg: Config) -> pd.DataFrame:
    parts = [p for p in (run(df, s, cfg) for s, df in data.items()) if len(p)]
    if not parts:
        return pd.DataFrame(columns=["sym", "entry_time", "pnl_bps"])
    return pd.concat(parts).sort_values("entry_time").reset_index(drop=True)
