"""EINMALIG: die 8 verwaisten Positionen des abgeschalteten OU-Modell-Solo-Bots
schliessen (Nutzerauftrag 2026-09-17: "Schliesse alle verwaisten Positionen bei
Boersenoeffnung bitte automatisch").

Herkunft: OU-Modell-MT5-Bridge (Kommentar "OU-Modell auto", magic 0) wurde Ende
August abgeschaltet; diese Positionen gehoeren keiner Bridge mehr, laufen seit
22-27 Tagen (Modell: max. 10 Tage) nur noch mit Broker-SL/TP und Swap.
Die verwaisten Positionen der Funded-Bridge (Signaldatum-Drift) schliesst die
Bridge selbst ueber run_once.py::_reconcile_ou_positions() -- NICHT hier.

Sicherungen:
  - Tickets sind fest verdrahtet. Jede Position wird vor dem Schliessen gegen
    Symbol, Volumen, magic 0 und Kommentar geprueft -- weicht etwas ab, wird sie
    nicht angefasst.
  - Nur bei offener NYSE (echte UTC-Zeit, unabhaengig von der Rechner-Zeitzone,
    die 2026-09-15..17 mehrfach sprang).
  - TTP-Konten unter dem account_state_lock() der Funded-Bridge, damit kein
    Bridge-Lauf gleichzeitig am selben Terminal haengt.
  - Ohne --live nur Vorschau. Bereits geschlossene Positionen werden gemeldet,
    nicht als Fehler behandelt; der Lauf ist wiederholbar.
  - Ergebnis in Telegram + Log.
"""
import logging
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5

LIVE = "--live" in sys.argv
IGNORE_NYSE = "--ignore-nyse" in sys.argv and not LIVE  # nur fuer die Vorschau
FUNDED = r"C:\Users\andre\Funded-Portfolio-Bridge"
EK = r"C:\Users\andre\EK-Portfolio-Bridge"
LOG = r"C:\Users\andre\Forex-Backtesting\scripts\close_ou_solo_orphans_once.log"

TARGETS = {
    # state_id / Konto -> [(ticket, symbol, volume)]
    "ttp": [(17997113, "AFL", 25.0), (18024039, "NUE", 6.0), (18024040, "UAL", 13.0), (18077241, "TXT", 35.0)],
    "ttp1": [(17997112, "DAL", 40.0), (18003269, "UAL", 22.0), (18003931, "NUE", 11.0)],
    "ek": [(254287619, "DAL", 5.0)],
}

