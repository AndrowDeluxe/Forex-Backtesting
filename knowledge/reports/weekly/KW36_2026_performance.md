# Weekly Checkup - Performance - KW36/2026

**Zeitraum:** Montag 2026-08-31 bis Sonntag 2026-09-06.

> **Hinweis zur Struktur:** Dies ist der erste Weekly-Checkup-Lauf nach der
> am 2026-09-04 beschlossenen Umstellung auf reines Portfolio-Bridge-
> Reporting (drei Zeilen statt einer pro Einzelbein/-konto) - siehe
> `scripts/reports/weekly_report_prompt.md` und CHANGELOG-Eintrag
> "Weekly Checkup - Performance auf Portfolio- statt Bein-Ebene
> umgestellt". Einzelbein-Beiträge werden nur noch in Prosa innerhalb der
> jeweiligen Bridge-Bullets erwähnt, nicht mehr tabellarisch aufgeschlüsselt.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen die ganze Woche in ihrem jeweils
bestehenden Modus weiter - keine `DRY_RUN`-Umstellung diese Woche:

- **EK-Portfolio-Bridge** (Tickmill, echtes Geld): durchgehend live. Am
  Donnerstag (09-04) wurden zwei echte Order-Bugs in `legs/ny_open_orb/
  executor.py` gefunden und behoben (fehlendes `deviation`-Feld +
  Tickmills strengeres Kommentarlängen-Limit ließen ein NASDAQ-Ticket
  ~13h hängen; ein zweiter Bug ließ TP bei US30 auf der falschen
  Kursseite landen) - beide live bestätigt (Ticket 262117522 um 10:48
  Uhr geschlossen). Zusätzlich wurde EK-Portfolio-Bridge-Fast (die drei
  MT5-nativen Beine ORB/Gold-Silber/Trend-Pullback) bereits am 09-03 in
  einen eigenen, alle 2 Minuten laufenden Task ausgelagert (Vorwoche
  begonnen, diese Woche der erste volle Betriebswoche).
- **Funded-Portfolio-Bridge** (TTP + IQ Markets/BeyondIQCapital, 4 echte
  Konten, echtes Geld): am 09-03 verbanden nach einer fast 24h-Fehlersuche
  endlich **alle 4 Konten** gleichzeitig (Root Cause: fehlende
  "DLL-Importe zulassen"-Option + ein strukturell defekter Terminal-
  Ordner, siehe Memory `challenge_portfolio_ttp_icapital`). Am 09-03 wurden
  außerdem die 6 Strategie-Scans von "1x pro Konto" auf "1x pro
  Bridge-Lauf" entdoppelt. Am **09-04 ging der neue lokale Data-Lake-Pilot
  live** - alle 6 Beine lesen Marktdaten seitdem aus einem lokalen
  Parquet-Lake statt live von Dukascopy/TradingView/yfinance zu ziehen
  (siehe Memory `data_lake_pilot_20260904`); am selben Tag wurde zusätzlich
  der 5-Minuten-Fast-Trigger für `ctnl_continuation`+ORB scharfgeschaltet
  (siehe Memory `funded_portfolio_bridge_5min_fast_trigger`) und der
  eigenständige CTNL-Kill-Switch (Stand-alone-Drawdown gegen die
  Phase-6-Schwelle) in die Bot-Logik nachgerüstet. Heute (09-06) wurde
  beim Bau einer Twelve-Data-Ausweichquelle ein kritischer
  Concurrency-Bug im Data-Lake-Manifest gefunden und behoben, der laut
  Changelog zwischenzeitlich "ALLE 6 Beine lahmlegte" (siehe Punkt 5
  unten - der Zeitpunkt des tatsächlichen Auftretens ist nicht
  hundertprozentig auf diese Woche eingrenzbar, aber ein Fehlerbild
  dieser Woche passt auffällig gut dazu).
- **FK Instant Funding** (BeyondIQCapital 17764): durchgehend `DRY_RUN=True`
  (Paper), keine Code-Änderungen an diesem Bein diese Woche. Läuft
  weiterhin stündlich, die eigene Wochenend-/Spread-Stunden-Sperre pausiert
  korrekt Sa/So sowie zur täglichen Spread-Stunde.

## 2. Risk-Management-Compliance

**Kein Kill-Switch- oder Drawdown-Halt auf einem echten Konto diese
Woche.** Im Detail:

