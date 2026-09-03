# Weekly Checkup - Performance - KW35/2026

**Zeitraum:** Montag 2026-08-24 bis Sonntag 2026-08-30.

> **Hinweis zur Ausführung dieses Reports:** Dieser Lauf fand tatsächlich in
> der Nacht Montag/Dienstag 2026-08-31→09-01 statt, nicht wie vorgesehen am
> Sonntagabend (die geplante Wochenkadenz) - ein verspäteter/nachgeholter
> Task-Scheduler-Lauf, derselbe Verzug wie beim allerersten Lauf (KW34).
> Die vollständig abgeschlossene Mo-So-Woche zum Ausführungszeitpunkt ist
> KW35 (08-24 bis 08-30) - genau die Woche, die der KW34-Report bereits als
> "nächster Lauf" angekündigt hatte. Da Sonntag 08-30 der letzte Sonntag im
> August war (08-30 + 7 Tage = 09-06, also September), greift diesmal **der
> Monats-Trigger** - die August-Monatsreports werden zusammen mit diesem
> Lauf erzeugt (`knowledge/reports/monthly/2026-08_*.md`).
>
> Wichtig: Während der Datensammlung für diesen Report (in der Nacht zum
> 09-01) liefen mehrere der unten beschriebenen Bots **weiter live** und
> haben den Repo-Zustand aktiv verändert (automatische Snapshot-Commits).
> Einige der unten unter Punkt 5 genannten Beobachtungen (BTC-EMA-Cross- und
> CTNL-Edge-FK-Paper-Deaktivierung, EK-Portfolio-Bridges erster echter
> Trade) fallen exakt auf den 2026-08-31 - technisch schon KW36, aber zu
> aktuell und zu relevant, um sie bis zum nächsten Lauf liegen zu lassen.
> Sie sind entsprechend gekennzeichnet.

## 1. Wochenkontext

Diese Woche war die Woche, in der die **Portfolio-Konsolidierung** (seit
Memory `portfolio_consolidation_pending` angekündigt) sichtbar wurde:

- **Mittwoch 08-27**: die vier Einzelstrategie-Bots **Gold ASB, CLS
  Practical, CTNL Edge und OU-Modell** wurden per `Disable-ScheduledTask`
  pausiert (reversibel, nichts gelöscht) - Teil des geplanten Umzugs auf
  konsolidierte Portfolios. BTC EMA Cross war bewusst **nicht** in dieser
  Liste. Details in Memory `individual_strategy_bots_stopped_20260827`. In der
  Praxis liefen die zugehörigen Scheduled Tasks noch bis Donnerstagmittag
  08-28 nach (letzte "Gold ASB Scan"/"CLS Practical Scan"-Commits um
  08-28 12:35-13:00 Uhr), dann Stille - vermutlich ein bereits gestarteter
  letzter Lauf, kein Fehler.
- **Donnerstag 08-27, 23:29 Uhr**: `EK-Portfolio-Bridge` kommt neu dazu -
  ein 8-Beine-Paper-Forward-Test-Bot (Gold ASB, CLS Practical, CTNL Edge,
  BTC EMA, Trend Pullback, Gold-Silber-Divergenz, NY-Open ORB, OU-Modell),
  siehe `knowledge/areas/paper-bot-architecture.md`.
- **Samstag 08-29**: `EK-Portfolio-Bridge` wird auf **`DRY_RUN=False`**
  umgestellt (expliziter User-Auftrag) - echtes Geld auf dem realen
  Tickmill-Konto (Login 55918977, **demselben Konto**, das bis 08-27 als
  OU-Modells "Konto3" lief und dann aus dessen Config entfernt wurde, siehe
  Memory: `ou_modell_tickmill_removed_20260827`). Gleichzeitig wird eine
  Wochenend-/Spread-Stunden-Sperre für EK-Portfolio, CTNL-Edge-FK-Paper und
  FK Instant Funding eingeführt (sichtbar an den Log-Pausen Sa-Nacht/So).
  Siehe Memory: `live_money_bridges_status_20260829`.
- **FK Instant Funding**: Gewichts-Optimierung der 6 Beine (Monte-Carlo-
  geprüft, 08-29), NY-Open ORB als 6. Strategie integriert (08-27), sowie
  mehrere echte Bugfixes (Kontostart-Bug, EOD-Trailing-DD-Floor-Bug,
  `scan_errors_today` auf lokalen Kalendertag umgestellt am 08-31) - bleibt
  aber die ganze Woche `DRY_RUN=True`, siehe Memory: `fk_instant_funding_scaling_plan`.
