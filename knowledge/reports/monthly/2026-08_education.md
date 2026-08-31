# Monthly Checkup - Education - August 2026

**Zeitraum:** 2026-08-01 bis 2026-08-31. Siehe `2026-08_performance.md` für
den Hinweis zur Erzeugung dieses Reports zusammen mit KW35.

## 1. Was stand den Monat an / Hauptthemen

Der Monat zerfällt in drei klar erkennbare Phasen:

- **Woche 1-2 (01.-16.08.): Strategie-Entwicklung.** Gold Asian-Range
  Breakout, OU-Modell (S&P 500 + Nasdaq-100), Trend Pullback, CLS
  Practical und BTC EMA9/21 wurden nacheinander gebaut, gegen Out-of-
  Sample-Daten getestet und mit Monte-Carlo-Robustheit geprüft - jeweils
  mit ehrlich dokumentierten negativen Ergebnissen für die meisten
  getesteten Zusatzfilter (COT-Sentiment, Momentum-Thrust, Execution-
  Overlay, Gap-Fade). Am 10.08. wurde das **"Second-Brain"-Prinzip**
  eingeführt (`knowledge/`-Ordner nach PARA+CODE) - die strukturelle
  Grundlage, auf der der Rest des Monats (und dieser Report) aufbaut.
- **Woche 3 (17.-23.08., KW34): erste Live-Gänge.** CTNL Edge ging live
  (20.-21.08.), der Gold-ASB-AutoTrading-Bug wurde gefunden und
  dokumentiert (aber nicht behoben), MT5-Deployment-Lektionen wurden
  formalisiert, Portfolio-Konstruktion um Walk-Forward-Validierung und
  Regime-Korrelationsanalyse erweitert, und die Weekly-Checkup-Automation
  selbst wurde gebaut und lief erstmals (27.08., rückwirkend für KW34).
- **Woche 4 (24.-31.08., KW35): Konsolidierung.** Die vier
  Einzelstrategie-Bots wurden pausiert, `EK-Portfolio-Bridge` (8 Beine)
  gebaut und binnen zwei Tagen mit echtem Geld live geschaltet, FK
  Instant Funding bekam drei Bugfixes und eine Monte-Carlo-Gewichts-
  Optimierung, NY-Open ORB wurde zur "Fertigen Strategie" befördert, und
  ein sehr dichter Forschungstag (25.08.) schloss die letzten offenen
  Phase-6-Lücken für David-V2, Gold-Silber-Divergenz, Haupt-Bot, OU-Modell,
  BTC EMA9/21 und Gold-Bitcoin.

## 2. Aktive Zeiten

Über den ganzen Monat gesehen konzentriert sich die inhaltliche (nicht
automatisierte) Arbeit klar auf **späte Nachmittage/Abende sowie
gelegentliche lange Nachtsessions** (z. B. 05.08. und 25.08., beides Tage
mit ununterbrochenen Commit-Ketten bis weit nach Mitternacht). Wochenenden
waren in der ersten Monatshälfte durchaus aktiv (09.08., 15.-16.08. -
mehrere neue Strategien entstanden an Wochenenden), in KW34 dagegen
praktisch inaktiv, und in KW35 wieder aktiv (29.08., Samstag). Insgesamt
kein festes Wochenmuster erkennbar, aber ein klares Tagesmuster:
Abend-/Nachtarbeit dominiert, Vormittage sind fast ausschließlich
automatisierten Bot-Läufen vorbehalten.

## 3. Meine Main Erkenntnisse (die 3 größten Learnings des Monats)

1. **Ein wiederholbarer Standardprozess zahlt sich messbar aus.** Die
   Einführung des 8-Phasen-Prozesses und des `knowledge/`-Second-Brain
   Mitte des Monats war zunächst reine Struktur-Arbeit ohne direkten
   Performance-Effekt - aber bis Monatsende hatten praktisch alle
   Kernstrategien (Haupt-Bot, OU-Modell, BTC EMA9/21, Gold-Bitcoin, David-
   V2, Gold-Silber-Divergenz) ihre Phase-6-Robustheitslücken geschlossen,
   und es existieren jetzt dauerhafte Referenzdokumente statt nur
   Chat-Historie. Der Wert eines Prozesses zeigt sich nicht in der Woche,
   in der er eingeführt wird, sondern darin, wie viel er einige Wochen
   später bereits automatisch abgedeckt hat.
2. **Diagnose ist nicht Behebung.** Der Gold-ASB-AutoTrading-Bug wurde am
   20.08. korrekt gefunden, sauber dokumentiert und mit einer konkreten
   Lösung (dediziertes Terminal) versehen - trat aber danach noch
   mindestens viermal auf, ohne dass die Lösung umgesetzt wurde. Über den
   ganzen Monat betrachtet ist das der auffälligste Fall, in dem ein
   "erledigt (dokumentiert)"-Status fälschlich als "erledigt (behoben)"
   gelesen werden könnte. Lehre: offene Maßnahmen aus Incident-Dokumenten
   brauchen eine explizite Nachverfolgung, nicht nur eine einmalige
   Erwähnung.
3. **Portfolio-Konsolidierung ist am Monatsende von der Theorie in die
   Praxis übergegangen - aber nicht auf einer sauberen Startlinie.** Der
   Backtest-Vergleich (Portfolio Max-DD -2,27% vs. -4,8% bis -9,26% je
   Einzelstrategie, siehe Performance-Report Abschnitt 5) war die
   Begründung für die Konsolidierung; `EK-Portfolio-Bridge` übernahm dafür
   aber bestehende Challenge-Konten samt deren laufender Positionen und
   Historie (z. B. das ehemalige OU-Modell-Tickmill-Konto), statt mit
   frischem Kapital zu starten. Künftige Performance-Auswertungen dieses
   Kontos müssen alte und neue Bot-Logik per Magic Number trennen, sonst
   wird die Übernahme fälschlich der neuen Strategie zugerechnet.

