# Weekly Checkup - Education - KW36/2026

**Zeitraum:** Montag 2026-08-31 bis Sonntag 2026-09-06. Siehe
`KW36_2026_performance.md` für den Hinweis, dass dies der erste Report
unter dem neuen Portfolio-Bridge-Reporting-Format ist.

## 1. Was stand die Woche an / Hauptfokus

Basierend auf `git log --since "2026-08-31" --until "2026-09-06"` (die
große Mehrheit der ~450 Commits dieser Woche sind automatisierte
Snapshot-Commits der laufenden Bots/des Bridge-Watchdogs; die inhaltlich
relevanten Commits plus zusätzlich per Datei-Zeitstempel identifizierte,
noch uncommittete Arbeit fallen in fünf Schwerpunkte):

- **Operative Second-Brain-Schicht eingeführt (Montag, kurz nach
  Mitternacht)**: `CLAUDE.md` + `knowledge/DASHBOARD.md` +
  `knowledge/CHANGELOG.md` gingen live - der Rahmen, in dem diese und alle
  folgenden Wochenberichte jetzt entstehen. Direkt im Zuge dessen wurden
  auch zwei echte CTNL-Reversal-Kaskaden-Bugs (EK-Portfolio + Challenge
  Portfolio) auf ein reales 3er-Gleichzeitigkeits-Limit gekappt.
- **Funded-Portfolio-Bridge: 4-Konten-Saga abgeschlossen + Dateninfrastruktur
  neu gebaut (Mittwoch/Donnerstag).** Nach einer fast 24h-Fehlersuche
  verbanden am Mittwoch (09-03) endlich alle 4 echten Broker-Konten
  gleichzeitig (Root Cause: fehlende "DLL-Importe zulassen"-Option + ein
  strukturell defekter Terminal-Ordner). Am selben Tag wurden die 6
  Strategie-Scans entdoppelt (1x/Lauf statt 1x/Konto) und der
  TradingView-Pro-Login entfernt (löste ein seit 2024 offenes
  `tvDatafeed`-Upstream-Problem). Am Donnerstag (09-04) ging der neue
  lokale **Data-Lake-Pilot** live (alle 6 Beine lesen seitdem aus einem
  Parquet-Lake statt live von Dukascopy/TradingView/yfinance), zusammen
  mit einem neuen 5-Minuten-Fast-Trigger für die zeitkritischen Beine
  (`ctnl_continuation`, NY-Open ORB) und einem nachgerüsteten
  CTNL-Standalone-Kill-Switch in allen drei Portfolio-Bots.
- **Zwei echte Order-Bugs auf EK-Portfolio-Bridge gefunden und live
  behoben (Donnerstag)**: ein hängendes NASDAQ-Ticket (fehlendes
  `deviation`-Feld + zu langer Order-Kommentar für Tickmill) und ein
  TP-auf-falscher-Seite-Bug bei US30 - beide bestätigt live gefixt.
- **Edge-Card-Workflow als neuer Second-Brain-Prozess definiert
  (Samstag)** - ein 5-Felder-Schema (Idee/Regel/Mechanismus/Gegenprobe/
  Test) für händisch entwickelte Strategien, verzahnt mit dem bestehenden
  8-Phasen-Backtest-Standardprozess. **Bisher nicht committet** (siehe
  Punkt 4 unten und Performance-Report Punkt 5).
- **Twelve-Data-Ausweichquelle + kritischer Manifest-Bug (heute,
  Sonntag)**: eine reaktive Backup-Datenquelle für den Fall anhaltender
  Dukascopy-Hänger gebaut, dabei einen Concurrency-Bug im Data-Lake-
  Manifest gefunden, der laut eigener Dokumentation zwischenzeitlich alle
  6 Funded-Portfolio-Bridge-Beine lahmgelegt hatte. **Ebenfalls bisher
  nicht committet** - das komplette `data_lake/`-Paket existiert entgegen
  der eigenen Changelog-Notiz nirgends in der Git-Historie, siehe
  Performance-Report Punkt 2.

## 2. Aktive Zeiten

