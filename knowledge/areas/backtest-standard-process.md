# Area: Backtest-Standardprozess (8 Phasen)

Laufende Verantwortlichkeit ohne Enddatum -- jede neue Strategie (Paper-
Nachbau oder eigene Chart-Idee) durchläuft denselben 8-Phasen-Prozess, bevor
sie als validiert gilt. Quelle der Wahrheit ist der Code in
`app_pages/education_gold_intraday.py` (interaktive Checkliste mit
Fortschritts-Tracking, `education_state/checklist_state.json`) -- diese
Notiz ist die `knowledge/`-Referenz dafür, damit `[[backtest-standard-process]]`
aus anderen Notizen heraus verlinkbar ist, ohne den Code selbst zu duplizieren.

**Wichtigste Regel (siehe `CLAUDE.md`)**: Phase 6 (Robustheit/Monte-Carlo)
läuft VOR jeder Portfolio-/Risiko-Arbeit, nicht danach -- mehrfach real
verletzt (siehe [[gold-ctnl-edge-portfolio]]: Phase 6 wurde dort erst
nachträglich auf Nutzer-Nachfrage nachgeholt, nachdem bereits Portfolio-/
Risiko-Arbeit lief).

## Die 8 Phasen

1. **Recherche** -- Suchbegriff-Kategorien durchgehen, pro Kategorie 2-3
   vielversprechende Paper sammeln, PDFs herunterladen.
2. **Papers teilen & sichten** -- direkt im Chat teilen (kein separates
   Pipeline-Tool nötig), pro Paper Kernthese/Regeln/Timeframe/behauptete
   Performance kurz zusammenfassen.
3. **Erstes Screening** -- einfaches Signal vs. echte State-Machine
   einordnen, Plausibilität grob abschätzen, 2-3 Kandidaten auswählen statt
   alle parallel zu vertiefen, dünnes Material früh aussortieren.
4. **Vertiefung je Kandidat** -- eigenes Backend-Package anlegen (Muster:
   `asian_range_breakout/`), echte Marktdaten nutzen (nicht nur den
   Screening-Proxy), Regeln 1:1 aus dem Paper umsetzen statt frei erfundener
   Parameter.
5. **Kombination mit vorhandenen Bausteinen** -- Kalman-Filter
   (`strategy/kalman_filter.py`), ADX-/VWAP-Deviation-Filter
   (`strategy/indicators.py`), EMA200-Regimefilter (`ou_paper_backtest/`),
   Session-/Uhrzeit-Filter (Muster: CLS-Squeeze, Asian-Range-Breakout) je
   einzeln testen -- hilft/schadet?
6. **Robustheit** -- Walk-Forward/echter Out-of-Sample-Split (anderer
   Zeitraum als beim Fitting), Monte-Carlo-Bootstrap der Trade-Sequenz
   (Muster: `ou_paper_backtest/monte_carlo.py`), Kosten-Sensitivität
   (Spread/Slippage bis zum Breakeven), mehrere Jahre/Marktregime statt nur
   ein gutes Jahr.
7. **Dokumentation & Dashboard** -- ehrlichen Befund festhalten (auch
   negativ), bei robustem Fund eigene `app_pages/*.py`-Seite + Karte auf
   `home.py`, vor jedem Commit/Push mit dem User abstimmen.
8. **Danach** -- Live-/Demo-Vorbereitung, separates Thema, erst auf Zuruf,
   nicht Teil dieses Checklisten-Flows.

**Verknüpfung**: [[paper-verarbeitung]] (vorgelagerter Prozess -- liefert die
Kandidaten, die hier ab Phase 3 einsortiert werden). Gilt unverändert für
Papers/Dokumente als Ausgangspunkt (Nutzerentscheid 2026-09-05). Für
händisch entwickelte/getradete Strategien (kein Paper als Ausgangspunkt)
tritt stattdessen [[edge-card-workflow]] vorgelagert an die Stelle von
Phase 1-3: die dortige Edge Card (Feld 02 REGEL) ist die 1:1-Spezifikation
für Phase 4, ihre Gegenproben (Feld 04) liefern zusätzliche
Kontrollgruppen/Ablations-Tests für Phase 6 Robustheit.
