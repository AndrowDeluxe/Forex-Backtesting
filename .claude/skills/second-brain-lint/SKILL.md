---
name: second-brain-lint
description: Fuehrt den Lint-Check aus CLAUDE.md Regel 6 fuer knowledge/ aus (tote Wikilinks, verwaiste Seiten, veraltete Dashboard-Daten, unverarbeitete Clippings, Widersprueche) und traegt die Befunde korrekt in DASHBOARD.md ein. Nutzen bei "Lint-Check", "second brain aufraeumen", "knowledge/ pruefen", "tote Links", "neue Clippings", oder wenn seit dem letzten Durchlauf (siehe DASHBOARD.md unter der Statustabelle) mehrere Wochen vergangen sind.
---

# Second-Brain-Lint

Deckt die automatisierbaren Teile von CLAUDE.md Regel 6 ab: (a) tote
`[[wikilinks]]`, (b) veraltete "Zuletzt geprueft"-Daten, (d) verwaiste
Seiten, (e) unverarbeitete Dateien in `Clippings/` (Raw-Inbox: Web-Clips,
PDFs, Bilder, eigene Notizen -- die der Nutzer dort parkt, um sie spaeter
verarbeiten zu lassen, siehe `resources/second-brain-methodik.md`). Punkt
(c) Widersprueche zwischen Notizen bleibt Handarbeit -- dafuer beim
Durchgehen der Befunde ein paar thematisch naheliegende Notizen
(`resources/`, aktive `projects/`) gegenlesen, kein separates Tool.

## Ablauf

1. Skript laufen lassen:
   ```
   python knowledge/scripts/lint.py
   ```
   Optional `--stale-days N` (Default 21) fuer die Alters-Schwelle der
   Dashboard-Status-Tabelle.

2. Rohbefunde triagieren, bevor irgendwas ins Dashboard geschrieben wird:
   - **False positives ignorieren**: Das Wort "wikilinks"/aehnliche Begriffe
     in Klammern als literaler Text (kein echter Link), sowie Funde in
     `Clippings/` (Obsidian-Web-Clips, keine kuratierten PARA-Notizen) --
     nur bei echtem Anlass aufnehmen, nicht automatisch.
   - **Cross-System-Links erkennen**: Wikilinks in `reports/` (oder anderswo),
     die auf Claude-Memory-Slugs zeigen (Dateien in
     `C:\Users\<user>\.claude\projects\...\memory\`, NICHT in `knowledge/`)
     sind fuer Obsidian technisch tot, obwohl der referenzierte Inhalt
     existiert -- das ist eine Konventionsfrage (z.B. eigene Zitierform
     statt `[[...]]` fuer Memory-Referenzen), keine reine Aufraeum-Aufgabe.
     -> `🔍 Braucht deine Bestätigung`.
   - **Echte inhaltliche Luecken**: mehrere tote Links auf denselben,
     offensichtlich fehlenden Zielnamen (z.B. ein Prozess/Konzept, das an
     mehreren Stellen referenziert aber nie als eigene Notiz angelegt wurde)
     sind ein Entscheidungspunkt (Notiz anlegen? wo?), kein Tippfehler.
     -> `🔍 Braucht deine Bestätigung`.
   - **Reines Aufraeumen**: einzelne tote Links ohne weitere Bedeutung,
     verwaiste Seiten ohne erkennbaren Grund zur Sorge.
     -> `Offene Aufgaben`, meist **Niedrig**.
   - **Unverarbeitete Clippings**: jede Datei aus dem neuen Abschnitt als
     kurze Liste eintragen (Dateiname reicht, kein Vorab-Distill) ->
     `Offene Aufgaben`, **Mittel** (das ist wartendes Nutzer-Material, keine
     reine Aufraeum-Aufgabe wie tote Links). Nicht selbst verarbeiten,
     ausser der Nutzer sagt explizit "leg jetzt los" -- nur sichtbar machen,
     dass etwas liegt. Ist der Fund neu seit dem letzten Lauf, das auch kurz
     im Chat erwaehnen statt nur im Dashboard zu vergraben.

3. `DASHBOARD.md` nachfuehren:
   - Zeile unter der Statustabelle ("_Letzter Lint-Check..._") mit
     heutigem Datum und Kurzfazit aktualisieren.
   - Befunde gemaess Triage oben einsortieren (nichts stillschweigend nur
     im Skript-Output lassen).
   - Bei inhaltlich relevanten Aenderungen (z.B. neue Notiz angelegt,
     Wikilinks korrigiert) zusaetzlich einen `CHANGELOG.md`-Eintrag
     ergaenzen (CLAUDE.md Regel 1).

Kein Scheduled Task/`loop`-Skill fuer diesen Check einrichten, ohne den
Nutzer vorher zu fragen -- das ist in `DASHBOARD.md` bereits als offener
Bestaetigungspunkt vermerkt.
