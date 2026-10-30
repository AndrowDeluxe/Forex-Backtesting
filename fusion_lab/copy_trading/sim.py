"""Stufe 1 (nackt) der Edge Card „Copy Trading Daily Update“, Regeln 1-15.

Eingang: fusion_lab/data/copy_trading/calls.jsonl (extract.py). Je gelesenem Setup:
  - Regel 3: nur Calls, die nach rechts in die Zukunft ragen und deren Entry/Zone
    zwischen Chart-Erstellung und Postzeit nicht beruehrt wurde (mit Kursdaten geprueft).
  - Regel 4-6: Update = Chartposts desselben Absenders mit <= 60 Min. Abstand; eine Order
    gilt bis zum naechsten Update desselben Absenders oder bis zum naechsten Call aufs
    selbe Symbol (gleich welcher Absender). Aktiv ab Postzeit + LAG.
  - Regel 8: Swings und ATR14 im Timeframe des Chartbilds; Bestaetigung auf M5; Ein- und
    Ausstieg minutengenau auf M1 (entspricht HTF-Kerzen mit M1 fuer die Reihenfolge).
    SL und TP in derselben M1-Kerze: SL. In der Fuellkerze zaehlt nur der SL.
  - Regel 9-13: 20 Varianten (A1/A2, B1/B2 x SL a/b/c x TP a/b/c).

Umsetzungsdetails, die die Karte offen laesst (ANNAHME 20.10.2026, im Bericht genannt):
  - Wird der SL der Variante vor dem Einstieg erreicht, entfaellt der Trade (Setup tot).
  - Ein Trade ohne SL/TP bis Datenende wird zum letzten Kurs bewertet (offen=True).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fusion_lab.copy_trading import data
from gold_smc_htf_ltf.structure import detect_fractal_swings

K_SWING = 2
UPDATE_GAP = pd.Timedelta(minutes=60)
LAG = pd.Timedelta(minutes=5)
MAX_DIST = 0.06          # Entry/Zone weiter als 6 % vom Kurs: Lesefehler oder falsches Symbol
SL_VARIANTS = ("a", "b", "c")
TP_VARIANTS = ("a", "b", "c")
MONTHS = {"Jan": 1, "Feb": 2, "Mär": 3, "Mar": 3, "Apr": 4, "Mai": 5, "May": 5, "Jun": 6, "Jul": 7,
          "Aug": 8, "Sep": 9, "Okt": 10, "Oct": 10, "Nov": 11, "Dez": 12, "Dec": 12}


# ----------------------------------------------------------------------------- Calls
def parse_created(s: str | None) -> pd.Timestamp | None:
    """'Okt 08, 2026 23:49 UTC+2' -> UTC-Zeitstempel."""
    if not s:
        return None
    import re
    m = re.match(r"(\w{3})\w*\.? (\d{1,2}), (\d{4}) (\d{1,2}):(\d{2}) UTC([+-]\d+)", s.strip())
    if not m or m.group(1) not in MONTHS:
        return None
    mon, d, y, hh, mm, off = m.groups()
    t = pd.Timestamp(int(y), MONTHS[mon], int(d), int(hh), int(mm), tz="UTC")
    return t - pd.Timedelta(hours=int(off))


@dataclass
class Call:
    msg_id: int
    t_post: pd.Timestamp
    sender: int
    sym: str
    tf: str
    typ: str
    d: int                      # +1 long, -1 short
    t_chart: pd.Timestamp | None
    entry: float | None = None
    sl: float | None = None
    tp: float | None = None
    z_hi: float | None = None
    z_lo: float | None = None
    path_end: float | None = None
    t_valid: pd.Timestamp | None = None
    drop: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def level(self) -> float:
        """Statischer Einstieg: Entry-Label (A) bzw. Zonenmitte (B); beim Pfad-Trade (P) das Ziel."""
        if self.typ == "P":
            return self.tp
        return self.entry if self.typ == "A" else (self.z_hi + self.z_lo) / 2

    @property
    def touch(self) -> float:
        """Beruehrungspreis: Entry-Label (A) bzw. naher Zonenrand (B)."""
        if self.typ == "A":
            return self.entry
        return self.z_hi if self.d > 0 else self.z_lo


def _num(x):
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def norm_tf(raw: str | None) -> str:
    """'4h', 'H4', '240', '30', '1D', 'D' -> TF_RULE-Schluessel."""
    import re
    s = (raw or "").upper().replace("MIN", "M").strip()
    if s in data.TF_RULE:
        return s
    if s in ("D", "1D", "TAG"):
        return "D1"
    if s in ("W", "1W"):
        return "W1"
    m = re.fullmatch(r"(\d+)\s*([MHD]?)", s) or re.fullmatch(r"([MHD])(\d+)", s)
    if not m:
        return s
    a, b = m.groups()
    n, unit = (int(a), b) if a.isdigit() else (int(b), a)
    if unit in ("", "M"):
        return f"H{n // 60}" if n % 60 == 0 and n >= 60 else f"M{n}"
    return f"{unit}{n}" if unit == "H" else f"D{n}"


def load_calls(path) -> tuple[list[Call], pd.DataFrame]:
    """Calls aus calls.jsonl plus Protokoll aller Bilder (warum verworfen)."""
    from fusion_lab.copy_trading.extract import latest
    rows, calls = [], []
    for r in latest(path):
        x = r.get("read") or {}
        base = {"msg_id": r["msg_id"], "date": r["date"], "sender": r["sender_id"],
                "symbol_read": x.get("symbol"), "is_call": x.get("is_call"),
                "no_call_reason": x.get("no_call_reason")}
        if not x.get("is_call"):
            rows.append({**base, "status": "kein Call"})
            continue
        sym = data.norm_symbol(x.get("symbol"))
        tf = norm_tf(x.get("chart_tf"))
        for k, s in enumerate(x.get("setups") or []):
            c = Call(msg_id=r["msg_id"], t_post=pd.Timestamp(r["date"]), sender=r["sender_id"],
                     sym=sym, tf=tf, typ=s.get("type"),
                     d=DIRS.get(s.get("direction"), 0),
                     t_chart=parse_created(x.get("chart_created")),
                     entry=_num(s.get("entry")), sl=_num(s.get("sl")), tp=_num(s.get("tp")),
                     z_hi=_num(s.get("zone_top")), z_lo=_num(s.get("zone_bottom")),
                     path_end=_num(s.get("path_end")),
                     extra={"setup": k, "extends_right": x.get("extends_right"),
                            "confidence": x.get("confidence"), "estimated": s.get("estimated"),
                            "status": s.get("status", "new"), "order_type": s.get("order_type"),
                            "alt": s.get("alternative_group"),
                            "prompt_version": r.get("prompt_version", 1),
                            "leg1": DIRS.get(s.get("leg1_direction"), 0),
                            "turn": _num(s.get("turn_price"))})
            if c.z_hi is not None and c.z_lo is not None and c.z_hi < c.z_lo:
                c.z_hi, c.z_lo = c.z_lo, c.z_hi
            if c.typ == "B":
                p = path_call(c)
                if p is not None:
                    p.drop = _static_check(p, x)
                    calls.append(p)
                zone_from_turn(c)
            c.drop = _static_check(c, x)
            calls.append(c)
    return calls, pd.DataFrame(rows)


DIRS = {"long": 1, "up": 1, "short": -1, "down": -1}


def zone_from_turn(c: Call) -> None:
    """Zonen-Trade (Lesart 2, Nutzer 21.10.): Die Zone gilt als Einstieg nur, wenn der
    gemalte Umkehrpunkt in ihr liegt (Toleranz 1/4 Zonenbreite). Sonst Limit am Umkehrpunkt."""
    turn = c.extra.get("turn")
    if turn is None:
        return
    if c.z_hi is None or c.z_lo is None:
        c.z_hi = c.z_lo = turn
        return
    tol = 0.25 * (c.z_hi - c.z_lo)
    if not (c.z_lo - tol <= turn <= c.z_hi + tol):
        c.extra["zone_ersetzt"] = (c.z_lo, c.z_hi)
        c.z_hi = c.z_lo = turn


def path_call(c: Call) -> "Call | None":
    """Pfad-Trade (Lesart 1, Nutzer 21.10.): Einstieg zum Markt beim Post in Richtung des
    ersten Pfadschenkels; Ziel = Umkehrpunkt, sonst naher Zonenrand, sonst Pfadende."""
    import copy
    leg1 = c.extra.get("leg1") or 0
    if not leg1:
        return None
    target = c.extra.get("turn")
    if target is None and c.z_hi is not None and c.z_lo is not None:
        target = c.z_lo if leg1 > 0 else c.z_hi
    if target is None:
        target = c.path_end
    if target is None:
        return None
    p = copy.copy(c)
    p.extra = dict(c.extra)
    p.typ, p.d, p.tp, p.entry, p.sl = "P", leg1, target, None, None
    return p


def _static_check(c: Call, x: dict) -> str | None:
    if c.extra.get("status") not in (None, "new"):
        return f"Setup nicht neu ({c.extra['status']})"
    if c.extra.get("order_type") == "stop":
        return "Stop-Order (nicht in der Edge Card)"
    if c.sym is None:
        return "Symbol nicht handelbar/unbekannt"
    if c.tf not in data.TF_RULE:
        return f"Timeframe unbekannt ({c.tf})"
    if c.d == 0 or c.typ not in ("A", "B", "P"):
        return "Typ/Richtung fehlt"
    if not x.get("extends_right"):
        return "ragt nicht nach rechts (Regel 3)"
    if c.typ == "P":
        return None
    if c.typ == "A":
        if None in (c.entry, c.sl, c.tp):
            return "Level fehlen"
        if not ((c.sl - c.entry) * c.d < 0 < (c.tp - c.entry) * c.d):
            return "SL/TP liegen falsch zur Richtung"
    else:
        if None in (c.z_hi, c.z_lo):
            return "Zone fehlt"
    return None


def assign_validity(calls: list[Call], end: pd.Timestamp) -> None:
    """Regel 4/6: Gueltigkeit bis naechstes Update desselben Absenders bzw. naechster Call
    aufs selbe Symbol."""
    posts = pd.DataFrame({"t": [c.t_post for c in calls], "sender": [c.sender for c in calls]})
    upd_start = {}
    for sender, g in posts.sort_values("t").groupby("sender"):
        ts = sorted(set(g["t"]))
        starts = [ts[0]] + [b for a, b in zip(ts, ts[1:]) if b - a > UPDATE_GAP]
        upd_start[sender] = starts
    for c in calls:
        own = max(s for s in upd_start[c.sender] if s <= c.t_post)
        later = [s for s in upd_start[c.sender] if s > own]
        t1 = later[0] if later else end
        same = [o.t_post for o in calls if o.sym == c.sym and o.t_post > c.t_post and o.drop is None]
        if same:
            t1 = min(t1, min(same))
        c.t_valid = t1


# ----------------------------------------------------------------------------- Struktur
class Market:
    """M1 eines Instruments plus abgeleitete Timeframes (Swings k=2, ATR14), gecacht."""

    def __init__(self, sym: str):
        self.sym = sym
        self.m1 = data.load(sym)
        self._tf = {}

    def tf(self, name: str) -> pd.DataFrame:
        if name not in self._tf:
            df = data.resample(self.m1, name)
            df = detect_fractal_swings(df, k=K_SWING)
            tr = pd.concat([df["high"] - df["low"], (df["high"] - df["close"].shift()).abs(),
                            (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
            df["atr14"] = tr.rolling(14).mean()
            df["t_close"] = df.index + pd.Timedelta(data.TF_RULE[name] if name != "W1" else "7D")
            self._tf[name] = df
        return self._tf[name]

    def price_at(self, t: pd.Timestamp) -> float | None:
        i = self.m1.index.searchsorted(t, side="right") - 1
        return float(self.m1["close"].iat[i]) if i >= 0 else None


def htf_level(mk: Market, tf: str, t: pd.Timestamp, ref: float, side: str) -> float | None:
    """Naechstes bestaetigtes Chart-TF-Swing-Low unter ref (side='low') bzw. -High ueber ref,
    nur Swings, die bis t bestaetigt waren (letzte 300 Kerzen)."""
    df = mk.tf(tf)
    df = df[df["t_close"] <= t].tail(300)
    if side == "low":
        px = df.loc[df["swing_low_confirmed"], "swing_low_price"]
        px = px[px < ref]
        return float(px.max()) if len(px) else None
    px = df.loc[df["swing_high_confirmed"], "swing_high_price"]
    px = px[px > ref]
    return float(px.min()) if len(px) else None


def atr_at(mk: Market, tf: str, t: pd.Timestamp) -> float | None:
    df = mk.tf(tf)
    df = df[df["t_close"] <= t]
    return float(df["atr14"].iat[-1]) if len(df) and pd.notna(df["atr14"].iat[-1]) else None


# ----------------------------------------------------------------------------- Einstieg
def first_touch(m1: pd.DataFrame, t0, t1, px: float, d: int) -> pd.Timestamp | None:
    """Erste M1-Kerze in [t0, t1), die px von der Gegenseite erreicht (Long: low <= px)."""
    w = m1.loc[t0:t1]
    w = w[w.index < t1]
    hit = w["low"] <= px if d > 0 else w["high"] >= px
    return hit.idxmax() if hit.any() else None


def static_entry(mk: Market, c: Call, t_act) -> tuple[pd.Timestamp, float] | None:
    t = first_touch(mk.m1, t_act, c.t_valid, c.level, c.d)
    if t is None:
        return None
    o = mk.m1.at[t, "open"]
    fill = min(o, c.level) if c.d > 0 else max(o, c.level)   # Gap ueber den Limit: Eroeffnungskurs
    return t, float(fill)


def bos_entry(mk: Market, c: Call, t_act) -> tuple[pd.Timestamp, float] | None:
    """Regel 10: nach Beruehrung zwei M5-Kerzenschluesse jenseits je eines neu gebildeten
    Swings in Call-Richtung (Fraktal k=2, nur Swings nach der Beruehrung)."""
    t_touch = first_touch(mk.m1, t_act, c.t_valid, c.touch, c.d)
    if t_touch is None:
        return None
    m5 = mk.tf("M5")
    w = m5[(m5.index >= t_touch.floor("5min")) & (m5["t_close"] <= c.t_valid)]
    if w.empty:
        return None
    # Swing-Bar-Zeit = Bestaetigungskerze - k; nur Swings, deren Extrem nach der Beruehrung liegt
    conf = "swing_high_confirmed" if c.d > 0 else "swing_low_confirmed"
    spx = "swing_high_price" if c.d > 0 else "swing_low_price"
    # Ein Swing zaehlt, wenn seine Extremkerze (Bestaetigung - k) nach der Beruehrung liegt,
    # fuer den zweiten BOS nach der Kerze des ersten Bruchs.
    level, n_bos, min_bar = None, 0, 0
    for i in range(len(w)):
        row = w.iloc[i]
        if level is not None and (row["close"] - level) * c.d > 0:
            n_bos += 1
            if n_bos == 2:
                return row["t_close"], float(row["close"])
            level, min_bar = None, i + 1
        if row[conf] and i - K_SWING >= min_bar:
            level = row[spx]          # juengster bestaetigter Swing seit Beruehrung bzw. 1. Bruch
    return None


# ----------------------------------------------------------------------------- Ausstieg
def run_trade(mk: Market, d: int, t_in, p_in, sl, tp, entry_is_close: bool):
    """Minutengenau ab Einstieg. entry_is_close: Einstieg zum Kerzenschluss (BOS) -> Pruefung
    ab der naechsten M1-Kerze; sonst Fuellkerze: nur SL zaehlt."""
    m1 = mk.m1
    hi, lo, cl = m1["high"].to_numpy(), m1["low"].to_numpy(), m1["close"].to_numpy()
    i0 = m1.index.searchsorted(t_in)   # BOS: t_in = Schlusszeit, i0 ist die naechste Kerze
    start = i0
    if not entry_is_close:              # Fuellkerze: nur der SL zaehlt
        if (lo[i0] <= sl) if d > 0 else (hi[i0] >= sl):
            return m1.index[i0], sl, "SL"
        start = i0 + 1
    for i in range(start, len(m1)):
        sl_hit = lo[i] <= sl if d > 0 else hi[i] >= sl
        tp_hit = hi[i] >= tp if d > 0 else lo[i] <= tp
        if sl_hit:
            o = m1["open"].iat[i]
            px = min(o, sl) if d > 0 else max(o, sl)       # Gap durch den SL: Eroeffnungskurs
            return m1.index[i], float(px), "SL"
        if tp_hit:
            return m1.index[i], tp, "TP"
    return m1.index[-1], float(cl[-1]), "offen"


def stops_targets(mk: Market, c: Call, t_in, p_in) -> dict:
    """SL/TP je Variante; None = fuer diesen Call nicht bestimmbar."""
    if c.typ == "A":
        return {("A", "A"): (c.sl, c.tp)}
    sl = {"a": c.z_lo if c.d > 0 else c.z_hi,
          "b": htf_level(mk, c.tf, t_in, p_in, "low" if c.d > 0 else "high"),
          "c": None}
    atr = atr_at(mk, c.tf, t_in)
    if atr:
        sl["c"] = p_in - c.d * 2 * atr
    out = {}
    for sk, s in sl.items():
        if s is None or (p_in - s) * c.d <= 0:
            continue
        risk = abs(p_in - s)
        tps = {"a": p_in + c.d * 2 * risk,
               "b": c.path_end,
               "c": htf_level(mk, c.tf, t_in, p_in, "high" if c.d > 0 else "low")}
        for tk, t in tps.items():
            if t is not None and (t - p_in) * c.d > 0:
                out[(sk, tk)] = (s, t)
    return out


def simulate(calls: list[Call], lag=LAG) -> tuple[pd.DataFrame, pd.DataFrame]:
    markets: dict[str, Market] = {}
    trades, audit = [], []
    for c in calls:
        rec = {"msg_id": c.msg_id, "setup": c.extra["setup"], "t_post": c.t_post, "sym": c.sym,
               "tf": c.tf, "typ": c.typ, "dir": c.d, "sender": c.sender, "drop": c.drop}
        if c.typ == "P":
            continue
        if c.drop:
            audit.append(rec)
            continue
        if c.sym not in markets:
            markets[c.sym] = Market(c.sym)
        mk = markets[c.sym]
        px = mk.price_at(c.t_post)
        if px is None or abs(c.level / px - 1) > MAX_DIST:
            rec["drop"] = "Level weit weg vom Kurs (Lesefehler/Feed)"
            audit.append(rec)
            continue
        if c.typ == "B" and (px - c.level) * c.d <= 0:
            rec["drop"] = "Zone nicht auf der Ruecksetzer-Seite"
            audit.append(rec)
            continue
        # Regel 3: zwischen Chart-Erstellung und Post darf der Beruehrungspreis nicht erreicht sein
        t_chart = c.t_chart if c.t_chart is not None and c.t_chart <= c.t_post else c.t_post - pd.Timedelta(minutes=30)
        if first_touch(mk.m1, t_chart, c.t_post, c.touch, c.d) is not None:
            rec["drop"] = "Entry/Zone schon vor dem Post erreicht (Regel 3)"
            audit.append(rec)
            continue
        t_act = c.t_post + lag
        audit.append({**rec, "t_valid": c.t_valid})
        for mode, fn in (("1", static_entry), ("2", bos_entry)):
            e = fn(mk, c, t_act)
            if e is None:
                continue
            t_in, p_in = e
            for (sk, tk), (sl, tp) in stops_targets(mk, c, t_in, p_in).items():
                # Setup tot, wenn der SL vor dem Einstieg erreicht wurde (nur BOS relevant)
                if mode == "2" and first_touch(mk.m1, t_act, t_in, sl, c.d) is not None:
                    continue
                if (p_in - sl) * c.d <= 0 or (tp - p_in) * c.d <= 0:
                    continue
                t_out, p_out, why = run_trade(mk, c.d, t_in, p_in, sl, tp, entry_is_close=(mode == "2"))
                risk = abs(p_in - sl)
                cost = data.roundtrip_cost(c.sym, p_in)
                r_gross = (p_out - p_in) * c.d / risk
                variant = f"{c.typ}{mode}" + ("" if c.typ == "A" else f"_SL{sk}_TP{tk}")
                trades.append({**rec, "variant": variant, "t_in": t_in, "p_in": p_in, "sl": sl, "tp": tp,
                               "t_out": t_out, "p_out": p_out, "exit": why, "risk": risk,
                               "r_gross": r_gross, "r": r_gross - cost / risk,
                               "cost_r": cost / risk, "offen": why == "offen"})
    return pd.DataFrame(trades), pd.DataFrame(audit)


def all_variants() -> list[str]:
    v = ["A1", "A2"]
    for m in ("1", "2"):
        v += [f"B{m}_SL{s}_TP{t}" for s in SL_VARIANTS for t in TP_VARIANTS]
    return v


def summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for v in all_variants():
        t = trades[trades["variant"] == v] if len(trades) else trades
        r = t["r"] if len(t) else pd.Series(dtype=float)
        n = len(r)
        sd = r.std(ddof=1) if n > 1 else np.nan
        rows.append({"variant": v, "n": n, "treffer": (r > 0).mean() if n else np.nan,
                     "avg_r": r.mean() if n else np.nan, "sum_r": r.sum(),
                     "t": r.mean() / sd * np.sqrt(n) if n > 1 and sd > 0 else np.nan,
                     "avg_r_brutto": t["r_gross"].mean() if n else np.nan,
                     "offen": int(t["offen"].sum()) if n else 0,
                     "bewertet": n >= 100})
    return pd.DataFrame(rows)
