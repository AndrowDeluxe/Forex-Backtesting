"""Ad-hoc August-2026-Monatsreport fuer das exakte, aktuell in
ek_portfolio/paper_bot.py konfigurierte 8-Bein-Portfolio (CTNL Continuation/
Reversal und die 3 ORB-Instrumente je als eigene Zeile aufgeschluesselt,
teilen sich aber wie im Original jeweils EINE Kapital-Scheibe -- siehe
CAPITAL_WEIGHT/LEG_LABELS in paper_bot.py) (Nutzerwunsch
2026-09-03: "Backteste das EK Portfolio fuer August 2026, Zahlen je Bein
separat"). Kein neues Produktionsmodul -- Einmal-Analyse-Skript, analog zu
scripts/research_ek_portfolio_2026_reconstruction.py (dort: gesamtes Jahr
2026 mit mehreren ueberlappenden Fenstern je Bein), hier aber bewusst
einfacher: alle Beine haben ein Trailing-Lookback-Fenster >= 90 Tage, ein
einziger Aufruf mit end=Monatsende deckt August komplett ab (kein
mehrfaches ueberlappendes Scannen wie bei der Jahres-Rekonstruktion noetig).

Wiederverwendet ALLE echten Scan-/Merge-/Compounding-Funktionen aus
ek_portfolio/paper_bot.py 1:1 (keine zweite Formel-Implementierung).
State startet frisch am 2026-08-01 (nicht am echten EK-Kontostart), damit
die Auswertung ausschliesslich August-Ereignisse zeigt -- der Vergleich mit
dem echten Live-Konto (EK-Portfolio-Bridge, ausserhalb des Repos) ist NICHT
Teil dieses Skripts, siehe Docstring in ek_portfolio/paper_bot.py.

OU-Modell: nur die ECHTEN Tages-Renditen aus ou_modell_logs/daily_log.csv,
gefiltert auf August 2026 (Konto 1 TTP + Konto 3 Tickmill, siehe
OU_REAL_ACCOUNTS in paper_bot.py)."""

import sys

import pandas as pd

sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting")

from ek_portfolio.paper_bot import (  # noqa: E402
    CAPITAL_WEIGHT, LEG_LABELS, LEG_RISK_PCT, _load_ou_modell_daily_returns,
    _merge_trades, _retry, _scan_btc_ema_cross, _scan_ctnl, _scan_cls_practical,
    _scan_gold_asb, _scan_gold_silver, _scan_orb, _scan_trend_pullback,
    _utc_naive, compute_shared_equity,
)
from gold_smc_htf_ltf.live_signal import REV_MAX_CONCURRENT  # noqa: E402

ACCOUNT_START = pd.Timestamp("2026-08-01")
MONTH_END = pd.Timestamp("2026-08-31 23:59:59")
REPORT_DIR = r"C:\Users\andre\Forex-Backtesting\scripts\reports"


