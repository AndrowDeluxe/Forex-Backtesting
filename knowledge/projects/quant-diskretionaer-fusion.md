# Project: Quant × diskretionäres Trading (Dachprojekt)

**Ziel**: Die frühere diskretionäre Analyse des Nutzers (Makro, Struktur,
Planung -- das Journal ist bereits übernommen) reproduzieren, testen und das
Beste davon automatisieren. Endziel: ein voll automatisierter,
selbstlernender Bot, der auf dem Wissen des Nutzers startet, sich selbst
weiterentwickelt und profitabel handelt -- wo sinnvoll mit Agenten/
Subagenten. Börse allgemein, aber **Aktien getrennt von Forex/Rohstoffen**.

**Status**: Gestartet 2026-10-04. Aktueller Strang: **0 (Inventur /
Material-Import)**. Code-Ordner: `fusion_lab/` (Repo-Wurzel).

Löst den Dashboard-Punkt "Manuelles Monatsjournal + Quant-System-
Verschmelzung" (2026-09-02) ab -- der Journal-Teil ist laut Nutzer erledigt.

## Entscheidungen (Nutzer, 2026-10-04)

- **Notion = Cockpit + Zwischenablage** (Sichtbarkeit: Makro-Übersicht,
  Analysen, Entscheidungslog des Bots). `knowledge/` bleibt die
  verbindliche, git-gesicherte Quelle der Wahrheit -- Regeln und
  Entscheidungen werden hierher zurückgeschrieben, nicht nur in Notion.
- **Material-Import automatisch** über APIs: OneNote (Microsoft Graph),
  Telegram-Gruppen (Telethon), inkl. Mentor-Material.
- **Start mit Makro** als Basis für FX/Rohstoffe, übergreifend Aktien. Die
  Makro-Analyse des Mentors soll künftig automatisiert werden.
- **Aktienanalyse + Aktienbot = eigenes Projekt** ([[aktien-analyse-und-bot]]),
  startet erst, wenn die Makro-Basis steht.
- **ELITE 3 = Haupt-Input für neues Wissen, Erkenntnisse und Aufgaben**
  (Nutzer, 2026-10-07). ELITE 3 ist die aktuelle Mentoring-Gruppe; neue
  Inhalte landet der Nutzer künftig direkt in der Notion-Datenbank
  „🎓 ELITE 3“ statt in OneNote (OneNote = Altbestand, wird importiert).
  Wissen dort ist erst verbindlich, wenn es nach `knowledge/` übernommen
  ist (Häkchen „In knowledge/ übernommen“) -- Übernahme-Routine steht noch aus.
- **Eigener Repo-Ordner `fusion_lab/`** statt separatem Repo -- vorhandene
  Makro-Bausteine bleiben direkt importierbar, ein Second Brain.

## Freigabe-Gates (3 Stufen, Nutzer bestätigt 2026-10-04)

| Stufe | Wer entscheidet | Beispiele |
|---|---|---|
| 1 | Bot/Agent autonom, mit Log + Rückgängig | Retries, Datenlücken, kleine Bugfixes in Paper-/Analyse-Code |
| 2 | Autonom, mit Telegram-Meldung | Parameter innerhalb vorher freigegebener Bandbreiten |
| 3 | Nur der Nutzer (Plan-Modus) | neue Regeln, Risiko, **alles mit echtem Geld** |

## Leitplanken

- **Strikt getrennt von den Live-Bridges**: `fusion_lab/` importiert keine
  Bridge und wird von keiner importiert (Muster siehe
  [[agentisches-research-system-und-self-learning-bot]]).
- **Makro muss sich im Test beweisen** wie jede andere Idee: der frühere
  Zins-Spread-Indikator hatte keinen Edge ([[bond-yield-spread-indikator]]).
  "Der Mentor macht es so" ist kein Mechanismus (Edge-Card-Grundregel 4).
- Rohmaterial (OneNote, Telegram) ist privat → `fusion_lab/raw/` gitignored.

## Stränge

