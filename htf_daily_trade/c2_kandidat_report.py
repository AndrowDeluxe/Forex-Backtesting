"""Ausfuehrlicher Backtest des C2-Kandidaten inkl. Swap, Kosten-Stress und Konto mit 1/2/5/10 % Risiko.

    python -m htf_daily_trade.c2_kandidat_report        # schreibt c2_kandidat_trades.csv + c2_kandidat_report.md

Nutzerauftrag 11.11.2026. Kandidat: C2 EL + Faber gegen + COT-Fluss mit + Rohstoff-Veto, Stop S1 (Struktur),
Ausstieg nach 10 Handelstagen, kein BE, 9 Maerkte, IS 2016-2021 + OOS 2022-2024. Keine Auswahl, nur Darstellung.

Kosten
  Spread + Kommission  wie bisher (Round-Trip in Preis je Markt, filter_matrix.MARKETS)
  Swap                 NEU, Modell aus Leitzinsen (fusion_lab.macro_data, *.policy_rate):
                       Kosten p.a. long = Zins Gegenwaehrung − Zins Basis + Aufschlag, short = umgekehrt + Aufschlag;
                       Metalle: Basiszins 0. Aufschlag aus echten MT5-Swaps vom 05.10.2026
                       (scripts/frozen_data/faber_symbol_specs_20261005.json): TTP FX 2,0 % / Metalle 4,0 %,
                       Tickmill FX 0,4 % / Metalle 0,7 %. Haltedauer in Kalendertagen (Wochenende = Dreifach-Swap).
  Stress               Spread+Kommission x2 und TTP-Swap
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.macro_data import store
from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.backtest_varianten import entries
from htf_daily_trade.c2_exit_varianten import EXITS, candidate, konto, sim
from htf_daily_trade.filter_matrix import MARKETS, OOS_END, WARMUP, load_market

CCY = {"EURUSD": ("EA", "US"), "GBPUSD": ("GB", "US"), "AUDUSD": ("AU", "US"), "NZDUSD": ("NZ", "US"),
       "USDJPY": ("US", "JP"), "USDCAD": ("US", "CA"), "USDCHF": ("US", "CH"), "XAUUSD": (None, "US"),
       "XAGUSD": (None, "US")}
AUFSCHLAG = {"TTP": (0.020, 0.040), "Tickmill": (0.004, 0.007)}   # (FX, Metalle) p.a.
RISIKEN = (0.01, 0.02, 0.05, 0.10)
CONFIG = {"setup": "C2 EL (Limit 50 % Ausloese-Schluss/Strukturstop, 3 Tage), Sweep 7 Tage, 3 Vorkerzen, MA 12/20",
          "filter": {"T6": "Faber 10 Monate GEGEN die Trade-Richtung",
                     "M7": "COT-Fluss Non-Commercials 4 Berichte MIT",
                     "RS": "Rohstoff-Veto 20 Tage (AUDUSD~Kupfer, USDCAD~Oel)"},
          "stop": "S1 Struktur", "ausstieg": "10 Handelstage", "be": None, "teilgewinne": None,
          "risiko": "fest je Trade", "maerkte": sorted(MARKETS), "parameter": 10}


def rates() -> pd.DataFrame:
    m = store.latest("macro")
    w = m[m["key"].str.endswith(".policy_rate")].pivot_table(index="date", columns="key", values="value")
    w.columns = [c.split(".")[0] for c in w.columns]
    return (w.sort_index().ffill().fillna(0.0) / 100.0)


def base_trades() -> pd.DataFrame:
    cand = candidate()
    keys = {(r.markt, r.datum.normalize(), r.seite): r for r in cand.itertuples()}
    rows, e = [], pd.Timestamp(OOS_END)
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp(WARMUP):e], grid)
        end_idx = int(np.searchsorted(x.index, e, side="right")) - 1
        used = set()
        for en in sorted((z for z in entries(x, "C") if z["v"] == "C2 EL"), key=lambda z: z["fill"]):
            key = (name, x.index[en["fill"]].normalize(), en["side"])
            r = keys.get(key)
            if r is None or key in used:
                continue
            used.add(key)
            res = sim(x, en, "S1", EXITS["A0"], None, cost, end_idx)
            if res is None:
                continue
            sign = 1 if en["side"] == "long" else -1
            risk = sign * (en["price"] - en["struct"])
            rows.append({"markt": name, "seite": en["side"], "einstieg": x.index[en["fill"]],
                         "ausstieg": x.index[res["exit_k"]], "kurs": en["price"], "stop": en["struct"],
                         "risiko_preis": risk, "kosten_preis": cost, "periode": r.periode,
                         "r_netto_ohne_swap": res["r"], "r_brutto": res["r"] + cost / risk})
    return pd.DataFrame(rows).sort_values("einstieg").reset_index(drop=True)


def add_swap(t: pd.DataFrame) -> pd.DataFrame:
    rt = rates()
    t = t.copy()
    t["tage"] = (t["ausstieg"] - t["einstieg"]).dt.days.clip(lower=1)
    for broker, (m_fx, m_met) in AUFSCHLAG.items():
        out = []
        for x in t.itertuples():
            base, quote = CCY[x.markt]
            row = rt.loc[:x.einstieg].iloc[-1]
            diff = row[quote] - (row[base] if base else 0.0)            # Kosten p.a. fuer long
            mk = m_met if base is None else m_fx
            pa = (diff if x.seite == "long" else -diff) + mk
            out.append(pa / 365 * x.tage * x.kurs / x.risiko_preis)
        t[f"swap_r_{broker}"] = out
        t[f"r_{broker}"] = t["r_netto_ohne_swap"] - t[f"swap_r_{broker}"]
    t["r_stress"] = t["r_netto_ohne_swap"] - t["kosten_preis"] / t["risiko_preis"] - t["swap_r_TTP"]
    return t


def md(df: pd.DataFrame, index: bool = True) -> str:
    """Markdown-Tabelle ohne Zusatzpaket."""
    d = df.reset_index() if index else df
    f = lambda v: f"{v:,.3f}" if isinstance(v, float) else str(v)
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    sep = "|" + "---|" * len(d.columns)
    return "\n".join([head, sep] + ["| " + " | ".join(f(v) for v in row) + " |" for row in d.itertuples(index=False)])


def r_block(r: pd.Series) -> dict:
    st = stats(r)
    w, l = r[r > 0], r[r <= 0]
    streak = max((len(list(g)) for k, g in __import__("itertools").groupby(r > 0) if not k), default=0)
    eq = r.cumsum()
    return {"n": st["n"], "Ø R": st["mean_r"], "t": st["t"], "Treffer": st["treffer"], "PF": st["pf"],
            "Σ R": r.sum(), "Ø Gewinn": w.mean(), "Ø Verlust": l.mean(), "bester": r.max(), "schlechtester": r.min(),
            "max. Verlustserie": streak, "max. DD (R)": (eq - eq.cummax()).min()}


def main() -> None:
    t = add_swap(base_trades())
    t.to_csv("htf_daily_trade/c2_kandidat_trades.csv", index=False)
    pd.set_option("display.width", 220)
    lines = ["# C2-Kandidat: ausführlicher Backtest (11.11.2026)", "",
             "Regeln: " + str(CONFIG), "", "## Kosten-Szenarien (R je Trade nach Kosten)", ""]
    sc = {"ohne Swap (bisher)": "r_netto_ohne_swap", "Swap Tickmill": "r_Tickmill", "Swap TTP": "r_TTP",
          "Stress (Spread×2 + TTP-Swap)": "r_stress", "brutto (ohne alle Kosten)": "r_brutto"}
    rows = []
    for name, col in sc.items():
        for per in ("IS", "OOS", "gesamt"):
            r = t[col] if per == "gesamt" else t.loc[t["periode"] == per, col]
            rows.append({"Szenario": name, "Periode": per, **r_block(r)})
    tab = pd.DataFrame(rows)
    lines += [md(tab, index=False), ""]
    print(tab.round(3).to_string(index=False))
    main_col = "r_TTP"
    lines += ["## Kostenanteile (Ø je Trade, in R)", "",
              f"Spread+Kommission {(t['kosten_preis'] / t['risiko_preis']).mean():.3f} R | Swap Tickmill "
              f"{t['swap_r_Tickmill'].mean():.3f} R | Swap TTP {t['swap_r_TTP'].mean():.3f} R | "
              f"Ø Haltedauer {t['tage'].mean():.1f} Kalendertage", ""]
    for title, key in (("Je Jahr", t["einstieg"].dt.year), ("Je Markt", t["markt"]), ("Je Richtung", t["seite"])):
        g = t.groupby(key)[main_col].agg(["size", "mean", "sum"]).rename(columns={"size": "n", "mean": "Ø R", "sum": "Σ R"})
        lines += [f"## {title} (Swap TTP)", "", md(g), ""]
        print(f"\n{title}\n{g.round(3).to_string()}")
    lines += ["## Konto 100.000 $ ab 2016, Zinseszins, Swap TTP", ""]
    kr = []
    kt = t.rename(columns={"einstieg": "datum", "ausstieg": "exit_datum", main_col: "r"})[["datum", "exit_datum", "r"]]
    for rk in RISIKEN:
        k = konto(kt, lambda x, rk=rk: rk)
        kr.append({"Risiko je Trade": f"{rk:.0%}", "Endkapital": round(k["ende"]), "CAGR": k["cagr"], "max. DD": k["max_dd"]})
    kd = pd.DataFrame(kr)
    open_max = max(((t["einstieg"] <= d) & (t["ausstieg"] > d)).sum() for d in t["einstieg"])
    lines += [md(kd, index=False), "",
              f"Max. gleichzeitig offene Trades: {open_max} → offenes Risiko bis {open_max}× Risiko je Trade.", ""]
    print(f"\n{kd.to_string(index=False)}\nmax. gleichzeitig offen: {open_max}")
    open("htf_daily_trade/c2_kandidat_report.md", "w", encoding="utf-8").write("\n".join(lines))


if __name__ == "__main__":
    main()