| Bridge/Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio-Bridge | Pro-Tag-Risikodeckel je Bein (`risk_cap_notified`) | **Griff korrekt** - Skip-Meldungen für `orb_NASDAQ`/`orb_SP500`/`orb_US30` am 09-02/09-03 (Deckel erreicht, Entry übersprungen) sowie ein `orb_stale_NASDAQ`-Skip am 09-04 (zu altes Signal übersprungen statt gejagt). Das ist die Sicherung, die wie vorgesehen funktioniert - keine Verletzung. |
| EK-Portfolio-Bridge | CTNL-Standalone-Kill-Switch (seit 09-04, `-6,6%`-Schwelle) | Nicht ausgelöst. |
| Funded-Portfolio-Bridge (alle 4 Konten) | `risk.kill_switch_active` pro Konto | `False` bei allen 4 Konten (ttp, iqmarkets, ttp1, iqmarkets2) - kein Trigger. |
| Funded-Portfolio-Bridge | CTNL-Standalone-Kill-Switch (seit 09-04) | **Nicht verifizierbar aus dem State** - anders als bei FK Instant Funding (wo `ctnl_kill_switch_active: false` explizit im State steht) taucht dieser Schlüssel in keiner der 4 `bridge_state_*.json` auf. Deckt sich mit der bereits im Changelog selbst vermerkten Einschränkung ("kein echter Live-Lauf abgewartet") - nicht neu, aber diese Woche nicht ausräumbar gewesen. |
| FK Instant Funding (Paper) | `kill_switch_active` + `ctnl_kill_switch_active` | Beide `False` die ganze Woche, `current_dd` blieb im Bereich von ca. -0,08% bis -0,3% - weit von jeder Schwelle entfernt. |

**Einordnung:** Keine Verletzung, keine Grenzwertüberschreitung. Die
einzige offene Lücke ist die fehlende Bestätigung, ob der
CTNL-Standalone-Kill-Switch in Funded-Portfolio-Bridge tatsächlich aktiv
mitläuft (siehe Tabelle) - sollte beim nächsten echten CTNL-Signal
gegengeprüft werden.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge**: Woche in etwa flach (Equity 3.467,90 € → 3.460,62 €,
  siehe Tabelle). Das NASDAQ-ORB-Bein war der Lichtblick - nach zwei
  frühen Stop-outs (Mo/Di, je knapp -3 bis -5 €) folgten am Donnerstag ein
  Teilausstieg und am Freitag der volle Ausstieg mit Gewinn (zusammen netto
  gut +15 €). Die OU-Modell-Aktienauswahl war gemischt (NUE ein Gewinner,
  RTX/UAL beides Stop-outs), SP500-ORB verlor sein einziges Signal knapp.
  Datenseitig war `cls_practical`/Dukascopy diese Woche die größte
  Baustelle (51 Scan-Fehler am Donnerstag, 26 am Freitag - siehe Punkt 5).
- **Funded-Portfolio-Bridge**: Auf Equity-Basis leicht positiv über alle 4
  Konten (+358,56 $ / +0,09%), aber getragen von einem einzelnen großen
  Gewinner (WFC-Position auf `ttp`, +232,29 $ netto) - ohne den wäre die
  Woche negativ gewesen. Die beiden größten Einzelverluste waren beides
  per Stop-Loss geschlossene OU-Modell-Aktienpositionen (TJX auf `ttp`
  -260,66 $, RTX auf `ttp1` -250,67 $). Gold-ASB/ORB-Legs lieferten kleine,
  gemischte Ergebnisse. `iqmarkets2` hatte diese Woche keinen einzigen
  geschlossenen Trade (nur eine noch offene Position mit positivem
  Floating-P&L).
- **FK Instant Funding (Paper)**: -147,53 $ / -0,15% simuliert über die
  Woche, 14 geschlossene Trades, nur 3 Gewinner. Die beiden ORB-US30-Trades
  (+2,96R je, 09-01 und 09-02) waren die klaren Lichtblicke, wurden aber
  von einer 3er-Verlustserie bei CTNL Reversal (Entries noch Freitag
  08-28, Exits Montagfrüh, je ca. -1,2R bis -1,3R) und wiederholten
  ORB-NASDAQ-Stop-outs (4x -1,03R, fast jeden Tag) aufgefressen. Die
  CTNL-Reversal-Serie passt zur bereits dokumentierten Fragilität dieses
  Beins, siehe Memory: `ctnl_reversal_edge_fragility_20260903`.

## 4. Trades, Winrate, Gewinn ($/%) - Summary

