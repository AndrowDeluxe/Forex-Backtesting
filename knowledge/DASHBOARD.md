# Dashboard

**Stand: 2026-09-17** _(wird bei jeder Session von Claude auf das aktuelle
Datum nachgeführt — "Zuletzt geprüft" in der Statustabelle unten kann davon
abweichen und älter sein, siehe `CLAUDE.md` Punkt 4)._

Die tägliche Cockpit-Ansicht — hier reinschauen, nicht in Task Scheduler,
config.py-Dateien oder Chat-Verläufe wühlen. Funktioniert in jedem Editor,
kein Obsidian nötig. Wird von Claude bei jeder relevanten Änderung
nachgeführt (siehe `CLAUDE.md`).

Research-Wissen (Papers, Strategie-Findings) gehört NICHT hierher, sondern
in die PARA-Struktur (`projects/`, `areas/`, `resources/`, `archive/`,
siehe `README.md`). Hier geht es nur um: was läuft gerade, was ist zuletzt
passiert, was steht an.

---

## ▶️ Als Nächstes

1. **Manuelles Monatsjournal + Quant-System-Verschmelzung** (Nutzerwunsch
   2026-09-02): händisches Monatsjournal + Plan, wie manuelles Trading und
   das Quant-System sinnvoll verschmolzen werden — braucht zuerst ein
   klärendes Gespräch (Format, Kennzahlen). Noch nichts gebaut.

---

## 📋 Offene Punkte (nach Priorität)

Zusammengeführt aus "Braucht deine Bestätigung" + "Offene Aufgaben" — nach
Priorität sortiert, erledigte Punkte pro Kategorie unten. Höchste Priorität:
offene Projekte mit konkretem nächstem Schritt (aktuell keins offen — der
gold_asb-Cache-Bug oben läuft über "Als Nächstes"). Danach: Bestätigungs-
Bedarf vor generischem Aufräumen.

### 🔍 Braucht deine Bestätigung

- **Git-Sync: Push-Rueckstand ist aufgeloest (09-19), aber die Ursache steht
  noch offen.** 242 Commits sind auf GitHub. Der Abbruch kam NICHT von
  widerspruechlichen Inhalten, sondern von nicht committeten Aenderungen an
  `knowledge/`-Dateien, die der Remote ebenfalls angefasst hatte.
  `scripts/lib/git_sync_push.ps1` erwartet einen sauberen Working Tree und
  meldet diesen Fall faelschlich als „echten Konflikt". **Vorschlag:** Merge
  mit `-c merge.autoStash=true` fahren (legt offene Aenderungen kurz beiseite)
  und die Warnung nach Ursache trennen. Sonst blockiert der naechste
  Session-Edit den Push wieder.

- **Tick-Rundung in den gemeinsamen Order-Engpass von Funded + FK — darf ich?**
  (2026-09-17, Lückenliste Punkt 1, **nicht umgesetzt**.) Heute rundet jeder
  Order-Pfad selbst oder gar nicht: Funded-Stop-Orders ja, Funded-Market-
  Orders **nein**, FK-Market-Orders nur den SL. Das ist derzeit harmlos, weil
  über den ungerundeten Pfad nur Symbole mit regulärem Raster laufen — die
  einzige Ausnahme `SPX500.gbe` (Tick 0,1 bei 2 Nachkommastellen) geht auf
  Funded über die rundenden Stop-Orders. Beim nächsten Umbau (z. B. Stop-Orders
  aus, neues Symbol) geht die Lücke still wieder auf. Vorschlag:
  `_send_order()` rundet `sl`/`tp`/`price` selbst, idempotent (Werte auf dem
  Raster bleiben unverändert, also No-Op für die schon rundenden Pfade), SL
  von der Position weg. **Mein Versuch wurde vom Auto-Mode-Classifier
  blockiert — und zwar mittendrin:** das erste von zwei Edits ging durch, der
  nötige `import math` nicht. Ich habe die Änderung daraufhin vollständig
  zurückgenommen, `py_compile` + Log-Prüfung sauber, kein Lauf betroffen.
  Wenn du willst, dass ich es baue: kurze Freigabe hier, und ich verifiziere
  per `order_check` (legt keine Order ins Buch) gegen `SPX500.gbe`.
- **Lake-Frischefenster: anpassen oder so lassen?** (2026-09-17, Lückenliste
  Punkt 4, **nicht umgesetzt**, weil sich die Voraussetzung verschoben hat.)
  Meine Annahme vom 09-14 war „35 Min. ist zu knapp". Belegt ist inzwischen,
  dass die Stale-Fenster dort liegen, wo Ingest **und** Bridge gleichzeitig
  ausfielen — springende Windows-Zeitzone (siehe Punkt darunter) und Schlaf.
  Ein breiteres Fenster würde das verdecken, nicht beheben. Vertretbar bleibt
  eine **Staffelung nach Timeframe**: M5/M15 bei 35 Min. lassen (timing-
  kritisch), H1/H4 lockern (dort ist ein 40 Minuten alter Balken derselbe
  Balken). Empfehlung: erst die Zeitzonen-Frage klären, dann eine Woche
  Fallback-Zählung abwarten (`soll_ist.py` liefert den Vergleich).

