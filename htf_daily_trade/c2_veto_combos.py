"""C2 + Faber gegen × Carry- und Rohstoff-Veto aus dem Remy-King-Buch (Nutzerauftrag 11.11.2026).

    python -m htf_daily_trade.c2_veto_combos

Trades und Filterzustaende aus htf_daily_trade/filter_matrix_trades.csv (Stufe 1/1b, 9 Maerkte).
Veto = Trade faellt nur weg, wenn der Filter „gegen“ ist (neutral bleibt):
  V-Carry     Matrix M2: FX 2J-Differenz Basis minus USD; Metalle US-Realzins faellt (20 Beob.)
  V-Rohstoff  Buch B6: AUDUSD ~ Kupfer, USDCAD ~ Oel (umgekehrt), 20-Tage-Trend bis Vortag;
              uebrige Maerkte neutral (NZD ohne GDT-Historie)
Parametergrenze fuer diesen Test: 10 (Nutzer 11.11.; C2 = 7, Faber 1, Carry-Veto 1, Rohstoff 1, DXY/Kalman/COT je 1).
Varianten gezaehlt unter `htf_daily_filter_matrix`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_r import stats
from research_lock import Lock, deflated_sharpe

LOCK = "htf_daily_filter_matrix"
COMMODITY = {"AUDUSD": ("HG=F", 1), "USDCAD": ("CL=F", -1)}
WINDOW = 20
BASE = [("T6", "gegen")]
ADDONS = {"": [], "DXY mit": [("X2", "mit")], "Kalman mit": [("X5", "mit")], "COT-Fluss mit": [("M7", "mit")]}
VETOS = {"": [], "Carry-Veto": ["M2"], "Rohstoff-Veto": ["RS"], "Carry- + Rohstoff-Veto": ["M2", "RS"]}
PARAMS = {"T6": 1, "X2": 1, "X5": 1, "M7": 1, "M2": 1, "RS": 1}
MAX_PARAMS = 10


def commodity_state(t: pd.DataFrame, start: str = "2014-01-01", end: str = "2025-01-31") -> pd.Series:
    import yfinance as yf
    px = {}
    for m, (sym, _) in COMMODITY.items():
        d = yf.download(sym, start=start, end=end, progress=False, auto_adjust=True)
        s = d["Close"].squeeze().dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        px[m] = s
    out = []
    for r in t.itertuples():
        if r.markt not in COMMODITY:
            out.append("neutral")
            continue
        hist = px[r.markt][px[r.markt].index < r.datum]
        if len(hist) <= WINDOW:
            out.append("neutral")
            continue
        trend = np.sign(hist.iloc[-1] - hist.iloc[-1 - WINDOW]) * COMMODITY[r.markt][1]
        side = 1 if r.seite == "long" else -1
        out.append("mit" if trend == side else "gegen" if trend == -side else "neutral")
    return pd.Series(out, index=t.index)


def fmt(r: pd.Series) -> str:
    st = stats(r)
    if st.get("n", 0) < 2:
        return f"n {st.get('n', 0)}"
    return f"n {st['n']:>3} Ø {st['mean_r']:+.3f} t {st['t']:+.2f}"


def main() -> None:
    t = pd.read_csv("htf_daily_trade/filter_matrix_trades.csv", parse_dates=["datum"])
    t = t[t["setup"] == "C2"].copy()
    t["RS"] = commodity_state(t)
    combos = []
    for an, add in ADDONS.items():
        for vn, vet in VETOS.items():
            p = 7 + sum(PARAMS[f] for f, _ in BASE + add) + sum(PARAMS[v] for v in vet)
            if p <= MAX_PARAMS:
                combos.append((" + ".join(x for x in ("Faber gegen", an, vn) if x), add, vet, p))
    lock = Lock(LOCK)
    lock.log_trials(len(combos) - 1, "C2 + Faber gegen x Carry-/Rohstoff-Veto (Buch) x DXY/Kalman/COT, max. 10 Param. (11.11.)")
    print(f"Lock {LOCK}: {lock.trials} Versuche\n")
    rows = []
    for name, add, vet, p in combos:
        sel = t
        for f, z in BASE + add:
            sel = sel[sel[f] == z]
        for v in vet:
            sel = sel[sel[v] != "gegen"]
        is_r, oos_r = sel.loc[sel["periode"] == "IS", "r"], sel.loc[sel["periode"] == "OOS", "r"]
        sr = is_r.mean() / is_r.std(ddof=1)
        rows.append({"variante": name, "param": p, "IS": fmt(is_r), "OOS": fmt(oos_r),
                     "IS_t": stats(is_r)["t"], "DSR": deflated_sharpe(sr, len(is_r), lock.trials),
                     "Jahre+": f"{(sel.groupby(sel['datum'].dt.year)['r'].mean() > 0).sum()}/9",
                     "Maerkte+": f"{(sel.groupby('markt')['r'].mean() > 0).sum()}/9"})
    res = pd.DataFrame(rows).sort_values("IS_t", ascending=False)
    pd.set_option("display.width", 200)
    print(res.drop(columns="IS_t").round(2).to_string(index=False))
    rs = t[t["markt"].isin(COMMODITY)]
    print("\nRohstoff-Zustand bei AUD/CAD (C2):", rs.groupby(["periode", "RS"])["r"].agg(["size", "mean"]).round(3).to_string())


if __name__ == "__main__":
    main()
