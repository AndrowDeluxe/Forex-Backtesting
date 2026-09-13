"""Misst die ECHTEN EURUSD-Handelskosten je Broker direkt aus den MT5-
Terminals -- Grundlage fuer die Kostenmodell-Validierung von cls_practical
(Vorfall 2026-09-09: drei Live-Trades realisierten 1,84x ihres Risikobudgets,
siehe knowledge/CHANGELOG.md).

Warum aus MT5 und nicht aus dem Repo-Datenbestand: dieses Repo hat KEINEN
historischen Bid/Ask-Feed. Dukascopy (cls_practical/data.py) liefert nur
OHLC-Mid, der data_lake speichert dasselbe weiter. Die einzige Quelle fuer
echte Spannen UND echte Ausfuehrungspreise dieser konkreten Broker sind deren
eigene Terminals. (bond_yield_indicator/friction.py::corwin_schultz_spread
schaetzt Spreads aus High/Low -- fuer FX-D1 gedacht, hier bewusst NICHT
benutzt: wir koennen die echte Groesse direkt messen statt sie zu schaetzen.)

Warum je Broker getrennt (Nutzervorgabe 2026-09-09): am 2026-09-09 lief EIN
Signal mit IDENTISCHEM SL ueber drei Konten -- TTP realisierte 2,8 Pips
Verlust, IQ Markets 1,8 Pips. Ein einziges globales Kostenpaar kann fuer beide
nicht gleichzeitig stimmen.

Gemessen werden ZWEI Groessen, weil der erste Testlauf am 2026-09-09 gezeigt
hat, dass sie sich voellig unterschiedlich verhalten:
  1. SPREAD -- auf diesen Brokern sehr eng (0,1-0,4 Pips im Handelsfenster).
     Die Annahme spread_bps=0.3 in cls_practical/engine.py ist damit
     ungefaehr richtig, entgegen der ersten Vermutung.
  2. SLIPPAGE -- im Engine-Default 0.0, real aber die dominante Kostenquelle:
     auf TTP 0,7 Pips beim Einstieg PLUS 0,7 Pips beim Stop-Ausstieg, bei
     einem nominalen Stop-Abstand von 1,2 Pips. Genau diese Groesse fehlt im
     Backtest komplett.

Messfenster 08:00-12:30 Berlin: cls_practical handelt zwischen test_hour=9.0
und entry_cutoff="12:00" (cls_practical/engine.py). Ein 24h-Spreadmittel waere
fuer diese Strategie irrefuehrend niedrig -- der Spread in der Asien-Session
und um den Rollover ist ein anderer als der zur Handelszeit.

REIN LESEND. Sendet keine Order, aendert keine Config. Startet fehlende
Terminals mit /portable und schliesst am Ende GENAU die wieder, die vorher
nicht liefen (Vorfall 2026-09-01: die Report-Automation liess MT5-GUIs
pausierter Bots offen stehen).

Aufruf:
    python scripts/measure_broker_spreads.py [--days 30] [--out <pfad.json>]
"""

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))

FUNDED_BRIDGE = Path(r"C:\Users\andre\Funded-Portfolio-Bridge")
EK_BRIDGE = Path(r"C:\Users\andre\EK-Portfolio-Bridge")

LOCAL_TZ = "Europe/Berlin"
WINDOW_START_H, WINDOW_END_H = 8.0, 12.5  # Berlin, siehe Modul-Docstring
DEFAULT_LOOKBACK_DAYS = 30
MAX_POOLED_SAMPLES = 400_000  # Downsampling-Ziel, damit 30 Tage EURUSD-Ticks nicht den Speicher sprengen

_CONNECT_RETRY_DELAY_S = 12  # identisch zu Funded-Portfolio-Bridge/executor.py


@dataclass(frozen=True)
class Target:
    """Ein zu vermessendes Konto. `broker` ist die Gruppierungsebene, die uns
    eigentlich interessiert -- zwei TTP-Konten haengen am selben Server und
    sehen denselben Spread, sind also eine Gegenprobe gegeneinander, keine
    zwei unabhaengigen Messungen."""
    portfolio: str
    account: str
    broker: str
    state_id: str | None  # None = Bridge ohne dieses State-Lock (EK)
    terminal_path: str
    login: int
    password: str
    server: str
    symbol: str


