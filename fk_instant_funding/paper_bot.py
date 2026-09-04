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

    risk_dollars = CAPITAL_WEIGHT[Bein] (siehe Tabelle, Monte-Carlo-optimiert,
                   NICHT mehr gleichgewichtet) x internes Risiko/Trade x
                   aktuelle SHARED-Equity, GEDECKELT auf 0.5% des STARTKAPITALS

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
import threading
import time
from pathlib import Path

import numpy as np
import pandas as pd

from fk_instant_funding.telegram_format import fk_message as _fk_message
from fk_instant_funding.telegram_notify import flush_queued_messages, queue_message, send_telegram_message
from gold_smc_htf_ltf.live_signal import CTNL_KILL_SWITCH_DD_THRESHOLD, ctnl_standalone_drawdown
from strategy.backtest import BacktestConfig, simulate_trades

# Telegram-Layout (Banner, Buendelung) lebt seit 2026-09-02 in
# fk_instant_funding/telegram_format.py + telegram_notify.py -- identisches
# Muster wie EK-Portfolio-Bridge/Funded-Portfolio-Bridge, siehe deren
# Docstrings. `_fk_message` bleibt als lokaler Alias fuer den Tagesabschluss
# weiter unten nutzbar (import oben).


def _call_with_timeout(fn, timeout_seconds: float):
    """Laesst fn() in einem Daemon-Thread laufen, wartet maximal timeout_seconds.
    Fund 2026-09-02 (Abend): dukascopy_python haengt manchmal OHNE jemals eine
    Exception zu werfen -- betrifft auch `fk_instant_funding.paper_bot`,
    mehrere Prozesse liefen dadurch stundenlang fest, `Stop-Process` war der
    einzige Weg raus (siehe knowledge/CHANGELOG.md). Ein echter Thread-Abbruch
    ist in Python nicht moeglich -- der haengende Aufruf laeuft im Hintergrund
    weiter, aber `daemon=True` verhindert, dass ER den Prozess am saubern
    Beenden hindert, und der Hauptablauf blockiert dadurch nie wieder
    unbegrenzt."""
    result: list = []
    error: list = []

    def _target():
        try:
            result.append(fn())
        except Exception as e:
            error.append(e)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout_seconds)
    if t.is_alive():
        raise TimeoutError(f"Aufruf haengt noch nach {timeout_seconds:.0f}s (dukascopy_python-Hang, siehe DASHBOARD.md)")
    if error:
        raise error[0]
    return result[0]


def _retry(fn, attempts: int = 6, delay_seconds: float = 8.0, timeout_seconds: float = 90.0):
    """dukascopy_python's Streaming-Client wirft gelegentlich ein KeyError(0)
    ODER (Fund 2026-09-02, siehe ek_portfolio/paper_bot.py::_retry()) ein
    TypeError tief in seiner eigenen _stream()-Cursor-Logik, wenn end nah an
    "jetzt" liegt (reproduzierbar bei fast jedem Live-Abruf bis zum
    aktuellen Moment, siehe Traceback ueber dukascopy_python/__init__.py:209)
    -- bekannte Instabilitaet der Drittanbieter-Bibliothek, kein Fehler in
    unserem Code. attempts/delay_seconds 2026-09-02 von 3x/5s auf 6x/8s
    erhoeht, nachdem 3 Versuche in einem realen Fall nicht ausgereicht
    haben (der zweite oder dritte Versuch kommt sonst fast immer durch).
    Jeder Versuch laeuft jetzt zusaetzlich durch _call_with_timeout() (siehe
    dortiger Docstring) -- ein haengender Versuch zaehlt wie jeder andere
    Fehlversuch, statt den ganzen Bridge-Lauf fuer immer zu blockieren."""
    last_exc = None
    for attempt in range(attempts):
        try:
            return _call_with_timeout(fn, timeout_seconds)
        except Exception as e:
            last_exc = e
            if attempt < attempts - 1:
                time.sleep(delay_seconds)
    raise last_exc

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_DIR / "fk_instant_funding_logs"
STATE_PATH = LOG_DIR / "paper_state.json"
HEARTBEAT_CSV = LOG_DIR / "heartbeat.csv"

