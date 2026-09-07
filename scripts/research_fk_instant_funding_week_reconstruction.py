"""Ad-hoc Wochen-Rekonstruktion fuer FK Instant Funding (Nutzerwunsch
2026-09-06: "Backtest der moeglichen Trades dieser Woche" vs. tatsaechlich
geloggte Trades in fk_instant_funding_logs/paper_state.json). Kein neues
Produktionsmodul -- Einmal-Analyse-Skript, Muster identisch zu
scripts/research_ek_portfolio_2026_reconstruction.py.

Alle 9 Beine haben ein Trailing-Fenster (LOOKBACK_DAYS/300/400/200/500 Tage),
das eine einzelne Handelswoche um Groessenordnungen ueberdeckt -- anders als
die EK-Jahres-Rekonstruktion braucht es hier KEINE mehrfachen ueberlappenden
end-Aufrufe, ein einziger Aufruf mit end=jetzt pro Bein reicht. Nutzt die
ECHTEN _scan_*()-Funktionen aus fk_instant_funding/paper_bot.py 1:1 (keine
zweite Formel-Implementierung); _scan_ctnl() kappt REV_MAX_CONCURRENT
bereits intern (anders als beim aelteren ek_portfolio-Code, siehe dortiger
_cap_concurrent_reversals()-Wrapper, der hier nicht mehr noetig ist)."""

import json
import sys

import pandas as pd

sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting")

from fk_instant_funding.paper_bot import (  # noqa: E402
    LOG_DIR, STATE_PATH, _merge_trades, _retry, _scan_ctnl, _scan_cls_practical,
    _scan_gold_asb, _scan_gold_silver, _scan_orb, _scan_trend_pullback, _utc_naive,
)

WEEK_START = pd.Timestamp("2026-08-31")  # Montag dieser Woche
# NICHT pd.Timestamp.now(): Fund 2026-09-06 beim ersten Lauf dieses Skripts an
# einem Sonntag -- ein end mitten im Wochenende laesst den "frische Daten
# seit gestern"-Teilfetch mehrerer _scan_*()-Funktionen (z.B. Gold ASB) eine
# GENUIN LEERE Dukascopy-Antwort (0 Zeilen, Wochenende = kein Handel) liefern,
# deren Spalten dann object-dtype statt float sind -- combined_strategy/
# data.py::validate_ohlc_numeric() haelt das faelschlich fuer korrupte Daten
# und wirft, _retry() erschoepft alle 6 Versuche erfolglos (kein transienter
# Fehler, JEDER Versuch liefert dieselbe leere Antwort). Betrifft NICHT den
# echten Bot: dessen run_scan() ueberspringt Scans am Wochenende komplett per
# is_market_paused() (siehe paper_bot.py), bevor je ein solcher Fetch
# passiert -- reines Artefakt dieses Skripts, das end=jetzt direkt an die
# _scan_*()-Funktionen durchreicht. Fix: end auf Freitagabend (letzter echter
# Handelszeitpunkt dieser Woche) fixieren statt auf das echte "jetzt".
NOW = pd.Timestamp("2026-09-04T21:00:00")

REPORT_PATH = LOG_DIR.parent / "scripts" / "reports" / "fk_instant_funding_week_20260831_reconstruction.json"


