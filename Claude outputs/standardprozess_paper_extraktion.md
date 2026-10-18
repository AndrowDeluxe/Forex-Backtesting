# Standardprozess: Paper-Extraktion

Stand 2026-10-18. Zusammengeführt aus den bestehenden Quellen im Repo. Das ist
nichts Neues, nur der vorhandene Prozess an einer Stelle:

- `knowledge/areas/paper-verarbeitung.md` (Ablauf pro Paper)
- `knowledge/README.md` (CODE-Prozess), `knowledge/_templates/paper_note.md`
- `app_pages/education_gold_intraday.py` (8-Phasen-Backtest-Standardprozess)
- `knowledge/areas/overfitting-sperre.md` (seit 2026-10-05)
- `scripts/research_paper_pipeline.py` + `paper_research/` (automatische Pipeline)

**Geltungsbereich:** Papers und Dokumente. Händisch entwickelte oder getradete
Strategien ohne Paper laufen stattdessen über die Edge Card
(`knowledge/areas/edge-card-workflow.md`).

---

## 0. Wer macht was

- **Du:** Paper teilen, entweder im Chat (PDF/Link/Auszug) oder als PDF in
  `paper_dropbox/` (gitignored).
- **Claude:** macht den ganzen Durchlauf selbst und schreibt die Notiz. Rückfragen
  gibt es nur bei echten Unklarheiten.

## 1. Zwei Eingangswege

| Weg | Wann | Was passiert |
|---|---|---|
| **Im Chat** (Standard) | Einzelne Papers, SSRN-Funde | Claude liest direkt in der Session, ohne API-Key und ohne Pipeline |
| **Automatische Pipeline** | arXiv-Suche + `paper_dropbox/` in größerer Menge | `python scripts/research_paper_pipeline.py` (braucht `ANTHROPIC_API_KEY`) |

### Was die automatische Pipeline macht

1. arXiv-Suche über die Keywords aus `paper_research/config.py` und dazu alle PDFs in `paper_dropbox/`
2. PDF-Text einlesen (`pdf_ingest.py`)
3. **Extraktion** mit Claude Haiku in ein festes JSON-Schema (`extract.py` → `StrategySpec`):
   `asset_class`, `timeframe`, `indicators`, `entry_rule_text`, `exit_rule_text`,
   `risk_rule_text`, `session_filter`, `claimed_performance`, `direction`,
   `complexity`, `entry_conditions`, `notes`
   - Nur, was das Paper wirklich sagt. Keine Parameter erschließen.
   - `simple_signal` nur, wenn alles auf eine Einzelbar-Schwelle oder einen Crossover hinausläuft. Im Zweifel gilt **`stateful`**.
   - `claimed_performance` wird wörtlich übernommen und nicht bewertet.
4. Auto-Backtest **nur für `simple_signal`** auf einem Proxy (EURUSD 2016–2026).
   Das ist ein Screening und kein Nachbau. `stateful` bekommt den Vermerk „needs manual reconstruction“.
5. Speichern (`store.py`, schon verarbeitete IDs werden übersprungen)
6. Stufe 2: Kombinationskandidaten über mehrere Papers (`combine.py`)

## 2. Notiz nach CODE (immer, bei beiden Wegen)

Vorlage: `knowledge/_templates/paper_note.md` → `knowledge/resources/<thema>.md`
(neu anlegen oder an die bestehende Themendatei anhängen).

1. **Capture**: Autoren/Jahr, Quelle/Link, Erfassungsdatum, Weg (Chat/Pipeline)
2. **Organize**: Thema/Tags, `[[Wikilinks]]` zu verwandten Notizen, Project/Area
3. **Distill**: Kernthese in 1–2 Sätzen, zentrales Modell/Filter/Formel, was davon integrierbar ist.
   Nicht das ganze Paper nacherzählen.
4. **Cross-Check**: Lässt sich ein Filter oder Baustein auf eine **andere** bestehende
   Strategie im Repo übertragen? Darin liegt der eigentliche Mehrwert.
5. **Express**: nächster Schritt
   - testbar mit vorhandenen Daten → Backtest starten (siehe 3) und das Ergebnis mit Link zurückschreiben
   - nicht testbar → Grund ausdrücklich in der Notiz vermerken

**Grundregel:** Eine Notiz ist erst fertig, wenn Distill und Express ausgefüllt sind.
Ein reiner Capture-Stub ist das Anti-Pattern, weil er das Second Brain zur Datenhalde macht.

## 3. Vom Extrakt zum Backtest (8 Phasen)

| Phase | Inhalt |
|---|---|
| **1 Recherche** | SSRN-Suchkategorien durchgehen, 2–3 Papers je Kategorie, PDFs laden |
| **2 Teilen & Sichten** | Je Paper Kernthese, Regeln, Timeframe und behauptete Performance kurz zusammenfassen |
| **3 Screening** | Einfaches Signal oder State-Machine? Plausibilität vor jedem Code prüfen. Nur die besten 2–3 Kandidaten vertiefen. Dünnes oder unklares Material aussortieren |
| **4 Vertiefung** | **Zuerst den Split registrieren** (`research_lock.Lock.register_split`: IS / OOS / Tresor = letzte 12 Monate). Eigenes Package anlegen (Muster `asian_range_breakout/`), echte Daten statt Proxy. Regeln 1:1 aus dem Paper, keine erfundenen Parameter |
| **5 Kombination** | Nur auf IS optimieren (`Lock.is_only`), keine OOS-Zahlen ausgeben, jede Variante zählen (`log_trials`). Kandidaten: Kalman, ADX/VWAP-Deviation, EMA200-Regime, Session-Filter. Richtwert max. 9 optimierte Punkte |
| **6 Robustheit** | Walk-Forward/OOS, Monte-Carlo-Bootstrap, Kosten bis Breakeven, mehrere Regime. **Kosten gemessen statt angenommen** (je Broker), Ausführungs-Lag simulieren, Sizing-Nenner und Hebel-Tail prüfen, SL < 3× Round-Trip-Kosten ausweisen. Dann `freeze` und Deflated Sharpe (Ziel > 0,95). **OOS einmal, Tresor einmal** (`unseal`), das Ergebnis zählt in jedem Fall |
| **7 Doku** | Ehrlichen Befund festhalten, auch negativ. Bei robustem Fund eigene `app_pages/*.py` + Karte auf `home.py`. Commit/Push mit dir abstimmen |
| **8 Danach** | Live/Demo ist ein eigenes Thema und läuft nur auf Zuruf |

Phase 6 läuft **vor** jeder Portfolio- oder Risikoarbeit.

## 4. Abschluss

- Ergebnis und Link in die Paper-Notiz zurückschreiben (Express)
- Inhaltlich relevante Änderung → `knowledge/CHANGELOG.md`
- Entscheidung auf Basis eigener Annahme → DASHBOARD „🔍 Braucht deine Bestätigung“
- Nicht-offensichtliche Erkenntnis (Durchbruch oder deine positive Reaktion) → Memory
- Seitenideen → Ideen-Inbox im DASHBOARD
