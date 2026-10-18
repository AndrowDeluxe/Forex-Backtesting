"""K4/K5 -- Dollar-W rund um die FX-Fixes (Krohn, Mueller & Whelan 2024, JF;
Bank-of-Canada-WP 2021-48), K4-Variante "breedon" nach Breedon & Ranaldo
(2013, SNB-WP 2011-04).

Mechanismus: Kunden fragen zu den Fixes (Tokio 9:55, EZB 14:15 Frankfurt,
London 16:00) unbedingt Dollar nach. Haendler bauen den Bestand VOR dem Fix
auf (Dollar steigt) und bauen ihn danach ab (Dollar faellt). Wer verliert:
wer zum Fix-Kurs handeln MUSS und den Lagerrisiko-Aufschlag der Haendler
bezahlt. Ergebnis: W-foermiges Dollar-Muster ueber den Tag.

Regel (Paper Tabelle IX, Zeiten in New York; hier in den Ortszeiten der
Fixes, damit Sommerzeit-Verschiebungen wie im Paper mitlaufen):
  K4 Europa  -- Long USD Frankfurt 08:00 -> 14:15 (vor EZB-Fix),
                Short USD London 16:00 -> New York 17:00 (nach London-Fix).
  K5 Tokio   -- Long USD New York 17:00 -> Tokio 09:55 (vor Tokio-Fix),
                Short USD Tokio 09:55 -> New York 02:00 (nach Tokio-Fix).
Jedes Bein ist ein eigener Trade. Kein Stop, Zeit-Exit wie im Paper.
Ergebnis in bps nach Kosten (Rundturn je Bein, costs.py).
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from smh_microstructure.costs import roundtrip_cost

USD_BASE = {"USDJPY", "USDCHF", "USDCAD", "USDNOK", "USDSEK"}   # Long USD = Long Paar; sonst Short Paar
TOL = pd.Timedelta(minutes=5)               # naechste Bar hoechstens 5 Min nach Sollzeit

NY, LDN, FRA, TYO = "America/New_York", "Europe/London", "Europe/Berlin", "Asia/Tokyo"


@dataclass(frozen=True)
class Config:
    window: str = "europa"          # "europa" (K4) | "tokio" (K5)
    leg_pre: bool = True            # Bein vor dem Fix (Long USD)
    leg_post: bool = True           # Bein nach dem Fix (Short USD)
    pre_start: str = ""             # leer = Paper-Wert (siehe _legs)
    pre_end: str = ""
    post_start: str = ""
    post_end: str = ""
    breedon: bool = False           # K4: Sitzungs-Variante (02-08 / 08-17 New York)
    gotobi_only: bool = False       # K5: nur Gotobi-Tage (Ito & Yamada 2017)
    pre_start_shift_min: int = 0    # Nachbarwert: Beginn des Vor-Fix-Beins verschieben
    post_end_shift_min: int = 0     # Nachbarwert: Ende des Nach-Fix-Beins verschieben
    shift_h: int = 0                # Gegenprobe: alle Zeiten um h Stunden verschieben
    cost_mult: float = 1.0

    def as_dict(self):
        return asdict(self)


def _legs(cfg: Config):
    """(name, tz_start, hh:mm, tag_offset_start, tz_end, hh:mm, tag_offset_end, usd_seite)."""
    if cfg.window == "europa":
        if cfg.breedon:   # Breedon & Ranaldo: EUR-Sitzung 2-8 NY Short Basis, USD-Sitzung 8-17 NY Long Basis
            pre = ("vor", NY, cfg.pre_start or "02:00", 0, NY, cfg.pre_end or "08:00", 0, +1)
            post = ("nach", NY, cfg.post_start or "08:00", 0, NY, cfg.post_end or "17:00", 0, -1)
        else:
            pre = ("vor", FRA, cfg.pre_start or "08:00", 0, FRA, cfg.pre_end or "14:15", 0, +1)
            post = ("nach", LDN, cfg.post_start or "16:00", 0, NY, cfg.post_end or "17:00", 0, -1)
    else:  # Tokio: Handelstag = Tokio-Datum D; Start am NY-Abend des Vortags
        pre = ("vor", NY, cfg.pre_start or "17:00", -1, TYO, cfg.pre_end or "09:55", 0, +1)
        post = ("nach", TYO, cfg.post_start or "09:55", 0, NY, cfg.post_end or "02:00", 0, -1)
    out = []
    if cfg.leg_pre:
        out.append(pre)
    if cfg.leg_post:
        out.append(post)
    return out


def _local_ts(days: pd.DatetimeIndex, tz: str, hhmm: str, day_off: int, shift_h: int) -> pd.DatetimeIndex:
    h, m = int(hhmm[:2]), int(hhmm[3:])
    naive = days + pd.Timedelta(days=day_off) + pd.Timedelta(hours=h + shift_h, minutes=m)
    return naive.tz_localize(tz, nonexistent="shift_forward", ambiguous=False).tz_convert("UTC")


def _price_at(opens: pd.Series, ts: pd.DatetimeIndex, closes: pd.Series | None = None) -> np.ndarray:
    """Open der ersten Bar >= ts, falls hoechstens TOL spaeter; sonst NaN.
    Mit `closes` (nur fuer Ausstiege): fehlt die Bar danach (Wochenschluss Freitag
    17:00 New York), gilt der Schluss der letzten Bar, die hoechstens TOL vor ts endet."""
    idx = opens.index
    pos = idx.searchsorted(ts, side="left")
    ok = pos < len(idx)
    out = np.full(len(ts), np.nan)
    p = pos[ok]
    hit = (idx[p] - ts[ok]) <= TOL
    vals = opens.to_numpy()[p]
    out[np.flatnonzero(ok)[hit]] = vals[hit]
    if closes is not None:
        miss = np.flatnonzero(~np.isfinite(out))
        q = pos[miss] - 1
        good = q >= 0
        miss, q = miss[good], q[good]
        near = (ts[miss] - (idx[q] + pd.Timedelta(minutes=1))) <= TOL
        out[miss[near]] = closes.to_numpy()[q[near]]
    return out


def gotobi_days(days: pd.DatetimeIndex) -> np.ndarray:
    """Gotobi = 5., 10., 15., 20., 25. und Monatsletzter; faellt er aufs Wochenende,
    gilt der Werktag davor (japanische Feiertage nicht beruecksichtigt)."""
    days = pd.DatetimeIndex(days)
    targets = set()
    for y, mth in sorted({(d.year, d.month) for d in days}):
        last = (pd.Timestamp(y, mth, 1) + pd.offsets.MonthEnd(0)).day
        for d in (5, 10, 15, 20, 25, last):
            t = pd.Timestamp(y, mth, d)
            while t.dayofweek >= 5:
                t -= pd.Timedelta(days=1)
            targets.add(t)
    return np.array([d in targets for d in days])


def run(df: pd.DataFrame, sym: str, cfg: Config) -> pd.DataFrame:
    opens = df["open"].copy()
    opens.index = opens.index.as_unit("ns")
    closes = df["close"].copy()
    closes.index = opens.index
    first, last = opens.index[0], opens.index[-1]
    tz_day = FRA if cfg.window == "europa" else TYO
    days = pd.date_range(first.tz_convert(tz_day).normalize().tz_localize(None),
                         last.tz_convert(tz_day).normalize().tz_localize(None), freq="D")
    days = days[days.dayofweek < 5]
    if cfg.gotobi_only:
        days = days[gotobi_days(days)]
    side_sym = 1 if sym in USD_BASE else -1
    rows = []
    for name, tz0, t0, o0, tz1, t1, o1, usd in _legs(cfg):
        ts0 = _local_ts(days, tz0, t0, o0, cfg.shift_h)
        ts1 = _local_ts(days, tz1, t1, o1, cfg.shift_h)
        if name == "vor":
            ts0 = ts0 + pd.Timedelta(minutes=cfg.pre_start_shift_min)
        else:
            ts1 = ts1 + pd.Timedelta(minutes=cfg.post_end_shift_min)
        pe, px = _price_at(opens, ts0), _price_at(opens, ts1, closes)
        ok = np.isfinite(pe) & np.isfinite(px) & (ts1 > ts0)
        side = usd * side_sym
        cost = np.array([roundtrip_cost(sym, p, cfg.cost_mult) for p in pe[ok]]) / pe[ok] * 1e4
        gross = side * (px[ok] - pe[ok]) / pe[ok] * 1e4
        rows.append(pd.DataFrame({"sym": sym, "leg": name, "entry_time": ts0[ok], "exit_time": ts1[ok],
                                  "day": days[ok].date, "side": side, "entry": pe[ok], "exit": px[ok],
                                  "gross_bps": gross, "cost_bps": cost, "pnl_bps": gross - cost}))
    out = pd.concat(rows) if rows else pd.DataFrame()
    return out.sort_values("entry_time").reset_index(drop=True) if len(out) else out


def run_all(data: dict[str, pd.DataFrame], cfg: Config) -> pd.DataFrame:
    parts = [p for p in (run(df, s, cfg) for s, df in data.items()) if len(p)]
    if not parts:
        return pd.DataFrame(columns=["sym", "entry_time", "pnl_bps"])
    return pd.concat(parts).sort_values("entry_time").reset_index(drop=True)
