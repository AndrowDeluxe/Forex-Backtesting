"""Kennzahlen-Score (0-100) je Titel + Gesamtscore + Signal (>= 65 KAUFEN, <= 35 VERKAUFEN).

Bausteine sind Querschnitts-Perzentile (0 = schlechtester, 100 = bester Titel im Universum), ausser Trend
(absolute Punkte). Fehlende Werte = 50 (neutral) und werden je Titel gezaehlt ("fehlend"). Gewichte in
config.WEIGHTS_* -- vorab festgelegt, nicht optimiert.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.screener import config as C


def pct(s: pd.Series, higher_better: bool = True) -> pd.Series:
    r = s.astype(float).rank(pct=True) * 100
    return r if higher_better else 100 - r + (100 / max(s.notna().sum(), 1))


def _fill(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    missing = df.isna().sum(axis=1)
    return df.fillna(50.0), missing


def trend_points(t: dict) -> float | None:
    """25 Punkte je: Kurs > SMA50, Kurs > SMA200, SMA50 > SMA200, SMA50 steigt (20 Tage)."""
    c, s50, s200, slope = t.get("close"), t.get("sma50"), t.get("sma200"), t.get("sma50_steigung")
    checks = []
    if s50 is not None:
        checks.append(c > s50)
    if s200 is not None:
        checks.append(c > s200)
        if s50 is not None:
            checks.append(s50 > s200)
    if slope is not None:
        checks.append(slope > 0)
    if not checks:
        return None
    return 100.0 * sum(checks) / len(checks)


def _mean(parts: list[pd.Series]) -> pd.Series:
    return pd.concat(parts, axis=1).mean(axis=1, skipna=True)


def stocks(tech: dict[str, dict], fund: dict[str, dict], sectors: dict[str, str], bench_ret63: float | None) -> pd.DataFrame:
    """tech: Ticker -> levels.technicals() (+ sma50_steigung); fund: Ticker -> Kennzahlen."""
    T = pd.DataFrame(tech).T
    F = pd.DataFrame(fund).T.reindex(T.index)
    num = lambda col: pd.to_numeric(F.get(col), errors="coerce") if col in F else pd.Series(np.nan, index=T.index)  # noqa: E731

    comp = pd.DataFrame(index=T.index)
    comp["trend"] = pd.Series({k: trend_points(v) for k, v in tech.items()})

    mom = pd.to_numeric(T["ret_126d"], errors="coerce") - pd.to_numeric(T["ret_21d"], errors="coerce")
    rs = pd.to_numeric(T["ret_63d"], errors="coerce") - (bench_ret63 if bench_ret63 is not None else 0.0)
    comp["momentum"] = _mean([pct(mom), pct(rs)])

    fcf_margin = num("freeCashflow") / num("totalRevenue").where(num("totalRevenue") > 0)
    comp["qualitaet"] = _mean([pct(num("grossMargins")), pct(num("operatingMargins")),
                               pct(num("returnOnEquity").clip(-1, 2)), pct(fcf_margin)])
    comp["wachstum"] = _mean([pct(num("revenueGrowth")), pct(num("earningsGrowth"))])

    fpe = num("forwardPE")
    sec = pd.Series(sectors).reindex(T.index).fillna("")
    fpe_pos = fpe.where(fpe > 0)
    fpe_sector = fpe_pos.groupby(sec).transform(lambda s: pct(s, higher_better=False))
    fpe_sector = fpe_sector.where(~(fpe <= 0), 0.0)          # Verlust/negativer Gewinn = 0 Punkte
    peg = num("trailingPegRatio").where(num("trailingPegRatio") > 0)
    ev = num("enterpriseToEbitda").where(num("enterpriseToEbitda") > 0)
    comp["bewertung"] = _mean([fpe_sector, pct(peg, higher_better=False), pct(ev, higher_better=False)])

    net_cash = (num("totalCash") - num("totalDebt")) / num("marketCap").where(num("marketCap") > 0)
    comp["bilanz"] = _mean([pct(num("debtToEquity"), higher_better=False), pct(num("currentRatio")), pct(net_cash)])

    upside = num("targetMeanPrice") / pd.to_numeric(T["close"], errors="coerce") - 1
    enough = num("numberOfAnalystOpinions") >= 3
    an = _mean([pct(upside.where(enough)), pct(num("recommendationMean").where(enough), higher_better=False)])
    comp["analysten"] = an

    filled, missing = _fill(comp)
    w = pd.Series(C.WEIGHTS_STOCKS)
    filled["kennzahlen_score"] = (filled[w.index] * w).sum(axis=1) / w.sum()
    filled["fehlend"] = missing
    return filled.round(1)


def crypto(tech: dict[str, dict], cg: pd.DataFrame, fund_rates: dict[str, float], bench: str) -> pd.DataFrame:
    """tech: Symbol -> technicals; cg: CoinGecko-Zeilen (index = Symbol); fund_rates: PAIR -> Funding."""
    T = pd.DataFrame(tech).T
    G = cg.reindex(T.index)
    comp = pd.DataFrame(index=T.index)
    comp["trend"] = pd.Series({k: trend_points(v) for k, v in tech.items()})
    r30 = pd.to_numeric(T["ret_21d"], errors="coerce")       # ~30 Kalendertage = 30 Kerzen bei Krypto
    r90 = pd.to_numeric(T["ret_63d"], errors="coerce")
    if bench in T.index:
        r30, r90 = r30 - r30[bench], r90 - r90[bench]
    comp["rel_staerke"] = _mean([pct(r30), pct(r90)])
    comp["liquiditaet"] = pct(pd.to_numeric(G["total_volume"], errors="coerce")
                              / pd.to_numeric(G["market_cap"], errors="coerce"))
    supply_max = pd.to_numeric(G["max_supply"], errors="coerce").fillna(pd.to_numeric(G["total_supply"], errors="coerce"))
    comp["verwaesserung"] = pct(pd.to_numeric(G["circulating_supply"], errors="coerce") / supply_max)
    fr = pd.Series({s: fund_rates.get(f"{s}USDT") for s in T.index}, dtype=float)
    comp["funding"] = pct(fr, higher_better=False)
    comp["abstand_hoch"] = pct(pd.to_numeric(G["ath_change_percentage"], errors="coerce"))
    filled, missing = _fill(comp)
    w = pd.Series(C.WEIGHTS_CRYPTO)
    filled["kennzahlen_score"] = (filled[w.index] * w).sum(axis=1) / w.sum()
    filled["fehlend"] = missing
    return filled.round(1)


def sentiment_points(sentiment: int | None) -> float | None:
    """-2..+2 -> 0..100."""
    return None if sentiment is None else 50.0 + 25.0 * max(-2, min(2, int(sentiment)))


def total(kennzahlen: float, sentiment: int | None) -> float:
    sp = sentiment_points(sentiment)
    if sp is None:
        return round(float(kennzahlen), 1)
    return round((1 - C.SENTIMENT_WEIGHT) * float(kennzahlen) + C.SENTIMENT_WEIGHT * sp, 1)


def signal(score: float) -> str:
    if score >= C.BUY_THRESHOLD:
        return "KAUFEN"
    if score <= C.SELL_THRESHOLD:
        return "VERKAUFEN"
    return "HALTEN"