Quelle: `mt5.history_deals_get()` read-only direkt vom jeweiligen Broker
für 2026-08-31 00:00 bis 2026-09-07 00:00 (EK-Portfolio-Bridge, alle 4
Funded-Portfolio-Bridge-Konten), ergänzt um die jeweils eigene
Equity-Baseline-Historie (`daily_baseline`/`risk.eod_equity`) für die
$/%-Spalte. FK Instant Funding ist `DRY_RUN=True` (die reale MT5-Historie
zeigt dort erwartungsgemäß 0 Deals) - Zahlen stammen aus der lokalen
Paper-Simulation (`fk_instant_funding_logs/paper_state.json`), letzter
verfügbarer Equity-Stand Freitag 09-04 (die Wochenend-Sperre verhindert
korrekt jede Aktualisierung Sa/So). Nur **geschlossene** Trades zählen in
Trades/Winrate. $/% ist die volle Equity-Kurven-Veränderung über die Woche
(inkl. Floating-P&L auf noch offenen Positionen), nicht nur realisierte
Trades - die beiden können auseinanderlaufen, siehe Bullets oben.

| Bridge | Konto(s) | Währung | Trades | Winrate | PnL | PnL (%) |
|---|---|---|---|---|---|---|
| **EK-Portfolio-Bridge** | Tickmill 55918977 | EUR | 8 | 37,5% (3/8) | -7,28 € | -0,21% |
| **Funded-Portfolio-Bridge** | TTP+IQ Markets, 4 Konten | USD | 7 | 57,1% (4/7) | +358,56 $ | +0,09% |
| **FK Instant Funding** (Paper, `DRY_RUN=True`) | BeyondIQCapital 17764 | USD (simuliert) | 14 | 21,4% (3/14) | -147,53 $ | -0,15% |
| **Grand Total** (nur Echtgeld: EK + Funded) | - | EUR/USD gemischt | 15 | 46,7% (7/15) | s. Hinweis | ≈ +0,08 bis +0,09% |

Hinweise zur Tabelle:
- EK (€) und Funded ($) werden **nicht** zu einer einzigen $-Summe
  addiert (unterschiedliche Kontowährungen, keine belastbare
  EUR/USD-Umrechnung für diesen Report verfügbar). Die kapitalgewichtete
  Gesamtprozentzahl (+0,08-0,09%) ist trotzdem aussagekräftig, weil
  EK-Portfolio-Bridges Kontogröße (~3.470 €) selbst ohne Wechselkurs nur
  rund 1% von Funded-Portfolio-Bridges Gesamtkapital (~395.600 $) ausmacht
  - das Gesamtergebnis wird de facto vollständig von Funded-Portfolio-
  Bridge bestimmt.
- EK-Portfolio-Bridge hatte zusätzlich zwei nicht-Trade-Kontobewegungen
  am 09-04 (+6,40 €, +0,92 €, kryptische Kommentar-Codes) - vermutlich
  Swap-/Rebate-Gutschriften, nicht klar einem Trade zuordenbar. In der
  Trades-Zeile oben nicht mitgezählt (kein Trade), in der $/%-Equity-Zahl
  aber enthalten.
- Funded-Portfolio-Bridge: `ttp1` und `iqmarkets2` haben erst seit 09-03
  eine vollständige Konto-Historie (siehe Punkt 1) - für sie deckt die
  Woche faktisch nur Mi-Fr ab, nicht Mo-Fr. Das ist kein Datenfehler,
  sondern schlicht der Zeitpunkt der erfolgreichen Erstverbindung.

## 5. Auffälligkeiten / offene Punkte

1. **Lokaler `main` liegt seit heute Vormittag 64 Commits vor / 1 Commit
   hinter `origin/main`** - jeder automatische Bot-Commit (EK-, FK-Instant-
   Funding-, Bridge-Watchdog-Snapshots) scheitert seitdem beim Push
   ("rejected - fetch first"). Snapshots landen nur noch lokal, nicht auf
   GitHub gesichert. Bereits in `knowledge/DASHBOARD.md` unter "Braucht
   deine Bestätigung" vermerkt, hier nur wiederholt, weil es die ganze
   Woche... genauer: den ganzen heutigen Tag betrifft und ein echtes
   Backup-Risiko für die Live-Bot-States darstellt. Dieser
   Report-Lauf committet wie angewiesen nur lokal (`knowledge/reports/`),
   verschärft das Problem also nicht zusätzlich.
