# CLAUDE.md

Anweisungen für Claude in diesem Repo. Gelten für JEDE Session (auch parallel
laufende), nicht nur die, die sie geschrieben hat.

## Begriffe/Naming

Wenn der Nutzer von **"EK"/"EK Portfolio"** oder **"Challenge"/"Challenge
Portfolio"** spricht, meint er IMMER den echten, live laufenden Bot (echtes
Geld) — NICHT die gleichnamige Repo-interne Paper-Simulation, auch wenn beide
sehr ähnlich heißen:

- **"EK"/"EK Portfolio"** = `EK-Portfolio-Bridge` (außerhalb des Repos,
  `C:\Users\andre\EK-Portfolio-Bridge\`, Tickmill, **LIVE, echtes Geld**).
  NICHT `ek_portfolio/paper_bot.py` (Repo-intern, treibt den separaten
  "EK-Portfolio-Paper"-Task, aktuell bewusst pausiert/Disabled — die Live-
  Bridge fährt dieselbe Logik bereits, siehe `knowledge/DASHBOARD.md`).
- **"Challenge"/"Challenge Portfolio"** = `Funded-Portfolio-Bridge`
  (außerhalb des Repos, TTP + IQ Markets/BeyondIQCapital, **LIVE, echtes
  Geld**), die `challenge_portfolio/paper_bot.py` DIREKT aus dem Repo
  importiert (kein eingefrorener Deploy-Snapshot) — ein Commit an dieser
  Datei wirkt sich beim nächsten Bridge-Lauf unmittelbar auf den echten Bot
  aus.

Bei Aufträgen zu "EK" oder "Challenge" zuerst prüfen, ob der lebende Bot
(Bridge, außerhalb des Repos) oder eine Repo-interne Paper-Variante gemeint
ist — im Zweifel nachfragen statt anzunehmen, besonders wenn Änderungen an
echtem Geld hängen.

## Operative Übersicht (Dashboard/Changelog)

Der Nutzer hat ADHS und verliert leicht den Überblick, wenn Änderungen "im
Hintergrund" passieren, ohne dass irgendwo sichtbar wird, was wann passiert
ist und ob es seinen Vorstellungen entspricht. Deshalb:

1. **Bei jeder inhaltlich relevanten Änderung** (Bugfix, Config-Änderung wie
   DRY_RUN-Flip, Strategie-/Risiko-Entscheidung, Bot aktiviert/deaktiviert,
   neuer Scheduled Task) einen Eintrag in `knowledge/CHANGELOG.md` ergänzen
   (oben einfügen, Format siehe bestehende Einträge dort: Datum, Bereich,
   Kurzbeschreibung, Commit-Hash wo zutreffend).
2. **Bei jeder Änderung/Entscheidung, die auf einer eigenen Annahme beruht**
   statt auf einer expliziten Nutzeranweisung: Eintrag unter "🔍 Braucht
   deine Bestätigung" in `knowledge/DASHBOARD.md` ergänzen. Erst entfernen,
   wenn der Nutzer es explizit bestätigt hat — nicht stillschweigend als
   erledigt behandeln.
3. **Bot-Status-Änderungen** (Task aktiviert/deaktiviert, DRY_RUN geändert,
   neuer Bot/neue Bridge) in der Status-Tabelle in `knowledge/DASHBOARD.md`
   nachführen.
4. Vor Aussagen über "was läuft gerade" den AKTUELLEN Stand prüfen (Task
   Scheduler, `config.py`-DRY_RUN-Flags) statt sich auf das Dashboard allein
   zu verlassen, falls seit dem letzten "Zuletzt geprüft"-Datum viel Zeit
   vergangen sein könnte — das Dashboard ist die Anlaufstelle, kein Ersatz
   fürs Nachprüfen bei echten Zweifeln.

Kleine, fast abgeschlossene offene Punkte (eine Bestätigung, ein letzter
Schritt) haben Vorrang vor dem Eintauchen in ein neu aufgemachtes, größeres
Thema — nicht stillschweigend liegen lassen, wenn der Nutzer etwas Neues
anspricht.

5. **Tangentiale Ideen sofort in die Ideen-Inbox** (Abschnitt in
   `knowledge/DASHBOARD.md`), statt sie entweder sofort voll zu verfolgen
   (und damit das laufende Thema zu verlassen) oder sie zu ignorieren/zu
   verlieren. Ein Satz reicht: was, seit wann, worauf bezieht es sich. Wird
   bei Gelegenheit einsortiert (Task, PARA-Notiz, oder bewusst verworfen).
6. **Lint-Check**: `knowledge/` auf (a) tote `[[wikilinks]]` ohne Ziel-Datei,
   (b) veraltete "Zuletzt geprüft"-Daten in der `DASHBOARD.md`-Statustabelle,
   (c) Widersprüche zwischen Notizen, (d) verwaiste Seiten ohne eingehende
   Links prüfen — automatisiert über `knowledge/scripts/lint.py` +
   Skill `second-brain-lint` (Triage-Logik: Befunde je nach Art einsortieren,
   Widersprüche/Unklarheiten → "🔍 Braucht deine Bestätigung", reines
   Aufräumen → "Offene Aufgaben", meist Niedrig). Läuft **geplant** (nicht
   nur auf Zuruf, seit 2026-09-01 — Second-Brain-Methodik-Video-Vorschlag,
   siehe `resources/second-brain-methodik.md`) über eine geschedulte
   Routine (`schedule`-Skill); zusätzlich weiterhin jederzeit manuell per
   "mach mal Lint" auslösbar. Datum des letzten Durchlaufs in
   `DASHBOARD.md` nachführen (Zeile unter der Statustabelle).
7. **Nicht-offensichtliche Erkenntnisse proaktiv in die Memory — aber mit
   Schwelle, nicht jede Kleinigkeit** (seit 2026-09-02, Nutzerentscheid,
   2026-09-02 präzisiert). Kandidaten: Architektur-Verhalten, das beim
   bloßen Lesen des Codes nicht sofort auffällt, überraschende
   System-Eigenheiten, wiederkehrende Muster, Root-Causes mit Relevanz über
   den akuten Einzelfall hinaus — UND spürbar größere Fortschritte/
   Optimierungen/"spannende" Themen. Zwei Signale, je eins reicht:
   (a) **Gewicht des Funds selbst** — ein echter Durchbruch/eine
   nicht-triviale Optimierung/ein Thema mit klarem "das ist mehr als eine
   Routine-Änderung"-Charakter, nicht jeder kleine Bugfix oder jede
   Konfig-Anpassung (die gehören weiterhin nur ins `CHANGELOG.md`, Punkt 1);
   (b) **Nutzerreaktion** — reagiert der Nutzer sichtbar positiv/begeistert
   ("klingt spannend", "sehr gut", o.ä.) auf einen Fund, ist das ein
   eigenständiger Auslöser, auch wenn der Fund für sich allein eher klein
   wäre. Im Zweifel (Fund wirkt bedeutsam, aber Nutzerreaktion steht noch
   aus) AKTIV FRAGEN ("soll das als Lernpunkt für den Weekly Journal
   geloggt werden?") statt selbst zu entscheiden — weder stillschweigend
   auslassen noch stillschweigend mitschreiben (Nutzerpräzisierung
   2026-09-02: explizit fragen, nicht nur "anbieten").
   Eindeutige Fälle (a oder b klar erfüllt) OHNE Rückfrage als Memory-Eintrag festhalten
   (`C:\Users\andre\.claude\projects\
   c--Users-andre-Forex-Backtesting\memory\`, Typ `project`, gleiches
   Frontmatter-Format wie bestehende Einträge, + Zeile in `MEMORY.md`).
   Kurz halten, nicht das laufende Thema verlassen — gleicher Geist wie die
   Ideen-Inbox (Punkt 5), aber andere Zielschublade: Ideen-Inbox ist für
   unentschiedene KÜNFTIGE Arbeit, dieser Punkt für bereits verifiziertes
   Wissen über bestehendes Systemverhalten. Grund: Der wöchentliche
   `Forex-Weekly-Report`-Task (`scripts/reports/weekly_report_prompt.md`)
   liest für den Abschnitt "Meine Main Erkenntnisse" im Education-Checkup
   automatisch `MEMORY.md` + verlinkte Dateien — ein Fund, der nicht in der
   Memory landet, taucht dort nicht auf.

## Kontextfenster-Hygiene

Übernommen aus einem vom Nutzer geteilten Second-Brain-Methodik-Video
(2026-09-01, siehe `knowledge/resources/second-brain-methodik.md`): Chats
nicht über ~300k Token laufen lassen. Ab dieser Größe lieber eine neue
Session starten (der aktuelle Stand steht ohnehin in `DASHBOARD.md`/
`CHANGELOG.md`/den PARA-Notizen, nicht nur im Chat-Verlauf) statt in einem
einzelnen, immer länger werdenden Gespräch weiterzuarbeiten — hält das
Second Brain als die verlässliche Quelle der Wahrheit, nicht den Chat selbst.

## Research-Wissen (PARA/CODE)

Getrennt von der operativen Übersicht: destilliertes Fachwissen (Papers,
Strategie-Findings) gehört in die PARA-Struktur unter `knowledge/`
(`projects/`, `areas/`, `resources/`, `archive/`) nach dem CODE-Prozess —
siehe `knowledge/README.md` für Details. Nicht in `DASHBOARD.md`/
`CHANGELOG.md` mischen.

## Backtest-Standardprozess

Neue Strategien durchlaufen den 8-Phasen-Prozess aus
`app_pages/education_gold_intraday.py`. Phase 6 (Robustheit/Monte-Carlo)
läuft VOR jeder Portfolio-/Risiko-Arbeit, nicht danach.
