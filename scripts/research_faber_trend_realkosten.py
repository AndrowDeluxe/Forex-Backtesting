"""Nachrechnung der geloggten Faber-Trend-Finalisten mit ECHTEN MT5-Werten
(scripts/frozen_data/faber_symbol_specs_*.json, gelesen 2026-10-05):
Swap je Instrument/Richtung, Spread, Kontraktgroesse, Mindestlot, Lot-Schritt,
Kontogroesse. Finalisten und Regeln unveraendert aus
Claude outputs/faber_trend_funded_is.json (keine neue Auswahl).

Zwei Swap-Modelle:
  heute     -- heutige Saetze ueber den ganzen Zeitraum (Stress)
  zinsangep -- fuer in USD finanzierte Instrumente (Indizes, Metalle, Oel,
               Kupfer): Kosten_long(t) = Kosten_long_heute - (IRX_heute - IRX_t),
               Kosten_short(t) = Kosten_short_heute + (IRX_heute - IRX_t).
               FX und BTC unveraendert (Zinsdifferenz bzw. fester Broker-Satz).
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import research_faber_trend_funded as R  # noqa: E402
from faber_trend import data as D, engine as E  # noqa: E402

ROOT = R.ROOT
OUT = os.path.join(ROOT, "Claude outputs", "faber_trend_realkosten.json")
SHIFT_INSTS = ("SP500", "NASDAQ", "US30", "DAX", "GOLD", "SILVER", "OIL", "COPPER")
FALLBACK_PRICE = {"DAX": "DAX", "OIL": "OIL", "COPPER": "COPPER"}


def irx_series():
    path = sorted(glob.glob(os.path.join(D.FROZEN_DIR, "irx_daily_*.csv")))
    if not path:
        import yfinance as yf
        d = yf.download("^IRX", start="1995-01-01", auto_adjust=False, progress=False)
        d.columns = d.columns.get_level_values(0)
        f = os.path.join(D.FROZEN_DIR, "irx_daily_20261005.csv")
        d[["Close"]].rename(columns={"Close": "close"}).to_csv(f, index_label="date")
        path = [f]
    return pd.read_csv(path[-1], index_col="date", parse_dates=True)["close"] / 100.0


def build(acc_specs, prep, irx, cal):
    spread_by, swap_by, lot = {}, {}, {}
    for k, s in acc_specs["symbole"].items():
        if s is None:
            continue
        price = s["bid"] or float(prep[k]["df"]["ref"].iloc[-1]) if k in prep else s["bid"]
        if not price:
            continue
        sp = s["spread"] * s["point"] / price / 2 if s["bid"] and s["spread"] else 0.00025
        mode = s["swap_mode"]
        def rate(x):
            if mode == 1:
                return x * s["point"] * 365 / price
            if mode == 3:
                return x * 365 / (s["trade_contract_size"] * price)
            if mode == 5:
                return x / 100.0
            return 0.0
        swap_by[k] = (-rate(s["swap_long"]), -rate(s["swap_short"]))
        spread_by[k] = sp
        lot[k] = {"contract": s["trade_contract_size"], "min": s["volume_min"], "step": s["volume_step"]}
    today = float(irx.iloc[-1])
    shift = (today - irx.reindex(cal).ffill()).fillna(0.0)
    return spread_by, swap_by, lot, shift.to_dict()


def main():
    specs = json.load(open(sorted(glob.glob(os.path.join(D.FROZEN_DIR, "faber_symbol_specs_*.json")))[-1], encoding="utf-8"))
    isr = json.load(open(R.OUT_IS, encoding="utf-8"))
    prep = R.load_all(with_btc=True)
    cal = pd.DatetimeIndex(sorted(set().union(*[v["df"].index for v in prep.values()])))
    irx = irx_series()
    mp = {q: dict(v) for q, v in isr["mae_params"].items()}
    for q, v in mp.items():
        v.setdefault("BTC", float(np.median(list(v.values()))))
    stop = R.stop_grid(mp)[isr["finalisten_stopp"]]
    eurusd = specs["konten"]["TTP"]["symbole"]["EURUSD"]["bid"]
    accounts = {
        "TTP": E.Account("TTP", specs["konten"]["TTP"]["equity"], True),
        "EK": E.Account("EK", specs["konten"]["EK"]["equity"] * eurusd, True),
    }
    res = {"specs_datei": specs["stand"], "konten": {k: a.equity0 for k, a in accounts.items()},
           "kosten_je_konto": {}, "finalisten": {}, "explorativ_ek": {}, "btc": {}}
    costs = {}
    for acc, a in accounts.items():
        spread_by, swap_by, lot, shift = build(specs["konten"][acc], prep, irx, cal)
        a.specs = lot
        res["kosten_je_konto"][acc] = {k: {"spread_je_seite_pct": round(spread_by[k] * 100, 4),
                                           "kosten_long_pa_pct": round(swap_by[k][0] * 100, 2),
                                           "kosten_short_pa_pct": round(swap_by[k][1] * 100, 2), **lot[k]}
                                       for k in swap_by}
        costs[acc] = {
            "heute": E.Costs(spread_by=spread_by, swap_by=swap_by),
            "zinsangep": E.Costs(spread_by=spread_by, swap_by=swap_by, shift=shift, shift_insts=SHIFT_INSTS),
        }

    def sz(sp):
        return E.Sizing(sp["risk"], open_risk_cap=sp["open_risk_cap"], vol_target=sp["vol_target"],
                        vol_filter_half=sp["vol_filter_half"])

    for name in isr["finalisten"]:
        sp = isr["stufe3_kandidaten"][name]["spec"]
        sl = R.sleeves_for(prep, sp["insts"], sp["mode"], sp["shorts"], sp["alts"])
        out = {}
        for acc, a in accounts.items():
            for model, c in costs[acc].items():
                for lab, (s0, s1) in {"is_2001_2012": (R.IS_START, R.IS_END), "oos_2013_2026": (R.OOS_START, R.END)}.items():
                    m, r = R.evaluate(prep, sl, stop, sz(sp), costs=c, account=a, start=s0, end=s1,
                                      mc=(acc == "TTP" and lab.startswith("oos")))
                    out[f"{acc}_{model}_{lab}"] = m
            m, _ = R.evaluate(prep, R.sleeves_for(prep, sp["insts"], "always"), stop, sz(sp),
                              costs=costs[acc]["zinsangep"], account=a, start=R.OOS_START, end=R.END)
            out[f"{acc}_kontrolle_immer_long_zinsangep_oos"] = m
        res["finalisten"][name] = out
        print(name, json.dumps(out, default=float)[:2500], flush=True)

    # BTC statt Cash mit echtem Swap (TTP -29 %/Jahr), nur OOS
    sp = isr["stufe3_kandidaten"][isr["finalisten"][0]]["spec"]
    for alts in (["BTC"], ["GOLD", "BTC"]):
        for acc, a in accounts.items():
            m, _ = R.evaluate(prep, R.sleeves_for(prep, sp["insts"], sp["mode"], sp["shorts"], alts), stop, sz(sp),
                              costs=costs[acc]["zinsangep"], account=a, start=R.OOS_START, end=R.END)
            res["btc"][f"{acc}_{'_'.join(alts)}"] = m

    # EK explorativ (NICHT vorab ausgewaehlt): einzelne Indexbeine, SMA10, A5-SL, 1 % / 2 % Risiko
    for insts in (["SP500"], ["SP500", "NASDAQ"], ["SP500", "NASDAQ", "DAX", "US30"]):
        for risk in (0.01, 0.02):
            m, _ = R.evaluate(prep, R.sleeves_for(prep, insts), stop, E.Sizing(risk),
                              costs=costs["EK"]["zinsangep"], account=accounts["EK"], start=R.OOS_START, end=R.END, mc=True)
            res["explorativ_ek"][f"{'+'.join(insts)}_r{risk*100:g}"] = m
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=float)
    print(json.dumps({k: v for k, v in res.items() if k != "finalisten"}, indent=1, default=float))


if __name__ == "__main__":
    main()