- **Funded-Portfolio-Bridge** (`challenge_portfolio/` extern, TTP + IQ
  Markets/"I Capital"): reale Order-Ausführung wurde implementiert und
  Ende-zu-Ende gegen die echten Konten getestet, bleibt aber `DRY_RUN=True`
  - siehe Memory: `challenge_portfolio_ttp_icapital`.
- **Randnotiz, außerhalb des Berichtszeitraums, aber aktuell**: Am
  **2026-08-31** (heute/gestern, KW36) wurden die Scheduled Tasks
  `BTC-EMA-Cross-Bridge`, `BTC-EMA-Cross-Scan` und `CTNL-Edge-FK-Paper`
  deaktiviert, und `EK-Portfolio-Bridge` platzierte um 16:36:01 Uhr ihren
  **ersten echten Trade** (Symbol D, OU-Modell-Bein, Magic 990011) - der
  erste reale Fill der neuen konsolidierten Bridge überhaupt. Das passt
  inhaltlich zur Konsolidierung (BTC EMA und CTNL Edge sind beide bereits
  Beine in `EK-Portfolio-Bridge`), ist aber **nicht** durch eine
  Memory-Notiz oder einen Commit bestätigt - siehe Punkt 5.

Aktive Bots/Legs mit echtem Geld während KW35 (vor der Mittwochs-Pause):
Gold ASB, BTC EMA Cross, CTNL Edge FK, OU-Modell (3 Konten). Ab Ende der
Woche: EK-Portfolio-Bridge (Tickmill). Weiterhin reiner Papierbetrieb:
CLS Practical, FK Instant Funding (echte MT5-Bridge), Funded-Portfolio-
Bridge, sowie die Repo-internen Paper-Diagnosen.

## 2. Risk-Management-Compliance

**Kein bestätigter Drawdown-/Kill-Switch-Trigger auf einem echten Konto
diese Woche.** Die strukturellen Lücken aus KW34 bestehen unverändert:

| Bot/Konto | Mechanismus | Diese Woche geprüft |
|---|---|---|
| OU-Modell (3 Konten) | `check_daily_drawdown()` pro Konto | Kein Trigger, alle Logs unauffällig. Konto3/Tickmill trug bis zur Entfernung (08-27) weiterhin das auffällig lockere 20%-Limit gegenüber 2% bei Konto1/2 - jetzt ohnehin nicht mehr OU-Modell-verwaltet. |
| **Gold ASB** | Kein Drawdown-/Kill-Switch-Mechanismus im Code. | Unverändert - noch nicht nachgerüstet. |
| **CTNL Edge FK** (die alte Bridge, bis 08-28) | Kein Drawdown-/Kill-Switch, nur `REV_MAX_CONCURRENT=3`. | Unverändert. Bot ist seit 08-28 ohnehin pausiert. |
| BTC EMA / CLS Challenge | `check_daily_drawdown()` (3%) live, `check_total_drawdown()` (7%) weiterhin toter Code (nie aufgerufen). | Kein Trigger (0 Trades/Signale). |
| **FK Instant Funding (Paper-Diagnose, Repo)** | Eigener Kill-Switch + Konsistenzregel | **Löste am 08-26 19:04 Uhr fälschlich aus** (-6,61% DD, 322 "Trades") - Bug im Kontostart-Gating, noch am selben Tag behoben (22:15 Uhr), Equity auf $100.000 zurückgesetzt. Kein echtes Geld betroffen, aber ein zweiter, bislang nicht erklärter Reset folgte am 08-27 20:58 Uhr (siehe Punkt 5). |

**Einordnung:** Gold ASB und CTNL Edge sendeten diese Woche zwar echte
Orders (Gold ASB: 2 fehlgeschlagene Versuche, siehe unten; CTNL: 0
Signale), aber weiterhin ohne jeden Drawdown-Deckel im echten Bridge-Code
- unverändert seit KW34. Da CTNL Edge FK seit 08-28 pausiert ist, sinkt
das akute Risiko vorübergehend; Gold ASB läuft (Stand des Wochenendes)
noch, bis auch dieser Bot laut Scheduled-Task-Status inzwischen deaktiviert
wurde (siehe Punkt 5) - die offene Empfehlung aus KW34 bleibt: den
`check_daily_drawdown()`-Bausatz auf Gold ASB portieren, bevor der Bot
wieder aktiviert wird.

## 3. Was hat gut / nicht gut funktioniert

