"""OU-Modell: die SIGNALSEITE auf Basis der Logik D durchtesten (Research, 2026-09-23).

Nutzerauftrag: "wir halten erstmal die optimale Logik unter D fest. Teste auf
Basis dieser Logik einmal die Signalseite durch."

Logik D ist damit FIX und wird nicht mehr variiert:
    stop_sigma 8,0 · be_trigger_r 0 · kein TP · Ausstieg am gleitenden Mittel ·
    max_hold 10 · Einstieg Folgetags-Eroeffnung, Gate 3,5 % · Kosten je Broker

Variiert wird ausschliesslich, WELCHE Signale ueberhaupt entstehen:
  A  BB_LOOKBACK   Fenster von Band UND Ausstiegs-Mittel (10/15/20/30/40)
  B  BB_K          wie weit unter dem Mittel gekauft wird (1,5/2,0/2,5/3,0)
  C  Regimefilter  heute: Benchmark ueber EMA200. Auch: aus, EMA100,
                   EMA200 + steigend
  D  OU-Auswahl    die Schwellen aus ou_parameters_in_sample.csv
  E  Universum     sp500 / nasdaq100 / beide

Warum Block D besonders interessant ist: im sp500-Universum hat KEIN Titel
theta unter 0,036, die Schwelle THETA_MIN = 0,03 filtert also nichts. Und
p_value laeuft von 0,117 bis 0,297 -- die Schwelle 0,2 waehlt das beste
Viertel einer Verteilung, die nie statistische Signifikanz erreicht. Ob diese
Vorauswahl ueberhaupt etwas beitraegt, wurde nie geprueft.

Schutz gegen Ueberanpassung wie in den Vorlaeufern: Rangfolge NUR auf
In-Sample (Signal < 2023), Out-of-Sample nur berichtet, dazu der Jahresaufriss
-- eine Variante, die ihren OOS-Schnitt aus einem einzigen Jahr zieht, ist
keine Verbesserung (Lehre aus Phase 6: die empfohlene Konfiguration ist
2023/2024 negativ und nur 2025/2026 positiv).

Aufruf: python research_ou_signal_side.py [block A|B|C|D|E|alle]
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
import research_ou_exit_logic as ex  # noqa: E402
import challenge_portfolio.paper_bot as pb  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT_JSON = REPO / "ou_paper_backtest" / "results" / "signal_side_20260923.json"
IS_END = pd.Timestamp("2023-01-01")
SIGMA_D = 8.0          # Logik D
MAX_HOLD_D = 10
MIN_IS_TRADES = 150

_CACHE = {}


def universe(ou_config, pvalue_max=None, theta_min=None, hl=None, markets=None, tradable_only=True):
    """Titelauswahl aus ou_parameters_in_sample.csv, Schwellen ueberschreibbar."""
    _, _, tradable_fn = pb._import_ou_paper_backtest()
    pvalue_max = ou_config.PVALUE_MAX if pvalue_max is None else pvalue_max
    theta_min = ou_config.THETA_MIN if theta_min is None else theta_min
    hl = (ou_config.HALFLIFE_MIN, ou_config.HALFLIFE_MAX) if hl is None else hl
    markets = markets or list(pb.OU_MODELL_MARKETS)
    uni = {}
    for mk in markets:
        tab = pd.read_csv(ou_config.RESULTS_DIR / mk / "ou_parameters_in_sample.csv", index_col=0)
        sel = tab[(tab["theta"] > theta_min) & (tab["p_value"] < pvalue_max)
                  & tab["half_life"].between(*hl)]
        tick = sel.index.tolist()
        if tradable_only:
            tr = tradable_fn(mk)
            if tr is not None:
                tick = [t for t in tick if t in tr]
        uni[mk] = tick
    return uni


def benchmark(ou_config, mk, index):
    key = ("bench", mk)
    if key not in _CACHE:
        b = rx.yf.download(ou_config.UNIVERSES[mk]["benchmark"], start=rx.DL_START, end="2026-09-17",
                           auto_adjust=True, progress=False)["Close"]
        if isinstance(b, pd.DataFrame):
            b = b.iloc[:, 0]
        _CACHE[key] = b
    return _CACHE[key]


def regime_series(ou_config, mk, panel_index, mode):
    """True = Einstiege an diesem Tag erlaubt (marktweit)."""
    if mode == "aus":
        return None
    b = benchmark(ou_config, mk, panel_index)
    if mode == "ema200":
        r = b > b.ewm(span=200).mean()
    elif mode == "ema100":
        r = b > b.ewm(span=100).mean()
    elif mode == "ema200_steigend":
        e = b.ewm(span=200).mean()
        r = (b > e) & (e > e.shift(20))
    else:
        raise ValueError(mode)
    return r.reindex(panel_index).ffill().fillna(False)


def build_trades(ou_config, ou_portfolio, uni, ohlc, lookback, k, regime_mode):
    trades = []
    for mk, tick in uni.items():
        tick = [t for t in tick if t in ohlc]
        if len(tick) < 2:
            continue
        panel = pd.DataFrame({t: ohlc[t]["Close"] for t in tick}).sort_index()
        regime = regime_series(ou_config, mk, panel.index, regime_mode)
        _, tl = ou_portfolio.simulate_bracket_portfolio(
            panel, list(panel.columns), rx.START, rx.END, lookback=lookback, k=k,
            stop_sigma=SIGMA_D, rr_ratio=None, be_trigger_r=0.0, allowed_directions=(1,),
            regime_filter=regime, max_hold=MAX_HOLD_D,
            risk_pct=pb.OU_MODELL_RISK_PCT, max_total_risk_pct=pb.OU_MODELL_MAX_TOTAL_RISK_PCT)
        std = panel.rolling(lookback).std()
        for t in tl:
            sd = std.loc[t["entry_date"], t["ticker"]] * SIGMA_D
            if not np.isfinite(sd) or sd <= 0:
                continue
            trades.append({"market": mk, "ticker": t["ticker"], "d0": t["entry_date"],
                           "c0": t["entry_price"], "stop_dist": sd, "rr": None})
    return trades


def evaluate(trades, ohlc, lookback, label, out, broker="FK (TTP)"):
    ma = {t: d["Close"].rolling(lookback).mean() for t, d in ohlc.items()}
    std = {t: d["Close"].rolling(lookback).std() for t, d in ohlc.items()}
    fam = "funded" if broker.startswith("FK") else "ek"
    rows = [r for r in (ex.replay_exit(tr, ohlc[tr["ticker"]], ma[tr["ticker"]], std[tr["ticker"]],
                                       logic="mean_revert", family=fam, cost=ex.COSTS[broker],
                                       be_r=0.0, max_hold=MAX_HOLD_D) for tr in trades) if r]
    if not rows:
        return None
    d = pd.DataFrame(rows)
    d0 = pd.to_datetime(d["d0"])
    iss, oos = ex.stats(d.loc[d0 < IS_END, "R"]), ex.stats(d.loc[d0 >= IS_END, "R"])
    jahre = d.assign(y=d0.dt.year).groupby("y")["R"].mean().round(3).to_dict()
    oos_jahre = {int(y): v for y, v in jahre.items() if y >= 2023}
    rec = {"IS": iss, "OOS": oos, "tage": round(float(d["days"].mean()), 1),
           "oos_jahre": oos_jahre,
           "oos_jahre_positiv": sum(1 for v in oos_jahre.values() if v > 0),
           "n_gesamt": len(d)}
    out[label] = rec
    print(f"  {label:34s} n={len(d):4d} IS {iss.get('avg_R', 0):+.4f} OOS {oos.get('avg_R', 0):+.4f} "
          f"PF {str(oos.get('PF')):5} Jahre+ {rec['oos_jahre_positiv']}/4  "
          f"{ {y: round(v, 3) for y, v in oos_jahre.items()} }", flush=True)
    return rec


def main():
    which = sys.argv[1].upper() if len(sys.argv) > 1 else "ALLE"
    ou_config, ou_portfolio, _ = rx.load_universe()
    uni_heute = universe(ou_config)
    alle_ticker = sorted({t for mk in ("sp500", "nasdaq100")
                          for t in universe(ou_config, pvalue_max=1.0, theta_min=0.0,
                                            hl=(0, 1e9))[mk]})
    ohlc = rx.download(alle_ticker)
    print(f"Titel mit Kursdaten: {len(ohlc)} (heutige Auswahl: "
          f"{sum(len(v) for v in uni_heute.values())})\n", flush=True)
    out = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {}

    def run(label, uni, lookback=20, k=2.0, regime="ema200"):
        tr = build_trades(ou_config, ou_portfolio, uni, ohlc, lookback, k, regime)
        return evaluate(tr, ohlc, lookback, label, out)

    if which in ("A", "ALLE"):
        print("=== A  BB_LOOKBACK (Band UND Ausstiegs-Mittel) ===", flush=True)
        for lb in (10, 15, 20, 30, 40):
            run(f"A lookback {lb}" + (" (heute)" if lb == 20 else ""), uni_heute, lookback=lb)
    if which in ("B", "ALLE"):
        print("\n=== B  BB_K (Einstiegsband) ===", flush=True)
        for k in (1.5, 2.0, 2.5, 3.0):
            run(f"B k {k}" + (" (heute)" if k == 2.0 else ""), uni_heute, k=k)
    if which in ("C", "ALLE"):
        print("\n=== C  Regimefilter ===", flush=True)
        for m in ("aus", "ema100", "ema200", "ema200_steigend"):
            run(f"C regime {m}" + (" (heute)" if m == "ema200" else ""), uni_heute, regime=m)
    if which in ("D", "ALLE"):
        print("\n=== D  OU-Auswahlschwellen ===", flush=True)
        for pv in (0.15, 0.2, 0.25, 1.0):
            run(f"D p_value < {pv}" + (" (heute)" if pv == 0.2 else " (Filter aus)" if pv == 1.0 else ""),
                universe(ou_config, pvalue_max=pv))
        for hl, lab in (((5, 60), "kurz 5-60"), ((60, 200), "lang 60-200"), ((5, 1e9), "aus")):
            run(f"D half_life {lab}", universe(ou_config, hl=hl))
    if which in ("E", "ALLE"):
        print("\n=== E  Universum ===", flush=True)
        for mk in ("sp500", "nasdaq100"):
            run(f"E nur {mk}", universe(ou_config, markets=[mk]))
        run("E ohne TTP-Handelbarkeitsfilter", universe(ou_config, tradable_only=False))

    OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
    print("\ngeschrieben:", OUT_JSON)


if __name__ == "__main__":
    main()
