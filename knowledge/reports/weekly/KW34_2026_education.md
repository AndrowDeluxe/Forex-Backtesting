# Weekly Checkup - Education - KW34/2026

**Zeitraum:** Montag 2026-08-17 bis Sonntag 2026-08-23. Siehe
`KW34_2026_performance.md` für den Hinweis zur untypischen
Ausführungszeit dieses Laufs (Donnerstag 08-27 statt Sonntagabend, erster
Lauf überhaupt) - dieselbe Einschränkung gilt hier.

## 1. Was stand die Woche an / Hauptfokus

Basierend auf `git log --since "2026-08-17" --until "2026-08-24"` (157
Commits gesamt, davon der Großteil automatisierte Scan-/Snapshot-Commits
der laufenden Bots; die inhaltlich relevanten Commits fallen in drei
Schwerpunkte):

- **CLS Practical - Forschungspush**: der genuine Front-End-2Y-Zinsfilter
  (DE02Y/US02Y via TradingView) wurde entwickelt, gegen FRED
  gegengeprüft und adoptiert; die bereits laufende Zins-Risikoskalierung
  wurde von "informativ angezeigt" zu **Standardverhalten** im Bot und im
  Dashboard gemacht; die Funded-Konto-Szenarien wurden mit aktiver
  Skalierung neu kalibriert. Volles Detail siehe Memory:
  `cls_practical_strategy_state`.
- **CTNL Edge (Gold SMC Continuation + Reversal-Kaskade)**: Live-Signal-
  Contract, Paper-Forward-Test, Telegram-Anbindung wurden gebaut, dann
  Phase-6-Robustheit/Regime-Untersuchung durchgeführt, ins Portfolio (EK/FK)
  integriert und schließlich am 08-21 die echte Bridge scharfgeschaltet.
  Cross-Market-Check zeigte, dass die Konfiguration auf G8-Majors nicht
  robust ist (bewusst nicht auf andere Paare übertragen).
- **Portfolio-Konstruktion**: Trade-Overlap-Analyse, Risiko-Optimierung,
  Walk-Forward-Validierung der Gewichte, Krisen-/Regime-Korrelationsanalyse
  sowie eine EK-Schnellkonto-Umstellung auf die 5 FK-Strategien mit eigener
  Risikostufen-Optimierung.
- Kleinere Posten: MTF-EMA-Ribbon-Filter als neuer Strategiebestandteil,
  Gold-ASB-Live-Log-Seite mit Chart-Overlays, zwei Fixes für
  Streamlit-Cloud-Speicherlimit-Abstürze (Lazy-Tab-Rendering).

## 2. Aktive Zeiten

Commit-Verteilung nach Wochentag: Donnerstag (41) und Freitag (45) klar
am aktivsten, Montag (25) und Mittwoch (25) moderat, Dienstag (16)
ruhiger, Wochenende nahezu inaktiv (Sa 2, So 3 - dort laufen praktisch
nur automatisierte Scan-Snapshots). Über den Tag verteilt gibt es
Commits rund um die Uhr (00, 01, 03, 05 Uhr eingeschlossen) - das sind
überwiegend die automatisierten Bot-Snapshot-Commits, nicht echte
Arbeitszeit. Die inhaltlichen Forschungs-/Feature-Commits (siehe Liste
oben) häufen sich eher im späteren Vormittag bis Abend - im Einklang mit
dem bisherigen Bild "meist abends/an ruhigeren Tagen" aus früheren
Beobachtungen, ohne dass hier eine präzisere Aussage möglich wäre.

## 3. Meine Main Erkenntnisse

- **Der Front-End-2Y-Zinsfilter war kein Sackgassen-Thema, sondern hatte
  nur die falsche Datenquelle im Verdacht**: FRED liefert DE/UK/JP/CA/CH/
  AU-Renditen nur monatlich (schon vorher bekannt), aber `tvDatafeed`
  liefert dieselben Serien täglich zurück bis 2014 - eine Lücke in der
  bisherigen Prüfung, keine echte Datenverfügbarkeitslücke. Lehre: "schon
  geprüft und verworfen" nochmal mit einer anderen Quelle prüfen, bevor
  man es endgültig abhakt.
- **Die Risikoskalierung auf Standard zu heben hat einen echten,
  vorher unbemerkten Regelverstoß aufgedeckt**: das bisherige flache
  0,50%-Basisrisiko für das Funded-Challenge-Szenario 1 (max. 7%
  Gesamt-DD) verletzte das 7%-Limit bereits **ohne** die neue Skalierung
  (-7,36% MaxDD) - eine Kalibrierungsdrift durch spätere
  Strategie-Änderungen (09:00-Checkpoint etc.), die nie erneut geprüft
  wurde. Wurde erst durch die Neukalibrierung sichtbar, nicht durch einen
  gezielten Audit. Lehre: Risikoszenarien mit festen Limits müssen nach
  JEDER Strategie-Parameteränderung neu gegen ihre Limits geprüft werden,
  nicht nur einmalig bei Erstellung.
- **MT5-Deployment-Lektionen wurden diese Woche formalisiert**
  (`knowledge/areas/mt5-bot-deployment.md`, neu angelegt): ein
  dediziertes Terminal pro Konto, Kontonummer nach Connect verifizieren,
  Scheduled-Task-Frequenz muss zur Bar-Größe passen. Der dort dokumentierte
  Gold-ASB-Vorfall vom 08-20 (AutoTrading disabled) ist derselbe, der laut
  diesem Report-Lauf am 08-26/08-27 **erneut** aufgetreten ist - die
  Diagnose war richtig, die Behebung steht aber noch aus.