- **Gold ASB / BTC EMA (geteiltes Konto 15514)**: **0 echte Trades** diese
  Woche bei beiden Bots - kein EMA-Cross ausgelöst, keine Gold-ASB-Setups
  bestätigt umgesetzt. Aber: am 08-26 und 08-27 versuchte Gold ASB je ein
  reguläres Long-Setup real zu senden und scheiterte beide Male am
  **exakt selben, bereits aus KW34 bekannten Bug** (`retcode=10027,
  AutoTrading disabled by client`, geteiltes Standard-Terminal). Dritte
  und vierte bestätigte Wiederholung desselben, seit 08-20 bekannten
  Problems - weiterhin ungelöst. Der nicht zuordenbare USDJPY-Restposten
  auf diesem Konto (siehe Punkt 5) ist weiterhin offen und hat sich diese
  Woche floating auf -$199,97 verschlechtert (war -$169,72 am 08-27).
- **CTNL Edge FK**: 0 Signale diese Woche (Fortsetzung des seit Live-Gang
  08-20 bekannten Musters), zusätzlich zwei neue, unbehandelte Python-
  Exceptions am 08-27 23:28 und 08-28 06:54 Uhr in der Dukascopy-Datenanbindung
  (`dukascopy_python`-Bibliothek, `TypeError`/`KeyError` in deren interner
  `_stream()`-Funktion) - neu, nicht root-caused, Bot wurde kurz danach im
  Zuge der Konsolidierung ohnehin pausiert.
- **OU-Modell**: einzige Bot-Familie mit nennenswertem echtem Handel bis
  zur Mittwochspause - 9 geschlossene Trades über 3 Konten, siehe Tabelle.
  Konto1 (TTP) verlor moderat weiter (nach einer sehr schlechten KW33),
  Konto2 (Demo) und Konto3/Tickmill blieben nahe der Nulllinie.
- **CLS Practical, FK Instant Funding, Funded-Portfolio-Bridge**: weiterhin
  reiner Papierbetrieb, daher keine echte Performance zu bewerten. FK
  Instant Funding lieferte diese Woche genau **ein geplantes** (nicht
  ausgeführtes) Signal (CTNL Reversal Gold, 08-28, auf `volume_min`
  angehoben: $59,88 statt Ziel $37,88).
- **TrendPullback FK1/FK2**: unverändert tot (FK1 seit 08-19, FK2 seit
  08-22) - siehe Punkt 5, jetzt fachlich redundant statt nur "still".
- **EK-Portfolio-Bridge**: ging diese Woche live, aber innerhalb des
  strengen KW35-Fensters (bis 08-30, 24 Uhr) **0 eigene Trades** - der Bot
  wurde erst Samstagabend scharf geschaltet und die neue Wochenend-Sperre
  verhinderte sofortiges Handeln; der erste echte Fill kam erst am
  Montag 08-31 (siehe Punkt 5).

## 4. Trades, Winrate, Gewinn ($/%) - Summary

Quelle: `mt5.history_deals_get()` direkt vom jeweiligen Broker (read-only)
für 2026-08-24 00:00 bis 2026-08-31 00:00, ergänzt um Bridge-Logs für
Fehlversuche. Nur **geschlossene** Trades zählen in Trades/Winrate; neu
eröffnete, noch offene Positionen werden separat genannt. Währungen werden
nicht umgerechnet/gemischt.