- [ ] **0 Inventur** -- Material automatisch importieren
  (`fusion_lab/ingest/`), Bestandteile der alten Analyse listen, je mit
  Quelle (eigenes Wissen / Mentor). Ergebnis befüllt die Checkliste in
  [[persoenlicher-tradingplan-validierung]].
  - [x] Telegram „SMH Trade & Invest“ (07.10.): 10.427 Nachrichten,
    ~660k Zeichen, 2.658 Bilder, 14.03.2025–02.10.2026.
  - [x] OneNote „Finanzielle Freiheit Neu / Smart Money Trading“ (09.10.):
    **3.224 Seiten**, ~16.000 Bilder, ~7 GB (Schätzung war 1.200). 368
    Seiten mit doppeltem Dateinamen nachgeladen, Bestand vollständig: 3.225
    Seiten, 11 GB, 0 Namensdopplungen (Fix
    `onenote_fix_names.py`).
    Fortsetzen: `python -m fusion_lab.ingest.onenote --notebook
    "Finanzielle Freiheit Neu" --section "Smart Money Trading"`.
  - [x] Telegram „SMH Daily Update“ (vollständig seit 16.10.: 6.579
    Nachrichten bis 16.10.2026; früherer Hinweis: Import 09.10., Stand
    13.09.2026): ~100 Makro-Reports als PDF ab 06.08.2025, Sonntag +
    Mittwoch. Drei Format-Generationen; seit 28.06.2026 einheitlich
    „SMT Macro Desk“ (Regime, G8-Ranking Makro/Rates/Preis/Quant,
    Szenarien, Trades mit 5 Gates/Aktivierung/Invalidierung) → Vorlage
    für den Makro-Agenten. Ältere Reports teils Bild-PDFs (OCR nötig).
  - [ ] „Währungsstärke G8“ (SMHxSMT, Thema „SMT & Markt“, täglich ab
    24.08.2026, Bild): laut Fußzeile Zustandsmodell auf FRED/BIZ-Daten ab
    1999. Score = Mittel der drei z-Werte 1W/1M/3M (nachgerechnet an
    06.10.: USD, GBP, NZD stimmen). Damit **nachbaubar und über ~27
    Jahre backtestbar**; die geposteten Tagesbilder dienen als
    Kalibrierung. Inhaltlich Querschnitts-FX-Momentum (bekannte, eher
    schwache Literatur-Anomalie) → Tresor/Overfitting-Sperre gilt.
  - **Reihenfolge Makro (Nutzerentscheid 09.10.)**: (1) alte Reports
    testen und klären, wie sich daraus automatisiert Trades erzeugen
    lassen; (2) danach Agent, der genau diese Reports schreibt und mit dem
    Nutzer interagieren kann. Agent nur vorwärts messbar (LLM kennt den
    Ausgang der Vergangenheit).
  - **Neuer Input für den Makro-Agenten (Nutzer, 14.10.)**: Dennis hat am
    14.10. zwei neue Makro-Reports hochgeladen. Einer davon ist ein sehr
    ausführlicher, tieferer Ansatz. Nutzerentscheid: dieses Wissen direkt
    in den Agenten integrieren.
    - Noch nicht importiert: Der Telegram-Bestand endet am 08.10.
    - Erst inkrementell importieren (`python -m fusion_lab.ingest.telegram`),
      dann lesen.
    - Den Ansatz als Baustein in [[makro-faktoren-katalog]] aufnehmen.
      Messbar ist er nur vorwärts bzw. über regelbasierte Teile, siehe
      Leitlinie unten.
  - **Leitlinie (Nutzer 10.10.)**: erst Daten + Makro-Analysen als
    einzelne Bausteine sammeln (G8-Stärke ist der erste, nachgebaut, als
    Signal allein negativ), erst später kombinieren und daraus einen Edge
    bauen. Nächster Schwerpunkt: Makro-Report automatisieren, gestützt auf
    das Makro-Wissen aus OneNote.
  - **Anforderung Makro-Agent (Nutzer 16.10.)**: echte, tiefe Analyse vor
    Report und vor jeder Trade-Freigabe. Dafür Datenschicht je G8-Währung
    (Zinsen/Erwartungen, CPI inkl. Bestandteile, Arbeitsmarkt, Wachstum,
    Exporte/Handel …) plus Wirtschaftskalender mit Konsens (Überraschung =
    Ist minus Konsens; Konsensquelle ist der Engpass). Der Agent muss die
    Daten, an denen ein Event-Trade hängt (z. B. „nach Kanada-CPI“), selbst
    beobachten. Wirkketten „Event → Erwartung → Währung → Gate“ aus den
    extrahierten Aktivierungstexten der 800 Report-Ideen ableiten. → Teil des
    Plan-Modus Phase 2.
  - [x] **Makro-Faktor-Katalog (12.10.)**: [[makro-faktoren-katalog]] -- OneNote
    Makro Education / Bankreports / News+Quick Notes+Incentive entdoppelt:
    49 Faktoren (mit Rolle im Report, Datenquelle, testbar), 13 Regime-
    Schemata, 37 Regeln + 9 Widersprüche, 12 Testkandidaten. Lücke: ~33
    Bild-Seiten (Endogene/Exogene Analyse, Gatekeeping, Reflektion) nicht
    ausgewertet. Grundlage für den Makro-Agenten (Strang 3).
  - [ ] Inventur selbst (Material sichten → Bestandteile-Liste).
    - [x] Inhaltsverzeichnis (09.10.): `python -m
      fusion_lab.inventory.onenote_toc` → `raw/onenote/_toc.md` und
      `_pages.csv`. Kategorien: Regeln & Edges 175 Seiten, Makro 216,
      Technik 131, Mindset 402, Journals 2.014, Calls 287.
    - [x] Entwurf Bestandteile-Liste A–F (09.10.) in
      [[persoenlicher-tradingplan-validierung]], Basis „Tradingplan 1.1
      2026“. Wartet auf die Durchsicht durch den Nutzer.
    - [ ] Noch nicht gesichtet: Makro Education (675 kB), SMH Calls
      2025/26, „Aufarbeitung GS Prozess“ (E4), Elite 2 „Settlements Ficker
      Edge“, Telegram-Material. Acht Final-Edges bestehen nur aus
      Chartbildern, der Nutzer muss ihre Regeln diktieren.
  - Nur dieses Notizbuch/dieser Abschnitt ist Trading -- die übrigen
    Notizbücher und Abschnitte sind privat und werden NICHT importiert.