## 4. Verbesserungen

- **Second-Brain-Struktur** (`knowledge/`, PARA+CODE) eingeführt - seitdem
  tragender Unterbau für Strategie-Dokumentation und die Weekly/Monthly
  Checkups selbst.
- **8-Phasen-Standardprozess vollständig durchlaufen** für Haupt-Bot,
  OU-Modell, BTC EMA9/21, Gold-Bitcoin, David-V2, Gold-Silber-Divergenz -
  alle offenen Phase-6-Lücken (Monte-Carlo, Kosten-Sensitivität) diesen
  Monat geschlossen.
- **Fünf Bots gingen diesen Monat live** (CTNL Edge, Gold ASB, BTC EMA
  Cross, und am Monatsende konsolidiert `EK-Portfolio-Bridge`) - vom
  Backtest zur echten Ausführung.
- **Weekly/Monthly-Checkup-Automation gebaut und zweimal erfolgreich
  gelaufen** (KW34, KW35) - erstmals ein systematischer, wiederkehrender
  Blick auf Compliance und Performance über den gesamten Bot-Fleet.
- **NY-Open ORB von Forschung zu "Fertiger Strategie"** befördert,
  inklusive Partial-Exit-Standardkonfiguration.
- **FK Instant Funding**: drei echte Bugs behoben, Gewichte Monte-Carlo-
  optimiert, Wochenend-/Spread-Stunden-Sperre eingeführt (auch auf
  EK-Portfolio und CTNL-Edge-FK-Paper ausgeweitet).
- **MT5-Deployment- und Paper-Bot-Architektur-Wissen dauerhaft
  dokumentiert** (`knowledge/areas/mt5-bot-deployment.md`,
  `knowledge/areas/paper-bot-architecture.md`).
- **Streamlit-Cloud-Speicherlimit-Ursachen app-weit behoben.**

## 5. Verschlechterungen / offene Probleme

- **Gold-ASB-AutoTrading-Bug**: mindestens 5 Wiederholungen im August,
  den ganzen Monat unbehoben trotz korrekter Diagnose am 20.08.
- **Nicht zuordenbarer EURUSD-Trade / USDJPY-Restposition** auf Konto
  15514: seit dem 19.08. offen, floating-Verlust wächst weiter
  (-$199,97 zum Monatsende).
- **TrendPullback FK1/FK2**: seit 19./22.08. ohne jede Log-Aktivität, den
  ganzen Rest des Monats nicht wiederhergestellt, jetzt zusätzlich durch
  `EK-Portfolio-Bridge`s eigenes Trend-Pullback-Bein fachlich redundant.
- **OU-Modell Konto1 (real)**: -$2.713,44 für den Monat, davon der
  Großteil in einer einzigen schlechten Woche (KW33) - Trend zwar
  zuletzt wieder besser, aber der Monat insgesamt klar negativ auf dem
  einzigen durchgehend real gehandelten OU-Modell-Konto.
- **CTNL Edge FK: zwei neue unbehandelte Dukascopy-Exceptions** kurz vor
  der Konsolidierungspause (27./28.08.), nicht root-caused.
- **BTC-EMA-Cross-Bridge und CTNL-Edge-FK-Paper am 31.08. ohne
  dokumentierte Begründung deaktiviert** - Klärung steht zum
  Monatsende noch aus.
- **Uncommittete lokale Änderungen** in zwei Paper-Bot-Dateien zum
  Monatsende vorgefunden (siehe KW35-Report Punkt 8).

## 6. Optimierungsmöglichkeiten für September

- Gold-ASB-Terminal-Fix **tatsächlich umsetzen** - die am häufigsten
  wiederholte, nie abgeschlossene Empfehlung des Monats.
- Jedem Bot/Konto eine eigene, feste **Magic Number** geben - würde sowohl
  die USDJPY-Zuordnung als auch die Trennung von alter/neuer Logik auf
  übernommenen Konten (EK-Portfolio/Tickmill) sofort lösen.
- Die zwei neuen `dukascopy_python`-Exceptions bei CTNL Edge root-causen,
  bevor der Bot wieder aktiviert wird - und gegen alle anderen Bots
  prüfen, die dieselbe Bibliothek nutzen.
- TrendPullback FK1/FK2 formal stilllegen statt als unklaren Ausfall
  weiterzuführen.
- Klären, warum OU-Modell Konto1 (real) und Konto2 (Demo) trotz
  vermeintlich identischer Strategie so unterschiedlich abschneiden
  (-$2.713 vs. +$290 im August) - Konfigurationsunterschied oder
  reiner Zufall bei unterschiedlichen Signal-Teilmengen?
- Vor einem Live-Gang von `Funded-Portfolio-Bridge` die Kontoüberschneidung
  mit pausierten Bots (CTNL-Edge-MT5-Bridge, OU-Modell Konto2) auflösen.
- September als erster echter "voller Monat" von `EK-Portfolio-Bridge`
  beobachten - erste belastbare Aussage darüber, ob sich die im Backtest
  gezeigte Drawdown-Reduktion (Abschnitt 5 im Performance-Report) real
  bestätigt.
