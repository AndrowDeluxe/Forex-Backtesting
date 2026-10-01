"""ORB: Pending-Order stornieren, sobald der Kurs den GEPLANTEN SL erreicht,
bevor die Order gefuellt ist -- und danach die optimale Haltedauer.

Nutzerauftrag 2026-10-01: "backteste das Loeschen der Orders sobald der Kurs
den geplanten SL der noch nicht gefillten Stop order erreicht [...] Backteste
dann bitte noch einmal die optimale Haltedauer von ORB."

WARUM EIN EIGENER ENTRY-FINDER: ny_open_orb/engine.py::_find_stop_breakout()
nimmt pro Tag den ERSTEN Ausbruch, egal in welche Richtung; SP500/US30 filtern
danach auf long. Bricht der Kurs zuerst nach UNTEN, gibt es im Backtest an dem
Tag keinen Trade. Live (Funded-Portfolio-Bridge/run_once.py::manage_orb_pending,
EK legs/ny_open_orb/executor.py) liegt bei SP500/US30 aber NUR die Long-Order,
ORDER_TIME_DAY bis 16:00 -- sie wird nach einem Bruch nach unten NICHT
storniert und fuellt, wenn der Kurs spaeter doch noch ueber orb_high steigt.
Live handelt also Trades, die der Backtest nie bewertet hat.

Storno-Regeln je ruhender Order (Richtung d, Level L, geplanter SL S):
  none      -- liegt bis Session-Ende (= heutiges Live-Verhalten)
  sl        -- storniert, sobald der Kurs S erreicht (Nutzervorschlag)
  opposite  -- storniert, sobald die Gegenseite der Range bricht
               (= Semantik des validierten Backtests)
NASDAQ ist beidseitig (OCO): die zuerst gefuellte Seite gewinnt, wie live.

Bar beruehrt in derselben M5-Bar Level UND Storno-Grenze: Reihenfolge unbekannt.
  opposite/OCO -> Bar ueberspringen (Konvention von _find_stop_breakout)
  sl           -> als Fuellung werten (konservativ: schmeichelt der Regel nicht)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb import filters, regime  # noqa: E402
from ny_open_orb.data import fetch_m1, fetch_m5, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame, find_entries, simulate  # noqa: E402

START, END = "2019-01-01", "2026-09-30"
IS_END = "2022-12-31"

# identisch zu scripts/research_orb_exit_grid.py (gemessene Broker-Spreads, Live-Fills)
SPREAD_BPS = {"SP500": 0.84, "US30": 0.48, "NASDAQ": 0.54}
ENTRY_SLIPPAGE_BPS = 0.45
EXIT_SLIPPAGE_BPS = 0.30

EXIT_CFG = pb.ORB_EXIT_CFG_BY_INSTRUMENT   # Live-Config (Variante C)
HOLDS_MIN = [30, 60, 90, 120, 150, 180, 240, 300, 360, None]   # None = bis 16:00

# --tf m1: Ausfuehrung auf M1 statt M5. Noetig, weil auf M5 bei ~70 % der Trades
# schon die FUELL-Bar den geplanten SL beruehrt -- ob der Kurs erst den SL und
# dann das Level erreichte (Storno) oder umgekehrt (Fill, dann Stop-out), ist
# auf M5 nicht entscheidbar. Range/ATR bleiben M15 wie in der Strategie.
TF = "m1" if "--tf" in sys.argv and sys.argv[sys.argv.index("--tf") + 1] == "m1" else "m5"


def load(instrument: str):
    m15 = pb._retry(lambda: fetch_m15(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=300)
    fetch_exec = fetch_m1 if TF == "m1" else fetch_m5
    m_exec = pb._retry(lambda: fetch_exec(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=900)
    frame = build_frame(m15, m_exec, range_bars=1)
    sessions = pd.DatetimeIndex(frame["session"].dropna().unique())
    if instrument == "NASDAQ":
        allowed = {s: ([] if s.day_name() == "Wednesday" else [1, -1]) for s in sessions}
    else:
        bias = regime.ema_trend_bias(m15, sessions)
        allowed = {s: ([1] if (not pd.isna(bias.get(s, np.nan)) and float(bias.get(s)) == 0.0) else [])
                   for s in sessions}
    return m15, frame, allowed


def find_live_entries(frame: pd.DataFrame, allowed: dict, stop_atr: float, rule: str) -> pd.DataFrame:
    rows = []
    tw = frame[frame.index >= frame["range_end"]]
    for session, day in tw.groupby("session"):
        dirs = allowed.get(pd.Timestamp(session), [])
        if not dirs or day.empty or pd.isna(day["orb_high"].iloc[0]):
            continue
        day = day[day.index < day["session_close"].iloc[0]]
        if day.empty:
            continue
        hi_lvl, lo_lvl, atr = day["orb_high"].iloc[0], day["orb_low"].iloc[0], day["atr"].iloc[0]
        if pd.isna(atr) or atr <= 0:
            continue
        level = {1: hi_lvl, -1: lo_lvl}
        sl = {d: level[d] - d * stop_atr * atr for d in dirs}
        pending = set(dirs)
        highs, lows, idx = day["high"].to_numpy(), day["low"].to_numpy(), day.index
        entry = None
        for k in range(len(day)):
            h, l = highs[k], lows[k]
            touch = {d: (h >= level[d]) if d == 1 else (l <= level[d]) for d in pending}
            if rule == "sl":
                cancel = {d: (l <= sl[d]) if d == 1 else (h >= sl[d]) for d in pending}
            elif rule == "opposite":
                cancel = {d: (l <= lo_lvl) if d == 1 else (h >= hi_lvl) for d in pending}
            else:
                cancel = {d: False for d in pending}
            filled = [d for d in pending if touch[d]]
            if len(filled) == 2:
                continue  # beide Seiten in einer Bar -- Konvention: ueberspringen
            if filled:
                d = filled[0]
                if cancel[d] and rule == "opposite":
                    continue  # Reihenfolge unbekannt -- Konvention: ueberspringen
                entry = (idx[k], d)
                break
            for d in [d for d in pending if cancel[d]]:
                pending.discard(d)
            if not pending:
                break
        if entry is None:
            continue
        t, d = entry
        rows.append({"entry_time": t, "session": session, "direction": d, "entry_price": level[d],
                     "orb_high": hi_lvl, "orb_low": lo_lvl, "orb_width": day["orb_width"].iloc[0], "atr": atr})
    cols = ["entry_time", "session", "direction", "entry_price", "orb_high", "orb_low", "orb_width", "atr"]
    out = pd.DataFrame(rows, columns=cols)
    out["entry_type"] = "stop_breakout"
    return out


def run(frame, entries, instrument, hold_min=None, cfg=None):
    cfg = cfg or EXIT_CFG[instrument]
    f = frame
    if hold_min is not None and not entries.empty:
        f = frame.copy()
        cut = entries.set_index("session")["entry_time"] + pd.Timedelta(minutes=hold_min)
        new_close = f["session"].map(cut)
        earlier = new_close.notna() & (new_close < f["session_close"])
        f["session_close"] = f["session_close"].where(~earlier, new_close)
    tr = simulate(f, entries, spread_bps=SPREAD_BPS[instrument], entry_slippage_bps=ENTRY_SLIPPAGE_BPS,
                  slippage_bps=EXIT_SLIPPAGE_BPS, entry_fill_mode="level", **cfg)
    return tr


def fill_bar_sl_touch(frame, entries, stop_atr):
    """Wie oft beruehrt schon die FUELL-Bar den SL? simulate() prueft den Stop erst
    ab der Folgebar -- in diesen Faellen ist die Reihenfolge unbekannt."""
    hit = set()
    for _, e in entries.iterrows():
        bar = frame.loc[e["entry_time"]]
        s = e["entry_price"] - e["direction"] * stop_atr * e["atr"]
        if (bar["low"] <= s) if e["direction"] == 1 else (bar["high"] >= s):
            hit.add(e["entry_time"])
    return hit


def stats(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return dict(n=0, avg=np.nan, pf=np.nan, sum=0.0, dd=0.0, is_avg=np.nan, oos_avg=np.nan, yrs="-")
    r = tr["r_multiple"]
    et = pd.to_datetime(tr["entry_time"])
    is_mask = (et <= pd.Timestamp(IS_END, tz=et.dt.tz)).values
    eq = r.cumsum()
    per_year = r.groupby(et.dt.year.values).sum()
    loss = -r[r < 0].sum()
    return dict(n=len(r), avg=r.mean(), pf=(r[r > 0].sum() / loss) if loss > 0 else np.inf, sum=r.sum(),
                dd=(eq - eq.cummax()).min(), is_avg=r[is_mask].mean(), oos_avg=r[~is_mask].mean(),
                yrs=f"{int((per_year > 0).sum())}/{len(per_year)}")


def fmt(label, s):
    return (f"  {label:<26} n {s['n']:>4} | Ø R {s['avg']:+.3f} | PF {s['pf']:.2f} | Σ R {s['sum']:+7.1f} | "
            f"MaxDD {s['dd']:6.1f}R | IS {s['is_avg']:+.3f} / OOS {s['oos_avg']:+.3f} | Jahre+ {s['yrs']}")


def boot_ci(x: np.ndarray, n_boot=5000, seed=7):
    if len(x) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    m = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def main() -> int:
    out_dir = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_cancel, rows_hold, all_trades = [], [], {}
    for instrument in ("SP500", "US30", "NASDAQ"):
        m15, frame, allowed = load(instrument)
        stop_atr = EXIT_CFG[instrument]["stop_atr_mult"]
        print(f"\n{'=' * 100}\n{instrument}  (Exit-Config live: {EXIT_CFG[instrument]})")

        # Plausibilitaet: 'opposite' muss den validierten Backtest reproduzieren
        ref = find_entries(frame, "stop_breakout")
        if instrument == "NASDAQ":
            ref = filters.filter_by_weekday(ref, exclude=["Wednesday"])
        else:
            le = filters.filter_by_direction(ref, 1)
            bias = regime.ema_trend_bias(m15, frame["session"].unique())
            ref = filters.filter_by_category(le, filters.values_at(le, bias), (0.0,))

        entries = {rule: find_live_entries(frame, allowed, stop_atr, rule) for rule in ("none", "sl", "opposite")}
        check_rule = "none" if instrument == "NASDAQ" else "opposite"
        same = set(ref["entry_time"]) == set(entries[check_rule]["entry_time"])
        print(f"  Abgleich Backtest-Entries vs. '{check_rule}': {len(ref)} vs {len(entries[check_rule])} "
              f"-> {'identisch' if same else 'ABWEICHEND'}")

        trades = {rule: run(frame, e, instrument) for rule, e in entries.items()}
        for rule, tr in trades.items():
            s = stats(tr)
            hit = fill_bar_sl_touch(frame, entries[rule], stop_atr)
            ft = len(hit)
            print(fmt(f"Storno={rule}", s) + f" | SL schon in Fuell-Bar: {ft}")
            # pessimistisch: Fuell-Bar beruehrt SL -> als Stop-out (-1R plus Kosten) werten
            pess = tr.copy()
            pess.loc[pess["entry_time"].isin(hit), "r_multiple"] = -1.05
            sp = stats(pess)
            print(fmt(f"  pessimistisch", sp))
            rows_cancel.append({"instrument": instrument, "rule": rule, "fill_bar_sl_touch": ft, **s,
                                **{f"pess_{k}": v for k, v in sp.items()}})
            tr = tr.assign(instrument=instrument, rule=rule)
            all_trades[(instrument, rule)] = tr

        # Welche Trades entfernt die SL-Regel gegenueber heute (none)?
        base, alt = trades["none"], trades["sl"]
        removed = base[~base["entry_time"].isin(alt["entry_time"])]
        late = base[~base["entry_time"].isin(trades["opposite"]["entry_time"])]
        for label, sub in (("von SL-Storno entfernt", removed), ("von Gegenseiten-Storno entfernt", late)):
            if sub.empty:
                print(f"  {label}: 0 Trades")
                continue
            lo, hi = boot_ci(sub["r_multiple"].to_numpy())
            print(f"  {label}: {len(sub)} Trades, Ø R {sub['r_multiple'].mean():+.3f} "
                  f"(95%-KI {lo:+.3f}..{hi:+.3f}), Σ R {sub['r_multiple'].sum():+.1f}, "
                  f"Trefferquote {(sub['r_multiple'] > 0).mean():.0%}")

        # Breiten-Check: SL innerhalb der Range? (nur dann kann 'sl' vor 'opposite' greifen)
        w = entries["none"]
        inside = (w["orb_width"] > stop_atr * w["atr"]).mean() if not w.empty else np.nan
        print(f"  Anteil Tage mit Range breiter als {stop_atr} ATR (SL liegt IN der Range): {inside:.0%}")

        # Haltedauer, je Storno-Regel
        print(f"\n  Haltedauer ab Fuellung (Ausstieg zum Schluss der Bar, die bei Fuellung+N oeffnet):")
        for rule in ("none", "sl", "opposite"):
            for hold in HOLDS_MIN:
                tr = run(frame, entries[rule], instrument, hold_min=hold)
                s = stats(tr)
                rows_hold.append({"instrument": instrument, "rule": rule, "hold_min": hold or "16:00", **s})
                print(fmt(f"{rule:<8} hold {str(hold or '16:00'):>5}", s))

    pd.DataFrame(rows_cancel).to_csv(out_dir / f"cancel_at_sl_{TF}.csv", index=False)
    pd.DataFrame(rows_hold).to_csv(out_dir / f"hold_duration_{TF}.csv", index=False)
    pd.concat(all_trades.values()).to_csv(out_dir / f"cancel_at_sl_trades_{TF}.csv", index=False)
    print(f"\nCSV -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
