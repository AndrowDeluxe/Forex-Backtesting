# Weekly Checkup - Performance - KW34/2026

**Zeitraum:** Montag 2026-08-17 bis Sonntag 2026-08-23.

> **Hinweis zur Ausführung dieses Reports:** Dieser Lauf fand am Donnerstag,
> 2026-08-27 statt, nicht wie vorgesehen am Sonntagabend (die geplante
> Wochenkadenz). Es existierten außerdem noch keine früheren "Weekly
> Checkup"-Reports in `knowledge/reports/weekly/` - dies ist der erste Lauf.
> Da die laufende Woche (KW35, 08-24 bis 08-30) am Ausführungstag erst bis
> Donnerstag reicht, deckt dieser Report bewusst die letzte **vollständig
> abgeschlossene** Mo-So-Woche ab (KW34) statt der unvollständigen KW35.
> KW35 sollte im nächsten Lauf (regulär oder nachgeholt) abgedeckt werden.
> Da der reguläre Monats-Trigger ("letzter Sonntag vor Monatswechsel") auf
> KW34 nicht zutrifft (KW34 endet nicht am Monatsende, es folgt noch KW35
> innerhalb des August), wurden **keine** Monatsreports erzeugt - siehe
> Punkt 5 unten für Details.

## 1. Wochenkontext

Aktive Bots/Legs in KW34 (Bridge-Ordner außerhalb des Repos, siehe Memory:
`paper_bots_status_20260826`):

- **BTC-EMA-Cross-Bridge**: FK (BeyondIQCapital, Login 15514, geteilt mit
  Gold ASB) live seit 2026-08-20 (`DRY_RUN=False`); EK (Axi MT4, Demo)
  weiterhin dateibasiert/`dry_run` markiert.
- **CLS-Practical-Bridge**: Challenge-Konto (MT5, Demo) **weiterhin
  `DRY_RUN=True`** die ganze Woche - keine echten Orders. EK (Axi MT4,
  Demo) ebenfalls ohne bestätigte Order diese Woche. Im Repo lief parallel
  viel Strategie-Forschung (09:00-Checkpoint, Zins-Skalierung als Standard,
  neuer Front-End-2Y-Filter - siehe Memory: `cls_practical_strategy_state`) -
  das betrifft aber nur die Anzeige/den Backtest, nicht die (weiterhin
  Paper-)Bridge.
- **CTNL-Edge-MT5-Bridge**: ging **mitten in der Woche live** -
  `DRY_RUN=False` seit 2026-08-21 (vorher Scheduled Task ab 08-20 im
  Dry-Run). Konto BeyondIQCapital Demo-Challenge IQCEV100K-130835.
- **GoldASB-MT5-Bridge**: durchgehend live (`DRY_RUN=False`), Konto 15514
  (geteilt mit BTC FK).
- **OU-Modell-MT5-Bridge** (3 Konten: Konto1 TTPMarkets-Server "TTP",
  Konto2 TTPMarkets-Server "TTP Demo", Konto3 TickmillEU-**Live**):
  **war bislang in keiner Memory-Notiz/keinem bekannten Bridge-Ordner
  dieses Reports gelistet** - durchgehend aktiv, mit echtem Handel diese
  Woche auf allen drei Konten. Konto1 und Konto3 tragen keinen
  "(Demo)"-Zusatz im Kontonamen bzw. laufen auf einem Server namens
  "...-Live" - vermutlich reale/Live-Konten, nicht nur Challenge-Demo wie
  die übrigen Bots. Wird ab diesem Report als Standard-Bestandteil des
  Weekly Checkups behandelt; bitte bestätigen, falls das nicht gewünscht
  ist.
- **TrendPullback-Bot FK1/FK2** (eigene dedizierte MT5-Terminals): beide
  liefen zu Wochenbeginn, aber **FK1 stoppte im Log am 2026-08-19 14:48
  Uhr** und hat seitdem (auch Stand heute, 08-27) keine einzige weitere
  Zeile geschrieben - 0 Trades diese Woche, aber auch keine erkennbare
  Aktivität nach Mittwoch. FK2 lief bis 08-22 15:59 Uhr normal weiter.
- **fk_instant_funding "Portfolio Bot"**: existierte diese Woche noch
  nicht (erster Commit 2026-08-26, außerhalb von KW34) - kein Eintrag in
  diesem Report.

