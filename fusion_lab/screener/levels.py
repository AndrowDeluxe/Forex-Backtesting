"""Technik + Preisbereiche, deterministisch aus Tageskerzen (kein LLM).

Marken: Swing-Hochs/-Tiefs, SMA20/50/200, Volumenprofil-Knoten, 52-Wochen-Hoch/-Tief, Kursluecken.
Marken naeher als CLUSTER_ATR werden zu Zonen zusammengefasst. Daraus bis zu drei Szenarien:

  A  Ruecksetzer: Limit-Kauf in der naechsten Unterstuetzungszone 0,5-2,5 ATR unter Kurs,
     Stopp = Zonenunterkante - 1 ATR.
  B  Ausbruch: Stop-Kauf ueber dem naechsten Widerstand (+0,1 ATR), hoechstens 3 ATR entfernt,
     Stopp = Trigger - 1,5 ATR.
  C  Abwarten (immer).

Ziel = erster Widerstand mit Chance-Risiko >= MIN_RR (unter den naechsten MAX_TARGETS); ohne solchen
Widerstand ist das Szenario ungueltig. Bei B ueber allen Widerstaenden (Allzeithoch): Ziel = Trigger + 3 ATR.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.screener import config as C


# ------------------------------------------------------------------ Indikatoren

def sma(c: pd.Series, n: int) -> pd.Series:
    return c.rolling(n).mean()


def rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(d: pd.DataFrame, n: int = C.ATR_N) -> pd.Series:
    pc = d["Close"].shift(1)
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - pc).abs(), (d["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def macd(c: pd.Series) -> tuple[pd.Series, pd.Series]:
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    return m, m.ewm(span=9, adjust=False).mean()


def technicals(d: pd.DataFrame) -> dict:
    """Kennzahlen fuer Bericht und Score. d: OHLCV-Tageskerzen, aufsteigend."""
    c = d["Close"]
    last = float(c.iloc[-1])
    a = atr(d)
    m, s = macd(c)
    out = {"close": last, "datum": str(d.index[-1].date()),
           "sma20": _f(sma(c, 20)), "sma50": _f(sma(c, 50)), "sma200": _f(sma(c, 200)),
           "rsi14": _f(rsi(c)), "macd": _f(m), "macd_signal": _f(s), "atr14": _f(a),
           "atr_pct": _f(a / c * 100)}
    y = d.iloc[-252:]
    out["hoch_52w"] = float(y["High"].max())
    out["tief_52w"] = float(y["Low"].min())
    out["abstand_hoch_pct"] = (last / out["hoch_52w"] - 1) * 100
    for n in (5, 21, 63, 126, 252):
        out[f"ret_{n}d"] = float((c.iloc[-1] / c.iloc[-1 - n] - 1) * 100) if len(c) > n else None
    if "Volume" in d and d["Volume"].iloc[-55:-5].mean() > 0:
        out["volumen_5t_vs_50t"] = float(d["Volume"].iloc[-5:].mean() / d["Volume"].iloc[-55:-5].mean())
    return out


def _f(s: pd.Series) -> float | None:
    v = s.iloc[-1]
    return None if pd.isna(v) else float(v)


# ------------------------------------------------------------------ Marken + Zonen

def pivots(d: pd.DataFrame, w: int = C.PIVOT_WINDOW) -> tuple[list[float], list[float]]:
    """Swing-Tiefs/-Hochs der letzten LOOKBACK_BARS (ohne die letzten w Kerzen, die nicht bestaetigt sind)."""
    lo, hi = d["Low"].iloc[-C.LOOKBACK_BARS:].to_numpy(), d["High"].iloc[-C.LOOKBACK_BARS:].to_numpy()
    lows = [float(lo[k]) for k in range(w, len(lo) - w) if lo[k] == lo[k - w:k + w + 1].min()]
    highs = [float(hi[k]) for k in range(w, len(hi) - w) if hi[k] == hi[k - w:k + w + 1].max()]
    return lows, highs


def volume_nodes(d: pd.DataFrame, n_bins: int = 30, top: int = 4) -> list[float]:
    """Preise mit dem meisten Handelsvolumen (Mitte der staerksten Klassen)."""
    if "Volume" not in d or d["Volume"].iloc[-C.LOOKBACK_BARS:].sum() <= 0:
        return []
    x = d.iloc[-C.LOOKBACK_BARS:]
    bins = np.linspace(x["Low"].min(), x["High"].max(), n_bins + 1)
    vp = pd.Series(x["Volume"].to_numpy(), index=pd.cut(x["Close"], bins)).groupby(level=0, observed=False).sum()
    best = vp.sort_values(ascending=False).head(top)
    return [float(iv.mid) for iv in best.index if best[iv] > 0]


def gap_levels(d: pd.DataFrame, a: float, lookback: int = 60) -> list[float]:
    """Offene Kursluecken > 1 ATR der letzten `lookback` Kerzen: Kante der Luecke als Marke."""
    x = d.iloc[-lookback:]
    out = []
    for k in range(1, len(x)):
        prev_c, o = x["Close"].iloc[k - 1], x["Open"].iloc[k]
        if abs(o - prev_c) > a:
            out.append(float(prev_c))
    return out


def levels(d: pd.DataFrame) -> list[dict]:
    """Alle Marken mit Herkunft."""
    c = d["Close"]
    a = float(atr(d).iloc[-1])
    lows, highs = pivots(d)
    out = [{"preis": p, "art": "swing_tief"} for p in lows] + [{"preis": p, "art": "swing_hoch"} for p in highs]
    for n in (20, 50, 200):
        v = sma(c, n).iloc[-1]
        if pd.notna(v):
            out.append({"preis": float(v), "art": f"sma{n}"})
    out += [{"preis": p, "art": "volumen"} for p in volume_nodes(d)]
    out += [{"preis": p, "art": "luecke"} for p in gap_levels(d, a)]
    y = d.iloc[-252:]
    out += [{"preis": float(y["High"].max()), "art": "hoch_52w"}, {"preis": float(y["Low"].min()), "art": "tief_52w"}]
    return out


def clusters(marks: list[dict], a: float) -> list[dict]:
    """Marken naeher als CLUSTER_ATR * ATR zu Zonen zusammenfassen (aufsteigend nach Preis)."""
    if not marks:
        return []
    ms = sorted(marks, key=lambda m: m["preis"])
    groups, cur = [], [ms[0]]
    for m in ms[1:]:
        # naeher als CLUSTER_ATR am Nachbarn UND Zone insgesamt hoechstens MAX_ZONE_ATR breit
        # (sonst ketten sich bei dichten Marken ganze Kursbereiche zu einer Zone zusammen)
        if m["preis"] - cur[-1]["preis"] <= C.CLUSTER_ATR * a and m["preis"] - cur[0]["preis"] <= C.MAX_ZONE_ATR * a:
            cur.append(m)
        else:
            groups.append(cur)
            cur = [m]
    groups.append(cur)
    out = []
    for g in groups:
        lo, hi = min(m["preis"] for m in g), max(m["preis"] for m in g)
        if hi - lo < C.MIN_ZONE_ATR * a:
            mid = (lo + hi) / 2
            lo, hi = mid - C.MIN_ZONE_ATR * a / 2, mid + C.MIN_ZONE_ATR * a / 2
        out.append({"lo": lo, "hi": hi, "mid": (lo + hi) / 2, "staerke": len(g),
                    "arten": sorted({m["art"] for m in g})})
    return out


# ------------------------------------------------------------------ Szenarien

def _target(entry: float, risk: float, resist: list[dict]) -> tuple[float | None, float | None, float | None]:
    """Erstes Ziel mit R >= MIN_RR unter den naechsten MAX_TARGETS Widerstaenden; (ziel, r, ziel2)."""
    cands = [z for z in resist if z["lo"] > entry][: C.MAX_TARGETS]
    for k, z in enumerate(cands):
        r = (z["lo"] - entry) / risk
        if r >= C.MIN_RR:
            nxt = cands[k + 1]["lo"] if k + 1 < len(cands) else None
            return z["lo"], r, nxt
    return None, None, None


def scenarios(d: pd.DataFrame) -> dict:
    """Szenarien A/B/C + Zonen fuer den Chart. Preise auf 4 signifikante Stellen gerundet."""
    a = float(atr(d).iloc[-1])
    px = float(d["Close"].iloc[-1])
    zones = clusters(levels(d), a)
    support = sorted([z for z in zones if z["hi"] < px], key=lambda z: -z["hi"])      # naechste zuerst
    resist = sorted([z for z in zones if z["lo"] > px], key=lambda z: z["lo"])
    out = {"kurs": px, "atr": a, "zonen": [_round_zone(z) for z in zones], "A": None, "B": None,
           "C": {"text": "Abwarten: kein Einstieg mit Chance-Risiko >= 2 oder Lage unklar"}}

    # A: naechste Unterstuetzung, deren Oberkante 0,5-2,5 ATR unter dem Kurs liegt
    for z in support:
        dist = (px - z["hi"]) / a
        if dist < C.A_MIN_ATR:
            continue
        if dist > C.A_MAX_ATR:
            break
        entry = z["mid"]
        stop = z["lo"] - C.STOP_BUFFER_ATR * a
        risk = entry - stop
        tgt, r, t2 = _target(entry, risk, resist)
        if tgt is not None:
            out["A"] = {"typ": "limit", "zone_lo": z["lo"], "zone_hi": z["hi"], "einstieg": entry, "stopp": stop,
                        "ziel": tgt, "ziel2": t2, "rr": r, "marken": z["arten"]}
        break

    # B: Ausbruch ueber den naechsten Widerstand
    if resist:
        z = resist[0]
        trig = z["hi"] + C.B_BUFFER_ATR * a
        if (trig - px) / a <= C.B_MAX_ATR:
            stop = trig - C.B_STOP_ATR * a
            risk = trig - stop
            above = [r for r in resist[1:] if r["lo"] > trig]
            tgt, r, t2 = _target(trig, risk, above)
            if tgt is None and not above:            # ueber allen Widerstaenden: gemessenes Ziel
                tgt, r, t2 = trig + 3 * a, 2.0, None
            if tgt is not None:
                out["B"] = {"typ": "stop", "trigger": trig, "einstieg": trig, "stopp": stop, "ziel": tgt,
                            "ziel2": t2, "rr": r, "marken": z["arten"]}
    for k in ("A", "B"):
        if out[k]:
            out[k] = {key: (_r(v) if isinstance(v, float) else v) for key, v in out[k].items()}
    out["kurs"], out["atr"] = _r(px), _r(a)
    return out


def _r(x: float | None) -> float | None:
    if x is None:
        return None
    if x == 0:
        return 0.0
    digits = max(2, 4 - int(np.floor(np.log10(abs(x)))) - 1)
    return round(float(x), digits)


def _round_zone(z: dict) -> dict:
    return {"lo": _r(z["lo"]), "hi": _r(z["hi"]), "staerke": z["staerke"], "arten": z["arten"]}


def scenario_prices(sc: dict) -> set[float]:
    """Alle Preise, die das LLM nennen darf (fuer den Validator)."""
    out = {sc["kurs"], sc["atr"]}
    for k in ("A", "B"):
        if sc.get(k):
            out |= {v for key, v in sc[k].items() if isinstance(v, float) and key != "rr"}
    for z in sc.get("zonen", []):
        out |= {z["lo"], z["hi"]}
    return {v for v in out if v is not None}
