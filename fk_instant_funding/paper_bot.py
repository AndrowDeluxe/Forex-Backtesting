"""FK Instant Funding - Paper-Forward-Test-Bot (2026-08-25).

NICHT der echte Order-Ausfuehrer. Voellig NEUES, separates Modul -- ruehrt an
KEINER Stelle die vier bestehenden, bereits live laufenden Bridges an
(GoldASB-MT5-Bridge, CLS-Practical-Bridge, TrendPullback-Bot,
CTNL-Edge-MT5-Bridge), die weiterhin unabhaengig auf ihren eigenen Konten mit
vollem Kapitalzugriff traden. Dieser Bot ist reine Paper-Simulation +
Telegram-Alerts fuer das GEMEINSAME 100k-Instant-Funding-Konto (5 Beine:
Gold ASB, CLS Practical, Trend Pullback, CTNL Edge [Continuation+Reversal],
Gold-Silber-Divergenz), bis eine bewusste, separate Entscheidung fuer echte
Order-Ausfuehrung gegen ein gemeinsames Konto getroffen wird -- Architektur-
Vorbild: gold_smc_htf_ltf/paper_bot.py.

Jeder Scan laesst die ECHTEN, bereits validierten Signal-Engines jeder
Strategie frisch auf einem strategie-eigenen Trailing-Fenster laufen (keine
Logik-Duplizierung), gleicht das Ergebnis gegen den PERSISTIERTEN
Trade-Verlauf ab (fk_instant_funding_logs/paper_state.json) und baut daraus
EINE gemeinsame, sequenziell kompoundierende Paper-Equity-Kurve mit der
Kapitalanteil-Verduennungsformel (siehe portfolio_construction/results/
fk_instant_funding_final.json):

    risk_dollars = CAPITAL_WEIGHT (20%) x internes Risiko/Trade x aktuelle
                   SHARED-Equity, GEDECKELT auf 0.5% des STARTKAPITALS

Der Deckel ist neu ggue. dem reinen Backtest: die 0,5%-Regel bezieht sich
laut Regelwerk explizit auf das STARTKAPITAL (fester Dollar-Betrag), waehrend
die Positionsgroessen-Formel bewusst mit der AKTUELLEN Equity mitwaechst
(damit das Konto compoundet). Ohne Deckel wuerde ein wachsendes Konto
irgendwann automatisch ueber die 0,5%-Grenze hinauswachsen (bei den hier
verwendeten Risikostufen z.B. sobald die Equity sich verdoppelt hat) -- ein
im reinen historischen Backtest nicht sichtbarer, aber realer Compliance-
Risiko, das dieser Bot durch den Deckel aktiv verhindert.

Ueberwacht alle drei Instant-Funding-Regeln:
1. Max. Verlust/Trade 0,5% vom Startkapital (harter Sizing-Deckel, s.o.)
2. Trailing-Drawdown 5% (End-of-Day gegen den bisherigen Hoechststand,
   Floor bewegt sich nur nach oben) -- Kill-Switch, pausiert neue Entries
3. Konsistenzregel 30% (bester Einzeltag / kumulierter Gesamtgewinn) -- laut
   Nutzer-Recherche verweigert ein Bruch nur die naechste Auszahlung, schliesst
   das Konto NICHT. Daher kein Kill-Switch, sondern ein Auszahlungs-Ampel-
   Status (siehe portfolio_construction.py-Tab "FK Instant Funding" fuer die
   Punkt-in-Zeit-Wahrscheinlichkeitskurve, auf der dieser Live-Check beruht)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from fk_instant_funding.telegram_notify import send_telegram_message
from strategy.backtest import BacktestConfig, simulate_trades

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_DIR / "fk_instant_funding_logs"
STATE_PATH = LOG_DIR / "paper_state.json"
HEARTBEAT_CSV = LOG_DIR / "heartbeat.csv"

STARTING_EQUITY = 100_000.0  # Platzhalter -- vor echtem Livegang auf die reale Kontogroesse setzen
CAPITAL_WEIGHT = 0.20  # je Bein, 5 gleichgewichtete Beine (CTNL Continuation+Reversal teilen sich EIN Bein)

MAX_POSITION_LOSS_PCT = 0.005   # vom STARTKAPITAL (fester Dollar-Deckel, siehe Docstring)
TRAILING_DD_PCT = 0.05          # End-of-Day, gegen den bisherigen Hoechststand
CONSISTENCY_CAP_PCT = 0.30      # bester Einzeltag / kumulierter Gesamtgewinn

# interne Risikostufen je Bein, identisch zu portfolio_construction/results/fk_instant_funding_final.json
LEG_RISK_PCT = {
    "gold_asb": 0.02,
    "cls_practical": 0.015,
    "trend_pullback": 0.005,
    "ctnl_continuation": 0.005,
    "ctnl_reversal": 0.0015,
    "gold_silver": 0.01,
}
LEG_LABELS = {
    "gold_asb": "Gold ASB", "cls_practical": "CLS Practical", "trend_pullback": "Trend Pullback",
    "ctnl_continuation": "CTNL Continuation", "ctnl_reversal": "CTNL Reversal", "gold_silver": "Gold-Silber-Divergenz",
}
MAX_POSITION_LOSS_DOLLARS = MAX_POSITION_LOSS_PCT * STARTING_EQUITY


def _utc_naive(x):
    """Jede der 5 Strategien liefert Zeitstempel in einer ANDEREN Zeitzone-
    Konvention (Gold ASB: America/New_York, CLS Practical: Europe/Berlin,
    Trend Pullback/Gold-Silber-Divergenz: UTC, CTNL: America/New_York) --
    ohne Normalisierung crasht jeder Vergleich mit dem tz-naiven `end`
    (tz-aware vs. tz-naive Timestamp-Vergleich ist in pandas ein TypeError,
    kein stiller Fehler). Konvertiert konsistent nach UTC, dann tz-naiv."""
    if isinstance(x, pd.DatetimeIndex):
        return x.tz_convert("UTC").tz_localize(None) if x.tz is not None else x
    s = pd.to_datetime(x, utc=True)
    return s.dt.tz_localize(None) if hasattr(s, "dt") else s.tz_localize(None)


def _default_state() -> dict:
    return {"trades": {}, "kill_switch_active": False, "last_heartbeat_hour": None, "eod_equity": {}}


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return _default_state()


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


# ------------------------------------------------------------------ per-leg Signal-Scans
# Jede Funktion laesst die ECHTE, bereits validierte Engine der Strategie auf
# einem eigenen Trailing-Fenster laufen und liefert eine Trades-DataFrame mit
# mindestens entry_time/exit_time/r_multiple/exit_reason -- identisch zum
# Backtest, keine zweite Implementierung der Entry/Exit-Regeln.

def _scan_gold_asb(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    """BEKANNTE LUECKE (2026-08-25): das echte, live laufende GoldASB-MT5-Bridge
    nutzt fuenf produktiv validierte Filter (ADX, Trend-Bias, Silber-Alignment,
    Liquiditaet, Fuellverzoegerung -- siehe scripts/collect_gold_asb_daily_log.py-
    Docstring), die HIER bewusst NICHT reimplementiert werden (identische
    Vorsicht wie dort: ein zweiter, unabhaengiger Nachbau mit evtl. falschen
    Parametern waere ein echtes Fehlerrisiko). simulate_asian_breakout(df) ohne
    Filter liefert daher MEHR und weniger selektive Signale als der echte Bot --
    diese Bein-Kurve ist bis auf Weiteres eine grobe Naeherung, kein Faksimile.
    Sauberer Fix waere, wie der Collector, direkt aus GoldASB-MT5-Bridge/state/
    *.sqlite3 zu lesen (die tatsaechliche Wahrheit dessen, was der echte Bot
    entschieden hat) statt hier ein zweites Mal zu simulieren -- noch nicht
    umgesetzt."""
    from asian_range_breakout.data import fetch_gold_m15
    from asian_range_breakout.engine import simulate_asian_breakout

    start = (end - pd.Timedelta(days=14)).strftime("%Y-%m-%d")  # Asian-Range ist ein 1-Nacht-Setup, 14 Tage Puffer reicht
    df = fetch_gold_m15(start, (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), force_refresh=force_refresh)
    if df.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])
    trades = simulate_asian_breakout(df)
    if trades.empty:
        return trades
    trades = trades[_utc_naive(trades["entry_time"]) <= end]
    return trades


def _scan_cls_practical(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    from cls_practical.data import fetch_2y_yield_daily, fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
    from cls_practical.engine import simulate_cls_practical
    from cls_practical.rates import compute_combined_rate_risk_multiplier
    from strategy.cls_advanced import PAIRS

    other_majors = [p for p in PAIRS if p != "EURUSD"]
    start = (end - pd.Timedelta(days=400)).strftime("%Y-%m-%d")  # SMA100/ADR14-Warmup, gleiche Konvention wie live_scan.py
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", start, end_str, force_refresh=force_refresh)
    if eurusd_m5.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])
    other_majors_m15 = {p: fetch_major_m15_berlin(p, start, end_str, force_refresh=force_refresh) for p in other_majors}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", start, end_str, force_refresh=force_refresh)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", start, end_str, force_refresh=force_refresh)
    de02y = fetch_2y_yield_daily("DE02Y", force_refresh=force_refresh)
    us02y = fetch_2y_yield_daily("US02Y", force_refresh=force_refresh)

    from strategy.cls_advanced import compute_daily_features
    daily = compute_daily_features(eurusd_m5)
    combined_mult = compute_combined_rate_risk_multiplier(bund_m5, ustbond_m5, de02y, us02y, daily["direction"])

    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, risk_multiplier=combined_mult)
    if trades.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])
    trades = trades[_utc_naive(trades["entry_time"]) <= end].copy()
    if "exit_reason" not in trades.columns:
        trades["exit_reason"] = np.where(trades["exit_time"].notna(), "closed", "data_end")
    return trades


def _scan_trend_pullback(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    from combined_strategy.data import fetch_timeframe
    from mt5_trend_pullback.filters import alignment_filter
    from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline

    CHOSEN_ADX_MIN = 25.0
    MARKETS = [("GOLD", "H1", "XAUUSD", 10.0), ("SILVER", "H1", "XAGUSD", 10.0), ("PLATINUM", "H1", "XPTUSD", 10.0),
               ("CHFJPY", "H4", "CHFJPY", 3.0), ("USDJPY", "H4", "USDJPY", 1.5)]
    _rename = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    start = (end - pd.Timedelta(days=300)).strftime("%Y-%m-%d")  # TREND_LEN=150-Bar-EMA-Warmup + Puffer
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    gold_daily_close = fetch_timeframe("GOLD", "D1", start, end_str, force_refresh=force_refresh)["Close"]
    if gold_daily_close.index.tz is not None:
        gold_daily_close.index = gold_daily_close.index.tz_localize(None)

    all_trades = []
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, start, end_str, force_refresh=force_refresh)
        if df.empty:
            continue
        df = df.rename(columns=_rename)
        signaled = run_pipeline(df, adx_min=CHOSEN_ADX_MIN)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        if label == "XAGUSD" and not trades.empty:
            trades = alignment_filter(trades, gold_daily_close)
        if not trades.empty:
            trades = trades[_utc_naive(trades["entry_time"]) <= end]
            trades["market"] = label
            all_trades.append(trades)
    if not all_trades:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason", "market"])
    return pd.concat(all_trades, ignore_index=True)


def _scan_ctnl(end: pd.Timestamp, force_refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent
    from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
    from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m15, fetch_gold_m5
    from gold_smc_htf_ltf.live_signal import CONT_KWARGS, LOOKBACK_DAYS, REV_KWARGS
    from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal

    start = (end - pd.Timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    h4 = fetch_gold_h4(start, end_str, force_refresh=force_refresh)
    h1 = fetch_gold_h1(start, end_str, force_refresh=force_refresh)
    m15 = fetch_gold_m15(start, end_str, force_refresh=force_refresh)
    m5 = fetch_gold_m5(start, end_str, force_refresh=force_refresh)
    if h4.empty or h1.empty or m15.empty or m5.empty:
        empty = pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])
        return empty, empty

    cont_cfg = BacktestConfig(spread_bps=8.0, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)
    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_KWARGS)
    cont_sig = cont_sig[_utc_naive(cont_sig.index) <= end]
    cont_trades = simulate_trades(cont_sig, cont_cfg)

    rev_cfg = BacktestConfig(spread_bps=8.0, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)
    rev_sig = run_reversal(h4, h1, m15, **REV_KWARGS)
    rev_sig = rev_sig[_utc_naive(rev_sig.index) <= end]
    rev_trades = simulate_trades_concurrent(rev_sig, rev_cfg)
    return cont_trades, rev_trades


def _scan_gold_silver(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    from combined_strategy.data import fetch_timeframe
    from mt5_gold_silver_divergenz.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline

    _rename = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    start = (end - pd.Timedelta(days=200)).strftime("%Y-%m-%d")  # TREND_LEN=150-H4-Bar-Warmup + Puffer
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    df_xau = fetch_timeframe("GOLD", "H4", start, end_str, force_refresh=force_refresh).rename(columns=_rename)
    df_xag = fetch_timeframe("SILVER", "H4", start, end_str, force_refresh=force_refresh).rename(columns=_rename)
    if df_xau.empty or df_xag.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])

    signaled = run_pipeline(df_xau, df_xag, ret_len=25, band_lookback=50, band_mult=1.75, confirm_len=10)
    cfg = BacktestConfig(spread_bps=10.0, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    trades = simulate_trades(signaled, cfg)
    if trades.empty:
        return trades
    return trades[_utc_naive(trades["entry_time"]) <= end]


# ------------------------------------------------------------------ State-Merge (Muster: gold_smc_htf_ltf/paper_bot.py)
def _merge_trades(state: dict, leg: str, trades: pd.DataFrame) -> list[str]:
    """Speichert entry_time/exit_time konsistent als UTC-naive ISO-Strings --
    ohne diese Normalisierung mischen sich beim Wiedereinlesen (_state_trades_df)
    Zeitstempel mit verschiedenen tz-Offsets je Bein in EINER Spalte, was
    pd.to_datetime() mit 'Mixed timezones detected' zum Absturz bringt."""
    messages = []
    for _, t in trades.iterrows():
        if pd.isna(t.get("r_multiple", np.nan)):
            continue
        entry_naive = _utc_naive(t["entry_time"])
        exit_naive = _utc_naive(t["exit_time"])
        key = f"{leg}_{entry_naive.isoformat()}_{int(t.get('direction', 1) if pd.notna(t.get('direction', 1)) else 1)}"
        exit_reason = t.get("exit_reason", "data_end")
        r_mult = float(t["r_multiple"])

        if key not in state["trades"]:
            state["trades"][key] = {
                "leg": leg, "entry_time": entry_naive.isoformat(),
                "exit_time": exit_naive.isoformat(), "exit_reason": exit_reason,
                "r_multiple": r_mult, "notified_exit": exit_reason != "data_end",
            }
            messages.append(f"[FK Instant Funding] \U0001F7E2 ENTRY {LEG_LABELS[leg]} @ {t['entry_time']}")
        else:
            rec = state["trades"][key]
            rec["exit_time"], rec["exit_reason"], rec["r_multiple"] = exit_naive.isoformat(), exit_reason, r_mult
            if exit_reason != "data_end" and not rec.get("notified_exit", False):
                icon = "\U0001F7E2" if r_mult > 0 else "\U0001F534"
                messages.append(f"[FK Instant Funding] {icon} EXIT {LEG_LABELS[leg]} ({exit_reason}) R={r_mult:+.2f}")
                rec["notified_exit"] = True
    return messages


def _state_trades_df(state: dict) -> pd.DataFrame:
    rows = list(state["trades"].values())
    if not rows:
        return pd.DataFrame(columns=["leg", "entry_time", "exit_time", "r_multiple"])
    df = pd.DataFrame(rows)
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True).dt.tz_localize(None)
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True).dt.tz_localize(None)
    return df.dropna(subset=["r_multiple"])


# ------------------------------------------------------------------ gemeinsame Equity + Regel-Checks
def compute_shared_equity(state: dict) -> pd.DataFrame:
    """Baut die EINE gemeinsame, sequenziell kompoundierende Paper-Equity ueber
    ALLE Beine hinweg -- Trades chronologisch nach exit_time sortiert (nicht
    pro Bein getrennt), da alle Beine dasselbe Konto teilen. Wendet pro Trade
    die verduennte, GEDECKELTE Positionsgroessen-Formel an (siehe Docstring)."""
    trades = _state_trades_df(state).sort_values("exit_time").reset_index(drop=True)
    equity = STARTING_EQUITY
    rows = []
    for _, t in trades.iterrows():
        risk_uncapped = CAPITAL_WEIGHT * LEG_RISK_PCT[t["leg"]] * equity
        risk_dollars = min(risk_uncapped, MAX_POSITION_LOSS_DOLLARS)
        pnl = risk_dollars * t["r_multiple"]
        equity += pnl
        rows.append({"exit_time": t["exit_time"], "leg": t["leg"], "risk_dollars": risk_dollars,
                      "risk_capped": risk_uncapped > MAX_POSITION_LOSS_DOLLARS, "pnl": pnl, "equity": equity})
    return pd.DataFrame(rows)


def check_trailing_dd(equity_df: pd.DataFrame, eod_equity_state: dict, as_of: pd.Timestamp) -> tuple[bool, float, float]:
    """EOD-Trailing-Drawdown: Floor = 95% des bisherigen EOD-Hoechststands,
    bewegt sich nur nach oben. Nutzt den PERSISTIERTEN EOD-Verlauf (nicht nur
    die aktuell im State bekannten Trades), damit der Floor ueber Neustarts
    hinweg stabil bleibt. `as_of` statt pd.Timestamp.now() -- sonst wuerde ein
    historischer Dry-Run/Backtest-Aufruf faelschlich das ECHTE heutige Datum
    als EOD-Schluessel benutzen statt des simulierten Datums."""
    if equity_df.empty:
        return False, 0.0, STARTING_EQUITY
    today = as_of.normalize().isoformat()
    current_equity = float(equity_df["equity"].iloc[-1])
    eod_equity_state[today] = current_equity
    running_max = max([STARTING_EQUITY] + list(eod_equity_state.values()))
    floor = (1 - TRAILING_DD_PCT) * running_max
    breached = current_equity < floor
    current_dd = current_equity / running_max - 1
    return breached, current_dd, floor


def check_consistency(equity_df: pd.DataFrame) -> tuple[float, bool, float]:
    """Punkt-in-Zeit-Konsistenz-Check (siehe portfolio_construction.py-Tab
    'FK Instant Funding'): Verhaeltnis bester Einzeltag-Gewinn / kumulierter
    Gesamtgewinn JETZT, nicht kumulativ-jemals-gebrochen (ein Bruch verweigert
    laut Nutzer-Recherche nur die naechste Auszahlung, schliesst das Konto
    nicht -- daher Ampel-Status statt Kill-Switch)."""
    if equity_df.empty:
        return 0.0, True, 0.0
    daily_pnl = equity_df.groupby(equity_df["exit_time"].dt.normalize())["pnl"].sum()
    cum_profit = daily_pnl.sum()
    best_day = daily_pnl.max()
    if cum_profit <= 0:
        return 0.0, False, cum_profit  # keine Auszahlung moeglich, da (noch) kein Gewinn
    ratio = best_day / cum_profit
    payout_safe = ratio <= CONSISTENCY_CAP_PCT
    return float(ratio), payout_safe, float(cum_profit)


# ------------------------------------------------------------------ Haupt-Scan
def scan_once(as_of: pd.Timestamp | None = None, dry_run: bool = False, state_override: dict | None = None) -> tuple[dict, dict]:
    end = as_of if as_of is not None else pd.Timestamp.now(tz="UTC").tz_localize(None)
    if end.tzinfo is not None:
        end = end.tz_convert("UTC").tz_localize(None)
    state = dict(state_override) if state_override is not None else load_state()
    if "trades" not in state:
        state = _default_state()
    state.setdefault("eod_equity", {})

    messages = []
    try:
        gold_asb_trades = _scan_gold_asb(end, force_refresh=not dry_run)
        messages += _merge_trades(state, "gold_asb", gold_asb_trades)
    except Exception as e:
        messages.append(f"[FK Instant Funding] ⚠️ Gold-ASB-Scan fehlgeschlagen: {e}")

    try:
        cls_trades = _scan_cls_practical(end, force_refresh=not dry_run)
        messages += _merge_trades(state, "cls_practical", cls_trades)
    except Exception as e:
        messages.append(f"[FK Instant Funding] ⚠️ CLS-Practical-Scan fehlgeschlagen: {e}")

    try:
        tp_trades = _scan_trend_pullback(end, force_refresh=not dry_run)
        messages += _merge_trades(state, "trend_pullback", tp_trades)
    except Exception as e:
        messages.append(f"[FK Instant Funding] ⚠️ Trend-Pullback-Scan fehlgeschlagen: {e}")

    try:
        cont_trades, rev_trades = _scan_ctnl(end, force_refresh=not dry_run)
        messages += _merge_trades(state, "ctnl_continuation", cont_trades)
        messages += _merge_trades(state, "ctnl_reversal", rev_trades)
    except Exception as e:
        messages.append(f"[FK Instant Funding] ⚠️ CTNL-Edge-Scan fehlgeschlagen: {e}")

    try:
        gsd_trades = _scan_gold_silver(end, force_refresh=not dry_run)
        messages += _merge_trades(state, "gold_silver", gsd_trades)
    except Exception as e:
        messages.append(f"[FK Instant Funding] ⚠️ Gold-Silber-Divergenz-Scan fehlgeschlagen: {e}")

    equity_df = compute_shared_equity(state)
    dd_breached, current_dd, dd_floor = check_trailing_dd(equity_df, state["eod_equity"], end)
    consistency_ratio, payout_safe, cum_profit = check_consistency(equity_df)
    current_equity = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else STARTING_EQUITY

    if dd_breached and not state.get("kill_switch_active", False):
        state["kill_switch_active"] = True
        messages.append(
            f"[FK Instant Funding] \U0001F6A8 KILL-SWITCH: Trailing-Drawdown {current_dd:.2%} unter dem "
            f"5%-Floor (${dd_floor:,.0f}). Neue Entries pruefen/pausieren."
        )
    elif not dd_breached and state.get("kill_switch_active", False) and current_dd >= -TRAILING_DD_PCT * 0.5:
        state["kill_switch_active"] = False  # Erholung ueber die Haelfte der Schwelle - Reset

    row = {
        "date": str(end), "equity": current_equity, "current_dd": current_dd,
        "consistency_ratio": consistency_ratio, "payout_safe": payout_safe, "cum_profit": cum_profit,
        "kill_switch_active": state.get("kill_switch_active", False), "n_trades": len(state["trades"]),
    }

    current_hour_key = end.strftime("%Y-%m-%d %H")
    if state.get("last_heartbeat_hour") != current_hour_key:
        state["last_heartbeat_hour"] = current_hour_key
        payout_label = "ZULAESSIG" if payout_safe else "NICHT zulaessig (Verhaeltnis > 30%)"
        heartbeat_msg = (
            f"[FK Instant Funding] Stuendlicher Status {end.strftime('%Y-%m-%d %H:%M')}\n"
            f"Equity: ${current_equity:,.0f}  |  Trailing-DD: {current_dd:.2%} (Floor ${dd_floor:,.0f})  |  "
            f"Trades: {len(state['trades'])}  |  Kill-Switch: {'AKTIV' if state['kill_switch_active'] else 'ok'}\n"
            f"Konsistenz-Verhaeltnis: {consistency_ratio:.1%}  |  Auszahlung: {payout_label}"
        )
        if not dry_run:
            send_telegram_message(heartbeat_msg)
            LOG_DIR.mkdir(exist_ok=True)
            is_new = not HEARTBEAT_CSV.exists()
            with open(HEARTBEAT_CSV, "a", encoding="utf-8") as f:
                if is_new:
                    f.write("date,equity,current_dd,consistency_ratio,payout_safe,kill_switch_active,n_trades\n")
                f.write(f"{end.isoformat()},{current_equity:.2f},{current_dd:.4f},{consistency_ratio:.4f},"
                        f"{payout_safe},{state['kill_switch_active']},{len(state['trades'])}\n")

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
