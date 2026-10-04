"""ORB: mehrdeutige Fuell-Minuten mit Tickdaten aufloesen.

Auf M1 beruehrt bei ~22 % (SP500/US30) bzw. ~33 % (NASDAQ) der Trades schon die
Fuell-Minute den geplanten SL (Stop 0,6 ATR). engine.simulate() prueft den Stop
erst ab der Folgebar und nimmt damit stillschweigend an, der SL sei VOR der
Fuellung beruehrt worden. Ob das stimmt, entscheidet zwischen "Edge" und
"kein Edge" (knowledge/projects/orb-order-storno-und-haltedauer.md).

Hier: fuer jede mehrdeutige Fuell-Minute die Dukascopy-Ticks (Bid, wie die
M1-Bars) holen und die Reihenfolge feststellen:
  sl_before -- SL vor der Fuellung beruehrt (Storno-am-SL-Regel haette storniert)
  sl_after  -- SL nach der Fuellung beruehrt (= sofortiger Stop-out)
fuer jede Stop-Weite des Exit-Gitters. Ergebnis wird von
scripts/research_orb_exit_grid_m1.py eingelesen.

FALLE: dukascopy_python.fetch() liest naive datetimes als ORTSZEIT -- hier
immer tz-aware UTC uebergeben.
Ausgabe: ny_open_orb/results/fill_minute_ticks.csv
"""
import sys
import time
from pathlib import Path

import dukascopy_python as duka
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from combined_strategy.data import INSTRUMENTS, OFFER_SIDE  # noqa: E402
from research_orb_cancel_at_sl_montecarlo import load_m1  # noqa: E402
from research_orb_cancel_at_sl_and_hold import SPREAD_BPS, find_live_entries  # noqa: E402

STOPS = [0.5, 0.6, 0.8, 1.0]
OUT = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results" / "fill_minute_ticks.csv"


def ticks(instrument: str, minute_utc: pd.Timestamp) -> pd.Series:
    start = minute_utc.to_pydatetime()
    end = (minute_utc + pd.Timedelta(minutes=1)).to_pydatetime()
    for attempt in range(3):
        try:
            df = duka.fetch(INSTRUMENTS[instrument], duka.INTERVAL_TICK, OFFER_SIDE, start, end)
            return df["bidPrice"].sort_index()
        except Exception:
            time.sleep(2 * (attempt + 1))
    return pd.Series(dtype=float)


def main() -> int:
    done = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()
    have = set(zip(done.get("instrument", []), done.get("entry_time", [])))
    rows = []
    for instrument in ("SP500", "US30", "NASDAQ"):
        frame, allowed = load_m1(instrument)
        entries = find_live_entries(frame, allowed, 0.6, "none")   # Obermenge aller Regeln
        half_cost = SPREAD_BPS[instrument] / 10_000 / 2
        todo = []
        for _, e in entries.iterrows():
            bar = frame.loc[e["entry_time"]]
            d = e["direction"]
            sig = e["entry_price"] * (1 + half_cost * d)
            s_min = sig - d * min(STOPS) * e["atr"]
            touched = (bar["low"] <= s_min) if d == 1 else (bar["high"] >= s_min)
            if touched and (instrument, str(e["entry_time"])) not in have:
                todo.append((e, sig))
        print(f"{instrument}: {len(entries)} Entries, {len(todo)} mehrdeutige Fuell-Minuten (Stop {min(STOPS)})",
              flush=True)
        for k, (e, sig) in enumerate(todo):
            d, level = e["direction"], e["entry_price"]
            tk = ticks(instrument, pd.Timestamp(e["entry_time"]).tz_convert("UTC"))
            row = {"instrument": instrument, "entry_time": str(e["entry_time"]), "direction": d, "n_ticks": len(tk)}
            hit = tk[tk >= level] if d == 1 else tk[tk <= level]
            if tk.empty or hit.empty:
                row["resolved"] = False
            else:
                t_fill = hit.index[0]
                before, after = tk[tk.index < t_fill], tk[tk.index >= t_fill]
                row["resolved"] = True
                for m in STOPS:
                    s = sig - d * m * e["atr"]
                    row[f"sl_before_{m}"] = bool(((before <= s) if d == 1 else (before >= s)).any())
                    row[f"sl_after_{m}"] = bool(((after <= s) if d == 1 else (after >= s)).any())
            rows.append(row)
            if (k + 1) % 50 == 0:
                print(f"  {instrument} {k + 1}/{len(todo)}", flush=True)
                pd.concat([done, pd.DataFrame(rows)]).to_csv(OUT, index=False)
    out = pd.concat([done, pd.DataFrame(rows)])
    out.to_csv(OUT, index=False)
    r = out[out["resolved"] == True]  # noqa: E712
    print(f"\nAufgeloest {len(r)} von {len(out)}")
    for inst, g in r.groupby("instrument"):
        for m in STOPS:
            amb = g[g[f"sl_before_{m}"] | g[f"sl_after_{m}"]]
            if amb.empty:
                continue
            print(f"  {inst} Stop {m}: {len(amb)} mehrdeutig -> SL nach Fill (Stop-out) "
                  f"{amb[f'sl_after_{m}'].mean():.0%}, nur vorher {(amb[f'sl_before_{m}'] & ~amb[f'sl_after_{m}']).mean():.0%}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
