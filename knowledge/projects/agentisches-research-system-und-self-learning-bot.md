# Project: Agentisches Research-System + separater Self-Learning-Bot

**Ziel**: Zwei getrennte, aber thematisch verwandte Ausbaustufen für Claude/
Agenten in diesem Repo:

- **Strang A**: ein Agentensystem, das den bestehenden 8-Phasen-Backtest-
  Prozess (`app_pages/education_gold_intraday.py`, siehe
  `areas/backtest-standard-process.md`) automatisiert — inklusive
  autonomer Ideen-Findung, nicht nur Ausführung vorgegebener Ideen.
- **Strang B**: ein komplett separater, "live-lernender" Bot (Modell passt
  sich laufend selbst an, statt manuell gesweept zu werden), strikt
  getrennt von allen bestehenden Live-Money-Bots, zuerst über Alpaca-
  Paper-Trading getestet.

**Status**: **Geparkt** (Nutzerentscheid 2026-09-07: "das bauen wir
frühestens in ein paar Wochen"). Kernentscheidungen sind geklärt (siehe
unten), aber noch nichts gebaut — kein Code, kein neuer Skill/Agent, kein
neues Repo-Paket. Diese Notiz sichert nur den Entscheidungs- und
Rechercheanstand, damit er bei Wiederaufnahme nicht neu erarbeitet werden
muss. Siehe auch Claude-Memory `ml-self-learning-idea` (ursprünglicher,
noch ungescopter Parkpunkt vom 2026-08-12).

## Strang A: Agentensystem für den 8-Phasen-Prozess

**Entscheidung (2026-09-07)**: Agenten sollen zusätzlich zur Ausführung
vorgegebener Ideen auch **autonom neue Kandidaten finden** — erweitert also
`scripts/research_paper_pipeline.py` (bisher: SSRN/arXiv-Suche → PDF-
Ingest → Claude-Extraktion → einfache Auto-Backtests → Store, deckt
Phase 1-3 teilautomatisiert ab), statt nur auf Zuruf ("teste diese Idee")
zu reagieren.

**Bestehende Bausteine, die wiederverwendet werden sollten** (Rechercheergebnis, nicht neu bauen):
- `.claude/skills/second-brain-lint/` als Strukturvorlage für neue Skills:
  dünnes deterministisches Script + Skill-Ebene für Triage/Urteil + fester,
  benannter Write-back-Ort (dort: `DASHBOARD.md`/`CHANGELOG.md`; hier
  vermutlich die passende `resources/`/`projects/`-Notiz oder
  `app_pages/*.py`).
- Phase 6 (Robustheit) hat bereits wiederverwendbare Bausteine:
  `ou_paper_backtest/monte_carlo.py` (Block-Bootstrap),
  `ou_paper_backtest/walk_forward.py` (rollierende Re-Estimation),
  `strategy/metrics.py::breakeven_spread_bps` (Kosten-Sensitivität).
- Der `research_*.py`-Skriptbestand (243 Dateien) dokumentiert bereits
  durchgängig die Walk-Forward-/Holdout-Disziplin in den Docstrings
  (inkl. "wievielte Peek auf dieses Holdout"-Tracking) — dieses Muster
  sollte ein neuer Agent/Skill erzwingen/prüfen können, nicht neu erfinden.
- `knowledge/areas/edge-card-workflow.md` ersetzt Phase 1-3 NUR für
  hand-entwickelte/getradete Strategien ohne Paper-Ursprung — für die
  autonome Ideen-Findung (Paper-basiert) bleibt der normale Phase-1-3-Flow
  maßgeblich, beide Wege müssen in der späteren Design-Phase sauber
  auseinandergehalten werden.

**Offene Design-Fragen für die spätere Bauphase** (bewusst noch nicht entschieden):
- Wie viele/welche spezialisierten Agenten (z.B. Researcher/Screener,
  Backtest-Runner, Robustheits-Checker als getrennte `.claude/agents/*.md`)
  vs. ein einzelner orchestrierender Skill, der bestehende Scripts aufruft?
