"""CLI: python -m fusion_lab.screener aktien|krypto|rohstoffe [--telegram] [--notion] [--no-llm] [--no-ledger]"""

from __future__ import annotations

import argparse
import sys

from fusion_lab.screener import pipeline, report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("art", choices=["aktien", "krypto", "rohstoffe"])
    p.add_argument("--telegram", action="store_true")
    p.add_argument("--notion", action="store_true")
    p.add_argument("--no-llm", action="store_true", help="ohne Claude-Einordnung (schneller Test)")
    p.add_argument("--no-ledger", action="store_true", help="nichts ins Ledger schreiben (Test)")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    run = {"aktien": pipeline.run_stocks, "krypto": pipeline.run_crypto, "rohstoffe": pipeline.run_commodities}[a.art]
    r = run(use_llm=not a.no_llm, write_ledger=not a.no_ledger)
    j, m = report.write(r)
    print(f"Bericht: {m}\nDaten: {j}\nLedger neu: {r.get('ledger_neu', 0)}, ausgewertet: {r['ledger_ausgewertet']}")
    if a.telegram:
        try:
            from fusion_lab.dashboard.deploy import config, public_url
            url = public_url()
            if url and (config() or {}).get("kv_namespace_id"):
                url = url.rstrip("/") + "/trading/"      # Cockpit liegt im Lebensjournal unter /trading/
        except Exception:
            url = None
        sys.path.insert(0, str(report.C.REPO / "scripts" / "reports"))
        from telegram_notify import send_telegram_message
        send_telegram_message(report.telegram(r, url))
        print("Telegram: versendet")
    if a.notion:
        try:
            from fusion_lab.notion.sync_screener import sync
            print(sync(r))
        except Exception as e:  # Notion darf den Lauf nie abbrechen
            print(f"Notion-Fehler: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
