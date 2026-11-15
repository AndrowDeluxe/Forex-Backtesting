"""Vorgriff-Waechter: findet Backtest-Code, der in die Zukunft schaut.

Idee (Nutzerentscheid 2026-11-15, Anstoss: AI-Pathways-Kurs, siehe
knowledge/areas/vorgriff-waechter.md): Eine kausale Rechnung liefert fuer jeden
Zeitpunkt s dasselbe Ergebnis, egal ob die Daten nach s noch dranhaengen oder
nicht. Also: Funktion einmal auf allen Daten rechnen, dann an N zufaelligen
Stichtagen die Daten abschneiden, neu rechnen und alle Zeilen bis zum Stichtag
vergleichen. Jede Abweichung ist ein Vorgriff.

Haette automatisch gefangen:
- ASB-Friktion (`corwin_schultz_spread` datiert auf t, nutzt t+1),
- Lake-H4-Duplikate (H4-Kerze 3 h vor ihrem Schluss angehaengt),
- CTNL-Risikohalbierung (Serie zaehlte noch offene Vorgaenger mit).

Zwei Werkzeuge:

1. `check_truncation(fn, data, ...)` -- der Abschneide-Test fuer jede Signal-,
   Indikator-, Filter- oder Trade-Funktion.
2. `engine_selftest(run_fn, ...)` -- prueft die Backtest-Engine selbst auf
   Kunstdaten: ein eingepflanzter Edge muss gefunden werden, reines Rauschen
   muss ~0 minus Kosten ergeben, und eine Bewegung auf dem Signal-Balken selbst
   darf nicht als Gewinn auftauchen (Fuellung vor Signal = Vorgriff).

Wichtig zur Zeitkonvention: Abgeschnitten wird nach dem Zeitpunkt, zu dem eine
Zeile BEKANNT ist. Bei Kerzen mit Eroeffnungs-Stempel ist das Stempel +
Balkenlaenge (`known_after`). Wer das falsch angibt, testet etwas anderes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd


class LookaheadError(AssertionError):
    """Abschneide-Test oder Engine-Selbsttest ist durchgefallen."""


# ---------------------------------------------------------------------------
# 1. Abschneide-Test
# ---------------------------------------------------------------------------

@dataclass
class Abweichung:
    stichtag: pd.Timestamp
    zeit: Any
    spalte: str
    voll: Any
    gekuerzt: Any

    def __str__(self) -> str:
        return (f"Stichtag {self.stichtag}: Zeile {self.zeit}, Spalte '{self.spalte}': "
                f"voll={self.voll!r} vs. gekuerzt={self.gekuerzt!r}")


@dataclass
class TruncationReport:
    name: str
    stichtage: list[pd.Timestamp]
    abweichungen: list[Abweichung] = field(default_factory=list)
    verglichene_zeilen: int = 0

    @property
    def ok(self) -> bool:
        return not self.abweichungen

    def __str__(self) -> str:
        kopf = (f"Vorgriff-Waechter '{self.name}': {len(self.stichtage)} Stichtage, "
                f"{self.verglichene_zeilen} Zeilen verglichen -> ")
        if self.ok:
            return kopf + "OK, kein Vorgriff."
        betroffen = sorted({a.stichtag for a in self.abweichungen})
        zeilen = "\n  ".join(str(a) for a in self.abweichungen[:10])
        return (kopf + f"VORGRIFF an {len(betroffen)} von {len(self.stichtage)} Stichtagen. "
                f"Erste Abweichungen:\n  {zeilen}")


def _as_frame(obj: Any) -> pd.DataFrame:
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, pd.Series):
        return obj.to_frame(obj.name if obj.name is not None else "wert")
    raise TypeError(f"Funktion muss Series oder DataFrame liefern, nicht {type(obj).__name__}")


def _truncate(frame: pd.DataFrame, cutoff: pd.Timestamp, delay: pd.Timedelta) -> pd.DataFrame:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("Eingabedaten brauchen einen DatetimeIndex")
    return frame.loc[frame.index + delay <= cutoff]


def _zeitachse(out: pd.DataFrame, time_col: str | None) -> pd.Series:
    if time_col is not None:
        return pd.to_datetime(out[time_col])
    if not isinstance(out.index, pd.DatetimeIndex):
        raise TypeError("Ergebnis ohne DatetimeIndex: `time_col` angeben (z. B. 'entry_time')")
    return pd.Series(out.index, index=out.index)


def _gleich(a: Any, b: Any, atol: float, rtol: float) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    if isinstance(a, (int, float, np.number)) and isinstance(b, (int, float, np.number)) \
            and not isinstance(a, (bool, np.bool_)):
        return bool(np.isclose(float(a), float(b), atol=atol, rtol=rtol))
    return a == b


def _vergleiche(voll: pd.DataFrame, teil: pd.DataFrame, cutoff: pd.Timestamp, settle: pd.Timedelta,
                time_col: str | None, key: list[str] | None, columns: list[str] | None,
                atol: float, rtol: float) -> tuple[list[Abweichung], int]:
    # Ergebniszeile s ist erst bei s + Verzoegerung entschieden (settle enthaelt sie)
    grenze = cutoff - settle
    v = voll.loc[(_zeitachse(voll, time_col) <= grenze).to_numpy()]
    t = teil.loc[(_zeitachse(teil, time_col) <= grenze).to_numpy()]
    if key:
        v, t = v.set_index(key), t.set_index(key)
    # Doppelte Schluessel wuerden den Abgleich verfaelschen -> laufende Nummer dazu
    if v.index.has_duplicates or t.index.has_duplicates:
        v = v.set_index(v.groupby(level=list(range(v.index.nlevels))).cumcount(), append=True)
        t = t.set_index(t.groupby(level=list(range(t.index.nlevels))).cumcount(), append=True)
    cols = columns or [c for c in v.columns if c != time_col]
    out: list[Abweichung] = []
    for z in v.index.difference(t.index):
        out.append(Abweichung(cutoff, z, "<Zeile>", "vorhanden", "fehlt"))
    for z in t.index.difference(v.index):
        out.append(Abweichung(cutoff, z, "<Zeile>", "fehlt", "vorhanden"))
    gemeinsam = v.index.intersection(t.index)
    for c in cols:
        if c not in t.columns:
            out.append(Abweichung(cutoff, "-", c, "Spalte da", "Spalte fehlt"))
            continue
        va, ta = v.loc[gemeinsam, c], t.loc[gemeinsam, c]
        for z, a, b in zip(gemeinsam, va.to_numpy(), ta.to_numpy()):
            if not _gleich(a, b, atol, rtol):
                out.append(Abweichung(cutoff, z, str(c), a, b))
    return out, len(gemeinsam)


def check_truncation(
    fn: Callable[..., pd.Series | pd.DataFrame],
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    *,
    n_cuts: int = 30,
    seed: int = 0,
    min_history: int | float = 0.25,
    known_after: pd.Timedelta | str | Mapping[str, pd.Timedelta | str] = "0s",
    settle: pd.Timedelta | str | None = None,
    time_col: str | None = None,
    key: list[str] | None = None,
    columns: list[str] | None = None,
    atol: float = 1e-9,
    rtol: float = 1e-7,
    name: str | None = None,
    raise_on_fail: bool = True,
) -> TruncationReport:
    """Abschneide-Test. `fn(data)` muss Series/DataFrame liefern.

    data          DataFrame oder dict {name: DataFrame} (mehrere Zeitebenen), je mit
                  DatetimeIndex. Bei dict wird `fn(**data)` aufgerufen.
    known_after   Ab wann eine Zeile bekannt ist, relativ zu ihrem Stempel. Kerzen mit
                  Eroeffnungs-Stempel: Balkenlaenge (z. B. "4h"). Je Zeitebene als dict.
    settle        Nur Ergebniszeilen bis Stichtag - settle vergleichen. Standard: die
                  kleinste `known_after`-Verzoegerung (Ergebnis auf dem Raster der feinsten
                  Zeitebene). Fuer Trade-Listen, deren Einstieg erst nach dem Signal-Balken
                  liegt, groesser setzen (z. B. "1D" bei Fuellung zur naechsten Eroeffnung).
    time_col      Zeitspalte des Ergebnisses, wenn dessen Index keine Zeit ist.
    key/columns   Zeilenschluessel bzw. zu vergleichende Spalten (Standard: alle). Bei
                  Trade-Listen nur Felder, die beim Einstieg feststehen (nicht exit_*).
    min_history   Stichtage erst nach diesem Anteil (<1) bzw. dieser Zeilenzahl der
                  Basisdaten (Aufwaermphase von Indikatoren).
    """
    frames = dict(data) if isinstance(data, Mapping) else {"_": data}
    if isinstance(known_after, Mapping):
        delays = {k: pd.Timedelta(known_after.get(k, "0s")) for k in frames}
    else:
        delays = {k: pd.Timedelta(known_after) for k in frames}
    settle_td = min(delays.values()) if settle is None else pd.Timedelta(settle)

    def call(fr: dict[str, pd.DataFrame]):
        return _as_frame(fn(fr["_"]) if "_" in fr else fn(**fr))

    # Stichtage aus den Bekannt-Zeitpunkten aller Ebenen (die feinste dominiert)
    zeiten = sorted(set().union(*[set(f.index + delays[k]) for k, f in frames.items()]))
    if len(zeiten) < 3:
        raise ValueError("zu wenige Daten fuer einen Abschneide-Test")
    start = int(len(zeiten) * min_history) if min_history < 1 else int(min_history)
    kandidaten = zeiten[max(start, 1):-1]
    rng = np.random.default_rng(seed)
    n = min(n_cuts, len(kandidaten))
    stichtage = sorted(pd.Timestamp(kandidaten[i]) for i in rng.choice(len(kandidaten), n, replace=False))

    voll = call(frames)
    report = TruncationReport(name or getattr(fn, "__name__", "fn"), stichtage)
    for cut in stichtage:
        teil = call({k: _truncate(f, cut, delays[k]) for k, f in frames.items()})
        diffs, n_rows = _vergleiche(voll, teil, cut, settle_td, time_col, key, columns, atol, rtol)
        report.abweichungen.extend(diffs)
        report.verglichene_zeilen += n_rows
    if raise_on_fail and not report.ok:
        raise LookaheadError(str(report))
    return report


# ---------------------------------------------------------------------------
# 2. Engine-Selbsttest auf Kunstdaten
# ---------------------------------------------------------------------------

def make_noise_ohlc(n: int = 3000, *, start: str = "2010-01-04", freq: str = "B", vol: float = 0.01,
                    seed: int = 0, price: float = 100.0) -> pd.DataFrame:
    """Zufallspfad ohne Drift und ohne Luecken (open = voriger close)."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, vol, n)
    close = price * np.exp(np.cumsum(r))
    open_ = np.r_[price, close[:-1]]
    spread = np.abs(rng.normal(0.0, vol / 2, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    idx = pd.date_range(start, periods=n, freq=freq)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=idx)


def _flags(n: int, every: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 1)
    f = rng.random(n) < 1.0 / every
    f[-2:] = False  # der Balken danach muss existieren
    return f


def _bump_bars(df: pd.DataFrame, bars: np.ndarray, bump: float) -> pd.DataFrame:
    """Gibt den markierten Balken (open->close) zusaetzlich +bump; alle spaeteren Preise
    verschieben sich mit, damit keine Luecken entstehen."""
    out = df.copy()
    faktor = np.cumprod(np.where(bars, 1 + bump, 1.0))
    vorher = np.r_[1.0, faktor[:-1]]
    for c in ("open", "high", "low", "close"):
        out[c] = out[c].to_numpy() * vorher
    out["close"] = out["close"].to_numpy() * np.where(bars, 1 + bump, 1.0)
    out["high"] = np.maximum(out["high"], out["close"])
    return out


@dataclass
class SelftestReport:
    bump: float
    cost: float
    ergebnisse: dict[str, dict] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(r["ok"] for r in self.ergebnisse.values())

    def __str__(self) -> str:
        z = [f"Engine-Selbsttest (Edge {self.bump:.2%}, Kosten {self.cost:.2%} je Trade):"]
        for k, r in self.ergebnisse.items():
            z.append(f"  {'OK ' if r['ok'] else 'FEHLER'} {k}: n={r['n']}, Mittel {r['mean']:+.4%} "
                     f"(erwartet {r['soll']}), t={r['t']:+.2f}")
        return "\n".join(z)


def _stats(ret) -> tuple[int, float, float, float]:
    a = np.asarray(pd.Series(ret, dtype=float).dropna())
    if len(a) < 2:
        return len(a), float("nan"), float("nan"), float("nan")
    se = float(a.std(ddof=1) / np.sqrt(len(a)))
    t = float(a.mean() / se) if se > 0 else float("inf")
    return len(a), float(a.mean()), t, se


def engine_selftest(
    run_fn: Callable[[pd.DataFrame, pd.Series], Any],
    *,
    bump: float = 0.01,
    cost: float = 0.0,
    n: int = 3000,
    every: int = 15,
    vol: float = 0.01,
    seed: int = 0,
    raise_on_fail: bool = True,
) -> SelftestReport:
    """Prueft eine Engine mit `run_fn(ohlc, signal) -> Trade-Renditen` (Bruchteile, nach
    Kosten). Erwartete Semantik: Signal am Schluss von Balken i, Einstieg zur Eroeffnung
    i+1, Ausstieg am Schluss i+1 (oder spaeter; der Edge sitzt auf Balken i+1).

    Drei Proben:
    - eingepflanzt: Balken nach jedem Signal bekommt +bump -> Mittel ~ bump - cost
      (Band 0,6..1,2 x bump, minus cost).
    - rauschen:     gleiche Signale, kein Edge -> Mittel ~ -cost, |t| < 3.
    - signalbalken: +bump auf dem Signal-Balken SELBST -> eine korrekte Engine sieht
      davon nichts (~ -cost). Profitiert sie, fuellt sie vor dem Signal (Vorgriff).
    """
    rep = SelftestReport(bump, cost)
    basis = make_noise_ohlc(n, vol=vol, seed=seed)
    f = _flags(n, every, seed)
    signal = pd.Series(f, index=basis.index, name="signal")
    naechster = np.r_[False, f[:-1]]

    proben = {
        "eingepflanzt": (_bump_bars(basis, naechster, bump), "edge"),
        "rauschen": (basis, "null"),
        "signalbalken": (_bump_bars(basis, f, bump), "null"),
    }
    for name, (df, art) in proben.items():
        k, m, t, se = _stats(run_fn(df, signal))
        if art == "edge":
            lo, hi = 0.6 * bump - cost, 1.2 * bump - cost
            ok = k >= 10 and lo <= m <= hi
            soll = f"{lo:+.3%}..{hi:+.3%}"
        else:
            ok = k >= 10 and abs(m + cost) <= max(3 * (se if np.isfinite(se) else 0.0), 0.1 * bump)
            soll = f"~{-cost:+.3%}"
        rep.ergebnisse[name] = {"ok": bool(ok), "n": k, "mean": m, "t": t, "soll": soll}
    if raise_on_fail and not rep.ok:
        raise LookaheadError(str(rep))
    return rep
