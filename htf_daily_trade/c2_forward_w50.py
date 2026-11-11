"""Forward-Test Daily-Kandidat W50 (Vorwochen-Mitte, Lock htf_daily_twin, Hash 5c82f5d4) + Referenz EL 6c55e525.

    python -m htf_daily_trade.c2_forward_w50                  # Ledger neu rechnen, Aenderungen melden
    python -m htf_daily_trade.c2_forward_w50 --kein-telegram  # nur rechnen

Nutzerauftrag 11.11.2026: beste Leiter-Variante als Forward mitlaufen lassen. NUR Log + Telegram, keine Orders.
Laeuft im Task „C2-Forward-Log“ nach dem alten Forward (aea4189b), der unveraendert bleibt.
Trades exakt mit den Backtest-Funktionen (c2_bis_heute.w50_trades / el_trades) auf Tageskerzen bis zum
letzten abgeschlossenen UTC-Tag, ab START. Zusaetzlich „wartet“: frische Signale (Filter Stand Signaltag),
deren Limit noch nicht gefuellt und noch gueltig ist (EL 3 Tage, W50 10 Tage).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.filters.cot_flow import CotFlowFilter, fetch_legacy
from htf_daily_trade.backtest_macro import c_signals
from htf_daily_trade.backtest_r import features
from htf_daily_trade.c2_bis_heute import el_trades, last_day, load_to_today, w50_trades
from htf_daily_trade.c2_veto_combos import commodity_state
from htf_daily_trade.filter_matrix import MARKETS, WARMUP, trend_dirs
from research_lock import Lock

START = "2026-11-12"
LEDGER = Path(__file__).resolve().parent / "forward" / "c2_w50_forward_ledger.csv"
KEY = ["variante", "markt", "seite", "tag"]
GUELTIG = {"EL": 3, "W50": 10}


def pending(end: pd.Timestamp) -> list[dict]:
    cot = CotFlowFilter(4)
    rows = []
    for name, (_, grid, _) in MARKETS.items():
        x = features(load_to_today(name).loc[pd.Timestamp(WARMUP):end], grid)
        n = len(x)
        nxt = x.index[-1] + pd.offsets.BDay(1)
        ext = pd.concat([x, pd.DataFrame(np.nan, index=[nxt], columns=x.columns)])
        td = trend_dirs(x)
        h, l, c = x["High"].to_numpy(), x["Low"].to_numpy(), x["Close"].to_numpy()
        wk = x[["High", "Low"]].resample("W-FRI").agg({"High": "max", "Low": "min"})
        for s in (s for s in c_signals(ext) if s["kind"] == "C2" and s["i"] >= n - 10):
            t, side = s["i"], s["side"]
            sign = 1 if side == "long" else -1
            day1 = x.index[t + 1] if t + 1 < n else nxt
            if td["T6"].iat[t] * sign >= 0 or cot.direction(name, day1) * sign <= 0:
                continue
            prev_w = wk[wk.index < day1 - pd.Timedelta(days=day1.dayofweek)]
            wh, wl = prev_w["High"].iat[-1], prev_w["Low"].iat[-1]
            lv = {"EL": (c[t] + s["frac_lvl"]) / 2,
                  "W50": wh - 0.5 * (wh - wl) if sign == 1 else wl + 0.5 * (wh - wl)}
            stops = {"EL": s["frac_lvl"], "W50": s["frac_lvl"] - sign * 0.5 * s["atr"]}
            for v, lvl in lv.items():
                if sign * (c[t] - lvl) <= 0 or sign * (lvl - stops[v]) <= 0:
                    continue
                seen = range(t + 1, n)
                if len(seen) >= GUELTIG[v]:
                    continue
                if any((sign == 1 and l[k] <= lvl) or (sign == -1 and h[k] >= lvl) for k in seen):
                    continue
                rows.append({"variante": v, "markt": name, "seite": side, "tag": x.index[t].date(),
                             "status": "wartet", "limit": lvl, "stop": stops[v],
                             "gueltig_bis": (x.index[t] + pd.offsets.BDay(GUELTIG[v])).date()})
    if not rows:
        return rows
    p = pd.DataFrame(rows).assign(datum=lambda d: pd.to_datetime(d["tag"]))
    p["RS"] = commodity_state(p, start="2026-01-01", end=(end + pd.Timedelta(days=5)).strftime("%Y-%m-%d"))
    return p[p["RS"] != "gegen"].drop(columns=["datum", "RS"]).to_dict("records")


def scan(start: str = START) -> pd.DataFrame:
    end = last_day()
    el = el_trades(start, end)
    w50 = w50_trades(end)
    w50 = w50[w50["einstieg"] >= pd.Timestamp(start)] if len(w50) else w50
    rows = []
    for t in (el, w50):
        for r in t.itertuples():
            rows.append({"variante": r.variante, "markt": r.markt, "seite": r.seite, "tag": r.einstieg.date(),
                         "status": "offen" if r.offen else "geschlossen", "einstieg_tag": r.einstieg.date(),
                         "exit_tag": None if r.offen else r.ausstieg.date(), "r": r.r_TTP})
    rows += [r for r in pending(end) if pd.Timestamp(r["tag"]) >= pd.Timestamp(start) - pd.Timedelta(days=14)]
    t = pd.DataFrame(rows, columns=KEY + ["status", "limit", "stop", "gueltig_bis", "einstieg_tag", "exit_tag", "r"])
    t["stand"] = end.date()
    return t.sort_values(["tag", "variante", "markt"]).reset_index(drop=True)


def meldungen(neu: pd.DataFrame, alt: pd.DataFrame | None) -> list[str]:
    prev = {} if alt is None or alt.empty else {tuple(map(str, k)): s for k, s in
                                                 zip(alt[KEY].itertuples(index=False), alt["status"])}
    out = []
    for _, r in neu.iterrows():
        k, st = tuple(map(str, (r["variante"], r["markt"], r["seite"], r["tag"]))), r["status"]
        if prev.get(k) == st:
            continue
        v = "W50 (Vorwochen-Mitte)" if r["variante"] == "W50" else "EL (Referenz)"
        if st == "wartet":
            out.append(f"🆕 Daily {v}: {r['markt']} {r['seite'].upper()} Limit {r['limit']:.5g}, Stop {r['stop']:.5g}, "
                       f"gültig bis {r['gueltig_bis']}")
        elif st == "offen":
            out.append(f"▶️ Daily {v} gefüllt: {r['markt']} {r['seite'].upper()} am {r['einstieg_tag']}")
        elif st == "geschlossen":
            out.append(f"✅ Daily {v} geschlossen: {r['markt']} {r['seite'].upper()} {r['r']:+.2f} R")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=START)
    ap.add_argument("--out", default=str(LEDGER))
    ap.add_argument("--kein-telegram", action="store_true")
    ap.add_argument("--wochenbericht", action="store_true")
    a = ap.parse_args()
    Lock("htf_daily_twin").register_forward(START, "2027-11-12", 30)
    try:
        print(f"COT: {fetch_legacy()} neue Berichte")
    except Exception as e:  # Netz/CFTC nicht erreichbar: mit Bestand weiterrechnen
        print(f"COT-Abruf fehlgeschlagen: {e}")
    out = Path(a.out)
    alt = pd.read_csv(out) if out.exists() else None
    t = scan(a.start)
    out.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(out, index=False)
    msgs = meldungen(t, alt)
    if a.wochenbericht:
        for v in ("W50", "EL"):
            g = t[(t["variante"] == v) & (t["status"] == "geschlossen")]
            msgs.append(f"📊 Daily-Forward {v} seit {a.start}: {len(g)} Trades, Σ {g['r'].sum():+.2f} R, "
                        f"offen {int(((t['variante'] == v) & (t['status'] == 'offen')).sum())}")
    print(f"{len(t)} Zeilen, Stand {t['stand'].iat[0] if len(t) else '-'}, "
          f"Status {t['status'].value_counts().to_dict() if len(t) else {}}")
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
