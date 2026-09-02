"""EK-Portfolio - Paper-Forward-Test-Bot (2026-08-27).

NICHT der echte Order-Ausfuehrer. Voellig NEUES, separates Modul, genaues
Architektur-Vorbild fk_instant_funding/paper_bot.py -- ruehrt an KEINER
Stelle die bereits live/demo laufenden Bridges an (GoldASB-MT5-Bridge,
CLS-Practical-Bridge, TrendPullback-Bot FK1/FK2, CTNL-Edge-MT5-Bridge,
BTC-EMA-Cross-Dry-Run-Bot, OU-Modell-MT5-Bridge), die weiterhin unabhaengig
auf ihren eigenen Konten traden. Dieser Bot ist reine Paper-Simulation +
Telegram-Alerts fuer das EK (Eigenkapital)-Portfolio -- die auf Nutzerwunsch
(2026-08-27) ausgewaehlten Beine: Gold ASB, Trend Pullback, BTC EMA9/21,
Gold-Silber-Divergenz, CLS Practical, CTNL Edge (Continuation+Reversal als
ein Bein), NY-Open ORB (SP500+US30+NASDAQ als ein Bein, 2026-08-27 auf
Nutzerwunsch nachtraeglich ergaenzt) und OU-Modell -- 8 Beine insgesamt.

Sieben der acht Beine folgen der FK-Konvention: die ECHTE, bereits
validierte Signal-Engine jeder Strategie laeuft frisch auf einem
strategie-eigenen Trailing-Fenster (keine Logik-Duplizierung), das Ergebnis
wird gegen den PERSISTIERTEN Trade-Verlauf (ek_portfolio_logs/paper_state.json)
abgeglichen und in EINE gemeinsame, sequenziell kompoundierende
Paper-Equity-Kurve eingerechnet mit der Kapitalanteil-Verduennungsformel:

    risk_dollars = CAPITAL_WEIGHT (1/7) x internes Risiko/Trade x aktuelle
                   SHARED-Equity

OU-Modell ist die Ausnahme (Nutzerentscheid 2026-08-27): es haelt bis zu
~147 gleichzeitige Positionen mit einem eingefrorenen, aus einem
Trailing-Fenster nicht rekonstruierbaren Ticker-Universum (siehe
ou_paper_backtest/) und handelt bereits ECHT auf 3 eigenen MT5-Konten. Eine
Paper-Nachsimulation waere aufwaendig (yfinance-Live-Fetch, Stop-Distanz-
Rekonstruktion pro Trade, 3 Handelskalender) UND ungenauer als die echten
Zahlen. Stattdessen liest dieses Modul die bereits separat gesammelten
ECHTEN Tages-Renditen aus ou_modell_logs/daily_log.csv (befuellt von
scripts/collect_ou_modell_daily_log.py, das echte MT5-Kontostaende liest)
und rechnet sie als eigene Ereignis-Art in dieselbe chronologische
Compounding-Zeitleiste ein -- siehe compute_shared_equity().

Anders als FK Instant Funding hat Eigenkapital KEINE externen Prop-Firm-
Regeln (kein Tages-Sizing-Deckel, keine 30%-Konsistenzregel fuer
Auszahlungen). Einziger Regel-Check: ein hartes 20%-Trailing-Drawdown-
Kill-Switch (Nutzerentscheid 2026-08-27, passend zur bereits getroffenen
EK-Risikoentscheidung in portfolio_construction/results/ek_v2_realistic_final.json
-- 20% statt der dort verworfenen 30%-Psychogrenze), EOD gegen den
bisherigen Hoechststand, Floor bewegt sich nur nach oben.

Risikostufen je Bein (moderat-aggressiv, Monte-Carlo-validiert, "empfohlen"
in ek_v2_realistic_final.json::riskopt_20dd, CTNL-Risiko unveraendert von
der FK-Stufe uebernommen -- siehe app_pages/portfolio_construction.py,
Tab "CTNL Edge als 8. Strategie": die konservative Stufe gewinnt dort sogar
auf Sharpe und wird explizit empfohlen, unabhaengig von EK/FK):
    Gold ASB 8%, Trend Pullback 5%, BTC EMA9/21 8%, Gold-Silber-Divergenz 8%,
    CLS Practical 1,5%, CTNL Continuation 0,5%, CTNL Reversal 0,15%.

ORB (nachtraeglich ergaenzt) bekommt bewusst KEINE eigene "moderat-aggressiv"-
Stufe -- die riskopt_20dd-Studie wurde erst NACH dem Entfernen von ORB aus
dem EK-Kernset gerechnet, es existiert also keine MC-validierte Zahl fuer
die aktuelle 3-Instrumente-Konfiguration unter der 20%-DD-Grenze. Uebernimmt
daher unveraendert FK's konservative Kalibrierung (1% Bein-Gesamtrisiko,
gleichgewichtet ueber SP500/US30/NASDAQ) statt eine unbelegte Zahl zu
erfinden -- bei Bedarf spaeter gezielt hochstufen."""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ek_portfolio.telegram_notify import send_telegram_message
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.schedule_guard import is_market_paused