Ungewöhnlich fragmentiertes Muster diese Woche, kein einzelner
"dichtester Tag" wie in KW35: kurze, verteilte Arbeitsblöcke statt einer
langen Session. Commit-Zeitstempel der inhaltlichen (nicht-Snapshot)
Änderungen: **Montag kurz nach Mitternacht** (00:06-00:59, vermutlich
Ausläufer der Sonntagabend-Session der Vorwoche), **Dienstagmittag**
(11:30-14:09), **Mittwochnachmittag/-abend** (15:11 und 21:09-22:46) und
**Donnerstagmorgen** (09:12-09:18). Auffällig: **für Freitag (09-05) und
heute (09-06) existiert kein einziger inhaltlicher Commit**, obwohl an
beiden Tagen nachweislich gearbeitet wurde - `knowledge/areas/
edge-card-workflow.md` hat Zeitstempel Samstag 13:51 Uhr, die neuen
`data_lake/`-Dateien (`twelvedata_source.py`, `manifest.py`, `ingest.py`)
Sonntag ca. 10:41-10:45 Uhr. Diese beiden Arbeitsblöcke sind nur über
Datei-Zeitstempel sichtbar, nicht über Git - passt zum in Punkt 1/
Performance-Report dokumentierten Commit-Rückstand dieser beiden Tage.

## 3. Meine Main Erkenntnisse

- **Eine im Changelog behauptete Eigenschaft ("git-getrackt") ist nicht
  automatisch wahr - auch wenn sie mit voller Überzeugung dokumentiert
  wurde.** Der `data_lake/`-Eintrag vom 09-04 beschreibt das neue Paket
  explizit als committet; tatsächlich zeigt `git log -- data_lake/`
  keinen einzigen Commit. Lehre: Changelog-Aussagen über den
  Commit-Status sind eine Behauptung zum Zeitpunkt des Schreibens, kein
  dauerhafter Fakt - ein Weekly Checkup sollte bei kritischer
  Infrastruktur (insbesondere wenn sie Echtgeld-Bots mit Daten versorgt)
  aktiv gegenprüfen (`git log --oneline -- <pfad>`), statt der eigenen
  vorherigen Dokumentation blind zu vertrauen.
- **Ein einzelner Infrastruktur-Fehler kann wie mehrere unabhängige
  Bein-Fehler aussehen, wenn man nur pro Bein zählt.** Der uniforme
  37-Fehler-Spike am 09-04 auf allen 4 Funded-Portfolio-Bridge-Konten
  gleichzeitig für 4 verschiedene Beine sah zunächst wie vier getrennte
  Probleme aus - passt aber im Muster (exakt gleiche Zahl, exakt gleicher
  Tag wie der Data-Lake-Pilot-Start) sehr gut zu einem einzigen
  gemeinsamen Fehler (der heute gefundene Manifest-Concurrency-Bug).
  Lehre: bei gleichzeitigen Fehlern über mehrere unabhängige Beine/Konten
  hinweg zuerst nach einer gemeinsamen Ursache (geteilte Infrastruktur)
  suchen, statt jedes Bein einzeln zu diagnostizieren.
- **Ein Risikodeckel, der korrekt Signale überspringt, sieht in den
  Logs genauso aus wie ein Bug, der Signale verschluckt - der einzige
  Unterschied ist die Absicht.** Diese Woche haben `risk_cap_notified`-
  Einträge auf EK-Portfolio-Bridge mehrfach ORB-Entries übersprungen
  (09-02/09-03/09-04) - das ist der Risikodeckel bei der Arbeit, keine
  Störung. Für den Weekly Checkup lohnt sich deshalb ein bewusster Blick
  darauf, OB ein Skip beabsichtigt war (Deckel/Signal-Alter), bevor er
  als "Bot hat nicht reagiert" fehlinterpretiert wird.
- **Fortsetzung aus KW34/35**: die bereits mehrfach dokumentierte
  CTNL-Reversal-Fragilität (siehe Memory: `ctnl_reversal_edge_fragility_20260903`)
  zeigte sich diese Woche erneut - 3 von 3 Signalen in Folge liefen im
  FK-Instant-Funding-Paper als Stop-out. Kein neuer Fund, aber eine
  weitere Bestätigung, dass dieses Bein strukturell fragiler ist als der
  Rest des Portfolios.

