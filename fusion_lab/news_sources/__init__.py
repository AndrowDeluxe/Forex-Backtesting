"""Echte News-/Sentiment-Quellen + Claude-Einordnung + Forward-Ledger je Quelle (Plan 21.11.2026).

    python -m fusion_lab.news_sources collect      # Quellen holen, Status je Quelle (ohne Claude)
    python -m fusion_lab.news_sources snapshot [--symbols=SPY,BTC]   # Quellen + Claude, latest.json schreiben
    python -m fusion_lab.news_sources record       # Tageslauf: Snapshot inkl. Alpha Vantage -> Ledger
    python -m fusion_lab.news_sources report       # Traegt welche Quelle? (Trefferquote vs. Kontrolle)

Genutzt vom Prosper-Kursprojekt (Lektion 5) als Research-Provider anstelle von Grok.
"""
