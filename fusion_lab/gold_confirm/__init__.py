"""Gold Confirmation Framework -- Nachbau des „XAU/USD Institutional Confirmation Framework“ (PDF einer
Bekannten des Nutzers, 14.11.2026) mit ausschliesslich freien Daten.

    python -m fusion_lab.gold_confirm.data      # alle Rohreihen laden -> fusion_lab/data/gold_confirm/

Bausteine: components.py (je Baustein eine Tagesreihe 0..1, hoeher = bullischer, nur Vergangenheit),
score.py (Bloecke Flow/Physical/Price Response/Macro -> Score 0..100, GoldScoreFilter).
Notiz: knowledge/resources/gold-confirmation-framework-pdf.md, Projekt: knowledge/projects/gold-confirmation-score.md
"""