## 4. Neues Wissen diese Woche (Papers/Ideen)

**6 neue `knowledge/`-PARA-Notizen diese Woche** (alle aktuell noch
uncommittet, siehe Punkt 1 oben und Performance-Report Punkt 5):

- [[edge-card-workflow]] (Samstag 09-05) - neuer 5-Felder-Prozess
  (Idee/Regel/Mechanismus/Gegenprobe/Test) für händisch entwickelte/
  getradete Strategien ohne Paper-Ursprung, ersetzt für diese Fälle die
  Phasen 1-3 des bestehenden 8-Phasen-Backtest-Standardprozesses.
- [[backtest-standard-process]] (Montag 09-01) - die neue
  `knowledge/`-Referenznotiz für den bereits bestehenden 8-Phasen-Prozess
  aus `education_gold_intraday.py`, damit `[[backtest-standard-process]]`
  ein echtes Linkziel hat statt eines toten Wikilinks.
- [[second-brain-methodik]] (laufend seit 09-01, diese Woche mehrfach
  erweitert) - Meta-Wissen über den Aufbau des Second Brain selbst,
  Quelle für die Handoff-Skill-Entscheidung (09-04) und die
  Kontextfenster-Hygiene-Regel.
- [[order-flow-trading]] (Dienstag 09-02) - Destillat zu Order-Flow-/
  diskretionärem Trading-Wissen; bewusst ohne direkten Backtest-Bezug, da
  die Kernsignale (Order Flow, Gamma Exposure) Echtzeitdaten brauchen,
  die im Repo nicht vorliegen.
- [[opening-range-breakout]] (Montag/Dienstag) - externe ORB-Paper,
  abgeglichen mit der bestehenden [[ny-open-orb-sp500]]-Strategie; daraus
  entstand die noch unentschiedene Ideen-Inbox-Idee "Stocks-in-Play
  5-Min-ORB als neue Asset-Klasse" (s.u.).
- [[strategie-backlog-inventar]] (Montag 09-01) - Inventar aktuell
  relevanter Strategien/Filter-Bausteine, Scope bewusst auf live/pausierte
  Bots mit echtem Dashboard-Bezug eingegrenzt statt Vollsweep über alle
  Ordner.

**Ideen-Inbox** (`knowledge/DASHBOARD.md`) - alle 6 aktuell offenen
Einträge kamen diese Woche neu rein, noch keiner davon einsortiert:

- Dashboard jeden Morgen 8 Uhr per Telegram (09-06)
- Periodischer `/doctor`-Check (09-04, zurückgestellt)
- CFDs → echte Futures umstellen, 2 Teilfragen (09-03)
- OU-Modell-Scanner ggf. komplett auf Telegram umstellen (09-02)
- PDFs/Bücher bulk-einbinden über `paper_dropbox/` (09-01)
- TTP/IQ ORB-Exits laufen pro Konto unabhängig auseinander - noch nicht
  bewertet, ob synchronisieren sinnvoll wäre (09-02)
- Stocks-in-Play 5-Min-ORB als neue Asset-Klasse (09-01, siehe
  [[opening-range-breakout]] oben)

**Zusätzlich gefunden, noch nicht verarbeitet**: 12 neue Clippings
(PDFs) seit 2026-09-03 in `knowledge/Clippings/` - siehe
Performance-Report Punkt 3. Themen laut Dateinamen u.a. Edge-Genesis/
-Decay, Risk-Factor-Investing (Kolanovic/JPM), Sektor-Rotation,
"Von Paper zu Strategie"-Leitfaden - noch nicht durch den CODE-Prozess
gelaufen, daher hier nur als Ankündigung, nicht als Erkenntnis.

## 5. Verbesserungen

- Operative Second-Brain-Schicht (`CLAUDE.md`/`DASHBOARD.md`/
  `CHANGELOG.md`) eingeführt - der Rahmen für alles Weitere diese Woche,
  inklusive Nutzer-Feedback nach einer Woche ("Workflow passt gut", siehe
  Memory `dashboard_workflow_positive_feedback_20260906`).