def _since_start(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    return trades[_utc_naive(trades["entry_time"]) >= ACCOUNT_START]


def _cap_concurrent_reversals(state: dict) -> int:
    """Identisch zu scripts/research_ek_portfolio_2026_reconstruction.py::
    _cap_concurrent_reversals -- reale REV_MAX_CONCURRENT-Kappung nachtraeglich
    auf den rohen Backtest-Export anwenden (siehe dortiger Docstring)."""
    rev_keys = [k for k, t in state["trades"].items() if t["leg"] == "ctnl_reversal"]
    rows = [(k, pd.Timestamp(state["trades"][k]["entry_time"]), pd.Timestamp(state["trades"][k]["exit_time"]))
            for k in rev_keys]
    rows.sort(key=lambda r: r[1])

    open_exits: list[pd.Timestamp] = []
    dropped = []
    for key, entry_time, exit_time in rows:
        open_exits = [e for e in open_exits if e > entry_time]
        if len(open_exits) >= REV_MAX_CONCURRENT:
            dropped.append(key)
            continue
        open_exits.append(exit_time)

    for key in dropped:
        del state["trades"][key]
    return len(dropped)


def main() -> None:
    state = {"trades": {}, "kill_switch_active": False, "last_heartbeat_hour": None,
             "eod_equity": {}, "account_start": ACCOUNT_START.isoformat(), "ou_notified_dates": []}

    scans = [
        ("gold_asb", lambda: _scan_gold_asb(MONTH_END, force_refresh=False)),
        ("trend_pullback", lambda: _scan_trend_pullback(MONTH_END, force_refresh=False)),
        ("cls_practical", lambda: _scan_cls_practical(MONTH_END, force_refresh=False)),
        ("gold_silver", lambda: _scan_gold_silver(MONTH_END, force_refresh=False)),
        ("btc_ema_cross", lambda: _scan_btc_ema_cross(MONTH_END, force_refresh=False)),
    ]
    for leg, fn in scans:
        print(f"=== {LEG_LABELS[leg]} ===", flush=True)
        trades = _since_start(_retry(fn))
        _merge_trades(state, leg, trades)
        print(f"  {len(trades)} Trades im August gefunden", flush=True)

    print("=== NY-Open ORB (SP500+US30+NASDAQ) ===", flush=True)
    orb_trades = _since_start(_retry(lambda: _scan_orb(MONTH_END, force_refresh=False)))
    orb_leg_by_market = {"SP500": "orb_sp500", "US30": "orb_us30", "NASDAQ": "orb_nasdaq"}
    if not orb_trades.empty:
        for market, sub in orb_trades.groupby("market"):
            _merge_trades(state, orb_leg_by_market[market], sub)
    print(f"  {len(orb_trades)} Trades im August gefunden", flush=True)

    print("=== CTNL Continuation + Reversal ===", flush=True)
    cont_trades, rev_trades = _retry(lambda: _scan_ctnl(MONTH_END, force_refresh=False))
    cont_trades, rev_trades = _since_start(cont_trades), _since_start(rev_trades)
    _merge_trades(state, "ctnl_continuation", cont_trades)
    _merge_trades(state, "ctnl_reversal", rev_trades)
    print(f"  {len(cont_trades)} Continuation- / {len(rev_trades)} Reversal-Trades im August gefunden", flush=True)

    n_dropped = _cap_concurrent_reversals(state)
    print(f"\nCTNL-Reversal-Trades verworfen (REV_MAX_CONCURRENT={REV_MAX_CONCURRENT}-Limit): {n_dropped}")
    print(f"Gesamt eindeutige Trades im August: {len(state['trades'])}")

    ou_returns = _load_ou_modell_daily_returns(ACCOUNT_START)
    ou_returns = ou_returns[ou_returns.index <= MONTH_END]
    print(f"OU-Modell echte Handelstage im August: {len(ou_returns)}")

    equity_df = compute_shared_equity(state, ou_returns)
    equity_df.to_csv(f"{REPORT_DIR}/ek_portfolio_2026-08_equity_events.csv", index=False)

    if equity_df.empty:
        print("Keine Ereignisse - Abbruch.")
        return

    equity_df["time"] = pd.to_datetime(equity_df["time"])
    equity_df["r_multiple"] = equity_df["pnl"] / equity_df["risk_dollars"]

    rows = []
    for leg in list(LEG_RISK_PCT) + ["ou_modell"]:
        sub = equity_df[equity_df["leg"] == leg]
        if sub.empty:
            rows.append({"leg": leg, "label": LEG_LABELS.get(leg, "OU-Modell"), "n": 0, "wins": 0,
                         "win_rate": None, "sum_r": 0.0, "avg_r": None, "pnl_usd": 0.0})
            continue
        wins = int((sub["pnl"] > 0).sum())
        rows.append({
            "leg": leg, "label": LEG_LABELS.get(leg, "OU-Modell"), "n": len(sub), "wins": wins,
            "win_rate": wins / len(sub), "sum_r": sub["r_multiple"].sum() if leg != "ou_modell" else None,
            "avg_r": sub["r_multiple"].mean() if leg != "ou_modell" else None,
            "pnl_usd": sub["pnl"].sum(),
        })
    leg_df = pd.DataFrame(rows)
    leg_df.to_csv(f"{REPORT_DIR}/ek_portfolio_2026-08_leg_breakdown.csv", index=False)

    starting_equity = 100_000.0
    ending_equity = float(equity_df["equity"].iloc[-1])
    running_max = equity_df["equity"].cummax()
    max_dd = float(((equity_df["equity"] - running_max) / running_max).min())

    print("\n=== August 2026 -- Ergebnis je Bein (EK-Portfolio, 8-Bein-Konfiguration) ===")
    for _, r in leg_df.iterrows():
        if r["leg"] == "ou_modell":
            print(f"{r['label']:<26} n={r['n']:>3}  PnL=${r['pnl_usd']:>10,.2f}  (echte Tagesrenditen, kein R-Multiple)")
        else:
            wr = f"{r['win_rate']:.0%}" if r["win_rate"] is not None else "  - "
            avg_r = f"{r['avg_r']:+.2f}" if r["avg_r"] is not None else "  - "
            sum_r = f"{r['sum_r']:+.2f}" if r["sum_r"] is not None else "  - "
            print(f"{r['label']:<26} n={r['n']:>3}  WinRate={wr:>5}  SumR={sum_r:>7}  AvgR={avg_r:>6}  PnL=${r['pnl_usd']:>10,.2f}")

    print(f"\nStart-Equity: ${starting_equity:,.2f}")
    print(f"End-Equity:   ${ending_equity:,.2f}")
    print(f"Monatsrendite: {(ending_equity / starting_equity - 1):+.2%}")
    print(f"Max Intra-Monats-Drawdown: {max_dd:.2%}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