- [ ] **1 Edge Cards** je Bestandteil ([[edge-card-workflow]]).
- [ ] **2 Reproduzieren + Testen** -- Phasen 4-6 ([[backtest-standard-process]]).
- [ ] **3 Analyse automatisieren** -- zuerst Makro: tägliche Analyse,
  noch ohne Handel.
- [ ] **4 Sichtbarkeit** -- Notion-Cockpit: Makro-Übersicht, Analysen,
  Entscheidungslog mit dem "Warum" jeder Handlung (gleichzeitig die
  Lerndaten für Strang 7).
  - [x] Grundgerüst (07.10.): Seite „Trading Fusion Cockpit“, eigene
    API-Integration (nicht der claude.ai-Connector -- geplante Bot-Läufe
    müssen ohne Session schreiben können). 5 Datenbanken: ELITE 3
    (Mentoring: Wissen/Erkenntnis/Aufgabe/Material/Session), Makro-Übersicht,
    Analysen, Entscheidungslog (Bot), Zwischenablage.
    `fusion_lab/notion/setup_cockpit.py` gleicht Titel/Felder idempotent ab.
  - [ ] Übernahme-Routine: neue ELITE-3-Einträge regelmäßig lesen, Wissen
    nach `knowledge/` überführen (bzw. als Edge-Card-Kandidat markieren),
    Häkchen setzen. Aufgaben ggf. mit Bot-Beitrag vorbereiten.
- [ ] **5 Ausführung auf Paper** -- FX/Rohstoffe über MT5-Demo (Aktien siehe
  [[aktien-analyse-und-bot]]).
- [ ] **6 Agentenschicht** = Strang A in
  [[agentisches-research-system-und-self-learning-bot]].
- [ ] **7 Selbstlernen** = Strang B dort; lernt aus dem Entscheidungslog,
  Änderungen laufen durch die Gates oben.

Jeder Strang bekommt beim Start einen eigenen Plan-Modus-Durchlauf.

## Wiederverwendbare Bausteine (für Strang 3)

- `bond_yield_indicator/fred.py` -- FRED-Loader
- `asian_range_breakout/cot.py` -- CFTC-COT-Positionierung
- `news_calendar/` (`fred_releases.py`, `eurostat_calendar.py`, `filter.py`) -- Wirtschaftskalender
- `ou_paper_backtest/monte_carlo.py`, `walk_forward.py`, `strategy/metrics.py` -- Phase 6
- **Unverarbeitetes Clipping `Clippings/Systematic Macro Modell 1.pdf`**
  (gefunden beim Lint 2026-10-04) -- vor Strang 3 sichten, möglicher
  Rahmen für die Makro-Automatisierung.

## Nächster Schritt

**Plan (Nutzer, 14.10.):**
- **Läuft parallel (Nutzer):** Makro-Reports testen und Makro-Agent bauen
  (Strang 3).
- **Eigene Session, sobald alle Daten aus OneNote und Telegram da sind**
  (wartet auf „SMH Daily Update“): Trading-Edges als Edge Cards (Strang 1),
  neben der Makro-Analyse. Einstieg dort:
  1. Durchsicht des Inventur-Entwurfs in
     [[persoenlicher-tradingplan-validierung]] (A–F): Fehlt etwas? Ist
     etwas falsch einsortiert?
  2. Regeln für die 8 Final-Edges diktieren, die nur als Chartbilder
     vorliegen.
  3. Reihenfolge der Edge Cards festlegen. Kandidat zuerst: C1 (bringt ein
     höherer Konfluenz-Score mehr Gewinn pro Trade?).
- Erledigt 09.10.: Inhaltsverzeichnis + Inventur-Entwurf.
- Offen aus 07.10.: Copy-Trading-Idee (erst Calls aus dem Verlauf
  nachtesten, Ideen-Inbox).

Strang 0: Nutzer legt die Zugänge an (Anleitung in `fusion_lab/README.md`):
Azure-App für OneNote, Telegram-API-Zugang, Notion-Connector in claude.ai.
Danach Vollimport, dann Inventur.