- Funded-Portfolio-Bridge: alle 4 echten Konten verbinden jetzt zuverlässig
  (nach fast 24h Fehlersuche), Scan-Redundanz beseitigt (6 statt 24
  Scans/Zyklus), TradingView-Pro-Login-Fehlerspam behoben.
- Neuer lokaler Data-Lake-Pilot live - entkoppelt Funded-Portfolio-Bridges
  6 Beine von der direkten Dukascopy/TradingView/yfinance-Live-Abhängigkeit;
  5-Minuten-Fast-Trigger für die zwei zeitkritischsten Beine ergänzt.
- CTNL-Standalone-Kill-Switch (Phase-6-Drawdown-Schwelle) in allen drei
  Portfolio-Bots nachgerüstet, nachdem er bei der Konsolidierung verloren
  gegangen war.
- Zwei echte, live bestätigte Order-Bugs auf EK-Portfolio-Bridge behoben
  (hängendes NASDAQ-Ticket, TP-Seiten-Bug bei US30).
- Neuer Edge-Card-Workflow-Prozess für händische Strategien definiert und
  mit dem bestehenden 8-Phasen-Prozess verzahnt.
- Neue Twelve-Data-Ausweichquelle für den Dukascopy-Hänger-Fall gebaut,
  dabei einen echten Concurrency-Bug im Data-Lake-Manifest gefunden und
  behoben.
- 5 Clippings aus der Vorwoche verarbeitet, 3 Claude-Workflow-Videos in
  [[second-brain-methodik]] destilliert, neuer `handoff`-Skill daraus
  abgeleitet.

## 6. Verschlechterungen / offene Probleme

- **Das komplette `data_lake/`-Paket wurde nie committet**, obwohl der
  eigene Changelog es als "git-getrackt" dokumentiert - kritische
  Dateninfrastruktur für 2 Live-Echtgeld-Konten existiert nur lokal.
  Neu diese Woche, siehe Performance-Report Punkt 2.
- **Lokaler `main` seit heute 64 Commits vor / 1 hinter `origin/main`** -
  automatische Bot-Commits scheitern seit heute Vormittag beim Push,
  Snapshots derzeit nur lokal gesichert.
- **`cls_practical`/Dukascopy-Instabilität auf EK-Portfolio-Bridge diese
  Woche ungewöhnlich stark** (51 Fehler Donnerstag, 26 Freitag) - bekannter
  Bug, aber diese Woche deutlich über dem sonstigen Niveau.
- **6 neue `knowledge/`-Notizen + der komplette `data_lake/`-Ordner sind
  uncommittet** - passend zum darüber liegenden Muster fehlender
  Freitags-/Sonntags-Commits (siehe Punkt 2).
- Weiterhin unklar, ob der CTNL-Standalone-Kill-Switch in
  Funded-Portfolio-Bridge produktiv mitläuft (kein sichtbarer State-Key,
  siehe Performance-Report Punkt 2 der Compliance-Tabelle) - keine neue
  Verschlechterung, aber weiterhin offen.

## 7. Optimierungsmöglichkeiten

- **`data_lake/` schnellstmöglich committen** - höchste Priorität dieser
  Woche, da es aktuell die einzige, nicht git-gesicherte Kopie der
  Datengrundlage für zwei Echtgeld-Konten ist.
- Den lokalen/`origin`-Push-Konflikt auflösen (Merge/Pull des einen
  fremden `origin`-Commits), damit automatische Bot-Snapshots wieder auf
  GitHub ankommen - siehe Performance-Report Punkt 1.
- 12 wartende Clippings verarbeiten, bevor der Stapel weiter wächst.
- Verifizieren, ob der CTNL-Standalone-Kill-Switch in
  Funded-Portfolio-Bridge tatsächlich aktiv geprüft wird (z.B. gezielter
  Test mit synthetischem Drawdown), statt nur auf ein reales Trigger-
  Ereignis zu warten.
- Die diese Woche neu entstandene Gewohnheit, an Wochenend-Tagen (Fr/Sa/So)
  ohne Commit zu arbeiten, im Blick behalten - erschwert die Nachverfolgung
  über Git und lässt Arbeit wie hier beschrieben fast unsichtbar werden,
  bis ein Report wie dieser gezielt nach Datei-Zeitstempeln sucht.