| Bot / Konto | Währung | Trades | Winrate | PnL | PnL (%, approx.) |
|---|---|---|---|---|---|
| Gold ASB + BTC EMA FK (Konto 15514) | USD | 0 | - | $0 (2 gescheiterte Versuche, kein Fill) | 0,00% |
| CTNL Edge FK (16054) | USD | 0 | - | $0 | 0,00% |
| CLS Practical Challenge (MT5) | EUR | 0 | - | €0 (DRY_RUN) | 0,00% |
| OU-Modell Konto1 (TTP) | USD | 4 | 25% (1/4) | -$283,28 | -0,29% |
| OU-Modell Konto2 (TTP, Demo) | USD | 2 (+1 neu eröffnet) | 50% (1/2) | +$35,43 | +0,04% |
| OU-Modell Konto3 / EK-Portfolio-Tickmill (55918977) | EUR | 3 | 33% (1/3) | -€40,17 | -1,14% |
| EK-Portfolio-Bridge (eigene neue Trades) | EUR | 0 (erster Trade erst 08-31, außerhalb) | - | €0 | 0,00% |
| FKInstantFunding-MT5-Bridge (echte Bridge) | - | 0 (1 geplant, DRY_RUN) | - | $0 | 0,00% |
| Funded-Portfolio-Bridge (TTP/IQ Markets) | - | 0 (DRY_RUN, gerade initialisiert) | - | $0 | 0,00% |
| TrendPullback FK1/FK2 | EUR | 0 (beide tot) | - | €0 | 0,00% |
| **Summe USD (nur Echtgeld/Challenge, ohne Demo)** | USD | 4 | 25% (1/4) | **-$283,28** | - |
| **Summe USD inkl. Demo-Konto2** | USD | 6 | 33% (2/6) | **-$247,85** | - |
| **Summe EUR (Echtgeld)** | EUR | 3 | 33% (1/3) | **-€40,17** | - |
| Portfolio Bot / FK Instant Funding (Repo-Paper-Diagnose) | USD | s. Hinweis | - | s. Hinweis | s. Hinweis |
| EK-Portfolio-Paper (Repo-Paper-Diagnose, inzwischen abgelöst) | USD | 10 | nicht ausgewertet | ≈ -$208,83 | -0,21% |

Hinweise zur Tabelle:
- OU-Modell Konto3/Tickmill trug bis 08-27 noch OU-Modells eigene Logik;
  alle 3 gezeigten Trades schlossen am 08-24/08-25, also **vor** der
  Entfernung aus OU-Modells Config und **vor** EK-Portfolio-Bridges
  Live-Gang - sie gehören sachlich noch zu OU-Modell, nicht zu
  EK-Portfolio-Bridge, auch wenn es dasselbe Konto ist.
- FK Instant Fundings Repo-Paper-Diagnose (`fk_instant_funding_logs`)
  durchlief diese Woche **zwei** Equity-Resets (08-26 20:00 nach dem
  Kontostart-Bug, dann nochmal 08-27 20:58, Ursache des zweiten Resets
  nicht abschließend geklärt) - eine saubere Wochensumme lässt sich daraus
  nicht seriös bilden, deshalb hier bewusst ausgelassen statt eine
  irreführende Zahl zu präsentieren. Kumulierte virtuelle Performance seit
  dem letzten Reset (08-27 20:58) bis 08-31 14:55 (reicht damit bereits in
  KW36 hinein): -$683,04 über 11 Trades (-0,68%) - als grobe Orientierung,
  nicht als Wochenzahl.
- EK-Portfolio-Paper war die Repo-interne Papier-Version vor dem Live-Gang
  der echten Bridge (08-29); der zugehörige Scheduled Task
  (`EK-Portfolio-Paper`) ist inzwischen deaktiviert/abgelöst.
- Die USDJPY-Restposition auf Konto 15514 (0,5 Lot, floating -$199,97) ist
  in der Trades-Zeile für Gold ASB/BTC EMA **nicht** enthalten, da sie
  diese Woche nicht geöffnet oder geschlossen wurde - siehe Punkt 5.

## 5. Auffälligkeiten / offene Punkte

1. **BTC-EMA-Cross-Bridge, BTC-EMA-Cross-Scan und CTNL-Edge-FK-Paper wurden
   am 2026-08-31 deaktiviert - ohne dokumentierte Begründung.** Per
   `schtasks`-Abfrage zum Ausführungszeitpunkt dieses Reports: beide
   BTC-Tasks zeigen `Deaktiviert`, letzter Lauf 08-31 ca. 03:15-03:40 Uhr;
   `CTNL-Edge-FK-Paper` zeigt ebenfalls `Deaktiviert`, letzter Lauf 08-31
   16:56 Uhr. Keine Memory-Notiz und kein Commit dieser Woche erklärt das.
   Zeitlich passt es zur Konsolidierung (beide Strategien sind bereits
   Beine in `EK-Portfolio-Bridge`, die am selben Tag ihren ersten echten
   Trade platzierte), aber das ist eine Vermutung, keine Bestätigung -
   bitte gegenprüfen, ob das beabsichtigt war, insbesondere weil
   BTC-EMA-Cross-Bridge echtes Geld verwaltet.
2. **Unzugeordnete USDJPY-Position auf Konto 15514 verschlechtert sich
   weiter** - floating jetzt -$199,97 (08-27: -$169,72; ursprünglich
   Ende August erstmals aufgefallen). Weder Gold ASB (nur XAUUSD/XAGUSD)
   noch BTC EMA (nur BTCUSD) handeln dieses Symbol; Magic Number weiterhin
   `0` bei beiden Bots, automatische Zuordnung unmöglich. Dritte Woche in
   Folge offen - dieselbe Empfehlung wie in KW34: eigene Magic Number pro
   Bot/Konto vergeben.
