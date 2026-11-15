"""Taeglicher Aktien- + Krypto-Screener (Dachprojekt, Nutzerentscheid 15.11.2026).

Python rechnet Kurse, Kennzahlen, Punktwerte und Preisbereiche; Claude (`claude.exe -p`, Abo) ordnet nur
News/Sentiment ein und waehlt eines der berechneten Szenarien. Ergebnis: Tagesbericht (Markdown + JSON),
Telegram, Notion, Dashboard und ein Forward-Ledger. Keine Orders, keine Bridge.

    python -m fusion_lab.screener aktien [--telegram] [--notion] [--no-llm]
    python -m fusion_lab.screener krypto [--telegram] [--notion] [--no-llm]
    python -m fusion_lab.screener evaluate          # nur Ledger auswerten
"""