- **🔴 OU-Modell: Edge wird von den Kosten aufgefressen — Bein weiterführen,
  pausieren oder umbauen?** (2026-09-17, Nutzerfrage, reine Auswertung, kein
  Code geändert). Modell reibungsfrei +0,097R/Trade (PF 1,34), realistisch
  ausgeführt +0,05R, mit live gemessenem Spread (12 bps, zur Eröffnung 26) und
  Swap (6,5 % p.a.) **−0,013R, PF 0,96**; seit 2023 −0,046R. Live 88 Trades
  ≈ 0R — passt zur Erwartung. Swap kostet so viel wie der Spread, weil 63 %
  der Trades die vollen 10 Tage laufen. Nur Einstieg nach 10:00 NY bringt es
  auf ±0. Entscheidung liegt bei dir. Details:
  [[ou-modell-kostenvalidierung]].
- **✅ Funded/OU: Signaldatum-Drift behoben 2026-09-17** (Nutzerauftrag).
  `_reconcile_ou_positions()` haelt je Titel hoechstens eine Position und
  schliesst, was das Modell nicht mehr haelt. Erster echter Abgleich beim
  Funded-Lauf 15:43 -- **bitte danach in Telegram auf 5 „🧹 ABGLEICH"-Meldungen
  pruefen** (Konto 2: FAST, ADI, AMGN, APD; Konto 1: AMGN). APD auf Konto 1
  bleibt bewusst offen (einzige APD dort, Modell haelt APD). Details: CHANGELOG.
- **🟠 8 verwaiste OU-Solo-Positionen: Schliessen ist vorbereitet, Ausloesen
  liegt bei dir** (2026-09-17). Du hast das Schliessen beauftragt; das Skript
  `scripts/close_ou_solo_orphans_once.py` ist fertig und per Vorschau gegen die
  echten Konten geprueft. Das automatische Einplanen hat der Auto-Modus
  blockiert. Befehl zum Einplanen (15:35:15) oder `--live` nach 15:30 direkt
  ausfuehren -- siehe Chat vom 2026-09-17. Punkt erst entfernen, wenn Telegram
  „OU-Solo-Waisen geschlossen" gemeldet hat.
- **🟡 EK/OU: Max-Holding schliesst nie, nur Warnung** (2026-09-17). ADI, AXP,
  DHI, GRMN laufen seit 14 Tagen (Modell: 10). `legs/ou_modell/executor.py::
  manage_open_positions()` loggt nur CRITICAL. Weicht vom Backtest ab und
  verlaengert den Swap -- gehoert zur OU-Optimierung, nicht still geaendert.
- **🟠 MNST-Split auf TTP nicht umgebucht: −2.492,56 $ auf Konto 1 (echtes
  Geld)** (2026-08-11, gefunden 2026-09-17). Tickmill buchte die Position beim
  2:1-Split korrekt um, TTP nicht — der alte SL wurde zum halbierten Kurs
  ausgelöst, keine Ausgleichsbuchung. Kandidat für eine Support-Anfrage bei
  TTP; ein Split-Schutz in der Bridge fehlt ebenfalls.

Punkte, bei denen etwas unklar/widersprüchlich ist oder eine Annahme von mir
noch nicht von dir bestätigt wurde. Erledigte Punkte werden entfernt, nicht
abgehakt-und-liegengelassen.

- **🟡 ORB-Stop-Orders (Demo ttp/iqmarkets): vier Annahmen von mir** (2026-09-17,
  Details `CHANGELOG.md` 2026-09-16/17). (1) Teilausstieg als zweite Order mit
  Broker-TP statt gepollt; (2) OCO-Whipsaw: spaeter gefuellte Seite sofort
  schliessen (Backtest verwirft solche Bars nur); (3) Ausbruch vor Platzierung
  = Tag verpasst, kein spaeter Entry; (4) Fast-Lauf wartet ~2 Min bis 09:45:03
  NY. Erster echter Test: 2026-09-17. **Nutzerentscheid 2026-09-17:** laeuft
  der Tag fehlerfrei, wird die Logik auf ALLE anderen Bridges uebertragen
  (ttp1, EK, FK) -- mit Rekalibrierung des Risikos je Bridge. **Risiko:** faellt der
  Fast-Lauf um 15:43 wegen des Zeitzonen-Springens (Punkt darunter) aus, gibt
  es keinen praezisen Pass -- dann Platzierung erst 15:48 und ~60 % der
  Ausbrueche verpasst.

- **Zeitzonen-Fix beobachten (2026-09-17 umgesetzt):** automatische Zeitzone
  ist aus, fest auf Berlin. Pruefen bis ~2026-09-19: keine neuen
  `Kernel-General`-Id-1-Events mit `reason=3` im System-Eventlog und keine
  1-h-Luecken in den Bridge-Logs. Danach Punkt entfernen.