STARTING_EQUITY = 100_000.0  # Platzhalter -- vor echtem Livegang auf die reale Kontogroesse setzen

# Kapitalanteil je Bein (2026-08-29, Monte-Carlo-optimiert statt Gleichgewichtung
# 1/6 -- siehe portfolio_construction/results/fk_instant_funding_final.json,
# weight_optimization_note): Grid-Suche ueber Kapitalanteile bei FIXEN, bereits
# validierten internen Risikostufen je Bein (LEG_RISK_PCT unten), ausgewaehlt
# nach bestem CAGR unter P(Trailing-DD-Bruch>5%) <= 1% ueber 3.000 Block-
# Bootstrap-Pfade. CTNL Continuation+Reversal und die 3 ORB-Instrumente teilen
# sich je EIN gemeinsames Bein-Gewicht (identisch zum Backtest-Aufbau).
CAPITAL_WEIGHT = {
    "gold_asb": 0.0606,
    "cls_practical": 0.1919,
    "trend_pullback": 0.0606,
    "ctnl_continuation": 0.2525,
    "ctnl_reversal": 0.2525,
    "gold_silver": 0.0606,
    "orb_sp500": 0.3737,
    "orb_us30": 0.3737,
    "orb_nasdaq": 0.3737,
}

MAX_POSITION_LOSS_PCT = 0.005   # vom STARTKAPITAL (fester Dollar-Deckel, siehe Docstring)
TRAILING_DD_PCT = 0.05          # End-of-Day, gegen den bisherigen Hoechststand
CONSISTENCY_CAP_PCT = 0.30      # bester Einzeltag / kumulierter Gesamtgewinn
DAILY_SUMMARY_HOUR = 22         # ECHTE lokale Zeit (Europe/Berlin, siehe _local_dt()) - erster Lauf nach
# dieser Stunde sendet den Tagesabschluss. Bug gefunden beim Review 2026-08-29: `end` ist UTC-naiv, ein
# direkter Vergleich end.hour >= 21 verglich also in Wahrheit gegen UTC 21 Uhr = 23 Uhr Sommerzeit lokal --
# der Tagesabschluss feuerte real zwei Stunden spaeter als der Kommentar behauptete. Ab jetzt ueber
# _local_hour() korrekt in Europe/Berlin umgerechnet. Von 21 auf 22 verschoben (Nutzerauftrag
# 2026-09-02, gemeinsame Zielzeit fuer alle 3 Portfolios).
LOCAL_TZ = "Europe/Berlin"
SPREAD_HOUR_LOCAL = 23  # taeglicher Broker-Rollover/Swap-Zeitpunkt, spuerbar breitere Spreads (User-Wunsch 2026-08-29)


def _local_dt(end: pd.Timestamp) -> pd.Timestamp:
    """`end` ist im ganzen Modul UTC-naiv (siehe _utc_naive-Docstring) --
    fuer Uhrzeit-basierte Entscheidungen (Tagesabschluss-Stunde, Wochenende,
    Spread-Stunde) muss das nach ECHTER lokaler Zeit umgerechnet werden,
    sonst verschiebt sich jede Stunden-Schwelle um den UTC-Offset (+1/+2h)."""
    return end.tz_localize("UTC").tz_convert(LOCAL_TZ)


