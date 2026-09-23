"""Read-only MT5-Abzug fuer den Weekly Checkup KW37/2026.

Nur account_info(), history_deals_get(), positions_get() -- niemals
order_send/modify/cancel. Temporaeres Hilfsskript des Report-Laufs.
"""
import json
import sys
from datetime import datetime

import MetaTrader5 as mt5

FROM = datetime(2026, 9, 7, 0, 0)
TO = datetime(2026, 9, 14, 0, 0)

ACCOUNTS = [
    ("EK-Portfolio-Bridge / Tickmill", 55918977, "TRading000!!", "Tickmill-Live",
     r"C:\Users\andre\MT5-Terminals\Tickmill MT5 Terminal - EKPortfolio\terminal64.exe"),
    ("Funded / TTP Konto2 (ttp)", 504072729, "TRading000!!", "TTPMarkets-Server",
     r"C:\Users\andre\MT5-Terminals\TTP MT5 Terminal Konto2neu\terminal64.exe"),
    ("Funded / IQ Markets (iqmarkets)", 16054, "Sm6^znlf", "BeyondIQCapital-Server",
     r"C:\Users\andre\MT5-Terminals\MT5 Terminal - GoldFKBot\terminal64.exe"),
    # ("Funded / TTP Konto1 (ttp1)", 504069845, ...) am 2026-09-23 entfernt --
    # Konto gebreacht/gesperrt, vom Nutzer als abgeschlossen erklaert.
    ("FK Instant Funding", 17764, "Sm6^znlf", "BeyondIQCapital-Server",
     r"C:\Users\andre\FKInstantFunding-MT5-Bridge\terminal\terminal64.exe"),
]

out = {}
for label, login, pw, server, path in ACCOUNTS:
    rec = {"login": login, "server": server}
    try:
        ok = mt5.initialize(path=path, login=login, password=pw, server=server, timeout=60000)
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"initialize raised: {exc}"
        out[label] = rec
        continue
    if not ok:
        rec["error"] = f"initialize failed: {mt5.last_error()}"
        out[label] = rec
        mt5.shutdown()
        continue

    ai = mt5.account_info()
    if ai is None:
        rec["error"] = f"account_info None: {mt5.last_error()}"
    else:
        d = ai._asdict()
        rec["account"] = {k: d.get(k) for k in
                          ("login", "server", "currency", "balance", "equity",
                           "profit", "margin", "margin_free", "leverage", "trade_mode")}

    deals = mt5.history_deals_get(FROM, TO)
    if deals is None:
        rec["deals_error"] = str(mt5.last_error())
        rec["deals"] = []
    else:
        rec["deals"] = [
            {k: v for k, v in dd._asdict().items()
             if k in ("ticket", "order", "time", "type", "entry", "position_id",
                      "symbol", "volume", "price", "profit", "commission", "swap",
                      "fee", "comment", "magic", "reason")}
            for dd in deals
        ]
        for dd in rec["deals"]:
            dd["time_iso"] = datetime.utcfromtimestamp(dd["time"]).isoformat()

    pos = mt5.positions_get()
    rec["positions"] = [] if pos is None else [
        {k: v for k, v in p._asdict().items()
         if k in ("ticket", "time", "type", "symbol", "volume", "price_open",
                  "sl", "tp", "price_current", "profit", "swap", "comment", "magic")}
        for p in pos
    ]
    for p in rec["positions"]:
        p["time_iso"] = datetime.utcfromtimestamp(p["time"]).isoformat()

    out[label] = rec
    mt5.shutdown()

json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str)
print("written", sys.argv[1])
for k, v in out.items():
    print(k, "|", v.get("error", "OK"), "| deals:", len(v.get("deals", [])),
          "| open:", len(v.get("positions", [])),
          "| equity:", (v.get("account") or {}).get("equity"))
