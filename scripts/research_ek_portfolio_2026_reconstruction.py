"""Ad-hoc 2026-Monatsperformance-Rekonstruktion fuer das EXAKTE, aktuell in
ek_portfolio/paper_bot.py konfigurierte 8-Bein-Portfolio (Nutzerwunsch
2026-08-29: "Uebersicht der moeglichen Ergebnisse von diesem Jahr auf das
exakte Portfolio"). Kein neues Produktionsmodul -- Einmal-Analyse-Skript.

Wiederverwendet ALLE echten Scan-/Merge-/Compounding-Funktionen aus
ek_portfolio/paper_bot.py 1:1 (keine zweite Formel-Implementierung). Die
einzige Huerde: jede _scan_*()-Funktion nutzt ein FEST codiertes Trailing-
Fenster relativ zu `end` (z.B. CTNL nur 90 Tage, BTC EMA nur 100 Tage,
Gold-Silber nur 200 Tage) - fuer eine echte Jahresrekonstruktion reicht ein
einzelner Aufruf mit end=jetzt bei diesen drei Beinen NICHT, da er Anfang
2026 verpassen wuerde. Loesung: bei den kurz-fenstrigen Beinen mehrfach mit
verschiedenen `end`-Zeitpunkten quer durchs Jahr aufrufen (Fenster
ueberlappen sich, kein Loch) und alle Ergebnisse ueber denselben
_merge_trades()-Dedupe-Key vereinigen. Gold ASB (seit 2016)/Trend Pullback
(300 Tage)/CLS Practical (400 Tage)/ORB (500 Tage) brauchen dafuer nur
EINEN Aufruf mit end=jetzt.

OU-Modell: nur die ECHTEN Tages-Renditen ab 2026-07-29 (ou_modell_logs/
daily_log.csv-Beginn) sind verfuegbar - Jan-Jun 2026 bleibt in dieser
Rekonstruktion ohne OU-Modell-Beitrag, klar ausgewiesen im Ergebnis."""

import json
import sys

import pandas as pd

sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting")

from ek_portfolio.paper_bot import (  # noqa: E402
    _load_ou_modell_daily_returns, _merge_trades, _retry, _scan_btc_ema_cross,
    _scan_ctnl, _scan_cls_practical, _scan_gold_asb, _scan_gold_silver,
    _scan_orb, _scan_trend_pullback, _utc_naive, compute_shared_equity,
)
from gold_smc_htf_ltf.live_signal import REV_MAX_CONCURRENT  # noqa: E402

ACCOUNT_START = pd.Timestamp("2026-01-01")
NOW = pd.Timestamp.now(tz="UTC").tz_localize(None)