def _retry(fn, attempts: int = 6, delay_seconds: float = 8.0):
    """dukascopy_python's Streaming-Client wirft gelegentlich ein KeyError(0)
    ODER (Fund 2026-09-02, CLS Practical auf EK-Portfolio-Bridge, 3x
    hintereinander ueber 45 Min. beobachtet) ein TypeError ("'>' not
    supported between instances of 'str' and 'float'") tief in seiner
    eigenen _stream()-Cursor-Logik, wenn end nah an "jetzt" liegt
    (reproduzierbar bei fast jedem Live-Abruf bis zum aktuellen Moment) --
    bekannte Instabilitaet der Drittanbieter-Bibliothek, kein Fehler in
    unserem Code. attempts/delay_seconds 2026-09-02 von 3x/5s auf 6x/8s
    erhoeht, nachdem 3 Versuche im obigen Fall nicht ausgereicht haben."""
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
LOG_DIR = REPO_DIR / "ek_portfolio_logs"
STATE_PATH = LOG_DIR / "paper_state.json"
HEARTBEAT_CSV = LOG_DIR / "heartbeat.csv"
OU_DAILY_LOG_CSV = REPO_DIR / "ou_modell_logs" / "daily_log.csv"

STARTING_EQUITY = 100_000.0  # Platzhalter -- auf die reale EK-Kontogroesse setzen, bevor die Kurve ernst genommen wird
CAPITAL_WEIGHT = 1 / 8  # 8 gleichgewichtete Beine (Equal-Weight, siehe walk_forward_results.json-Fazit: Max-Sharpe
# verliert den Out-of-Sample-Test gegen Equal-Weight klar) -- CTNL Continuation+Reversal teilen sich EIN Bein,
# die 3 ORB-Instrumente teilen sich ebenfalls EIN Bein (wie bei FK: alle Sub-Legs bekommen die VOLLE
# 1/8-Kapitalscheibe, nicht je einen Anteil -- identische Konvention zu fk_instant_funding/paper_bot.py::
# CAPITAL_WEIGHT). OU-Modell bekommt dieselbe 1/8-Scheibe, aber ueber echte Tages-Renditen statt eines
# internen LEG_RISK_PCT (siehe compute_shared_equity).

TRAILING_DD_PCT = 0.20  # EOD, gegen den bisherigen Hoechststand -- EK-spezifische 20%-Grenze, siehe Moduldocstring

ORB_COMBINED_RISK_PCT = 0.01  # "ORB Portfolio"-Bein gesamt, gleichgewichtet ueber 3 Instrumente -- unveraendert
# von FK's Kalibrierung uebernommen, siehe Moduldocstring (keine EK-eigene MC-validierte Zahl vorhanden)
ORB_RISK_PCT_PER_INSTRUMENT = ORB_COMBINED_RISK_PCT / 3  # exakt die Backtest-Konvention (combined += ret/3)

