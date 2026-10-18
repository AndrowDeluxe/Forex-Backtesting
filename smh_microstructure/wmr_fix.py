"""K2 -- London-4pm-Fix (WM/Reuters; Evans 2018, Melvin & Prins 2015).

Mechanismus: Indexfonds, Vermoegensverwalter und Hedger sind an den WM/R-
Benchmark gebunden und muessen zum Fix (16:00 London, Fenster seit 2015
15:57:30-16:02:30) handeln. Ihr gebuendelter Order-Flow drueckt den Kurs in
der halben Stunde davor in eine Richtung; nach dem Fix faellt der Druck weg
und der Kurs kehrt teilweise zurueck (Evans 2018). Am Monatsende ist der
Flow am groessten (Rebalancing der Waehrungs-Hedges, Melvin & Prins 2015).
Wer verliert: wer zum Fix handeln MUSS und den Preisdruck bezahlt.

Regel: Bewegung 15:30 -> 16:00 London messen. Einstieg nach dem Fix-Fenster
(Eroeffnung 16:03-Bar) GEGEN diese Bewegung, Ausstieg 17:00 London.
Variante month_end: nur am letzten Handelstag des Monats.
Ergebnis in bps (kein Stop -- Zeit-Exit wie im Paper).
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from smh_microstructure.costs import roundtrip_cost


@dataclass(frozen=True)
class Config:
    pre_start: str = "15:30"    # Beginn der Messung (30 Min vor dem Fix, Evans)
    fix: str = "16:00"
    entry: str = "16:03"        # erste volle Minute nach dem 5-Min-Fix-Fenster
    exit: str = "17:00"         # 1 Stunde nach dem Fix
    month_end_only: bool = False
    min_move_bps: float = 0.0   # 0 = jeder Tag
    cost_mult: float = 1.0

    def as_dict(self):
        return asdict(self)


def _bar_open(day_df: pd.DataFrame, hhmm: str):
    t = day_df.index.normalize()[0] + pd.Timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[3:]))
    return day_df["open"].get(t, np.nan)


def run(df: pd.DataFrame, sym: str, cfg: Config) -> pd.DataFrame:
    ldn = df.tz_convert("Europe/London")
    ldn = ldn[ldn.index.dayofweek < 5]
    days = ldn.index.normalize()
    rows = []
    # letzter Handelstag des Monats = letzter Wochentag mit Daten im Monat
    uniq = pd.DatetimeIndex(days.unique())
    month_last = pd.Series(uniq, index=uniq).groupby([uniq.year, uniq.month]).transform("max")
    is_me = dict(zip(uniq, uniq == month_last.to_numpy()))
    for day, g in ldn.groupby(days):
        if cfg.month_end_only and not is_me.get(day, False):
            continue
        p0, pf, pe, px = (_bar_open(g, t) for t in (cfg.pre_start, cfg.fix, cfg.entry, cfg.exit))
        if not np.all(np.isfinite([p0, pf, pe, px])):
            continue
        move = (pf - p0) / p0 * 1e4
        if move == 0 or abs(move) < cfg.min_move_bps:
            continue
        side = -np.sign(move)
        cost_bps = roundtrip_cost(sym, pe, cfg.cost_mult) / pe * 1e4
        pnl = side * (px - pe) / pe * 1e4 - cost_bps
        t_entry = day + pd.Timedelta(hours=int(cfg.entry[:2]), minutes=int(cfg.entry[3:]))
        rows.append({"sym": sym, "entry_time": t_entry.tz_convert("UTC"), "day": day.date(),
                     "month_end": is_me.get(day, False),
                     "pre_move_bps": move, "side": int(side), "pnl_bps": pnl, "cost_bps": cost_bps})
    out = pd.DataFrame(rows)
    if len(out):
        out["entry_time"] = pd.to_datetime(out["entry_time"], utc=True)
    return out


def run_all(data: dict[str, pd.DataFrame], cfg: Config) -> pd.DataFrame:
    parts = [p for p in (run(df, s, cfg) for s, df in data.items()) if len(p)]
    if not parts:
        return pd.DataFrame(columns=["sym", "entry_time", "pnl_bps"])
    return pd.concat(parts).sort_values("entry_time").reset_index(drop=True)
