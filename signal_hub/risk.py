"""Risiko-Leitplanken gegen Overtrading (Stufe 1: Anzeige + Sperre, keine Orders).

Profile aus config.PROFILES. Gesperrt wird, wenn EIN Profil sperrt (Ausfuehrung ist auf allen Konten identisch):
  - bereits bestaetigte Trades heute (Berlin) >= max_trades_day
  - EK: realisierte Paper-Rendite seit Wochenbeginn <= week_stop
  - Funded: Paper-Equity >= trailing_dd unter dem Hoechststand
  - schon eine offene bestaetigte Position im selben Markt (eine Position je Markt)
"""

from __future__ import annotations

import pandas as pd

from signal_hub import config

LOT_UNITS = {"XAUUSD": 100.0, "XAGUSD": 5000.0}   # Unzen je Lot; FX 100.000 Einheiten


def lots(markt: str, entry: float, stop: float, risk_usd: float) -> float:
    dist = abs(entry - stop)
    if dist <= 0:
        return 0.0
    units = LOT_UNITS.get(markt, 100_000.0)
    usd_per_lot = dist * units
    if markt.startswith("USD") and markt not in LOT_UNITS:   # Gegenwaehrung != USD: in USD umrechnen
        usd_per_lot = usd_per_lot / entry
    return round(risk_usd / usd_per_lot, 2)


def _closed_conf(j: pd.DataFrame) -> pd.DataFrame:
    if "p_conf_status" not in j:
        return j.iloc[0:0]
    return j[(j["status"] == "ja") & (j["p_conf_status"] == "geschlossen")]


def check(j: pd.DataFrame, markt: str, now: pd.Timestamp) -> tuple[bool, str]:
    now = now.tz_convert(config.TZ)
    conf = j[j["status"] == "ja"] if "status" in j else j.iloc[0:0]
    if len(conf):
        heute = conf["entschieden_um"].dt.tz_convert(config.TZ).dt.date == now.date()
        n_heute = int(heute.sum())
        offen = conf[(conf["markt"] == markt) & (conf.get("p_conf_status", pd.Series(index=conf.index)) != "geschlossen")]
        if len(offen):
            return False, f"schon eine offene Position in {markt}"
    else:
        n_heute = 0
    closed = _closed_conf(j)
    for name, p in config.PROFILES.items():
        if n_heute >= p["max_trades_day"]:
            return False, f"{name}: max. {p['max_trades_day']} Trades heute erreicht"
        if len(closed):
            r = closed.sort_values("p_conf_exit_t")
            pnl = r["p_conf_r"].astype(float) * p["risk"]
            if p["week_stop"] is not None:
                wstart = (now - pd.Timedelta(days=now.dayofweek)).normalize()
                wk = pnl[r["p_conf_exit_t"].dt.tz_convert(config.TZ) >= wstart].sum()
                if wk <= p["week_stop"]:
                    return False, f"{name}: Wochenstopp {wk:.1%} erreicht"
            if p["trailing_dd"] is not None:
                eq = (1 + pnl).cumprod()
                dd = (eq / eq.cummax().clip(lower=1.0)).iloc[-1] - 1
                if dd <= -p["trailing_dd"]:
                    return False, f"{name}: Trailing-Drawdown {dd:.1%} erreicht"
    return True, ""


def sizing_text(markt: str, entry: float, stop: float) -> str:
    parts = []
    for name, p in config.PROFILES.items():
        usd = p["kapital_ref"] * p["risk"]
        parts.append(f"{name} {p['risk']:.1%} = {lots(markt, entry, stop, usd):.2f} Lot je {p['kapital_ref'] // 1000}k")
    return " · ".join(parts)
