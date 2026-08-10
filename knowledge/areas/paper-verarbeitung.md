# Area: Paper-Verarbeitung

Laufende Verantwortlichkeit ohne Enddatum -- jedes neue Paper (egal ob
automatisiert über `paper_dropbox/` oder manuell im Chat geteilt) durchläuft
denselben Prozess.

**Wer schreibt die Notiz**: Claude, nicht der Nutzer. Der Nutzer teilt ein
Paper (Chat oder `paper_dropbox/`) -- Claude macht den kompletten CODE-Durchlauf
selbstständig und legt/ergänzt die Notiz in `resources/<thema>.md`. Kein
separates Aufschreiben durch den Nutzer nötig.

**Standardablauf pro Paper (ohne Rückfrage, außer bei echten Unklarheiten)**:
1. Capture + Organize: Metadaten erfassen, passende Themendatei finden/anlegen,
   mit verwandten Notizen verlinken.
2. Distill: Kernthese, Modell/Filter destillieren.
3. **Cross-Check**: aktiv prüfen, ob sich daraus ein Filter/Baustein ableiten
   lässt, der auf eine ANDERE bestehende Strategie im Repo anwendbar ist
   (nicht nur die im Paper behandelte) -- das ist der eigentliche Mehrwert
   ggü. reinem Paper-Nacherzählen.
4. Express: wenn mit vorhandenen Daten testbar -> Backtest direkt anstoßen,
   Ergebnis in die Notiz zurückschreiben, Link zu Commit/Streamlit-Seite.
   Wenn nicht testbar (fehlende Daten/Instrument) -> das explizit als Grund
   in der Notiz vermerken, nicht stillschweigend liegen lassen.

**Prozess-Referenz**: siehe `knowledge/README.md` -> CODE, Template unter
`_templates/paper_note.md`.

**Grundregel**: eine Notiz ist erst fertig, wenn Distill + Express ausgefüllt
sind. Rohe Capture-Stubs sind der Anti-Pattern-Fall (Second Brain als
Datenhalde) -- lieber seltener, aber vollständig verarbeiten.

**Aktive Projects, die aus dieser Area gespeist werden**:
- [[gold-ssrn-strategie-auswertung]]
