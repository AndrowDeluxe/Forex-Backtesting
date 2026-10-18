# Handoff 2026-10-18 -- Edge aus Trade-Liste 2025

## Learnings
- Das ganze Plus 2025 kam aus händischem Makro/IPDA-Trading: +120 % auf dem
  Eigenkonto (mit eher höherem Risiko) und ~10k $ auf einem 100k-Funded-Konto.
  Bots waren 2025 nicht beteiligt. Memory: `diskretionaer_2025_traegt_funded_fokus.md`.
- Nutzer will den Fokus auf das 100k-Funded-Konto legen, hat aber
  ausdrücklich entschieden: **an Bots und Konten erstmal nichts ändern**.
  Keine Budget-Aufteilung, kein Abschalten von Beinen ohne neuen Auftrag.

## Offene Fäden
- Datenquellen laut Nutzer:
  - Axi-MT4-Trade-Listen, als PDF und Excel gespeichert. Ablageort noch erfragen.
  - Altes Journal, einige Trades darin vollständig rekonstruiert. Vermutlich
    die ~2.014 Journal-Seiten in `fusion_lab/raw/onenote/` (Kategorie
    "Journals" in `_toc.md`), das ist zu prüfen.
  - Eventuell Tradezella.
- Tradezella: **keine Zugangsdaten im Chat annehmen.** Stattdessen einen
  CSV-Export von Tradezella vorschlagen. Falls doch ein API-Zugang nötig ist,
  die Zugangsdaten nur nach `fusion_lab/_secrets.py` (gitignored) legen.
- Bei PDFs [[pdf_textextraktion_klebt_felder_zusammen]] beachten. Die Excel-Datei
  ist die bessere Quelle; die PDF nur zum Gegenprüfen nutzen.
- Hypothese, die zu prüfen ist: Der Dollar fiel im ersten Halbjahr 2025 stark.
  Wenn der Gewinn überwiegend aus USD-Richtungstrades kam, ist ein Teil davon
  Regime und kein reproduzierbares Können.

## Nächster Schritt
- Plan-Modus für diesen Strang im [[quant-diskretionaer-fusion]] (CLAUDE.md
  verlangt einen Plan-Modus-Durchlauf je Strang). Mit dem Nutzer vereinbarte
  Grobschritte:
  1. Trades einlesen und in R umrechnen.
  2. Zuordnen, welche Setups, Instrumente und Sessions den Gewinn getragen haben.
  3. Kontext am Einstieg (IPDA 20/40/60, Sweeps, FVG, Session, Bias) mit
     zufälligen Zeitpunkten vergleichen.
  4. Edge Card mit dem Nutzer schreiben.
  5. Lock registrieren: 2025 nur zum Aufstellen der Hypothese, Test auf
     2018–24, Tresor 2026 genau einmal öffnen.
  6. Makro in drei Varianten testen: Bias wie damals tatsächlich (Journal und
     Reports), ganz ohne Bias, regelbasierter Bias (G8 / Zinsdifferenz).
- Idee steht schon in der Ideen-Inbox in `DASHBOARD.md` (18.10.). Beim Start
  dort einsortieren unter "Als Nächstes".
