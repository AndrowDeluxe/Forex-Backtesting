# Weekly Checkup - Education - KW35/2026

**Zeitraum:** Montag 2026-08-24 bis Sonntag 2026-08-30. Siehe
`KW35_2026_performance.md` für den Hinweis zur untypischen Ausführungszeit
dieses Laufs (Nacht Mo/Di 08-31→09-01 statt Sonntagabend) und dazu, dass
dieser Lauf den August-Monatsreport gleich mit erzeugt.

## 1. Was stand die Woche an / Hauptfokus

Basierend auf `git log --since "2026-08-23" --until "2026-09-01"` (die
große Mehrheit der Commits sind automatisierte Scan-/Snapshot-Commits der
laufenden Bots; die inhaltlich relevanten Commits fallen in vier
Schwerpunkte):

- **Portfolio-Konsolidierung wird real**: die vier Einzelstrategie-Bots
  (Gold ASB, CLS Practical, CTNL Edge, OU-Modell) wurden Mittwoch pausiert,
  Donnerstag kam `EK-Portfolio-Bridge` (8 Beine) als Paper-Bot dazu, und
  Samstag ging sie mit echtem Geld auf dem ehemaligen OU-Modell-Tickmill-
  Konto live. Details siehe Performance-Report Abschnitt 1. Dies ist die
  Umsetzung dessen, was bereits in [[portfolio_consolidation_pending]] als
  "kommt noch" vermerkt war.
- **FK Instant Funding**: Gewichts-Optimierung der 6 Beine (Monte-Carlo-
  geprüft), NY-Open ORB als 6. Strategie integriert, drei echte Bugs
  behoben (Kontostart-Bug, EOD-Trailing-DD-Floor-Bug, `scan_errors_today`
  auf echten lokalen Kalendertag umgestellt), eigenes Telegram-Layout mit
  gebündelten Scan-Nachrichten. Bleibt weiterhin `DRY_RUN=True`.
- **NY-Open ORB**: Partial-Exit-Standardkonfiguration festgelegt, $100k-
  Kontosimulation ergänzt, von "in Arbeit" zu "Fertige Strategien"
  verschoben - der alte, separate ORB-Forward-Test-Live-Log wurde entfernt.
- **Strategie-Forschung (v. a. Dienstag 08-25, sehr dichter Tag)**:
  David-V2 rekonstruiert und in Phase 5 erschöpfend getestet (weiterhin
  nicht empfohlen), Gold-Silber-Divergenz rekonstruiert/optimiert
  (Phase 5+6, Cache-Key-Bug im Monte-Carlo-Vergleich gefunden und behoben),
  Haupt-Bot: verbleibende Bausteine (Kalman-Filter, MTF-EMA-Ribbon,
  Zentralbank-Event-Filter) getestet, keiner übernommen, dafür die letzte
  Phase-6-Monte-Carlo-Lücke geschlossen; außerdem Kosten-Sensitivitäts-
  Nachholtermine für OU-Modell, BTC EMA9/21 und Gold-Bitcoin Dual Momentum
  (alle drei hatten laut Standard-Prozess noch eine offene Phase-6-Lücke).
- **Kleinere Posten**: Streamlit-Cloud-Speicherlimit-Fixes app-weit (voller
  `app_pages/`-Audit, nicht nur Einzelfälle), neue Standardprozess-
  Dokumentation für MT5-Bridges und Paper-Portfolio-Bots
  (`knowledge/areas/paper-bot-architecture.md`), der erste Weekly-Checkup-
  Lauf überhaupt für KW34 (08-27).

## 2. Aktive Zeiten

Der mit Abstand dichteste Tag war **Dienstag 08-25** - eine lange
Forschungssession mit Commits von 02:08 Uhr bis 23:21 Uhr, Schwerpunkt
spätabends (21:29-23:21 Uhr: vier Strategie-Rekonstruktionen kurz
hintereinander). Der zweite Schwerpunkt liegt auf **Donnerstag 08-27 bis
Samstag 08-29** - EK-Portfolio-Bridge-Bau und -Live-Gang, FK-Instant-
Funding-Fixes, jeweils mit Commits bis spät in den Abend (22-23 Uhr).
**Bemerkenswert gegenüber KW34**: dort war das Wochenende praktisch
inaktiv ("nur automatisierte Snapshots"); diese Woche gab es am **Samstag
08-29** echte Feature-Arbeit (Gewichts-Optimierung, Wochenend-Sperre,
Telegram-Layout) - ein Bruch mit dem bisherigen Muster reiner
Wochentagsarbeit. Insgesamt bleibt das Bild "meist abends" bestehen, wird
aber diese Woche um "gelegentlich auch samstags" ergänzt.

