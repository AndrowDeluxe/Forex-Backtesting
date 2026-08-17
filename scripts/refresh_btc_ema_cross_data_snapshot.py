"""Aktualisiert den committeten BTCUSDT-Daily-Datensnapshot fuer
app_pages/btc_ema_cross.py.

Grund: `auction_playbook.data.fetch_klines()` cached nach
`data_cache_crypto/` (gitignored - siehe .gitignore) und ruft bei fehlendem
Cache-Eintrag live `api.binance.com` auf. Auf Streamlit Cloud existiert
dieser lokale Cache nie (frischer Checkout bei jedem Deploy), und
Binance.com blockiert Anfragen von vielen Cloud-Provider-IP-Bereichen
(HTTP 451/403) - deshalb crasht die Seite dort mit einem HTTPError beim
Live-Fetch-Versuch (beobachtet 2026-08-17).

Fix nach demselben etablierten Repo-Prinzip wie die Live-Log-Seiten
("Collector laeuft lokal, Seite liest nur committete Daten"): dieses
Skript laeuft lokal (gleicher Rechner, keine Geo-Blockade), schreibt einen
committeten Snapshot nach btc_ema_cross/data/, den load_data() in
app_pages/btc_ema_cross.py bevorzugt liest (Live-Fetch bleibt als
Fallback fuer lokale Entwicklung ohne vorhandenen Snapshot).

Eingebunden in scripts/btc_ema_cross_scan_task.ps1 (taeglicher Task
"BTC-EMA-Cross-Scan"), der den Snapshot mit committet/pusht."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auction_playbook.data import fetch_klines

FULL_START = "2017-08-17"  # BTCUSDT listing date on Binance
SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "btc_ema_cross" / "data" / "btcusdt_1d_snapshot.parquet"


def main() -> None:
    end = datetime.now(timezone.utc).date().isoformat()
    print(f"Fetching BTCUSDT daily {FULL_START} -> {end} (force_refresh) ...")
    df = fetch_klines("BTCUSDT", "1d", FULL_START, end, force_refresh=True)
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SNAPSHOT_PATH)
    print(f"Snapshot geschrieben: {SNAPSHOT_PATH} ({len(df)} Zeilen, bis {df.index[-1]}).")


if __name__ == "__main__":
    main()
