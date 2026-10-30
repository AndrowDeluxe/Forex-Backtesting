"""Datenschicht A1 des Makro-Agenten (Plan Phase 2, Dachprojekt Strang 3).

Holt Zinsen, Inflation, Arbeitsmarkt, Wachstum, Handel, Kalender + Konsens,
Positionierung und Maerkte je G8-Land aus freien Quellen und legt jeden Wert mit
Abrufzeit ab. Kein Handel, keine Bridge: fusion_lab importiert keine Bridge.

Aufruf:  python -m fusion_lab.macro_data [--only kalender,cftc] [--coverage]
Ablage:  fusion_lab/data/macro_data/ (gitignored)
"""