- **Cloud-Bridge-Monitor meldete 09-16/17/18 dreimal Alarm — beides inzwischen
  geklaert (2026-09-19).** (1) „CLS-Fix greift nicht": der Cloud-Fix in
  `cls_practical/rates.py` war richtig, aber nicht die ganze Ursache — die
  Zinsreihen waren im Lake verdoppelt (behoben 09-16) und der Ausloeser war die
  springende Windows-Zeitzone (behoben 09-17). (2) „`snapshot.json` seit ~3 Tagen
  eingefroren": der Watchdog laeuft lokal normal (letzter Snapshot 09-18 23:31,
  heute Wochenendpause) — eingefroren war nur GitHub, weil die Auto-Pushes seit
  09-16 an diesem Merge haengen blieben. Genau dieser Merge ist jetzt aufgeloest.



  | | PF | Ø R | Sharpe | MaxDD | Calmar | Hebel max |
  |---|---|---|---|---|---|---|
  | EK heute (neu verankert) | 1,42 | 0,25 | 0,65 | −5,57 % | 0,48 | 11,0x |
  | absoluter SL + R-Detektor | **1,85** | **0,42** | **1,02** | **−4,20 %** | **0,93** | 15,5x |

  Auf jeder Kennzahl besser außer dem maximalen Hebel. Gilt über alle
  getesteten Kostenannahmen (0,50 / 1,00 / 2,05 Pips). Ursache: der neu
  verankerte Stop sitzt nicht mehr am strukturellen Invalidierungspunkt, und
  genau dieses Niveau trägt den Edge.
  **Nicht umgestellt** — das ist eine Architekturänderung an einer
  Echtgeld-Bridge. Sag Bescheid, dann ziehe ich EK auf dasselbe Muster wie
  Funded/FK (absoluter SL + R-Detektor 0,50R).


- **Kurztakt-Task-Ausfälle (1–2 h, 09-07 bis 09-11) beobachten bis ~2026-09-24**
  (Nutzerentscheid 2026-09-17). Die Ausfälle lagen VOR den Zeitzonen-Sprüngen
  (ab 09-15), Ursache also offen. Tritt nach dem Zeitzonen-Fix erneut eine
  Lücke auf: Task-Scheduler-Verhalten gezielt instrumentieren. Sonst löschen.





### Offene Aufgaben



- **FK SP500 „Invalid stops“: behoben 2026-09-17** (SL aufs Tick-Raster).
  Nur noch: ersten echten SP500-Entry im FK-Log gegenlesen, dann Punkt löschen.

- **CLS-Bein auf Bewährung: Prüfung nach 30 Live-Trades** (Kriterium festgelegt
  2026-09-17, Nutzerentscheid). Dann: Live-Ø R < 0 oder außerhalb des
  Monte-Carlo-Bands → pausieren. Hintergrund: Edge real, CAGR nur 0,78 %
  (`projects/cls-practical-kostenvalidierung.md` Befund 7).
- **Mindest-Stopabstand für weitere Beine: zurückgestellt bis nach den
  Kosten-Checks je Bein** (Nutzerentscheid 2026-09-17). Kandidat vor allem
  CTNL; für Tagessignale wie OU nicht sinnvoll. Bis dahin begrenzen nur
  `volume_max` und der Margin-Deckel.

**Mittel**
- **14 unverarbeitete Clippings** in `knowledge/Clippings/` (Stand
  2026-09-14-Lint, unveraendert seit 2026-09-09) — u.a. Edge-Genesis/-Decay,
  Risk-Factor-Investing, Sektor-Rotation, "Six Repos One System", "How
  system works" — noch nicht durch den CODE-Prozess.