3. **Gold-ASB-AutoTrading-Bug (retcode=10027) trat diese Woche zwei weitere
   Male auf** (08-26, 08-27) - vierte/fünfte bestätigte Wiederholung seit
   Erstauftreten 08-20. Die in KW34 empfohlene Behebung (eigenes,
   dediziertes Terminal für Gold ASB, analog zu CLS/CTNL/OU-Modell) ist
   weiterhin nicht umgesetzt.
4. **CTNL Edge FK: zwei neue unbehandelte Exceptions** in der
   `dukascopy_python`-Datenanbindung (08-27 23:28 `TypeError`, 08-28 06:54
   `KeyError`), beide innerhalb der Bibliothek selbst (`_stream()`), nicht
   im eigenen Bot-Code. Nicht root-caused - könnte ein breiteres, auch
   andere Bots betreffendes Dukascopy-Problem sein (CLS Practical hatte
   bereits eine andere Dukascopy-bezogene Datumsgrenze-Bug, siehe
   Memory: `paper_bots_status_20260826`). Bot wurde kurz danach ohnehin pausiert,
   daher kein akuter Schaden, aber ungeklärt für die Wiederinbetriebnahme.
5. **FK Instant Fundings Paper-Diagnose durchlief zwei Equity-Resets diese
   Woche** - der erste (08-26 20:00) ist der bekannte, dokumentierte
   Kontostart-Bug-Fix; der zweite (08-27 20:58, direkt nach einem einzelnen
   -0,06%-Trade) ist in den verfügbaren Logs nicht eindeutig erklärt.
   Vermutlich ein weiterer Code-Deploy an diesem Tag (mehrere Commits rund
   um diese Zeit), aber nicht bestätigt.
6. **CTNL Edge FK (16054): Kontostand exakt $100.000,00 den ganzen Monat.**
   War in KW34 als mögliche Anomalie im Hinterkopf zu behalten - jetzt
   durch den vollständigen August-Datenabzug (Abschnitt Monatsreport)
   bestätigt: 0 geschlossene Trades seit Live-Gang 08-20 überhaupt, nicht
   nur diese Woche. Kein Datenfehler, sondern eine Strategie, die in
   diesem Marktumfeld bislang schlicht nie ausgelöst hat.
7. **TrendPullback FK1/FK2 weiterhin ohne jede Log-Aktivität** (FK1 seit
   08-19, FK2 seit 08-22, unverändert seit KW34) - inzwischen fachlich
   redundant, da `EK-Portfolio-Bridge` bereits ein eigenes
   `trend_pullback`-Bein enthält. Empfehlung: FK1/FK2 formal stilllegen
   statt als unklaren "stillen Ausfall" weiterzuführen, statt weiter auf
   eine Wiederherstellung zu warten.
8. **Unfertige, uncommittete Änderungen im Repo gefunden**:
   `challenge_portfolio/paper_bot.py` (+48/-6 Zeilen) und
   `ek_portfolio/paper_bot.py` (+33/-2 Zeilen) waren zum Ausführungszeitpunkt
   dieses Reports lokal verändert, aber nicht committet. Nicht Teil dieses
   Reports (nur `knowledge/reports/` wird von diesem Lauf committet) - nur
   zur Kenntnisnahme, falls das kein absichtlich offen gelassener
   Zwischenstand war.
9. **Kontoüberschneidung zwischen alten und neuen Bots**: `Funded-
   Portfolio-Bridge` (weiterhin DRY_RUN) ist auf **dieselben** Konten
   konfiguriert wie die pausierte `CTNL-Edge-MT5-Bridge` (Login 16054) und
   OU-Modells pausiertes Konto2 (Login 504072729). Aktuell kein Problem, da
   Funded-Portfolio-Bridge noch nicht live sendet - aber falls die alten
   Scheduled Tasks versehentlich reaktiviert werden, würden zwei
   unabhängige Bot-Codebasen dasselbe Konto verwalten. Vor einem Live-Gang
   von Funded-Portfolio-Bridge einmal bewusst gegenprüfen.
10. **CLS EK und BTC EK (beide MT4/Axi) weiterhin nicht per
    `MetaTrader5`-Python-Paket verifizierbar** - unverändert seit KW34,
    schwächste Datenquelle in diesem Report.
