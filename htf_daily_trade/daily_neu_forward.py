"""Forward-Schatten der zwei Daily-Varianten aus daily_neu_is (Nutzerauftrag 27.11.2026). NUR Log + Telegram.

    python -m htf_daily_trade.daily_neu_forward                  # Ledger neu rechnen, Aenderungen melden
    python -m htf_daily_trade.daily_neu_forward --kein-telegram

Varianten (Lock `htf_daily_neu`, eingefroren beim ersten Lauf):
  C2EL_F3   C2 (Faber gegen, COT mit, Rohstoff-Veto) + Makro-Veto, Limit 50 % Ausloese-Schluss<->Strukturstop
            3 Tage, Strukturstop, 10 Handelstage
  R_EO_F2F4 Typ R + ML-Flaeche >= 50 % (3 Kerzen) + Fuelltag kein News-Tag, Markt zur Eroeffnung nach der
            Fractal-Bestaetigung, Strukturstop, Ausstieg gegenlaeufiges Fractal (max. 30 Tage)
Gleiche Funktionen wie der Backtest (daily_neu_is), Tageskerzen UTC bis zum letzten abgeschlossenen Tag
(c2_bis_heute.load_to_today). Ideen ab START. Status: wartet (Signal da, Einstieg steht aus) / offen / geschlossen.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.filters.cot_flow import CotFlowFilter
from htf_daily_trade import daily_neu_is as dn
from htf_daily_trade import indikator_edge as ie
from htf_daily_trade.backtest_r import features
from htf_daily_trade.c2_bis_heute import last_day, load_to_today
from htf_daily_trade.c2_veto_combos import commodity_state
from htf_daily_trade.filter_matrix import MARKETS, MacroDirs
from research_lock import Lock

START = "2026-11-27"
EVAL, MIN_TRADES = "2027-11-27", 30
LEDGER = Path(__file__).resolve().parent / "forward" / "daily_neu_forward_ledger.csv"
KEY = ["variante", "markt", "seite", "signal"]
VARIANTS = {"C2EL_F3": ("C2", "EL", ("F3",)), "R_EO_F2F4": ("R", "EO", ("F2", "F4"))}
CONFIG = {k: {"basis": b, "einstieg": e, "filter": list(f)} for k, (b, e, f) in VARIANTS.items()}
HOLD = {"C2": 10, "R": 30}


def scan(start: str = START) -> pd.DataFrame:
    from news_calendar.filter import get_news_dates
    end = last_day()
    cot = CotFlowFilter(4)
    md = MacroDirs()
    md.init_extra()
    md.news = set(get_news_dates("2026-01-01", (end + pd.Timedelta(days=40)).strftime("%Y-%m-%d")))
    rows, states = [], {}
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_to_today(name).loc[pd.Timestamp(dn.WARMUP):end], grid)
        n = len(x)
        nxt = x.index[-1] + pd.offsets.BDay(1)
        ext = pd.concat([x, pd.DataFrame(np.nan, index=[nxt], columns=x.columns)])
        st = ie.states(x.rename(columns=str.lower))[["I2", "I4"]]
        st["X2"] = 0
        states[name] = st
        for idea in dn.ideas_market(name, ext, cot):
            if ext.index[idea["sig"]] < pd.Timestamp(start) or idea["sig"] >= n:
                continue
            base = idea["base"]
            for var, (b, e, _) in VARIANTS.items():
                if b != base:
                    continue
                row = {"variante": var, "base": base, "markt": name, "side": idea["side"], "sign": idea["sign"],
                       "sigdate": ext.index[idea["sig"]], "datum": ext.index[idea["start"]]}
                res = dn.daily_entries(x, {**idea, "end": min(idea["end"], n - 1)}, cost) if idea["start"] < n else {}
                v = res.get(e)
                lvl = idea["el"] if e == "EL" else None
                if v is None:
                    days_left = (3 if e == "EL" else 1) - (n - idea["start"])
                    if days_left <= 0:
                        continue                         # Limit verfallen / nicht ausfuehrbar
                    rows.append({**row, "status": "wartet", "limit": lvl, "stop": idea["struct"], "fill": pd.NaT})
                    continue
                r0, r, kf, kx = v
                offen = kx == n - 1 and kx - kf < HOLD[base] and r0 > -0.99
                rows.append({**row, "status": "offen" if offen else "geschlossen", "limit": lvl,
                             "stop": idea["struct"], "fill": x.index[kf], "exit": None if offen else x.index[kx],
                             "fill_k": kf, "exit_k": kx, "r": r})
    t = pd.DataFrame(rows)
    for col in ("fill_k", "exit_k", "exit", "r"):
        if col not in t:
            t[col] = np.nan
    if t.empty:
        return pd.DataFrame(columns=KEY + ["status", "limit", "stop", "einstieg_tag", "exit_tag", "r", "stand"])
    ideas = t.drop_duplicates(["base", "markt", "side", "sigdate"])[["base", "markt", "side", "sign", "sigdate", "datum"]]
    ideas = dn.add_filters(ideas, states, md)
    ideas["RS"] = commodity_state(ideas.rename(columns={"side": "seite"}), start="2026-01-01",
                                  end=(end + pd.Timedelta(days=5)).strftime("%Y-%m-%d"))
    t = t.merge(ideas.drop(columns=["sign", "datum"]), on=["base", "markt", "side", "sigdate"])
    t = t[~((t["base"] == "C2") & (t["RS"] == "gegen"))]
    t["F4"] = ~t["fill"].fillna(t["datum"]).dt.normalize().isin(md.news)
    keep = []
    for var, (_, _, filt) in VARIANTS.items():
        s = t[t["variante"] == var]
        for f in filt:
            s = s[s[f]]
        busy = {}
        for r in s.sort_values("sigdate").itertuples():     # je Markt und Seite ein Trade zur Zeit
            k = (r.markt, r.side)
            if pd.notna(r.fill_k):
                if r.fill_k <= busy.get(k, -1):
                    continue
                busy[k] = r.exit_k
            keep.append(r.Index)
    t = t.loc[keep]
    out = pd.DataFrame({"variante": t["variante"], "markt": t["markt"], "seite": t["side"],
                        "signal": t["sigdate"].dt.date, "status": t["status"], "limit": t["limit"], "stop": t["stop"],
                        "einstieg_tag": t["fill"].dt.date, "exit_tag": pd.to_datetime(t["exit"]).dt.date,
                        "r": t["r"], "makro_gegen": t["makro_gegen"]})
    out["stand"] = end.date()
    return out.sort_values(["signal", "variante", "markt"]).reset_index(drop=True)


def meldungen(neu: pd.DataFrame, alt: pd.DataFrame | None) -> list[str]:
    prev = {} if alt is None or alt.empty else {tuple(map(str, k)): s for k, s in
                                                 zip(alt[KEY].itertuples(index=False), alt["status"])}
    out = []
    for _, r in neu.iterrows():
        k, st = tuple(map(str, (r["variante"], r["markt"], r["seite"], r["signal"]))), r["status"]
        if prev.get(k) == st:
            continue
        v = {"C2EL_F3": "C2 Limit + Makro-Veto", "R_EO_F2F4": "Typ R + ML-Fläche"}[r["variante"]]
        if st == "wartet":
            wo = f"Limit {r['limit']:.5g}" if pd.notna(r["limit"]) else "Eröffnung"
            out.append(f"🆕 Daily-Schatten {v}: {r['markt']} {r['seite'].upper()} {wo}, Stop {r['stop']:.5g}")
        elif st == "offen":
            out.append(f"▶️ Daily-Schatten {v} gefüllt: {r['markt']} {r['seite'].upper()} am {r['einstieg_tag']}")
        elif st == "geschlossen":
            out.append(f"✅ Daily-Schatten {v} geschlossen: {r['markt']} {r['seite'].upper()} {r['r']:+.2f} R")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=START)
    ap.add_argument("--out", default=str(LEDGER))
    ap.add_argument("--kein-telegram", action="store_true")
    ap.add_argument("--wochenbericht", action="store_true")
    a = ap.parse_args()
    lock = Lock(dn.LOCK)
    lock.freeze(CONFIG)
    lock.register_forward(START, EVAL, MIN_TRADES)
    out = Path(a.out)
    alt = pd.read_csv(out) if out.exists() else None
    t = scan(a.start)
    out.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(out, index=False)
    msgs = meldungen(t, alt)
    if a.wochenbericht:
        for v in VARIANTS:
            g = t[(t["variante"] == v) & (t["status"] == "geschlossen")]
            msgs.append(f"📊 Daily-Schatten {v} seit {a.start}: {len(g)} Trades, Σ {g['r'].sum():+.2f} R, "
                        f"offen {int(((t['variante'] == v) & (t['status'] == 'offen')).sum())}")
    print(f"{len(t)} Zeilen, Stand {t['stand'].iat[0] if len(t) else '-'}")
    for m in msgs:
        print(m)
    if msgs and not a.kein_telegram:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "reports"))
        from telegram_notify import send_telegram_message
        send_telegram_message("\n".join(msgs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