- **Neu für diesen Report-Lauf selbst** (nicht aus Commits, sondern aus der
  Dateninventur für diesen Weekly Checkup): `OU-Modell-MT5-Bridge` ist eine
  voll aktive, dreikontenübergreifende Bot-Familie mit vermutlich echtem
  Kapital (Konto1 TTP, Konto3 Tickmill-"Live"), die bislang in keiner
  Memory-Notiz als Bridge-Ordner auftauchte. Lehre: die "bekannte
  Bridge-Liste" war nicht vollständig - ein einfacher `ls
  C:\Users\andre\*-Bridge` / `*-Bot` reicht nicht, wenn ein Ordner anders
  benannt ist als erwartet; künftige Inventuren sollten das systematisch
  wiederholen, nicht nur die zuletzt bekannte Liste abhaken.

## 4. Verbesserungen

- CTNL Edge: von reiner Forschung zu einer live geschalteten Bridge
  (DRY_RUN False seit 08-21) nach sauberem manuellem und
  Scheduled-Task-Dry-Run-Test.
- CLS Practical: 2Y-Zinsfilter + kombinierte Risikoskalierung produktiv
  im Repo-Code und Dashboard verankert (Bot selbst bleibt vorerst
  DRY_RUN, siehe Performance-Report).
- Funded-Konto-Risikoszenarien korrigiert, sodass sie ihre eigenen
  7%/3%-Limits jetzt tatsächlich einhalten (vorher unbemerkt verletzt,
  siehe oben).
- MT5-Deployment-Wissen aus zwei realen Incidents in eine dauerhafte,
  wiederverwendbare Checkliste überführt (`knowledge/areas/
  mt5-bot-deployment.md`) statt es nur in Memory/Chat-Historie zu lassen.
- Portfolio-Konstruktion um Walk-Forward-Validierung der Gewichte und eine
  Krisen-/Regime-Korrelationsanalyse erweitert - robustere Grundlage für
  künftige Kapitalallokations-Entscheidungen.

## 5. Verschlechterungen / offene Probleme

- **TrendPullback FK1** ist seit 2026-08-19 14:48 Uhr ohne jede
  Logaktivität - stiller Ausfall mitten in der Berichtswoche, bis heute
  (08-27) nicht behoben.
- **TrendPullback FK2** zusätzlich seit 08-22 15:59 Uhr still (außerhalb
  der Berichtswoche, aber zum Zeitpunkt dieses Laufs weiterhin unklar/
  unbeobachtet).
- **Gold-ASB-AutoTrading-Bug erneut aufgetreten** (08-26/08-27) trotz
  Diagnose in derselben Woche, in der er zuerst gefunden wurde (08-20) -
  die Diagnose allein hat das Problem nicht gelöst.
- **Nicht zuordenbarer EURUSD-Trade** auf dem geteilten Gold-ASB/BTC-Konto
  (08-19, -$920) - weder Strategie passt zum Symbol, weder eine Magic
  Number noch ein State-Log-Eintrag erlauben eine automatische Zuordnung.
  Ungelöst.
- Gold ASB und CTNL Edge senden weiterhin echte Orders ohne jeden
  automatisierten Drawdown-/Kill-Switch-Schutz (Detail siehe
  Performance-Report, Abschnitt 2) - das ist keine neue Verschlechterung
  dieser Woche, aber ein bestehendes, unverändertes Risiko, das mit CTNL
  Edges Live-Schaltung diese Woche jetzt für ein zweites Konto real
  relevant wurde.

## 6. Optimierungsmöglichkeiten

- Jedem Bot/Konto eine eigene, feste **Magic Number** geben (aktuell
  überall `0`) - hätte den nicht zuordenbaren EURUSD-Trade dieser Woche
  sofort auflösbar gemacht, statt raten zu müssen.
- Das bei BTC EMA/CLS/OU-Modell/FK1/FK2 bereits vorhandene
  `check_daily_drawdown()`-Muster auf **Gold ASB** und **CTNL Edge**
  portieren, bevor mehr Volumen über diese beiden Konten läuft.
- Eine einfache **Log-Staleness-Überwachung** einführen (z. B. ein
  separater, unabhängig laufender Check, der Alarm schlägt, wenn ein
  Bot-Log während der Handelszeiten N Stunden keine neue Zeile bekommen
  hat) - FK1s achttägiger stiller Ausfall wäre damit am selben Tag
  aufgefallen statt erst in diesem Wochenreport.
- Prüfen, ob `check_total_drawdown()` (7%-Gesamtlimit) bei BTC FK/CLS
  Challenge absichtlich nicht verdrahtet ist oder ob das ein vergessener
  Schritt war - aktuell toter Code.
- Konto3 (Tickmill) im OU-Modell hat ein auffällig lockeres
  20%-Tages-Drawdown-Limit gegenüber 2% bei Konto1/2 (TTP) - einmal
  bewusst gegenprüfen, ob das so gewollt ist.
- Entscheiden, ob `OU-Modell-MT5-Bridge` dauerhaft Teil jedes künftigen
  Weekly/Monthly Checkups sein soll (dieser Report geht davon aus: ja).