2. **Das komplette `data_lake/`-Paket (8 Dateien inkl. `manifest.py`,
   `storage.py`, `sources.py`, dem heutigen `twelvedata_source.py`) ist
   entgegen der eigenen Changelog-Dokumentation NIE committet worden.**
   Der Changelog-Eintrag vom 2026-09-04 beschreibt es explizit als
   "Neues Paket `data_lake/` (git-getrackt)" - `git log --oneline --
   data_lake/` liefert aber **keinen einzigen Commit**, `git status` zeigt
   den gesamten Ordner als `??` (untracked). Das ist eine andere, ernstere
   Kategorie als der Push-Fehler unter Punkt 1: dort existieren
   wenigstens lokale Commits, die nur nicht auf GitHub ankommen - hier
   wurde nie `git add`/`git commit` ausgeführt. Der komplette Code, von
   dem seit 09-04 alle 6 Beine von Funded-Portfolio-Bridge (echtes Geld,
   4 Konten) ihre Marktdaten beziehen, existiert ausschließlich auf
   dieser einen Maschine - ein Festplattenausfall würde ihn vollständig
   und ohne Wiederherstellungsmöglichkeit aus der Git-Historie löschen.
   Sollte zeitnah nachgeholt werden.
3. **12 neue, unverarbeitete Clippings seit 2026-09-03** in
   `knowledge/Clippings/` gefunden (PDFs zu Edge-Genesis/Risk-Factor-
   Investing/Sektor-Rotation u.a.) - drei Tage alt, noch nicht durch den
   CODE-Prozess gelaufen. In `knowledge/DASHBOARD.md` als offene Aufgabe
   ergänzt.
4. **Funded-Portfolio-Bridge: auffälliger Gleichlauf von Scan-Fehlern am
   09-04.** An allen 4 Konten traten an diesem Tag für `gold_asb`,
   `cls_practical`, `trend_pullback` UND `ctnl_edge` gleichzeitig exakt
   37 Scan-Fehler auf, davon 0 als "bekannt" klassifiziert - ein Muster,
   das eher zu einem gemeinsamen Infrastruktur-Fehler passt als zu vier
   unabhängigen Bein-Problemen. 09-04 ist genau der Tag, an dem der neue
   Data-Lake-Pilot live ging - und der heute (09-06) gefundene und
   behobene Manifest-Concurrency-Bug (siehe Punkt 1 im Wochenkontext)
   beschreibt exakt dieses Fehlerbild ("legte ALLE 6 Beine lahm"). **Nicht
   abschließend verifiziert**, ob es tatsächlich derselbe Vorfall war -
   der Fund wurde erst nachträglich am 09-06 dokumentiert, eine exakte
   Zeitkorrelation mit dem 09-04-Spike wurde nicht geprüft - aber die
   Übereinstimmung ist auffällig genug, um sie hier festzuhalten statt
   stillschweigend zu übergehen.
5. **6 neue `knowledge/`-PARA-Notizen diese Woche erstellt, aber nie
   committet** (`edge-card-workflow.md`, `backtest-standard-process.md`,
   `second-brain-methodik.md`, `order-flow-trading.md`,
   `opening-range-breakout.md`, `strategie-backlog-inventar.md` - alle
   laut `git status` weiterhin `??`/untracked). Existieren nur auf dieser
   einen Maschine, nicht in der Git-Historie gesichert. Nicht Teil dieses
   Reports (nur `knowledge/reports/` wird committet), nur zur Kenntnis.
6. **`cls_practical`/Dukascopy-Instabilität auf EK-Portfolio-Bridge
   diese Woche deutlich schlimmer als sonst** - 51 Scan-Fehler am
   Donnerstag (09-03), 26 am Freitag (09-04), gegenüber 1-4/Tag an den
   übrigen Tagen. Bekannter, nicht behebbarer Bug in der
   `dukascopy_python`-Bibliothek selbst (`_stream()`), aber die Größenordnung
   dieser Woche sticht heraus - falls sich das fortsetzt, könnte ein
   dediziertes Monitoring dieser speziellen Fehlerquote sinnvoll sein.
7. **EK-Portfolio-Bridge: zwei nicht zuordenbare Kontobewegungen** am
   09-04 (siehe Tabellen-Hinweis oben, +6,40 € / +0,92 €) - vermutlich
   harmlose Broker-Gutschriften, aber nicht mit Sicherheit einem Trade
   zugeordnet.
8. **Uncommittete lokale Änderungen im Repo** (`CLAUDE.md`,
   `challenge_portfolio/paper_bot.py`, mehrere `knowledge/`-Dateien)
   waren zum Ausführungszeitpunkt dieses Reports bereits vorhanden - nicht
   durch diesen Lauf verursacht, nicht Teil des Commits dieses Reports,
   nur zur Kenntnis.