**Niedrig**

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Letzter echter Entry | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld** (btc/ou_modell weiterhin direkt Dukascopy/yfinance; gold_asb/cls_practical/ctnl x2 jetzt `source="lake"`) | Ready (alle 15 Min, Mo–Fr)      | **16.09.** ou_modell (IVZ) | 2026-09-13      |
| EK-Portfolio-Bridge-Fast                                | Tickmill Live (55918977, geteiltes Terminal)                                             | **LIVE — echtes Geld** (3 MT5-native Beine: ORB/Gold-Silber/Trend-Pullback, kein Dukascopy)  | Ready (alle 2 Min, Mo–Fr)       | ↑ gleiches Konto | 2026-09-13      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | **LIVE — echtes Geld** (7 Beine via `LIVE_LEGS`: orb_sp500/us30/nasdaq + gold_asb/cls_practical/ctnl_continuation/ctnl_reversal seit 09-09; trend_pullback/gold_silver bleiben geplant/geloggt) | Ready (stündlich, Mo–Fr)        | **14.09.** orb_nasdaq — erster echter Entry seit Livegang | 2026-09-13      |
| FKInstantFunding-MT5-Bridge-Fast                        | BeyondIQCapital (17764, geteiltes Terminal)                                              | **LIVE — echtes Geld** (ctnl_continuation + orb_sp500/us30/nasdaq + cls_practical, `source="lake"`, analog Funded-Fast) | Ready (alle 5 Min, Mo–Fr)       | ↑ gleiches Konto | 2026-09-13      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram, **nur noch trend_pullback/gold_silver** (die anderen 7 Beine laufen live über die Bridge, seit 09-09 hier entfernt) | Ready (stündlich, Mo–Fr)        | — | 2026-09-13      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner + Telegram (3x täglich: 15:35/18:35/21:35)                                           | Ready (Mo–Fr, US-Handelszeiten) | — | 2026-09-02      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator (seit 09-15: Zeitlimit 4h statt 1h, Vollständigkeitsprüfung + 3x Wiederholung alle 4h bei unvollständigem Lauf) | Ready (So 18:00 — läuft am Wochenende bewusst weiter) | — | 2026-09-15      |
| Bridge-Watchdog                                         | — (nur Log-Frische, kein Order-Bezug)                                                    | Heartbeat-Alarm + Status-Snapshot ins Repo                                                   | Ready (alle 30 Min, Mo–Fr)      | — | 2026-09-13      |
| Funded-Portfolio-Bridge (TTP 6 Beine @1/6, IQ 5 Beine @1/3) | TTP Konto 2 (504072729) + TTP Konto 1 (504069845) + BeyondIQCapital (16054) — **alle 3 verbunden** (IQ 15514 am 2026-09-07 entfernt) | **LIVE — DRY_RUN=False** (alle 6 Beine `source="lake"`; **seit 09-13 kontospezifisch: IQ ohne `ou_modell`, Kapitalanteil 1/3 statt 1/6 — IQ handelt keine Aktien**; IPC-Timeouts 09-08 09:52-12:24 Uhr, seither stabil, siehe 🔍 Bestätigung) | Ready (alle 15 Min, Mo–Fr)      | **16.09.** orb_sp500 (TTP1) | 2026-09-13      |
| Funded-Portfolio-Bridge-Fast                            | Gleiche 3 Konten (geteilte Terminals)                                                    | **LIVE — DRY_RUN=False** (ctnl_continuation + orb_sp500/us30/nasdaq + cls_practical, `source="lake"`) | Ready (alle 5 Min, Mo–Fr)       | ↑ gleiche Konten | 2026-09-13      |
| DataLake-Ingest-Fast                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt `data_lake_store/` für Funded-Portfolio-Bridge (19 Keys, 15-Min-Kadenz)                | Ready (alle 15 Min, Mo–Fr)      | — | 2026-09-13      |
| DataLake-Ingest-Fast5                                   | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt 8 M5/M15-Timing-kritische Keys für ctnl_continuation/orb/cls_practical (EURUSD M5 seit 2026-09-07) | Ready (alle 5 Min, Mo–Fr)       | — | 2026-09-13      |
| DataLake-Ingest-Slow                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt OU-Modell-Universum (~59 Ticker) via yfinance                                          | Ready (stündlich, Mo–Fr)        | — | 2026-09-13      |
| Dashboard-Telegram-Digest (neu)                         | — (nur Lesezugriff auf DASHBOARD.md, kein Order-Bezug)                                   | Schickt offene Punkte aus DASHBOARD.md per Telegram                                          | Ready (täglich 8:00, auch Sa/So — bewusst) | — | 2026-09-13      |

**Letzter echter Entry** (Spalte seit 2026-09-16): letzter Eröffnungs-Deal beim Broker, der **dieser Bridge zugeordnet** ist (EK über Magic, Funded/FK über die Tickets im `bridge_state`). Fremdpositionen zählen nicht mit — auf FK lagen am 14.09. zwei manuelle Positionen, die sonst wie Bridge-Aktivität ausgesehen hätten. Grund für die Spalte: der Modus LIVE hat fünf Tage lang verdeckt, dass FK nichts ausführte. Aktualisieren mit `python scripts/reports/soll_ist.py --last-entries`. Zeiten sind Broker-Serverzeit.

### ⏸️ Wochenend-Pause (seit 2026-09-13)

Alle Tasks oben mit „Mo–Fr" sind am Wochenende komplett still (Markt zu,
keine Daten) — ein leerer Sa/So-Log ist also **KEIN Ausfall, sondern Plan**.
Gestartet wird wieder Mo 00:00; die erste Handelsstunde So 23:00–24:00
entfällt bewusst. Ausnahmen, die weiterlaufen: `Forex-Weekly-Report` (So
18:00) und `Dashboard-Telegram-Digest` (tägl. 8:00). BTC-Tasks unangetastet.

