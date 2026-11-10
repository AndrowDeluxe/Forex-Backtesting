"""C2 + Zins-Momentum + Regime-Matrix (eingefroren aea4189b) auf einem 100k-Konto ab 2015.

    python -m htf_daily_trade.c2_konto

Nutzerauftrag 10.11.2026. Keine Auswahl, nur Darstellung der eingefrorenen Regeln: alle Trades
2015 bis heute (2015 = Blind, 2016-21 IS, 2022-24 OOS, ab 2025 bisher ungesehen).
Zwei Rechnungen mit 1 % Risiko je Trade:
  fest       1 % vom Startkapital (1.000 USD je R)
  zinseszins 1 % vom Kontostand bei Einstieg; zaehlt nur Trades, die vorher geschlossen wurden
R ist nach Kosten (htf_daily_trade.backtest_varianten.simulate).
"""

from __future__ import annotations

import pandas as pd

from htf_daily_trade.backtest_r import stats
from htf_daily_trade.c2_filter_overlap import keep, label_trades
from htf_daily_trade.c2_goldfilter import evaluate

START_KAPITAL = 100_000.0
RISIKO = 0.01


def konto(t: pd.DataFrame) -> pd.DataFrame:
    t = t.sort_values("datum").reset_index(drop=True)
    eq, offen, pnl = START_KAPITAL, [], []
    for _, x in t.iterrows():
        d = pd.Timestamp(x["datum"])
        for o in [o for o in offen if o[0] < d]:  # vor dem Einstieg geschlossene Trades verbuchen
            eq += o[1]
            offen.remove(o)
        risk = eq * RISIKO
        pnl.append(risk * x["r"])
        offen.append((pd.Timestamp(x["exit_datum"]), risk * x["r"]))
    t["pnl_fest"] = t["r"] * START_KAPITAL * RISIKO
    t["pnl_zins"] = pnl
    return t


def kurve(t: pd.DataFrame, col: str) -> pd.Series:
    s = t.groupby(pd.to_datetime(t["exit_datum"]))[col].sum().sort_index().cumsum() + START_KAPITAL
    return s


def max_dd(eq: pd.Series) -> float:
    eq = pd.concat([pd.Series([START_KAPITAL]), eq.reset_index(drop=True)])
    return float((eq / eq.cummax() - 1).min())


def offenes_risiko(t: pd.DataFrame) -> int:
    ev = [(pd.Timestamp(d), 1) for d in t["datum"]] + [(pd.Timestamp(d), -1) for d in t["exit_datum"]]
    n = mx = 0
    for _, v in sorted(ev, key=lambda e: (e[0], e[1])):
        n += v
        mx = max(mx, n)
    return mx


def main() -> None:
    alle = label_trades(evaluate("2015-01-01", pd.Timestamp.today().strftime("%Y-%m-%d"), "2014-01-01"))
    t = konto(alle.loc[keep(alle, ("F1", "F3"))].copy())
    t.to_csv("htf_daily_trade/c2_konto_trades.csv", index=False)
    jahre = (pd.Timestamp(t["exit_datum"].max()) - pd.Timestamp("2015-01-01")).days / 365.25
    print(f"Trades: {stats(t['r'])}")
    print(f"Basis C2 ohne Filter im selben Zeitraum: {stats(alle['r'])}")
    for col, name in (("pnl_fest", "fest 1 % vom Start"), ("pnl_zins", "1 % vom Kontostand")):
        eq = kurve(t, col)
        end = eq.iloc[-1]
        cagr = (end / START_KAPITAL) ** (1 / jahre) - 1
        print(f"\n== {name}: Ende {end:,.0f} USD, Gewinn {end - START_KAPITAL:+,.0f}, "
              f"CAGR {cagr:.1%}, max. Drawdown {max_dd(eq):.1%}")
    t["jahr"] = pd.to_datetime(t["exit_datum"]).dt.year
    j = t.groupby("jahr").agg(trades=("r", "size"), summe_r=("r", "sum"), pnl_fest=("pnl_fest", "sum"),
                               pnl_zins=("pnl_zins", "sum"))
    print("\n" + j.round(1).to_string())
    print(f"\nHoechstens gleichzeitig offen: {offenes_risiko(t)} Trades "
          f"(= bis {offenes_risiko(t)} % Risiko gleichzeitig)")
    print(f"Laengste Verlustserie: {(t['r'] <= 0).astype(int).groupby((t['r'] > 0).cumsum()).sum().max()} Trades")


if __name__ == "__main__":
    main()