def _since_week_start(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    return trades[_utc_naive(trades["entry_time"]) >= WEEK_START]


def main() -> None:
    backtest_state = {"trades": {}}

    print(f"=== FK Instant Funding: Rekonstruktion moeglicher Trades {WEEK_START.date()} bis {NOW} ===\n")

    print("Gold ASB ...")
    trades = _since_week_start(_retry(lambda: _scan_gold_asb(NOW, force_refresh=False)))
    _merge_trades(backtest_state, "gold_asb", trades)
    print(f"  {len(trades)} Trade(s)")

    print("CLS Practical ...")
    trades = _since_week_start(_retry(lambda: _scan_cls_practical(NOW, force_refresh=False)))
    _merge_trades(backtest_state, "cls_practical", trades)
    print(f"  {len(trades)} Trade(s)")

    print("Trend Pullback ...")
    trades = _since_week_start(_retry(lambda: _scan_trend_pullback(NOW, force_refresh=False)))
    _merge_trades(backtest_state, "trend_pullback", trades)
    print(f"  {len(trades)} Trade(s)")

    print("NY-Open ORB (SP500/US30/NASDAQ) ...")
    orb_trades = _since_week_start(_retry(lambda: _scan_orb(NOW, force_refresh=False)))
    orb_leg_by_market = {"SP500": "orb_sp500", "US30": "orb_us30", "NASDAQ": "orb_nasdaq"}
    if not orb_trades.empty:
        for market, sub in orb_trades.groupby("market"):
            _merge_trades(backtest_state, orb_leg_by_market[market], sub)
    print(f"  {len(orb_trades)} Trade(s)")

    print("Gold-Silber-Divergenz ...")
    trades = _since_week_start(_retry(lambda: _scan_gold_silver(NOW, force_refresh=False)))
    _merge_trades(backtest_state, "gold_silver", trades)
    print(f"  {len(trades)} Trade(s)")

    print("CTNL Continuation+Reversal ...")
    cont_trades, rev_trades = _retry(lambda: _scan_ctnl(NOW, force_refresh=False))
    cont_trades = _since_week_start(cont_trades)
    rev_trades = _since_week_start(rev_trades)
    _merge_trades(backtest_state, "ctnl_continuation", cont_trades)
    _merge_trades(backtest_state, "ctnl_reversal", rev_trades)
    print(f"  {len(cont_trades) + len(rev_trades)} Trade(s)")

    print(f"\nGesamt moegliche Trades laut Backtest diese Woche: {len(backtest_state['trades'])}")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(backtest_state, f, indent=2, default=str)

    # ------------------------------------------------------------- Vergleich
    logged_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    logged_this_week = {
        k: t for k, t in logged_state["trades"].items()
        if pd.Timestamp(t["entry_time"]) >= WEEK_START
    }

    bt_keys = set(backtest_state["trades"].keys())
    logged_keys = set(logged_this_week.keys())

    matched = sorted(bt_keys & logged_keys)
    only_backtest = sorted(bt_keys - logged_keys)
    only_logged = sorted(logged_keys - bt_keys)

    print(f"\n=== Vergleich gegen tatsaechlich geloggte Trades ({STATE_PATH}) ===")
    print(f"Geloggte Trades diese Woche: {len(logged_keys)}")
    print(f"Uebereinstimmend (gleicher Leg/Markt/Entry-Zeit/Richtung): {len(matched)}")
    print(f"Nur im Backtest gefunden (vom Bot NICHT geloggt): {len(only_backtest)}")
    print(f"Nur geloggt (vom Backtest NICHT reproduziert): {len(only_logged)}")

    def _fmt(key: str, t: dict) -> str:
        return (f"  {t['entry_time']}  {t['leg']:<18} r={t['r_multiple']:+.2f}  "
                f"exit={t['exit_reason']:<10} key={key}")

    if matched:
        print("\n--- Uebereinstimmend ---")
        for k in matched:
            bt_r = backtest_state["trades"][k]["r_multiple"]
            log_r = logged_this_week[k]["r_multiple"]
            flag = "" if abs(bt_r - log_r) < 0.01 else f"  [r_multiple weicht ab: backtest={bt_r:+.2f} vs. log={log_r:+.2f}]"
            print(_fmt(k, backtest_state["trades"][k]) + flag)

    if only_backtest:
        print("\n--- NUR im Backtest (moeglicher verpasster Trade -- z.B. Scan-Fehler/Timeout) ---")
        for k in only_backtest:
            print(_fmt(k, backtest_state["trades"][k]))

    if only_logged:
        print("\n--- NUR geloggt (vom frischen Backtest nicht reproduziert -- ungewoehnlich, pruefen) ---")
        for k in only_logged:
            print(_fmt(k, logged_this_week[k]))

    print(f"\nRoh-Ergebnis gespeichert: {REPORT_PATH}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
