"""Daily-Kandidat 2016 bis heute mit allen Kennzahlen (Nutzerauftrag 11.11.2026, oeffnet den Tresor einmal).

    python -m htf_daily_trade.c2_bis_heute        # schreibt c2_bis_heute_report.md + c2_bis_heute_trades.csv

Zwei Varianten, Regeln unveraendert:
  EL   eingefroren 6c55e525 (Lock htf_daily_filter_matrix): C2 + Faber gegen + COT-Fluss mit + Rohstoff-Veto,
       Limit 50 % Ausloese-Schluss/Strukturstop 3 Tage, Strukturstop, 10 Handelstage (c2_blind.trades).
  W50  beste Leiter-Variante (Lock htf_daily_twin, hier eingefroren): gleiche Ideen (ltf_entry.daily_ideas),
       Limit 50 % der Vorwochen-Range bis Ideen-Ende, Stop Struktur + 0,5 ATR, 10 Handelstage ab Fuellung.
Kosten Spread + Kommission + TTP-Swap. Konto 100.000 $, 1 % Risiko je Trade, Zinseszins, Buchung bei Ausstieg.
Tageskerzen UTC wie im Backtest; nach dem Ende der Backtest-Dateien aus H1-Dateien bzw. Data Lake gebuendelt
(forward_data.daily_from_intraday). Offene Trades: R zum letzten Schlusskurs.
"""

from __future__ import annotations

import functools

import numpy as np
import pandas as pd

from htf_daily_trade import c2_blind as cb
from htf_daily_trade import ltf_entry as le
from htf_daily_trade.backtest_r import features
from htf_daily_trade.c2_kandidat_report import md, r_block
from htf_daily_trade.c2_ladder import point_legs
from htf_daily_trade.c2_veto_combos import commodity_state
from htf_daily_trade.filter_matrix import MARKETS, WARMUP, load_market
from htf_daily_trade.forward_data import daily_from_intraday
from research_lock import Lock

START = "2016-01-01"
START_KAPITAL = 100_000.0
H1_FILES = {"XAUUSD": "GOLD_H1_2018-01-01_2026-11-10.parquet", "XAGUSD": "SILVER_H1_2016-01-01_2026-08-01.parquet"}
LAKE = {"EURUSD": ("EURUSD", "M5"), "GBPUSD": ("GBPUSD", "M15"), "AUDUSD": ("AUDUSD", "M15"),
        "USDJPY": ("USDJPY", "M15"), "USDCAD": ("USDCAD", "M15"), "USDCHF": ("USDCHF", "M15"),
        "XAUUSD": ("GOLD", "H1"), "XAGUSD": ("SILVER", "H1")}
W50_CONFIG = {
    "basis": "Ideen des eingefrorenen Kandidaten 6c55e525 (ltf_entry.daily_ideas: C2-Signal, Faber 10M gegen, "
             "COT-Fluss 4 Berichte mit, Rohstoff-Veto 20 Tage, 10 Tage Sperre je Seite)",
    "einstieg": "Limit 50 % der Vorwochen-Range (W50), gueltig bis Ideen-Ende (10 Handelstage)",
    "stop": "Strukturstop + 0,5 x Daily-ATR", "ausstieg": "10 Handelstage nach Fuellung", "be": None,
    "risiko": "1 % je Trade", "kosten": "Spread+Kommission (filter_matrix.MARKETS) + TTP-Swap",
    "maerkte": sorted(MARKETS), "parameter": 12, "variante": "W50 V10 SA",
    "code": ["htf_daily_trade/c2_ladder.py", "htf_daily_trade/ltf_entry.py", "htf_daily_trade/c2_bis_heute.py"],
}


# --------------------------------------------------------------------------- Daten bis heute
@functools.lru_cache(maxsize=None)
def load_to_today(name: str, today: str | None = None) -> pd.DataFrame:
    hist = load_market(name)
    day = pd.Timestamp(today) if today else None
    parts = []
    f = H1_FILES.get(name, f"{name}_H1_2007-01-01_2026-11-10.parquet")
    try:
        b = pd.read_parquet(f"data_cache/combined/{f}")[["Open", "High", "Low", "Close"]].sort_index()
        parts.append(daily_from_intraday(b, day))
    except FileNotFoundError:
        pass
    if name in LAKE:
        from data_lake.storage import read_bars
        lk = read_bars("dukascopy", *LAKE[name])
        if lk is not None and len(lk):
            parts.append(daily_from_intraday(lk[["Open", "High", "Low", "Close"]].sort_index(), day))
    d = hist
    for p in parts:                        # Vorrang: Backtest-Datei > H1-Datei > Data Lake
        d = d.combine_first(p[p.index > hist.index.max()])
    return d.sort_index()