LEG_RISK_PCT = {
    "gold_asb": 0.08,
    "trend_pullback": 0.05,
    "btc_ema_cross": 0.08,
    "gold_silver": 0.08,
    "cls_practical": 0.015,
    "ctnl_continuation": 0.005,
    "ctnl_reversal": 0.0015,
    "orb_sp500": ORB_RISK_PCT_PER_INSTRUMENT,
    "orb_us30": ORB_RISK_PCT_PER_INSTRUMENT,
    "orb_nasdaq": ORB_RISK_PCT_PER_INSTRUMENT,
}
LEG_LABELS = {
    "gold_asb": "Gold ASB", "trend_pullback": "Trend Pullback", "btc_ema_cross": "BTC EMA9/21",
    "gold_silver": "Gold-Silber-Divergenz", "cls_practical": "CLS Practical",
    "ctnl_continuation": "CTNL Continuation", "ctnl_reversal": "CTNL Reversal",
    "orb_sp500": "NY-Open ORB (SP500)", "orb_us30": "NY-Open ORB (US30)", "orb_nasdaq": "NY-Open ORB (NASDAQ)",
}

OU_REAL_ACCOUNTS = ["Konto 1 (TTP)", "Konto 3 (Tickmill)"]  # nur die beiden ECHTEN Konten -- "Konto 2 (TTP, Demo)"
# ist eine reine Demo-Kopie ohne echtes Kapital und zaehlt bewusst nicht in die EK-Kurve


def _utc_naive(x):
    """Jede der 8 Strategien liefert Zeitstempel in einer ANDEREN Zeitzone-
    Konvention (Gold ASB: America/New_York, CLS Practical: Europe/Berlin,
    Trend Pullback/Gold-Silber-Divergenz/BTC EMA9/21/ORB: UTC, CTNL: America/
    New_York) -- ohne Normalisierung crasht jeder Vergleich mit dem
    tz-naiven `end` (tz-aware vs. tz-naive Timestamp-Vergleich ist in pandas
    ein TypeError, kein stiller Fehler). Konvertiert konsistent nach UTC,
    dann tz-naiv."""
    if isinstance(x, pd.DatetimeIndex):
        return x.tz_convert("UTC").tz_localize(None) if x.tz is not None else x
    s = pd.to_datetime(x, utc=True)
    return s.dt.tz_localize(None) if hasattr(s, "dt") else s.tz_localize(None)


def _default_state() -> dict:
    return {"trades": {}, "kill_switch_active": False, "last_heartbeat_hour": None,
            "eod_equity": {}, "account_start": None, "ou_notified_dates": []}


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
# Backtest, keine zweite Implementierung der Entry/Exit-Regeln. Die ersten
# fuenf sind wortgleich mit fk_instant_funding/paper_bot.py uebernommen (die
# Engines selbst kennen kein FK/EK, nur die Risikostufen weiter unten
# unterscheiden sich).

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
    """Repliziert die fuenf produktiv validierten Live-Filter der echten
    GoldASB-MT5-Bridge (ADX, Trend-Bias, Fuellverzoegerung, Silber-Alignment,
    Liquiditaet) -- Parameter und Filterkette 1:1 aus app_pages/asian_range_
    breakout.py uebernommen. Volle Historie seit GOLD_ASB_HISTORY_START
    noetig, weil die Liquiditaets-Schwelle eine expanding Quantile ist."""
    from asian_range_breakout.data import fetch_gold_m15
    from asian_range_breakout.engine import simulate_asian_breakout
    from asian_range_breakout.filters import (
        apply_adx_filter, apply_entry_delay_filter, apply_gold_liquidity_filter_causal,
        apply_silver_alignment_filter, apply_trend_bias_filter,
    )
    from asian_range_breakout.sizing import simulate_equity
    from bond_yield_indicator.friction import fetch_fx_friction
    from combined_strategy.data import fetch_timeframe

    # fetch_timeframe() cached unter dem exakten (start, end)-Datumspaar -- mit end=jetzt wuerde JEDER
    # stuendliche Lauf einen NEUEN Cache-Schluessel erzeugen und die vollen ~10 Jahre M15-Gold/Silber
    # komplett frisch herunterladen. Fix: alte, laengst abgeschlossene Historie bis GESTERN cachen
    # (aendert sich nur einmal pro Tag), nur den kurzen frischen Rest seit gestern wirklich
    # force_refresh=True abrufen und anhaengen.
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


