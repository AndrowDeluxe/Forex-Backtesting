"""OU-Modell: Ausfuehrung und kostentreibende Parameter optimieren (Research, 2026-09-17).

Plan: C:\\Users\\andre\\.claude\\plans\\breezy-wiggling-dove.md
Vorlauf:  scripts/research_ou_execution_costs.py (Kostenvalidierung 2026-09-16)
Daten:    scripts/research_ou_intraday_pull.py (TTP-Stundenkerzen + Spread-Stichproben)

Bloecke
  0  Kostenkurve: Spread je NY-Uhrzeit aus TTP-Tick-Stichproben
  1  Ausfuehrung auf Tageskerzen 2018-2026: Einstieg vor Schluss am Signaltag,
     Folgetag-Eroeffnung, Folgetag-Limit, Abweichungsgrenze (sym./nur nach oben)
  2  Einstiegszeit am Folgetag auf TTP-Stundenkerzen 2023-2026
  3  Modell-Hebel (max_hold, stop_sigma, be_trigger_r) mit der besten Ausfuehrung

Schutz gegen Ueberanpassung (Nutzerentscheid): Rangfolge NUR auf In-Sample,
Bewertung auf Out-of-Sample mit Bootstrap-Konfidenzintervall.
  Tageskerzen:  IS Signal < 2023-01-01, OOS ab 2023-01-01
  Stundenkerzen: IS Signal < 2025-01-01, OOS ab 2025-01-01

Ausfuehrungsfamilien (live unterschiedlich):
  funded  nur der Initial-SL liegt beim Broker (intraday), BE/TP/Max-Holding
          ueber den Re-Scan auf Schlusskursen
  ek      zusaetzlich BE-Stop und TP broker-seitig (intraday, am Fill-Preis)

Kostenmodell je Einstieg: halber Spread der Einstiegs-Uhrzeit (Block 0) +
3 bps Ausfuehrung (live gemessen: Fill vs. Mid +9 bps bei ~6 bps halbem Spread).
Limit-Einstieg: kein Spread-Kreuzen, gilt aber erst als gefuellt, wenn das
Tagestief um den halben Spread unter dem Limit lag. Exit 5 bps, Swap 1,78 bps je
Kalendertag (beides live gemessen).

Aufruf: python research_ou_execution_optimization.py [block0|block1|block2|block3|all]
"""
import json
import sys
from itertools import product
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import research_ou_execution_costs as rx  # noqa: E402
import challenge_portfolio.paper_bot as pb  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

INTRA = REPO / "ou_paper_backtest" / "data_cache" / "intraday_ttp"
RES = REPO / "ou_paper_backtest" / "results"
OUT_JSON = RES / "execution_optimization_20260917.json"
NY = ZoneInfo("America/New_York")
SERVER = ZoneInfo("Europe/Helsinki")

EXEC_SLIP_BPS = 3.0
EXIT_BPS = 5.0
SWAP_BPS_DAY = 1.78
IS_END_DAILY = pd.Timestamp("2023-01-01")
IS_END_HOURLY = pd.Timestamp("2025-01-01")
MIN_IS_TRADES = 150
rng = np.random.default_rng(20260917)


# ============================================================ Block 0 -- Kostenkurve
def spread_curve() -> dict:
    """Median-Spread (bps) je Bucket ueber alle Ticker und Tage."""
    s = pd.read_parquet(INTRA / "spread_samples.parquet")
    per_ticker = s.groupby(["bucket", "ticker"])["spread_bps"].median().reset_index()
    curve = per_ticker.groupby("bucket")["spread_bps"].agg(["median", lambda x: x.quantile(0.75), "size"])
    curve.columns = ["median_bps", "p75_bps", "n_tickers"]
    return {b: {k: round(float(v), 2) for k, v in r.items()} for b, r in curve.iterrows()}


def entry_cost(curve: dict, bucket: str) -> float:
    return curve[bucket]["median_bps"] / 2 + EXEC_SLIP_BPS