Config-/Status-Änderungen innerhalb der Woche: CTNL Edge Dry-Run→Live
(08-21).

## 2. Risk-Management-Compliance

**Kein Kill-Switch/Drawdown-Halt hat diese Woche irgendwo ausgelöst.**
Aber die Qualität der Absicherung ist sehr unterschiedlich - das ist der
wichtigste Befund dieses Abschnitts:

| Bot/Konto | Mechanismus | Live verdrahtet? | Diese Woche geprüft |
|---|---|---|---|
| TrendPullback FK1/FK2 | `risk_manager.py::RiskManager` (Trailing-DD + Tages-Notbremse, persistiert in `risk_state_fk*.json`) | Ja | `halted=false` beide Konten, kein Trigger |
| BTC EMA FK / CLS Challenge | `check_daily_drawdown()` (Tages-DD, 3%) | Ja, bei jedem Lauf | Kein Trigger (Drawdown < 1%) |
| BTC EMA FK / CLS Challenge | `check_total_drawdown()` (Gesamt-DD, 7%) | **Nein - Funktion existiert in `executor_mt5.py`, wird aber in `run_once.py` nirgends aufgerufen.** Toter Code, kein aktiver Gesamt-Deckel. | - |
| OU-Modell (3 Konten) | `check_daily_drawdown()` pro Konto | Ja | Kein Trigger. Auffällig: Konto3 (Tickmill) hat `max_daily_drawdown_pct=20%`, Konto1/2 (TTP) nur `2%` - großer Unterschied, evtl. gegenprüfen ob beabsichtigt. |
| **Gold ASB** | - | **Kein Drawdown-/Kill-Switch-Mechanismus im Code vorhanden.** `AccountConfig`-Dataclass hat nicht mal ein `max_daily_drawdown_pct`-Feld, `run_once.py` ruft keine Drawdown-Prüfung auf. Einzige Bremse ist `risk_pct=1%` pro Einzeltrade. | - |
| **CTNL Edge** | - | **Ebenfalls kein Drawdown-/Kill-Switch im echten Bridge-Code.** (Ein Commit erwähnt einen "Kill-Switch" - das bezieht sich auf `gold_smc_htf_ltf/paper_bot.py`, das separate Repo-interne Paper-Diagnose-Skript, **nicht** auf `CTNL-Edge-MT5-Bridge`, die echte Bridge, die diese Woche live ging. Nicht verwechseln.) Einzige Bremse: `REV_MAX_CONCURRENT=3` (Positionsanzahl-Deckel bei Reversal-Re-Entries). | - |

**Einordnung:** Dass diese Woche nichts passiert ist, liegt bei Gold ASB
und CTNL Edge nicht an einer funktionierenden Sicherung, sondern daran,
dass die Drawdowns klein genug blieben. Beide Bots senden diese Woche
echte Orders an einen echten Broker (Demo-Challenge-Konten, aber mit
realen Challenge-Konsequenzen bei Regelbruch). Empfehlung: das bei
BTC/CLS/OU-Modell bereits vorhandene Muster (`check_daily_drawdown`) auf
beide portieren, bevor mehr Volumen über diese Konten läuft.

## 3. Was hat gut / nicht gut funktioniert

- **CLS Practical**: weiterhin reiner Papierbetrieb (DRY_RUN), daher keine
  echte Performance zu bewerten. Die Woche brachte aber echte
  Forschungsfortschritte im Repo (2Y-Zinsfilter adoptiert, Skalierung zum
  Standard). Noch nicht live geschaltet.
- **Gold ASB / BTC EMA (geteiltes Konto 15514)**: Das Konto verlor diese
  Woche netto rund -$920 bis -$960 (siehe Tabelle unten) - aber **weder
  Gold ASB noch BTC EMA haben laut ihrer eigenen State-Datenbank einen
  einzigen echten Trade ausgelöst** (BTC: 0 Zeilen in `executed_signals`;
  Gold ASB: alle Fenster diese Woche entweder durch Trend/Silber-Filter
  übersprungen oder - am 08-20 - durch einen fehlgeschlagenen Order-Send
  wegen deaktiviertem AutoTrading verhindert). Der reale Verlust stammt
  von einem einzelnen **nicht zuordenbaren EURUSD-Trade** (siehe
  Auffälligkeiten). Getrennt davon: Gold ASB hat am 08-20 ein reguläres
  Setup wegen des bekannten Shared-Terminal-Bugs (`retcode=10027
  AutoTrading disabled by client`) verpasst - bereits in
  `knowledge/areas/mt5-bot-deployment.md` dokumentiert, aber noch nicht
  behoben (trat am 08-26 und 08-27 erneut auf).