def _since_start(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    return trades[_utc_naive(trades["entry_time"]) >= ACCOUNT_START]


def _cap_concurrent_reversals(state: dict) -> int:
    """simulate_trades_concurrent() (der Backtest-Simulator hinter CTNL
    Reversal) erzwingt KEIN Limit gleichzeitig offener Positionen - das
    reale REV_MAX_CONCURRENT=3-Limit lebt nur in der Ausfuehrungsschicht
    (siehe EK-Portfolio-Bridge/legs/ctnl_edge/executor.py::
    check_and_execute_reversal, gold_smc_htf_ltf/live_signal.py-Docstring).
    Ein roher Backtest-Trade-Export ueberzeichnet deshalb systematisch, was
    real ausfuehrbar gewesen waere. Simuliert hier nachtraeglich dieselbe
    Greedy-Kappung: Trades chronologisch nach Entry-Zeit durchgehen, ein
    Trade wird verworfen, wenn zu diesem Zeitpunkt bereits REV_MAX_CONCURRENT
    andere (nach ihrer jeweiligen Exit-Zeit) noch offene Reversal-Trades
    laufen -- exakt die Regel, die eine echte Bridge angewendet haette."""
    rev_keys = [k for k, t in state["trades"].items() if t["leg"] == "ctnl_reversal"]
    rows = [(k, pd.Timestamp(state["trades"][k]["entry_time"]), pd.Timestamp(state["trades"][k]["exit_time"]))
            for k in rev_keys]
    rows.sort(key=lambda r: r[1])  # nach entry_time

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

    print("=== Gold ASB (ein Aufruf, Historie seit 2016 deckt 2026 komplett ab) ===")
    trades = _since_start(_retry(lambda: _scan_gold_asb(NOW, force_refresh=False)))
    _merge_trades(state, "gold_asb", trades)
    print(f"  {len(trades)} Trades seit Jahresanfang gefunden")

    print("=== Trend Pullback (ein Aufruf, 300-Tage-Fenster deckt 2026 komplett ab) ===")
    trades = _since_start(_retry(lambda: _scan_trend_pullback(NOW, force_refresh=False)))
    _merge_trades(state, "trend_pullback", trades)
    print(f"  {len(trades)} Trades seit Jahresanfang gefunden")

    print("=== CLS Practical (ein Aufruf, 400-Tage-Fenster deckt 2026 komplett ab) ===")
    trades = _since_start(_retry(lambda: _scan_cls_practical(NOW, force_refresh=False)))
    _merge_trades(state, "cls_practical", trades)
    print(f"  {len(trades)} Trades seit Jahresanfang gefunden")

    print("=== NY-Open ORB (ein Aufruf, 500-Tage-Fenster deckt 2026 komplett ab) ===")
    orb_trades = _since_start(_retry(lambda: _scan_orb(NOW, force_refresh=False)))
    orb_leg_by_market = {"SP500": "orb_sp500", "US30": "orb_us30", "NASDAQ": "orb_nasdaq"}
    if not orb_trades.empty:
        for market, sub in orb_trades.groupby("market"):
            _merge_trades(state, orb_leg_by_market[market], sub)
    print(f"  {len(orb_trades)} Trades seit Jahresanfang gefunden")

    print("=== Gold-Silber-Divergenz (2 Aufrufe, 200-Tage-Fenster braucht Ueberlappung) ===")
    total = 0
    for end in [pd.Timestamp("2026-04-01"), NOW]:
        trades = _since_start(_retry(lambda e=end: _scan_gold_silver(e, force_refresh=False)))
        _merge_trades(state, "gold_silver", trades)
        total += len(trades)
    print(f"  {total} Trade-Fund-Ereignisse ueber beide Fenster (Ueberlappung dedupliziert automatisch)")

    print("=== BTC EMA9/21 (4 Aufrufe, 100-Tage-Fenster braucht Ueberlappung) ===")
    total = 0
    for end in [pd.Timestamp("2026-02-15"), pd.Timestamp("2026-04-15"),
                pd.Timestamp("2026-06-15"), NOW]:
        trades = _since_start(_retry(lambda e=end: _scan_btc_ema_cross(e, force_refresh=False)))
        _merge_trades(state, "btc_ema_cross", trades)
        total += len(trades)
    print(f"  {total} Trade-Fund-Ereignisse ueber alle Fenster")

    print("=== CTNL Continuation+Reversal (4 Aufrufe, 90-Tage-Fenster braucht Ueberlappung) ===")
    total = 0
    for end in [pd.Timestamp("2026-03-15"), pd.Timestamp("2026-05-15"),
                pd.Timestamp("2026-07-15"), NOW]:
        cont_trades, rev_trades = _retry(lambda e=end: _scan_ctnl(e, force_refresh=False))
        _merge_trades(state, "ctnl_continuation", _since_start(cont_trades))
        _merge_trades(state, "ctnl_reversal", _since_start(rev_trades))
        total += len(cont_trades) + len(rev_trades)
    print(f"  {total} Trade-Fund-Ereignisse ueber alle Fenster")

    print(f"\nGesamt eindeutige Trades vor Bereinigung: {len(state['trades'])}")

    with open(r"C:\Users\andre\Forex-Backtesting\scripts\reports\ek_portfolio_2026_raw_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)

    n_dropped = _cap_concurrent_reversals(state)
    print(f"CTNL-Reversal-Trades verworfen (haetten das reale REV_MAX_CONCURRENT={REV_MAX_CONCURRENT}-Limit "
          f"gerissen): {n_dropped}")
    print(f"Gesamt eindeutige Trades nach Bereinigung: {len(state['trades'])}")

    ou_returns = _load_ou_modell_daily_returns(ACCOUNT_START)
    print(f"OU-Modell echte Tage gefunden: {len(ou_returns)} (ab {ou_returns.index.min() if len(ou_returns) else '-'})")

    equity_df = compute_shared_equity(state, ou_returns)
    equity_df.to_csv(r"C:\Users\andre\Forex-Backtesting\scripts\reports\ek_portfolio_2026_equity_events.csv", index=False)
    print(f"\n{len(equity_df)} Equity-Ereignisse insgesamt, gespeichert.")

    if equity_df.empty:
        print("Keine Ereignisse - Abbruch.")
        return

    equity_df["time"] = pd.to_datetime(equity_df["time"])
    equity_df = equity_df.sort_values("time")
    monthly = equity_df.set_index("time")["equity"].resample("ME").last().ffill()

    print("\n=== Monatsperformance 2026 (exaktes 8-Bein-Portfolio) ===")
    prev = 100_000.0
    for dt, val in monthly.items():
        ret = (val / prev - 1) * 100
        print(f"{dt.strftime('%Y-%m')}: Equity {val:>12,.2f}  ({ret:+.2f}% MoM)")
        prev = val
    total_ret = (monthly.iloc[-1] / 100_000.0 - 1) * 100
    print(f"\nGesamt seit Jahresanfang: {total_ret:+.2f}%")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
