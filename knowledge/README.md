# Knowledge (Second-Brain-Prinzip, kein separates Tool)

Ablage im Repo statt in einer eigenen App -- git-versioniert, durchsuchbar,
verknüpfbar per Markdown-Link. Struktur nach PARA, Verarbeitung einzelner
Notizen nach CODE (siehe `_templates/paper_note.md`).

**Für "was läuft gerade / was ist passiert / was steht an" nicht hier
suchen** -- das ist die operative Ebene, dafür gibt es
[`DASHBOARD.md`](DASHBOARD.md) (Status, offene Aufgaben, Punkte die deine
Bestätigung brauchen) und [`CHANGELOG.md`](CHANGELOG.md) (vollständiges Log
aller relevanten Änderungen). Diese README/PARA-Struktur bleibt reines
Research-/Strategie-Wissen.

## Struktur (PARA)

- **projects/** -- aktive Arbeit mit klarem Ziel/Ende (z.B. "Gold-SSRN-Strategie
  auswerten"). Wenn abgeschlossen: nach `archive/` verschieben.
- **areas/** -- laufende Verantwortlichkeiten ohne Enddatum (z.B.
  "Paper-Verarbeitung", "Risk-Management-Standards").
- **resources/** -- destilliertes Referenzwissen nach Thema (z.B.
  `resources/gold.md`, `resources/execution-microstructure.md`) --
  hier landen die Kernaussagen aus Papers, verknüpft mit den Strategie-
  Bausteinen/Backtests, die daraus entstanden sind.
- **archive/** -- abgeschlossene Projects/Areas, nicht mehr aktiv gepflegt,
  aber durchsuchbar.

## Verhältnis zu bestehender Infrastruktur

- `paper_dropbox/` + `paper_research/` = automatisierte Ingestion (PDF rein,
  Extraktion + Auto-Backtest raus). Bleibt unverändert.
- `knowledge/` = die Destillations- und Verknüpfungsebene *darüber* --
  unabhängig davon, ob ein Paper automatisiert oder manuell im Chat
  besprochen wurde (wie bisher beim Gold-SSRN-Thread).
- Streamlit-Seite "Erkenntnisse" bleibt die Präsentationsebene für Nutzer;
  `knowledge/` ist die Rohnotiz-Ebene dahinter -- nicht 1:1 dasselbe.

## Prozess für ein neues Paper (CODE)

1. **Capture**: `_templates/paper_note.md` kopieren nach `resources/<thema>.md`
   (oder an bestehende Themendatei anhängen), Metadaten sofort eintragen.
2. **Organize**: Thema/Tag zuordnen, Verlinkung zu verwandten Notizen/Projects.
3. **Distill**: Kernthese in 1-2 Sätzen, wichtigste Formel/Modell/Filter --
   nur was potenziell integrierbar ist, nicht das ganze Paper nacherzählen.
4. **Express**: konkreter nächster Schritt (Backtest ja/nein + warum) und,
   sobald getestet, Link zum Ergebnis (Commit/Streamlit-Seite).

Keine Notiz bleibt bei Schritt 1 stehen -- unverdichtete Rohnotizen sind
das Anti-Pattern, das ein Second Brain zur Datenhalde macht.
