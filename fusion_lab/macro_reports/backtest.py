"""Backtest der Ideen aus den SMH-Makro-Reports (Phase 1, Schritt 3).

Die Varianten sind VOR dem ersten Lauf festgelegt und im Research-Lock
"smh_macro_reports" registriert (Bewertungsmodus: keine Optimierung, alle
Varianten werden ausgewiesen; Regelwerk knowledge/areas/overfitting-sperre.md):

  A1  Bias alle      jede gerichtete Idee ausser "inaktiv"; Einstieg naechste
                     H1-Eroeffnung nach Postzeit; Ausstieg zur ersten H1-Eroeffnung
                     nach Postzeit des naechsten Reports.
  A2  Bias Main      wie A1, nur eine Idee je Report (role main, sonst hoechste
                     Konfidenz, sonst die erste).
  B   Level          Einstieg wie A1; Stop = Report-Stop (falls auf der richtigen
                     Seite) sonst 1,5 ATR; Ziel = naechstes Report-Ziel auf der
                     Gewinnseite sonst 2 R; Zeitausstieg nach 7 Handelstagen;
                     H1-intrabar, Stop und Ziel in derselben Bar -> Stop.
  C   Aktivierung    nur Generation 3 mit numerischer Aktivierung: Trade erst,
                     wenn ein D1-Schluss binnen 5 Handelstagen jenseits des Levels
                     liegt; Einstieg naechste H1-Eroeffnung danach; Stop =
                     Invalidierung (falls richtige Seite) sonst 1,5 ATR; Ausstieg wie B.

1 R = Abstand Einstieg-Stop; fuer A1/A2 (kein Stop) 1,5 x ATR(20, D1) am
Vortag des Einstiegs. Kosten als Round-Trip-bps je Instrumentklasse, in R
umgerechnet. Swap wird nicht modelliert.

Kontrollen (keine Kandidaten): Zufallsrichtung (Permutation der Vorzeichen
von A1) und 20-Tage-Momentum-Richtung auf denselben Ein-/Ausstiegen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import combined_strategy.data as cdata
from fusion_lab.macro_reports.schema import load

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "macro_reports"
EXTRACTED = DATA_DIR / "extracted"

ATR_MULT = 1.5
DEFAULT_TARGET_R = 2.0
TIME_EXIT_DAYS = 7
ACTIVATION_WINDOW_DAYS = 5
MAX_LEVEL_DIST = 0.20  # Report-Level >20 % vom Einstieg = Tippfehler/Jahresziel, ignoriert
STALE_DAYS = 7  # Report-Datum mehr als 7 Tage vor dem Post = Repost, nicht gewertet
CONF_ORDER = {"hoch": 0, "mittel-hoch": 1, "mittel": 2, "mittel-niedrig": 3, "niedrig": 4, None: 5}

# Round-Trip-Kosten in bps des Preises (Spread + Kommission, konservativ).
COST_BPS = {"fx_major": 1.5, "fx_cross": 2.5, "GOLD": 3.0, "SILVER": 6.0, "OIL": 5.0, "BRENT": 5.0,
            "index": 2.0, "DXY": 2.0, "COPPER": 6.0, "BTCUSD": 10.0}
_MAJORS = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"}
_INDICES = {"SP500", "NASDAQ", "US30", "DAX"}

# Instrumente, die combined_strategy.data noch nicht kennt -- nur zur Laufzeit in
# diesem Prozess ergaenzt (das Modul selbst bleibt unveraendert, Bridges unberuehrt).
_EXTRA = {
    "DXY": "INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD", "DAX": "INSTRUMENT_IDX_EUROPE_E_DAAX",
    "BRENT": "INSTRUMENT_CMD_ENERGY_E_BRENT", "COPPER": "INSTRUMENT_CMD_METALS_COPPER_CMD_USD",
    "BTCUSD": "INSTRUMENT_VCCY_BTC_USD",
}


def _register_instrument(key: str) -> bool:
    if key in cdata.INSTRUMENTS:
        return True
    import dukascopy_python.instruments as d
    name = _EXTRA.get(key)
    if name is None and len(key) == 6:
        name = f"INSTRUMENT_FX_CROSSES_{key[:3]}_{key[3:]}"
    if name and hasattr(d, name):
        cdata.INSTRUMENTS[key] = getattr(d, name)
        return True
    return False


def cost_bps(key: str) -> float:
    if key in _MAJORS:
        return COST_BPS["fx_major"]
    if key in _INDICES:
        return COST_BPS["index"]
    if key in COST_BPS:
        return COST_BPS[key]
    return COST_BPS["fx_cross"]


# ---------------------------------------------------------------- Ideen laden

def load_ideas(until: str | None = None, folder: Path | None = None) -> pd.DataFrame:
    rows = []
    for f in sorted((folder or EXTRACTED).glob("*.json")):
        r = load(f)
        if r.report_date and (pd.Timestamp(r.posted_utc).tz_convert(None).normalize()
                              - pd.Timestamp(r.report_date)) > pd.Timedelta(days=STALE_DAYS):
            continue  # alter Report erneut gepostet (z. B. 4850: 01.04. am 13.05.) -- kein neuer Call
        for i, idea in enumerate(r.ideas):
            d = idea.model_dump()
            d.update(msg_id=r.msg_id, posted=pd.Timestamp(r.posted_utc), generation=r.generation, idea_no=i)
            rows.append(d)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if until:
        df = df[df.posted < pd.Timestamp(until, tz="UTC") + pd.Timedelta(days=1)]
    return df.sort_values(["posted", "idea_no"]).reset_index(drop=True)


def report_times(ideas: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(ideas.posted.unique())


def drop_two_way(ideas: pd.DataFrame) -> pd.DataFrame:
    """Zwei-Wege-Setups (gleiches Instrument long UND short im selben Report) sind keine
    Richtungsaussage -- fuer A1/A2/B raus, sonst hoben sie sich zu reinen Kosten auf.
    Ausnahme: ist nur EINE Seite unbedingt (aktiv/bias) und die andere bedingt
    (vorbereitet/watch/inaktiv), ist das ein aktueller Call plus Plan B -> unbedingte Seite bleibt.
    Festgelegt 2026-10-10 vor dem ersten Lauf (siehe Lock-Protokoll smh_macro_reports)."""
    d = ideas.copy()
    d["_uncond"] = d.status.isin(["aktiv", "bias"])
    g = d.groupby(["msg_id", "instrument"])
    n_dir = g.direction.transform("nunique")
    n_uncond_dir = d[d._uncond].groupby(["msg_id", "instrument"]).direction.nunique()
    key = list(zip(d.msg_id, d.instrument))
    uncond_dirs = d.assign(_k=key).set_index("_k").index.map(lambda k: n_uncond_dir.get(k, 0))
    keep = (n_dir < 2) | ((uncond_dirs == 1) & d._uncond.to_numpy())
    return d[keep].drop(columns="_uncond")


def pick_main(ideas: pd.DataFrame) -> pd.DataFrame:
    """Eine Idee je Report: main > hoechste Konfidenz > erste."""
    cand = ideas[ideas.status != "inaktiv"].copy()
    cand["_r"] = (cand.role != "main").astype(int)
    cand["_c"] = cand.confidence.map(lambda c: CONF_ORDER.get(c, 5))
    return cand.sort_values(["msg_id", "_r", "_c", "idea_no"]).groupby("msg_id").head(1).drop(columns=["_r", "_c"])


# ---------------------------------------------------------------- Kursdaten

class Prices:
    def __init__(self, start: str, end: str):
        self.start, self.end = start, end
        self._h1: dict[str, pd.DataFrame] = {}
        self._d1: dict[str, pd.DataFrame] = {}
        self.missing: set[str] = set()

    def _get(self, key, tf, store):
        if key not in store:
            if not _register_instrument(key):
                self.missing.add(key)
                store[key] = None
            else:
                try:
                    store[key] = cdata.fetch_timeframe(key, tf, self.start, self.end)
                except Exception:
                    self.missing.add(key)
                    store[key] = None
        return store[key]

    def h1(self, key):
        return self._get(key, "H1", self._h1)

    def d1(self, key):
        return self._get(key, "D1", self._d1)

    def atr(self, key, before: pd.Timestamp, n: int = 20) -> float | None:
        d = self.d1(key)
        if d is None:
            return None
        d = d[d.index < before.normalize()]
        if len(d) < n + 1:
            return None
        tr = pd.concat([d.High - d.Low, (d.High - d.Close.shift()).abs(), (d.Low - d.Close.shift()).abs()],
                       axis=1).max(axis=1)
        return float(tr.iloc[-n:].mean())


def _first_bar_after(h1: pd.DataFrame, t: pd.Timestamp) -> int | None:
    """Index der ersten H1-Bar, deren Start NACH t liegt (Postzeit ist nie Teil der Einstiegsbar)."""
    i = h1.index.searchsorted(t, side="right")
    return int(i) if i < len(h1) else None


def _add_business_days(t: pd.Timestamp, n: int) -> pd.Timestamp:
    return t + pd.offsets.BDay(n)


# ---------------------------------------------------------------- Trades

@dataclass
class Trade:
    variant: str
    msg_id: int
    generation: int
    instrument: str
    direction: str
    role: str
    status: str
    confidence: str | None
    entry_time: pd.Timestamp
    entry: float
    exit_time: pd.Timestamp
    exit: float
    risk: float
    r_gross: float
    r_net: float
    exit_reason: str


def _make(variant, idea, h1, i_in, i_out_price, exit_time, exit_reason, risk, key, entry=None) -> Trade:
    sign = 1 if idea.direction == "long" else -1
    entry = float(h1.Open.iloc[i_in]) if entry is None else float(entry)
    r_gross = sign * (i_out_price - entry) / risk
    cost_r = cost_bps(key) / 10_000 * entry / risk
    return Trade(variant, int(idea.msg_id), int(idea.generation), key, idea.direction, idea.role, idea.status,
                 idea.confidence, h1.index[i_in], entry, exit_time, float(i_out_price), float(risk),
                 float(r_gross), float(r_gross - cost_r), exit_reason)


def _hold_until(variant, idea, px: Prices, exit_at: pd.Timestamp) -> Trade | None:
    key = idea.instrument
    h1 = px.h1(key)
    if h1 is None:
        return None
    i_in = _first_bar_after(h1, idea.posted)
    i_out = _first_bar_after(h1, exit_at)
    if i_in is None or i_out is None or i_out <= i_in:
        return None
    risk = (px.atr(key, h1.index[i_in]) or np.nan) * ATR_MULT
    if not np.isfinite(risk) or risk <= 0:
        return None
    return _make(variant, idea, h1, i_in, float(h1.Open.iloc[i_out]), h1.index[i_out], "next_report", risk, key)


def _level_trade(variant, idea, px: Prices, i_in: int, stop_hint: float | None,
                 entry: float | None = None) -> Trade | None:
    key = idea.instrument
    h1 = px.h1(key)
    sign = 1 if idea.direction == "long" else -1
    entry = float(h1.Open.iloc[i_in]) if entry is None else float(entry)
    atr_risk = (px.atr(key, h1.index[i_in]) or np.nan) * ATR_MULT
    def plausible(x):
        return x is not None and abs(x / entry - 1) <= MAX_LEVEL_DIST

    if plausible(stop_hint) and sign * (entry - stop_hint) > 0:
        stop = float(stop_hint)
    elif np.isfinite(atr_risk) and atr_risk > 0:
        stop = entry - sign * atr_risk
    else:
        return None
    risk = abs(entry - stop)
    wins = [t for t in (idea.targets or []) if plausible(t) and sign * (t - entry) > 0]
    target = (min(wins, key=lambda t: abs(t - entry)) if wins else entry + sign * DEFAULT_TARGET_R * risk)
    t_end = _add_business_days(h1.index[i_in], TIME_EXIT_DAYS)
    path = h1.iloc[i_in:]
    for ts, bar in path.iterrows():
        if ts >= t_end:
            return _make(variant, idea, h1, i_in, float(bar.Open), ts, "time", risk, key, entry)
        hit_stop = bar.Low <= stop if sign > 0 else bar.High >= stop
        hit_tgt = bar.High >= target if sign > 0 else bar.Low <= target
        if hit_stop:  # Stop zuerst, auch wenn das Ziel in derselben Bar liegt
            return _make(variant, idea, h1, i_in, stop, ts, "stop", risk, key, entry)
        if hit_tgt:
            return _make(variant, idea, h1, i_in, target, ts, "target", risk, key, entry)
    return None  # Daten enden vor dem Ausstieg -> offener Trade, nicht gewertet


LIMIT_ATR = 0.5        # D: Limit so viel ATR besser als der Markt (Rücksetzer-Einstieg)
LIMIT_VALID_DAYS = 3   # D: Limit-Order gilt so viele Handelstage
UNCONDITIONAL = ("aktiv", "bias")


def select_ideas(variant: str, ideas: pd.DataFrame, mode: str = "v1") -> pd.DataFrame:
    """Welche Ideen eine Variante handelt.
    v1: alles ausser inaktiv. v2 (Nutzerdefinition 16.10.): A1/A2/B/D nur unbedingte
    Richtungs-Calls (aktiv, bias) ohne Hedges; C nur Generation 3 mit numerischer Aktivierung."""
    if variant == "C":
        return ideas[(ideas.generation == 3) & ideas.activation_price.notna()]
    d = drop_two_way(ideas)
    if mode == "v1":
        d = d[d.status != "inaktiv"]
        return pick_main(d) if variant == "A2" else d
    d = d[d.status.isin(UNCONDITIONAL) & (d.role != "hedge")]
    return pick_main(d) if variant == "A2" else d


def _limit_trade(idea, px: Prices) -> Trade | None:
    """D: Limit LIMIT_ATR x ATR besser als die erste Eröffnung nach Postzeit, gültig
    LIMIT_VALID_DAYS Handelstage; Füllung zum Limit; danach Exits wie B (Stop/Ziel aus
    dem Füllkurs, Stop zuerst in derselben Bar)."""
    key = idea.instrument
    h1 = px.h1(key)
    if h1 is None:
        return None
    i0 = _first_bar_after(h1, idea.posted)
    if i0 is None:
        return None
    atr = px.atr(key, h1.index[i0])
    if not atr:
        return None
    sign = 1 if idea.direction == "long" else -1
    limit = float(h1.Open.iloc[i0]) - sign * LIMIT_ATR * atr
    t_end = _add_business_days(h1.index[i0], LIMIT_VALID_DAYS)
    for k in range(i0, len(h1)):
        ts = h1.index[k]
        if ts >= t_end:
            return None
        bar = h1.iloc[k]
        if (sign > 0 and bar.Low <= limit) or (sign < 0 and bar.High >= limit):
            fill = min(limit, float(bar.Open)) if sign > 0 else max(limit, float(bar.Open))
            return _level_trade("D", idea, px, k, idea.stop, entry=fill)
    return None


def run_variant(variant: str, ideas: pd.DataFrame, px: Prices, mode: str = "v1") -> pd.DataFrame:
    times = report_times(ideas)
    nxt = {t: (times[k + 1] if k + 1 < len(times) else None) for k, t in enumerate(times)}
    trades = []
    for idea in select_ideas(variant, ideas, mode).itertuples():
        if variant in ("A1", "A2"):
            if nxt[idea.posted] is None:
                continue
            t = _hold_until(variant, idea, px, nxt[idea.posted])
        elif variant == "B":
            h1 = px.h1(idea.instrument)
            i_in = None if h1 is None else _first_bar_after(h1, idea.posted)
            t = None if i_in is None else _level_trade(variant, idea, px, i_in, idea.stop)
        elif variant == "C":
            t = _activation_trade(idea, px)
        elif variant == "D":
            t = _limit_trade(idea, px)
        else:
            raise ValueError(variant)
        if t is not None:
            trades.append(t)
    return pd.DataFrame([t.__dict__ for t in trades])


def _activation_trade(idea, px: Prices) -> Trade | None:
    key = idea.instrument
    d1, h1 = px.d1(key), px.h1(key)
    if d1 is None or h1 is None:
        return None
    window = d1[(d1.index > idea.posted.normalize()) &
                (d1.index <= _add_business_days(idea.posted.normalize(), ACTIVATION_WINDOW_DAYS))]
    lvl = idea.activation_price
    hit = window[window.Close < lvl] if idea.activation_side == "below" else window[window.Close > lvl]
    if hit.empty:
        return None
    close_time = hit.index[0] + pd.Timedelta(days=1)  # D1-Bar schliesst einen Tag nach ihrem Start
    i_in = _first_bar_after(h1, close_time - pd.Timedelta(seconds=1))
    if i_in is None:
        return None
    return _level_trade("C", idea, px, i_in, idea.invalidation_price)


# ---------------------------------------------------------------- Kontrollen + Kennzahlen

def momentum_control(trades: pd.DataFrame, px: Prices, lookback: int = 20) -> pd.DataFrame:
    """Gleiche Ein-/Ausstiege wie A1, Richtung = Vorzeichen der 20-Tage-Rendite."""
    out = trades.copy()
    signs = []
    for t in out.itertuples():
        d = px.d1(t.instrument)
        d = d[d.index < t.entry_time.normalize()]
        signs.append(np.sign(d.Close.iloc[-1] - d.Close.iloc[-1 - lookback]) if len(d) > lookback else 0)
    s = np.array(signs)
    orig = np.where(out.direction == "long", 1, -1)
    cost = out.r_gross - out.r_net
    out["r_gross"] = out.r_gross * orig * s
    out["r_net"] = out.r_gross - cost
    out["variant"] = "MOM20"
    return out


def permutation_p(trades: pd.DataFrame, n: int = 1000, seed: int = 7) -> float:
    """Anteil zufaelliger Vorzeichen-Folgen mit mindestens so hohem Ø R netto."""
    rng = np.random.default_rng(seed)
    g, cost = trades.r_gross.to_numpy(), (trades.r_gross - trades.r_net).to_numpy()
    obs = (g - cost).mean()
    sims = [(g * rng.choice([-1, 1], size=len(g)) - cost).mean() for _ in range(n)]
    return float((np.sum(np.array(sims) >= obs) + 1) / (n + 1))


def metrics(trades: pd.DataFrame, col: str = "r_net") -> dict:
    if trades.empty:
        return {"n": 0}
    r = trades[col]
    eq = r.cumsum()
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return {
        "n": int(len(r)), "hit": round(float((r > 0).mean()), 3), "mean_r": round(float(r.mean()), 3),
        "sum_r": round(float(r.sum()), 1), "pf": round(float(pos / neg), 2) if neg > 0 else None,
        "t": round(float(r.mean() / r.std(ddof=1) * np.sqrt(len(r))), 2) if len(r) > 2 and r.std() > 0 else None,
        "max_dd_r": round(float((eq.cummax() - eq).max()), 1),
    }


def breakdown(trades: pd.DataFrame, by: str) -> pd.DataFrame:
    return pd.DataFrame({k: metrics(g) for k, g in trades.groupby(by)}).T


def instrument_class(key: str) -> str:
    if key in _MAJORS:
        return "fx_major"
    if key in _INDICES:
        return "index"
    if key in {"GOLD", "SILVER", "COPPER"}:
        return "metal"
    if key in {"OIL", "BRENT"}:
        return "energy"
    if key == "DXY":
        return "dxy"
    return "fx_cross" if len(key) == 6 else "other"


def save(df: pd.DataFrame, name: str) -> Path:
    p = DATA_DIR / "results" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p


def dump_json(obj, name: str) -> Path:
    p = DATA_DIR / "results" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return p
