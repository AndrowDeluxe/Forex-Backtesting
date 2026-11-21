"""Feste Einstellungen des TradingAgents-Forward-Tests (Nutzerentscheid 21.11.2026)."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = Path(__file__).resolve().parent
# Testlaeufe lenken das Ledger per Umgebungsvariable um, damit nichts ins echte Ledger faellt.
LEDGER_DIR = Path(os.environ.get("AGENT_FORWARD_LEDGER") or PKG / "ledger")
DECISIONS = LEDGER_DIR / "decisions.csv"
RUNS = LEDGER_DIR / "runs.csv"
SUMMARY = LEDGER_DIR / "summary.json"
MEMORY_LOG = LEDGER_DIR / "memory.md"
REPORTS_DIR = LEDGER_DIR / "reports"

TA_HOME = Path(r"C:\Users\andre\TradingAgents")
TA_CACHE = TA_HOME / "cache"

# Korb: fuenf Sektoren, damit die Entscheide nicht alle am selben Thema haengen.
TICKERS = ["NVDA", "JPM", "XOM", "UNH", "WMT"]

# Analysten: der Sentiment-Analyst faellt weg (Reddit liefert HTTP 403).
ANALYSTS = ["market", "news", "fundamentals"]

QUICK_MODEL = "haiku"     # Analysten, Debatten, Trader, Reflexion
DEEP_MODEL = "sonnet"     # Research Manager, Portfolio Manager
LLM_TIMEOUT = 600

HOLDING_DAYS = 5
BENCHMARK = "SPY"

START = "2026-11-23"                  # erster offizieller Forward-Tag (davor = Probe)
EVAL_AFTER_WEEKS = 12
HURDLE = ("Frühestens nach 12 Wochen auswerten. Erfolg = der Agent schlägt beim Richtungs-Alpha alle drei "
          "Kontrollen (immer Buy, Zufall, Momentum) und t > 2 über Wochenmittel.")

SCORE = {"Buy": 2, "Overweight": 1, "Hold": 0, "Underweight": -1, "Sell": -2}
SOURCES = {"agent": "Agenten-Team", "always_buy": "Immer Buy", "random": "Zufall", "momentum": "Momentum 20 T"}


def ta_config() -> dict:
    """TradingAgents-Config: Standard + unsere Abweichungen."""
    from tradingagents.default_config import DEFAULT_CONFIG
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(
        results_dir=str(TA_HOME / "logs"),
        data_cache_dir=str(TA_CACHE),
        memory_log_path=str(MEMORY_LOG),
        max_debate_rounds=1,
        max_risk_discuss_rounds=1,
        max_tool_rounds=2,
        holding_period_days=HOLDING_DAYS,
        benchmark_ticker=BENCHMARK,
        output_language="English",   # Rating-Erkennung im Freitext-Weg braucht die englischen Begriffe
        checkpoint_enabled=False,
    )
    return cfg
