"""ORB: Exit-Gitter (Stop/Ziel/Teilziel) auf M1 + Tick-Korrektur der Fuell-Minute.

Nutzerauftrag 2026-10-03 ("teste beide Punkte nochmal durch"):
  (1) NASDAQ-Storno am geplanten SL -- auf belastbarer Basis
  (2) Variante C (Teilziel 3R, Ziel 6R, Stop 0,6 ATR) wurde auf M5 gefunden,
      also mit dem Fuell-Bar-Fehler (knowledge/projects/orb-order-storno-und-
      haltedauer.md) -- haelt sie auf M1 mit aufgeloesten Fuell-Minuten?

WARUM EIN EIGENER SIMULATOR: engine.simulate() laeuft per iterrows; ein Gitter
auf M1 (bis 375 Bars je Trade) waere Stunden. `sim()` bildet simulate()
(entry_fill_mode="level", ohne Lag, ohne BE) exakt nach -- Stop vor Teilziel vor
Ziel innerhalb einer Bar, Teilziel-Bar ueberspringt die Zielpruefung, Kosten
identisch -- und wird zu Beginn Trade fuer Trade gegen simulate() abgeglichen.

TICK-KORREKTUR (scripts/research_orb_fill_minute_ticks.py): beruehrt die
Fuell-Minute den SL, sagen die Ticks, ob davor (Trade ok bzw. bei der
Storno-am-SL-Regel: gar kein Trade) oder danach (sofortiger Stop-out).
Nicht aufloesbare Minuten werden pessimistisch als Stop-out gewertet.
Ausgabe: ny_open_orb/results/exit_grid_m1.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb.engine import simulate  # noqa: E402
from research_orb_cancel_at_sl_and_hold import (  # noqa: E402
    ENTRY_SLIPPAGE_BPS, EXIT_CFG, EXIT_SLIPPAGE_BPS, IS_END, SPREAD_BPS, find_live_entries,
)
from research_orb_cancel_at_sl_montecarlo import load_m1  # noqa: E402

STOPS = [0.5, 0.6, 0.8, 1.0]
TARGETS = [None, 3.0, 4.0, 6.0, 8.0]
PARTIALS = [None, 2.0, 3.0]
FRACTION = 0.5
RULES = {"SP500": ("opposite", "sl"), "US30": ("opposite", "sl"), "NASDAQ": ("none", "sl")}
LIVE_RULE = {"SP500": "opposite", "US30": "opposite", "NASDAQ": "none"}   # Stand 03.10.
RES = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results"


def prepare(frame: pd.DataFrame, entries: pd.DataFrame) -> list[dict]:
    """Je Trade die Pfad-Arrays (Bars NACH der Fuell-Bar bis session_close)."""
    idx = frame.index
    hi, lo, cl = frame["high"].to_numpy(), frame["low"].to_numpy(), frame["close"].to_numpy()
    sc = frame["session_close"]
    out = []
    for _, e in entries.iterrows():
        if pd.isna(e["atr"]) or e["atr"] <= 0:
            continue
        i0 = idx.get_loc(e["entry_time"])
        i1 = idx.searchsorted(sc.iloc[i0], side="right")
        out.append({"t": e["entry_time"], "d": int(e["direction"]), "level": float(e["entry_price"]),
                    "atr": float(e["atr"]), "hi": hi[i0 + 1:i1], "lo": lo[i0 + 1:i1], "cl": cl[i0 + 1:i1]})
    return out


def _first(mask: np.ndarray, start: int = 0) -> int:
    nz = np.flatnonzero(mask[start:])
    return nz[0] + start if nz.size else 10**9


def sim(trades: list[dict], instrument: str, stop_m: float, target_r, partial_r) -> pd.DataFrame:
    half = SPREAD_BPS[instrument] / 10_000 / 2
    es, xs = ENTRY_SLIPPAGE_BPS / 10_000, EXIT_SLIPPAGE_BPS / 10_000
    rows = []
    for tr in trades:
        d, level = tr["d"], tr["level"]
        if tr["hi"].size == 0:
            continue
        entry = level * (1 + (half + es) * d)
        stop = level * (1 + half * d) - d * stop_m * tr["atr"]
        if (entry - stop) * d <= 0:
            continue
        risk = abs(entry - stop)
        fav = tr["hi"] if d == 1 else -tr["lo"]           # "Hoch in Handelsrichtung"
        adv = tr["lo"] if d == 1 else -tr["hi"]
        s_i = _first(adv <= stop * d)
        p_i = 10**9
        partial_r_contrib, remaining = 0.0, 1.0
        if partial_r is not None:
            pl = entry + d * partial_r * risk
            p_i = _first(fav >= pl * d)
            if p_i < s_i:
                pf = pl * (1 - (half + xs) * d)
                partial_r_contrib = FRACTION * d * (pf - entry) / risk
                remaining = 1 - FRACTION
            else:
                p_i = 10**9
        t_i = 10**9
        if target_r is not None:
            tp = entry + d * target_r * risk
            t_i = _first(fav >= tp * d, 0 if p_i == 10**9 else p_i + 1)
        if s_i <= t_i and s_i < 10**9:
            exit_raw, reason, k = stop, "stop", s_i
        elif t_i < 10**9:
            exit_raw, reason, k = tp, "target", t_i
        else:
            exit_raw, reason, k = tr["cl"][-1], "session_end", tr["cl"].size - 1
        xp = exit_raw * (1 - (half + xs) * d)
        r = partial_r_contrib + remaining * d * (xp - entry) / risk
        stop_r = d * (stop * (1 - (half + xs) * d) - entry) / risk   # Wert eines sofortigen Stop-outs
        rows.append({"entry_time": tr["t"], "r": r, "reason": reason, "stop_out_r": stop_r})
    return pd.DataFrame(rows)


def stats(r: pd.Series, et: pd.Series) -> dict:
    if r.empty:
        return {"n": 0}
    eq = r.cumsum().to_numpy()
    loss = -r[r < 0].sum()
    is_mask = (et <= pd.Timestamp(IS_END, tz=et.dt.tz)).to_numpy()
    yrs = r.groupby(et.dt.year.to_numpy()).sum()
    return {"n": len(r), "avg": r.mean(), "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "sum": r.sum(),
            "dd": (eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min(),
            "is": r[is_mask].mean(), "oos": r[~is_mask].mean(), "yrs_pos": int((yrs > 0).sum()), "yrs": len(yrs)}


def main() -> int:
    ticks = pd.read_csv(RES / "fill_minute_ticks.csv")
    ticks["key"] = ticks["instrument"] + "|" + ticks["entry_time"].astype(str)
    tk = ticks.set_index("key")
    out = []
    for instrument, rules in RULES.items():
        frame, allowed = load_m1(instrument)

        # --- Abgleich sim() vs. engine.simulate() auf der Live-Config ---------
        cfg = EXIT_CFG[instrument]
        ent = find_live_entries(frame, allowed, cfg["stop_atr_mult"], LIVE_RULE[instrument])
        ref = simulate(frame, ent, spread_bps=SPREAD_BPS[instrument], entry_slippage_bps=ENTRY_SLIPPAGE_BPS,
                       slippage_bps=EXIT_SLIPPAGE_BPS, entry_fill_mode="level", **cfg)
        mine = sim(prepare(frame, ent), instrument, cfg["stop_atr_mult"],
                   cfg["target_r_mult"] if cfg["target_mode"] == "r_multiple" else None, cfg["partial_exit_r"])
        diff = np.abs(ref["r_multiple"].to_numpy() - mine["r"].to_numpy()).max() if len(ref) == len(mine) else np.inf
        print(f"\n{instrument}: Abgleich sim() vs simulate(): {len(ref)} vs {len(mine)} Trades, max |ΔR| = {diff:.2e}",
              flush=True)
        if not diff < 1e-9:
            print("  ABBRUCH: Simulator weicht ab"); return 1

        for rule in rules:
            for stop_m in STOPS:
                ent = find_live_entries(frame, allowed, stop_m, rule)
                prep = prepare(frame, ent)
                # Tick-Status je Trade fuer DIESE Stop-Weite
                keys = [f"{instrument}|{t['t']}" for t in prep]
                before = np.array([bool(tk.at[k, f"sl_before_{stop_m}"]) if k in tk.index and tk.at[k, "resolved"] else False for k in keys])
                after = np.array([bool(tk.at[k, f"sl_after_{stop_m}"]) if k in tk.index and tk.at[k, "resolved"] else False for k in keys])
                unres = np.array([(k in tk.index and not tk.at[k, "resolved"]) for k in keys])
                for target_r in TARGETS:
                    for partial_r in PARTIALS:
                        if partial_r is not None and target_r is not None and partial_r >= target_r:
                            continue
                        res = sim(prep, instrument, stop_m, target_r, partial_r)
                        if res.empty:
                            continue
                        # sim() ueberspringt Trades nur bei leerem Pfad/negativem Risiko --
                        # Ausrichtung ueber entry_time
                        pos = pd.Index([t["t"] for t in prep]).get_indexer(res["entry_time"])
                        b, a, u = before[pos], after[pos], unres[pos]
                        r_tick = np.where(a | u, res["stop_out_r"], res["r"])
                        keep = ~(b & (rule == "sl"))            # SL vor Fill: diese Regel haette storniert
                        et = pd.to_datetime(res["entry_time"])
                        row = {"instrument": instrument, "rule": rule, "stop": stop_m, "target": target_r,
                               "partial": partial_r, "stop_out_fill_min": int((a | u).sum()), "unresolved": int(u.sum())}
                        row.update({f"m1_{k}": v for k, v in stats(res["r"], et).items()})
                        row.update({f"tick_{k}": v for k, v in stats(pd.Series(r_tick[keep]), et[keep].reset_index(drop=True)).items()})
                        out.append(row)
            print(f"  {rule}: fertig", flush=True)
    df = pd.DataFrame(out)
    df.to_csv(RES / "exit_grid_m1.csv", index=False)

    pd.set_option("display.width", 250)
    for instrument in RULES:
        g = df[df.instrument == instrument]
        cfg = EXIT_CFG[instrument]
        cur = g[(g.rule == LIVE_RULE[instrument]) & (g.stop == cfg["stop_atr_mult"])
                & ((g.target.isna()) if cfg["target_mode"] is None else (g.target == cfg["target_r_mult"]))
                & ((g.partial.isna()) if cfg["partial_exit_r"] is None else (g.partial == cfg["partial_exit_r"]))]
        print(f"\n{'=' * 110}\n{instrument} -- HEUTE (Variante C, Regel {LIVE_RULE[instrument]}):")
        cols = ["rule", "stop", "target", "partial", "tick_n", "tick_avg", "tick_is", "tick_oos", "tick_pf",
                "tick_sum", "tick_dd", "tick_yrs_pos", "m1_avg", "stop_out_fill_min"]
        print(cur[cols].to_string(index=False))
        robust = g[(g.tick_is > 0) & (g.tick_oos > 0)]
        print(f"IS und OOS positiv (tick-korrigiert): {len(robust)} von {len(g)}")
        print("Top 8 nach OOS Ø R (tick-korrigiert):")
        print(robust.sort_values("tick_oos", ascending=False).head(8)[cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