def last_day() -> pd.Timestamp:
    return max(load_to_today(m).index.max() for m in MARKETS)   # NZDUSD ohne Lake endet frueher


# --------------------------------------------------------------------------- Trades
def el_trades(start: str, end: pd.Timestamp) -> pd.DataFrame:
    cb.load_market = load_to_today
    t = cb.trades(start, end.strftime("%Y-%m-%d"))
    t["variante"] = "EL"
    hold = t.apply(lambda r: len(load_to_today(r.markt).loc[r.einstieg:r.ausstieg]) - 1, axis=1)
    t["offen"] = (t["ausstieg"] >= end) & (hold < 10) & (t["r_netto_ohne_swap"] > -0.99)
    return t


def w50_trades(end: pd.Timestamp) -> pd.DataFrame:
    le.load_market = load_to_today
    le.RUN_END = end + pd.Timedelta(hours=23, minutes=59)
    le.commodity_state = functools.partial(commodity_state, start="2013-06-01",
                                           end=(end + pd.Timedelta(days=5)).strftime("%Y-%m-%d"))
    ideas = le.daily_ideas()
    rows = []
    for name, (_, grid, cost) in MARKETS.items():
        im = ideas[ideas["markt"] == name]
        if im.empty:
            continue
        x = features(load_to_today(name).loc[pd.Timestamp(WARMUP):end], grid)
        end_idx = len(x) - 1
        for _, idea in im.iterrows():
            t = int(x.index.searchsorted(idea.signal))
            if t + 1 > end_idx:
                continue
            leg = point_legs(x, idea, t, cost, end_idx)[("W50", "V10", "SA")]
            if leg is None:
                continue
            r, d0, d1 = leg
            k0 = x.index.get_loc(d0)
            sign = 1 if idea.seite == "long" else -1
            stop = idea.daily_stop - sign * 0.5 * idea.atr
            k1 = x.index.get_loc(d1)
            stopped = (x["Low"].iat[k1] <= stop) if sign == 1 else (x["High"].iat[k1] >= stop)
            rows.append({"variante": "W50", "markt": name, "seite": idea.seite, "signal": idea.signal,
                         "einstieg": d0, "ausstieg": d1, "stop": stop, "r_TTP": r,
                         "offen": (not stopped) and k1 == end_idx and k1 - k0 < 10})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- Kennzahlen
def equity(t: pd.DataFrame, risk: float = 0.01) -> pd.Series:
    """Kontostand je Ausstiegstag (Groesse ab Kontostand beim Einstieg), wie c2_exit_varianten.konto."""
    t = t.sort_values("einstieg")
    eq, offen, book = START_KAPITAL, [], []
    for x in t.itertuples():
        for o in sorted(o for o in offen if o[0] < x.einstieg):
            eq += o[1]
            book.append((o[0], eq))
            offen.remove(o)
        offen.append((x.ausstieg, eq * risk * x.r_TTP))
    for o in sorted(offen):
        eq += o[1]
        book.append((o[0], eq))
    s = pd.Series([v for _, v in book], index=pd.DatetimeIndex([d for d, _ in book]))
    s = s.groupby(level=0).last()
    return pd.concat([pd.Series([START_KAPITAL], index=[t["einstieg"].min() - pd.Timedelta(days=1)]), s])


def kennzahlen(t: pd.DataFrame, end: pd.Timestamp) -> dict:
    r = t["r_TTP"]
    k = r_block(r)
    eq = equity(t)
    jahre = (end - pd.Timestamp(START)).days / 365.25
    m = eq.resample("ME").last().reindex(pd.date_range(START, end, freq="ME")).ffill().fillna(START_KAPITAL)
    mr = m.pct_change().dropna()
    dd = eq / eq.cummax() - 1
    under = (eq < eq.cummax())
    dauer, cur, start_dd = 0, None, None
    for d, u in under.items():
        if u and start_dd is None:
            start_dd = d
        if not u and start_dd is not None:
            dauer = max(dauer, (d - start_dd).days)
            start_dd = None
    if start_dd is not None:
        dauer = max(dauer, (end - start_dd).days)
    cagr = (eq.iat[-1] / START_KAPITAL) ** (1 / jahre) - 1
    down = mr[mr < 0]
    return {**k, "Trades/Jahr": len(t) / jahre, "Ø Haltedauer (Kalendertage)": (t["ausstieg"] - t["einstieg"]).dt.days.mean(),
            "Endkapital 1 %": eq.iat[-1], "CAGR 1 %": cagr, "max. DD Konto": dd.min(),
            "längste Unterwasserphase (Tage)": dauer,
            "Sharpe (Monate, ann.)": mr.mean() / mr.std(ddof=1) * np.sqrt(12),
            "Sortino (Monate, ann.)": mr.mean() / np.sqrt((down ** 2).sum() / len(mr)) * np.sqrt(12),
            "Calmar": cagr / abs(dd.min()), "Monate positiv": (mr > 0).sum() / max(1, (mr != 0).sum()),
            "bester Monat": mr.max(), "schlechtester Monat": mr.min()}