def is_market_paused(end: pd.Timestamp) -> bool:
    """Kein Forex-/Indexhandel am Wochenende (Markt schliesst Freitagabend,
    oeffnet erst Sonntagabend wieder -- eine grosszuegige, aber einfache
    Kalendertag-Naeherung: gesamter Samstag+Sonntag pausiert) und waehrend
    der taeglichen Spread-Stunde (User-Wunsch 2026-08-29: "damit nichts
    unnoetig am Wochenende laeuft" + "pausiere zur Spreadstunde 23:00 Uhr").
    Wird von paper_bot.scan_once() UND der echten Bridge (run_once.py) VOR
    jedem Daten-Fetch/jeder MT5-Verbindung geprueft -- komplett kostenloser
    No-Op ausserhalb der Handelszeiten, kein unnoetiger Terminal-Start am
    Wochenende."""
    local = _local_dt(end)
    if local.weekday() >= 5:  # 5=Samstag, 6=Sonntag
        return True
    if local.hour == SPREAD_HOUR_LOCAL:
        return True
    return False

# interne Risikostufen je Bein, identisch zu portfolio_construction/results/fk_instant_funding_final.json
ORB_COMBINED_RISK_PCT = 0.01  # "ORB Portfolio"-Bein gesamt, gleichgewichtet ueber 3 Instrumente (siehe unten)
ORB_RISK_PCT_PER_INSTRUMENT = ORB_COMBINED_RISK_PCT / 3  # exakt die Backtest-Konvention (combined += ret/3)
LEG_RISK_PCT = {
    "gold_asb": 0.02,
    "cls_practical": 0.015,
    "trend_pullback": 0.005,
    "ctnl_continuation": 0.005,
    "ctnl_reversal": 0.0015,
    "gold_silver": 0.01,
    "orb_sp500": ORB_RISK_PCT_PER_INSTRUMENT,
    "orb_us30": ORB_RISK_PCT_PER_INSTRUMENT,
    "orb_nasdaq": ORB_RISK_PCT_PER_INSTRUMENT,
}
LEG_LABELS = {
    "gold_asb": "Gold ASB", "cls_practical": "CLS Practical", "trend_pullback": "Trend Pullback",
    "ctnl_continuation": "CTNL Continuation", "ctnl_reversal": "CTNL Reversal", "gold_silver": "Gold-Silber-Divergenz",
    "orb_sp500": "NY-Open ORB (SP500)", "orb_us30": "NY-Open ORB (US30)", "orb_nasdaq": "NY-Open ORB (NASDAQ)",
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
    return {"trades": {}, "kill_switch_active": False, "last_heartbeat_hour": None, "eod_equity": {}, "account_start": None}


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
    Liquiditaet -- siehe GoldASB-MT5-Bridge/config.py, Parameter dort mit
    dieser Reihenfolge/diesen Werten identisch) statt des rohen, ungefilterten
    Signals -- Parameter und Filterkette 1:1 aus app_pages/asian_range_
    breakout.py uebernommen (dieselben apply_*_filter-Funktionen, die laut
    config.py-Docstring bereits gegen die Bridge abgeglichen wurden), nicht
    neu erfunden. Volle Historie seit GOLD_ASB_HISTORY_START noetig, weil die
    Liquiditaets-Schwelle eine expanding Quantile ist (siehe Konstante oben)."""
    from asian_range_breakout.data import fetch_gold_m15
    from asian_range_breakout.engine import simulate_asian_breakout
    from asian_range_breakout.filters import (
        apply_adx_filter, apply_entry_delay_filter, apply_gold_liquidity_filter_causal,
        apply_silver_alignment_filter, apply_trend_bias_filter,
    )
    from asian_range_breakout.sizing import simulate_equity
    from bond_yield_indicator.friction import fetch_fx_friction
    from combined_strategy.data import fetch_timeframe

    # fetch_timeframe() cached unter dem exakten (start, end)-Datumspaar
    # (combined_strategy/data.py::_cache_path) -- mit end=jetzt wuerde JEDER
    # stuendliche Lauf einen NEUEN Cache-Schluessel erzeugen und die vollen
    # ~10 Jahre M15-Gold/Silber komplett frisch von Dukascopy herunterladen
    # (langsam UND die Ursache der beobachteten "KeyError: 0"/Streaming-
    # Aussetzer in der dukascopy_python-Bibliothek bei Live-Abrufen bis genau
    # jetzt). Fix: alte, laengst abgeschlossene Historie bis GESTERN cachen
    # (aendert sich nur einmal pro Tag), nur den kurzen frischen Rest seit
    # gestern wirklich force_refresh=True abrufen und anhaengen.
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
    # simulate_asian_breakout() liefert nur return_pct (roher Preis-Move), KEIN
    # r_multiple -- simulate_equity() rechnet es exakt wie asian_range_breakout/
    # sizing.py (r_multiple = vorzeichenbehafteter Preis-Move / stop_distance)
    # nach; starting_equity/risk_pct hier sind irrelevant, nur die r_multiple-
    # Spalte wird verwendet, die eigentliche Positionsgroesse kommt aus der
    # gemeinsamen Kapitalanteil-Verduennungsformel weiter unten im Modul.
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
    # simulate_cls_practical() liefert nur return_pct + pnl_usd (mit dem
    # Tages-Zins-Multiplikator bereits VERRECHNET in ihrer eigenen internen
    # Equity-Annahme), kein r_multiple. Fuer die gemeinsame Kapitalanteil-
    # Verduennungsformel brauchen wir ein von dieser internen Equity-Annahme
    # unabhaengiges r_multiple: sign*(exit-entry)/sl_distance ist die reine
    # Preis-Bewegung relativ zum Stop (wie asian_range_breakout/sizing.py),
    # multipliziert mit dem TAGES-Zins-Multiplikator (derselbe, der auch beim
    # Backtest -- cls_practical_rXXX.csv-Beinkurven -- bereits standardmaessig
    # in die Rendite eingerechnet ist, siehe rates.py/live_scan.py) --
    # dadurch bleibt die Risiko-Skalierung ueber Trade und Tages-Zinssignal
    # konsistent mit den bereits validierten Backtest-Zahlen.
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
    Rekonstruktion des EK-Portfolios betrafen genau dieses Muster). Greedy-
    Kappung nach Entry-Zeit: ein Trade wird verworfen, wenn zu seinem
    Entry-Zeitpunkt bereits max_concurrent andere (nach ihrer Exit-Zeit)
    noch offene Reversal-Trades laufen -- exakt die Regel, die eine echte
    Bridge angewendet haette."""
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