def _load_targets() -> list[Target]:
    """Liest Terminalpfade/Zugangsdaten aus den bestehenden Bridge-Configs,
    statt sie hier zu duplizieren -- die Bridges liegen ausserhalb des Repos
    und sind die einzige Wahrheit fuer diese Werte."""
    targets: list[Target] = []

    sys.path.insert(0, str(FUNDED_BRIDGE))
    import config as funded_config  # noqa: E402

    for acc in funded_config.ACCOUNTS:
        # resolve_symbol()-Logik der Bridge in Kurzform: symbol_map schlaegt
        # symbol_suffix. Fuer EURUSD ist auf allen drei Konten der Suffix-Pfad
        # relevant (".gbe" bei BeyondIQCapital, leer bei TTP).
        symbol = acc.symbol_map.get("EURUSD", "EURUSD" + acc.symbol_suffix)
        targets.append(Target(
            portfolio="Funded", account=acc.name, broker=acc.mt5_server, state_id=acc.state_id,
            terminal_path=acc.mt5_terminal_path, login=acc.mt5_login,
            password=acc.mt5_password, server=acc.mt5_server, symbol=symbol,
        ))
    sys.path.remove(str(FUNDED_BRIDGE))
    del sys.modules["config"]

    sys.path.insert(0, str(EK_BRIDGE))
    import config as ek_config  # noqa: E402

    targets.append(Target(
        portfolio="EK", account="EK-Portfolio (Tickmill, echtes Geld)", broker=ek_config.MT5_SERVER,
        state_id=None, terminal_path=ek_config.TERMINAL_PATH, login=ek_config.MT5_LOGIN,
        password=ek_config.MT5_PASSWORD, server=ek_config.MT5_SERVER,
        symbol=ek_config.SYMBOL_MAP["EURUSD"],
    ))
    sys.path.remove(str(EK_BRIDGE))
    del sys.modules["config"]

    return targets


_LOCK_ACQUIRE_TIMEOUT_S = 60.0
_LOCK_POLL_INTERVAL_S = 0.5


@contextlib.contextmanager
def account_state_lock(target: Target, timeout_s: float = _LOCK_ACQUIRE_TIMEOUT_S):
    """Belegt DIESELBE Lock-Datei wie Funded-Portfolio-Bridge/run_once.py::
    account_state_lock() (os.O_CREAT|O_EXCL auf bridge_state_<id>.json.lock).

    Grund: dieses Skript macht mt5.shutdown()+initialize()+login() auf genau
    den Terminals, mit denen der Bot alle 5 bzw. 15 Minuten echte Orders
    sendet. Ohne Lock koennte die Messung mitten in einen laufenden Zyklus
    greifen -- IPC-Kollisionen zwischen zwei Python-Prozessen auf einem
    Terminal sind in diesem Projekt real belegt (siehe DASHBOARD.md,
    geteiltes Gold-ASB/BTC/ORB-Terminal).

    Bewusste Konsequenz: solange die Messung laeuft, ueberspringt ein parallel
    startender Bridge-Zyklus dieses Konto (nach dessen 45s-Timeout) und
    versucht es 5 Minuten spaeter erneut. Ein uebersprungener Scan ist
    ungefaehrlich, eine Order-Kollision nicht -- deshalb diese Richtung.

    Das Protokoll ist reines Dateivorhandensein, deshalb ist diese eigene
    kleine Implementierung mit der der Bridge kompatibel; run_once.py zu
    importieren wuerde dessen komplettes Modul-Setup mitziehen."""
    if target.state_id is None:
        yield  # EK-Portfolio-Bridge kennt dieses Lock nicht (eigenes Terminal, SQLite-State)
        return

    lock_path = FUNDED_BRIDGE / f"bridge_state_{target.state_id}.json.lock"
    deadline = time.monotonic() + timeout_s
    fd = None
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"State-Lock fuer {target.state_id} nach {timeout_s:.0f}s nicht frei -- ein "
                    f"Bridge-Lauf haelt das Terminal gerade. Konto uebersprungen, spaeter erneut."
                )
            time.sleep(_LOCK_POLL_INTERVAL_S)
    try:
        yield
    finally:
        os.close(fd)
        lock_path.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Terminal-/Verbindungshandhabung -- Muster woertlich aus
