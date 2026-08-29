"""FK-Challenge Paper-Forward-Test-Bot fuer CTNL Edge (chat 2026-08-20) -
NICHT der echte Order-Ausfuehrer (der laeuft ueber die private MT5-Bridge,
siehe live_signal.py-Docstring). Dieser Bot tracked ein hypothetisches
Konto mit dem finalen FK-Risiko-Split (0.50% Continuation / 0.15%
Reversal-Kaskade, max_concurrent=3 fuer Reversal), sendet Telegram bei
Trade-Ereignissen, schreibt einen stuendlichen Heartbeat und prueft den
Kill-Switch (rollierender Drawdown gegen die Phase-6-Monte-Carlo-P5-
Schwelle, siehe knowledge/projects/gold-ctnl-edge-portfolio.md).

Architektur: statt Stop/Target/Exit inkrementell neu zu implementieren
(Risiko fuer stille Abweichung vom getesteten Backtest-Code), laesst
jeder Scan die ECHTEN strategy.backtest.simulate_trades / gold_smc_htf_
ltf.concurrent_backtest.simulate_trades_concurrent Engines frisch auf dem
90-Tage-Trailing-Fenster laufen (identische Funktionen wie im Backtest -
keine Duplizierung von Stop/Target-Logik) und gleicht das Ergebnis gegen
den PERSISTIERTEN Trade-Verlauf ab (gold_ctnl_edge_logs/fk_paper_state.json):
neue Trades -> ENTRY-Telegram, ein Trade dessen exit_reason von "data_end"
(noch offen) zu einem echten Grund wechselt -> EXIT-Telegram (genau einmal,
per notified_exit-Flag)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.concurrent_backtest import equity_curve_to_daily_returns, simulate_combined_account, simulate_trades_concurrent
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.live_signal import CONT_KWARGS, FK_RISK_CONT, FK_RISK_REV, LOOKBACK_DAYS, REV_KWARGS, REV_MAX_CONCURRENT
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from gold_smc_htf_ltf.telegram_notify import send_telegram_message
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe
from strategy.schedule_guard import is_market_paused

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_DIR / "gold_ctnl_edge_logs"
STATE_PATH = LOG_DIR / "fk_paper_state.json"
HEARTBEAT_CSV = LOG_DIR / "fk_paper_heartbeat.csv"

STARTING_EQUITY = 100_000.0  # Platzhalter - vor echtem Livegang auf die reale FK-Kontogroesse setzen
MAX_CONCURRENT = {"continuation": None, "reversal": REV_MAX_CONCURRENT}

# Phase-6-Bootstrap-Referenz (research_gold_smc_phase6_robustness.py,
# block_size=20, n_sims=2000, FK 0.50%/0.15%): P5-MaxDD lag bei -6.56%
# (erster Bootstrap-Lauf) bzw. -6.56% im finalen 0.50/0.15-Sweep - konservativ
# gerundet. Bei substanzieller Config-Aenderung neu ziehen, nicht blind
# weiterverwenden.
KILL_SWITCH_MDD_THRESHOLD = -0.066

CONT_CFG = BacktestConfig(spread_bps=8.0, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)
REV_CFG = BacktestConfig(spread_bps=8.0, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)


def _default_state() -> dict:
    return {"trades": {}, "kill_switch_active": False, "last_heartbeat_hour": None}


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return _default_state()


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _fetch_window(end: pd.Timestamp, force_refresh: bool):
    start = (end - pd.Timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    h4 = fetch_gold_h4(start, end_str, force_refresh=force_refresh)
    h1 = fetch_gold_h1(start, end_str, force_refresh=force_refresh)
    m15 = fetch_gold_m15(start, end_str, force_refresh=force_refresh)
    m5 = fetch_gold_m5(start, end_str, force_refresh=force_refresh)
    return h4, h1, m15, m5


def _merge_trades(state: dict, strategy: str, trades: pd.DataFrame, dry_run: bool) -> list[str]:
    """Merges freshly-computed window `trades` into state["trades"], returns
    a list of Telegram messages to send (entries/first-time real exits)."""
    messages = []
    for _, t in trades.iterrows():
        key = f"{strategy}_{t['entry_time'].isoformat()}_{int(t['direction'])}"
        entry_price, exit_price, exit_reason = float(t["entry_price"]), float(t["exit_price"]), t["exit_reason"]
        direction_label = "LONG" if t["direction"] == 1 else "SHORT"
        r_mult = float(t["r_multiple"]) if pd.notna(t.get("r_multiple", np.nan)) else None

        if key not in state["trades"]:
            state["trades"][key] = {
                "strategy": strategy, "entry_time": t["entry_time"].isoformat(), "direction": int(t["direction"]),
                "entry_price": entry_price, "exit_time": t["exit_time"].isoformat(), "exit_price": exit_price,
                "exit_reason": exit_reason, "r_multiple": r_mult, "notified_exit": exit_reason != "data_end",
            }
            messages.append(
                f"[CTNL Edge FK-Paper] \U0001F7E2 ENTRY {strategy} {direction_label} @ {entry_price:.2f}\n"
                f"Zeit: {t['entry_time']}"
            )
        else:
            rec = state["trades"][key]
            rec["exit_time"], rec["exit_price"], rec["exit_reason"], rec["r_multiple"] = t["exit_time"].isoformat(), exit_price, exit_reason, r_mult
            if exit_reason != "data_end" and not rec.get("notified_exit", False):
                icon = "\U0001F7E2" if (r_mult or 0) > 0 else "\U0001F534"
                messages.append(
                    f"[CTNL Edge FK-Paper] {icon} EXIT {strategy} {direction_label} ({exit_reason}) @ {exit_price:.2f}\n"
                    f"R-Multiple: {r_mult:+.2f}" if r_mult is not None else f"[CTNL Edge FK-Paper] EXIT {strategy} {direction_label} ({exit_reason})"
                )
                rec["notified_exit"] = True
    return messages


def _state_trades_df(state: dict, strategy: str) -> pd.DataFrame:
    rows = [r for r in state["trades"].values() if r["strategy"] == strategy]
    if not rows:
        return pd.DataFrame(columns=["entry_time", "exit_time", "direction", "entry_price", "exit_price", "exit_reason", "r_multiple"])
    df = pd.DataFrame(rows)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    return df


def scan_once(as_of: pd.Timestamp | None = None, dry_run: bool = False, state_override: dict | None = None) -> dict:
    end = as_of if as_of is not None else pd.Timestamp.now(tz="America/New_York")

    # Wochenende/Spread-Stunde: Gold (XAUUSD) handelt nicht am Wochenende und
    # hat dieselbe taegliche Spread-Ausweitung wie andere FX-Instrumente
    # (User-Wunsch 2026-08-29, siehe strategy/schedule_guard.py). `end` ist
    # hier NY-zeitzonenbehaftet, is_market_paused() erwartet UTC-naiv -- erst
    # umrechnen. Ein expliziter as_of-Aufruf (Tests/Backtests) wird NICHT
    # pausiert.
    if as_of is None and is_market_paused(end.tz_convert("UTC").tz_localize(None)):
        state = dict(state_override) if state_override is not None else load_state()
        return {"date": str(end), "paused": True, "messages": []}, state

    state = dict(state_override) if state_override is not None else load_state()
    if "trades" not in state:
        state = _default_state()

    h4, h1, m15, m5 = _fetch_window(end, force_refresh=not dry_run)
    if m5.empty or h1.empty or h4.empty:
        return {"date": str(end), "status": "keine Daten", "messages": []}, state

    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_KWARGS)
    cont_sig = cont_sig[cont_sig.index <= end]
    cont_trades = simulate_trades(cont_sig, CONT_CFG)

    rev_sig = run_reversal(h4, h1, m15, **REV_KWARGS)
    rev_sig = rev_sig[rev_sig.index <= end]
    rev_trades = simulate_trades_concurrent(rev_sig, REV_CFG)

    messages = []
    messages += _merge_trades(state, "continuation", cont_trades, dry_run)
    messages += _merge_trades(state, "reversal", rev_trades, dry_run)

    all_cont = _state_trades_df(state, "continuation")
    all_rev = _state_trades_df(state, "reversal")
    sim = simulate_combined_account(
        {"continuation": all_cont, "reversal": all_rev},
        {"continuation": FK_RISK_CONT, "reversal": FK_RISK_REV},
        MAX_CONCURRENT, starting_equity=STARTING_EQUITY,
    )
    eq = sim["equity_curve"]["equity"].to_numpy()
    peak = np.maximum.accumulate(eq) if len(eq) else np.array([STARTING_EQUITY])
    current_dd = float(((eq - peak) / peak).min()) if len(eq) else 0.0

    row = {
        "date": str(end), "final_equity": sim["final_equity"], "current_dd": current_dd,
        "n_trades": sim["n_taken"], "kill_switch_active": state.get("kill_switch_active", False),
    }

    if current_dd < KILL_SWITCH_MDD_THRESHOLD and not state.get("kill_switch_active", False):
        state["kill_switch_active"] = True
        messages.append(
            f"[CTNL Edge FK-Paper] \U0001F6A8 KILL-SWITCH: Drawdown {current_dd:.2%} unter der "
            f"Phase-6-P5-Schwelle ({KILL_SWITCH_MDD_THRESHOLD:.2%}). Neue Entries pruefen/pausieren, "
            f"Phase 6 auf frischeren Daten neu durchlaufen."
        )
    elif current_dd >= KILL_SWITCH_MDD_THRESHOLD * 0.5 and state.get("kill_switch_active", False):
        state["kill_switch_active"] = False  # Erholung ueber die Haelfte der Schwelle - Reset

    current_hour_key = end.strftime("%Y-%m-%d %H")
    if state.get("last_heartbeat_hour") != current_hour_key:
        state["last_heartbeat_hour"] = current_hour_key
        heartbeat_msg = (
            f"[CTNL Edge FK-Paper] Stuendlicher Status {end.strftime('%Y-%m-%d %H:%M')}\n"
            f"Equity: ${sim['final_equity']:,.0f}  |  DD: {current_dd:.2%}  |  Trades: {sim['n_taken']}  |  "
            f"Kill-Switch: {'AKTIV' if state['kill_switch_active'] else 'ok'}"
        )
        if not dry_run:
            send_telegram_message(heartbeat_msg)
            LOG_DIR.mkdir(exist_ok=True)
            is_new = not HEARTBEAT_CSV.exists()
            with open(HEARTBEAT_CSV, "a", encoding="utf-8") as f:
                if is_new:
                    f.write("date,final_equity,current_dd,n_trades,kill_switch_active\n")
                f.write(f"{end.isoformat()},{sim['final_equity']:.2f},{current_dd:.4f},{sim['n_taken']},{state['kill_switch_active']}\n")

    if not dry_run:
        for m in messages:
            send_telegram_message(m)
        save_state(state)

    row["messages"] = messages
    return row, state


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows-Konsole ist sonst cp1252, Telegram-Emojis crashen den print()

    result, _ = scan_once()
    print(json.dumps({k: v for k, v in result.items() if k != "messages"}, indent=2, default=str))
    for m in result.get("messages", []):
        print("---")
        print(m)
