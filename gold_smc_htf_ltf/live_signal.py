"""Pure, stateless live-signal reader for CTNL Edge (Continuation +
Reversal-Kaskade), FINAL locked configs (chat 2026-08-20: "kommen wir wie
gewohnt zum Bot"). Mirrors btc_ema_cross.live_scan.current_signal()'s
contract exactly: "the broker account itself IS the position state" - a
real execution bridge (private, outside this repo - pattern: CLS-
Practical-Bridge, OU-Modell-MT5-Bridge, GoldASB-MT5-Bridge) tracks open
positions via mt5.positions_get() itself; this module only answers "does
the rule fire right now, and what are entry/stop/target" - no state, no
file writes, no side effects.

Recomputes the full vectorised pipeline (gold_smc_htf_ltf.continuation/
reversal_cascade) on a TRAILING lookback window ending "now" rather than
the full history - much faster for a frequent live scan, but this is a
disclosed approximation that MUST be verified against the full-history
backtest before being trusted (scripts/verify_gold_ctnl_edge_live_signal.py,
same discipline as scripts/verify_btc_ema_cross_live_scan.py: "run the
bot's --backfill command and check its trade list matches your backtest.
If they disagree, stop and fix - never run logic you haven't verified.").

Signal is read off the MOST RECENTLY CLOSED bar (M5 for Continuation, M15
for Reversal-Kaskade) - matching simulate_trades' own "signal known at
close of bar t, fill at bar t+1's open" convention. A bridge polling this
function right after each M5/M15 bar close will see a signal on the very
bar it fires, and should fill at the current market price (the "next
bar's open" the backtest assumes)."""

import numpy as np
import pandas as pd

from .concurrent_backtest import simulate_combined_account
from .continuation import run_pipeline as run_continuation
from .data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from .reversal_cascade import run_pipeline as run_reversal

CONT_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_STOP_ATR_MULT = 0.5

REV_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_STOP_ATR_MULT = 3.0
REV_TP_R = 5.0
REV_MAX_CONCURRENT = 3

# FK-Challenge-Risiko-Split (chat 2026-08-20, "die als letzte validierte FK
# Risiko Splittung" - siehe knowledge/projects/gold-ctnl-edge-portfolio.md):
FK_RISK_CONT = 0.005
FK_RISK_REV = 0.0015

LOOKBACK_DAYS = 90  # empirisch gegen die Vollhistorie verifiziert, siehe verify-Skript

# Phase-6-Bootstrap-Referenz (research_gold_smc_phase6_robustness.py, block_size=20,
# n_sims=2000, FK 0.50%/0.15%): P5-MaxDD lag bei -6.56%, konservativ gerundet. Bei
# substanzieller Config-Aenderung (anderer Risiko-Split, neue Pipeline-Kwargs) neu
# ziehen statt blind weiterzuverwenden.
CTNL_KILL_SWITCH_DD_THRESHOLD = -0.066


