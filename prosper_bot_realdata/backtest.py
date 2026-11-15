"""Prosper-AI-"Grok Trading Team"-Bot: Trendregel 1:1 auf echten Kursen.

Lock `prosper_bot_realdata` (Split 2017-09-01 / 2022-12-31 / 2026-02-28, Tresor bis
2026-08-31, 6 Varianten = 3 Zeitrahmen x 2 Stops). Plan:
C:/Users/andre/.claude/plans/functional-skipping-codd.md

Nachgebaut aus C:/Users/andre/prosper-ai-grok-trading-team (unveraendert):
  Score  (agents/market_analyst.py): mom20 / max(4*vola20, 0.5), bei SMA5<SMA20 auf <=0
         gekappt, auf +-1 begrenzt.
  Signal (agents/strategy_agent.py): BUY bei Score >= 0.45 (nur long), SELL bei
         offener Position und Score <= -0.45.
  Risiko (agents/risk_manager.py): Stop -5 % / Ziel +10 % auf dem Schlusskurs geprueft;
         Konto: 5 Positionen, 15 %/Position, 30 % Krypto, Score < 0.55 = NEEDS REVIEW
         (uebersprungen), -3 % Tag = Pause, -10 % vom Hoch = Dauersperre.
Abweichung: Fuellung zum Open der naechsten Kerze (kein Vorgriff).
Variante "atr": Stop 2xATR14, Ziel 2x Stopweite (Annahme, Dashboard-Bestaetigung).

Der Tresor wird NICHT angefasst: alle Daten werden vor 2026-03-01 abgeschnitten.

Aufruf:  python -m prosper_bot_realdata.backtest
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from research_lock import Lock, deflated_sharpe
from prosper_bot_realdata.data import CRYPTOS, MARKETS, TIMEFRAMES, kind, load

LOCK = Lock("prosper_bot_realdata")
OUT = Path(__file__).resolve().parent / "results"
CUTOFF = pd.Timestamp("2026-03-01", tz="UTC")  # Tresor-Beginn, nichts danach laden
START = pd.Timestamp("2017-09-01", tz="UTC")
WARMUP = pd.Timedelta(days=40)

BUY, SELL = 0.45, -0.45
REVIEW_BELOW = 0.55
SL_PCT, TP_PCT = 0.05, 0.10
ATR_N, ATR_STOP, ATR_TARGET_R = 14, 2.0, 2.0
GAP_LIMIT = pd.Timedelta(days=4)
BOT_FEE_RT = 0.002  # Prosper: 0,1 % je Seite

# Round-Trip bps, aus fusion_lab/macro_reports/backtest.py::COST_BPS
COST_BPS = {"fx": 1.5, "index": 2.0, "metal": 3.0, "crypto": 10.0}
VARIANTS = ["fix", "atr"]
N_RANDOM = 200
SEED = 20261112


# ------------------------------------------------------------------ Score

def score(close: pd.Series) -> pd.Series:
    sma5 = close.rolling(5).mean()
    sma20 = close.rolling(20).mean()
    mom = (close / close.shift(19) - 1) * 100
    vol = (close.pct_change() * 100).rolling(20).std(ddof=0)
    raw = mom / np.maximum(vol * 4, 0.5)
    raw = raw.where(~(sma5 < sma20), np.minimum(raw, 0))
    return raw.clip(-1, 1).round(3)


def atr(d: pd.DataFrame, n: int = ATR_N) -> pd.Series:
    pc = d["Close"].shift(1)
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - pc).abs(), (d["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def prepare(market: str, tf: str) -> pd.DataFrame:
    d = load(market, tf)
    if not len(d):
        return d
    d = d[(d.index >= START - WARMUP) & (d.index < CUTOFF)].copy()
    if len(d) < 50:
        return d.iloc[0:0]
    d["score"] = score(d["Close"])
    d["atr"] = atr(d)
    return d


# ------------------------------------------------------------- Ebene A

def simulate_signals(d: pd.DataFrame, variant: str) -> list[dict]:
    """Ein Markt, eine Position zur Zeit; Fuellung naechstes Open."""
    o, c = d["Open"].to_numpy(), d["Close"].to_numpy()
    sc, at = d["score"].to_numpy(), d["atr"].to_numpy()
    ts = d.index
    trades, pos = [], None
    for i in range(len(d) - 1):
        if pos is not None:
            if variant == "fix":
                chg = c[i] / pos["entry"] - 1
                reason = "SL" if chg <= -SL_PCT else "TP" if chg >= TP_PCT else None
            else:
                reason = "SL" if c[i] <= pos["stop"] else "TP" if c[i] >= pos["target"] else None
            if reason is None and sc[i] <= SELL:
                reason = "SIG"
            if reason:
                pos.update(exit=o[i + 1], exit_time=ts[i + 1], reason=reason, bars=i + 1 - pos["i"],
                           max_gap=(ts[pos["i"]:i + 2].to_series().diff().max()))
                trades.append(pos)
                pos = None
            continue
        if ts[i] < START or not (sc[i] >= BUY):
            continue
        entry = o[i + 1]
        if variant == "fix":
            stop_frac = SL_PCT
            stop, target = entry * (1 - SL_PCT), entry * (1 + TP_PCT)
        else:
            if not np.isfinite(at[i]) or at[i] <= 0:
                continue
            dist = ATR_STOP * at[i]
            stop_frac = dist / entry
            stop, target = entry - dist, entry + ATR_TARGET_R * dist
        pos = {"entry_time": ts[i + 1], "entry": entry, "i": i + 1, "score": sc[i],
               "stop_frac": stop_frac, "stop": stop, "target": target}
    return trades


def trade_frame(trades: list[dict], market: str, tf: str, variant: str) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    t = pd.DataFrame(trades)
    t["market"], t["tf"], t["variant"] = market, tf, variant
    t["gap"] = t["max_gap"] > GAP_LIMIT
    t["ret_gross"] = t["exit"] / t["entry"] - 1
    cost = COST_BPS[kind(market)] / 1e4
    t["ret_net"] = t["ret_gross"] - cost
    t["ret_botfee"] = t["ret_gross"] - BOT_FEE_RT
    for k in ("gross", "net", "botfee"):
        t[f"R_{k}"] = t[f"ret_{k}"] / t["stop_frac"]
    t = t.drop(columns=["i", "max_gap"]).set_index("entry_time")
    return t


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    n = len(r)
    if n < 2:
        return {"n": n}
    m, s = r.mean(), r.std(ddof=1)
    gains, losses = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": n, "mean_R": round(m, 4), "t": round(m / s * math.sqrt(n), 2) if s > 0 else np.nan,
            "PF": round(gains / losses, 2) if losses > 0 else np.inf, "win": round((r > 0).mean(), 3),
            "sum_R": round(r.sum(), 1), "sr": m / s if s > 0 else 0.0}


def random_control(d: pd.DataFrame, t: pd.DataFrame, rng: np.random.Generator, cost: float) -> np.ndarray:
    """Zufallseinstiege (long) mit gleicher Anzahl und gleicher Haltedauer-Verteilung."""
    if len(t) < 2:
        return np.array([])
    o = d["Open"].to_numpy()
    lo, hi = d.index.searchsorted(t.index.min()), d.index.searchsorted(t.index.max())
    bars, sf = t["bars"].to_numpy(), t["stop_frac"].to_numpy()
    means = np.empty(N_RANDOM)
    for k in range(N_RANDOM):
        h = rng.choice(bars, size=len(t))
        e = rng.integers(lo, max(lo + 1, hi), size=len(t))
        x = np.minimum(e + h, len(o) - 1)
        r = (o[x] / o[e] - 1 - cost) / rng.choice(sf, size=len(t))
        means[k] = r.mean()
    return means


def run_signal_level() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    all_trades, rows = [], []
    for tf in TIMEFRAMES:
        for m in MARKETS:
            d = prepare(m, tf)
            if not len(d):
                rows.append({"tf": tf, "market": m, "variant": "-", "note": "keine Daten"})
                continue
            for v in VARIANTS:
                t = trade_frame(simulate_signals(d, v), m, tf, v)
                if not len(t):
                    continue
                n_gap = int(t["gap"].sum())
                t = t[~t["gap"]]
                all_trades.append(t)
                cost = COST_BPS[kind(m)] / 1e4
                for per, sl in (("IS", LOCK.is_only(t)), ("OOS", LOCK.oos_only(t))):
                    if not len(sl):
                        continue
                    dsl = LOCK.is_only(d) if per == "IS" else LOCK.oos_only(d)
                    ctrl = random_control(d, sl, rng, cost)
                    st = stats(sl["R_net"])
                    rows.append({"tf": tf, "market": m, "variant": v, "period": per, **st,
                                 "mean_R_gross": round(sl["R_gross"].mean(), 4),
                                 "mean_R_botfee": round(sl["R_botfee"].mean(), 4),
                                 "mean_ret_net_%": round(sl["ret_net"].mean() * 100, 3),
                                 "avg_bars": round(sl["bars"].mean(), 1),
                                 "rand_mean_R": round(float(ctrl.mean()), 4) if len(ctrl) else np.nan,
                                 "pctl_vs_rand": round(float((ctrl < st.get("mean_R", np.nan)).mean()), 3) if len(ctrl) else np.nan,
                                 "buyhold_%": round((dsl["Close"].iloc[-1] / dsl["Close"].iloc[0] - 1) * 100, 1) if len(dsl) else np.nan,
                                 "gap_trades_dropped": n_gap})
    trades = pd.concat(all_trades)
    return trades, pd.DataFrame(rows)


def pooled(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (tf, v), g in trades.groupby(["tf", "variant"]):
        for per, sl in (("IS", LOCK.is_only(g)), ("OOS", LOCK.oos_only(g))):
            st = stats(sl["R_net"])
            dsr = deflated_sharpe(st["sr"], st["n"], LOCK.trials) if st.get("n", 0) >= 2 else np.nan
            yearly = sl.groupby(sl.index.year)["R_net"].mean().round(3).to_dict()
            rows.append({"tf": tf, "variant": v, "period": per, **{k: st[k] for k in st if k != "sr"},
                         "mean_R_gross": round(sl["R_gross"].mean(), 4),
                         "mean_R_botfee": round(sl["R_botfee"].mean(), 4),
                         "DSR": round(dsr, 3), "pos_markets": int((sl.groupby("market")["R_net"].mean() > 0).sum()),
                         "n_markets": sl["market"].nunique(), "yearly_mean_R": json.dumps(yearly)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------- Ebene B

def run_account(tf: str, variant: str, permanent_halt: bool = True, start_cash: float = 100_000.0) -> dict:
    """Ein gemeinsames Bot-Konto ueber alle Maerkte, Regeln wie risk_manager.review()."""
    data = {m: prepare(m, tf) for m in MARKETS}
    data = {m: d[d.index >= START - WARMUP] for m, d in data.items() if len(d)}
    idx = sorted(set().union(*[set(d.index) for d in data.values()]))
    idx = pd.DatetimeIndex(idx)
    arr = {}
    for m, d in data.items():
        r = d.reindex(idx)
        arr[m] = {"has": r["Close"].notna().to_numpy(), "o": r["Open"].to_numpy(), "c": r["Close"].to_numpy(),
                  "sc": r["score"].to_numpy(), "atr": r["atr"].to_numpy()}
    mkts = list(arr)
    last = {m: np.nan for m in mkts}
    cash, positions, pending = start_cash, {}, {}
    peak = day_start = start_cash
    cur_day, halted_at, n_trades, n_review_skipped, n_rejected = None, None, 0, 0, 0
    curve = []
    fee = {m: COST_BPS[kind(m)] / 2 / 1e4 for m in mkts}

    def equity():
        return cash + sum(p["qty"] * (last[m] if np.isfinite(last[m]) else p["entry"]) for m, p in positions.items())

    for k, t in enumerate(idx):
        # 1) offene Auftraege zum Open fuellen
        for m in list(pending):
            a = arr[m]
            if not a["has"][k]:
                continue
            act, px = pending.pop(m), a["o"][k]
            if act["side"] == "SELL" and m in positions:
                p = positions.pop(m)
                cash += p["qty"] * px * (1 - fee[m])
                n_trades += 1
            elif act["side"] == "BUY" and m not in positions:
                qty = act["budget"] / px
                cash -= qty * px * (1 + fee[m])
                dist = SL_PCT * px if variant == "fix" else ATR_STOP * act["atr"]
                positions[m] = {"qty": qty, "entry": px, "stop": px - dist,
                                "target": px * (1 + TP_PCT) if variant == "fix" else px + ATR_TARGET_R * dist}
        for m in mkts:
            if arr[m]["has"][k]:
                last[m] = arr[m]["c"][k]
        eq = equity()
        day = t.date()
        if day != cur_day:
            cur_day, day_start = day, eq
        peak = max(peak, eq)
        if t < START:
            continue
        curve.append((t, eq))
        # 2) Ausstiege (check_exits + SELL-Signal)
        for m, p in positions.items():
            a = arr[m]
            if not a["has"][k] or m in pending:
                continue
            c = a["c"][k]
            if variant == "fix":
                chg = c / p["entry"] - 1
                hit = chg <= -SL_PCT or chg >= TP_PCT
            else:
                hit = c <= p["stop"] or c >= p["target"]
            if hit or a["sc"][k] <= SELL:
                pending[m] = {"side": "SELL"}
        # 3) Kaufvorschlaege -> Risk Manager
        props = [(arr[m]["sc"][k], m) for m in mkts
                 if arr[m]["has"][k] and m not in positions and m not in pending and arr[m]["sc"][k] >= BUY]
        if not props:
            continue
        props.sort(reverse=True)
        props = props[:4]
        dd = 1 - eq / peak if peak else 0
        if permanent_halt and dd >= 0.10 and halted_at is None:
            halted_at = t
        halt = (eq / day_start - 1 <= -0.03) or (permanent_halt and halted_at is not None) or \
               (not permanent_halt and dd >= 0.10)
        if halt:
            n_rejected += len(props)
            continue
        slots = 5 - len(positions) - sum(1 for a in pending.values() if a["side"] == "BUY")
        free_cash = cash - sum(a["budget"] for a in pending.values() if a["side"] == "BUY")
        crypto_exp = sum(p["qty"] * p["entry"] for m, p in positions.items() if m in CRYPTOS)
        for s, m in props:
            if slots <= 0:
                n_rejected += 1
                continue
            budget = min(eq * 0.15, free_cash * 0.95)
            if m in CRYPTOS:
                budget = min(budget, eq * 0.30 - crypto_exp)
            if budget < 50:
                n_rejected += 1
                continue
            if round(abs(s), 2) < REVIEW_BELOW:
                n_review_skipped += 1
                continue
            pending[m] = {"side": "BUY", "budget": budget, "atr": arr[m]["atr"][k]}
            free_cash -= budget
            slots -= 1
            if m in CRYPTOS:
                crypto_exp += budget

    c = pd.Series(dict(curve))
    daily = c.groupby(c.index.date).last()
    dd = (1 - daily / daily.cummax()).max()
    out = {"tf": tf, "variant": variant, "permanent_halt": permanent_halt,
           "end_equity": round(c.iloc[-1], 0), "return_%": round((c.iloc[-1] / start_cash - 1) * 100, 2),
           "max_dd_%": round(dd * 100, 2), "closed_trades": n_trades,
           "halted_at": str(halted_at.date()) if halted_at is not None else None,
           "skipped_needs_review": n_review_skipped, "rejected": n_rejected}
    for per, sl in (("IS", LOCK.is_only(daily.set_axis(pd.to_datetime(daily.index)))),
                    ("OOS", LOCK.oos_only(daily.set_axis(pd.to_datetime(daily.index))))):
        if len(sl) > 1:
            out[f"return_{per}_%"] = round((sl.iloc[-1] / sl.iloc[0] - 1) * 100, 2)
    daily.to_csv(OUT / f"account_curve_{tf}_{variant}_{'halt' if permanent_halt else 'nohalt'}.csv")
    return out


# ---------------------------------------------------------------- main

def main():
    OUT.mkdir(exist_ok=True)
    trades, per_market = run_signal_level()
    trades.to_csv(OUT / "trades.csv")
    per_market.to_csv(OUT / "per_market.csv", index=False)
    pool = pooled(trades)
    pool.to_csv(OUT / "pooled.csv", index=False)
    accounts = pd.DataFrame([run_account(tf, v, ph) for tf in TIMEFRAMES for v in VARIANTS for ph in (True, False)])
    accounts.to_csv(OUT / "account.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print("=== Gepoolt (R netto) ===")
    print(pool.drop(columns=["yearly_mean_R"]).to_string(index=False))
    print("\n=== Jahre (Ø R netto) ===")
    print(pool[["tf", "variant", "period", "yearly_mean_R"]].to_string(index=False))
    print("\n=== Bot-Konto 1:1 ===")
    print(accounts.to_string(index=False))


if __name__ == "__main__":
    main()