# ============================================================ gemeinsame Helfer
def stats(r) -> dict:
    r = np.asarray(r, dtype=float)
    if len(r) == 0:
        return {"n": 0}
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    boot = rng.choice(r, size=(2000, len(r)), replace=True).mean(axis=1)
    return {"n": int(len(r)), "avg_R": round(float(r.mean()), 4), "sum_R": round(float(r.sum()), 1),
            "hit": round(float((r > 0).mean()), 3), "PF": round(float(w / l), 3) if l else None,
            "ci95": [round(float(np.quantile(boot, 0.025)), 4), round(float(np.quantile(boot, 0.975)), 4)]}


def split_stats(res: list[dict], is_end: pd.Timestamp) -> dict:
    d = pd.DataFrame(res)
    if d.empty:
        return {"IS": {"n": 0}, "OOS": {"n": 0}}
    d0 = pd.to_datetime(d["d0"])
    return {"IS": stats(d.loc[d0 < is_end, "R"]), "OOS": stats(d.loc[d0 >= is_end, "R"]),
            "skipped_share": None}


# ============================================================ Replay auf Tageskerzen
def replay_daily(tr, bars, *, entry_mode="open_d1", gate=0.035, gate_mode="sym", family="funded",
                 entry_cost_bps=0.0, exit_bps=0.0, swap_bps_day=0.0, limit_k=0.0, limit_fallback=False,
                 max_hold=10, be_r=0.35, spread_half_bps=0.0):
    """Verallgemeinerung von research_ou_execution_costs.replay().

    entry_mode: close_d0 (Einstieg zum Schluss des Signaltags), open_d1, close_d1,
                limit_d1 (Limit c0 - limit_k*stopdist, Tag gueltig).
    gate: max. Abweichung Einstieg vs. Signalpreis (None = aus); gate_mode sym|up.
    Rueckgabe dict(R, reason, days) oder None (kein Einstieg)."""
    c0, sd = tr["c0"], tr["stop_dist"]
    sl0 = c0 - sd
    after = bars[bars.index > tr["d0"]]
    if after.empty:
        return None

    first_sl_bar = 0  # Index in `after`, ab dem der Intraday-SL geprueft wird
    if entry_mode == "close_d0":
        raw = c0
    elif entry_mode == "open_d1":
        raw = after["Open"].iloc[0]
    elif entry_mode == "close_d1":
        raw = after["Close"].iloc[0]
        first_sl_bar = 1
    elif entry_mode == "limit_d1":
        lim = c0 - limit_k * sd
        b = after.iloc[0]
        need = lim * (1 - spread_half_bps / 1e4)
        if b["Open"] <= lim:
            raw = b["Open"]  # Gap unter das Limit -> Fill zur Eroeffnung
        elif b["Low"] <= need:
            raw = lim
        elif limit_fallback:
            raw, first_sl_bar = b["Close"], 1
            entry_mode = "close_d1"
        else:
            return None
    else:
        raise ValueError(entry_mode)

    if entry_mode != "close_d0" and gate is not None:
        dev = (raw - c0) / c0
        if (gate_mode == "sym" and abs(dev) > gate) or (gate_mode == "up" and dev > gate):
            return None
    if raw <= sl0:
        return None

    entry = raw * (1 + entry_cost_bps / 1e4)
    risk = entry - sl0
    if risk <= 0:
        return None

    broker = family == "ek"
    if broker:
        be_level = raw + be_r * (raw - sl0) if be_r else None
        tp = raw + tr["rr"] * (raw - sl0) if tr["rr"] else None
        be_price = raw
    else:
        be_level = c0 + be_r * sd if be_r else None
        tp = c0 + tr["rr"] * sd if tr["rr"] else None
        be_price = c0
    stop, be_moved = sl0, False
    exit_px = reason = None
    days = 0
    entry_date = tr["d0"] if entry_mode == "close_d0" else after.index[0 if first_sl_bar == 0 else 0]
    for i, (dt, b) in enumerate(after.iterrows()):
        days = i + 1
        if i >= first_sl_bar:
            active = stop if broker else sl0
            if b["Low"] <= active:
                exit_px = min(b["Open"], active)
                reason = "BE" if (broker and be_moved) else "SL"
                break
            if broker and tp is not None and b["High"] >= tp:
                exit_px, reason = max(b["Open"], tp), "TP"
                break
            if broker and be_level is not None and not be_moved and b["High"] >= be_level:
                be_moved, stop = True, be_price
        close = b["Close"]
        if not broker and be_level is not None:
            if not be_moved and close >= be_level:
                be_moved = True
            elif be_moved and close <= be_price:
                exit_px, reason = close, "BE"
                break
        if not broker and tp is not None and close >= tp:
            exit_px, reason = close, "TP"
            break
        if days >= max_hold:
            exit_px, reason = close, "MaxHold"
            break
    if exit_px is None:
        return None
    exit_px *= 1 - exit_bps / 1e4
    cal_days = max((after.index[days - 1] - pd.Timestamp(entry_date)).days, 1)
    swap = raw * swap_bps_day / 1e4 * cal_days
    return {"R": (exit_px - entry - swap) / risk, "reason": reason, "days": days}