- **CTNL Edge**: ging diese Woche live, aber 0 Signale ausgelöst - deckt
  sich mit dem bereits in Memory `paper_bots_status_20260826` aufgelösten
  Fehlalarm (der Offline-Replay fand ebenfalls keine Signale im
  Live-Zeitraum). Zu früh für ein Urteil.
- **OU-Modell**: einzige Bot-Familie mit nennenswertem echtem Handel diese
  Woche (15 geschlossene Trades über 3 Konten). Ergebnis gemischt, siehe
  Tabelle - alle Konten deutlich innerhalb ihrer Drawdown-Grenzen.
- **TrendPullback FK1**: **ist mitten in der Woche (08-19) kommentarlos
  verstummt** und lief den Rest der Woche nicht mehr. Da die Märkte laut
  letzten Logzeilen ohnehin durchgehend "Trend falsch"/kein Setup zeigten,
  sind vermutlich keine Trades verpasst worden - der Ausfall selbst ist
  aber ein Betriebsproblem, unabhängig vom entgangenen PnL.
- **TrendPullback FK2**: lief die ganze Woche sauber (0 Trades, korrekt
  laut eigenem Log kein bestätigtes Setup).

## 4. Trades, Winrate, Gewinn ($/%) - Summary

Quelle: `mt5.history_deals_get()` direkt vom jeweiligen Broker für den
Zeitraum 2026-08-17 00:00 bis 2026-08-24 00:00 (read-only), ergänzt um
die eigenen `weekly_baseline`/`daily_baseline`-Tabellen der Bridges für
den Wochen-Equity-Delta. **Währungen sind nicht vermischt/umgerechnet**
(kein Live-FX-Kurs abgerufen) - USD- und EUR-Konten werden getrennt
summiert.

| Bot / Konto | Währung | Trades | Winrate | PnL ($/€) | PnL (%) |
|---|---|---|---|---|---|
| Gold ASB + BTC EMA FK (geteiltes Konto 15514) | USD | 1 (nicht eindeutig zuordenbar, s. u.) | 0% (1/1 Verlust) | ≈ -$920 (Trade) / -$959 (Konto-Delta, Proxy) | ≈ -0,96% |
| CLS Practical Challenge (MT5) | EUR | 0 | - | €0 (DRY_RUN) | 0,00% |
| CLS Practical EK (MT4 Axi) | - | kein bestätigtes Signal | - | nicht verifizierbar (kein Broker-API-Zugriff auf MT4) | - |
| CTNL Edge FK | USD | 0 | - | $0 | 0,00% |
| OU-Modell Konto1 (TTP) | USD | 5 | 20% (1/5) | -$816,12 | -0,83% |
| OU-Modell Konto2 (TTP, Demo) | USD | 5 | 40% (2/5) | +$155,66 | +0,16% |
| OU-Modell Konto3 (Tickmill) | EUR | 5 | 20% (1/5) | -€38,81 (davon +€3,80 Broker-Gutschrift, kein Trade-PnL) | -1,10% |
| TrendPullback FK1 | EUR | 0 (Bot seit 08-19 gestoppt) | - | €0 | 0,00% |
| TrendPullback FK2 | EUR | 0 | - | €0 | 0,00% |
| BTC EMA EK (Axi MT4) | - | 1 Signal, `dry_run=1` | - | kein echter Fill | - |
| **Summe USD** | USD | 11 gewertete Trades | 27% (3/11) | **≈ -$1.580,46** (Konto-Delta-Proxy für 15514 + exakte Baseline-Deltas OU1/OU2/CTNL) | - |
| **Summe EUR** | EUR | 5 gewertete Trades | 20% (1/5) | **-€38,81** | - |
| Portfolio Bot (FK Instant Funding) | - | - | - | **noch nicht gestartet** (erster Commit 2026-08-26, außerhalb dieser Woche) | - |

