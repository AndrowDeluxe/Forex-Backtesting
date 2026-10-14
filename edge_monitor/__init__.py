"""Fruehwarnung + Kill-Switch fuer kippende Edges (Plan 2026-10-14).

signals.py   Badness-Statistiken je Trade (hoeher = schlechter), nur aus
             bereits geschlossenen Trades.
calibrate.py Schwellen aus Vor-Bruch-Daten per Bootstrap unter "Edge intakt"
             (Fehlalarm-Budget je Jahr), ohne Blick auf den Bruch.
switch.py    Pause + Schattenkonto + Hysterese (Muster: gold_smc_htf_ltf/ctnl_kill_switch.py).
cases.py     Laden der Faelle (ORB, Live-Beine, Zarattini, EU-Open).
"""