# Funded-Portfolio-Bridge/executor.py (_terminal_running/_ensure_terminal_
# running/_connect_once). Dort steht die vollstaendige Begruendung fuer den
# zweistufigen initialize()+login()-Aufruf und den /portable-Vorstart.
# --------------------------------------------------------------------------

def _terminal_running(terminal_path: str) -> bool:
    ps_cmd = (
        "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.Path -eq '{terminal_path}' }}).Count"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=20,
    )
    return result.stdout.strip() not in ("", "0")


def _stop_terminal(terminal_path: str) -> None:
    ps_cmd = (
        "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.Path -eq '{terminal_path}' }} | Stop-Process -Force"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                   capture_output=True, text=True, timeout=30)


def _connect(mt5, target: Target) -> None:
    def _once() -> str | None:
        if not _terminal_running(target.terminal_path):
            subprocess.Popen([target.terminal_path, "/portable"])
            time.sleep(20)
        mt5.shutdown()
        if not mt5.initialize(path=target.terminal_path, timeout=20000):
            return f"initialize() fehlgeschlagen: {mt5.last_error()}"
        if not mt5.login(target.login, password=target.password, server=target.server, timeout=20000):
            return f"login() fehlgeschlagen: {mt5.last_error()}"
        return None

    err = _once()
    if err is not None:
        print(f"    erster Verbindungsversuch fehlgeschlagen ({err}) - noch einer in {_CONNECT_RETRY_DELAY_S}s")
        time.sleep(_CONNECT_RETRY_DELAY_S)
        err = _once()
        if err is not None:
            raise RuntimeError(f"Verbindung zu {target.account} fehlgeschlagen: {err}")

    info = mt5.account_info()
    if info is None:
        raise RuntimeError(f"account_info() fehlgeschlagen fuer {target.account}: {mt5.last_error()}")
    if info.login != target.login:
        raise RuntimeError(f"Terminal ist in Konto {info.login} eingeloggt, erwartet {target.login}.")