**Die tatsächlichen Trigger** (Soll-Zustand, deklarativ hinterlegt in
`scripts/weekend_pause.ps1` — `-Verify` zeigt den Ist-Zustand, `-Apply` ist
idempotent, `-Revert` spielt die XML-Backups aus `scripts/task_backups/`
zurück). Alle Wochentags-Trigger, Bitfeld `DaysOfWeek=62` = Mo–Fr:

| Task                               | Erster Lauf | Takt  | Wiederholung endet |
| ---------------------------------- | ----------- | ----- | ------------------ |
| `EK-Portfolio-Bridge-Fast`         | 00:00:10    | 2 Min | PT23H58M (23:58)   |
| `Funded-Portfolio-Bridge-Fast`     | 00:03:00    | 5 Min | PT23H55M (23:58)   |
| `FKInstantFunding-MT5-Bridge-Fast` | 00:03:00    | 5 Min | PT23H55M (23:58)   |
| `DataLake-Ingest-Fast5`            | 00:01:50    | 5 Min | PT23H55M (23:56)   |
| `DataLake-Ingest-Fast`             | 00:10:28    | 15 Min| PT23H45M (23:55)   |
| `Funded-Portfolio-Bridge`          | 00:13:00    | 15 Min| PT23H45M (23:58)   |
| `EK-Portfolio-Bridge`              | 00:14:00    | 15 Min| PT23H45M (23:59)   |
| `DataLake-Ingest-Slow`             | 00:10:29    | 1 Std | PT23H (23:10)      |
| `FKInstantFunding-MT5-Bridge`      | 00:14:00    | 1 Std | PT23H (23:14)      |
| `FK-Instant-Funding-Paper`         | 00:55:22    | 1 Std | PT23H (23:55)      |
| `Bridge-Watchdog`                  | 00:01:23    | 30 Min| PT23H30M (23:31)   |

Die Sekunden sind kein Zufall: der **Ingest muss vor dem Bridge-Scan laufen**
(Fast5 :01:50 vor Fast-Bridges :03:00, Fast :10:28 vor Funded :13:00 — Fund
2026-09-09, Task-Offsets). Beim Ändern eines Triggers diesen Versatz
mitziehen, sonst scannt eine Bridge auf Daten des vorigen Intervalls.

**Zwei Lernpunkte aus dem Umbau** (beides war von außen nicht sichtbar):

1. Ein Wochentags-Trigger reicht **nicht**, wenn die Wiederholungsdauer
   `P1D` ist — die Wiederholung läuft dann über Mitternacht hinaus weiter
   (drei Bridges liefen so bis Sa 00:03 bzw. 00:13). Deshalb steht bei jedem
   Task jetzt eine Dauer, die vor 24:00 endet.
2. Diese Statustabelle führte mehrere Tasks als „Mo–Fr", die im Task
   Scheduler tatsächlich 7 Tage liefen (`EK-Portfolio-Bridge-Fast` alle 2 Min
   rund um die Uhr). Die Modus-Spalte allein beweist nichts — **bei Zweifeln
   `weekend_pause.ps1 -Verify` statt Dashboard lesen** (CLAUDE.md Punkt 4).

