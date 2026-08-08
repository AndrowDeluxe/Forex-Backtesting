"""CLS-Settle-Breakout - Gold-Variante der Asian-Range-Breakout-Idee, auf
Vorschlag des Users (2026-08-05), basierend auf einer Beobachtung aus den
bereits erforschten CLS-Settlement-Fenstern (siehe strategy/cls_advanced.py
in diesem Repo): statt der Asien-Range wird die KOMBINIERTE Range aus
Pre-Settle (06:00-08:30 Berlin-Zeit) und Settle (08:30-10:00 Berlin-Zeit)
gehandelt - technisch ein durchgehendes Fenster 06:00-10:00 Berlin-Zeit
(die Vereinigung von High/Low beider Teilfenster ist identisch mit einem
einzigen Fenster ueber beide hinweg). Ausbruch wird erst NACH 10:00
gehandelt.

Exit-Logik ist bewusst NICHT range-relativ wie beim Original
(asian_range_breakout/engine.py: dort kein TP, Stop = stop_frac x
Range-Breite, Zeit-Exit): hier laut User-Vorgabe
- TP = adr_mult x ADR(adr_period) (Average Daily Range der letzten N
  abgeschlossenen Handelstage in Berlin-Kalendertagen, kein Lookahead)
- SL = atr_mult x ATR(atr_period) auf M30-Bars (Berlin-lokal resampled,
  ebenfalls kein Lookahead - nutzt nur den zuletzt VOLLSTAENDIG
  geschlossenen M30-Bar)
Kein Zeit-Exit - die Position laeuft bis TP/SL, oder bis Datenende."""

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from strategy.indicators import compute_atr


