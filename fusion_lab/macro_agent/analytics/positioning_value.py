"""Fact Sheet v4 (24.11.2026): FX-Bewertung, Carry je Risiko und eine Trendfolger-Schaetzung.

- Carry/Vol: 2J-Zinsdifferenz Basis minus Quote (% p.a.) geteilt durch die 20-T-Vol des Paares.
  Carry allein taeuscht: 3 % Differenz bei 15 % Vol traegt weniger als 1,5 % bei 5 %.
- Trendfolger (CTA) als Schaetzung, kein Positionsdaten-Ersatz: Signal je Markt = Mittel der
  Vorzeichen des 1-, 3- und 12-Monats-Trends (-1..+1). Wendemarke je Horizont = Kurs vor h Tagen;
  faellt der Kurs darunter (bzw. steigt darueber), kippt dieser Teil des Signals. Abstand in % und
  in Tages-Vol zeigt, wo eine kleine Bewegung Trendfolger zum Umdrehen zwingt.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CCY_LAND = {"USD": "US", "EUR": "EA", "GBP": "GB", "JPY": "JP", "CHF": "CH", "AUD": "AU", "CAD": "CA", "NZD": "NZ"}
HORIZONS = {"1M": 21, "3M": 63, "12M": 252}
VOL_DAYS = 20


def _r(v, d: int = 2):
    return None if v is None or pd.isna(v) else round(float(v), d)


def carry_vol(prices: dict[str, pd.DataFrame], macro_w: pd.DataFrame) -> list[dict]:
    rows = []
    for m, df in prices.items():
        base, quote = m[:3], m[3:6]
        if base not in CCY_LAND or quote not in CCY_LAND:
            continue
        y_b, y_q = (macro_w.get(f"{CCY_LAND[c]}.2y") for c in (base, quote))
        if y_b is None or y_q is None or y_b.dropna().empty or y_q.dropna().empty:
            continue
        carry = float(y_b.dropna().iloc[-1] - y_q.dropna().iloc[-1])
        r = np.log(df["Close"].dropna()).diff().dropna().iloc[-VOL_DAYS:]
        if len(r) < VOL_DAYS // 2:
            continue
        vol = float(r.std() * np.sqrt(252) * 100)
        rows.append({"markt": m, "carry_pct": _r(carry), "vol_pct": _r(vol, 1),
                     "carry_je_vol": _r(carry / vol if vol else None)})
    return sorted(rows, key=lambda x: -(x["carry_je_vol"] or 0))


def trend_signal(close: pd.Series) -> dict | None:
    c = close.dropna()
    if len(c) <= max(HORIZONS.values()):
        return None
    last = float(c.iloc[-1])
    daily_vol = float(np.log(c).diff().iloc[-VOL_DAYS:].std() * 100)
    parts, flips = {}, {}
    for name, h in HORIZONS.items():
        ref = float(c.iloc[-1 - h])
        parts[name] = 1 if last > ref else -1
        flips[name] = (ref / last - 1) * 100
    signal = float(np.mean(list(parts.values())))
    # naechste Wende: der Horizont, dessen Wendemarke am naechsten liegt
    near = min(flips, key=lambda k: abs(flips[k]))
    dist = flips[near]
    return {"signal": _r(signal), "teile": parts, "naechste_wende": near,
            "abstand_pct": _r(dist), "abstand_tagesvol": _r(abs(dist) / daily_vol if daily_vol else None, 1),
            "datum": c.index[-1].date().isoformat()}


def trend_followers(prices: dict[str, pd.DataFrame], mkt_w: pd.DataFrame,
                    extra: dict[str, str] | None = None) -> dict[str, dict]:
    """prices: FX/Gold aus markets.load (lange Historie noetig); extra: Name -> Schluessel in mkt_w."""
    out = {}
    for m, df in prices.items():
        s = trend_signal(df["Close"])
        if s:
            out[m] = s
    for name, key in (extra or {}).items():
        if key in mkt_w:
            s = trend_signal(mkt_w[key])
            if s:
                out[name] = s
    return out


def crowded(tf: dict[str, dict], max_vol: float = 1.0) -> list[str]:
    """Maerkte mit vollem Trend (|Signal| = 1) und Wendemarke binnen max_vol Tagesschwankungen."""
    return [m for m, s in tf.items() if abs(s["signal"]) == 1 and (s["abstand_tagesvol"] or 99) <= max_vol]