- Wo genau sitzen die Freigabe-Gates vor Portfolio-/Live-Schritten (Phase 7
  "vor jedem Commit/Push mit dem Nutzer abstimmen" gilt schon heute manuell
  — wie wird das in einem autonomeren Fluss nicht umgangen)?
- Wie wird "autonome Ideen-Findung" mit der bestehenden Data-Snooping-
  Disziplin (Holdout-Peek-Tracking) vereinbart, wenn Agenten schneller/öfter
  neue Kandidaten vorschlagen als bisher manuell?

## Strang B: Separater Self-Learning-Bot

**Entscheidung (2026-09-07)**:
- **Lernparadigma**: Hybrid aus Online/inkrementellem ML und Reinforcement
  Learning (genaue Aufteilung noch offen für die Design-Phase — ein
  möglicher Ausgangspunkt, NICHT bereits entschieden: ML-Schicht für
  Signal-/Richtungsprognose, RL-Schicht nur für Sizing-/Timing-Policy
  obendrauf, kleinerer Aktionsraum = weniger Instabilität als volles
  End-to-End-RL).
- **Testumgebung**: Paper-Trading via Alpaca. Offizieller MCP-Server
  bestätigt: `alpacahq/alpaca-mcp-server` — defaultet auf Paper-Trading,
  65 Tools über Trading- + Market-Data-API, zuletzt aktiv Anfang September
  2026. Neue Assetklasse (US-Aktien/ETFs/Crypto/Optionen) statt der
  bisherigen FX/Metalle/Indizes.
- **Reihenfolge**: Strang A zuerst, Strang B danach (risikoärmerer,
  schneller nutzbringender Strang zuerst).

**Wichtigste Leitplanke — strikte Trennung von Live-Geld** (Rechercheergebnis):
Bestehende Bot-Pakete (`challenge_portfolio/`, `ek_portfolio/`,
`fk_instant_funding/`) folgen alle demselben Isolationsmuster: eigener
Ordner, eigene `<name>_logs/`, eigener gitignored `telegram_config.py`,
und — kritisch — `challenge_portfolio/paper_bot.py` wird von der echten
`Funded-Portfolio-Bridge` **direkt importiert** (kein eingefrorener
Deploy-Snapshot), siehe CLAUDE.md "Begriffe/Naming". Der Self-Learning-Bot
MUSS diesem Muster folgen: eigener Ordner (Name noch offen, z.B.
`self_learning_lab/`), eigene Logs, eigener Alpaca-Paper-Key, **kein**
Import von/durch irgendeine bestehende Live-Bridge, keine Wiederverwendung
von `data_lake/` (deckt die neue Alpaca-Assetklasse ohnehin nicht ab —
eigene, neue Datenanbindung nötig).

**Risiko-Warnung aus der Repo-Historie** (unbedingt in der Design-Phase
berücksichtigen): Ein früherer RL-Ansatz aus einem Paper (Kalman-Enhanced
Deep RL für Gold, siehe `strategy/kalman_filter.py`/`app_pages/kalman_filter.py`)
wurde am 2026-08-20 nach Tests **verworfen** — keine Verbesserung
gegenüber reinem Kalman-Smoothing. Es gibt aktuell keinerlei ML/RL-
Code-Basis im Repo (nur ein statisches, offline gefittetes GMM in
`triple_ma_strategy/regime.py`, kein Online-Lernen). Der Hybrid-Ansatz
sollte dieselbe Walk-Forward-/Holdout-Disziplin wie der Rest des Repos
durchlaufen, bevor überhaupt Paper-Trading beginnt — sonst Regression statt
Verbesserung (siehe auch Ernest Chans "Conditional Parameter Optimization",
bereits als Konzept in der Kelly-Formel-Education-Seite verankert, als
risikoärmerer Referenzpunkt falls der volle Hybrid zu instabil wird).

## Nächster Schritt

Nichts akut — bewusst geparkt. Bei Wiederaufnahme (frühestens in ein paar
Wochen): erst Strang A grob durchdesignen (Agenten-Aufteilung, Freigabe-
Gates), dann bauen; Strang B erst danach angehen.
