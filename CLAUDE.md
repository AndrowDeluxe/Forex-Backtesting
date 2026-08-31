# CLAUDE.md

Anweisungen für Claude in diesem Repo. Gelten für JEDE Session (auch parallel
laufende), nicht nur die, die sie geschrieben hat.

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
