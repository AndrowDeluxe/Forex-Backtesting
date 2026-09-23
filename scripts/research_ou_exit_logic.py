"""OU-Modell: taugt die SL/TP-LOGIK? (Research, 2026-09-19)

Nutzerfrage nach der Kosten-/Zeitraum-Auswertung: "gehe tiefer in den Backtest
und pruefe mit den festgestellten Kosten eine andere SL/TP-Logik".

Abgrenzung zu den Vorlaeufern:
  research_ou_execution_costs.py        Kosten ueberhaupt (Varianten A-D)
  research_ou_execution_optimization.py EINSTIEG (Zeitpunkt, Ordertyp, Gate)
                                        + Parameter (max_hold/sigma/be)
  dieses Skript                         AUSSTIEG (welche Regel beendet den Trade)

Die Einstiegsliste bleibt fix (dieselben Modell-Trades wie in beiden
Vorlaeufern, Funded-Konfiguration) -- damit ist jede Differenz zwischen den
Varianten ausschliesslich die Ausstiegslogik. Gleiche Trennung wie am 16.09.
fuer die Ausfuehrung, nur eine Ebene weiter.

Geprueft (alle mit live gemessenen Kosten):
  bracket_be     SL 3sigma + TP 1,5R + Breakeven 0,35R + max_hold   = HEUTE LIVE
  bracket        dito ohne Breakeven                                 = Block-3-Sieger
  sl_only        SL + max_hold, kein TP, kein BE
  mean_revert    SL + Ausstieg beim Ruecklauf ans gleitende Mittel (MA20) --
                 die Regel des Original-Papers (portfolio.py::simulate_portfolio),
                 die der Bracket-Bot 2026 ersetzt hat. Kein festes Kursziel:
                 der Trade endet, wenn die Mean Reversion EINGETRETEN ist.
  mean_revert_tp Ruecklauf ans MA ODER TP 1,5R, was zuerst kommt
  trail_std      Trailing-Stop trail_mult * rollende Std, taeglich nachgezogen
  TP <r>R        TP-Sweep 0,75R ... 3,0R ohne BE
  no_sl          kein Stop, nur MA-Ausstieg + max_hold (Referenz: was kostet der
                 Stop an Edge? Live NICHT einsetzbar -- ein Funded-Konto braucht
                 einen Broker-Stop)

Kostenmodell je Broker: halber Spread am Einstieg + 3 bps Ausfuehrung,
5 bps Ausstieg, Swap je Kalendertag auf den Nominalwert (Block 0 vom 17.09.).
Ausfuehrungsfamilien: funded = nur Initial-SL beim Broker (alles andere auf
Tagesschluss ueber den Re-Scan), ek = BE/TP/Trailing broker-seitig (intraday).

Aufruf: python research_ou_exit_logic.py [--broker=ttp|tickmill|beide]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import research_ou_execution_costs as rx  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RES = REPO / "ou_paper_backtest" / "results"
OUT_JSON = RES / "exit_logic_20260919.json"
IS_END = pd.Timestamp("2023-01-01")
rng = np.random.default_rng(20260919)

# Kostensaetze je Broker. ttp = live gemessen (Block 0 / Deal-Historie 09-16):
# halber Eroeffnungsspread 27,9/2 + 3 bps Ausfuehrung. tickmill wird von
# research_ou_broker_costs.py gemessen und dort nachgetragen.
# Der H1-Spreadfeld-Median unterschaetzt den echten Spread systematisch (er wird
# am Kerzenschluss gestempelt): TTP H1 9,31 bps zur Eroeffnung gegen 27,9 bps aus
# den Ticks. Deshalb wird NICHT der H1-Wert eingesetzt, sondern das VERHAELTNIS
# der beiden Broker (Tickmill/TTP = 4,95/9,31 = 0,53) auf die tick-kalibrierten
# TTP-Zahlen angewendet. Slippage (3 bps Einstieg, 3 bps Stop-Ausstieg) ist live
# gemessen und brokerunabhaengig angesetzt.
_EK_SPREAD_RATIO = 4.95 / 9.31
COSTS = {
    "FK (TTP)": {"entry_bps": 16.9, "exit_bps": 5.0, "swap_bps_day": 1.71},
    "EK (Tickmill)": {"entry_bps": round(14.0 * _EK_SPREAD_RATIO + 3, 1),
                      "exit_bps": round(2.0 * _EK_SPREAD_RATIO + 3, 1), "swap_bps_day": 1.71},
    "kostenfrei": {"entry_bps": 0.0, "exit_bps": 0.0, "swap_bps_day": 0.0},
}


def stats(rs) -> dict:
    r = np.asarray(rs, dtype=float)
    if len(r) == 0:
        return {"n": 0}
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    boot = rng.choice(r, size=(2000, len(r)), replace=True).mean(axis=1)
    return {"n": int(len(r)), "avg_R": round(float(r.mean()), 4), "hit": round(float((r > 0).mean()), 3),
            "PF": round(float(w / l), 3) if l else None,
            "worst_R": round(float(r.min()), 2), "p05_R": round(float(np.quantile(r, 0.05)), 2),
            "sum_R": round(float(r.sum()), 1),
            "ci95": [round(float(np.quantile(boot, 0.025)), 4), round(float(np.quantile(boot, 0.975)), 4)]}


def replay_exit(tr, bars, ma, std, *, logic, family, cost, max_hold=10, be_r=0.35, rr=None,
                trail_mult=3.0, entry_mode="open_d1", gate=0.035, sl_scale=1.0):
    """Ein Trade, eine Ausstiegslogik. Einstieg wie heute live (Folgetags-Eroeffnung + Gate).

    R wird gegen die TATSAECHLICHE Stopdistanz (Fill -> Initial-SL) gemessen, weil die
    Bridges genau darauf sizen. Bei `no_sl` gibt es keinen Stop -- dort ist der Nenner
    die nominale 3sigma-Distanz, auf die die Bridge gesized haette.
    """
    c0, sd = tr["c0"], tr["stop_dist"]
    # sl_scale > 1 = breiterer Stop. Die Bridge sized auf die tatsaechliche Distanz,
    # ein breiterer Stop heisst also automatisch eine KLEINERE Position -- R bleibt
    # vergleichbar, und die Kosten in R sinken mit dem groesseren Nenner.
    sl0 = c0 - sl_scale * sd
    after = bars[bars.index > tr["d0"]]
    if after.empty:
        return None
    raw = after["Open"].iloc[0] if entry_mode == "open_d1" else after["Close"].iloc[0]
    if gate is not None and abs(raw - c0) / c0 > gate:
        return None
    has_sl = logic != "no_sl"
    if has_sl and raw <= sl0:
        return None

    entry = raw * (1 + cost["entry_bps"] / 1e4)
    risk = (entry - sl0) if has_sl else sd
    if risk <= 0:
        return None

    use_be = logic == "bracket_be"
    use_ma = logic in ("mean_revert", "mean_revert_tp", "no_sl")
    use_trail = logic == "trail_std"
    if logic in ("bracket_be", "bracket", "mean_revert_tp"):
        tp = c0 + tr["rr"] * sl_scale * sd if tr["rr"] else None
    elif rr is not None:
        tp = c0 + rr * sl_scale * sd
    else:
        tp = None

    broker = family == "ek"  # BE/TP/Trailing liegen beim Broker -> intraday gepruef
    sd_eff = sl_scale * sd
    be_level = c0 + be_r * sd_eff if use_be else None
    stop, be_moved = sl0, False
    exit_px = reason = None
    days = 0
    for i, (dt, b) in enumerate(after.iterrows()):
        days = i + 1
        active = stop if (broker and (use_be or use_trail)) else sl0
        if has_sl and b["Low"] <= active:
            exit_px = min(b["Open"], active)
            reason = "BE" if be_moved else ("Trail" if (use_trail and stop > sl0) else "SL")
            break
        if broker and tp is not None and b["High"] >= tp:
            exit_px, reason = max(b["Open"], tp), "TP"
            break
        close = b["Close"]
        if use_be and not be_moved and close >= be_level:
            be_moved, stop = True, c0
        if use_trail:
            s_t = std.get(dt, np.nan)
            if not np.isnan(s_t):
                stop = max(stop, close - trail_mult * s_t)
            if not broker and close <= stop and i > 0:
                exit_px, reason = close, ("Trail" if stop > sl0 else "SL")
                break
        if use_ma:
            m_t = ma.get(dt, np.nan)
            if not np.isnan(m_t) and close >= m_t:
                exit_px, reason = close, "MeanRevert"
                break
        if not broker and tp is not None and close >= tp:
            exit_px, reason = close, "TP"
            break
        if not broker and use_be and be_moved and close <= c0:
            exit_px, reason = close, "BE"
            break
        if days >= max_hold:
            exit_px, reason = close, "MaxHold"
            break
    if exit_px is None:
        return None
    exit_px *= 1 - cost["exit_bps"] / 1e4
    cal = max((after.index[days - 1] - after.index[0]).days + 1, 1)
    swap = raw * cost["swap_bps_day"] / 1e4 * cal
    return {"R": (exit_px - entry - swap) / risk, "reason": reason, "days": days, "cal": cal, "d0": tr["d0"]}


LOGICS = {
    "bracket_be (HEUTE LIVE)": dict(logic="bracket_be"),
    "bracket (BE aus)": dict(logic="bracket"),
    "sl_only (kein TP, kein BE)": dict(logic="sl_only"),
    "mean_revert (MA-Ausstieg)": dict(logic="mean_revert"),
    "mean_revert + TP 1,5R": dict(logic="mean_revert_tp"),
    "trail_std 3,0": dict(logic="trail_std", trail_mult=3.0),
    "trail_std 2,0": dict(logic="trail_std", trail_mult=2.0),
    "no_sl (nur MA + max_hold)": dict(logic="no_sl"),
}
for _r in (0.75, 1.0, 2.0, 3.0):
    LOGICS[f"TP {_r}R (BE aus)"] = dict(logic="sl_only", rr=_r)
# Stop-Weite: 1,0 = heutige 3 Sigma. Breiter = kleinere Position bei gleichem $-Risiko.
for _s in (1.0, 1.33, 1.67, 2.0, 2.67):
    LOGICS[f"SL {_s*3:.1f}sigma + MA-Ausstieg"] = dict(logic="mean_revert", sl_scale=_s)
    LOGICS[f"SL {_s*3:.1f}sigma + max_hold"] = dict(logic="sl_only", sl_scale=_s)


def main():
    which = "beide"
    for a in sys.argv[1:]:
        if a.startswith("--broker"):
            which = a.split("=")[-1]
    ou_config, ou_portfolio, uni = rx.load_universe()
    ohlc = rx.download([t for v in uni.values() for t in v])
    trades = []
    for mk, tick in uni.items():
        trades += rx.model_trades(ou_config, ou_portfolio, mk, [t for t in tick if t in ohlc], ohlc)
    print(f"Modell-Trades: {len(trades)}  (BB_LOOKBACK={ou_config.BB_LOOKBACK})", flush=True)

    ma, std = {}, {}
    for t, d in ohlc.items():
        ma[t] = d["Close"].rolling(ou_config.BB_LOOKBACK).mean()
        std[t] = d["Close"].rolling(ou_config.BB_LOOKBACK).std()

    out = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {}
    brokers = [b for b in COSTS if b != "kostenfrei"] if which == "beide" else [which]
    for broker in brokers + ["kostenfrei"]:
        cost = COSTS[broker]
        print(f"\n=== Kosten: {broker}  {cost} ===", flush=True)
        for name, kw in LOGICS.items():
            for fam in ("funded", "ek"):
                res = [r for r in (replay_exit(tr, ohlc[tr["ticker"]], ma[tr["ticker"]], std[tr["ticker"]],
                                               family=fam, cost=cost, **kw) for tr in trades) if r]
                if not res:
                    continue
                d = pd.DataFrame(res)
                d0 = pd.to_datetime(d["d0"])
                rec = {"IS": stats(d.loc[d0 < IS_END, "R"]), "OOS": stats(d.loc[d0 >= IS_END, "R"]),
                       "days_mean": round(float(d["days"].mean()), 2),
                       "cal_mean": round(float(d["cal"].mean()), 2),
                       "reasons": {k: int(v) for k, v in d["reason"].value_counts().items()}}
                out[f"{broker} | {fam} | {name}"] = rec
                if fam == "funded":
                    print(f"  {name:30s} IS {rec['IS']['avg_R']:+.4f} OOS {rec['OOS']['avg_R']:+.4f} "
                          f"PF {str(rec['OOS']['PF']):5}  Tage {rec['days_mean']:4.1f}  n {rec['OOS']['n']}", flush=True)
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
    print("\ngeschrieben:", OUT_JSON)


if __name__ == "__main__":
    main()