# Per-Instrument (2026-09-02, gleicher Stand wie app_pages/ny_open_orb_portfolio.py::
# EXIT_CFG_BY_INSTRUMENT / EK-Portfolio-Bridge/config.py nach dem NASDAQ-EOD-Exit-Update
# + Stage-6-Teilausstieg): NASDAQ laeuft bis Handelsschluss (target_mode=None) statt
# 4R-Cap, alle drei Instrumente mit 1.5R/2R-Teilausstieg (50%) + Rest auf Breakeven,
# siehe knowledge/projects/ny-open-orb-sp500.md Stage 6/8/9. Anders als bei
# challenge_portfolio/paper_bot.py (Funded-Portfolio-Bridge sendet ECHTE Orders, kann
# aber nur ganz/offen pro Ticket) ist der Teilausstieg hier unbedenklich: dieses Modul
# treibt nur FKInstantFunding-MT5-Bridge (reiner Order-PLANER, kein echter Order-Versand)
# und FK-Instant-Funding-Paper (reine Simulation) -- keine echte Position, die vom
# Papier-P&L abweichen koennte.
ORB_EXIT_CFG_BY_INSTRUMENT = {
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0,
                  partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0,
                 partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode=None,
                   partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
}
ORB_HISTORY_LOOKBACK_DAYS = 500  # EMA-Ribbon-Bias (4H/1D/1W) braucht Monate an Vorlauf