def fetch_gold_m15_berlin(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_timeframe("GOLD", "M15", start, end, force_refresh=force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def _minutes(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.hour * 60 + index.minute).to_numpy()


def _minutes_of(hhmm: str) -> int:
    t = pd.Timestamp(hhmm)
    return t.hour * 60 + t.minute


def compute_adr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    """Average Daily Range: rolling n-Tage-Mittel aus (Tages-Hoch -
    Tages-Tief) über abgeschlossene VORTAGE (shift(1), kein Lookahead - der
    heutige Tag ist per Definition noch nicht fertig), pro Berlin-
    Kalendertag, zurückgemappt auf den M15-Index dieses df."""
    daily = df.resample("1D").agg({"high": "max", "low": "min"}).dropna()
    daily_range = daily["high"] - daily["low"]
    adr = daily_range.rolling(n, min_periods=n).mean().shift(1)
    day_key = df.index.normalize()
    return adr.reindex(day_key).to_numpy()


def compute_m30_atr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    """ATR(n) auf M30-Bars (30-Minuten-Kerzen im Index von df, hier
    Europe/Berlin-lokal resampled - andere Zeitzone würde andere M30-
    Bar-Grenzen ergeben), zurückgemappt auf den M15-Index. Kein Lookahead:
    jeder M15-Bar sieht nur den ATR-Wert des zuletzt VOLLSTÄNDIG
    geschlossenen M30-Bars (shift(1) auf M30-Ebene vor dem Zurückmappen -
    der ATR-Wert "erscheint" erst, nachdem sein eigener M30-Bar fertig ist)."""
    m30 = df.resample("30min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    atr_m30 = compute_atr(m30, n=n).shift(1)
    return atr_m30.reindex(df.index, method="ffill").to_numpy()


def simulate_cls_settle_breakout(
    df: pd.DataFrame,
    range_start: str = "06:00",
    range_end: str = "10:00",
    adr_mult: float = 0.35,
    adr_period: int = 14,
    atr_mult: float = 1.0,
    atr_period: int = 14,
    spread_price: float = 0.30,
    slippage_price: float = 0.10,
) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_cls_settle_breakout: missing columns {missing}")

    start_min = _minutes_of(range_start)
    end_min = _minutes_of(range_end)
    minutes = _minutes(df.index)
    in_window = (minutes >= start_min) & (minutes < end_min)

    adr = compute_adr(df, n=adr_period)
    atr = compute_m30_atr(df, n=atr_period)

    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df.index
    n = len(df)
    half_spread = spread_price / 2

    trades = []
    i = 0
    while i < n:
        while i < n and not in_window[i]:
            i += 1
        if i >= n:
            break
        window_start = i
        while i < n and in_window[i]:
            i += 1
        window_end = i  # exklusiv - erster Bar NICHT mehr im Fenster (Range gerade geschlossen)
        if window_end >= n:
            break

        r_hi = high[window_start:window_end].max()
        r_lo = low[window_start:window_end].min()
        if r_hi - r_lo <= 0:
            continue

        this_adr = adr[window_end]
        this_atr = atr[window_end]
        if np.isnan(this_adr) or np.isnan(this_atr) or this_adr <= 0 or this_atr <= 0:
            continue  # noch nicht genug Historie für TP/SL (frühe Bars im Datensatz)

        tp_dist = adr_mult * this_adr
        sl_dist = atr_mult * this_atr

        # Fill-Suche: bis zum Start des NÄCHSTEN Fensters (kein festes
        # Zeit-Exit für die Warteperiode in dieser Variante) - ab dann ist
        # die Range durch die neue Range-Bildung überholt.
        entry_i, direction = None, 0
        j = window_end + 1
        while j < n and not in_window[j]:
            broke_up = high[j] >= r_hi
            broke_down = low[j] <= r_lo
            if broke_up and not broke_down:
                entry_i, direction = j, 1
                break
            if broke_down and not broke_up:
                entry_i, direction = j, -1
                break
            j += 1

        if entry_i is None:
            continue  # kein Fill vor der nächsten Range-Bildung

        raw_entry = r_hi if direction == 1 else r_lo
        entry_price = raw_entry + half_spread if direction == 1 else raw_entry - half_spread
        sl = raw_entry - sl_dist if direction == 1 else raw_entry + sl_dist
        tp = raw_entry + tp_dist if direction == 1 else raw_entry - tp_dist

        exit_i, exit_price, exit_reason = None, None, None
        k = entry_i
        while k < n:
            hit_stop = (low[k] <= sl) if direction == 1 else (high[k] >= sl)
            hit_tp = (high[k] >= tp) if direction == 1 else (low[k] <= tp)
            if hit_stop:
                exit_price = sl - half_spread - slippage_price if direction == 1 else sl + half_spread + slippage_price
                exit_i, exit_reason = k, "stop"
                break
            if hit_tp:
                exit_price = tp - half_spread if direction == 1 else tp + half_spread
                exit_i, exit_reason = k, "take_profit"
                break
            k += 1

        if exit_i is None:
            exit_price = close[n - 1] - half_spread if direction == 1 else close[n - 1] + half_spread
            exit_i, exit_reason = n - 1, "data_end"

        return_pct = (
            (exit_price - entry_price) / entry_price
            if direction == 1
            else (entry_price - exit_price) / entry_price
        )
        trades.append(
            {
                "window_start": times[window_start],
                "window_end": times[window_end],
                "entry_time": times[entry_i],
                "exit_time": times[exit_i],
                "direction": "long" if direction == 1 else "short",
                "entry_price": entry_price,
                "exit_price": exit_price,
                "sl": sl,
                "tp": tp,
                "range_high": r_hi,
                "range_low": r_lo,
                "range_width": r_hi - r_lo,
                "adr_at_entry": this_adr,
                "atr_m30_at_entry": this_atr,
                "return_pct": return_pct,
                "hold_bars": exit_i - entry_i,
                "exit_reason": exit_reason,
            }
        )
        i = exit_i + 1

    return pd.DataFrame(trades)


def check_settle_confirmation(
    df_berlin: pd.DataFrame,
    asia_trades: pd.DataFrame,
    range_start: str = "06:00",
    range_end: str = "10:00",
) -> pd.Series:
    """Für jeden Asia-Range-Trade (asian_range_breakout.engine.
    simulate_asian_breakout-Output): wurde die noch im Entstehen befindliche
    CLS-Settle-Range (range_start-range_end Berlin-Zeit) VOR ODER
    GLEICHZEITIG mit dem Asia-Entry bereits in dieselbe Richtung
    durchbrochen? (User-Entscheidung 2026-08-05: Bestätigung muss vor/zeit-
    gleich mit dem Asia-Entry vorliegen, nicht irgendwann später am Tag.)

    Kausal: nur Bars bis einschließlich des Asia-Entry-Zeitpunkts fließen
    ein, die Referenz-Range wächst bar-für-bar (derselbe Mechanismus wie
    simulate_cls_settle_breakout, nur ohne auf range_end zu warten - hier
    zählt jeder Punkt VOR dem Entry als potenzieller Bruch einer bis dahin
    etablierten Teil-Range)."""

    start_min = _minutes_of(range_start)
    end_min = _minutes_of(range_end)
    minutes = _minutes(df_berlin.index)
    in_window = (minutes >= start_min) & (minutes < end_min)

    confirmed = []
    for _, trade in asia_trades.iterrows():
        entry_berlin = trade["entry_time"].tz_convert("Europe/Berlin")
        day = entry_berlin.normalize()

        mask = (df_berlin.index.normalize() == day) & in_window & (df_berlin.index <= entry_berlin)
        window_bars = df_berlin.loc[mask]

        if len(window_bars) < 2:
            confirmed.append(False)
            continue

        r_hi = r_lo = None
        broke_up = broke_down = False
        for _, bar in window_bars.iterrows():
            if r_hi is not None and bar["high"] >= r_hi:
                broke_up = True
            if r_lo is not None and bar["low"] <= r_lo:
                broke_down = True
            r_hi = bar["high"] if r_hi is None else max(r_hi, bar["high"])
            r_lo = bar["low"] if r_lo is None else min(r_lo, bar["low"])

        confirmed.append(broke_up if trade["direction"] == "long" else broke_down)

    return pd.Series(confirmed, index=asia_trades.index)
