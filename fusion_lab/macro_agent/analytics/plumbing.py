"""Fact Sheet v4 (24.11.2026): was Macro-Desks taeglich unter der Oberflaeche ansehen.

Liquiditaet/Funding, Zins-Volatilitaet + Laufzeitpraemie, Wachstum jetzt, Marktverfassung.
Alles Kontext, kein Signal: Werte, Aenderungen und eine Einordnung gegen die eigene Historie.
Jede Funktion arbeitet auf den breiten Tabellen bis zum Stichtag (`fact_sheet._stored` filtert as-of).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .profiles import series

G8 = ["US", "EA", "GB", "JP", "CH", "AU", "CA", "NZ"]
CURVE_DAYS = 20
CORR_DAYS = 60


def _r(v, d: int = 2):
    return None if v is None or pd.isna(v) else round(float(v), d)


def _date(s: pd.Series) -> str | None:
    return None if s.empty else s.index[-1].date().isoformat()


def _pctile(s: pd.Series) -> float | None:
    """Rang des letzten Werts in der eigenen Historie, 0-100."""
    s = s.dropna()
    return None if len(s) < 50 else round(float((s < s.iloc[-1]).mean() * 100), 0)


def _chg(s: pd.Series, n: int, scale: float = 1.0):
    s = s.dropna()
    return None if len(s) <= n else _r((s.iloc[-1] - s.iloc[-1 - n]) * scale, 1)


def net_liquidity(macro_w: pd.DataFrame) -> pd.Series:
    """Fed-Bilanz minus Treasury-Konto minus Reverse Repo, Mrd. USD, an den Wochenstichtagen der Bilanz."""
    walcl = series(macro_w, "US.fed_assets") / 1000
    if walcl.empty:
        return walcl
    tga = series(macro_w, "US.tga") / 1000
    rrp = series(macro_w, "US.rrp")
    days = walcl.index
    tga = tga.reindex(tga.index.union(days)).ffill().reindex(days)
    rrp = rrp.reindex(rrp.index.union(days)).ffill().reindex(days).fillna(0.0)
    return (walcl - tga - rrp).dropna()


def liquidity(macro_w: pd.DataFrame) -> dict:
    net = net_liquidity(macro_w)
    spread = (series(macro_w, "US.sofr") - series(macro_w, "US.iorb")).dropna() * 100
    res = series(macro_w, "US.reserves") / 1000
    out = {"net_mrd": _r(net.iloc[-1], 0) if len(net) else None, "datum": _date(net),
           "chg_4w_mrd": _chg(net, 4), "chg_13w_mrd": _chg(net, 13),
           "reserven_mrd": _r(res.iloc[-1], 0) if len(res) else None, "reserven_chg_13w_mrd": _chg(res, 13),
           "sofr_iorb_bp": _r(spread.iloc[-1], 1) if len(spread) else None,
           "sofr_iorb_max_20t_bp": _r(spread.iloc[-20:].max(), 1) if len(spread) else None,
           "sofr_datum": _date(spread)}
    c13 = out["chg_13w_mrd"]
    out["lesart"] = ("n.v." if c13 is None else "Liquidität steigt" if c13 > 50 else
                     "Liquidität sinkt" if c13 < -50 else "Liquidität seitwärts")
    sp = out["sofr_iorb_bp"]
    out["funding"] = ("n.v." if sp is None else "angespannt (SOFR über IORB)" if sp > 2 else
                      "normal")
    return out


def curve_shape(d2: float | None, d10: float | None) -> str:
    """Bewegung der Kurve aus den Aenderungen von 2J und 10J (bp)."""
    if d2 is None or d10 is None:
        return "n.v."
    steeper = (d10 - d2) > 3
    flatter = (d10 - d2) < -3
    if not steeper and not flatter:
        return "parallel"
    if steeper:
        return "Bull-Steepener" if d2 < 0 and abs(d2) >= abs(d10) else "Bear-Steepener"
    return "Bear-Flattener" if d2 > 0 and abs(d2) >= abs(d10) else "Bull-Flattener"


def rates_vol(macro_w: pd.DataFrame, mkt_w: pd.DataFrame) -> dict:
    move = series(mkt_w, "MKT.move")
    tp = series(macro_w, "US.term_premium_10y")
    exp = series(macro_w, "US.expected_10y")
    out = {"move": _r(move.iloc[-1], 1) if len(move) else None, "move_datum": _date(move),
           "move_perzentil": _pctile(move), "move_chg_20t": _chg(move, 20),
           "praemie_10j": _r(tp.iloc[-1], 2) if len(tp) else None, "praemie_datum": _date(tp),
           "praemie_chg_20t_bp": _chg(tp, 20, 100), "erwartung_chg_20t_bp": _chg(exp, 20, 100),
           "praemie_perzentil": _pctile(tp)}
    p, e = out["praemie_chg_20t_bp"], out["erwartung_chg_20t_bp"]
    out["lesart_10j"] = ("n.v." if p is None or e is None else
                         "kaum Bewegung" if max(abs(p), abs(e)) < 5 else
                         "Prämie treibt" if abs(p) > abs(e) else "Zinserwartung treibt")
    kurven = {}
    for land in G8:
        y2, y10 = series(macro_w, f"{land}.2y"), series(macro_w, f"{land}.10y")
        if y2.empty or y10.empty:
            continue
        d2, d10 = _chg(y2, CURVE_DAYS, 100), _chg(y10, CURVE_DAYS, 100)
        kurven[land] = {"kurve": _r(y10.iloc[-1] - y2.iloc[-1], 2), "d2j_bp": d2, "d10j_bp": d10,
                        "form": curve_shape(d2, d10)}
    out["kurven"] = kurven
    out["kurven_tage"] = CURVE_DAYS
    return out


def growth(macro_w: pd.DataFrame) -> dict:
    now = series(macro_w, "US.gdpnow")
    claims = series(macro_w, "US.claims") / 1000
    sahm = series(macro_w, "US.sahm")
    out = {"gdpnow": _r(now.iloc[-1], 1) if len(now) else None,
           "gdpnow_quartal": None if now.empty else str(now.index[-1].to_period("Q")),
           "erstantraege_tsd": _r(claims.iloc[-1], 0) if len(claims) else None, "erstantraege_datum": _date(claims),
           "erstantraege_4w_tsd": _r(claims.iloc[-4:].mean(), 0) if len(claims) >= 4 else None,
           "erstantraege_52w_tief_tsd": _r(claims.iloc[-52:].min(), 0) if len(claims) >= 52 else None,
           "sahm": _r(sahm.iloc[-1], 2) if len(sahm) else None}
    s = out["sahm"]
    out["sahm_lesart"] = "n.v." if s is None else "Rezessionssignal (≥ 0,5)" if s >= 0.5 else \
        "Warnzone (≥ 0,3)" if s >= 0.3 else "unauffällig"
    return out


def internals(mkt_w: pd.DataFrame) -> dict:
    vix, v9, v3 = (series(mkt_w, k) for k in ("MKT.vix_yf", "MKT.vix9d", "MKT.vix3m"))
    out = {}
    if len(vix) and len(v3):
        r = (vix / v3).dropna()
        out["vix"] = _r(vix.iloc[-1], 1)
        out["vix_vix3m"] = _r(r.iloc[-1], 2)
        out["vix9d_vix"] = _r((v9 / vix).dropna().iloc[-1], 2) if len(v9) else None
        out["vix_datum"] = _date(r)
        out["vix_struktur"] = "invertiert (akuter Stress)" if r.iloc[-1] > 1 else \
            "flach" if r.iloc[-1] > 0.95 else "normal (Contango)"
    spy, tlt, rsp = (series(mkt_w, k) for k in ("MKT.spy", "MKT.tlt", "MKT.rsp"))
    if len(spy) and len(tlt):
        rets = pd.concat([np.log(spy).diff(), np.log(tlt).diff()], axis=1).dropna()
        corr = rets.iloc[:, 0].rolling(CORR_DAYS).corr(rets.iloc[:, 1]).dropna()
        if len(corr):
            out["aktien_anleihen_korr"] = _r(corr.iloc[-1], 2)
            out["aktien_anleihen_korr_vor_60t"] = _r(corr.iloc[-61], 2) if len(corr) > 61 else None
            out["aktien_anleihen_lesart"] = ("Anleihen sichern nicht ab (Inflations-/Zinsregime)"
                                             if corr.iloc[-1] > 0.2 else
                                             "Anleihen sichern ab (Wachstumsregime)" if corr.iloc[-1] < -0.2
                                             else "neutral")
    if len(rsp) and len(spy):
        ratio = (rsp / spy).dropna()
        out["breite_chg_20t_pct"] = _r((ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100, 2) if len(ratio) > 21 else None
        out["breite_chg_60t_pct"] = _r((ratio.iloc[-1] / ratio.iloc[-61] - 1) * 100, 2) if len(ratio) > 61 else None
        out["breite_datum"] = _date(ratio)
    br = series(mkt_w, "MKT.brent_spread_6m")
    if len(br):
        out["brent_m1_m6_pct"] = _r(br.iloc[-1], 2)
        out["brent_kurve"] = "Backwardation (Knappheit jetzt)" if br.iloc[-1] > 1 else \
            "Contango (Angebot reicht)" if br.iloc[-1] < -1 else "flach"
    return out
