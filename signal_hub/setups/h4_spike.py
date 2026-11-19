"""Setup H4-Spike (Edge Card A6): Grundsignal + Qualitaet + Aktivitaet/Kalender (h4_v4.masks Q & A) -> Alarm.

Merkmale exakt wie im Backtest (htf_daily_trade.h4_v4.features_at). ⭐ = zusaetzlich beste Test-4-Variante:
  FX      Vormonats-Lage + (Daily-Swing mit ODER Erschoepfung) + Makro max. 3 gegen + nicht 23/07 Uhr
  Metalle Vormonats-Lage + (Daily-Swing mit ODER Erschoepfung) + Makro-Veto (Gold) bzw. Realzins (Silber)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from htf_daily_trade.h4_manip import Market, server_time
from htf_daily_trade.h4_v4 import Ctx, blocked_days, features_at, masks

SETUP = "H4-Spike"


def last_closed_bar_end(now_utc: pd.Timestamp) -> pd.Timestamp:
    """Ende der juengsten abgeschlossenen H4-Kerze (Serverzeit-Raster 0/4/8/... NY+7) in UTC."""
    srv = server_time(pd.DatetimeIndex([now_utc]))[0]
    end_srv = srv.floor("4h")
    ny = (end_srv - pd.Timedelta(hours=7)).tz_localize("America/New_York", ambiguous=True, nonexistent="shift_forward")
    return ny.tz_convert("UTC")


def ampel(r: dict) -> tuple[str, str]:
    if r["markt"] == "XAUUSD":
        gv = r.get("GV", "neutral")
        return ({"mit": "gruen", "gegen": "rot"}.get(gv, "gelb"), f"Gold-Makro-Veto {gv}")
    if r["markt"] == "XAGUSD":
        x3 = r.get("X3", "neutral")
        return ({"mit": "gruen", "gegen": "rot"}.get(x3, "gelb"), f"Realzins {x3}")
    n = int(r["makro_gegen"])
    farbe = "gruen" if n <= 2 else ("gelb" if n <= 4 else "rot")
    gegen = [f for f in ("M1", "M2", "M3", "M6", "M7", "X3", "X4") if r.get(f) == "gegen"]
    names = {"M1": "Zins-Mom.", "M2": "Carry", "M3": "Regime", "M6": "G8", "M7": "COT-Fluss", "X3": "Realzins", "X4": "COT-Index"}
    return farbe, f"{n}/7 gegen" + (f" ({', '.join(names[g] for g in gegen)})" if gegen else "")


def scan_market(name: str, now_utc: pd.Timestamp, md, gv, blocked: set) -> tuple[list[dict], pd.DataFrame | None, int]:
    """Signale an der juengsten abgeschlossenen H4-Kerze. Rueckgabe: (Signale, H4-Daten, k)."""
    today = now_utc.tz_convert("UTC").normalize().tz_localize(None) + pd.Timedelta(days=1)
    m = Market(name, end=str(today.date()), cut=now_utc)
    if len(m.x) < 200:
        return [], None, -1
    ctx = Ctx(m, end=str(today.date()))
    k = len(m.x) - 1
    out = []
    for side in ("long", "short"):
        r = features_at(ctx, k, side, md, gv, blocked)
        if r is None:
            continue
        sign = 1 if side == "long" else -1
        t = pd.DataFrame([r])
        mk = masks(t)
        q, a = bool(mk["Q"].iat[0]), bool(mk["A"].iat[0])
        kl = r["klasse"]
        stern = bool(q and a and mk["L"]["VM"].iat[0] and mk["T"]["Trend_oder_Erschoepfung"].iat[0]
                     and mk["M"]["max3" if kl == "FX" else "max2"].iat[0]
                     and (mk["H"]["ohne_23_07"].iat[0] if kl == "FX" else True))
        entry = float(m.c[k])
        risk = sign * (entry - r["stop"])
        swing = m.target("TB", sign, entry, risk, k, k) if risk > 0 else np.nan
        mpos = ctx.mpos[k]
        farbe, txt = ampel(r)
        r.update({"setup": SETUP, "q": q, "a": a, "alarm": q and a, "stern": stern, "kurs": entry,
                  "ziel_3r": entry + sign * 3 * risk, "ziel_swing": swing, "ampel": farbe, "ampel_text": txt,
                  "vm_hoch": ctx.mo["High"].iat[mpos] if mpos >= 0 else np.nan,
                  "vm_tief": ctx.mo["Low"].iat[mpos] if mpos >= 0 else np.nan,
                  "gueltig_bis": (m.x.index[k] + pd.Timedelta(hours=8)).tz_convert("Europe/Berlin"),
                  "id": f"{name}_{m.x.index[k].tz_convert('Europe/Berlin'):%Y%m%d%H}_{side[0]}"})
        out.append(r)
    return out, m.x, k


def scan_period(name: str, start: str, end: str, md, gv) -> pd.DataFrame:
    """Rueckwaertsprobe: alle Grundsignale eines Zeitraums mit Alarm-/Stern-Status (gleicher Code wie live)."""
    m = Market(name, end=end)
    ctx = Ctx(m, end=end)
    blocked = blocked_days()
    k0 = int(m.x.index.searchsorted(pd.Timestamp(start, tz="UTC")))
    rows = []
    for k in range(k0, len(m.x)):
        for side in ("long", "short"):
            r = features_at(ctx, k, side, md, gv, blocked)
            if r is None:
                continue
            mk = masks(pd.DataFrame([r]))
            r["alarm"] = bool(mk["Q"].iat[0] and mk["A"].iat[0])
            rows.append(r)
    return pd.DataFrame(rows)