logging.basicConfig(filename=LOG, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("close_orphans")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def say(msg):
    print(msg)
    log.info(msg)


def nyse_open():
    ny = datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York"))
    return ny.weekday() < 5 and (9 * 60 + 30) <= ny.hour * 60 + ny.minute < 16 * 60


def filling_for(symbol):
    info = mt5.symbol_info(symbol)
    fm = getattr(info, "filling_mode", 0) if info else 0
    if fm & 2:
        return mt5.ORDER_FILLING_IOC
    if fm & 1:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def close_one(ticket, symbol, volume):
    pos = mt5.positions_get(ticket=ticket) or ()
    if not pos:
        deals = [d for d in (mt5.history_deals_get(position=ticket) or ()) if d.entry == 1]
        if deals:
            return f"{symbol} #{ticket}: war bereits geschlossen @ {deals[-1].price} (P/L {deals[-1].profit:+.2f})"
        return f"{symbol} #{ticket}: nicht gefunden -- nicht angefasst"
    p = pos[0]
    if p.symbol != symbol or abs(p.volume - volume) > 1e-9 or p.magic != 0 or p.comment != "OU-Modell auto":
        return (f"{symbol} #{ticket}: ABWEICHUNG (symbol={p.symbol} vol={p.volume} magic={p.magic} "
                f"comment={p.comment!r}) -- NICHT geschlossen")
    mt5.symbol_select(symbol, True)
    tick = None
    for _ in range(40):
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None and tick.bid > 0 and tick.ask > 0:
            break
        time.sleep(0.05)
    if tick is None or tick.bid <= 0:
        return f"{symbol} #{ticket}: kein Kurs -- nicht geschlossen"
    if not LIVE:
        return f"{symbol} #{ticket}: VORSCHAU -- wuerde {p.volume} @ ~{tick.bid} schliessen (P/L jetzt {p.profit:+.2f}, Swap {p.swap:+.2f})"
    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": p.volume,
           "type": mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
           "position": ticket, "price": tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask,
           "deviation": 20, "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling_for(symbol)}
    res = mt5.order_send(req)
    if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
        return f"{symbol} #{ticket}: FEHLER beim Schliessen: {res} last_error={mt5.last_error()}"
    return f"{symbol} #{ticket}: geschlossen @ {res.price} (P/L vorher {p.profit:+.2f}, Swap {p.swap:+.2f})"


def connect(path, login, password, server, two_step=False):
    """two_step: initialize(path) + login() getrennt -- so verbindet die Funded-Bridge
    (executor.py-Docstring: ein kombinierter Aufruf hing bei manchen Terminals).
    EK verbindet kombiniert (core/mt5_client.py)."""
    for attempt in range(4):
        mt5.shutdown()
        if two_step:
            ok = mt5.initialize(path=path, timeout=60000) and mt5.login(login, password=password, server=server, timeout=60000)
        else:
            ok = mt5.initialize(path=path, login=login, password=password, server=server, timeout=60000)
        if ok:
            ai = mt5.account_info()
            if ai is not None and ai.login == login:
                return True
        say(f"  Verbindung Versuch {attempt + 1} fehlgeschlagen: {mt5.last_error()}")
        time.sleep(20)
    return False


def main():
    say(f"=== OU-Solo-Waisen schliessen ({'LIVE' if LIVE else 'VORSCHAU'}) ===")
    if not nyse_open() and not IGNORE_NYSE:
        say("NYSE ist geschlossen -- nichts getan (Sicherung gegen Fehlstart).")
        return 0 if not LIVE else 2
    lines = []

    sys.path.insert(0, FUNDED)
    import run_once as funded  # noqa: E402  (liefert ACCOUNTS + account_state_lock)
    from telegram_notify import send_telegram_message  # noqa: E402
    for acc in funded.ACCOUNTS:
        if acc.state_id not in ("ttp", "ttp1"):
            continue
        for lock_try in range(6):
            try:
                with funded.account_state_lock(acc):
                    if not connect(acc.mt5_terminal_path, acc.mt5_login, acc.mt5_password, acc.mt5_server, two_step=True):
                        lines.append(f"[{acc.telegram_title}] Verbindung fehlgeschlagen -- nichts geschlossen")
                    else:
                        for ticket, sym, vol in TARGETS[acc.state_id]:
                            lines.append(f"[{acc.telegram_title}] " + close_one(ticket, sym, vol))
                        mt5.shutdown()
                break
            except TimeoutError as e:
                say(f"  {acc.state_id}: {e} -- neuer Versuch in 60 s")
                time.sleep(60)
        else:
            lines.append(f"[{acc.telegram_title}] State-Lock nie frei -- nichts geschlossen")

    sys.path.insert(0, EK)
    import importlib.util
    spec = importlib.util.spec_from_file_location("ek_config", EK + r"\config.py")
    ek = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ek)
    if connect(ek.TERMINAL_PATH, ek.MT5_LOGIN, ek.MT5_PASSWORD, ek.MT5_SERVER):
        for ticket, sym, vol in TARGETS["ek"]:
            lines.append("[EK Tickmill] " + close_one(ticket, sym, vol))
        mt5.shutdown()
    else:
        lines.append("[EK Tickmill] Verbindung fehlgeschlagen -- nichts geschlossen")

    for x in lines:
        say(x)
    if LIVE:
        send_telegram_message("🧹 OU-Solo-Waisen geschlossen\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