def _server_utc_offset_hours(mt5, symbol: str) -> float:
    """MT5 gibt Zeitstempel in BROKER-Serverzeit zurueck, nicht in UTC -- und
    jeder dieser Broker kann einen anderen Offset haben. Ohne diese Korrektur
    wuerde das 08:00-12:30-Berlin-Fenster je Broker ein anderes reales Fenster
    treffen und die Spreads waeren nicht vergleichbar. Bestimmt aus dem
    aktuellen Tick gegen die echte UTC-Zeit."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None or tick.time == 0:
        raise RuntimeError(f"kein Tick fuer {symbol} - Offset nicht bestimmbar ({mt5.last_error()})")
    now_utc = datetime.now(timezone.utc).timestamp()
    return round((tick.time - now_utc) / 1800) / 2  # auf halbe Stunden runden


def _berlin_window_to_server(day: pd.Timestamp, offset_h: float) -> tuple[datetime, datetime]:
    """08:00/12:30 Berlin dieses Tages -> naive Serverzeit-Stempel, wie sie
    copy_ticks_range()/copy_rates_range() erwarten."""
    start_local = day.tz_localize(LOCAL_TZ) + pd.Timedelta(hours=WINDOW_START_H)
    end_local = day.tz_localize(LOCAL_TZ) + pd.Timedelta(hours=WINDOW_END_H)
    to_server = pd.Timedelta(hours=offset_h)
    return ((start_local.tz_convert("UTC").tz_localize(None) + to_server).to_pydatetime(),
            (end_local.tz_convert("UTC").tz_localize(None) + to_server).to_pydatetime())


def _pip_size(info) -> float:
    """Pip = 10 Points bei 5-/3-stelligen FX-Quotes (EURUSD 1.16373 -> point
    0.00001, 1 Pip = 0.0001)."""
    return info.point * 10 if info.digits in (3, 5) else info.point


def _ensure_symbol(mt5, symbol: str):
    info = mt5.symbol_info(symbol)
    if info is None:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Symbol {symbol} nicht verfuegbar: {mt5.last_error()}")
        info = mt5.symbol_info(symbol)
    return info


def _pool(arrays: list, label: str) -> dict:
    if not arrays:
        return {}
    a = np.concatenate(arrays)
    if a.size > MAX_POOLED_SAMPLES:  # gleichmaessiges Downsampling, Verteilungsform bleibt erhalten
        a = a[:: int(np.ceil(a.size / MAX_POOLED_SAMPLES))]
    return {
        f"{label}_samples": int(a.size),
        f"{label}_median_pips": float(np.median(a)),
        f"{label}_p75_pips": float(np.percentile(a, 75)),
        f"{label}_p90_pips": float(np.percentile(a, 90)),
        f"{label}_max_pips": float(a.max()),
    }


def _measure_spreads(mt5, target: Target, days: int) -> dict:
    """Spread im Handelsfenster, aus zwei Quellen:

    - PRIMAER die M1-Rates (`spread`-Feld, in Points): das Terminal haelt davon
      Monate vor, auch auf Konten mit duenner Tickhistorie. Beim Testlauf am
      2026-09-09 lieferte Tickmill ueber zwei Tage ganze 7 Ticks, aber ~11.700
      M1-Baren -- ohne diesen Weg waere EK gar nicht messbar.
    - ZUSAETZLICH tickgenau (ask-bid) fuer die Tage, die das Terminal noch
      vorhaelt, als Gegenprobe gegen die gerundeten Points der M1-Baren.
    """
    info = _ensure_symbol(mt5, target.symbol)
    pip = _pip_size(info)
    points_per_pip = pip / info.point

    offset_h = _server_utc_offset_hours(mt5, target.symbol)
    today = pd.Timestamp.now(tz=LOCAL_TZ).normalize().tz_localize(None)
    # range(0, ...) -- HEUTE gehoert dazu: der Vorfall, der diese Messung
    # ausgeloest hat, lag heute frueh mitten im Messfenster.
    day_list = [today - pd.Timedelta(days=i) for i in range(0, days + 1)]
    day_list = [d for d in day_list if d.dayofweek < 5]

    rate_spreads, tick_spreads, per_day = [], [], []
    for day in day_list:
        srv_from, srv_to = _berlin_window_to_server(day, offset_h)

        day_rate = np.array([])
        rates = mt5.copy_rates_range(target.symbol, mt5.TIMEFRAME_M1, srv_from, srv_to)
        if rates is not None and len(rates) > 0 and "spread" in (rates.dtype.names or ()):
            day_rate = rates["spread"].astype(float) / points_per_pip
            day_rate = day_rate[np.isfinite(day_rate) & (day_rate > 0)]
            if day_rate.size:
                rate_spreads.append(day_rate)

        ticks = mt5.copy_ticks_range(target.symbol, srv_from, srv_to, mt5.COPY_TICKS_INFO)
        if ticks is not None and len(ticks) > 0:
            df = pd.DataFrame(ticks)
            ts = ((df["ask"] - df["bid"]).to_numpy()) / pip
            ts = ts[np.isfinite(ts) & (ts > 0)]
            if ts.size:
                tick_spreads.append(ts)

        if day_rate.size:
            per_day.append({
                "day": day.strftime("%Y-%m-%d"), "m1_bars": int(day_rate.size),
                "median_pips": float(np.median(day_rate)),
                "p90_pips": float(np.percentile(day_rate, 90)),
            })

    if not rate_spreads and not tick_spreads:
        return {"error": "weder M1-Rates noch Ticks im Messfenster erhalten", "days_with_data": 0}

    out = {
        "days_with_data": len(per_day),
        "first_day": per_day[-1]["day"] if per_day else None,
        "last_day": per_day[0]["day"] if per_day else None,
        "server_utc_offset_h": offset_h,
        "pip_size": pip,
        "per_day": per_day,
    }
    out.update(_pool(rate_spreads, "m1"))
    out.update(_pool(tick_spreads, "tick"))

    # spread_bps ist die Groesse, die cls_practical/engine.py direkt frisst
    # (dort: half_spread = price * spread_bps / 10_000 / 2, also Round-Trip).
    mid = float(mt5.symbol_info_tick(target.symbol).bid)
    for key in ("m1_median", "m1_p75", "m1_p90", "tick_median", "tick_p75", "tick_p90"):
        if f"{key}_pips" in out:
            out[f"{key}_bps"] = out[f"{key}_pips"] * pip / mid * 10_000
    return out


def _measure_slippage(mt5, target: Target, days: int) -> dict:
    """Realisierte Slippage aus den ECHTEN Orders/Deals dieses Kontos -- BEIDE
    Seiten, nicht nur der Ausstieg:

    - EINSTIEG: Ausfuehrungspreis des Deals gegen `order.price_current`, den
      Marktpreis, den das Terminal bei Auftragsannahme sah. Genau dieser Preis
      geht in Funded-Portfolio-Bridge/sizing.py in die Lot-Berechnung ein --
      jede Abweichung davon ist Risiko, das in der Positionsgroesse nicht
      steckt. Am 2026-09-09 waren das auf TTP 0,7 Pips bei einem nominalen
      Stop-Abstand von 1,2 Pips.
    - AUSSTIEG: Ausfuehrungspreis gegen `order.price_open` der Stop-Order, also
      gegen das tatsaechlich gesetzte SL-Niveau.

    Vorzeichen: POSITIV = schlechter fuer uns. Ein BUY-Deal ist schlechter, je
    hoeher er fuellt, ein SELL-Deal, je tiefer.

    SL-Niveaus kommen aus MT5 selbst statt aus den bridge_state_*.json --
    dadurch funktioniert die Messung auch fuer EK (anderer State) und
    unabhaengig davon, dass der Fill-Ruecklesepfad auf TTP `entry_price: 0.0`
    speichert (Nebenbefund 2026-09-09).

    Die Bridges laufen erst seit 2026-09-01, die Stichprobe ist also klein --
    deshalb wird jeder Einzelfall mit ausgegeben statt nur ein Aggregat."""
    to_dt = datetime.now() + timedelta(days=1)
    from_dt = to_dt - timedelta(days=days + 1)
    orders = mt5.history_orders_get(from_dt, to_dt) or []
    deals = mt5.history_deals_get(from_dt, to_dt) or []
    if not deals:
        return {"deals": 0, "note": "keine Deal-Historie im Zeitraum"}

    info = _ensure_symbol(mt5, target.symbol)
    pip = _pip_size(info)
    order_by_ticket = {int(o.ticket): o for o in orders}

    rows = []
    for d in deals:
        if d.symbol != target.symbol:
            continue
        o = order_by_ticket.get(int(d.order))
        if o is None:
            continue
        is_entry = d.entry == mt5.DEAL_ENTRY_IN
        reference = float(o.price_current) if is_entry else float(o.price_open)
        if reference <= 0:
            continue
        # BUY (type 0) fuellt schlechter nach oben, SELL (type 1) nach unten
        worse = (d.price - reference) if d.type == mt5.DEAL_TYPE_BUY else (reference - d.price)
        rows.append({
            "position": int(d.position_id), "side": "entry" if is_entry else "exit",
            "time": datetime.fromtimestamp(d.time).isoformat(),
            "reference": reference, "fill": float(d.price),
            "slippage_pips": float(worse / pip), "volume": float(d.volume),
            "commission": float(d.commission), "profit": float(d.profit), "comment": d.comment,
        })

    if not rows:
        return {"deals": 0, "note": f"keine {target.symbol}-Deals mit zuordenbarer Order"}

    out: dict = {"deals": len(rows), "detail": rows}
    for side in ("entry", "exit"):
        vals = np.array([r["slippage_pips"] for r in rows if r["side"] == side])
        if vals.size:
            out[f"{side}_n"] = int(vals.size)
            out[f"{side}_median_pips"] = float(np.median(vals))
            out[f"{side}_mean_pips"] = float(vals.mean())
            out[f"{side}_max_pips"] = float(vals.max())
    out["roundtrip_median_pips"] = float(
        out.get("entry_median_pips", 0.0) + out.get("exit_median_pips", 0.0)
    )

    # Kommission: im Backtest komplett unmodelliert, real aber materiell --
    # der CLS-Trade vom 2026-09-09 kostete auf TTP $83.20 (20,8 Lots) und auf
    # IQ $113.60 (22,72 Lots) zusaetzlich zum Kursverlust. Umgerechnet auf die
    # Position (1 Lot EURUSD = 100.000, 1 Pip = $10) ist das ein Aufschlag in
    # derselben Waehrung wie Spread/Slippage und gehoert deshalb dazu.
    per_pos: dict[int, dict] = {}
    for r in rows:
        p = per_pos.setdefault(r["position"], {"commission": 0.0, "volume": 0.0})
        p["commission"] += abs(r["commission"])
        p["volume"] = max(p["volume"], r["volume"])  # Ein- und Ausstieg haben dasselbe Volumen
    per_lot = [p["commission"] / p["volume"] for p in per_pos.values() if p["volume"] > 0]
    if per_lot:
        usd_per_pip_per_lot = 10.0  # EURUSD, USD als Quote-Waehrung
        out["commission_positions"] = len(per_lot)
        out["commission_usd_per_lot_roundtrip"] = float(np.median(per_lot))
        out["commission_pips_roundtrip"] = float(np.median(per_lot) / usd_per_pip_per_lot)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "broker_spreads_eurusd.json")
    args = ap.parse_args()

    import MetaTrader5 as mt5

    targets = _load_targets()
    was_running = {t.terminal_path: _terminal_running(t.terminal_path) for t in targets}
    results = []

    try:
        for t in targets:
            print(f"\n=== {t.portfolio} | {t.account}\n    Broker {t.broker}, Symbol {t.symbol}")
            entry = {"portfolio": t.portfolio, "account": t.account, "broker": t.broker, "symbol": t.symbol}
            try:
                with account_state_lock(t):
                    _connect(mt5, t)
                    entry["spread"] = _measure_spreads(mt5, t, args.days)
                    entry["slippage"] = _measure_slippage(mt5, t, args.days)

                s = entry["spread"]
                if "error" in s:
                    print(f"    SPREAD: {s['error']}")
                else:
                    print(f"    SPREAD ({s['days_with_data']} Tage, {s['first_day']}..{s['last_day']}, "
                          f"Serverzeit UTC{s['server_utc_offset_h']:+g}):")
                    if "m1_median_pips" in s:
                        print(f"      M1-Baren ({s['m1_samples']:,}): Median {s['m1_median_pips']:.2f} Pips "
                              f"({s['m1_median_bps']:.2f} bps) | p75 {s['m1_p75_pips']:.2f} "
                              f"| p90 {s['m1_p90_pips']:.2f} | max {s['m1_max_pips']:.2f}")
                    if "tick_median_pips" in s:
                        print(f"      Ticks    ({s['tick_samples']:,}): Median {s['tick_median_pips']:.2f} Pips "
                              f"| p90 {s['tick_p90_pips']:.2f} | max {s['tick_max_pips']:.2f}")
                sl = entry["slippage"]
                if sl.get("note"):
                    print(f"    SLIPPAGE: {sl['note']}")
                else:
                    print("    SLIPPAGE:")
                    for side in ("entry", "exit"):
                        if f"{side}_n" in sl:
                            print(f"      {side.upper():5} n={sl[f'{side}_n']}: Median "
                                  f"{sl[f'{side}_median_pips']:+.2f} Pips | max {sl[f'{side}_max_pips']:+.2f}")
                    print(f"      -> Round-Trip (Median): {sl['roundtrip_median_pips']:+.2f} Pips")
                    if "commission_pips_roundtrip" in sl:
                        print(f"    KOMMISSION ({sl['commission_positions']} Pos.): "
                              f"${sl['commission_usd_per_lot_roundtrip']:.2f}/Lot Round-Trip "
                              f"= {sl['commission_pips_roundtrip']:.2f} Pips")
            except Exception as e:  # ein toter Broker darf die anderen Messungen nicht verhindern
                entry["error"] = str(e)
                print(f"    FEHLER: {e}")
            results.append(entry)
    finally:
        mt5.shutdown()
        for path, running_before in was_running.items():
            if not running_before and _terminal_running(path):
                print(f"\nSchliesse selbst gestartetes Terminal: {path}")
                _stop_terminal(path)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "measured_at": datetime.now().isoformat(timespec="seconds"),
        "window_berlin": f"{WINDOW_START_H:g}:00-{WINDOW_END_H:g}",
        "lookback_days": args.days,
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