def jahrestabelle(t: pd.DataFrame) -> pd.DataFrame:
    eq = equity(t)
    out = []
    for y, g in t.groupby(t["einstieg"].dt.year):
        e0 = eq[eq.index < pd.Timestamp(f"{y}-01-01")]
        e1 = eq[eq.index <= pd.Timestamp(f"{y}-12-31")]
        ret = e1.iat[-1] / (e0.iat[-1] if len(e0) else START_KAPITAL) - 1
        out.append({"Jahr": y, "n": len(g), "Ø R": g["r_TTP"].mean(), "Σ R": g["r_TTP"].sum(),
                    "Treffer": (g["r_TTP"] > 0).mean(), "Konto 1 %": ret})
    return pd.DataFrame(out).set_index("Jahr")


def main() -> None:
    end = last_day()
    print(f"Daten bis {end.date()}", flush=True)
    lk = Lock("htf_daily_filter_matrix")
    if "tresor" not in lk._load()["unsealed"]:
        print("Tresor htf_daily_filter_matrix:", lk.unseal("tresor", cb.FROZEN))
    lt = Lock("htf_daily_twin")
    h = lt.freeze(W50_CONFIG)
    if "tresor" not in lt._load()["unsealed"]:
        print("Tresor htf_daily_twin:", lt.unseal("tresor", h), "Hash", h[:8])
    el = el_trades(START, end)
    w50 = w50_trades(end)
    cols = ["variante", "markt", "seite", "einstieg", "ausstieg", "r_TTP", "offen"]
    alle = pd.concat([el[cols], w50[cols]]).sort_values("einstieg")
    alle.to_csv("htf_daily_trade/c2_bis_heute_trades.csv", index=False)
    lines = [f"# Daily-Kandidat {START} bis {end.date()} (Stand 11.11.2026)", "",
             "Kosten Spread + Kommission + TTP-Swap. Konto 100.000 $, 1 % Risiko je Trade, Zinseszins.",
             "IS 2016–21, OOS 2022–24, Tresor ab 2025 (am 11.11. einmal geöffnet). Offene Trades zum letzten Schluss.", ""]
    kz = {}
    for name, t in (("EL eingefroren (6c55e525)", el), ("W50 Vorwochen-Mitte", w50)):
        kz[name] = kennzahlen(t, end)
    kt = pd.DataFrame(kz)
    lines += ["## Kennzahlen", "", md(kt.map(lambda v: round(v, 3) if isinstance(v, float) else v)), ""]
    pd.set_option("display.width", 220)
    print(kt.round(3).to_string())
    for name, t in (("EL", el), ("W50", w50)):
        jt = jahrestabelle(t)
        print(f"\n{name} je Jahr\n{jt.round(3).to_string()}")
        lines += [f"## {name} je Jahr", "", md(jt.round(3)), ""]
        per = t.assign(p=np.select([t["einstieg"] <= "2021-12-31", t["einstieg"] <= "2024-12-31"], ["IS", "OOS"], "Tresor"))
        pt = pd.DataFrame({p: r_block(g["r_TTP"]) for p, g in per.groupby("p")}).T[["n", "Ø R", "t", "Treffer", "PF", "Σ R"]]
        print(pt.round(3).to_string())
        lines += [f"## {name} je Periode", "", md(pt.astype(float).round(3)), ""]
        mt = t.groupby("markt")["r_TTP"].agg(["size", "mean", "sum"]).rename(columns={"size": "n", "mean": "Ø R", "sum": "Σ R"})
        lines += [f"## {name} je Markt", "", md(mt.round(3)), ""]
        y = t[t["einstieg"] >= "2026-01-01"][["markt", "seite", "einstieg", "ausstieg", "r_TTP", "offen"]]
        y = y.assign(einstieg=y["einstieg"].dt.date, ausstieg=y["ausstieg"].dt.date)
        print(f"\n{name} 2026:\n{y.round(3).to_string(index=False)}")
        lines += [f"## {name} Trades 2026", "", md(y.round(3), index=False), ""]
    open("htf_daily_trade/c2_bis_heute_report.md", "w", encoding="utf-8").write("\n".join(lines))


if __name__ == "__main__":
    main()