## 3. Meine Main Erkenntnisse

- **Die in der Memory angekündigte Portfolio-Konsolidierung ist diese
  Woche tatsächlich eingetreten, fast genau wie vorhergesagt.**
  [[portfolio_consolidation_pending]] (27.08.) sagte voraus, dass Telegram/
  Reporting irgendwann auf Portfolio-Ebene umgestellt werden, sobald die
  konsolidierten Portfolios live gehen - das ist mit `EK-Portfolio-Bridge`
  jetzt eingetreten, innerhalb von zwei Tagen (Paper 08-27 → Live 08-29).
  Lehre: solche "wird noch passieren"-Notizen sollten bei jedem Weekly
  Checkup aktiv gegengeprüft werden, nicht nur bei Bedarf - sie verfallen
  schnell.
- **Konsolidierte Bots übernehmen bestehende Konten, statt neue zu
  eröffnen.** `EK-Portfolio-Bridge` handelt auf demselben Tickmill-Konto,
  das vorher OU-Modells Konto3 war. Das bedeutet: die Handelshistorie
  dieses Kontos ist jetzt ein Gemisch aus zwei verschiedenen Bot-
  Generationen (alte OU-Modell-Logik bis 08-27, neue EK-Portfolio-Logik ab
  08-31) - beim Lesen künftiger MT5-Historien auf diesem Konto muss die
  Magic Number (0 = alt/"OU-Modell auto", 990011 = neu/"EK-ou_modell
  auto") zur Unterscheidung herangezogen werden, sonst wirkt es wie
  inkonsistentes Verhalten eines einzigen Bots.
- **Ein einmal korrekt diagnostizierter Bug ist kein behobener Bug.** Der
  Gold-ASB-AutoTrading-Bug wurde erstmals am 08-20 gefunden und in
  `knowledge/areas/mt5-bot-deployment.md` sauber dokumentiert - trat aber
  seitdem viermal erneut auf (zuletzt 08-26/08-27), ohne dass die
  empfohlene Behebung (dediziertes Terminal) tatsächlich umgesetzt wurde.
  Eine Diagnose, die Woche für Woche wiederholt wird, ohne dass sich der
  Status ändert, sollte zu einer expliziten Entscheidung führen (jetzt
  beheben oder bewusst akzeptieren), statt stillschweigend erneut notiert
  zu werden.
- **Drittanbieter-Datenanbindungen sind ein geteiltes Risiko über mehrere
  Bots hinweg.** CLS Practicals frühere Datumsgrenze-Bug und CTNL Edges
  diese Woche neu aufgetretene `TypeError`/`KeyError` stecken beide in
  derselben `dukascopy_python`-Bibliothek. Ein Fix oder eine Auffälligkeit
  in einem Bot ist ein Hinweis darauf, dieselbe Stelle bei allen anderen
  Bots zu prüfen, die dieselbe Bibliothek nutzen, nicht nur im
  betroffenen Bot selbst.

## 4. Verbesserungen

- `EK-Portfolio-Bridge` gebaut und binnen zwei Tagen live geschaltet (8
  Beine, echtes Geld) - der bislang größte konkrete Schritt der
  Portfolio-Konsolidierung.
- FK Instant Funding: drei echte Bugs behoben (Kontostart, EOD-Trailing-
  DD-Floor, Kalendertag-Logik), Gewichte Monte-Carlo-optimiert, NY-Open
  ORB als 6. Bein integriert.
- Wochenend-/Spread-Stunden-Sperre auf EK-Portfolio, CTNL-Edge-FK-Paper und
  FK Instant Funding ausgeweitet - reduziert das Risiko von Ausführungen
  in Zeiten mit strukturell weiten Spreads/geringer Liquidität.
- NY-Open ORB von "in Arbeit" zu "Fertige Strategien" befördert, inklusive
  Partial-Exit-Standardkonfiguration und $100k-Kontosimulation.
- Gold-Silber-Divergenz rekonstruiert, optimiert (Phase 5+6), Cache-Key-
  Bug im Monte-Carlo-Vergleich gefunden und behoben.
- Letzte offene Phase-6-Lücken (Monte-Carlo-Bootstrap, Kosten-
  Sensitivität) für Haupt-Bot, OU-Modell, BTC EMA9/21 und Gold-Bitcoin
  nachgeholt - der 8-Phasen-Standardprozess ist damit für diese Strategien
  jetzt vollständig durchlaufen.
- Standardprozess-Dokumentation für MT5-Bridges und Paper-Portfolio-Bots
  geschrieben (`knowledge/areas/paper-bot-architecture.md`) - überführt
  Wissen aus Chat/Memory in eine dauerhafte Referenz.
- Streamlit-Cloud-Speicherlimit-Ursachen app-weit behoben (voller
  `app_pages/`-Audit statt Einzelfall-Fixes).

## 5. Verschlechterungen / offene Probleme

- **Gold-ASB-AutoTrading-Bug** erneut zweimal aufgetreten (08-26, 08-27) -
  vierte/fünfte Wiederholung seit Erstauftreten, weiterhin unbehoben.
- **CTNL Edge FK: zwei neue unbehandelte Exceptions** in der Dukascopy-
  Anbindung (08-27/08-28), nicht root-caused.
- **Unzugeordnete USDJPY-Position auf Konto 15514** verschlechtert sich
  weiter (jetzt -$199,97 floating) - dritte Woche in Folge ungelöst.
- **TrendPullback FK1/FK2** weiterhin ohne jede Log-Aktivität, jetzt
  zusätzlich fachlich redundant (durch `EK-Portfolio-Bridge`s eigenes
  `trend_pullback`-Bein), aber formal nicht stillgelegt.
- **BTC-EMA-Cross-Bridge/-Scan und CTNL-Edge-FK-Paper wurden am 08-31 ohne
  dokumentierte Begründung deaktiviert** - vermutlich Teil der
  Konsolidierung, aber nicht bestätigt; BTC EMA verwaltet echtes Geld,
  daher besonders klärungsbedürftig.
- **Uncommittete lokale Änderungen** in `challenge_portfolio/paper_bot.py`
  und `ek_portfolio/paper_bot.py` zum Ausführungszeitpunkt dieses Reports
  vorgefunden - nicht bewertet, nur zur Kenntnisnahme.

## 6. Optimierungsmöglichkeiten

- Jedem Bot/Konto endlich eine eigene, feste **Magic Number** geben
  (dritte Woche in Folge empfohlen) - würde sowohl den USDJPY-Fall als
  auch die künftige Unterscheidung von alter/neuer Logik auf übernommenen
  Konten (siehe Erkenntnis 2 oben) sofort lösen.
- **Gold-ASB-Terminal-Fix tatsächlich umsetzen** statt erneut nur zu
  dokumentieren - vierte Wiederholung desselben Bugs ist ein klares
  Signal, dass die Diagnose allein nicht reicht.
- Die zwei neuen `dukascopy_python`-Exceptions bei CTNL Edge root-causen
  und **gegen alle anderen Bots prüfen, die dieselbe Bibliothek nutzen**
  (CLS Practical, ggf. weitere), bevor CTNL Edge wieder aktiviert wird.
- TrendPullback FK1/FK2 formal stilllegen (Task/Prozess sauber beenden)
  statt als unklaren "stillen Ausfall" weiterzuführen.
- Kurze Memory-Notiz nachtragen, warum BTC-EMA-Cross-Bridge und
  CTNL-Edge-FK-Paper am 08-31 deaktiviert wurden, damit der nächste
  Weekly-Checkup-Lauf das nicht erneut als offene Frage aufführen muss.
- Vor einem Live-Gang von `Funded-Portfolio-Bridge` die Kontoüberschneidung
  mit den pausierten Bots (CTNL-Edge-MT5-Bridge, OU-Modell Konto2) bewusst
  auflösen (siehe Performance-Report Punkt 9).
