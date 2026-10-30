# Handoff 28.10.2026 19:45 -- Makro-Agent Phase 2 starten

## Learnings
- **Unteragenten und Nutzungslimit:** Mehr als ~6 parallele Sonnet-Agenten
  mit großen Leseaufträgen (je 200–500k Token) liefen zweimal komplett ins
  Claude-Session-Limit. Bewährt haben sich 3–6 Agenten gleichzeitig und
  die Pflicht „nach jeder Datei sofort speichern, vorhandene überspringen“.
  So kostet ein Abbruch nichts.
- **Agenten sind selten fehlerfrei**, selbst bei Zitatpflicht. Typische
  Fehler, die vorkamen: eine Richtung „angenommen“ (6165), eine vom Nutzer
  verworfene Idee wieder aufgenommen (3332 USDJPY long), Quervergleich mit
  späteren Reports (1441). Nach jedem Agentenlauf die Rückmeldung lesen
  und gegen Nutzerurteile prüfen.
- **Bild-PDFs:** pypdf liest bei vielen Gen-2-Reports viel weniger als
  pymupdf. Erste Seiten sind oft Bilder. Immer pymupdf nutzen und
  Bildseiten per Render prüfen.
- **Telegram-Import:** große Videos blockieren `fusion_lab.ingest.telegram`.
  Seit 14.10. gibt es `--skip-video`. Ein zweiter, fremder Importprozess
  kann die Session-Datei sperren; vorher `tasklist` prüfen.

## Fehlannahmen
- Die Status-Definition „vorbereitet = technische Bestätigung fehlt“ war
  falsch. Nutzerdefinition: aktiv / event (Ereignis entscheidet) / watch /
  bias / inaktiv / hedge. Steht in `fusion_lab/macro_reports/EXTRACTION.md`.
- Richtung je Regime und Asset: 250 Parameter wurden ohne Prüfung der
  Punktezahl getestet. Künftig VOR jedem Lauf die Zahl der auf den Daten
  gewählten Punkte gegen den Richtwert 9 prüfen und im Chat nennen.

## Offene Fäden
- Report 5305: drei Event-Ideen passen laut Prüfer nicht zum Report. Sie
  laufen nicht im Richtungstest, sollten aber bei Gelegenheit angesehen
  werden.
- Reports ab 08.10.2026 (6641, 6673, 6693, 6694, 6749, 6759, 6760, …) sind
  noch nicht extrahiert. Gebraucht für den Forward-Zeitraum
  (Öffnung 31.01.2027) und als Wirkketten-Quelle. Deep Dives
  (6694, 6760) enthalten Ketten im Vier-Felder-Format.
- Die 13 Notion-Lernkarten (`fusion_lab/notion/makro_education.py`) haben
  noch keine Karte zu Positionierung/F-Gate und Zinspricing-Regeln aus SMT
  21.10. Beim nächsten Notion-Update ergänzen.
- MT5-Demo-Konto für Schritt 6 muss der Nutzer noch bereitstellen.

## Nächster Schritt
- Freigegebener Plan: `C:\Users\andre\.claude\plans\eventual-rolling-heron.md`
  (Phase 2). Mit **Schritt 1 = Datenschicht A1** beginnen, in
  `fusion_lab/macro_data/`: FRED/OECD je G8-Land, Forex-Factory-Wochenfeed
  (Konsens) täglich archivieren, CFTC TFF (Muster
  `asian_range_breakout/cot.py`), Fed-Funds-Futures, Märkte. Danach
  Daten-Task wie `G8-Notion-Sync`. Der Nutzer erwartet das Fact Sheet aus
  Schritt 2 zur Prüfung.
