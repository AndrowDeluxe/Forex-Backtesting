"""K7 -- Overnight Drift (Boyarchenko, Larsen & Whelan 2023, NY-Fed SR 917).

Mechanismus (Grossman & Miller 1988): Bei einem Abverkauf zum US-Schluss
uebernehmen Market Maker den Verkaufsueberhang und tragen das Lagerrisiko
ueber Nacht. Sie verlangen dafuer eine Praemie, die sich mit dem Eintreffen
neuer Kaeufer zur Europa-Eroeffnung (02:00-03:00 New York) aufloest.
Wer verliert: wer zum Schluss sofort verkaufen will.

Regel: Long Index-CFD New York 02:00 -> 03:00 (Paper-Fenster; breiter:
01:30 -> 03:30). Bedingung "abverkauf": Kassasitzung des Vortags
(09:30 -> 16:00 New York) negativ -- Proxy fuer das negative Schluss-
Ungleichgewicht, das das Paper aus signiertem Volumen misst (haben wir nicht).
"stark": Vortag unter -1 Standardabweichung der letzten 20 Kassasitzungen.
Kein Stop, Zeit-Exit. Ergebnis in bps nach Kosten.
Hinweis: die Autoren melden selbst (Liberty Street, 07/2026), dass das
02-03-Uhr-Fenster seit 2021 im Mittel nahe null liegt.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from smh_microstructure.costs import roundtrip_cost
from smh_microstructure.fix_windows import _price_at

NY = "America/New_York"


@dataclass(frozen=True)
class Config:
    start: str = "02:00"
    end: str = "03:00"
    condition: str = "keine"     # "keine" | "abverkauf" | "stark"
    start_shift_min: int = 0     # Nachbarwert
    end_shift_min: int = 0       # Nachbarwert
    cost_mult: float = 1.0

    def as_dict(self):
        return asdict(self)


def _ts(days, hhmm):
    return (days + pd.Timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[3:]))).tz_localize(
        NY, nonexistent="shift_forward", ambiguous=False).tz_convert("UTC")


def run(df: pd.DataFrame, sym: str, cfg: Config) -> pd.DataFrame:
    opens = df["open"].copy()
    opens.index = opens.index.as_unit("ns")
    closes = df["close"].copy()
    closes.index = opens.index
    first, last = opens.index[0].tz_convert(NY), opens.index[-1].tz_convert(NY)
    days = pd.date_range(first.normalize().tz_localize(None), last.normalize().tz_localize(None), freq="D")
    days = days[days.dayofweek < 5]
    # Kassasitzung je Tag (09:30 -> 16:00)
    c0, c1 = _price_at(opens, _ts(days, "09:30")), _price_at(opens, _ts(days, "16:00"), closes)
    cash = pd.Series((c1 / c0 - 1) * 1e4, index=days)
    valid = cash.dropna()
    roll_sd = valid.rolling(20, min_periods=20).std()
    # letzte VOLLSTAENDIGE Sitzung strikt vor Tag d (endet 16:00 am Vortag, vor dem Einstieg 02:00)
    j = valid.index.searchsorted(days, side="left") - 1
    has = j >= 0
    pv = np.where(has, valid.to_numpy()[np.maximum(j, 0)], np.nan)
    sd = np.where(has, roll_sd.to_numpy()[np.maximum(j, 0)], np.nan)
    ts0 = _ts(days, cfg.start) + pd.Timedelta(minutes=cfg.start_shift_min)
    ts1 = _ts(days, cfg.end) + pd.Timedelta(minutes=cfg.end_shift_min)
    pe, px = _price_at(opens, ts0), _price_at(opens, ts1, closes)
    ok = np.isfinite(pe) & np.isfinite(px)
    if cfg.condition == "abverkauf":
        ok &= np.isfinite(pv) & (pv < 0)
    elif cfg.condition == "stark":
        ok &= np.isfinite(pv) & np.isfinite(sd) & (pv < -sd)
    cost = np.array([roundtrip_cost(sym, p, cfg.cost_mult) for p in pe[ok]]) / pe[ok] * 1e4
    gross = (px[ok] - pe[ok]) / pe[ok] * 1e4
    return pd.DataFrame({"sym": sym, "entry_time": ts0[ok], "exit_time": ts1[ok], "day": days[ok].date,
                         "prev_cash_bps": pv[ok], "side": 1, "entry": pe[ok], "exit": px[ok],
                         "gross_bps": gross, "cost_bps": cost, "pnl_bps": gross - cost})


def run_all(data: dict[str, pd.DataFrame], cfg: Config) -> pd.DataFrame:
    parts = [p for p in (run(df, s, cfg) for s, df in data.items()) if len(p)]
    if not parts:
        return pd.DataFrame(columns=["sym", "entry_time", "pnl_bps"])
    return pd.concat(parts).sort_values("entry_time").reset_index(drop=True)