def run_daily(trades, ohlc, **kw):
    out, skipped = [], []
    for tr in trades:
        r = replay_daily(tr, ohlc[tr["ticker"]], **kw)
        if r is None:
            skipped.append(tr)
        else:
            out.append({**r, "d0": tr["d0"], "ticker": tr["ticker"], "engine_R": tr["engine_R"]})
    return out, skipped


# ============================================================ Regressionstest
def regression(trades, ohlc) -> dict:
    """Muss die Werte vom 2026-09-16 treffen (A +0,097 / C$ -0,011, gleiche Anzahl)."""
    a, _ = run_daily(trades, ohlc, entry_mode="close_d0", gate=None, family="funded")
    # A im alten Skript prueft den SL nur auf Schlusskursen -> eigener Ausgleich nicht moeglich;
    # verglichen wird deshalb direkt mit rx.replay (identische Trade-Liste, gleicher Datenstand)
    old_a = [rx.replay(t, ohlc[t["ticker"]], "A", 10, pb.OU_MODELL_BE_TRIGGER_R) for t in trades]
    old_c = [rx.replay(t, ohlc[t["ticker"]], "C$", 10, pb.OU_MODELL_BE_TRIGGER_R) for t in trades]
    new_c, _ = run_daily(trades, ohlc, entry_mode="open_d1", gate=0.035, family="funded",
                         entry_cost_bps=rx.COST_ENTRY_BPS, exit_bps=rx.COST_EXIT_BPS, swap_bps_day=rx.SWAP_BPS_DAY)
    old_c = [x for x in old_c if x]
    return {"old_A": rx.stats([x["R"] for x in old_a if x]), "old_Ccost": rx.stats([x["R"] for x in old_c]),
            "new_Ccost": rx.stats([x["R"] for x in new_c]),
            "match_Ccost": len(old_c) == len(new_c) and bool(np.allclose(sorted(x["R"] for x in old_c), sorted(x["R"] for x in new_c), atol=2e-3))}  # Swap-Basis inkl./exkl. Einstiegskosten