def _scan_orb(end: pd.Timestamp, force_refresh: bool) -> pd.DataFrame:
    """NY-Open ORB (SP500+US30+NASDAQ), 1:1 die validierte Config aus
    app_pages/ny_open_orb_portfolio.py (siehe knowledge/projects/ny-open-
    orb-sp500.md, Stage 1-5 + Phase 6 abgeschlossen). Anders als die anderen
    5 Beine schliesst ORB IMMER innerhalb derselben NY-Handelssession
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
        # direction ist je nach Engine numerisch (1/-1, strategy.backtest) ODER
        # ein String ("long"/"short", asian_range_breakout/cls_practical) --
        # int(...) wuerde bei Strings crashen, daher roh in den Key. "market"
        # zusaetzlich noetig, weil trend_pullback 5 Instrumente auf denselben
        # "leg"-Schluessel mappt -- ohne market koennten zwei verschiedene
        # Instrumente mit zufaellig identischem entry_time+direction denselben
        # Key erzeugen und sich gegenseitig ueberschreiben.
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
        risk_uncapped = CAPITAL_WEIGHT[t["leg"]] * LEG_RISK_PCT[t["leg"]] * equity
        risk_dollars = min(risk_uncapped, MAX_POSITION_LOSS_DOLLARS)
        pnl = risk_dollars * t["r_multiple"]
        equity += pnl
        rows.append({"exit_time": t["exit_time"], "leg": t["leg"], "risk_dollars": risk_dollars,
                      "risk_capped": risk_uncapped > MAX_POSITION_LOSS_DOLLARS, "pnl": pnl, "equity": equity})
    return pd.DataFrame(rows)


def check_trailing_dd(equity_df: pd.DataFrame, eod_equity_state: dict, as_of: pd.Timestamp) -> tuple[bool, float, float]:
    """EOD-Trailing-Drawdown: Floor = 95% des bisherigen EOD-Hoechststands
    (Regeltext: "floor = previous day's highest equity, moves only up"),
    bewegt sich nur nach oben. `as_of` statt pd.Timestamp.now() -- sonst
    wuerde ein historischer Dry-Run/Backtest-Aufruf faelschlich das ECHTE
    heutige Datum als EOD-Schluessel benutzen statt des simulierten Datums.

    Der Floor darf NUR auf abgeschlossenen VORTAGEN beruhen, niemals auf dem
    noch laufenden heutigen Wert -- sonst wuerde jeder stuendliche Lauf den
    Floor faelschlich an ein reines INTRADAY-Hoch dieses Tages anpassen
    (echter Bug, gefunden beim Regel-Re-Audit vor der echten Kontoanbindung:
    eod_equity_state[today] wurde VOR der running_max-Berechnung gesetzt,
    wodurch der heutige Wert seinen eigenen Floor mitbestimmte). Der heutige
    Stand wird erst NACH dem Vergleich gespeichert, damit er ab dem naechsten
    Kalendertag als abgeschlossener Vortag in die Floor-Berechnung eingeht."""
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

    # Wochenende/Spread-Stunde: kompletter No-Op, kein Datenabruf, kein
    # Telegram, kein State-Write (User-Wunsch 2026-08-29). Ein reiner
    # Backtest-/Test-Aufruf mit explizitem as_of wird NICHT pausiert --
    # sonst koennte man historische Wochenend-Randdaten nie gezielt testen.
    if as_of is None and is_market_paused(end):
        state = dict(state_override) if state_override is not None else load_state()
        return {"date": str(end), "paused": True, "messages": []}, state

    state = dict(state_override) if state_override is not None else load_state()
    if "trades" not in state:
        state = _default_state()
    state.setdefault("eod_equity", {})
    state.setdefault("ctnl_kill_switch_active", False)

    # Kontostart fixieren: manche Scans brauchen JAHRE an Historie fuer ihre
    # eigene Filter-/Indikator-Aufwaermzeit (z.B. Gold ASB's expanding
    # Liquiditaets-Quantile seit 2016), das darf aber nicht heissen, dass
    # deren komplette Mehrjahres-Historie ins gemeinsame Paper-Konto einfliesst
    # -- sonst compoundiert das Konto de facto Gold-ASB-Trades seit 2016,
    # waehrend jedes andere Bein erst seit ein paar Monaten mitzaehlt (genau
    # der Bug, der den ersten Live-Lauf "surreal" aussehen liess: +32% "seit
    # heute" war in Wahrheit ein 10-Jahre-Gold-ASB-Backtest mit ein paar
    # Monaten der anderen 5 Beine oben drauf). account_start wird beim
    # allerersten Lauf einmalig auf `end` gesetzt und danach persistiert --
    # nur Trades mit entry_time >= account_start zaehlen fuers Paper-Konto.
    if state.get("account_start") is None:
        state["account_start"] = end.isoformat()
    account_start = pd.Timestamp(state["account_start"])

    def _since_start(trades: pd.DataFrame) -> pd.DataFrame:
        if trades.empty:
            return trades
        return trades[_utc_naive(trades["entry_time"]) >= account_start]

    # Scan-Fehler pro Kalendertag mitschreiben (fuer die "hat heute alles
    # funktioniert?"-Zeile im Tagesabschluss, Nutzer-Wunsch 2026-08-29) --
    # Reset bei Tageswechsel, analog zum last_daily_summary_day-Muster unten.
    # ECHTER lokaler Kalendertag (nicht UTC) -- Bug gefunden 2026-08-31: ein
    # Lauf um 01:20 Uhr lokal ist noch 23:20 Uhr UTC des VORTAGS, ein UTC-
    # basierter Tagesschluessel haette die Fehler dieses Laufs faelschlich
    # als "gestern" gezaehlt und beim naechsten Lauf (der schon UTC-Mitternacht
    # ueberschritten hatte) sofort wieder zurueckgesetzt -- genau das ist
    # heute passiert (4 Fehler um 01:20 verschwanden, bevor der Tagesabschluss
    # sie je zeigen konnte).
    current_day_key = _local_dt(end).strftime("%Y-%m-%d")
    if state.get("scan_errors_today", {}).get("day") != current_day_key:
        state["scan_errors_today"] = {"day": current_day_key, "legs": []}

    messages = []
    try:
        gold_asb_trades = _since_start(_retry(lambda: _scan_gold_asb(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "gold_asb", gold_asb_trades)
    except Exception as e:
        messages.append(f"⚠️ Gold-ASB-Scan fehlgeschlagen: {e}")
        state["scan_errors_today"]["legs"].append("Gold ASB")

    try:
        cls_trades = _since_start(_retry(lambda: _scan_cls_practical(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "cls_practical", cls_trades)
    except Exception as e:
        messages.append(f"⚠️ CLS-Practical-Scan fehlgeschlagen: {e}")
        state["scan_errors_today"]["legs"].append("CLS Practical")

    try:
        tp_trades = _since_start(_retry(lambda: _scan_trend_pullback(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "trend_pullback", tp_trades)
    except Exception as e:
        messages.append(f"⚠️ Trend-Pullback-Scan fehlgeschlagen: {e}")
        state["scan_errors_today"]["legs"].append("Trend Pullback")

    try:
        cont_trades, rev_trades = _retry(lambda: _scan_ctnl(end, force_refresh=not dry_run))
        messages += _merge_trades(state, "ctnl_continuation", _since_start(cont_trades))
        messages += _merge_trades(state, "ctnl_reversal", _since_start(rev_trades))
    except Exception as e:
        messages.append(f"⚠️ CTNL-Edge-Scan fehlgeschlagen: {e}")
        state["scan_errors_today"]["legs"].append("CTNL Edge")

    try:
        gsd_trades = _since_start(_retry(lambda: _scan_gold_silver(end, force_refresh=not dry_run)))
        messages += _merge_trades(state, "gold_silver", gsd_trades)
    except Exception as e:
        messages.append(f"⚠️ Gold-Silber-Divergenz-Scan fehlgeschlagen: {e}")
        state["scan_errors_today"]["legs"].append("Gold-Silber-Divergenz")

    try:
        orb_trades = _since_start(_retry(lambda: _scan_orb(end, force_refresh=not dry_run)))
        orb_leg_by_market = {"SP500": "orb_sp500", "US30": "orb_us30", "NASDAQ": "orb_nasdaq"}
        if not orb_trades.empty:
            for market, sub in orb_trades.groupby("market"):
                messages += _merge_trades(state, orb_leg_by_market[market], sub)
    except Exception as e:
        messages.append(f"⚠️ NY-Open-ORB-Scan fehlgeschlagen: {e}")
        state["scan_errors_today"]["legs"].append("NY-Open ORB")

    equity_df = compute_shared_equity(state)
    dd_breached, current_dd, dd_floor = check_trailing_dd(equity_df, state["eod_equity"], end)
    consistency_ratio, payout_safe, cum_profit = check_consistency(equity_df)
    current_equity = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else STARTING_EQUITY

    if dd_breached and not state.get("kill_switch_active", False):
        state["kill_switch_active"] = True
        messages.append(
            f"\U0001F6A8 KILL-SWITCH: Trailing-Drawdown {current_dd:.2%} unter dem "
            f"5%-Floor (${dd_floor:,.0f}). Neue Entries pruefen/pausieren."
        )
    elif not dd_breached and state.get("kill_switch_active", False) and current_dd >= -TRAILING_DD_PCT * 0.5:
        state["kill_switch_active"] = False  # Erholung ueber die Haelfte der Schwelle - Reset

    # CTNL-eigener Kill-Switch (Nutzerauftrag 2026-09-03): der urspruengliche, in
    # gold_smc_htf_ltf/paper_bot.py gebaute Monitor (Stand-alone Cont+Rev-Drawdown gegen
    # die Phase-6-P5-Schwelle) lief NUR in der eigenstaendigen "CTNL-Edge-FK-Paper"-Task,
    # die am 2026-08-27 bei der Portfolio-Konsolidierung deaktiviert wurde -- diese
    # spezifische Pruefung wurde dabei NICHT in die 3 Nachfolge-Bots uebernommen. Hier
    # nachgeruestet, auf einem EIGENEN 100k-Stand-alone-Konto (ctnl_standalone_drawdown()),
    # unbeeindruckt von der Monte-Carlo-optimierten CAPITAL_WEIGHT-Verduennung.
    try:
        ctnl_all = _state_trades_df(state)
        ctnl_dd = ctnl_standalone_drawdown(
            ctnl_all[ctnl_all["leg"] == "ctnl_continuation"], ctnl_all[ctnl_all["leg"] == "ctnl_reversal"]
        )
        if ctnl_dd < CTNL_KILL_SWITCH_DD_THRESHOLD and not state.get("ctnl_kill_switch_active", False):
            state["ctnl_kill_switch_active"] = True
            messages.append(
                f"\U0001F6A8 CTNL-KILL-SWITCH: Stand-alone Cont+Rev-Drawdown {ctnl_dd:.2%} unter der "
                f"Phase-6-P5-Schwelle ({CTNL_KILL_SWITCH_DD_THRESHOLD:.2%}). CTNL-Entries pruefen/pausieren, "
                f"Phase 6 auf frischeren Daten neu durchlaufen."
            )
        elif ctnl_dd >= CTNL_KILL_SWITCH_DD_THRESHOLD * 0.5 and state.get("ctnl_kill_switch_active", False):
            state["ctnl_kill_switch_active"] = False  # Erholung ueber die Haelfte der Schwelle - Reset
    except Exception as e:
        messages.append(f"⚠️ CTNL-Kill-Switch-Check fehlgeschlagen: {e}")

    row = {
        "date": str(end), "equity": current_equity, "current_dd": current_dd,
        "consistency_ratio": consistency_ratio, "payout_safe": payout_safe, "cum_profit": cum_profit,
        "kill_switch_active": state.get("kill_switch_active", False),
        "ctnl_kill_switch_active": state.get("ctnl_kill_switch_active", False), "n_trades": len(state["trades"]),
    }

    # Taeglicher statt stuendlicher Status (User-Wunsch, 2026-08-27: "keine
    # stuendlichen Logs mehr ... nur noch wenn aktive Trades erkannt werden
    # und am Ende des Tages einen kleinen Tagesabschluss") - Kill-Switch-/
    # Scan-Fehler-Meldungen oben (`messages`) bleiben Sofort-Alarme INNERHALB
    # dieses Scan-Laufs (werden weiter unten zu EINER Nachricht gebuendelt,
    # Nutzer-Wunsch 2026-08-29), nur dieser Routine-Status wird auf einmal/Tag reduziert.
    if state.get("last_daily_summary_day") != current_day_key and _local_dt(end).hour >= DAILY_SUMMARY_HOUR:
        state["last_daily_summary_day"] = current_day_key
        payout_label = "ZULAESSIG" if payout_safe else "NICHT zulaessig (Verhaeltnis > 30%)"
        failed_legs = state.get("scan_errors_today", {}).get("legs", [])
        if failed_legs:
            fail_counts: dict[str, int] = {}
            for leg_name in failed_legs:
                fail_counts[leg_name] = fail_counts.get(leg_name, 0) + 1
            health_line = "System: ⚠️ Scan-Fehler heute bei " + ", ".join(
                f"{leg_name} ({n}x)" for leg_name, n in fail_counts.items()
            )
        else:
            health_line = "System: ✅ alle Scans liefen heute fehlerfrei"
        heartbeat_msg = _fk_message(f"Tagesabschluss {end.strftime('%Y-%m-%d')}", [
            health_line,
            f"Equity: ${current_equity:,.0f}  |  Trailing-DD: {current_dd:.2%} (Floor ${dd_floor:,.0f})",
            f"Trades gesamt: {len(state['trades'])}  |  Kill-Switch: {'AKTIV' if state['kill_switch_active'] else 'ok'}",
            f"Konsistenz-Verhaeltnis: {consistency_ratio:.1%}  |  Auszahlung: {payout_label}",
        ])
        if not dry_run:
            send_telegram_message(heartbeat_msg)
            LOG_DIR.mkdir(exist_ok=True)
            is_new = not HEARTBEAT_CSV.exists()
            with open(HEARTBEAT_CSV, "a", encoding="utf-8") as f:
                if is_new:
                    f.write("date,equity,current_dd,consistency_ratio,payout_safe,kill_switch_active,n_trades\n")
                f.write(f"{end.isoformat()},{current_equity:.2f},{current_dd:.4f},{consistency_ratio:.4f},"
                        f"{payout_safe},{state['kill_switch_active']},{len(state['trades'])}\n")

    # Alle Ereignisse DIESES Scan-Laufs (Entries/Exits/Fehler/Kill-Switch) als
    # EINE gebuendelte Telegram-Nachricht statt einer pro Strategie (Nutzer-
    # Wunsch 2026-08-29) -- ueber dieselbe queue_message()/flush_queued_
    # messages()-Infrastruktur wie EK-Portfolio-Bridge/Funded-Portfolio-Bridge
    # (Fund 2026-09-02, vorher eigener Code-Pfad mit gleichem Ergebnis). `messages`
    # bleibt als lokale Liste fuer den Rueckgabewert (row["messages"]) unveraendert
    # bestehen, wird zusaetzlich durch die gemeinsame Queue geschickt.
    if not dry_run:
        for m in messages:
            queue_message(m)
        flush_queued_messages()
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