def ctnl_standalone_drawdown(cont_trades: pd.DataFrame, rev_trades: pd.DataFrame, starting_equity: float = 100_000.0) -> float:
    """Stand-alone Continuation+Reversal-Drawdown mit den EIGENEN FK-Risikogroessen
    (FK_RISK_CONT/FK_RISK_REV) auf einem eigenen 100k-Konto, komplett unabhaengig von
    der Equity/Gewichtung des aufrufenden Portfolio-Bots -- exakt dieselbe Rechnung wie
    gold_smc_htf_ltf/paper_bot.py's Kill-Switch (dort das Original). Fund 2026-09-03:
    dieser Monitor lief nur in der eigenstaendigen "CTNL-Edge-FK-Paper"-Task, die bei
    der Portfolio-Konsolidierung 2026-08-27 deaktiviert wurde, OHNE dass die Pruefung
    selbst in die 3 Nachfolge-Bots (EK/Challenge/FK Instant Funding) uebernommen wurde --
    lief seitdem live nirgends mehr, obwohl genau er den Trigger fuer den beobachteten
    August-2026-Bruch (CTNL Reversal 0/14) haette liefern sollen. Nachgeruestet in allen
    drei `paper_bot.py`, damit jede Portfolio-Instanz ihn wieder selbst prueft."""
    sim = simulate_combined_account(
        {"continuation": cont_trades, "reversal": rev_trades},
        {"continuation": FK_RISK_CONT, "reversal": FK_RISK_REV},
        {"continuation": None, "reversal": REV_MAX_CONCURRENT},
        starting_equity=starting_equity,
    )
    eq = sim["equity_curve"]["equity"].to_numpy()
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def _fetch_window(end: pd.Timestamp, lookback_days: int, force_refresh: bool):
    start = (end - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    h4 = fetch_gold_h4(start, end_str, force_refresh=force_refresh)
    h1 = fetch_gold_h1(start, end_str, force_refresh=force_refresh)
    m15 = fetch_gold_m15(start, end_str, force_refresh=force_refresh)
    m5 = fetch_gold_m5(start, end_str, force_refresh=force_refresh)
    return h4, h1, m15, m5


def continuation_signal(as_of: pd.Timestamp | None = None, lookback_days: int = LOOKBACK_DAYS, force_refresh: bool = True,
                          _h4=None, _h1=None, _m15=None, _m5=None) -> dict:
    """{date, has_signal} or {date, has_signal: True, direction, entry_ref,
    stop, target, atr, risk_pct} for the most recently closed M5 bar.
    entry_ref is the trigger bar's own close (informational) - the bridge
    fills at the current live price, matching the backtest's next-bar-open
    convention. `_h4`/`_h1`/`_m15`/`_m5` let the verify-script inject an
    already-fetched full-history slice instead of a fresh trailing fetch."""
    end = as_of if as_of is not None else pd.Timestamp.now(tz="America/New_York")
    if _m5 is not None:
        h4, h1, m15, m5 = _h4, _h1, _m15, _m5
    else:
        h4, h1, m15, m5 = _fetch_window(end, lookback_days, force_refresh)
    if m5.empty or h1.empty or h4.empty:
        return {"date": str(end), "status": "keine Daten"}

    merged = run_continuation(h4, h1, m5, trend_df=m15, **CONT_KWARGS)
    merged = merged[merged.index <= end]
    if merged.empty:
        return {"date": str(end), "status": "keine Bars im Fenster"}

    last = merged.iloc[-1]
    sig = int(last["signal"])
    if sig == 0:
        return {"date": str(merged.index[-1]), "has_signal": False}

    direction = "long" if sig == 1 else "short"
    atr = float(last["atr"])
    trigger = float(last["low"]) if sig == 1 else float(last["high"])
    stop = trigger - CONT_STOP_ATR_MULT * atr if sig == 1 else trigger + CONT_STOP_ATR_MULT * atr
    target = float(last["vwap"]) if pd.notna(last["vwap"]) else None

    return {
        "date": str(merged.index[-1]), "has_signal": True, "direction": direction,
        "entry_ref": float(last["close"]), "stop": stop, "target": target, "atr": atr,
        "risk_pct": FK_RISK_CONT,
    }


def reversal_signal(as_of: pd.Timestamp | None = None, lookback_days: int = LOOKBACK_DAYS, force_refresh: bool = True,
                      _h4=None, _h1=None, _m15=None) -> dict:
    """Same contract as continuation_signal(), for the most recently
    closed M15 bar. target is the 5R ATR-multiple level (informational -
    the bridge should manage the actual TP itself, see max_hold_bars
    caveat in reversal_cascade.py's module docstring: vwap/h1_target
    drifts as new H1 context arrives, a resting broker TP order at THIS
    snapshot's level is the correct live-execution semantics, matching
    how continuation's literal H4-level TP is meant to be read too - it's
    a live price target, not a backtest-only artifact)."""
    end = as_of if as_of is not None else pd.Timestamp.now(tz="America/New_York")
    if _m15 is not None:
        h4, h1, m15 = _h4, _h1, _m15
    else:
        h4, h1, m15, _ = _fetch_window(end, lookback_days, force_refresh)
    if m15.empty or h1.empty or h4.empty:
        return {"date": str(end), "status": "keine Daten"}

    merged = run_reversal(h4, h1, m15, **REV_KWARGS)
    merged = merged[merged.index <= end]
    if merged.empty:
        return {"date": str(end), "status": "keine Bars im Fenster"}

    last = merged.iloc[-1]
    sig = int(last["signal"])
    if sig == 0:
        return {"date": str(merged.index[-1]), "has_signal": False}

    direction = "long" if sig == 1 else "short"
    atr = float(last["atr"])
    trigger = float(last["low"]) if sig == 1 else float(last["high"])
    stop = trigger - REV_STOP_ATR_MULT * atr if sig == 1 else trigger + REV_STOP_ATR_MULT * atr
    initial_risk = abs(trigger - stop)
    target = trigger + REV_TP_R * initial_risk if sig == 1 else trigger - REV_TP_R * initial_risk

    return {
        "date": str(merged.index[-1]), "has_signal": True, "direction": direction,
        "entry_ref": float(last["close"]), "stop": stop, "target": target, "atr": atr,
        "risk_pct": FK_RISK_REV, "max_concurrent": REV_MAX_CONCURRENT,
    }


def continuation_market_state(as_of: pd.Timestamp | None = None, lookback_days: int = LOOKBACK_DAYS, force_refresh: bool = True) -> dict:
    """For a bridge managing an ALREADY-OPEN Continuation position: the
    target (h1_target/vwap) is DYNAMIC (re-read fresh every bar, per
    continuation.py's module docstring - it is NOT a static broker-side TP
    the backtest sets once at entry), so an open position must be re-
    checked against the CURRENT target on every poll, independent of
    whether a fresh entry signal exists this bar. Returns {date, close,
    target} - target is None if h1_target has gone stale/NaN (H4 context
    expired) - a bridge seeing that should flatten defensively rather than
    hold with no exit reference."""
    end = as_of if as_of is not None else pd.Timestamp.now(tz="America/New_York")
    h4, h1, m15, m5 = _fetch_window(end, lookback_days, force_refresh)
    if m5.empty or h1.empty or h4.empty:
        return {"date": str(end), "status": "keine Daten"}

    merged = run_continuation(h4, h1, m5, trend_df=m15, **CONT_KWARGS)
    merged = merged[merged.index <= end]
    if merged.empty:
        return {"date": str(end), "status": "keine Bars im Fenster"}

    last = merged.iloc[-1]
    return {
        "date": str(merged.index[-1]), "close": float(last["close"]),
        "target": float(last["vwap"]) if pd.notna(last["vwap"]) else None,
    }


def current_signal(as_of: pd.Timestamp | None = None) -> dict:
    """Combined read for both strategies - one Dukascopy fetch, both
    pipelines. Convenience wrapper for a bridge/scanner that wants both in
    one call."""
    end = as_of if as_of is not None else pd.Timestamp.now(tz="America/New_York")
    h4, h1, m15, m5 = _fetch_window(end, LOOKBACK_DAYS, force_refresh=True)
    return {
        "date": str(end),
        "continuation": continuation_signal(end, _h4=h4, _h1=h1, _m15=m15, _m5=m5),
        "reversal": reversal_signal(end, _h4=h4, _h1=h1, _m15=m15),
    }
