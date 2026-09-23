"""Read-only Nachzieh-Pull fuer FK Instant Funding (Login 17764).

Der KW37-Lauf vom 2026-09-13 kam hier nicht durch (4x IPC timeout), siehe
KW37_2026_performance.md Punkt 5.1. Das Terminal laeuft seit 2026-09-14
00:03 bereits (fremder Prozess) -- dieser Pull startet also KEINE GUI und
schliesst auch keine. NUR Lesezugriffe.
"""
import json
import sys
from datetime import datetime, timezone

import MetaTrader5 as mt5

LOGIN = 17764
PASSWORD = "Sm6^znlf"
SERVER = "BeyondIQCapital-Server"
PATH = r"C:\Users\andre\FKInstantFunding-MT5-Bridge\terminal\terminal64.exe"

out = {}
ok = mt5.initialize(path=PATH, login=LOGIN, password=PASSWORD, server=SERVER,
                    timeout=60000)
if not ok:
    print("INIT FAILED", mt5.last_error())
    sys.exit(1)

ai = mt5.account_info()
out["account"] = {
    "login": ai.login, "equity": ai.equity, "balance": ai.balance,
    "currency": ai.currency, "margin": ai.margin, "server": ai.server,
    "name": ai.name,
}

frm = datetime(2026, 9, 6, 0, 0, tzinfo=timezone.utc)
to = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
deals = mt5.history_deals_get(frm, to)
out["deals"] = [
    {
        "ticket": d.ticket, "order": d.order, "time": datetime.fromtimestamp(
            d.time, timezone.utc).isoformat(), "type": d.type,
        "entry": d.entry, "symbol": d.symbol, "volume": d.volume,
        "price": d.price, "profit": d.profit, "commission": d.commission,
        "swap": d.swap, "comment": d.comment, "position_id": d.position_id,
    }
    for d in (deals or [])
]

pos = mt5.positions_get()
out["positions"] = [
    {
        "ticket": p.ticket, "symbol": p.symbol, "volume": p.volume,
        "type": p.type, "price_open": p.price_open, "sl": p.sl, "tp": p.tp,
        "profit": p.profit, "comment": p.comment,
        "time": datetime.fromtimestamp(p.time, timezone.utc).isoformat(),
    }
    for p in (pos or [])
]

orders_hist = mt5.history_orders_get(frm, to)
out["orders"] = [
    {
        "ticket": o.ticket, "symbol": o.symbol, "volume_initial":
        o.volume_initial, "price_open": o.price_open, "sl": o.sl,
        "state": o.state, "comment": o.comment,
        "time_setup": datetime.fromtimestamp(o.time_setup,
                                             timezone.utc).isoformat(),
    }
    for o in (orders_hist or [])
]

mt5.shutdown()
with open(r"C:\Users\andre\Forex-Backtesting\scripts\reports\_kw37_fk.json",
          "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False)
print(json.dumps(out["account"], indent=1))
print("deals:", len(out["deals"]), "positions:", len(out["positions"]),
      "orders:", len(out["orders"]))
