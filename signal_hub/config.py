"""Pfade, Risiko-Profile und Konstanten des Signal-Hubs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOURNAL = ROOT / "journal" / "signals.csv"          # alarmierte Signale + Entscheidung + Paper-Ergebnis (committet)
ALL_SIGNALS = ROOT / "journal" / "grundsignale.csv"  # alle Grundsignale (auch unter der Schwelle) fuer spaetere Auswertung
STATE = ROOT / "state" / "state.json"                # Telegram-Offset, verarbeitete Kerzen (nicht committet)
LOCKFILE = ROOT / "state" / "journal.lock"
CHARTS = ROOT / "charts"                             # PNGs (nicht committet)
OUT = ROOT / "out" / "signals.json"                  # fuer die App (Stufe 5)
TZ = "Europe/Berlin"
MARKETS = ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF", "XAUUSD", "XAGUSD")
# Lake-Quelle je Markt fuer Frische-Pruefung und Paper-Simulation (feinste verfuegbare Aufloesung)
LAKE_BARS = {"EURUSD": ("EURUSD", "M5"), "GBPUSD": ("GBPUSD", "M15"), "AUDUSD": ("AUDUSD", "M15"),
             "NZDUSD": ("NZDUSD", "M15"), "USDJPY": ("USDJPY", "M15"), "USDCAD": ("USDCAD", "M15"),
             "USDCHF": ("USDCHF", "M15"), "XAUUSD": ("GOLD", "M15"), "XAGUSD": ("SILVER", "M15")}
TF_MIN = {"M5": 5, "M15": 15, "H1": 60}

# Risiko je Kontotyp (Nutzer 19.11.): Ausfuehrung identisch, Risiko getrennt.
PROFILES = {
    "EK": {"risk": 0.01, "max_trades_day": 3, "week_stop": -0.05, "trailing_dd": None, "kapital_ref": 10_000},
    # Funded = FK-/IQ-Regeln (fk_instant_funding/paper_bot.py): max. 0,5 % Verlust je Position vom Startkapital,
    # 5 % Trailing-Drawdown (Tagesende). Max. 3 Trades/Tag wie EK (eigene Annahme).
    "Funded": {"risk": 0.005, "max_trades_day": 3, "week_stop": None, "trailing_dd": 0.05, "kapital_ref": 100_000},
}
# Paper-Ausstieg = beste Familie aus Test 4: Ziel 3R, BE nach 1R, max. 60 H4-Kerzen
PAPER_TARGET_R, PAPER_BE_R, PAPER_MAX_DAYS = 3.0, 1.0, 10
REMIND_AFTER_MIN = 60