# ============================================================ Block 1
def block1(trades, ohlc, curve):
    c_open, c_close = entry_cost(curve, "09:35"), entry_cost(curve, "15:45")
    base = dict(exit_bps=EXIT_BPS, swap_bps_day=SWAP_BPS_DAY)
    variants = {
        "open_d1 gate3.5 (heute)": dict(entry_mode="open_d1", gate=0.035, entry_cost_bps=c_open),
        "close_d0 (vor Schluss am Signaltag)": dict(entry_mode="close_d0", gate=None, entry_cost_bps=c_close),
        "close_d1 gate3.5 (Folgetag vor Schluss)": dict(entry_mode="close_d1", gate=0.035, entry_cost_bps=c_close),
    }
    for k in (0.0, 0.25, 0.5):
        variants[f"limit_d1 k={k} verfallen"] = dict(entry_mode="limit_d1", gate=None, limit_k=k,
                                                    spread_half_bps=curve["10:00"]["median_bps"] / 2)
        variants[f"limit_d1 k={k} sonst Schluss"] = dict(entry_mode="limit_d1", gate=None, limit_k=k, limit_fallback=True,
                                                        entry_cost_bps=c_close, spread_half_bps=curve["10:00"]["median_bps"] / 2)
    for g in (0.01, 0.02, 0.03, 0.035, 0.05, None):
        variants[f"open_d1 gate {g} sym"] = dict(entry_mode="open_d1", gate=g, gate_mode="sym", entry_cost_bps=c_open)
        if g is not None:
            variants[f"open_d1 gate {g} nur-oben"] = dict(entry_mode="open_d1", gate=g, gate_mode="up", entry_cost_bps=c_open)

    result = {}
    for name, kw in variants.items():
        for fam in ("funded", "ek"):
            res, skipped = run_daily(trades, ohlc, family=fam, **base, **kw)
            st = split_stats(res, IS_END_DAILY)
            st["skipped_share"] = round(len(skipped) / len(trades), 3)
            st["skipped_engine_avgR"] = round(float(np.mean([t["engine_R"] for t in skipped])), 4) if skipped else None
            result[f"{fam} | {name}"] = st
        print(f"  {name:42s} funded IS {result['funded | ' + name]['IS'].get('avg_R')} "
              f"OOS {result['funded | ' + name]['OOS'].get('avg_R')}  skip {result['funded | ' + name]['skipped_share']}", flush=True)
    return result


