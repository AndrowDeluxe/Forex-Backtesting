"""Gold ASB als ruhende Stop-Order -- geteilte Logik fuer alle drei Bridges
(Funded-Portfolio, FK Instant Funding, EK-Portfolio), 2026-10-01.

WARUM: der Backtest (engine.py) modelliert seit jeher eine RUHENDE OCO-Stop-
Order am Range-Level. Live lief dagegen in allen drei Bridges eine Marktorder
~30 Min. nach dem Ausbruch, EK verankerte den SL zusaetzlich am Live-Kurs neu.
Kosten-/Optimierungspruefung 2026-10-01 (knowledge/projects/gold-asb-
kostenvalidierung.md): Lag war fuer Funded Rauschen, EKs Neuverankerung kostete
~0,05 R/Trade und hob den Drawdown von -5,9 auf -8,6 R. Nutzerentscheid
2026-10-01: Stop-Order-Logik wie bei ORB, Stop 1,5x Range, Storno 03:00 NY,
EK mit absolutem SL. Kein Rueckfall auf Marktorders.

EINE Implementierung, drei Nutzer -- gleiches Muster wie ribbon_gate/
ctnl_kill_switch. Die Bridges holen nur die Broker-Bars und fuehren die Orders;
was heute gehandelt wird, entscheidet allein todays_setup().

HOECHSTENS EINE ORDER JE TAG: Trend- und Silberfilter legen die Richtung fest
(long nur bei Gold > SMA200 UND Silber steigend, short nur umgekehrt). Die
OCO-Semantik des Backtests ("bricht zuerst die Gegenseite, gibt es heute keinen
Trade") bilden die Bridges ueber opposite_level nach.

ADX KAUSAL: gelesen an der 00:45-Bar (schliesst um 01:00), nicht an der
01:00-Bar wie die Engine bis 2026-10-01 (die schliesst erst 01:15 -- eine Bar
Lookahead). Gemessen 2016-2026: kippt den Filter an 3,1 % der Tage, Ergebnis
gleich bis leicht besser (Oe R +0,295 statt +0,285). engine.py ist im selben
Zug angeglichen, damit Paper-Simulation und Live dieselbe Entscheidung treffen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --- Parameter: Single Source of Truth (auch fuer die drei Paper-Bots) --------
HISTORY_START = "2016-01-01"
RANGE_START = "21:00"          # NY, Vortag
RANGE_END = "01:00"            # NY, Range-Schluss = fruehester Platzierungszeitpunkt
CANCEL_TIME = "03:00"          # NY, ungefuellte Order wird storniert (Nutzerentscheid 2026-10-01)
EXIT_TIME = "11:00"            # NY, Zeit-Exit (unveraendert)
STOP_FRAC = 1.5                # x Range-Breite (Nutzerentscheid 2026-10-01, vorher 1.0)
MAX_DELAY_BARS = 7             # Engine-Aequivalent zu CANCEL_TIME: Fill-Bars 01:15..02:45 (vorher 3 = 02:00)
ADX_MIN = 15.0
TREND_SMA_WINDOW = 200
SILVER_ALIGNMENT_WINDOW = 5
LIQUIDITY_QUANTILE = 2 / 3
LIQUIDITY_MIN_PERIODS = 250
MAX_STALE_TRADING_DAYS = 2     # Ausfall-Ersatz: so viele Handelstage duerfen die Filterdaten hinterherhinken
STALE_FALLBACK_ENABLED = False # Ausfall-Ersatz aus (Nutzerentscheid 2026-11-02: Backtest Oe +0,08 R, t 1,16)

NY = "America/New_York"
LEG = "gold_asb"
SYMBOL_KEY = "XAUUSD"


def _hm(hhmm: str) -> tuple[int, int]:
    h, m = hhmm.split(":")
    return int(h), int(m)


def session_times(day: pd.Timestamp) -> dict:
    """Alle Zeitpunkte eines Handelstags (NY-Datum `day`) als tz-aware NY."""
    d = pd.Timestamp(day).tz_localize(NY) if pd.Timestamp(day).tzinfo is None else pd.Timestamp(day).tz_convert(NY)
    d = d.normalize()

    def at(hhmm, base=d):
        h, m = _hm(hhmm)
        return base + pd.Timedelta(hours=h, minutes=m)

    return {
        "range_start": at(RANGE_START, d - pd.Timedelta(days=1)),
        "range_end": at(RANGE_END),
        "cancel_at": at(CANCEL_TIME),
        "exit_at": at(EXIT_TIME),
    }


# --- Daten fuer die Vortagsfilter (identisch zu frueher _scan_gold_asb) -------

def load_inputs(end: pd.Timestamp, force_refresh: bool, *, source: str = "live", allow_stale: bool = False) -> dict:
    """Gold-M15 (Dukascopy + Lake-Frischteil), Tagesschluesse Gold/Silber und
    Corwin-Schultz-Friktion. Vorher in drei identischen Kopien in den Paper-Bots
    (challenge_portfolio/fk_instant_funding/ek_portfolio::_scan_gold_asb);
    Begruendung der alt/neu-Aufteilung dort (stabiler Monatsanfang als Cache-Grenze)."""
    from asian_range_breakout.data import fetch_gold_m15
    from bond_yield_indicator.friction import fetch_fx_friction
    from combined_strategy.data import fetch_timeframe

    outage: dict = {}
    if source == "lake":
        import data_lake.reader as _lake
        fallback = ((lambda lake, live: _lake.with_stale_fallback(lake, live, outage))
                    if allow_stale and STALE_FALLBACK_ENABLED else _lake.with_live_fallback)
        fetch_gold_m15_new = fallback(_lake.fetch_gold_m15, fetch_gold_m15)
        fetch_timeframe_new = fallback(_lake.fetch_timeframe, fetch_timeframe)
        fetch_fx_friction_new = fallback(_lake.fetch_fx_friction, fetch_fx_friction)
    else:
        fetch_gold_m15_new, fetch_timeframe_new, fetch_fx_friction_new = fetch_gold_m15, fetch_timeframe, fetch_fx_friction

    end_str = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    stable_end_str = end.normalize().replace(day=1).strftime("%Y-%m-%d")

    def _concat_fresh(old, new):
        if old.empty:
            return new
        if new.empty:
            return old
        combined = pd.concat([old, new])
        return combined[~combined.index.duplicated(keep="last")].sort_index()

    gold_m15 = _concat_fresh(fetch_gold_m15(HISTORY_START, stable_end_str, force_refresh=False),
                             fetch_gold_m15_new(stable_end_str, end_str, force_refresh=force_refresh))
    silver_m15 = _concat_fresh(fetch_timeframe("SILVER", "M15", HISTORY_START, stable_end_str, force_refresh=False),
                               fetch_timeframe_new("SILVER", "M15", stable_end_str, end_str, force_refresh=force_refresh))
    friction = _concat_fresh(fetch_fx_friction("GOLD", HISTORY_START, stable_end_str, force_refresh=False),
                             fetch_fx_friction_new("GOLD", stable_end_str, end_str, force_refresh=force_refresh))
    daily_close = (gold_m15["close"].tz_localize(None).resample("D").last().dropna()
                   if not gold_m15.empty else pd.Series(dtype=float))
    daily_close_silver = (silver_m15["Close"].tz_localize(None).resample("D").last().dropna()
                          if not silver_m15.empty else pd.Series(dtype=float))
    return {"gold_m15": gold_m15, "daily_close": daily_close,
            "daily_close_silver": daily_close_silver, "friction": friction,
            "stale": bool(outage.get("stale"))}


def live_state_friction(gold_m15: pd.DataFrame, d1: pd.DataFrame) -> pd.Series:
    """Corwin-Schultz fuer Tag t mit Tag t+1 nur bis 01:00 NY -- der Wissensstand der
    Bridges bei Range-Ende. corwin_schultz_spread nutzt den VOLLEN Tag t+1, der Backtest
    sieht damit den Handelstag (+0,308 vs. live +0,168 R, 2026-11-01). Nur fuer
    Sollwerte/Ampel (liquidity="live"); der Filter selbst bleibt unveraendert, die
    Korrektur fiel im OOS durch (knowledge/projects/gold-asb-liquiditaetsfilter-vorgriff.md)."""
    from bond_yield_indicator.friction import _K

    m = gold_m15.tz_convert("UTC")
    hp, lp = [], []
    for bar in d1.index:
        bar = bar.tz_convert("UTC")
        re = (pd.Timestamp(bar.date()).tz_localize(NY) + pd.Timedelta(hours=1)).tz_convert("UTC")
        w = m[(m.index >= bar) & (m.index < re)]
        hp.append(w["high"].max() if len(w) else np.nan)
        lp.append(w["low"].min() if len(w) else np.nan)
    H, L = d1["High"], d1["Low"]
    h2n, l2n = pd.Series(hp, index=d1.index).shift(-1), pd.Series(lp, index=d1.index).shift(-1)
    h2 = pd.concat([H, h2n], axis=1).max(axis=1)
    l2 = pd.concat([L, l2n], axis=1).min(axis=1)
    gamma = np.log(h2 / l2) ** 2
    beta = (np.log(H / L) + np.log(h2n / l2n)) ** 2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / _K - np.sqrt(gamma / _K)
    s = (2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))).where(h2n.notna())
    s.index = s.index.tz_localize(None)
    return s


def _trade_day(trades: pd.DataFrame) -> pd.Series:
    return trades["entry_time"].dt.tz_localize(None).dt.normalize().dt.strftime("%Y-%m-%d")


def _apply_journal(raw: pd.DataFrame, filtered: pd.DataFrame, journal: dict) -> tuple[pd.DataFrame, list[str]]:
    """Tage mit Bot-Protokoll: Trend/Silber/Liquiditaet/ADX wie der Bot entschieden hat, nur
    die Einstiegs-Verzoegerung bleibt Sim. Uebrige Tage behalten die Filterkette. Drift = Tage,
    an denen die Nachrechnung (`filtered`) anders entschieden haette als der Bot."""
    from asian_range_breakout.filters import apply_entry_delay_filter

    in_j_raw = _trade_day(raw).isin(journal.keys())
    jt = apply_entry_delay_filter(raw[in_j_raw], max_delay_bars=MAX_DELAY_BARS)
    if not jt.empty:
        days = _trade_day(jt)
        sign = jt["direction"].map({"long": 1, "short": -1})
        keep = [journal[d]["filter_direction"] == s and (journal[d]["adx"] is None or journal[d]["adx"] >= ADX_MIN)
                for d, s in zip(days, sign)]
        jt = jt[keep]
    rest = filtered[~_trade_day(filtered).isin(journal.keys())] if not filtered.empty else filtered
    bot_days = set(_trade_day(jt)) if not jt.empty else set()
    sim_days = set(_trade_day(filtered)) & set(journal.keys()) if not filtered.empty else set()
    drift = sorted(bot_days ^ sim_days)
    out = pd.concat([rest, jt]).sort_values("entry_time") if not jt.empty else rest
    return out, drift


def scan_trades(end: pd.Timestamp, force_refresh: bool, *, source: str = "live", utc_naive=None,
                liquidity: str = "backtest", journal: dict | None = None) -> pd.DataFrame:
    """Simulierte Trades mit der Produktions-Filterkette -- frueher der Rumpf von
    _scan_gold_asb in allen drei Paper-Bots. Dient Paper-Simulation, Soll/Ist und
    Reports; die Bridges handeln NICHT mehr daraus, sondern ueber todays_setup().

    liquidity="live" (seit 2026-11-02, fuer Soll/Ist): Friktionswert auf dem
    Wissensstand 01:00 NY statt mit vollem Folgetag, Schwelle unveraendert.

    journal (seit 2026-11-10, read_journal()): an protokollierten Tagen gilt die Filter-
    Entscheidung des Bots; `trades.attrs["journal_drift"]` listet die Tage, an denen die
    Nachrechnung anders entschieden haette."""
    from asian_range_breakout.engine import simulate_asian_breakout
    from asian_range_breakout.filters import (
        apply_adx_filter, apply_entry_delay_filter, apply_gold_liquidity_filter_causal,
        apply_silver_alignment_filter, apply_trend_bias_filter,
    )
    from asian_range_breakout.sizing import simulate_equity

    inp = load_inputs(end, force_refresh, source=source)
    df = inp["gold_m15"]
    if df.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])
    trades = simulate_asian_breakout(df, range_start=RANGE_START, range_end=RANGE_END,
                                     exit_time=EXIT_TIME, stop_frac=STOP_FRAC)
    if trades.empty:
        return trades
    raw = trades
    trades = apply_adx_filter(trades, adx_min=ADX_MIN)
    trades = apply_trend_bias_filter(trades, inp["daily_close"], sma_window=TREND_SMA_WINDOW)
    trades = apply_entry_delay_filter(trades, max_delay_bars=MAX_DELAY_BARS)
    trades = apply_silver_alignment_filter(trades, inp["daily_close_silver"], window=SILVER_ALIGNMENT_WINDOW)
    if liquidity == "live":
        from asian_range_breakout.filters import attach_series_level, rolling_liquidity_threshold
        from combined_strategy.data import fetch_timeframe
        fetch_d1 = fetch_timeframe
        if source == "lake":
            import data_lake.reader as _lake
            fetch_d1 = _lake.with_live_fallback(_lake.fetch_timeframe, fetch_timeframe)
        # Lake-D1 reicht nur ~1,5 Jahre zurueck: Historie aus dem Cache, Frischteil aus dem Lake
        stable_end_str = end.normalize().replace(day=1).strftime("%Y-%m-%d")
        d1 = pd.concat([fetch_timeframe("GOLD", "D1", HISTORY_START, stable_end_str, force_refresh=False),
                        fetch_d1("GOLD", "D1", stable_end_str, (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                                 force_refresh=force_refresh)])
        d1 = d1[~d1.index.duplicated(keep="last")].sort_index()
        thr = rolling_liquidity_threshold(inp["friction"], quantile=LIQUIDITY_QUANTILE,
                                          min_periods=LIQUIDITY_MIN_PERIODS)
        trades = attach_series_level(trades, live_state_friction(df, d1), "friction_prior")
        trades = attach_series_level(trades, thr, "friction_thr").dropna(subset=["friction_prior", "friction_thr"])
        trades = trades[trades["friction_prior"] <= trades["friction_thr"]]
    else:
        trades = apply_gold_liquidity_filter_causal(trades, inp["friction"], quantile=LIQUIDITY_QUANTILE,
                                                    min_periods=LIQUIDITY_MIN_PERIODS)
    drift: list[str] = []
    if journal:
        trades, drift = _apply_journal(raw, trades, journal)
    if trades.empty:
        trades.attrs["journal_drift"] = drift
        return trades
    trades = simulate_equity(trades, starting_equity=100_000.0, risk_pct=0.005)
    trades.attrs["journal_drift"] = drift
    if utc_naive is not None:
        trades = trades[utc_naive(trades["entry_time"]) <= end]
    return trades


def prior_day_filters(inputs: dict, day: pd.Timestamp) -> dict:
    """Trend, Silber und Liquiditaet fuer Handelstag `day` (NY-Datum) -- exakt die
    Ausrichtung der apply_*-Filter (Wert des letzten Tages STRIKT vor dem
    Entry-Datum), deshalb ueber dieselben attach_*-Funktionen statt nachgebaut."""
    from asian_range_breakout.filters import attach_series_change, attach_series_level, rolling_liquidity_threshold

    t = session_times(day)["range_end"]
    row = pd.DataFrame({"entry_time": [t]})
    dc = inputs["daily_close"]
    row = attach_series_level(row, dc, "gold_close_prior")
    row = attach_series_level(row, dc.rolling(TREND_SMA_WINDOW).mean(), "gold_sma_prior")
    row = attach_series_change(row, inputs["daily_close_silver"], "silver_chg", window=SILVER_ALIGNMENT_WINDOW)
    row = attach_series_level(row, inputs["friction"], "friction_prior")
    thr = rolling_liquidity_threshold(inputs["friction"], quantile=LIQUIDITY_QUANTILE, min_periods=LIQUIDITY_MIN_PERIODS)
    row = attach_series_level(row, thr, "friction_thr")
    r = row.iloc[0]
    vals = {k: (None if pd.isna(r[k]) else float(r[k]))
            for k in ("gold_close_prior", "gold_sma_prior", "silver_chg", "friction_prior", "friction_thr")}
    vals["day"] = pd.Timestamp(day).date().isoformat()
    # Datum des verwendeten Friktionswerts (2026-11-10): zeigt im Filter-Protokoll, ob der
    # Vortag (mit halbem Handelstag) oder ein aelterer Tag den Ausschlag gab.
    fr_idx = inputs["friction"].dropna().sort_index().index
    if getattr(fr_idx, "tz", None) is not None:
        fr_idx = fr_idx.tz_localize(None)
    pos = fr_idx.searchsorted(pd.Timestamp(day).normalize(), side="left") - 1
    vals["friction_date"] = fr_idx[pos].date().isoformat() if pos >= 0 else None
    if inputs.get("stale"):
        # Ausfall-Ersatz: aelterer Tagesstand von Gold/Silber, Tagesgrenze wie beim Filter. Friktion zaehlt
        # nicht mit: ihr Wert von t braucht Tag t+1 und hinkt deshalb immer einen Tag hinterher.
        cutoff = pd.Timestamp(day).normalize()
        through = min(s[s.index < cutoff].index.max() for s in (inputs["daily_close"], inputs["daily_close_silver"]))
        lag = int(np.busday_count(through.date(), cutoff.date())) - 1
        if lag > MAX_STALE_TRADING_DAYS:
            raise ValueError(f"Filterdaten {lag} Handelstage alt (Stand {through.date()}), "
                             f"Grenze {MAX_STALE_TRADING_DAYS}")
        vals.update(stale=True, data_through=through.date().isoformat(), stale_trading_days=lag)
    return vals


def stale_note(filters: dict) -> str:
    """Zusatz fuer die Telegram-Meldung, wenn die Order auf dem Ausfall-Ersatz beruht."""
    if not filters.get("stale"):
        return ""
    return f" | ⚠️ Dukascopy-Ausfall: Filter auf Stand {filters['data_through']}"


def allowed_direction(filters: dict) -> tuple[int | None, str]:
    """Richtung, die heute handeln darf, oder (None, Grund)."""
    f = filters
    if any(f.get(k) is None for k in ("gold_close_prior", "gold_sma_prior", "silver_chg", "friction_prior", "friction_thr")):
        return None, "Filterdaten unvollstaendig"
    if f["friction_prior"] > f["friction_thr"]:
        return None, f"Liquiditaet: Friktion {f['friction_prior']:.5f} > Schwelle {f['friction_thr']:.5f}"
    trend_up = f["gold_close_prior"] > f["gold_sma_prior"]
    if trend_up and f["silver_chg"] > 0:
        return 1, "long (Trend auf, Silber steigend)"
    if not trend_up and f["silver_chg"] < 0:
        return -1, "short (Trend ab, Silber fallend)"
    return None, f"Trend {'auf' if trend_up else 'ab'} vs. Silber {f['silver_chg']:+.2f} % -- keine Uebereinstimmung"


def _adx_at(m15: pd.DataFrame, label: pd.Timestamp) -> float | None:
    from strategy.indicators import compute_adx
    adx = compute_adx(m15)["adx"]
    if label not in adx.index:
        return None
    v = adx.loc[label]
    return None if pd.isna(v) else float(v)


JOURNAL_NAME = "gold_asb_filter_journal.jsonl"
_JOURNAL_KEYS = ("gold_close_prior", "gold_sma_prior", "silver_chg", "friction_prior", "friction_thr",
                 "friction_date", "stale")


def journal_path() -> Path | None:
    """Protokolldatei der laufenden Bridge (`<…-Bridge>/logs/`), sonst None -- Research-
    Skripte und Tests schreiben nichts. Liegt ausserhalb von Git (kein Push-Stau)."""
    try:
        root = Path(sys.argv[0]).resolve().parent
    except (OSError, IndexError):
        return None
    return root / "logs" / JOURNAL_NAME if root.name.endswith("-Bridge") else None


def _journal(setup: dict, filters: dict, path: Path | None = None) -> None:
    """Filter-Entscheidung des Bots je Tag protokollieren (Nutzerentscheid 2026-11-10: Soll/Ist
    uebernimmt diese Entscheidung, statt sie mit spaeter ueberarbeiteten Daten nachzurechnen;
    knowledge/projects/gold-asb-liquiditaetsfilter-vorgriff.md). Nur ab Range-Ende, eine Zeile
    je Aenderung. Darf nie eine Order verhindern: Fehler werden nur ausgegeben."""
    if setup.get("status") in ("range_not_ready", "window_over"):
        return
    path = path or journal_path()
    if path is None:
        return
    try:
        direction, why = allowed_direction(filters)
        row = {"logged_at": pd.Timestamp.now(tz="UTC").isoformat(), "day": setup.get("day"),
               "status": setup.get("status"), "filter_direction": direction, "filter_detail": why,
               "adx": setup.get("adx"), "detail": setup.get("detail"),
               **{k: filters.get(k) for k in _JOURNAL_KEYS}}
        sig = (row["day"], row["status"], direction, row["friction_prior"], row["adx"] is None)
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                lines = fh.readlines()[-20:]
            for ln in reversed(lines):
                prev = json.loads(ln)
                if prev.get("day") == row["day"]:
                    if (prev.get("day"), prev.get("status"), prev.get("filter_direction"),
                            prev.get("friction_prior"), prev.get("adx") is None) == sig:
                        return
                    break
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 -- Protokoll ist Beiwerk
        print(f"Gold-ASB-Filterprotokoll nicht geschrieben: {type(exc).__name__}: {exc}")


def read_journal(path: Path) -> dict[str, dict]:
    """Je Tag die Bot-Entscheidung: Filterrichtung aus der ersten Zeile ab Range-Ende, ADX aus
    der ersten Zeile, die ihn kennt. {"2026-11-03": {"filter_direction": -1, "adx": 22.1}}"""
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        for ln in fh:
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            d = out.setdefault(r["day"], {"filter_direction": r.get("filter_direction"), "adx": None})
            if d["adx"] is None and r.get("adx") is not None:
                d["adx"] = r["adx"]
    return out


def todays_setup(m15_broker: pd.DataFrame, now_utc, filters: dict) -> dict:
    setup = _todays_setup(m15_broker, now_utc, filters)
    _journal(setup, filters)
    return setup


def _todays_setup(m15_broker: pd.DataFrame, now_utc, filters: dict) -> dict:
    """Entscheidung fuer den Handelstag, in dessen Platzierungsfenster `now_utc` liegt.

    m15_broker: Broker-M15 (Spalten open/high/low/close, Index tz-aware NY), mind.
    ~5 Handelstage Historie fuer den ADX-Vorlauf. Die laufende Bar darf enthalten
    sein (MT5 liefert sie mit) -- sie zaehlt fuer die Ausbruchs-Pruefung mit.
    filters: prior_day_filters() fuer genau diesen Tag.

    Status: setup | range_not_ready | window_over | levels_pending_data |
            no_data | filtered_out | breakout_passed | opposite_broken"""
    now_ny = pd.Timestamp(now_utc).tz_convert(NY)
    day = now_ny.normalize()
    t = session_times(day)
    base = {"day": day.date().isoformat(), "cancel_at": t["cancel_at"].isoformat(),
            "exit_at": t["exit_at"].isoformat(), "range_end": t["range_end"].isoformat()}
    if filters.get("day") != base["day"]:
        return {**base, "status": "no_data", "detail": f"Filter fuer {filters.get('day')}, nicht {base['day']}"}
    if now_ny < t["range_end"]:
        return {**base, "status": "range_not_ready"}
    if now_ny >= t["cancel_at"]:
        return {**base, "status": "window_over"}

    m15 = m15_broker[m15_broker.index <= now_ny]
    win = m15[(m15.index >= t["range_start"]) & (m15.index < t["range_end"])]
    last_label = t["range_end"] - pd.Timedelta(minutes=15)
    if win.empty or win.index.max() < last_label:
        return {**base, "status": "levels_pending_data"}
    if len(win) < 8:   # von 16 Bars -- Feiertag/Wochenstart ohne echte Asien-Session
        return {**base, "status": "no_data", "detail": f"nur {len(win)} Range-Bars"}
    r_hi, r_lo = float(win["high"].max()), float(win["low"].min())
    rng = r_hi - r_lo
    if not rng > 0:
        return {**base, "status": "no_data", "detail": "Range-Breite 0"}

    adx = _adx_at(m15, last_label)
    if adx is None:
        return {**base, "status": "no_data", "detail": "ADX nicht berechenbar"}
    base.update(range_high=r_hi, range_low=r_lo, range_width=rng, adx=adx)
    if adx < ADX_MIN:
        return {**base, "status": "filtered_out", "detail": f"ADX {adx:.1f} < {ADX_MIN}"}
    direction, why = allowed_direction(filters)
    if direction is None:
        return {**base, "status": "filtered_out", "detail": why}

    level = r_hi if direction == 1 else r_lo
    opposite = r_lo if direction == 1 else r_hi
    after = m15[m15.index >= t["range_end"]]
    if not after.empty:
        hit_own = (after["high"] >= level) if direction == 1 else (after["low"] <= level)
        hit_opp = (after["low"] <= opposite) if direction == 1 else (after["high"] >= opposite)
        if hit_own.any() or hit_opp.any():
            first_own = after.index[hit_own.to_numpy()].min() if hit_own.any() else None
            first_opp = after.index[hit_opp.to_numpy()].min() if hit_opp.any() else None
            if first_opp is not None and (first_own is None or first_opp < first_own):
                return {**base, "status": "opposite_broken", "detail": f"Gegenseite {opposite:.2f} zuerst"}
            return {**base, "status": "breakout_passed", "detail": f"Level {level:.2f} vor Platzierung beruehrt"}

    stop = level - direction * STOP_FRAC * rng
    return {**base, "status": "setup", "direction": direction, "level": level, "opposite_level": opposite,
            "stop": stop, "detail": why}


def opposite_touched_first(bars: pd.DataFrame, direction: int, opposite_level: float,
                           since: pd.Timestamp, fill_time: pd.Timestamp | None = None) -> bool:
    """Wurde die Gegenseite seit `since` beruehrt -- und, falls `fill_time` gegeben,
    VOR dem Fill? `bars` am besten M1 (Broker, NY-Index). Fuer den Gegenseiten-
    Waechter der Bridges: pending -> stornieren; schon gefuellt, aber Gegenseite
    war frueher -> Position schliessen (Backtest haette heute nicht gehandelt)."""
    b = bars[bars.index >= pd.Timestamp(since).tz_convert(NY)]
    if fill_time is not None:
        b = b[b.index < pd.Timestamp(fill_time).tz_convert(NY).floor("min")]
    if b.empty:
        return False
    hit = (b["low"] <= opposite_level) if direction == 1 else (b["high"] >= opposite_level)
    return bool(np.asarray(hit).any())
