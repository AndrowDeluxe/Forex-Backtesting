"""Gold-Richtungs-Komposition -- mehrere Makro-Bausteine stimmen ab (Plan 18.11.2026,
`~/.claude/plans/snoopy-nibbling-whisper.md`, Notiz knowledge/areas/filter-gold-komposition.md).

Bausteine (je +1 long / 0 keine Aussage / −1 short), alle nur mit Daten VOR dem Entscheidungstag:
  Z   Zinskurven-Regime (GoldZinskurvenFilter, Dennis-Matrix: Goldilocks/Reflation long, Inflation short)
  M   Makro-Block wie das Live-Veto (Realzins, USD, Breakeven, EPU als 3-J-Perzentil; >= 65 long, <= 35 short)
  R2  US-2J faellt ueber 20 Beobachtungen -> long (wie ZinsFxFilter.momentum_dir fuer Metalle)
  RR  US-Realzins 10J faellt ueber 20 Beobachtungen -> long (wie ZinsFxFilter.carry_dir fuer Metalle)
  C   COT Non-Commercials Gold: Netto-Aufbau ueber 4 Berichte -> Richtung (CotFlowFilter)

Regeln:
  K1  Mehrheit: Summe >= +2 long, <= −2 short
  K2  K1, aber keine Richtung, wenn M oder Z dagegen stimmt (Veto)
  K3  einstimmig: mindestens 3 Stimmen ungleich 0 und keine Gegenstimme

M wird hier aus denselben Rohreihen und Funktionen wie `gold_confirm` berechnet, aber auf GC=F-Handelstagen
ab 2004, damit ein Blindzeitraum vor 2010 moeglich ist. Ab ~2013 stimmt es mit dem Live-Veto praktisch
ueberein (Pruefung im Forschungsskript, Stufe `overlap`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.filters.zinskurve_regime import GOLD_DIR, GoldZinskurvenFilter

BAUSTEINE = ("Z", "M", "R2", "RR", "C")
REGELN = ("K1", "K2", "K3")
VETO = ("M", "Z")


def _vor(s: pd.Series, days: pd.DatetimeIndex) -> pd.Series:
    """Wert mit Datum t gilt erst ab t+1 Kalendertag (= nur Daten VOR dem Entscheidungstag)."""
    s = s.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize() + pd.Timedelta(days=1)
    return s.reindex(days.union(s.index)).ffill().reindex(days)


def _sign(x: pd.Series) -> pd.Series:
    return np.sign(x).fillna(0).astype(int)


def macro_series(days: pd.DatetimeIndex | None = None) -> pd.Series:
    """MACRO 0..1 wie `gold_confirm` (gleiche Rohwerte, gleiche Normierung), auf GC=F-Tagen ab 2004."""
    from fusion_lab.gold_confirm.components import _on, normalize
    from fusion_lab.gold_confirm.data import load

    yf, fred = load("yf"), load("fred")
    if days is None:
        days = pd.DatetimeIndex(yf["gc_close"].dropna().index)
    raw = pd.DataFrame(index=days)
    raw["m_real"] = -_on(fred["real10"], days, lag_days=1).diff(20)
    raw["m_usd"] = -np.log(_on(yf["dxy_close"], days)).diff(20)
    raw["m_infl"] = _on(fred["be10"], days, lag_days=1).diff(20)
    epu = _on(fred["epu"], days, lag_days=1)
    raw["m_geo"] = epu.rolling(20).mean() / epu.rolling(120).mean() - 1
    comp = pd.DataFrame({k: normalize(raw[k]) for k in raw.columns}, index=days)
    return comp.mean(axis=1, skipna=True).where(comp.notna().any(axis=1)).rename("MACRO")


def vote_frame(z_lag: int = 20, twist_resets: bool = True, days: pd.DatetimeIndex | None = None,
               macro: pd.Series | None = None) -> pd.DataFrame:
    """Stimmen aller Bausteine je Entscheidungstag (Index = Werktage ab 2004)."""
    from fusion_lab.filters.cot_flow import CODES, load_cot
    from fusion_lab.g8.data import fetch_fred
    from fusion_lab.gold_confirm.data import load

    fred = load("fred")
    if days is None:
        end = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
        days = pd.bdate_range("2004-01-01", end)
    out = pd.DataFrame(index=days)

    reg = GoldZinskurvenFilter(lag=z_lag, twist_resets=twist_resets).regime
    out["Z"] = _vor(reg.map(GOLD_DIR).astype(float), days).fillna(0).astype(int)

    m = macro_series() if macro is None else macro
    m_vote = pd.Series(np.where(m >= 0.65, 1, np.where(m <= 0.35, -1, 0)), index=m.index).where(m.notna())
    out["M"] = _vor(m_vote, days).fillna(0).astype(int)

    y2 = fetch_fred("DGS2")
    out["R2"] = _vor(-_sign(y2.dropna().diff(20)), days).fillna(0).astype(int)
    real = fred["real10"].dropna()
    out["RR"] = _vor(-_sign(real.diff(20)), days).fillna(0).astype(int)

    cot = load_cot()
    g = cot[cot["cftc_contract_market_code"] == CODES["XAUUSD"][0]].set_index("avail")["nc"]
    out["C"] = _vor(_sign(g.diff(4)) * CODES["XAUUSD"][1], days).fillna(0).astype(int)
    return out


def combine(votes: pd.DataFrame, rule: str = "K2", bausteine: tuple[str, ...] = BAUSTEINE) -> pd.Series:
    """Richtung aus den Stimmen nach Regel K1/K2/K3."""
    v = votes[list(bausteine)]
    s = v.sum(axis=1)
    if rule in ("K1", "K2"):
        d = pd.Series(np.where(s >= 2, 1, np.where(s <= -2, -1, 0)), index=v.index)
        if rule == "K2":
            for b in (x for x in VETO if x in bausteine):
                d = d.where(~((v[b] != 0) & (v[b] == -d)), 0)
        return d.astype(int)
    if rule == "K3":
        nz = (v != 0).sum(axis=1)
        pos, neg = (v > 0).sum(axis=1), (v < 0).sum(axis=1)
        return pd.Series(np.where((nz >= 3) & (neg == 0), 1, np.where((nz >= 3) & (pos == 0), -1, 0)),
                         index=v.index).astype(int)
    raise ValueError(f"Regel {rule!r} unbekannt, erlaubt: {REGELN}")


class GoldRichtungKomposition:
    """Schnittstelle wie die anderen Filter: direction(day), allows(side, day), votes(day), explain(day)."""

    def __init__(self, z_lag: int = 20, twist_resets: bool = True, rule: str = "K2",
                 bausteine: tuple[str, ...] = BAUSTEINE, frame: pd.DataFrame | None = None):
        self.rule, self.bausteine = rule, tuple(bausteine)
        self.frame = vote_frame(z_lag, twist_resets) if frame is None else frame
        self.dir = combine(self.frame, rule, self.bausteine)

    def _row(self, day) -> pd.Timestamp | None:
        day = pd.Timestamp(day)
        day = (day.tz_localize(None) if day.tzinfo else day).normalize()
        i = self.frame.index.searchsorted(day, side="right") - 1
        return None if i < 0 else self.frame.index[i]

    def votes(self, day) -> dict[str, int]:
        r = self._row(day)
        return {} if r is None else {b: int(self.frame.at[r, b]) for b in self.bausteine}

    def direction(self, day) -> int:
        r = self._row(day)
        return 0 if r is None else int(self.dir.at[r])

    def allows(self, side, day) -> bool:
        want = 1 if (side in ("long", "buy") if isinstance(side, str) else side > 0) else -1
        d = self.direction(day)
        return d == 0 or d == want

    def explain(self, day) -> dict:
        return {"tag": str(self._row(day).date()) if self._row(day) is not None else None,
                "regel": self.rule, "stimmen": self.votes(day), "richtung": self.direction(day)}