# ============================================================ Block 2 -- Stundenkerzen
def load_h1(ticker):
    p = INTRA / f"{ticker}_H1.parquet"
    if not p.exists():
        return None
    d = pd.read_parquet(p)
    ts = pd.to_datetime(d["time"], unit="s").dt.tz_localize(SERVER, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert(NY)
    d = d.assign(ny=ts).dropna(subset=["ny"]).set_index("ny").sort_index()
    return d[["open", "high", "low", "close", "spread"]]


def daily_from_h1(h1):
    g = h1.groupby(h1.index.date)
    d = pd.DataFrame({"Open": g["open"].first(), "High": g["high"].max(), "Low": g["low"].min(), "Close": g["close"].last()})
    d.index = pd.to_datetime(d.index)
    return d


def replay_hourly(tr, h1, daily, entry_hour, family, curve_bucket, curve, max_hold=10, be_r=0.35):
    """Einstieg am Folgetag zur Eroeffnung der Stundenkerze `entry_hour` (NY, 9 = erster Quote 09:35).
    Stop/BE/TP relativ zum Signal in Prozent, auf die Broker-Preisebene uebertragen (TTP-Kurse sind
    nicht dividendenbereinigt). Tage mit Kurssprung > 35 % (Split) werden verworfen."""
    d0 = pd.Timestamp(tr["d0"]).normalize()
    if d0 not in daily.index:
        return None
    c0 = daily.loc[d0, "Close"]
    frac = tr["stop_dist"] / tr["c0"]
    sd = c0 * frac
    sl0 = c0 - sd
    after_days = daily[daily.index > d0]
    if after_days.empty:
        return None
    d1 = after_days.index[0]
    day1 = h1[h1.index.date == d1.date()]
    bar = day1[day1.index.hour == entry_hour]
    if bar.empty:
        return None
    raw = bar["open"].iloc[0]
    if abs(raw - c0) / c0 > 0.035 or raw <= sl0:
        return None
    window = after_days.iloc[:max_hold]
    if (window["Close"].pct_change().abs() > 0.35).any() or abs(window["Open"].iloc[0] / c0 - 1) > 0.35:
        return None
    entry = raw * (1 + entry_cost(curve, curve_bucket) / 1e4)
    risk = entry - sl0
    broker = family == "ek"
    be_level = (raw + be_r * (raw - sl0)) if broker else (c0 + be_r * sd)
    be_price = raw if broker else c0
    rr = tr["rr"]
    tp = ((raw + rr * (raw - sl0)) if broker else (c0 + rr * sd)) if rr else None
    stop, be_moved = sl0, False
    exit_px = reason = None
    days = 0
    for i, (dt, b) in enumerate(window.iterrows()):
        days = i + 1
        if i == 0:
            rest = day1[day1.index >= bar.index[0]]
            lo, hi = rest["low"].min(), rest["high"].max()
            op = raw
        else:
            lo, hi, op = b["Low"], b["High"], b["Open"]
        active = stop if broker else sl0
        if lo <= active:
            exit_px, reason = min(op, active), ("BE" if broker and be_moved else "SL")
            break
        if broker and tp is not None and hi >= tp:
            exit_px, reason = max(op, tp), "TP"
            break
        if broker and not be_moved and hi >= be_level:
            be_moved, stop = True, be_price
        close = b["Close"]
        if not broker:
            if not be_moved and close >= be_level:
                be_moved = True
            elif be_moved and close <= be_price:
                exit_px, reason = close, "BE"
                break
            if tp is not None and close >= tp:
                exit_px, reason = close, "TP"
                break
        if days >= max_hold:
            exit_px, reason = close, "MaxHold"
            break
    if exit_px is None:
        return None
    exit_px *= 1 - EXIT_BPS / 1e4
    cal = max((window.index[days - 1] - d1).days, 1)
    return {"R": (exit_px - entry - raw * SWAP_BPS_DAY / 1e4 * cal) / risk, "reason": reason}


def block2(trades, curve):
    hours = {9: "09:35", 10: "10:00", 11: "11:00", 12: "12:00", 13: "13:00", 14: "14:00", 15: "15:00"}
    cache = {}
    result = {}
    for fam in ("funded", "ek"):
        for h, bucket in hours.items():
            res = []
            for tr in trades:
                if tr["ticker"] not in cache:
                    h1 = load_h1(tr["ticker"])
                    cache[tr["ticker"]] = (h1, daily_from_h1(h1)) if h1 is not None else (None, None)
                h1, daily = cache[tr["ticker"]]
                if h1 is None:
                    continue
                r = replay_hourly(tr, h1, daily, h, fam, bucket, curve)
                if r:
                    res.append({**r, "d0": tr["d0"]})
            result[f"{fam} | Einstieg {bucket}"] = split_stats(res, IS_END_HOURLY)
            print(f"  {fam:6s} {bucket}: IS {result[f'{fam} | Einstieg {bucket}']['IS']}  OOS {result[f'{fam} | Einstieg {bucket}']['OOS']}", flush=True)
    return result


# ============================================================ Block 3 -- Modell-Hebel
def model_trades_params(ou_config, ou_portfolio, uni, ohlc, max_hold, stop_sigma, be_r):
    trades = []
    for mk, tick in uni.items():
        tick = [t for t in tick if t in ohlc]
        panel = pd.DataFrame({t: ohlc[t]["Close"] for t in tick}).sort_index()
        bench = rx.yf.download(ou_config.UNIVERSES[mk]["benchmark"], start=rx.DL_START, end="2026-09-17",
                               auto_adjust=True, progress=False)["Close"]
        if isinstance(bench, pd.DataFrame):
            bench = bench.iloc[:, 0]
        regime = (bench > bench.ewm(span=200).mean()).reindex(panel.index).ffill().fillna(False)
        rr = 1.5 if mk == "sp500" else None
        _, tl = ou_portfolio.simulate_bracket_portfolio(
            panel, list(panel.columns), rx.START, rx.END, stop_sigma=stop_sigma, rr_ratio=rr,
            be_trigger_r=be_r, allowed_directions=(1,), regime_filter=regime, max_hold=max_hold,
            risk_pct=pb.OU_MODELL_RISK_PCT, max_total_risk_pct=pb.OU_MODELL_MAX_TOTAL_RISK_PCT)
        std20 = panel.rolling(ou_config.BB_LOOKBACK).std()
        for t in tl:
            sd = std20.loc[t["entry_date"], t["ticker"]] * stop_sigma
            trades.append({"market": mk, "ticker": t["ticker"], "d0": t["entry_date"], "c0": t["entry_price"],
                           "stop_dist": sd, "rr": rr, "engine_R": (t["exit_price"] - t["entry_price"]) / sd})
    return trades


def block3(ou_config, ou_portfolio, uni, ohlc, curve, exec_kw):
    result = {}
    for max_hold, stop_sigma, be_r in product((5, 7, 10), (2.5, 3.0, 3.5), (0.35, 0.5, 0.0)):
        trades = model_trades_params(ou_config, ou_portfolio, uni, ohlc, max_hold, stop_sigma, be_r)
        name = f"hold={max_hold} sigma={stop_sigma} be={be_r}"
        for fam in ("funded", "ek"):
            res, _ = run_daily(trades, ohlc, family=fam, max_hold=max_hold, be_r=be_r if be_r else None,
                               exit_bps=EXIT_BPS, swap_bps_day=SWAP_BPS_DAY, **exec_kw)
            result[f"{fam} | {name}"] = split_stats(res, IS_END_DAILY)
        print(f"  {name}: funded IS {result['funded | ' + name]['IS'].get('avg_R')} OOS {result['funded | ' + name]['OOS'].get('avg_R')}", flush=True)
    return result


# ============================================================ Auswahl
def select(block: dict) -> list[dict]:
    """Rangfolge nur nach IS-Ø-R (mit Mindest-Tradezahl); OOS wird nur berichtet."""
    rows = [{"variant": k, **{f"IS_{m}": v["IS"].get(m) for m in ("n", "avg_R", "PF")},
             **{f"OOS_{m}": v["OOS"].get(m) for m in ("n", "avg_R", "PF", "ci95")}}
            for k, v in block.items() if v["IS"].get("n", 0) >= MIN_IS_TRADES]
    rows.sort(key=lambda r: r["IS_avg_R"], reverse=True)
    return rows


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {}
    curve = spread_curve()
    out["block0_spread_curve"] = curve
    print("Block 0 Spread-Kurve (Median bps):", {b: v["median_bps"] for b, v in curve.items()}, flush=True)

    if what == "block0":
        OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
        return
    ou_config, ou_portfolio, uni = rx.load_universe()
    ohlc = rx.download([t for v in uni.values() for t in v])
    trades = []
    for mk, tick in uni.items():
        trades += rx.model_trades(ou_config, ou_portfolio, mk, [t for t in tick if t in ohlc], ohlc)
    print(f"Modell-Trades: {len(trades)}", flush=True)

    if what in ("block1", "all"):
        out["regression"] = regression(trades, ohlc)
        print("Regression:", out["regression"], flush=True)
        out["block1"] = block1(trades, ohlc, curve)
        out["block1_ranking"] = select(out["block1"])
    if what in ("block2", "all"):
        out["block2"] = block2(trades, curve)
        out["block2_ranking"] = select(out["block2"])
    if what in ("block3", "all"):
        best = out.get("block1_ranking", [{}])[0].get("variant", "")
        if "close_d1" in best:
            exec_kw = dict(entry_mode="close_d1", gate=0.035, entry_cost_bps=entry_cost(curve, "15:45"))
        elif "close_d0" in best:
            exec_kw = dict(entry_mode="close_d0", gate=None, entry_cost_bps=entry_cost(curve, "15:45"))
        else:
            exec_kw = dict(entry_mode="open_d1", gate=0.035, entry_cost_bps=entry_cost(curve, "09:35"))
        out["block3_exec"] = best or "open_d1 gate3.5"
        out["block3"] = block3(ou_config, ou_portfolio, uni, ohlc, curve, exec_kw)
        out["block3_ranking"] = select(out["block3"])
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
    print("geschrieben:", OUT_JSON)


if __name__ == "__main__":
    main()