def _cap_concurrent_reversals(rev_trades: pd.DataFrame, max_concurrent: int) -> pd.DataFrame:
    """simulate_trades_concurrent() erzwingt KEIN Limit gleichzeitig offener
    Positionen -- das reale REV_MAX_CONCURRENT-Limit lebt nur in der
    Ausfuehrungsschicht (gold_smc_htf_ltf/live_signal.py-Docstring,
    EK-Portfolio-Bridge/legs/ctnl_edge/executor.py::check_and_execute_
    reversal). Ohne diese Kappung ueberzeichnet der Paper-Bot systematisch,
    was real ausfuehrbar gewesen waere (Fund 2026-08-31: mehrere "parallele"
    Reversal-Trades pro Tag mit fast identischem Exit-Zeitpunkt+R-Multiple
    in der Live-Nachrichtenflut -- 1122 von 1417 Trades in einer Jahres-
    Rekonstruktion betrafen genau dieses Muster). Greedy-Kappung nach
    Entry-Zeit: ein Trade wird verworfen, wenn zu seinem Entry-Zeitpunkt
    bereits max_concurrent andere (nach ihrer Exit-Zeit) noch offene
    Reversal-Trades laufen -- exakt die Regel, die eine echte Bridge
    angewendet haette."""
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


BTC_EMA_LOOKBACK_DAYS = 100  # identisch zu btc_ema_cross/live_scan.py::LOOKBACK_DAYS -- ausreichender Warmup fuer EMA21/ATR14


def _scan_btc_ema_cross(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    """Nutzt dieselbe validierte Engine wie btc_ema_cross/live_scan.py
    (btc_ema_cross.engine.simulate_risk_sized), aber frisch auf einem eigenen
    Trailing-Fenster statt den bereits separat laufenden BTC-EMA-Cross-
    Dry-Run-Bot anzufassen oder dessen paper_state.json zu lesen -- exakt
    dieselbe Konvention wie bei den anderen 6 Beinen.

    Einschraenkung: simulate_risk_sized() liefert nur GESCHLOSSENE Trades
    (anders als strategy.backtest.simulate_trades/asian_range_breakout.sizing.
    simulate_equity, die eine noch offene Position als 'data_end'-Zeile mit
    Mark-to-Market-R mitliefern). Eine noch offene BTC-Position triggert
    daher die ENTRY-Telegram-Meldung erst beim tatsaechlichen Exit, nicht
    sofort bei Eroeffnung. Die gemeinsame Equity-Kurve ist davon nicht
    betroffen, da compute_shared_equity() ohnehin nur geschlossene
    R-Multiples aufsummiert."""
    from auction_playbook.data import fetch_klines
    from btc_ema_cross.engine import simulate_risk_sized

    start_str = (end - pd.Timedelta(days=BTC_EMA_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    df = fetch_klines("BTCUSDT", "1d", start_str, end_str, force_refresh=force_refresh)
    if df.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])

    result = simulate_risk_sized(df, fast=9, slow=21, capital=100_000.0, risk_pct=0.01,
                                  sim_from=pd.Timestamp(start_str, tz="UTC"))
    trades = result["trades"]
    if not trades:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])

    out = pd.DataFrame(trades).rename(columns={"entry_date": "entry_time", "exit_date": "exit_time", "r": "r_multiple"})
    out["exit_reason"] = np.where(out["stopped_out"], "stop", "crossunder")
    out = out[_utc_naive(out["entry_time"]) <= end]
    return out[["entry_time", "exit_time", "r_multiple", "exit_reason"]]


ORB_EXIT_CFG_BY_INSTRUMENT = {
    # identisch zu app_pages/ny_open_orb_portfolio.py::EXIT_CFG_BY_INSTRUMENT -- Teilausstieg
    # (50% der Position bankt bei 2R/1.5R, Rest-Stop danach auf Break-Even) ist seit der
    # Partial-Exit-Ergaenzung in ny_open_orb/engine.py::simulate() der aktuelle Standard.
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
}
ORB_HISTORY_LOOKBACK_DAYS = 500  # EMA-Ribbon-Bias (4H/1D/1W) braucht Monate an Vorlauf


