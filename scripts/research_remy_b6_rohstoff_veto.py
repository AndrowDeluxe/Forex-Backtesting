"""Remy-King B6: Rohstoff-Veto fuer Rohstoffwaehrungen auf den Daily-Edge-Trades.

    python -m scripts.research_remy_b6_rohstoff_veto

Trades: htf_daily_trade/filter_matrix_trades.csv (Setups R und C2, IS 2016-2021, OOS 2022-2024,
gleiche Perioden wie die Filter-Matrix). Rohstoff-Trend = Schluss heute vs. vor N Handelstagen,
Stand Vortag des Einstiegs. AUDUSD ~ Kupfer (HG=F), USDCAD ~ Oel (CL=F, umgekehrt gepolt, da
steigendes Oel CAD stuetzt = USDCAD faellt). NZD fehlt (keine freie GDT-Milchpreis-Historie).
Zustand je Trade: "mit" (Rohstoff stuetzt die Trade-Richtung), "gegen" (Veto-Fall).

Sperre `remy_b6_rohstoff_veto`, Regel seit 10.11.: OOS frei, Varianten gezaehlt.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from research_lock import Lock

LOCK = Lock("remy_b6_rohstoff_veto")
COMMODITY = {"AUDUSD": ("HG=F", 1), "USDCAD": ("CL=F", -1)}   # Vorzeichen: Rohstoff steigt -> Paar steigt
WINDOWS = (20, 60)


def closes(symbol: str) -> pd.Series:
    d = yf.download(symbol, start="2014-01-01", end="2025-01-31", progress=False, auto_adjust=True)
    s = d["Close"].squeeze().dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s


def stats(r: pd.Series) -> dict:
    n = len(r)
    if n < 2:
        return {"n": n, "mean_r": r.mean() if n else np.nan, "t": np.nan}
    return {"n": n, "mean_r": r.mean(), "t": r.mean() / r.std(ddof=1) * np.sqrt(n)}


def main() -> None:
    LOCK.register_split("2016-01-01", "2021-12-31", "2024-12-31", "2025-06-30")
    t = pd.read_csv("htf_daily_trade/filter_matrix_trades.csv", parse_dates=["datum"])
    t = t[t["markt"].isin(COMMODITY)].copy()
    px = {m: closes(sym) for m, (sym, _) in COMMODITY.items()}
    LOCK.log_trials(len(WINDOWS), "B6 Rohstoff-Trend 20/60 Tage, mit/gegen")
    rows = []
    for n in WINDOWS:
        state = []
        for r in t.itertuples():
            s = px[r.markt]
            hist = s[s.index < r.datum]                      # nur bis Vortag
            if len(hist) <= n:
                state.append("neutral")
                continue
            trend = np.sign(hist.iloc[-1] - hist.iloc[-1 - n]) * COMMODITY[r.markt][1]
            side = 1 if r.seite == "long" else -1
            state.append("mit" if trend == side else "gegen" if trend == -side else "neutral")
        t[f"N{n}"] = state
        for setup in ("C2", "R", "beide"):
            sub = t if setup == "beide" else t[t["setup"] == setup]
            for z in ("alle", "mit", "gegen"):
                g = sub if z == "alle" else sub[sub[f"N{n}"] == z]
                a, b = stats(g[g["periode"] == "IS"]["r"]), stats(g[g["periode"] == "OOS"]["r"])
                rows.append({"Fenster": n, "Setup": setup, "Zustand": z, "IS n": a["n"], "IS Ø R": a["mean_r"],
                             "IS t": a["t"], "OOS n": b["n"], "OOS Ø R": b["mean_r"], "OOS t": b["t"]})
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
    print("\nJe Markt, Fenster 20 (IS+OOS):")
    print(t.groupby(["markt", "N20"])["r"].agg(["size", "mean"]).round(3).to_string())


if __name__ == "__main__":
    main()
