"""Challenge-Portfolio - Paper-Forward-Test-Bot fuer TTP und IQ Markets/"I Capital"
(2026-08-27).

NICHT der echte Order-Ausfuehrer. Getrennt von den bereits live laufenden
Solo-Bots (OU-Modell-MT5-Bridge auf den echten TTP-Konten konto1_ttp/
konto2_ttp, CTNL-Edge-MT5-Bridge auf dem echten BeyondIQCapital/IQ-Markets-
Konto) -- ruehrt an KEINER Stelle deren Order-Ausfuehrung an. Dieser Bot ist
reine Paper-Simulation + Telegram-Alerts fuer den vollen 6-Bein-FK-Blend
(Gold ASB, CLS Practical, Trend Pullback, CTNL Edge [Continuation+Reversal],
OU-Modell [TTP-handelbare Teilmenge], NY-Open ORB [SP500+US30+NASDAQ]) auf
ZWEI virtuellen 100k-Konten -- eines je Zielfirma/Regelwerk -- bis eine
bewusste, separate Entscheidung fuer echte Order-Ausfuehrung getroffen wird.
Architektur-Vorbild: fk_instant_funding/paper_bot.py (das selbst gold_smc_htf_
ltf/paper_bot.py als Vorbild nennt).

Roster/Risikostufen aus scripts/research_challenge_portfolio_6leg.py
(2026-08-27, portfolio_construction/results/challenge_portfolio_6leg.json):
6 Beine gleichgewichtet (1/6 Kapitalanteil je Bein) schlagen die 5-Bein-
Baseline OHNE ORB auf BEIDEN Regelwerken gleichzeitig (hoehere CAGR,
niedrigerer MaxDD, niedrigere Bruchwahrscheinlichkeit, schnelleres Ziel) --
siehe JSON fuer die vollen Zahlen. ORB war zuvor bewusst ausgeschlossen
("keine Evidenz, dass TTP/IQ Markets die Instrumente anbieten") -- auf
Nutzerwunsch (2026-08-27) jetzt aufgenommen, Broker-Verfuegbarkeit bleibt vor
echtem Livegang zu pruefen.

Beide Konten sehen DIESELBEN Trades (identischer Signal-Strom, identische
Kapitalanteil-Verduennungsformel: risk_dollars = CAPITAL_WEIGHT (1/6) x
internes Risiko/Trade x aktuelle SHARED-Equity, gedeckelt auf 1% des
STARTKAPITALS -- erfuellt IQ Markets' explizite 1%-Positionsgrenze strukturell,
nicht nur zufaellig) -- ein einziger gemeinsamer Trade-Log/Equity-Verlauf
reicht deshalb; NUR die Regel-Auswertung (Tageslimit/Gesamt-Drawdown/
Zielschwelle) unterscheidet sich je Konto:

  - TTP:       Tageslimit -3% (Tages-Reset, pausiert NEUE Entries fuer den
               Rest des Handelstags), Gesamt-Drawdown -7% (harter, manuell
               zurueckzusetzender Kill-Switch), Ziel +10%.
  - IQ Markets: kein Tageslimit, Gesamt-Drawdown -6% (harter Kill-Switch),
               Ziel +8%. Positionslimit 1% strukturell erfuellt (s.o.).

Jeder Scan laesst die ECHTEN, bereits validierten Signal-Engines jeder
Strategie frisch auf einem strategie-eigenen Trailing-Fenster laufen (keine
Logik-Duplizierung), gleicht das Ergebnis gegen den PERSISTIERTEN
Trade-Verlauf ab (challenge_portfolio_logs/paper_state.json) und baut daraus
EINE gemeinsame, sequenziell kompoundierende Paper-Equity-Kurve, gegen die
BEIDE Regelwerke unabhaengig ausgewertet werden."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from challenge_portfolio.telegram_notify import send_telegram_message
from strategy.backtest import BacktestConfig, simulate_trades


def _retry(fn, attempts: int = 3, delay_seconds: float = 5.0):
    """dukascopy_python's Streaming-Client wirft gelegentlich ein KeyError(0)
    tief in seiner eigenen _stream()-Cursor-Logik, wenn end nah an "jetzt"
    liegt -- bekannte Instabilitaet der Drittanbieter-Bibliothek, kein Fehler
    in unserem Code (identisches Muster wie fk_instant_funding/paper_bot.py).
    Ein einfacher Retry reicht empirisch aus."""
    last_exc = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < attempts - 1:
                time.sleep(delay_seconds)
    raise last_exc


REPO_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_DIR / "challenge_portfolio_logs"
STATE_PATH = LOG_DIR / "paper_state.json"
HEARTBEAT_CSV = LOG_DIR / "heartbeat.csv"

STARTING_EQUITY = 100_000.0  # Platzhalter je virtuellem Konto -- vor echtem Livegang auf die reale Kontogroesse setzen
CAPITAL_WEIGHT = 1 / 6  # 6 gleichgewichtete Beine (CTNL teilt sich EIN Bein ueber Continuation+Reversal,
# ORB teilt sich EIN Bein ueber SP500/US30/NASDAQ -- siehe ORB_RISK_PCT_PER_INSTRUMENT unten)
MAX_POSITION_RISK_PCT = 0.01  # von der AKTUELLEN Kontoequity (Nutzerauftrag 2026-09-01: "in jedem Fall 1% der
# aktuellen Kontogroesse") -- IMMER live gegen die Equity zum Trade-Zeitpunkt gerechnet (siehe
# compute_shared_equity()/Funded-Portfolio-Bridge/run_once.py::_process_leg()), NICHT gegen einen fixen
# Dollarbetrag. Ein frueherer fixer MAX_POSITION_RISK_DOLLARS-Deckel (STARTING_EQUITY x 1%) wurde entfernt --
# er blieb bei wachsender/schrumpfender Equity stur auf dem $100k-Platzhalter stehen, war also NICHT wirklich
# "1% der aktuellen Kontogroesse" (Review-Fund 2026-09-01).

ORB_COMBINED_RISK_PCT = 0.01  # "ORB Portfolio"-Bein gesamt, gleichgewichtet ueber 3 Instrumente
ORB_RISK_PCT_PER_INSTRUMENT = ORB_COMBINED_RISK_PCT / 3
LEG_RISK_PCT = {
    "gold_asb": 0.02,
    "cls_practical": 0.015,
    "trend_pullback": 0.005,
    "ctnl_continuation": 0.005,
    "ctnl_reversal": 0.0015,
    "ou_modell": 0.01,
    "orb_sp500": ORB_RISK_PCT_PER_INSTRUMENT,
    "orb_us30": ORB_RISK_PCT_PER_INSTRUMENT,
    "orb_nasdaq": ORB_RISK_PCT_PER_INSTRUMENT,
}
LEG_LABELS = {
    "gold_asb": "Gold ASB", "cls_practical": "CLS Practical", "trend_pullback": "Trend Pullback",
    "ctnl_continuation": "CTNL Continuation", "ctnl_reversal": "CTNL Reversal", "ou_modell": "OU-Modell (TTP-Teilmenge)",
    "orb_sp500": "NY-Open ORB (SP500)", "orb_us30": "NY-Open ORB (US30)", "orb_nasdaq": "NY-Open ORB (NASDAQ)",
}

RULES = {
    "ttp": {"daily_loss_cap": 0.03, "total_dd_cap": 0.07, "target_gain": 0.10, "label": "TTP"},
    "iqmarkets": {"daily_loss_cap": None, "total_dd_cap": 0.06, "target_gain": 0.08, "label": "IQ Markets"},
}

# Telegram-Struktur (2026-08-31, Nutzerwunsch: "dieselbe Telegram Anbindung
# wie fuer die anderen beiden Portfolios") -- identisches Muster zu
# fk_instant_funding/paper_bot.py::_fk_message + EK-Portfolio-Bridge/core/
# telegram_format.py: fester Banner, ALLE Ereignisse EINES Laufs zu EINER
# "Scan-Update"-Nachricht gebuendelt statt je Bein einzeln, plus EIN
# taeglicher Tagesabschluss statt stuendlicher Routine-Nachrichten. Zwei
# Konten -> zwei getrennte Banner/Nachrichtenstroeme ("TTP Challenge" / "IQ
# Challenge", siehe Nutzervorgabe), auch wenn beide denselben Trade-Strom
# sehen (gemeinsame Entry/Exit-Zeilen landen in BEIDEN Nachrichten -- jedes
# Konto erlebt dieselben Trades unabhaengig, nur die Regel-Auswertung
# unterscheidet sich).
_RULE = "─" * 24
_CHALLENGE_TITLES = {"ttp": "TTP Challenge", "iqmarkets": "IQ Challenge"}
LOCAL_TZ = "Europe/Berlin"
DAILY_SUMMARY_HOUR = 21  # echte lokale Zeit -- NIE direkt gegen UTC-Stunde vergleichen (siehe
# _local_dt()-Docstring, realer Bug in fk_instant_funding/paper_bot.py am 2026-08-29 gefunden)


def _challenge_message(rule_key: str, subtitle: str, body_lines: list[str] | None = None) -> str:
    header = f"\U0001F3E6 {_CHALLENGE_TITLES[rule_key].upper()}\n{_RULE}\n{subtitle}"
    if body_lines:
        return header + "\n\n" + "\n".join(body_lines)
    return header


def _local_dt(end: pd.Timestamp) -> pd.Timestamp:
    """`end` ist im ganzen Modul UTC-naiv -- fuer die Tagesabschluss-Stunden-
    Entscheidung muss das nach ECHTER lokaler Zeit umgerechnet werden, sonst
    verschiebt sich die Schwelle um den UTC-Offset (+1/+2h)."""
    return end.tz_localize("UTC").tz_convert(LOCAL_TZ)


def _record_scan_error(state: dict, day: str, leg: str) -> None:
    """Fuer die Gesundheits-Zeile im taeglichen Tagesabschluss -- ein
    fehlgeschlagener Scan loest KEINEN Sofort-Alarm mehr aus, taucht aber im
    Tagesabschluss auf (identisches Muster zu Funded-Portfolio-Bridge/
    run_once.py::_record_scan_error)."""
    day_errors = state.setdefault("scan_errors_today", {}).setdefault(day, {})
    day_errors[leg] = day_errors.get(leg, 0) + 1


def _utc_naive(x):
    """Jede Strategie liefert Zeitstempel in einer ANDEREN Zeitzone-Konvention
    -- ohne Normalisierung crasht jeder Vergleich mit dem tz-naiven `end`
    (identisches Muster wie fk_instant_funding/paper_bot.py)."""
    if isinstance(x, pd.DatetimeIndex):
        return x.tz_convert("UTC").tz_localize(None) if x.tz is not None else x
    s = pd.to_datetime(x, utc=True)
    return s.dt.tz_localize(None) if hasattr(s, "dt") else s.tz_localize(None)


def _default_state() -> dict:
    return {
        "trades": {}, "account_start": None, "scan_errors_today": {},
        "ttp": {"eod_equity": {}, "kill_switch_active": False, "daily_paused": False, "target_reached": False,
                "last_daily_summary_day": None},
        "iqmarkets": {"kill_switch_active": False, "target_reached": False, "last_daily_summary_day": None},
    }


def load_state() -> dict:
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        for key, default in _default_state().items():
            state.setdefault(key, default)
        return state
    return _default_state()


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


# ------------------------------------------------------------------ per-leg Signal-Scans
# Jede Funktion laesst die ECHTE, bereits validierte Engine der Strategie auf
# einem eigenen Trailing-Fenster laufen und liefert eine Trades-DataFrame mit
# mindestens entry_time/exit_time/r_multiple/exit_reason -- identisch zum
# Backtest, keine zweite Implementierung der Entry/Exit-Regeln. Gold ASB, CLS
# Practical, Trend Pullback, CTNL und ORB sind 1:1 aus fk_instant_funding/
# paper_bot.py uebernommen (dort bereits validiert) -- nur OU-Modell ist neu,
# da FK Instant Funding dieses Bein nicht enthaelt.

GOLD_ASB_HISTORY_START = "2016-01-01"  # identisch zu app_pages/asian_range_breakout.py START -- die
# Liquiditaets-Filterschwelle ist eine EXPANDING Quantile ueber die volle Historie (min_periods=250
# Handelstage); ein kuerzeres Trailing-Fenster wuerde eine andere Schwelle berechnen als der echte Bot.
GOLD_ASB_ADX_MIN = 15.0
GOLD_ASB_TREND_SMA_WINDOW = 200
GOLD_ASB_SILVER_ALIGNMENT_WINDOW = 5
GOLD_ASB_LIQUIDITY_QUANTILE = 2 / 3
GOLD_ASB_LIQUIDITY_MIN_PERIODS = 250
GOLD_ASB_MAX_DELAY_BARS = 3


def _scan_gold_asb(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    from asian_range_breakout.data import fetch_gold_m15
    from asian_range_breakout.engine import simulate_asian_breakout
    from asian_range_breakout.filters import (
        apply_adx_filter, apply_entry_delay_filter, apply_gold_liquidity_filter_causal,
        apply_silver_alignment_filter, apply_trend_bias_filter,
    )
    from asian_range_breakout.sizing import simulate_equity
    from bond_yield_indicator.friction import fetch_fx_friction
    from combined_strategy.data import fetch_timeframe

    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    stable_end_str = (end.normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    def _concat_fresh(old: pd.DataFrame | pd.Series, new: pd.DataFrame | pd.Series):
        if old.empty:
            return new
        if new.empty:
            return old
        combined = pd.concat([old, new])
        return combined[~combined.index.duplicated(keep="last")].sort_index()

    gold_m15_old = fetch_gold_m15(GOLD_ASB_HISTORY_START, stable_end_str, force_refresh=False)
    gold_m15_new = fetch_gold_m15(stable_end_str, end_str, force_refresh=force_refresh)
    df = _concat_fresh(gold_m15_old, gold_m15_new)
    if df.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])
    trades = simulate_asian_breakout(df)
    if trades.empty:
        return trades

    daily_close = df["close"].tz_localize(None).resample("D").last().dropna()
    silver_m15_old = fetch_timeframe("SILVER", "M15", GOLD_ASB_HISTORY_START, stable_end_str, force_refresh=False)
    silver_m15_new = fetch_timeframe("SILVER", "M15", stable_end_str, end_str, force_refresh=force_refresh)
    silver_m15 = _concat_fresh(silver_m15_old, silver_m15_new)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()
    gold_friction_old = fetch_fx_friction("GOLD", GOLD_ASB_HISTORY_START, stable_end_str, force_refresh=False)
    gold_friction_new = fetch_fx_friction("GOLD", stable_end_str, end_str, force_refresh=force_refresh)
    gold_friction = _concat_fresh(gold_friction_old, gold_friction_new)

    trades = apply_adx_filter(trades, adx_min=GOLD_ASB_ADX_MIN)
    trades = apply_trend_bias_filter(trades, daily_close, sma_window=GOLD_ASB_TREND_SMA_WINDOW)
    trades = apply_entry_delay_filter(trades, max_delay_bars=GOLD_ASB_MAX_DELAY_BARS)
    trades = apply_silver_alignment_filter(trades, daily_close_silver, window=GOLD_ASB_SILVER_ALIGNMENT_WINDOW)
    trades = apply_gold_liquidity_filter_causal(
        trades, gold_friction, quantile=GOLD_ASB_LIQUIDITY_QUANTILE, min_periods=GOLD_ASB_LIQUIDITY_MIN_PERIODS
    )
    if trades.empty:
        return trades
    trades = simulate_equity(trades, starting_equity=100_000.0, risk_pct=0.005)
    trades = trades[_utc_naive(trades["entry_time"]) <= end]
    return trades


def _scan_cls_practical(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    from cls_practical.data import fetch_2y_yield_daily, fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
    from cls_practical.engine import simulate_cls_practical
    from cls_practical.rates import compute_combined_rate_risk_multiplier
    from strategy.cls_advanced import PAIRS

    other_majors = [p for p in PAIRS if p != "EURUSD"]
    start = (end - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
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
    trades = trades.copy()
    sign = trades["direction"].map({"long": 1, "short": -1})
    raw_r = sign * (trades["exit_price"] - trades["entry_price"]) / trades["sl_distance"]
    rate_mult = trades["date"].map(lambda d: combined_mult.get(d, 1.0))
    trades["r_multiple"] = raw_r * rate_mult
    trades = trades[_utc_naive(trades["entry_time"]) <= end]
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
    start = (end - pd.Timedelta(days=300)).strftime("%Y-%m-%d")
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


def _cap_concurrent_reversals(rev_trades: pd.DataFrame, max_concurrent: int) -> pd.DataFrame:
    """simulate_trades_concurrent() erzwingt KEIN Limit gleichzeitig offener
    Positionen -- das reale REV_MAX_CONCURRENT-Limit lebt nur in der
    Ausfuehrungsschicht (gold_smc_htf_ltf/live_signal.py-Docstring,
    EK-Portfolio-Bridge/legs/ctnl_edge/executor.py::check_and_execute_
    reversal). Ohne diese Kappung ueberzeichnet der Paper-Bot systematisch,
    was real ausfuehrbar gewesen waere (Fund 2026-08-31, zuerst in
    fk_instant_funding/paper_bot.py behoben, hier auf Nutzerwunsch 2026-09-01
    identisch uebernommen). Greedy-Kappung nach Entry-Zeit: ein Trade wird
    verworfen, wenn zu seinem Entry-Zeitpunkt bereits max_concurrent andere
    (nach ihrer Exit-Zeit) noch offene Reversal-Trades laufen -- exakt die
    Regel, die eine echte Bridge angewendet haette."""
    if rev_trades.empty:
        return rev_trades
    entry_naive = _utc_naive(rev_trades["entry_time"])
    exit_naive = _utc_naive(rev_trades["exit_time"])
    open_exits: list[pd.Timestamp] = []
    keep_idx = []
    for idx in entry_naive.sort_values().index:
        e, x = entry_naive.loc[idx], exit_naive.loc[idx]
        open_exits = [t for t in open_exits if t > e]
        if len(open_exits) >= max_concurrent:
            continue
        open_exits.append(x)
        keep_idx.append(idx)
    return rev_trades.loc[keep_idx].sort_index()


def _scan_ctnl(end: pd.Timestamp, force_refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent
    from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
    from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m15, fetch_gold_m5
    from gold_smc_htf_ltf.live_signal import CONT_KWARGS, LOOKBACK_DAYS, REV_KWARGS, REV_MAX_CONCURRENT
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
    rev_trades = _cap_concurrent_reversals(rev_trades, REV_MAX_CONCURRENT)
    return cont_trades, rev_trades


# Per-Instrument (2026-09-02, gleicher Stand wie app_pages/ny_open_orb_portfolio.py::
# EXIT_CFG_BY_INSTRUMENT NACH dem NASDAQ-EOD-Exit-Update): NASDAQ laesst die Position
# jetzt bis Handelsschluss laufen (target_mode=None) statt zum 4R-Cap, siehe
# knowledge/projects/ny-open-orb-sp500.md Stage 8/9. SP500/US30 unveraendert.
# ABSICHTLICH (noch) OHNE Stage-6-Teilausstieg (partial_exit_r/-fraction/move_stop_
# to_be_after_partial): _process_leg() in Funded-Portfolio-Bridge/run_once.py kennt nur
# EIN offen/geschlossen pro Position (ein Ticket, eine volle Groesse, ein Schluss-Call)
# -- es gibt dort keine Zwischen-Verwaltung, die einen Teil einer echten Position bei
# 1.5R schliessen und den Rest-Stop auf Breakeven verschieben koennte. Wuerde man
# partial_exit_* hier trotzdem setzen, wuerde simulate() intern einen sauberen
# geblendeten Teilausstieg-Trade fuer die PAPIER-Nachverfolgung berechnen, aber die
# ECHTE Position bliebe die GANZE Zeit in voller Groesse gegen den urspruenglichen Stop
# offen -- Papier-P&L und echtes Broker-P&L wuerden auseinanderlaufen, ohne dass das im
# Log sichtbar waere. Braucht echte neue Verwaltungslogik in run_once.py/executor.py
# (Ticket-Teilschliessung + SL-Modify), keine reine Config-Aenderung -- nicht Teil
# dieser Umstellung, siehe DASHBOARD.md.
ORB_EXIT_CFG_BY_INSTRUMENT = {
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode=None),
}
ORB_HISTORY_LOOKBACK_DAYS = 500  # EMA-Ribbon-Bias (4H/1D/1W) braucht Monate an Vorlauf


def _scan_orb(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    from ny_open_orb import filters, regime
    from ny_open_orb.data import fetch_m5, fetch_m15
    from ny_open_orb.engine import build_frame, find_entries, simulate

    start = (end - pd.Timedelta(days=ORB_HISTORY_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    all_trades = []
    for instrument in ["SP500", "US30", "NASDAQ"]:
        m15 = fetch_m15(instrument, start, end_str, force_refresh=force_refresh)
        m5 = fetch_m5(instrument, start, end_str, force_refresh=force_refresh)
        if m15.empty or m5.empty:
            continue
        frame = build_frame(m15, m5, range_bars=1)
        all_entries = find_entries(frame, "stop_breakout")
        if all_entries.empty:
            continue

        if instrument == "NASDAQ":
            entries = filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
        else:
            long_entries = filters.filter_by_direction(all_entries, 1)
            bias = regime.ema_trend_bias(m15, frame["session"].unique())
            bias_vals = filters.values_at(long_entries, bias)
            entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))
        if entries.empty:
            continue

        trades = simulate(frame, entries, **ORB_EXIT_CFG_BY_INSTRUMENT[instrument])
        if trades.empty:
            continue
        trades = trades[_utc_naive(trades["entry_time"]) <= end].copy()
        if trades.empty:
            continue

        session_close_naive = _utc_naive(frame["session_close"])
        for idx in trades.index[trades["exit_reason"] == "session_end"]:
            entry_t = trades.loc[idx, "entry_time"]
            if entry_t not in session_close_naive.index:
                continue
            if session_close_naive.loc[entry_t] > end:
                trades.loc[idx, "exit_reason"] = "data_end"

        trades["market"] = instrument
        all_trades.append(trades)

    if not all_trades:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason", "market"])
    return pd.concat(all_trades, ignore_index=True)


OU_MODELL_LOOKBACK_DAYS = 450  # 20d-Bollinger + 200d-EMA-Regimefilter-Warmup + Puffer, gleiche Konvention wie
# ou_paper_backtest/scanner.py::_refresh_universe_prices (400 Tage dort fuer eine reine Punkt-in-Zeit-Signal-
# Pruefung; hier etwas mehr, da eine volle Trailing-Trade-Simulation laeuft statt nur der letzte Tag)
OU_MODELL_MARKETS = ("sp500", "nasdaq100")  # DAX strukturell 0 TTP-handelbare Ticker, siehe scanner.py
OU_MODELL_STOP_SIGMA = 3.0
# 2026-09-02: von der reinen "gesperrten Baseline" (be=0.25R, kein TP) auf die zuletzt live auf
# Konto 2 (TTP, OU-Modell-MT5-Bridge, bis 2026-09-01) gefahrene, dort ueber den 2025er-Holdout
# validierte Konfiguration umgestellt (siehe ou_paper_backtest/results/sp500/oos_holdout_
# challenge_profiles_ttp_universe.csv, Zeile "konto2_aktuell_tp1.5_0.25pct_5pct_be0.35": schlechtester
# Einzeltag -1.31% -- deutlich unter der 3%-Tagesverlust-Regel -- bei MaxDD -5.1%, und erreicht das
# 10%-Ziel ~200 Tage frueher als die alte No-TP-Config bei aehnlichem Risiko). Nur die Exit-Logik
# uebernommen (be_trigger_r, max_total_risk_pct-Gate, TP), NICHT das reale Order-Sizing -- die
# 1/6-Kapitalgewichtung dieses Beins macht das reale Risiko/Trade schon konservativer (0.167%) als
# Konto 2s eigenstaendige 0.25%, das bleibt bewusst unangetastet (Nutzerentscheidung 2026-09-02).
OU_MODELL_BE_TRIGGER_R = 0.35
OU_MODELL_RISK_PCT = 0.01
OU_MODELL_MAX_TOTAL_RISK_PCT = 0.05


def _import_ou_paper_backtest():
    """ou_paper_backtest/{config,portfolio,scanner}.py verwenden intern
    NACKTE 'import config'-Anweisungen (kein Package) -- ueber sys.path
    eingebunden kollidiert das mit jedem GLEICHNAMIGEN Modul, das der
    Aufrufer selbst schon geladen hat, weil Python sys.modules['config'] nur
    EINMAL pro Prozess befuellt. Real aufgetreten (2026-08-29): eine MT5-
    Bridge mit eigener config.py (import config VOR dem Aufruf dieser
    Funktion) bekam ou_paper_backtest/portfolio.py's eigenes 'import config'
    faelschlich die BRIDGE-config zurueck -> AttributeError (fehlendes
    INITIAL_EQUITY). Fix: config/portfolio/scanner unter EINDEUTIGEN
    sys.modules-Schluesseln frisch laden (importlib), waehrend 'config'
    dort NUR WAEHREND DES LADENS temporaer auf die ou_paper_backtest-eigene
    Instanz zeigt (portfolio.py/scanner.py brauchen das fuer ihr eigenes
    bare-import), danach den vorherigen Zustand des Aufrufers wiederherstellen
    -- der Aufrufer bekommt alle drei Module unter eigenen Namen zurueck,
    sein eigenes 'config' bleibt unangetastet."""
    import importlib.util

    def _load(mod_name: str, file_path: Path):
        spec = importlib.util.spec_from_file_location(mod_name, file_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        return mod

    ou_dir = REPO_DIR / "ou_paper_backtest"
    prior_config = sys.modules.get("config")
    try:
        ou_config = _load("_ou_paper_backtest_config", ou_dir / "config.py")
        sys.modules["config"] = ou_config  # portfolio.py/scanner.py's eigenes "import config" braucht das
        ou_portfolio = _load("_ou_paper_backtest_portfolio", ou_dir / "portfolio.py")
        ou_scanner = _load("_ou_paper_backtest_scanner", ou_dir / "scanner.py")
    finally:
        if prior_config is not None:
            sys.modules["config"] = prior_config
        else:
            sys.modules.pop("config", None)
    return ou_config, ou_portfolio, ou_scanner._load_ttp_tradable_tickers


def _scan_ou_modell(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    """OU-Modell, TTP-handelbare Teilmenge (SP500+Nasdaq100, DAX raus -- 0
    Ticker dort ueberhaupt handelbar, siehe ou_paper_backtest/scanner.py::
    _load_ttp_tradable_tickers). Bracket-Exit-Engine (portfolio.py::
    simulate_bracket_portfolio) statt der reinen Punkt-in-Zeit-Scanner-Logik,
    da diese Funktion -- wie alle anderen Beine hier -- eine volle Trades-
    DataFrame mit r_multiple liefern muss, nicht nur das juengste Tages-
    Signal. Konfiguration (stop_sigma=3.0, be_trigger_r=0.25, kein TP) ist die
    ueber viele Skripte hinweg als "gesperrte Baseline" referenzierte Config
    (siehe ou_paper_backtest/oos_holdout_challenge_profiles.py).

    simulate_bracket_portfolio()'s Trades-Liste enthaelt kein r_multiple direkt
    (nur pnl_dollars/pnl_pct relativ zur EIGENEN internen Equity-Annahme dieser
    Simulation) -- wie bei Gold ASB/CLS Practical eigenstaendig aus Entry/Exit-
    Preis + derselben Stop-Distanz-Formel hergeleitet, die auch die Positions-
    groesse bestimmt hat (stop_sigma * rollierende 20-Tage-Std zum Entry-Datum),
    damit r_multiple unabhaengig von dieser Simulation eigener Equity-Groesse
    bleibt -- exakt dieselbe Notwendigkeit wie bei den anderen Beinen."""
    import yfinance as yf

    ou_config, ou_portfolio, _load_ttp_tradable_tickers = _import_ou_paper_backtest()

    start = (end - pd.Timedelta(days=OU_MODELL_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    all_trades = []
    for market_key in OU_MODELL_MARKETS:
        ou_table = pd.read_csv(ou_config.RESULTS_DIR / market_key / "ou_parameters_in_sample.csv", index_col=0)
        sel = ou_table[
            (ou_table["theta"] > ou_config.THETA_MIN) & (ou_table["p_value"] < ou_config.PVALUE_MAX)
            & (ou_table["half_life"].between(ou_config.HALFLIFE_MIN, ou_config.HALFLIFE_MAX))
        ]
        tickers = sel.index.tolist()
        tradable = _load_ttp_tradable_tickers(market_key)
        if tradable is not None:
            tickers = [t for t in tickers if t in tradable]
        if not tickers:
            continue

        panel = {}
        for t in tickers:
            df = yf.download(t, start=start, end=end_str, auto_adjust=True, progress=False)
            if df is None or df.empty:
                continue
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            panel[t] = close.dropna()
        if not panel:
            continue
        panel_df = pd.DataFrame(panel).sort_index()

        bench_ticker = ou_config.UNIVERSES[market_key]["benchmark"]
        bench_df = yf.download(bench_ticker, start=start, end=end_str, auto_adjust=True, progress=False)
        benchmark = bench_df["Close"]
        if isinstance(benchmark, pd.DataFrame):
            benchmark = benchmark.iloc[:, 0]
        regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel_df.index).ffill().fillna(False)

        today_str = panel_df.index.max().date().isoformat()
        # 2026-09-02: TP=1:1.5R nur fuer S&P (identisch zu ou_paper_backtest/scanner.py::scan_market's
        # Einschraenkung) -- bewusst NICHT auf Nasdaq/DAX uebertragen, da dort nie validiert.
        rr_ratio = 1.5 if market_key == "sp500" else None
        # Fund 2026-09-02 (Root Cause, nicht nur Config): simulate_bracket_portfolio() liess bis eben
        # jede noch OFFENE Position beim Rueckgabe-Zeitpunkt STILLSCHWEIGEND unter den Tisch fallen --
        # nur tatsaechlich GESCHLOSSENE Trades landeten in `trades`. Dieses Bein konnte dadurch
        # STRUKTURELL nie ein aktuell offenes/handelbares Signal an Funded-Portfolio-Bridge melden,
        # unabhaengig davon, ob die OU-Kriterien gerade zutrafen -- jede erkannte Zeile hatte immer
        # einen konkreten exit_reason (nie "data_end"), _process_leg() sah sie deshalb immer nur als
        # "verpasst" (laengst geschlossen), nie als neuen Entry. `include_open_positions=True` behebt
        # das (siehe portfolio.py-Docstring).
        _, trades = ou_portfolio.simulate_bracket_portfolio(
            panel_df, tickers, start, today_str, stop_sigma=OU_MODELL_STOP_SIGMA, rr_ratio=rr_ratio,
            be_trigger_r=OU_MODELL_BE_TRIGGER_R, allowed_directions=(1,), regime_filter=regime,
            risk_pct=OU_MODELL_RISK_PCT, max_total_risk_pct=OU_MODELL_MAX_TOTAL_RISK_PCT,
            include_open_positions=True,
        )
        if not trades:
            continue

        std20 = panel_df.rolling(ou_config.BB_LOOKBACK).std()
        rows = []
        for t in trades:
            ticker, entry_date, exit_date = t["ticker"], t["entry_date"], t["exit_date"]
            if entry_date not in std20.index or ticker not in std20.columns:
                continue
            std_at_entry = std20.loc[entry_date, ticker]
            if pd.isna(std_at_entry) or std_at_entry == 0:
                continue
            stop_distance = OU_MODELL_STOP_SIGMA * std_at_entry
            sign = 1 if t["direction"] == "long" else -1
            r_multiple = sign * (t["exit_price"] - t["entry_price"]) / stop_distance
            rows.append({
                "entry_time": entry_date, "exit_time": exit_date, "r_multiple": r_multiple,
                "exit_reason": t["reason"], "market": ticker, "direction": t["direction"],
                "entry_price": float(t["entry_price"]), "sl": float(t["entry_price"] - sign * stop_distance),
            })
        if rows:
            all_trades.append(pd.DataFrame(rows))

    if not all_trades:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason", "market"])
    combined = pd.concat(all_trades, ignore_index=True)
    combined = combined[_utc_naive(combined["entry_time"]) <= end]
    return combined


# ------------------------------------------------------------------ State-Merge (Muster: fk_instant_funding/paper_bot.py)
def _merge_trades(state: dict, leg: str, trades: pd.DataFrame) -> list[str]:
    messages = []
    for _, t in trades.iterrows():
        if pd.isna(t.get("r_multiple", np.nan)):
            continue
        entry_naive = _utc_naive(t["entry_time"])
        exit_naive = _utc_naive(t["exit_time"])
        direction_raw = t.get("direction", 1)
        direction_key = direction_raw if pd.notna(direction_raw) else 1
        market_key = t.get("market", "")
        key = f"{leg}_{market_key}_{entry_naive.isoformat()}_{direction_key}"
        exit_reason = t.get("exit_reason", "data_end")
        r_mult = float(t["r_multiple"])

        if key not in state["trades"]:
            state["trades"][key] = {
                "leg": leg, "entry_time": entry_naive.isoformat(),
                "exit_time": exit_naive.isoformat(), "exit_reason": exit_reason,
                "r_multiple": r_mult, "notified_exit": exit_reason != "data_end",
            }
            messages.append(f"\U0001F7E2 ENTRY {LEG_LABELS[leg]} @ {t['entry_time']}")
        else:
            rec = state["trades"][key]
            rec["exit_time"], rec["exit_reason"], rec["r_multiple"] = exit_naive.isoformat(), exit_reason, r_mult
            if exit_reason != "data_end" and not rec.get("notified_exit", False):
                icon = "\U0001F7E2" if r_mult > 0 else "\U0001F534"
                messages.append(f"{icon} EXIT {LEG_LABELS[leg]} ({exit_reason}) R={r_mult:+.2f}")
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


# ------------------------------------------------------------------ gemeinsame Equity (beide Konten identisch)
def compute_shared_equity(state: dict) -> pd.DataFrame:
    """Beide virtuellen Konten (TTP-Paper, IQMarkets-Paper) sehen dieselben
    Trades UND dieselbe Positionsgroessen-Formel -- ein gemeinsamer Equity-
    Verlauf reicht, nur die Regel-Auswertung unten unterscheidet sich je Konto."""
    trades = _state_trades_df(state).sort_values("exit_time").reset_index(drop=True)
    equity = STARTING_EQUITY
    rows = []
    for _, t in trades.iterrows():
        risk_uncapped = CAPITAL_WEIGHT * LEG_RISK_PCT[t["leg"]] * equity
        max_position_risk_dollars = MAX_POSITION_RISK_PCT * equity  # 1% der AKTUELLEN (simulierten) Equity, nicht STARTING_EQUITY
        risk_dollars = min(risk_uncapped, max_position_risk_dollars)
        pnl = risk_dollars * t["r_multiple"]
        equity += pnl
        rows.append({"exit_time": t["exit_time"], "leg": t["leg"], "risk_dollars": risk_dollars,
                      "risk_capped": risk_uncapped > max_position_risk_dollars, "max_position_risk_dollars": max_position_risk_dollars,
                      "pnl": pnl, "equity": equity})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ Regel-Checks (je Zielfirma unterschiedlich)
def _total_dd(equity_df: pd.DataFrame, current_equity: float) -> float:
    if equity_df.empty:
        return 0.0
    peak = max(STARTING_EQUITY, equity_df["equity"].cummax().iloc[-1])
    return current_equity / peak - 1.0


def check_ttp_rules(equity_df: pd.DataFrame, ttp_state: dict, as_of: pd.Timestamp) -> dict:
    """Tageslimit -3% (Tages-Reset, pausiert NEUE Entries fuer den Rest des
    Handelstags -- vergleicht EOD-Equity mit dem letzten ABGESCHLOSSENEN
    Vortag, nicht mit einem trailing Hoechststand) UND Gesamt-Drawdown -7%
    (harter, gegen den ALLZEIT-Hoechststand seit Kontostart gemessener
    Kill-Switch -- KEIN automatischer Reset, anders als das Tageslimit)."""
    current_equity = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else STARTING_EQUITY
    today = as_of.normalize().isoformat()
    eod = ttp_state.setdefault("eod_equity", {})
    prior_days = {k: v for k, v in eod.items() if k != today}
    prior_day_dates = sorted(prior_days.keys())
    prior_day_equity = prior_days[prior_day_dates[-1]] if prior_day_dates else STARTING_EQUITY
    daily_return = current_equity / prior_day_equity - 1.0
    daily_breach_today = daily_return <= -RULES["ttp"]["daily_loss_cap"]

    total_dd = _total_dd(equity_df, current_equity)
    total_dd_breach = total_dd <= -RULES["ttp"]["total_dd_cap"]
    target_hit = current_equity >= STARTING_EQUITY * (1 + RULES["ttp"]["target_gain"])

    eod[today] = current_equity  # NACH dem Vergleich speichern (nur abgeschlossene Vortage zaehlen fuer den naechsten Lauf)

    ttp_state["daily_paused"] = bool(daily_breach_today)
    if total_dd_breach:
        ttp_state["kill_switch_active"] = True
    if target_hit:
        ttp_state["target_reached"] = True

    return {
        "current_equity": current_equity, "daily_return": daily_return, "daily_breach_today": daily_breach_today,
        "total_dd": total_dd, "total_dd_breach": total_dd_breach, "target_hit": target_hit,
        "kill_switch_active": ttp_state["kill_switch_active"], "target_reached": ttp_state["target_reached"],
    }


def check_iqmarkets_rules(equity_df: pd.DataFrame, iq_state: dict) -> dict:
    """Kein Tageslimit -- nur Gesamt-Drawdown -6% (harter Kill-Switch, gleiche
    Allzeit-Hoechststand-Definition wie TTP) + Zielschwelle +8%. Das explizite
    1%-Positionslimit wird strukturell durch den DYNAMISCHEN Deckel in
    compute_shared_equity() (1% der Equity ZUM JEWEILIGEN Trade-Zeitpunkt,
    nicht STARTING_EQUITY) erfuellt -- hier nur als Invariante mitgefuehrt,
    keine stille Annahme."""
    current_equity = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else STARTING_EQUITY
    if not equity_df.empty:
        # Explizites raise statt assert (Fund beim Review 2026-09-01): ein assert wird mit
        # `python -O` komplett entfernt -- genau die "stille Annahme", die dieser Check laut
        # eigenem Docstring vermeiden soll. Ein echtes Exception behaelt die Pruefung auch dann.
        # Pro-Zeile gegen den DAMALIGEN Deckel pruefen (nicht gegen einen einzelnen globalen Wert --
        # der Deckel selbst bewegt sich mit der wachsenden/schrumpfenden Equity).
        over_cap = equity_df["risk_dollars"] > equity_df["max_position_risk_dollars"] + 1e-6
        if over_cap.any():
            bad = equity_df[over_cap].iloc[0]
            raise ValueError(
                f"IQ-Markets-1%-Positionslimit verletzt: risk_dollars={bad['risk_dollars']:.2f} > "
                f"{bad['max_position_risk_dollars']:.2f} (1% der Equity zum Zeitpunkt dieses Trades) bei {bad['leg']}"
            )

    total_dd = _total_dd(equity_df, current_equity)
    total_dd_breach = total_dd <= -RULES["iqmarkets"]["total_dd_cap"]
    target_hit = current_equity >= STARTING_EQUITY * (1 + RULES["iqmarkets"]["target_gain"])

    if total_dd_breach:
        iq_state["kill_switch_active"] = True
    if target_hit:
        iq_state["target_reached"] = True

    return {
        "current_equity": current_equity, "total_dd": total_dd, "total_dd_breach": total_dd_breach,
        "target_hit": target_hit, "kill_switch_active": iq_state["kill_switch_active"],
        "target_reached": iq_state["target_reached"],
    }


# ------------------------------------------------------------------ Haupt-Scan
def scan_once(as_of: pd.Timestamp | None = None, dry_run: bool = False, state_override: dict | None = None) -> tuple[dict, dict]:
    end = as_of if as_of is not None else pd.Timestamp.now(tz="UTC").tz_localize(None)
    if end.tzinfo is not None:
        end = end.tz_convert("UTC").tz_localize(None)
    state = dict(state_override) if state_override is not None else load_state()
    if "trades" not in state:
        state = _default_state()
    for key, default in _default_state().items():
        state.setdefault(key, default)

    if state.get("account_start") is None:
        state["account_start"] = end.isoformat()
    account_start = pd.Timestamp(state["account_start"])

    def _since_start(trades: pd.DataFrame) -> pd.DataFrame:
        if trades.empty:
            return trades
        return trades[_utc_naive(trades["entry_time"]) >= account_start]

    day = end.strftime("%Y-%m-%d")

    messages = []
    try:
        gold_asb_trades = _since_start(_retry(lambda: _scan_gold_asb(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "gold_asb", gold_asb_trades)
    except Exception as e:
        print(f"[Challenge Portfolio] Gold-ASB-Scan fehlgeschlagen: {e}")
        _record_scan_error(state, day, "gold_asb")

    try:
        cls_trades = _since_start(_retry(lambda: _scan_cls_practical(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "cls_practical", cls_trades)
    except Exception as e:
        print(f"[Challenge Portfolio] CLS-Practical-Scan fehlgeschlagen: {e}")
        _record_scan_error(state, day, "cls_practical")

    try:
        tp_trades = _since_start(_retry(lambda: _scan_trend_pullback(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "trend_pullback", tp_trades)
    except Exception as e:
        print(f"[Challenge Portfolio] Trend-Pullback-Scan fehlgeschlagen: {e}")
        _record_scan_error(state, day, "trend_pullback")

    try:
        cont_trades, rev_trades = _retry(lambda: _scan_ctnl(end, force_refresh=not dry_run))
        messages += _merge_trades(state, "ctnl_continuation", _since_start(cont_trades))
        messages += _merge_trades(state, "ctnl_reversal", _since_start(rev_trades))
    except Exception as e:
        print(f"[Challenge Portfolio] CTNL-Edge-Scan fehlgeschlagen: {e}")
        _record_scan_error(state, day, "ctnl_edge")

    try:
        ou_trades = _since_start(_retry(lambda: _scan_ou_modell(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "ou_modell", ou_trades)
    except Exception as e:
        print(f"[Challenge Portfolio] OU-Modell-Scan fehlgeschlagen: {e}")
        _record_scan_error(state, day, "ou_modell")

    try:
        orb_trades = _since_start(_retry(lambda: _scan_orb(end, force_refresh=not dry_run)))
        orb_leg_by_market = {"SP500": "orb_sp500", "US30": "orb_us30", "NASDAQ": "orb_nasdaq"}
        if not orb_trades.empty:
            for market, sub in orb_trades.groupby("market"):
                messages += _merge_trades(state, orb_leg_by_market[market], sub)
    except Exception as e:
        print(f"[Challenge Portfolio] NY-Open-ORB-Scan fehlgeschlagen: {e}")
        _record_scan_error(state, day, "orb")

    equity_df = compute_shared_equity(state)
    ttp_result = check_ttp_rules(equity_df, state["ttp"], end)
    iq_result = check_iqmarkets_rules(equity_df, state["iqmarkets"])

    # Gemeinsame Entry/Exit-Zeilen (oben) landen in BEIDEN Konten-Nachrichten --
    # jedes Konto erlebt dieselben Trades unabhaengig. Nur Regel-Ereignisse
    # (Kill-Switch/Tageslimit/Ziel) sind je Konto eigenstaendig.
    ttp_messages = list(messages)
    iq_messages = list(messages)

    if ttp_result["total_dd_breach"] and not state["ttp"].get("_notified_kill", False):
        state["ttp"]["_notified_kill"] = True
        ttp_messages.append(
            f"\U0001F6A8 KILL-SWITCH: Gesamt-Drawdown {ttp_result['total_dd']:.2%} "
            f"unter der -7%-Grenze. Manueller Reset noetig, neue Entries pruefen/pausieren."
        )
    if ttp_result["daily_breach_today"]:
        ttp_messages.append(f"⏸️ Tageslimit erreicht ({ttp_result['daily_return']:.2%}) -- neue Entries fuer heute pausiert.")
    if ttp_result["target_hit"] and not state["ttp"].get("_notified_target", False):
        state["ttp"]["_notified_target"] = True
        ttp_messages.append(f"\U0001F3AF ZIEL ERREICHT: Equity ${ttp_result['current_equity']:,.0f} (+10%).")

    if iq_result["total_dd_breach"] and not state["iqmarkets"].get("_notified_kill", False):
        state["iqmarkets"]["_notified_kill"] = True
        iq_messages.append(
            f"\U0001F6A8 KILL-SWITCH: Gesamt-Drawdown {iq_result['total_dd']:.2%} "
            f"unter der -6%-Grenze. Manueller Reset noetig, neue Entries pruefen/pausieren."
        )
    if iq_result["target_hit"] and not state["iqmarkets"].get("_notified_target", False):
        state["iqmarkets"]["_notified_target"] = True
        iq_messages.append(f"\U0001F3AF ZIEL ERREICHT: Equity ${iq_result['current_equity']:,.0f} (+8%).")

    row = {
        "date": str(end), "equity": ttp_result["current_equity"], "n_trades": len(state["trades"]),
        "ttp": ttp_result, "iqmarkets": iq_result,
    }

    if not dry_run:
        if ttp_messages:
            send_telegram_message(_challenge_message("ttp", "Scan-Update", ttp_messages))
        if iq_messages:
            send_telegram_message(_challenge_message("iqmarkets", "Scan-Update", iq_messages))

        local_hour = _local_dt(end).hour
        if state["ttp"].get("last_daily_summary_day") != day and local_hour >= DAILY_SUMMARY_HOUR:
            state["ttp"]["last_daily_summary_day"] = day
            _send_daily_summary("ttp", state, day, ttp_result, end)
        if state["iqmarkets"].get("last_daily_summary_day") != day and local_hour >= DAILY_SUMMARY_HOUR:
            state["iqmarkets"]["last_daily_summary_day"] = day
            _send_daily_summary("iqmarkets", state, day, iq_result, end)

        save_state(state)

    row["messages"] = ttp_messages + iq_messages
    return row, state


def _send_daily_summary(rule_key: str, state: dict, day: str, result: dict, end: pd.Timestamp) -> None:
    day_errors = state.get("scan_errors_today", {}).get(day, {})
    if day_errors:
        health_line = "System: ⚠️ Scan-Fehler heute bei " + ", ".join(f"{leg} ({n}x)" for leg, n in day_errors.items())
    else:
        health_line = "System: ✅ alle Scans liefen heute fehlerfrei"

    # Gesamt-P&L seit Kontostart statt "seit Tagesbeginn" -- ein taeglicher
    # EOD-Baseline-Wert existiert nur fuer TTP (eod_equity, fuer den
    # Tageslimit-Check gebraucht), IQ Markets hat keinen. Gesamt-P&L ist
    # ausserdem die relevantere Zahl fuer den Blick auf den Zielabstand.
    current_equity = result["current_equity"]
    total_pnl = current_equity - STARTING_EQUITY
    total_pnl_pct = total_pnl / STARTING_EQUITY
    rule_line = (
        f"DD {result['total_dd']:.2%} (Grenze -7%)  |  Tag {result['daily_return']:+.2%} (Grenze -3%)  |  "
        f"Kill-Switch {'AKTIV' if result['kill_switch_active'] else 'ok'}"
        if rule_key == "ttp" else
        f"DD {result['total_dd']:.2%} (Grenze -6%)  |  Kill-Switch {'AKTIV' if result['kill_switch_active'] else 'ok'}"
    )
    send_telegram_message(_challenge_message(rule_key, f"Tagesabschluss {end.strftime('%Y-%m-%d')}", [
        health_line,
        f"Equity: ${current_equity:,.0f} ({total_pnl:+,.0f}, {total_pnl_pct:+.2%} seit Kontostart)",
        rule_line,
        f"Trades gesamt: {sum(1 for t in state['trades'].values())}"
        + ("  |  Ziel erreicht" if result.get("target_reached") else ""),
    ]))
    LOG_DIR.mkdir(exist_ok=True)
    is_new = not HEARTBEAT_CSV.exists()
    with open(HEARTBEAT_CSV, "a", encoding="utf-8") as f:
        if is_new:
            f.write("date,rule,equity,total_pnl,total_dd,kill_switch_active,target_reached\n")
        f.write(f"{end.isoformat()},{rule_key},{current_equity:.2f},{total_pnl:.2f},"
                f"{result['total_dd']:.4f},{result['kill_switch_active']},{result.get('target_reached', False)}\n")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows-Konsole ist sonst cp1252, Telegram-Emojis crashen den print()

    result, _ = scan_once()
    print(json.dumps({k: v for k, v in result.items() if k != "messages"}, indent=2, default=str))
    for m in result.get("messages", []):
        print("---")
        print(m)
