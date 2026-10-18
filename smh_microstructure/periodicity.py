"""K6 -- Intraday-Periodizitaet (Heston, Korajczyk & Sadka 2010, JF).

Mechanismus: Grosse Haendler zerlegen Auftraege und fuehren sie Tag fuer Tag
zur selben Uhrzeit aus (gleicher Algo-Fahrplan, gleiche Fonds-Routinen). Ihr
Liquiditaetsbedarf drueckt den Kurs in derselben Halbstunde wiederholt in
dieselbe Richtung. Wer verliert: der wiederkehrende Ausfuehrer, der zur
festen Zeit Liquiditaet nachfragt.

Regel: US-Kassasitzung in 13 Halbstunden (09:30-16:00 New York). Signal je
Halbstunde = Mittel der Rendite DERSELBEN Halbstunde an den letzten L Tagen
(nur Vergangenheit). Ist |Signal| >= thr x Kosten, wird die Halbstunde in
Signalrichtung gehandelt (Einstieg Open der Halbstunde, Ausstieg Open der
naechsten). Kein Stop, Zeit-Exit. Ergebnis in bps nach Kosten.
Gegenprobe slot_shift: Signal aus einer ANDEREN Halbstunde (k Slots weiter).
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from smh_microstructure.costs import roundtrip_cost

NY = "America/New_York"


@dataclass(frozen=True)
class Config:
    lookback_days: int = 20   # HKS: Fortsetzung bei Tages-Lags 1..40
    thr: float = 0.0          # Mindestsignal in Vielfachen der Rundturn-Kosten
    slot_shift: int = 0       # Gegenprobe
    cost_mult: float = 1.0

    def as_dict(self):
        return asdict(self)


def slot_returns(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(Rendite in bps, Einstiegskurs) je Tag x Halbstunde der Kassasitzung."""
    ny = df["open"].copy()
    ny.index = ny.index.as_unit("ns").tz_convert(NY)
    ny = ny[ny.index.dayofweek < 5]
    t = ny.index
    mins = t.hour * 60 + t.minute
    ny = ny[(mins >= 570) & (mins <= 960)]           # 09:30 .. 16:00
    t = ny.index
    on_grid = (t.minute % 30 == 0)
    g = ny[on_grid]
    day = g.index.normalize().tz_localize(None)
    slot = (g.index.hour * 60 + g.index.minute - 570) // 30   # 0..13 (13 = 16:00 Ausstieg)
    px = pd.DataFrame({"day": day, "slot": slot, "p": g.to_numpy()}).pivot_table(
        index="day", columns="slot", values="p", aggfunc="first")
    px = px.reindex(columns=range(14))
    ret = (px.shift(-1, axis=1) / px - 1) * 1e4
    return ret.iloc[:, :13], px.iloc[:, :13]


def run(df: pd.DataFrame, sym: str, cfg: Config) -> pd.DataFrame:
    ret, px = slot_returns(df)
    hist = ret.shift(1).rolling(cfg.lookback_days, min_periods=cfg.lookback_days).mean()
    if cfg.slot_shift:
        hist = pd.DataFrame(np.roll(hist.to_numpy(), cfg.slot_shift, axis=1), index=hist.index, columns=hist.columns)
    cost = pd.DataFrame(np.vectorize(lambda p: roundtrip_cost(sym, p, cfg.cost_mult) if np.isfinite(p) else np.nan)(
        px.to_numpy()), index=px.index, columns=px.columns) / px * 1e4
    sig = np.sign(hist)
    take = (hist.abs() >= cfg.thr * cost) & sig.ne(0) & ret.notna() & hist.notna()
    pnl = sig * ret - cost
    st = take.stack()
    st = st[st]
    if not len(st):
        return pd.DataFrame(columns=["sym", "entry_time", "pnl_bps"])
    d, s = st.index.get_level_values(0), st.index.get_level_values(1)
    entry = (pd.DatetimeIndex(d) + pd.to_timedelta(570 + 30 * np.asarray(s), unit="min")).tz_localize(NY).tz_convert("UTC")
    out = pd.DataFrame({
        "sym": sym, "entry_time": entry, "slot": np.asarray(s),
        "side": [int(sig.at[a, b]) for a, b in zip(d, s)],
        "signal_bps": [hist.at[a, b] for a, b in zip(d, s)],
        "gross_bps": [sig.at[a, b] * ret.at[a, b] for a, b in zip(d, s)],
        "cost_bps": [cost.at[a, b] for a, b in zip(d, s)],
        "pnl_bps": [pnl.at[a, b] for a, b in zip(d, s)],
    })
    return out.sort_values("entry_time").reset_index(drop=True)


def run_all(data: dict[str, pd.DataFrame], cfg: Config) -> pd.DataFrame:
    parts = [p for p in (run(df, s, cfg) for s, df in data.items()) if len(p)]
    if not parts:
        return pd.DataFrame(columns=["sym", "entry_time", "pnl_bps"])
    return pd.concat(parts).sort_values("entry_time").reset_index(drop=True)
