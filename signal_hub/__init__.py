"""Signal-Hub: Hybrid-Bestaetigungssystem (Dachprojekt, Plan freigegeben 19.11.2026).

Maschine findet Setups (Stufe 1: H4-Spike), bewertet sie (Merkmale, Makro-Ampel, Risiko) und schickt sie per Telegram mit
Chart und Ja/Nein-Knoepfen. Der Nutzer bestaetigt; jede Entscheidung landet im Journal und wird als Paper-Trade
simuliert (bestaetigte UND abgelehnte -- "was waere gewesen"). Keine Orders, kein echtes Geld (Stufe 2: MT5-Demo).

    python -m signal_hub scan       # neue abgeschlossene H4-Kerzen pruefen, Alarme senden (Task alle 10 Min.)
    python -m signal_hub listen     # Telegram-Knoepfe, Verfall, Erinnerungen, Paper-Update (Task alle 2 Min.)
    python -m signal_hub status     # Journal-Uebersicht
Roadmap: knowledge/projects/signal-hub.md
"""
