"""Realkosten- und Ausfuehrungs-Probe fuer das NY-Open-ORB-Bein
(Nutzerauftrag 2026-09-13: "die Kostenprobe jetzt auf ORB ziehen").

Das ist Schritt 2-4 der Probe aus knowledge/areas/realkosten-und-ausfuehrungs-
probe.md, angewandt auf ORB statt auf cls_practical. Schritt 1 (echte Kosten je
Broker messen) laeuft ueber scripts/measure_broker_spreads.py und kommt separat.
Bis dahin: SWEEP ueber eine Bandbreite von Kostenannahmen, damit sofort ablesbar
ist, wo das Bein landet, sobald die Messwerte da sind.

AUSGANGSBEFUND (vor jedem Rechnen, aus dem Code selbst):
  ny_open_orb/engine.py::simulate() hat `spread_bps: float = 0.5` als Default --
  und challenge_portfolio/paper_bot.py::_scan_orb() uebergibt ihn NIE. Das Bein
  laeuft also live mit 0,5 bps Round-Trip, ohne Slippage und ohne Kommission.
  Exakt dasselbe Muster, das bei cls_practical einen Faktor 2 im Erwartungswert
  ausmachte (siehe knowledge/projects/cls-practical-kostenvalidierung.md).

  Der Stop haengt an `stop_atr_mult=0.6` x ATR(M15,14) der letzten Range-Bar --
  also an einem relativen Mass, genau der Bauart, die bei CLS in ruhigen Phasen
  mitschrumpfte und dort den gesamten Verlust verursachte.

METHODE, bewusst identisch zur CLS-Probe, damit die Ergebnisse vergleichbar sind:
  p6_3  Kosten-Sensitivitaet bis zum Breakeven, je Instrument und gepoolt
  p6_8  Stop-Abstaende gegen die Kosten stellen
  p6_6  Ausfuehrungs-Lag simulieren (Backtest fuellt am Ausbruchslevel, der
        Live-Bot schickt eine MARKTorder beim naechsten 5-Minuten-Scan)
  p6_7  Verteilung des erzeugten Hebels, nicht nur der Median

Selbstpruefung: build_orb_trades() bildet die Filterkette aus _scan_orb() nach.
main() vergleicht die Trade-Zahl gegen den echten Scan-Pfad -- weichen sie ab,
ist die Nachbildung falsch und keine Zahl darunter belastbar.

Aufruf:
    python scripts/research_orb_cost_probe.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import challenge_portfolio.paper_bot as pb
from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m5, fetch_m15
from ny_open_orb.engine import build_frame, find_entries, simulate

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)

START, END = "2019-01-01", "2026-09-13"
SPLIT = "2023-06-01"          # Out-of-Sample-Grenze; ORB-Historie ist kuerzer als die von CLS
INSTRUMENTS = ("SP500", "US30", "NASDAQ")
ENGINE_DEFAULT_BPS = 0.5      # der nie ueberschriebene Default
COST_SWEEP_BPS = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
LAGS = (0, 1, 2, 3)           # M5-Baren zwischen Signal und Ausfuehrung

# Risiko je ORB-Instrument im Live-Pfad: ORB_COMBINED_RISK_PCT (1 %) / 3,
# multipliziert mit CAPITAL_WEIGHT (1/6) -- siehe challenge_portfolio/paper_bot.py
LIVE_RISK_PCT = pb.CAPITAL_WEIGHT * pb.ORB_RISK_PCT_PER_INSTRUMENT
INITIAL_EQUITY = 100_000.0


def load_frame(instrument: str):
    # MIT Timeout: ein dukascopy_python-Request ohne eigenes Zeitlimit blockiert
    # unbegrenzt -- am 2026-09-13 real passiert, der Lauf hing 7,5 Stunden ohne
    # eine Zeile Fortschritt. challenge_portfolio/paper_bot.py::_retry() ist die
    # im Repo etablierte Loesung dafuer (Timeout je Versuch + Wiederholungen).
    m15 = pb._retry(lambda: fetch_m15(instrument, START, END),
                    attempts=3, delay_seconds=5.0, timeout_seconds=240.0)
    m5 = pb._retry(lambda: fetch_m5(instrument, START, END),
                   attempts=3, delay_seconds=5.0, timeout_seconds=240.0)
    if m15.empty or m5.empty:
        return None, None
    return build_frame(m15, m5, range_bars=1), m15


def select_entries(instrument: str, frame: pd.DataFrame, m15: pd.DataFrame) -> pd.DataFrame:
    """1:1 die Filterkette aus challenge_portfolio/paper_bot.py::_scan_orb().
    NASDAQ: alle Richtungen, Mittwoch ausgeschlossen. SP500/US30: nur Long,
    nur bei neutralem EMA-Ribbon-Bias."""
    all_entries = find_entries(frame, "stop_breakout")
    if all_entries.empty:
        return all_entries
    if instrument == "NASDAQ":
        return filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    return filters.filter_by_category(long_entries, bias_vals, (0.0,))


def build_orb_trades(instrument: str, frame: pd.DataFrame, entries: pd.DataFrame,
                     spread_bps: float, **overrides) -> pd.DataFrame:
    cfg = dict(pb.ORB_EXIT_CFG_BY_INSTRUMENT[instrument])
    cfg.update(overrides)
    t = simulate(frame, entries, spread_bps=spread_bps, **cfg)
    if t.empty:
        return t
    t = t.copy()
    t["market"] = instrument
    t["stop_pts"] = cfg["stop_atr_mult"] * t["atr_at_entry"]
    t["stop_bps"] = t["stop_pts"] / t["entry_price"] * 10_000
    return t


def metrics(t: pd.DataFrame, label: str) -> dict:
    if t.empty:
        return {"Variante": label, "Trades": 0}
    r = t["r_multiple"]
    ex = pb._utc_naive(t["exit_time"])
    wins = t[r > 0]
    gl = abs(r[r <= 0].sum())
    return {
        "Variante": label, "Trades": len(t),
        "Treffer%": 100 * len(wins) / len(t),
        "PF": (r[r > 0].sum() / gl) if gl > 0 else np.inf,
        "Ø R": r.mean(),
        "Ø R (IS)": r[(ex < SPLIT).to_numpy()].mean(),
        "Ø R (OOS)": r[(ex >= SPLIT).to_numpy()].mean(),
        "Summe R": r.sum(),
    }


def main() -> None:
    print(f"Lade ORB-Daten {START}..{END} ...")
    data = {}
    for inst in INSTRUMENTS:
        frame, m15 = load_frame(inst)
        if frame is None:
            print(f"  {inst}: KEINE DATEN -- uebersprungen")
            continue
        entries = select_entries(inst, frame, m15)
        data[inst] = (frame, entries)
        print(f"  {inst}: {len(frame):,} M5-Baren, {len(entries)} Entries nach Filterkette")

    # ---------------------------------------------------- Selbstpruefung
    print("\n" + "=" * 120)
    print("SELBSTPRUEFUNG -- Nachbildung gegen den echten Live-Scan-Pfad (_scan_orb)")
    print("=" * 120)
    live = pb._scan_orb(pd.Timestamp(END), force_refresh=False)
    for inst in data:
        mine = build_orb_trades(inst, *data[inst], ENGINE_DEFAULT_BPS)
        mine_recent = mine[pb._utc_naive(mine["entry_time"]) >= pb._utc_naive(live["entry_time"]).min()]
        theirs = live[live["market"] == inst]
        flag = "OK" if len(mine_recent) == len(theirs) else "ABWEICHUNG"
        print(f"  {inst:8}: Nachbildung {len(mine_recent):4d} | Live-Scan {len(theirs):4d}  -> {flag}")

    # ------------------------------------------- p6_3 Kosten-Sensitivitaet
    print("\n" + "=" * 150)
    print("p6_3 KOSTEN-SENSITIVITAET -- Ø R je Instrument und gepoolt, ueber Round-Trip-Kosten in bps")
    print("=" * 150)
    rows = []
    for bps in COST_SWEEP_BPS:
        pooled = []
        row = {"Kosten (bps)": bps}
        for inst in data:
            t = build_orb_trades(inst, *data[inst], bps)
            if t.empty:
                continue
            pooled.append(t)
            row[inst] = t["r_multiple"].mean()
        if pooled:
            allt = pd.concat(pooled, ignore_index=True)
            row["PORTFOLIO Ø R"] = allt["r_multiple"].mean()
            row["PF"] = (allt["r_multiple"][allt["r_multiple"] > 0].sum()
                         / abs(allt["r_multiple"][allt["r_multiple"] <= 0].sum()))
            row["Trades"] = len(allt)
        rows.append(row)
    sweep = pd.DataFrame(rows)
    print(sweep.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    be = _breakeven_bps(data)
    print(f"\n  BREAKEVEN des Portfolios (Ø R = 0) bei rund {be:.2f} bps Round-Trip.")
    print(f"  Engine-Default: {ENGINE_DEFAULT_BPS} bps -- Abstand zum Breakeven: {be - ENGINE_DEFAULT_BPS:.2f} bps.")

    # --------------------------------------------- p6_8 Stop-Abstaende
    print("\n" + "=" * 130)
    print("p6_8 STOP-ABSTAENDE (stop_atr_mult 0,6 x ATR(M15,14)) -- wie eng wird es im ruhigen Markt?")
    print("=" * 130)
    srows = []
    for inst in data:
        t = build_orb_trades(inst, *data[inst], ENGINE_DEFAULT_BPS)
        srows.append({
            "Instrument": inst, "Trades": len(t),
            "Kurs Ø": t["entry_price"].mean(),
            "Stop Median (Pkt)": t["stop_pts"].median(),
            "Stop p10 (Pkt)": t["stop_pts"].quantile(0.10),
            "Stop Median (bps)": t["stop_bps"].median(),
            "Stop p10 (bps)": t["stop_bps"].quantile(0.10),
            "Stop min (bps)": t["stop_bps"].min(),
        })
    print(pd.DataFrame(srows).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    print("\n  Anteil der Trades, deren Stop kleiner als ein Vielfaches der Kosten ist,")
    print("  und deren Ø R getrennt ausgewiesen (Muster der CLS-Probe, Befund 3):")
    for assumed in (2.0, 4.0):
        print(f"\n  --- angenommene Round-Trip-Kosten {assumed:.1f} bps ---")
        for inst in data:
            t = build_orb_trades(inst, *data[inst], assumed)
            for k in (2, 3):
                thr = k * assumed
                sub, rest = t[t["stop_bps"] < thr], t[t["stop_bps"] >= thr]
                if sub.empty:
                    continue
                print(f"    {inst:8} Stop < {k}x Kosten ({thr:4.1f} bps): {len(sub):3d} Trades "
                      f"({100*len(sub)/len(t):4.1f}%) | Ø R {sub['r_multiple'].mean():+.3f} "
                      f"| uebrige {rest['r_multiple'].mean():+.3f}")

    # ------------------------------------------- p6_6/p6_7 Ausfuehrungs-Lag
    print("\n" + "=" * 150)
    print("p6_6/p6_7 AUSFUEHRUNGS-LAG -- Backtest fuellt am Ausbruchslevel, der Live-Bot schickt")
    print("           eine Marktorder beim naechsten 5-Minuten-Scan. Sizing live: Risiko / |Live-Kurs - SL|")
    print("=" * 150)
    lrows = []
    for inst in data:
        frame, entries = data[inst]
        t = build_orb_trades(inst, frame, entries, 2.0)   # mittlere Kostenannahme
        if t.empty:
            continue
        lrows.extend(_lag_stats(inst, t, frame))
    print(pd.DataFrame(lrows).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    out = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results" / "cost_probe_sweep.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    sweep.to_csv(out, index=False)
    print(f"\nGespeichert: {out}")


def _lag_stats(inst: str, t: pd.DataFrame, frame: pd.DataFrame) -> list[dict]:
    """Effektiver Risiko-Abstand und erzeugter Hebel bei verzoegerter
    Marktorder. Der SL haengt am SIGNAL-Entry (entry_price - dir*stop_pts),
    der Live-Einstieg am Kurs `lag` Baren spaeter -- dieselbe Mechanik wie bei
    cls_practical, deshalb dieselben Kennzahlen."""
    close = frame["close"]
    pos = {ts: i for i, ts in enumerate(frame.index)}
    risk = INITIAL_EQUITY * LIVE_RISK_PCT
    out = []
    for lag in LAGS:
        eff, lev, behind = [], [], 0
        for _, r in t.iterrows():
            i = pos.get(r["entry_time"])
            if i is None or i + lag >= len(close):
                continue
            d = 1 if r["direction"] == 1 else -1
            sl = r["entry_price"] - d * r["stop_pts"]
            live_px = float(close.iloc[i + lag])
            rest = (live_px - sl) * d
            if rest <= 0:
                behind += 1
                continue
            eff.append(rest / r["stop_pts"])          # Anteil der Stopdistanz, der noch uebrig ist
            # Nominal = Risiko / Restabstand-in-Preis * Preis ; Hebel = Nominal / Equity
            lev.append((risk / rest) * live_px / INITIAL_EQUITY)
        if not eff:
            continue
        eff, lev = np.array(eff), np.array(lev)
        out.append({
            "Instrument": inst, "Lag (Min)": lag * 5, "n": len(eff),
            "schon hinter SL": behind,
            "Restabstand Median": eff.mean(),
            "verbraucht >0,5R %": 100 * (eff < 0.5).mean(),
            "Hebel Median": np.median(lev), "Hebel p90": np.percentile(lev, 90),
            "Hebel max": lev.max(),
        })
    return out


def _breakeven_bps(data: dict, lo: float = 0.0, hi: float = 20.0) -> float:
    """Bisektion auf die Round-Trip-Kosten, bei denen das gepoolte Ø R auf 0
    faellt -- Muster wie in der CLS-Probe."""
    def mean_r(bps: float) -> float:
        pooled = [build_orb_trades(i, *data[i], bps) for i in data]
        pooled = [p for p in pooled if not p.empty]
        if not pooled:
            return -np.inf
        return float(pd.concat(pooled)["r_multiple"].mean())

    if mean_r(lo) < 0:
        return lo
    if mean_r(hi) > 0:
        return hi
    for _ in range(12):
        mid = (lo + hi) / 2
        if mean_r(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.1:
            break
    return (lo + hi) / 2


if __name__ == "__main__":
    main()
