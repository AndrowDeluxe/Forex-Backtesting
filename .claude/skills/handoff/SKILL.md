---
name: handoff
description: Schreibt eine Handoff-Datei nach `knowledge/_handoff/`, wenn eine Session endet, das Kontextfenster sich der ~300k-Token-Grenze naehert (siehe CLAUDE.md "Kontextfenster-Hygiene"), oder der Nutzer explizit "Handoff"/"Session-Uebergabe" sagt. Haelt NUR fest, was sonst nirgendwo landet (Learnings, Fehlannahmen, offene halbfertige Gedanken) -- kein Task-Recap, das aus Git/DASHBOARD/CHANGELOG rekonstruierbar ist. Am Anfang einer NEUEN Session immer zuerst `knowledge/_handoff/` auf wartende Dateien pruefen.
---

# Session-Handoff

Ersetzt "Chat einfach voll laufen lassen" bzw. blindes `/compact` am
Kontextfenster-Limit (CLAUDE.md "Kontextfenster-Hygiene", ~300k Token) durch
eine bewusste Übergabe: was diese Session weiß, das sonst mit dem
Chat-Fenster verloren ginge.

## Wann schreiben

- Kontextfenster nähert sich der ~300k-Token-Grenze (per Statusanzeige/
  `/context` einschätzen).
- Nutzer sagt explizit "Handoff schreiben" / "Session-Übergabe" / "Übergabe
  für die nächste Session".
- Session endet mitten in einem mehrteiligen Thema. Nicht bei jedem
  Sessionende nötig — bleibt nichts Unfertiges/Nicht-Dokumentiertes übrig,
  einfach nichts schreiben (siehe unten, "wenn nichts zutrifft").

## Was rein gehört (und was nicht)

**NICHT wiederholen**, was ohnehin rekonstruierbar ist: Git-Log,
`DASHBOARD.md` ("Als Nächstes" / "Braucht deine Bestätigung" /
"Letzte Aktivität"), `CHANGELOG.md`, PARA-Notizen. Eine Aufgabenliste, die
man auch aus dem Dashboard ablesen könnte, gehört NICHT in die
Handoff-Datei — das ist genau der Fehler, den dieser Skill vermeiden soll.

**Rein gehört** nur, was sonst nirgendwo steht:
- **Learnings**: Erkenntnisse aus dieser Session, die noch nicht in eine
  PARA-Notiz oder Memory destilliert wurden.
- **Fehlannahmen**: wovon ausgegangen wurde und was sich als falsch
  herausstellte, inkl. wie es korrigiert wurde — spart der nächsten Session,
  denselben Fehler nochmal zu machen.
- **Offene Fäden**: unfertige Gedanken/halb getroffene Entscheidungen, die
  noch zu vorläufig für einen Dashboard-Eintrag sind, aber beim
  Weiterdenken helfen.
- **Nächster Schritt**: falls die nächste Session nahtlos weitermachen
  soll, ein bis zwei Sätze, wo genau anzusetzen ist — nicht mehr, sonst
  Dopplung mit Dashboard "Als Nächstes".

Wenn nach ehrlicher Prüfung nichts davon zutrifft: keine Datei erzwingen.
Eine leere/generische Handoff-Datei ist selbst wieder
Kontextfenster-Verschwendung für die nächste Session.

## Wo speichern

`knowledge/_handoff/<YYYY-MM-DD>_<HHmm>_<kurzer-slug>.md` — Zeitstempel +
Slug statt fester Dateiname, weil mehrere Sessions parallel laufen können
(siehe CLAUDE.md Kopfzeile: "Gelten für JEDE Session, auch parallel
laufende"). Kurzes Template:

```markdown
# Handoff <Datum/Zeit> -- <Thema in 3-5 Worten>

## Learnings
- ...

## Fehlannahmen
- ...

## Offene Fäden
- ...

## Nächster Schritt
- ...
```

Abschnitte ohne Inhalt weglassen statt leer stehen zu lassen.

## Beim Start einer neuen Session

`knowledge/_handoff/` auf wartende Dateien prüfen. Pro gefundener Datei:
1. Inhalt berücksichtigen wie jede andere Session-Übergabe.
2. Ist ein Punkt daraus dauerhaft relevant (echte Erkenntnis, offene
   Entscheidung): ins passende Ziel überführen (`DASHBOARD.md`,
   `CHANGELOG.md`, PARA-Notiz, oder Memory nach CLAUDE.md Punkt 7).
3. Datei danach löschen. Nicht anhäufen lassen — ein wachsender
   `_handoff/`-Ordner ist genau die Datenhalde, die das Second Brain laut
   `knowledge/README.md` vermeiden soll (gleiches Prinzip wie bei
   `Clippings/`: roh rein, verarbeitet, dann geleert).