def _scan_orb(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    """NY-Open ORB (SP500+US30+NASDAQ), 1:1 die validierte Config aus
    app_pages/ny_open_orb_portfolio.py (siehe knowledge/projects/ny-open-
    orb-sp500.md, Stage 1-5 + Phase 6 abgeschlossen) -- wortgleich mit
    fk_instant_funding/paper_bot.py::_scan_orb uebernommen. Anders als die
    anderen Beine schliesst ORB IMMER innerhalb derselben NY-Handelssession
    (spaetestens per session_end) -- kein Mehrtage-Halten. Deshalb eine
    Besonderheit: simulate() labelt "keine Bar mehr im gefetchten Fenster
    gefunden" auch als "session_end", selbst wenn die echte Session noch
    gar nicht vorbei ist (ein Scan MITTEN in der Session haette sonst
    faelschlich einen finalen Exit gemeldet, statt eines vorlaeufigen
    Mark-to-Market-Stands wie bei den anderen Beinen ueber "data_end") --
    wird hier anhand der frame-eigenen session_close-Spalte korrigiert."""
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
                trades.loc[idx, "exit_reason"] = "data_end"  # Session noch nicht wirklich vorbei

        trades["market"] = instrument
        all_trades.append(trades)

    if not all_trades:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason", "market"])
    return pd.concat(all_trades, ignore_index=True)


def _load_ou_modell_daily_returns(account_start: pd.Timestamp) -> pd.Series:
    """Liest die ECHTEN Tages-Renditen des bereits live laufenden OU-Modells
    aus ou_modell_logs/daily_log.csv (separat befuellt von
    scripts/collect_ou_modell_daily_log.py, das echte MT5-Kontostaende
    liest) -- KEINE Nachsimulation, siehe Moduldocstring. Nur die beiden
    ECHTEN Konten (OU_REAL_ACCOUNTS) zaehlen. Gibt je Kalendertag den
    Durchschnitt der verfuegbaren daily_pnl_pct-Werte zurueck, Index auf
    23:59:59 jenes Tages gesetzt, damit das Ereignis in der gemeinsamen
    Zeitleiste chronologisch NACH den Exit-Zeiten der anderen Beine am
    selben Tag einsortiert wird (OU-Modell-Equity gilt EOD als final)."""
    if not OU_DAILY_LOG_CSV.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(OU_DAILY_LOG_CSV)
    if df.empty or "account" not in df.columns:
        return pd.Series(dtype=float)
    df = df[df["account"].isin(OU_REAL_ACCOUNTS)].copy()
    df["daily_pnl_pct"] = pd.to_numeric(df["daily_pnl_pct"], errors="coerce")
    df = df.dropna(subset=["daily_pnl_pct"])
    if df.empty:
        return pd.Series(dtype=float)
    by_date = df.groupby("date")["daily_pnl_pct"].mean()
    idx = pd.to_datetime(by_date.index) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    series = pd.Series(by_date.to_numpy(), index=idx).sort_index()
    return series[series.index >= account_start]


# ------------------------------------------------------------------ State-Merge (Muster: fk_instant_funding/paper_bot.py)
def _merge_trades(state: dict, leg: str, trades: pd.DataFrame) -> list[str]:
    """Speichert entry_time/exit_time konsistent als UTC-naive ISO-Strings --
    ohne diese Normalisierung mischen sich beim Wiedereinlesen Zeitstempel
    mit verschiedenen tz-Offsets je Bein in EINER Spalte, was pd.to_datetime()
    mit 'Mixed timezones detected' zum Absturz bringt."""
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
            messages.append(f"[EK Portfolio] \U0001F7E2 ENTRY {LEG_LABELS[leg]} @ {t['entry_time']}")
        else:
            rec = state["trades"][key]
            rec["exit_time"], rec["exit_reason"], rec["r_multiple"] = exit_naive.isoformat(), exit_reason, r_mult
            if exit_reason != "data_end" and not rec.get("notified_exit", False):
                icon = "\U0001F7E2" if r_mult > 0 else "\U0001F534"
                messages.append(f"[EK Portfolio] {icon} EXIT {LEG_LABELS[leg]} ({exit_reason}) R={r_mult:+.2f}")
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


# ------------------------------------------------------------------ gemeinsame Equity + Regel-Check
def compute_shared_equity(state: dict, ou_returns: pd.Series) -> pd.DataFrame:
    """Baut die EINE gemeinsame, sequenziell kompoundierende Paper-Equity
    ueber alle 7 Beine. Sechs Beine liefern diskrete R-Multiple-Trades
    (Kapitalanteil-Verduennungsformel: risk_dollars = CAPITAL_WEIGHT x
    LEG_RISK_PCT x equity); OU-Modell liefert echte Tages-Renditen statt
    eines internen Risiko/Trade (risk_dollars = CAPITAL_WEIGHT x equity,
    pnl = risk_dollars x Tagesrendite -- die Rendite selbst ist bereits
    real, braucht keinen zusaetzlichen Risiko-Faktor). Beide Ereignis-Arten
    werden in EINE chronologische Zeitleiste gemischt, damit jedes Ereignis
    auf die Equity VOR sich selbst bezogen wird (echtes Compounding ueber
    alle Beine hinweg, nicht nur innerhalb eines Beins)."""
    trade_events = _state_trades_df(state).sort_values("exit_time")
    events = [{"time": t["exit_time"], "kind": "trade", "leg": t["leg"], "r_multiple": t["r_multiple"]}
              for _, t in trade_events.iterrows()]
    events += [{"time": ts, "kind": "ou_daily", "leg": "ou_modell", "pct": pct} for ts, pct in ou_returns.items()]

    if not events:
        return pd.DataFrame(columns=["time", "leg", "risk_dollars", "pnl", "equity"])

    events_df = pd.DataFrame(events).sort_values("time").reset_index(drop=True)
    equity = STARTING_EQUITY
    rows = []
    for _, e in events_df.iterrows():
        if e["kind"] == "trade":
            risk_dollars = CAPITAL_WEIGHT * LEG_RISK_PCT[e["leg"]] * equity
            pnl = risk_dollars * e["r_multiple"]
        else:
            risk_dollars = CAPITAL_WEIGHT * equity
            pnl = risk_dollars * e["pct"]
        equity += pnl
        rows.append({"time": e["time"], "leg": e["leg"], "risk_dollars": risk_dollars, "pnl": pnl, "equity": equity})
    return pd.DataFrame(rows)


def check_trailing_dd(equity_df: pd.DataFrame, eod_equity_state: dict, as_of: pd.Timestamp) -> tuple[bool, float, float]:
    """EOD-Trailing-Drawdown: Floor = 80% des bisherigen EOD-Hoechststands
    (TRAILING_DD_PCT=0.20), bewegt sich nur nach oben. `as_of` statt
    pd.Timestamp.now() -- sonst wuerde ein historischer Dry-Run/Backtest-
    Aufruf faelschlich das ECHTE heutige Datum als EOD-Schluessel benutzen.

    Der Floor darf NUR auf abgeschlossenen VORTAGEN beruhen, niemals auf dem
    noch laufenden heutigen Wert -- sonst wuerde jeder stuendliche Lauf den
    Floor faelschlich an ein reines INTRADAY-Hoch dieses Tages anpassen
    (siehe fk_instant_funding/paper_bot.py fuer den dort real gefundenen Bug
    vor der echten Kontoanbindung). Der heutige Stand wird erst NACH dem
    Vergleich gespeichert, damit er ab dem naechsten Kalendertag als
    abgeschlossener Vortag in die Floor-Berechnung eingeht."""
    if equity_df.empty:
        return False, 0.0, STARTING_EQUITY
    today = as_of.normalize().isoformat()
    current_equity = float(equity_df["equity"].iloc[-1])
    prior_days_only = {k: v for k, v in eod_equity_state.items() if k != today}
    running_max = max([STARTING_EQUITY] + list(prior_days_only.values()))
    floor = (1 - TRAILING_DD_PCT) * running_max
    breached = current_equity < floor
    current_dd = current_equity / running_max - 1
    eod_equity_state[today] = current_equity
    return breached, current_dd, floor


def _notify_ou_updates(state: dict, ou_returns: pd.Series) -> list[str]:
    messages = []
    notified = set(state.get("ou_notified_dates", []))
    for ts, pct in ou_returns.items():
        date_key = ts.strftime("%Y-%m-%d")
        if date_key in notified:
            continue
        icon = "\U0001F7E2" if pct >= 0 else "\U0001F534"
        messages.append(f"[EK Portfolio] {icon} OU-Modell Tagesrendite {date_key} (echt, Konto 1+3): {pct:+.2%}")
        notified.add(date_key)
    state["ou_notified_dates"] = sorted(notified)
    return messages


# ------------------------------------------------------------------ Haupt-Scan
def scan_once(as_of: pd.Timestamp | None = None, dry_run: bool = False, state_override: dict | None = None) -> tuple[dict, dict]:
    end = as_of if as_of is not None else pd.Timestamp.now(tz="UTC").tz_localize(None)
    if end.tzinfo is not None:
        end = end.tz_convert("UTC").tz_localize(None)
    state = dict(state_override) if state_override is not None else load_state()
    if "trades" not in state:
        state = _default_state()
    state.setdefault("eod_equity", {})
    state.setdefault("ou_notified_dates", [])

    # Kontostart fixieren: manche Scans brauchen JAHRE an Historie fuer ihre eigene Filter-/
    # Indikator-Aufwaermzeit (z.B. Gold ASB's expanding Liquiditaets-Quantile seit 2016), das darf
    # aber nicht heissen, dass deren komplette Mehrjahres-Historie ins gemeinsame Paper-Konto
    # einfliesst (siehe fk_instant_funding/paper_bot.py fuer den real gefundenen Bug: +32% "seit
    # heute" war in Wahrheit ein 10-Jahre-Backtest). account_start wird beim allerersten Lauf
    # einmalig auf `end` gesetzt und danach persistiert -- nur Ereignisse ab account_start zaehlen.
    if state.get("account_start") is None:
        state["account_start"] = end.isoformat()
    account_start = pd.Timestamp(state["account_start"])

    def _since_start(trades: pd.DataFrame) -> pd.DataFrame:
        if trades.empty:
            return trades
        return trades[_utc_naive(trades["entry_time"]) >= account_start]

    # Wochenende/Spread-Stunde: die 7 Forex-/Gold-/Index-Beine pausieren
    # (kein Handel, kein Sinn in einem Scan), BTC EMA9/21 handelt aber rund
    # um die Uhr (Krypto) und bleibt bewusst ausgenommen (User-Wunsch
    # 2026-08-29, siehe strategy/schedule_guard.py-Docstring). Ein expliziter
    # as_of-Aufruf (Tests/Backtests) wird NICHT pausiert.
    fx_paused = as_of is None and is_market_paused(end)

    messages = []
    if not fx_paused:
        try:
            gold_asb_trades = _since_start(_retry(lambda: _scan_gold_asb(end, force_refresh=not dry_run)))
            messages += _merge_trades(state, "gold_asb", gold_asb_trades)
        except Exception as e:
            messages.append(f"[EK Portfolio] ⚠️ Gold-ASB-Scan fehlgeschlagen: {e}")

        try:
            cls_trades = _since_start(_retry(lambda: _scan_cls_practical(end, force_refresh=not dry_run)))
            messages += _merge_trades(state, "cls_practical", cls_trades)
        except Exception as e:
            messages.append(f"[EK Portfolio] ⚠️ CLS-Practical-Scan fehlgeschlagen: {e}")

        try:
            tp_trades = _since_start(_retry(lambda: _scan_trend_pullback(end, force_refresh=not dry_run)))
            messages += _merge_trades(state, "trend_pullback", tp_trades)
        except Exception as e:
            messages.append(f"[EK Portfolio] ⚠️ Trend-Pullback-Scan fehlgeschlagen: {e}")

        try:
            cont_trades, rev_trades = _retry(lambda: _scan_ctnl(end, force_refresh=not dry_run))
            messages += _merge_trades(state, "ctnl_continuation", _since_start(cont_trades))
            messages += _merge_trades(state, "ctnl_reversal", _since_start(rev_trades))
        except Exception as e:
            messages.append(f"[EK Portfolio] ⚠️ CTNL-Edge-Scan fehlgeschlagen: {e}")

        try:
            gsd_trades = _since_start(_retry(lambda: _scan_gold_silver(end, force_refresh=not dry_run)))
            messages += _merge_trades(state, "gold_silver", gsd_trades)
        except Exception as e:
            messages.append(f"[EK Portfolio] ⚠️ Gold-Silber-Divergenz-Scan fehlgeschlagen: {e}")

    # BTC EMA9/21 IMMER scannen -- Krypto handelt 24/7, keine Wochenend-/Spread-Stunden-Sperre.
    try:
        btc_trades = _since_start(_retry(lambda: _scan_btc_ema_cross(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "btc_ema_cross", btc_trades)
    except Exception as e:
        messages.append(f"[EK Portfolio] ⚠️ BTC-EMA9/21-Scan fehlgeschlagen: {e}")

    if not fx_paused:
        try:
            orb_trades = _since_start(_retry(lambda: _scan_orb(end, force_refresh=not dry_run)))
            orb_leg_by_market = {"SP500": "orb_sp500", "US30": "orb_us30", "NASDAQ": "orb_nasdaq"}
            if not orb_trades.empty:
                for market, sub in orb_trades.groupby("market"):
                    messages += _merge_trades(state, orb_leg_by_market[market], sub)
        except Exception as e:
            messages.append(f"[EK Portfolio] ⚠️ NY-Open-ORB-Scan fehlgeschlagen: {e}")

    try:
        ou_returns = _load_ou_modell_daily_returns(account_start)
        messages += _notify_ou_updates(state, ou_returns)
    except Exception as e:
        ou_returns = pd.Series(dtype=float)
        messages.append(f"[EK Portfolio] ⚠️ OU-Modell-Tageslog konnte nicht gelesen werden: {e}")

    equity_df = compute_shared_equity(state, ou_returns)
    dd_breached, current_dd, dd_floor = check_trailing_dd(equity_df, state["eod_equity"], end)
    current_equity = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else STARTING_EQUITY

    if dd_breached and not state.get("kill_switch_active", False):
        state["kill_switch_active"] = True
        messages.append(
            f"[EK Portfolio] \U0001F6A8 KILL-SWITCH: Trailing-Drawdown {current_dd:.2%} unter dem "
            f"{TRAILING_DD_PCT:.0%}-Floor (${dd_floor:,.0f}). Neue Entries pruefen/pausieren."
        )
    elif not dd_breached and state.get("kill_switch_active", False) and current_dd >= -TRAILING_DD_PCT * 0.5:
        state["kill_switch_active"] = False  # Erholung ueber die Haelfte der Schwelle - Reset

    row = {
        "date": str(end), "equity": current_equity, "current_dd": current_dd,
        "kill_switch_active": state.get("kill_switch_active", False), "n_trades": len(state["trades"]),
    }

    current_hour_key = end.strftime("%Y-%m-%d %H")
    if state.get("last_heartbeat_hour") != current_hour_key:
        state["last_heartbeat_hour"] = current_hour_key
        heartbeat_msg = (
            f"[EK Portfolio] Stuendlicher Status {end.strftime('%Y-%m-%d %H:%M')}\n"
            f"Equity: ${current_equity:,.0f}  |  Trailing-DD: {current_dd:.2%} (Floor ${dd_floor:,.0f})  |  "
            f"Trades: {len(state['trades'])} (+OU-Modell echte Tagesrenditen)  |  "
            f"Kill-Switch: {'AKTIV' if state['kill_switch_active'] else 'ok'}"
        )
        if not dry_run:
            send_telegram_message(heartbeat_msg)
            LOG_DIR.mkdir(exist_ok=True)
            is_new = not HEARTBEAT_CSV.exists()
            with open(HEARTBEAT_CSV, "a", encoding="utf-8") as f:
                if is_new:
                    f.write("date,equity,current_dd,kill_switch_active,n_trades\n")
                f.write(f"{end.isoformat()},{current_equity:.2f},{current_dd:.4f},"
                        f"{state['kill_switch_active']},{len(state['trades'])}\n")

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
