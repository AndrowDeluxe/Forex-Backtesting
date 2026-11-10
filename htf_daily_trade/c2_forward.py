"""Forward-Test C2 + Zins-Momentum + Regime-Matrix (eingefroren aea4189b) -- nur Log + Telegram.

    python -m htf_daily_trade.c2_forward                  # Ledger neu rechnen, Aenderungen melden
    python -m htf_daily_trade.c2_forward --kein-telegram  # nur rechnen
    python -m htf_daily_trade.c2_forward --start 2026-01-01 --kein-telegram --out <csv>  # Rueckwaertsprobe

Nutzerentscheid 11.11.2026: keine Orders, nichts beruehrt echtes Geld. Regeln unveraendert aus
c2_goldfilter (Signal C2, Limit 50 %, 3 Tage, Stop S1, Ausstieg nach 10 Tagen, Gold-Zinskurven-Filter)
und c2_filter_overlap (F1 Zins-Momentum, F3 Regime-Matrix). Das Ledger wird jeden Lauf ab START
komplett neu gerechnet (deterministisch). Gefilterte Trades laufen als Schatten mit.

Status: wartet (Limit liegt) / verfallen (3 Tage ohne Fuellung) / offen (R zum letzten Schluss) /
geschlossen. im_test = Gold-Filter ok, F1 und F3 nicht dagegen, Seite nicht durch offenen Trade belegt.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.filters.zinskurve_regime import GoldZinskurvenFilter, regime_series
from fusion_lab.macro_data import store
from htf_daily_trade.backtest_macro import c_signals
from htf_daily_trade.backtest_r import MARKETS, features
from htf_daily_trade.backtest_varianten import LIMIT_DAYS, simulate
from htf_daily_trade.c2_filter_overlap import keep, label_trades
from htf_daily_trade.c2_goldfilter import CONFIG
from htf_daily_trade.forward_data import load_market_forward

START = "2026-11-12"
LEDGER = Path(__file__).resolve().parent / "forward" / "c2_forward_ledger.csv"
KEY = ["markt", "seite", "signal_tag"]
MAX_HOLD = 10  # T8
ZINS_KEYS = ["US.2y", "EA.2y", "GB.2y", "AU.2y", "JP.2y"]


def _limit_fill(x: pd.DataFrame, side: str, start: int, lvl: float):
    """Wie backtest_varianten.entries.limit_fill."""
    h, l, o = x["High"].to_numpy(), x["Low"].to_numpy(), x["Open"].to_numpy()
    for k in range(start, min(len(x), start + LIMIT_DAYS)):
        if side == "long" and l[k] <= lvl:
            return k, min(o[k], lvl)
        if side == "short" and h[k] >= lvl:
            return k, max(o[k], lvl)
    return None, None


def scan_market(name: str, start: pd.Timestamp, flt, today=None) -> list[dict]:
    _, grid, cost = MARKETS[name]
    x = features(load_market_forward(name, today).loc["2014-01-01":], grid)
    last = len(x) - 1
    # Platzhalterkerze, damit auch ein Signal am letzten abgeschlossenen Tag erkannt wird
    ext = pd.concat([x, pd.DataFrame(np.nan, index=[x.index[-1] + pd.Timedelta(days=1)], columns=x.columns)])
    sigs = [s for s in c_signals(ext) if s["kind"] == "C2"]
    h, l, c = x["High"].to_numpy(), x["Low"].to_numpy(), x["Close"].to_numpy()
    rows, busy = [], {"long": -1, "short": -1}
    filled = []
    for s in sigs:
        t, side = s["i"], s["side"]
        lvl = (c[t] + s["frac_lvl"]) / 2
        k, px = _limit_fill(x, side, t + 1, lvl)
        base = {"markt": name, "seite": side, "signal_tag": x.index[t].date(), "limit": lvl, "stop": s["frac_lvl"]}
        if k is None:
            if x.index[t] >= start:
                rows.append({**base, "status": "wartet" if t + LIMIT_DAYS > last else "verfallen",
                             "datum": (x.index[t] + pd.offsets.BDay(1)).date(), "belegt": busy[side] >= last})
            continue
        filled.append((k, s, px, base))
    for k, s, px, base in sorted(filled, key=lambda z: z[0]):
        side, t = s["side"], s["i"]
        fill_t = x.index[k]
        gold_ok = name != "XAUUSD" or flt.allows(side, fill_t)
        belegt = k <= busy[side]
        en = dict(side=side, fill=k, price=px, struct=s["frac_lvl"], atr=s["atr"], start=k, limit=True)
        res = simulate(x, en, CONFIG["stop"], CONFIG["ziel"], cost, last)
        if res is None:
            continue
        e = res["exit_k"]
        stopped = (l[e] <= s["frac_lvl"]) if side == "long" else (h[e] >= s["frac_lvl"])
        offen = (not stopped) and e == last and last < k + MAX_HOLD
        if gold_ok and not belegt:  # wie evaluate(): nur gueltige Basis-Trades belegen die Seite
            busy[side] = e
        if x.index[t] < start:
            continue
        rows.append({**base, "status": "offen" if offen else "geschlossen", "einstieg": px,
                     "fuell_tag": fill_t.date(), "exit_tag": None if offen else x.index[e].date(),
                     "r": res["r"], "datum": fill_t.date(), "gold_filter": "ok" if gold_ok else "gegen",
                     "belegt": belegt})
    return rows


def scan(start: str = START, today=None) -> pd.DataFrame:
    regime_series(CONFIG["gold_filter"]["lag"], refresh=True)  # FRED-Cache fuer Regime + Gold-Filter auffrischen
    flt = GoldZinskurvenFilter(**CONFIG["gold_filter"])
    rows = [r for name in MARKETS for r in scan_market(name, pd.Timestamp(start), flt, today)]
    if not rows:
        return pd.DataFrame(columns=KEY + ["status"])
    t = pd.DataFrame(rows)
    t["gold_filter"] = t.get("gold_filter", pd.Series(dtype=object)).fillna("ok")
    t = label_trades(t)
    t["im_test"] = keep(t, ("F1", "F3")) & (t["gold_filter"] == "ok") & ~t["belegt"].fillna(False).astype(bool)
    return t.sort_values(["signal_tag", "markt"]).reset_index(drop=True)


def zinsdaten_alt(max_tage: int = 6) -> list[str]:
    d = store.latest("macro")
    last = d[d["key"].isin(ZINS_KEYS)].groupby("key")["date"].max()
    heute = pd.Timestamp.now().normalize()
    return [f"{k} {v.date()}" for k, v in last.items() if (heute - v).days > max_tage]


def _fmt(r: pd.Series) -> str:
    px = (lambda v: f"{v:.5g}")
    s = f"{r['markt']} {r['seite'].upper()} (Signal {r['signal_tag']}): Limit {px(r['limit'])}, Stop {px(r['stop'])}"
    return s + ("" if r["im_test"] else "  [Schatten: Filter dagegen]")


def meldungen(neu: pd.DataFrame, alt: pd.DataFrame | None) -> list[str]:
    prev = {} if alt is None or alt.empty else {tuple(map(str, k)): s for k, s in
                                                 zip(alt[KEY].itertuples(index=False), alt["status"])}
    out = []
    for _, r in neu.iterrows():
        k, st = tuple(map(str, (r["markt"], r["seite"], r["signal_tag"]))), r["status"]
        if prev.get(k) == st or not r["im_test"]:
            continue
        if st == "wartet":
            out.append("🆕 C2-Signal: " + _fmt(r) + f", gültig 3 Tage")
        elif st == "offen":
            out.append(f"▶️ C2 gefüllt: {r['markt']} {r['seite'].upper()} zu {r['einstieg']:.5g}, Stop {r['stop']:.5g}")
        elif st == "geschlossen":
            out.append(f"✅ C2 geschlossen: {r['markt']} {r['seite'].upper()} {r['r']:+.2f} R")
        elif st == "verfallen" and prev.get(k) == "wartet":
            out.append(f"⌛ C2 verfallen (nicht gefüllt): {r['markt']} {r['seite'].upper()}")
    return out


def wochenbericht(t: pd.DataFrame) -> str:
    g = t[t["status"] == "geschlossen"]
    test, schatten = g[g["im_test"]], g
    return (f"📊 C2-Forward seit {START}: {len(test)} Trades im Test, Σ {test['r'].sum():+.2f} R"
            f" (ohne Makro-Filter: {len(schatten)} Trades, Σ {schatten['r'].sum():+.2f} R);"
            f" offen {int(((t['status'] == 'offen') & t['im_test']).sum())},"
            f" wartend {int(((t['status'] == 'wartet') & t['im_test']).sum())}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=START)
    ap.add_argument("--out", default=str(LEDGER))
    ap.add_argument("--kein-telegram", action="store_true")
    ap.add_argument("--wochenbericht", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    alt = pd.read_csv(out) if out.exists() else None
    t = scan(a.start)
    out.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(out, index=False)
    msgs = meldungen(t, alt)
    warn = zinsdaten_alt()
    if warn:
        hinweis = "⚠️ C2-Forward: Filterdaten alt (" + ", ".join(warn) + ") -- F1 evtl. ungenau"
        print(hinweis)
        if msgs or a.wochenbericht:  # nicht taeglich allein melden, nur mit echter Meldung
            msgs.append(hinweis)
    if a.wochenbericht:
        msgs.append(wochenbericht(t))
    print(f"{len(t)} Zeilen, Status {t['status'].value_counts().to_dict() if len(t) else {}}")
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
