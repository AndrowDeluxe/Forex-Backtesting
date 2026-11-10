# Handoff 2026-11-11 -- Remy-King-Buch: Edges + Filter B4–B8

Stand und Zahlen: [[remy-king-trading-strategie-top1]] (Abschnitte „Test-Ergebnisse“ und „Filter B4–B8“).

## Offene Fäden (Nutzerentscheid ausstehend)
- **Gold-Deckel je Konto** (B4): Stapelung fast nur Gold/USD, seit W40 max. 2–4 gleichgerichtete
  Positionen, W38/39 bis 22 (alter CTNL-Fehler). Vorschlag max. 2 gleichgerichtete Gold-Positionen über
  alle Beine je Konto = Live-Eingriff in EK/Funded/FK-Bridges → nur nach ausdrücklichem Go, Bridges sind
  nicht git-gesichert (Backup-Ordner anlegen).
- **C2-Stufe-2-Kandidaten**: Carry-Veto (Matrix M2, OOS +0,39 R, t 2,2) und Rohstoff-Veto B6 (C2 „mit“ >
  „gegen“ in allen Zellen, OOS n 47) an die Filter-Matrix der parallelen Session (`htf_daily_trade/
  filter_matrix.py`, Stufe 2) übergeben – Nutzer fragen, ob ja; nicht in deren Dateien schreiben, solange
  die Session läuft.

## Learnings
- Die parallele Session hatte B5 (M1) und B8 (X4 COT-Index konträr) schon getestet → vor neuen
  Filtertests immer erst `htf_daily_trade/filter_matrix*.csv` lesen.
- Neue Sperr-Regel seit 10.11.: OOS frei (`Lock.oos_only`), Tresor 6 Monate einmalig.
- Wiederverwendbare Daten in `data_cache/remy/` (gitignored, lokal): Zins-Langhistorie ab 2003,
  Legacy-COT ab 2000, ForexFactory-Kalender 2007–2026 (Ist/Konsens), H1 FX ab 2007.

## Fehlannahmen
- B4 zeigte anfangs 22 gleichzeitige Gold-Shorts – zuerst für Messfehler gehalten, war aber echt
  (W38/39), heute nicht mehr.