Live-Status aller drei Portfolio-Bridges jetzt auch als Streamlit-Seiten
(„Portfolio-Bridges" in der Sidebar) — lesen `bridge_status/snapshot.json`,
das der Bridge-Watchdog alle 30 Min. committet.

_Letzter Lint-Durchlauf: **2026-09-17** (manuell, bei der Dashboard-Durchsicht
mit dem Nutzer). Ergebnis: 0 tote Wikilinks, 0 verwaiste Seiten, 0 veraltete
Statustabellen-Daten; 14 unverarbeitete Clippings bleiben für den nächsten
Lint-Lauf (Nutzerentscheid). Verweise nach außerhalb von `knowledge/` jetzt
als Pfad in Backticks (siehe `README.md`)._

## Status — aktuell nicht aktiv

| Bot/Bridge                                              | Konto/Broker                                                                             | Status                                                                                          | Task Scheduler | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------- | --------------- |
| Challenge Portfolio (Paper-Bot, `challenge_portfolio/`) | — (reine Simulation)                                                                     | Paper-Bot fertig entwickelt, kein Task angelegt                                                | —              | 2026-09-01      |
| BTC-EMA-Cross-Bridge/-Scan                              | Binance / BeyondIQCapital (15514, geteilt mit GoldASB)                                   | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS_MT5` leer                       | Disabled       | 2026-09-02      |
| CLS-Practical-Bridge/-Scan                              | —                                                                                        | aufgelöst — Logik steckt bereits in allen drei Portfolio-Bots                                 | Disabled       | 2026-09-02      |
| CTNL-Edge-FK-Paper                                      | —                                                                                        | aufgelöst — Logik steckt bereits in allen drei Portfolio-Bots                                 | Disabled       | 2026-09-02      |
| CTNL-Edge-MT5-Bridge                                    | BeyondIQCapital (16054)                                                                  | aufgelöst — Konto/Terminal bereits bei Funded-Portfolio-Bridge live                            | Disabled       | 2026-09-01      |
| Gold-ASB-Scan / GoldASB-MT5-Bridge                      | BeyondIQCapital (15514)                                                                  | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` leer                           | Disabled       | 2026-09-02      |
| OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat               | —                                                                                         | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` komplett leer                  | Disabled       | 2026-09-02      |
| EK-Portfolio-Paper                                      | —                                                                                        | pausiert (Paper-Zwilling von EK-Portfolio-Bridge, gehört zum Portfolio)                        | Disabled       | 2026-09-01      |

## 💡 Ideen-Inbox (unsortiert, später einordnen)

Kurz einfangen, was gerade auftaucht, ohne das aktuelle Thema zu verlassen —
wird bei Gelegenheit einsortiert (Offene Aufgaben, PARA-Struktur, oder
bewusst verworfen), nicht hier für immer liegen gelassen.

- **FK-CLS-Scan liefert einen Trade am Sonntag** (2026-09-17): `_scan_cls_practical`
  (source=lake) zeigt Entry 2026-09-06 09:55 Berlin -- ein Sonntag, FX geschlossen.
  Beim Pip-Boden-Test aufgefallen, nicht untersucht (Lake-Bars am Wochenende?).
- **NY-Open ORB komplett von dukascopy lösen** (2026-09-09): der heutige
  Fix verkürzt nur die Hang-Dauer (3x/20s statt 6x/90s), beseitigt sie
  nicht. Strukturell sauberer wäre, die ORB-Entry-Daten direkt per MT5
  (`mt5.copy_rates_range()`) zu holen — genau das macht
  `EK-Portfolio-Bridge/run_once_fast.py` für seine 3 zeitkritischen Beine
  bereits ("sie haengen NIE an einem dukascopy_python-Hang"). Bewusst
  zurückgestellt (Nutzerentscheid 2026-09-09): braucht neuen Code +
  Validierung (Symbol-Suffixe, Zeitzonen, Abgleich gegen den bestehenden
  dukascopy-basierten Backtest), also eine eigene Session wert.
- **Periodischer `/doctor`-Check** (2026-09-04): zurückgestellt, noch keine
  nennenswerte Skill/MCP-Altlast bei aktuell nur 2 Skills.
- **CFDs → echte Futures umstellen** (2026-09-03): zwei getrennte,
  unentschiedene Punkte — (a) "echtere" Daten, aber eigene Rollover-Logik +
  Neuvalidierung nötig; (b) eigene Futures-Challenges bei Prop-Firms als
  möglicher neuer Track.
- **OU-Modell-Scanner ggf. komplett auf Telegram umstellen** (2026-09-02):
  Website bleibt vorerst, nicht entschieden.
- **PDFs/Bücher bulk-einbinden** (2026-09-01): prüfen ob
  `paper_dropbox/`-Pipeline dafür wiederverwendbar ist.
- **TTP/IQ ORB-Exits laufen pro Konto unabhängig auseinander** (2026-09-02):
  kein Bug (beide folgen korrekt ihrer Regel), aber noch nicht bewertet ob
  Exits kontoübergreifend synchronisiert werden sollten.
- **Stocks-in-Play 5-Min-ORB als neue Asset-Klasse** (2026-09-01, Paper
  Zarattini/Barbon/Aziz 2024, siehe [[opening-range-breakout]]): braucht
  neue Datenquelle (breites US-Aktienuniversum) + eigene Selektionslogik —
  eigenständige Idee, kein Filter-Add-on.
- **Volles 42-Asset-Futures-Universum aus dem JPM-Spillover-Paper**
  (2026-09-09, siehe [[cross-asset-momentum-spillover]]): Commodities/
  Aktienindizes/US-Treasury-Futures über den aktuellen FX/Gold-Fokus
  hinaus -- bewusst zurückgestellt, kein Termin. FX-only-Teilmenge +
  Gold-Cross-Check laufen stattdessen jetzt als eigenes Project.
- **Agentisches Research-System + separater Self-Learning-Bot** (2026-09-07):
  Konzept steht (Kernentscheidungen geklärt — autonome Ideen-Findung,
  Hybrid ML/RL, Alpaca Paper-Trading, erst Agentensystem dann Lern-Bot),
  siehe [[agentisches-research-system-und-self-learning-bot]]. Bau
  frühestens in ein paar Wochen (Nutzerentscheid), aktuell nichts zu tun.

## Letzte Aktivität

_(Auszug — vollständiges Log in [CHANGELOG.md](CHANGELOG.md))_

- 2026-09-09 — FK Instant Funding: Paper-Bot auf die 2 noch nicht live
  geschalteten Beine (trend_pullback/gold_silver) reduziert, um doppelte
  Telegram-Meldungen mit der jetzt 7-beinigen live Bridge zu vermeiden.
  Details: CHANGELOG.
- 2026-09-09 — dukascopy-Hang entschärft: Slow-Pfad-Retry bei FK Instant
  Funding + Funded-Portfolio-Bridge von 6x/8s/90s auf die in beiden
  Fast-Lanes längst bewährten 3x/3s/20s verkürzt (Worst Case pro Bein
  ~9,7 Min. → ~66s, gehalten wird dabei der State-Lock) + FKs unbehandelten
  Lock-Absturz behoben (Fast-Lauf crashte ohne Log-Zeile, wenn der Slow-Lauf
  den Lock hielt — Funded fängt das seit jeher ab). Details: CHANGELOG.
- 2026-09-09 — FK Instant Funding: `LIVE_LEGS` um gold_asb/cls_practical/
  ctnl_continuation/ctnl_reversal erweitert (Nutzerentscheid, nach zwei
  weiteren sauberen `run_once_fast.py`-Testläufen). Damit sind 7 von 9
  Beinen live; trend_pullback/gold_silver bleiben bewusst DRY_RUN. Details:
  CHANGELOG.
- 2026-09-08 — FK Instant Funding: Fast/M5-Scan-Lane (`run_once_fast.py` +
  Scheduled Task `FKInstantFunding-MT5-Bridge-Fast`, 5 Min) + Terminal-
  Restart-Fix in `executor.py` nachgerüstet, nach Vergleich der drei
  Portfolio-Bridges beim Scan-/M5-Timing (Nutzerauftrag). `LIVE_LEGS`-
  Erweiterung (gold_asb/cls_practical/ctnl_continuation/ctnl_reversal)
  steht noch aus, wartet auf einen vollen Connect-Test außerhalb der
  Spread-Stunden-Pause. Details: CHANGELOG.
- 2026-09-08 — FK Instant Funding: `DRY_RUN=False` gesetzt (Nutzerauftrag),
  NY-Open ORB live auf echtem Geld. Second Brain: Git-Sync-Reparatur
  (lokal/GitHub 38 vs. 2 Commits auseinandergelaufen, Bridge-Watchdog-
  "Ausfall" war ein Fehlalarm), cls_practical-Cache-Bugfix einer parallelen
  Session eingespielt, neuer Fund: Funded-Portfolio-Bridge IPC-Timeouts auf
  allen 3 Konten. Details: CHANGELOG.
- 2026-09-07 — Data Lake: automatischer Live-Fallback bei Cold Start/
  haengender Ingestion gebaut (`with_live_fallback()`), beantwortet die
  seit 2026-09-04 offene Cold-Start-Frage. Details: CHANGELOG.
- 2026-09-06 — `data_lake/`-Paket committet + gepusht, Data-Lake-Pilot von
  Funded-Portfolio-Bridge auf EK-Portfolio-Bridge (gold_asb, cls_practical,
  ctnl_edge) und FKInstantFunding-MT5-Bridge (alle 6 Beine) erweitert —
  keine neue Ingestion noetig (liest denselben laufenden Lake), ein neuer
  Key (SILVER H4) ergaenzt. Jeder Pfad vor dem Umschalten gegen
  `source="live"` verifiziert; dabei echten tz-Bug in `legs/cls_practical/
  signal_source.py` gefunden und gefixt (identischer Bugtyp wie der am
  2026-09-01 fuer gold_asb behobene). Details: CHANGELOG.
- 2026-09-06 — Neuer Scheduled Task `Dashboard-Telegram-Digest`: schickt
  jeden Morgen 8:00 die offenen Punkte aus diesem Dashboard per Telegram
  (Nutzerwunsch). Details: CHANGELOG.
- 2026-09-04 — Second Brain: neuer Skill `handoff` (+ Inbox
  `knowledge/_handoff/`) für Session-Übergaben am Kontextfenster-Limit,
  aus dem "Everlast AI"-Clip übernommen (3 der 4 vorgeschlagenen Ideen
  bewusst verworfen/zurückgestellt, siehe `resources/second-brain-methodik.md`).
- 2026-09-04 — Data-Lake-Pilot gebaut + live geschaltet: Funded-Portfolio-
  Bridges 6 Beine lesen jetzt aus einem lokalen Parquet-Lake
  (`data_lake/`) statt live von Dukascopy/TradingView/yfinance. Neue
  Scheduled Tasks `DataLake-Ingest-Fast`/`-Slow`. Vollstaendig end-to-end
  verifiziert (Seed-Laeufe, `run_shared_scans()` direkt gegen die echte
  Config, kuenstlicher Stale-Test) — siehe CHANGELOG fuer Details. EK-
  Portfolio-Bridge/FK Instant Funding folgen erst nach Bewaehrung.
- 2026-09-04 — CTNL-eigener Kill-Switch (Stand-alone Cont+Rev-Drawdown
  gegen die Phase-6-P5-Schwelle) in EK-Portfolio/Challenge-Portfolio/FK
  Instant Funding nachgeruestet, nachdem er bei der Portfolio-Konsolidierung
  nicht automatisch mit uebernommen wurde — siehe CHANGELOG.
- 2026-09-03 (spät) — Bridge Error Monitor: dritte Lücke im heutigen OHLC-
  Validierungsfix geschlossen (`fetch_2y_yield_daily()` in
  `cls_practical/data.py`, siehe CHANGELOG). Zwei neue Echtgeld-Befunde auf
  EK-Portfolio-Bridge zur Bestätigung im Dashboard vermerkt: NASDAQ-Ticket
  262117522 scheitert wiederholt am Session-Ende-Exit, US30-Order erneut
  mit "Invalid stops" (derselbe, am 2026-09-02 als behoben dokumentierte
  Fehler) gescheitert.
- 2026-09-03 — Bridge Error Monitor: den am 2026-09-02 dokumentierten, aber
  nie tatsächlich umgesetzten "OHLC vor dem Cachen validieren"-Fix jetzt
  wirklich in `combined_strategy/data.py` + `cls_practical/data.py`
  ergänzt, nachdem derselbe `str`/`float`-Fehler heute erneut in drei
  Beinen gleichzeitig auftrat. Neue vage Fehlerzeile auf EK-Portfolio-
  Bridge zur Bestätigung im Dashboard vermerkt.
- 2026-09-03 — Funded-Portfolio-Bridge: redundante Scans behoben (6 Scans
  1x/Lauf statt 1x/Konto) + tvDatafeed-Pro-Login entfernt (TradingView-
  Captcha-Wall, seit 2026-09-01 taeglich hunderte Signin-Fehler). MT5 als
  Dukascopy-Ersatz geprueft und verworfen (Instrumenten-Abdeckung zu duenn).
- 2026-09-02 — Second Brain: 5 offene Clippings verarbeitet (CODE-Prozess) —
  3 Claude-Workflow-Videos als neue Einträge in
  `resources/second-brain-methodik.md`, 1 Trading-Video (Order Flow, nicht
  quant-übertragbar) als neue `resources/order-flow-trading.md`, 1 bestätigtes
  Duplikat. 4 Workflow-Verbesserungsideen daraus in DASHBOARD "Braucht deine
  Bestätigung" vermerkt. `Clippings/`-Ordner danach geleert.
- 2026-09-01 — Second Brain: Scope von `strategie-backlog-inventar.md`
  eingegrenzt (nur aktuell relevante Strategien + Filter mit echtem
  Mehrwert, kein Vollsweep über alle Ordner mehr), 5 echte Lücken bei
  laufenden/pausierten Bots identifiziert (`asian_range_breakout`,
  `cls_practical`, `btc_ema_cross`, `ek_portfolio`, OU-Modell). Dabei
  Task Scheduler + alle Live-Bridge-`DRY_RUN`-Flags gegen die Statustabelle
  geprüft — keine Abweichung gefunden.
- 2026-09-01 — EK-Portfolio: Echtgeld-Bugfix (Gold-ASB-Scan crashte seit
  11:30 bei jedem Lauf, tz-Vergleichsfehler) + Dukascopy-Retry in 3 Beinen
  nachgezogen. Verifiziert per fehlerfreiem 13-Bein-Lauf um 12:15.
- 2026-09-01 — Funded-Portfolio-Bridge: Scheduled Task angelegt (alle 15
  Min Mo–Fr) + 2 Bugs beim ersten automatischen Lauf gefunden/behoben
  (endlos wiederholte "verpasst"-Meldung, falscher `entry_price` im State).
- 2026-09-01 — Funded-Portfolio-Bridge (TTP/IQ Markets) auf `DRY_RUN=False`
  gestellt, erste 2 echten Orders platziert; OU-Modell/CTNL-Edge-MT5-Bridge
  sauber von den Zielkonten abgekoppelt.
- 2026-09-01 — 5 verwaiste MT5-Terminals geschlossen, nur die 2 aktiven blieben offen.
- 2026-09-01 — Challenge Portfolio: CTNL-Reversal-Kaskade gekappt + OU-Modell-Import-Fix (`69f9ca6`).
- 2026-09-01 — EK-Portfolio: CTNL-Reversal-Kaskade auf reales 3er-Limit gekappt (`c195924`).
- 2026-08-31 — FK Instant Funding: `scan_errors_today` auf lokalen Kalendertag umgestellt (`adc7d7c`).
- 2026-08-29 — Wochenend-/Spread-Stunden-Sperre auf EK-Portfolio + CTNL-Edge-FK-Paper ausgeweitet (`5fcf1da`).
- 2026-08-29 — FK Instant Funding: Wochenend-/Spread-Stunden-Sperre + UTC/Lokalzeit-Bug behoben (`79df9f3`).
- 2026-08-29 — FK Instant Funding: eigenes Telegram-Layout + gebündelte Nachrichten (`8f9a11a`).
- 2026-08-29 — FK Instant Funding: Gewichts-Optimierung + `CAPITAL_WEIGHT`-Umbau (`59ba4df`, `11f8979`).