Hinweise zur Tabelle: Die "1 Trade" auf dem geteilten Konto 15514 ist der
einzige reale Deal der Woche, kann aber keinem der beiden dort laufenden
Bots zugeordnet werden (Symbol EURUSD.gbe - weder Gold-ASB- noch
BTC-EMA-Symbol). Der Konto-Delta-Proxy (-$959) nutzt BTC EMAs eigene
`daily_baseline`-Reihe (08-17 → 08-24, da diese Bridge keine
`weekly_baseline` führt) als bestverfügbaren Näherungswert für die
Wochenbewegung, nicht die exakte Wochengrenze.

## 5. Auffälligkeiten / offene Punkte

1. **Nicht zuordenbarer EURUSD-Trade auf Konto 15514** (2026-08-19,
   12:53-15:34 Uhr, -$880 realisiert + -$40 Kommission = -$920 netto).
   Weder Gold ASB (handelt nur XAUUSD.gbe/XAGUSD.gbe) noch BTC EMA FK
   (handelt nur BTCUSD.gbe) haben dieses Symbol im Programm, und keines
   der beiden Bots hat in seiner eigenen Dedupe-/State-Tabelle einen
   passenden Eintrag. Magic Number ist bei beiden Bots `0`, macht
   automatische Zuordnung unmöglich. Braucht manuelle Prüfung (manueller
   Trade? Drittes, nicht dokumentiertes Skript?) - nicht stillschweigend
   der einen oder anderen Strategie zugerechnet.
2. **Gold ASB verpasstes Setup, 08-20** (`retcode=10027, AutoTrading
   disabled by client`) - bereits als bekanntes Shared-Terminal-Problem in
   `knowledge/areas/mt5-bot-deployment.md` dokumentiert, aber weiterhin
   ungelöst: exakt derselbe Fehler trat laut `windows`-Tabelle auch am
   08-26 und 08-27 erneut auf (außerhalb dieser Woche, aber Beleg dass der
   Fix noch aussteht).
3. **TrendPullback FK1 seit 2026-08-19 14:48 Uhr ohne jede Logzeile** -
   Stand heute (08-27) 8 Tage Stillstand, keine erkennbare
   Wiederherstellung. FK2 zusätzlich seit 08-22 15:59 Uhr still (sollte
   Montag 08-24 fürs FX-Geschäft wieder gelaufen sein) - das liegt zwar
   größtenteils außerhalb dieser Berichtswoche, wird hier aber
   festgehalten, weil es zum Zeitpunkt dieses Laufs weiterhin besteht.
   Aktuell gibt es keine Überwachung, die einen solchen stillen Ausfall
   selbst meldet (siehe Education-Report, Optimierungsmöglichkeiten).
4. **OU-Modell-MT5-Bridge war in keiner bisherigen Memory-Notiz als
   Bridge-Ordner gelistet**, obwohl alle drei Konten diese Woche aktiv
   gehandelt haben und mindestens Konto1/Konto3 nach Kontoname/Server
   real bzw. Live wirken (nicht als Demo gekennzeichnet). Wird ab jetzt in
   jedem Weekly Checkup mitgeführt.
5. **Kein Monatsreport diese Woche** - die Trigger-Bedingung aus dem
   Report-Prompt ("letzter Sonntag vor Monatswechsel") ist an "heute"
   (2026-08-27, Donnerstag) gebunden und würde formal zutreffen
   (08-27 + 7 Tage = 08-03... nein, 09-03, also September). Da dieser
   Report aber bewusst KW34 (endet 08-23) statt der laufenden KW35 (endet
   08-30, dem tatsächlich letzten Sonntag im August) abdeckt, wäre ein
   Monatsreport jetzt unvollständig - er würde die letzte Augustwoche
   komplett auslassen. Deshalb hier bewusst zurückgestellt, nicht
   automatisch erzeugt. Empfehlung: sobald KW35 nachgeholt/regulär läuft,
   dort den Monatsreport für August anhängen.
6. **CLS EK und BTC EK (beide MT4/Axi)** lassen sich nicht per
   `MetaTrader5`-Python-Paket gegenseitig verifizieren (das Paket spricht
   nur MT5) - Aussagen zu diesen beiden Beinen stützen sich ausschließlich
   auf lokale Bridge-Logs/Signaldateien, nicht auf eine unabhängige
   Broker-Quelle. Als schwächste Datenquelle in diesem Report zu werten.
