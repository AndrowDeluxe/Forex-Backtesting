# Dashboard

**Stand: 2026-09-13** _(wird bei jeder Session von Claude auf das aktuelle
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

0. **FK-ORB auf MT5-Bars: Beobachtung läuft, Phase 2 (Funded) wartet darauf.**
   Seit 2026-09-09 ~22:20 holt FKs ORB-Bein seine Bars direkt aus MT5
   (`orb_mt5_source.py`, Fallback auf den Lake-Weg eingebaut).
   **Log-Stand 2026-09-10 11:28: null Fallback-Warnungen** in
   `task_run.log` und `task_run_fast.log` — der MT5-Pfad trägt bisher
   durchgehend, Fast-Läufe brauchen ~8 Sekunden.
   **Update 2026-09-13: der erste echte Entry über den neuen Pfad ist da — und
   der Broker hat ihn abgelehnt.** 2026-09-11 16:03:08, `orb_sp500`
   SPX500.gbe, 25,3 Lots @ 7672,0, SL 7667,066270640961 → `retcode=10016
   "Invalid stops"`. Der Datenpfad hat also getragen, die Order-Ebene nicht.
   **Phase 2 (Funded) wartet damit nicht mehr auf Beobachtung, sondern auf
   diesen Fix** — siehe Offene Aufgaben. Vergleich der Datenquellen siehe
   [[bridge-infrastruktur-vergleich]].
   ⚠️ **ORB-Backtest/Kostenprobe läuft ab 2026-09-13 in einer PARALLELEN
   Session** (Nutzerentscheid) — nicht doppelt anfangen; hier nur die
   Bridge-/Order-Seite anfassen.
1. ~~`data_lake/`-Paket nie committet~~ — **committet + gepusht 2026-09-06**
   (`19e5b2c`) + im selben Zug auf EK-Portfolio-Bridge (gold_asb,
   cls_practical, ctnl_edge) und FKInstantFunding-MT5-Bridge (alle 6 Beine)
   erweitert (`f8db9f3`), inkl. Verifikation jedes Pfads gegen `source=
   "live"` und Fix eines dabei gefundenen echten tz-Bugs in cls_practical.
   Details: CHANGELOG. Push zunaechst durch den separaten Sync-Konflikt
   blockiert, nach dessen Merge durch eine parallele Session (siehe unten)
   sauber als Fast-Forward durchgegangen (`e592d4d..f8db9f3`).
2. ~~gold_asb: Historie-Cache greift nie~~ — **behoben 2026-09-06.**
   `stable_end_str` (Alt/Neu-Grenze) lief auf "gestern" (wandert täglich,
   verfehlte den Datums-Cache dadurch jeden Tag) → jetzt auf Monatsanfang
   stabilisiert (ändert sich nur 1x/Monat), "neues" Fenster deckt dafür den
   laufenden Monat ab (max. ~31 Tage, bleibt klein). Verifiziert: zwei
   Aufrufe lieferten identische 188 Zeilen, zweiter schneller. Voller
   Cache-Vorteil zeigt sich über die nächsten Tage.
3. **Manuelles Monatsjournal + Quant-System-Verschmelzung** (Nutzerwunsch
   2026-09-02): händisches Monatsjournal + Plan, wie manuelles Trading und
   das Quant-System sinnvoll verschmolzen werden — braucht zuerst ein
   klärendes Gespräch (Format, Kennzahlen). Noch nichts gebaut.
3. ~~M5-Scan-Frequenz für CTNL Continuation + NY-Open ORB~~ — **erledigt,
   live seit 2026-09-04.** Neue `data_lake`-Lane `"fast5"` + eigener
   Fast-Task, Cross-Prozess-Lock gegen Doppel-Ausführung. Nutzer hat
   Testlauf + beide Scheduled Tasks selbst verifiziert. Details: CHANGELOG.
4. ~~Funded-Portfolio-Bridge: redundante Scans vermeiden~~ — **erledigt
   2026-09-03.** MT5 als Datenquellen-Ersatz geprüft und verworfen (deckt
   nur 9 von ~30 gebrauchten Instrumenten ab). Stattdessen `run_once.py`
   umgebaut: 6 Scans laufen jetzt 1x pro Bridge-Lauf statt 1x pro Konto.
   Nebenfund: `tvDatafeed`-Pro-Login entfernt (TradingView-Captcha-Wall).
   Details: CHANGELOG.
5. ~~FKInstantFunding-MT5-Bridge: vollen Connect-Scan-Gates-Entry-Pfad nach
   Fast-Lane-/Terminal-Fix-Umbau beobachten, dann LIVE_LEGS erweitern~~ —
   **erledigt 2026-09-09.** Task Scheduler bestätigt (`LastTaskResult=0`,
   läuft sauber im 5-Min-Takt Mo–Fr); Root Cause des eigentlichen Auslösers
   (beide bisherigen ORB-Signale 07./08.09. vom stündlichen Takt verpasst)
   damit behoben. Ein zweiter Testlauf außerhalb der Spread-Stunden-Pause
   zeigte den vollen Connect-Scan-Gates-Durchlauf fehlerfrei (nur zufällig
   kein neues Signal) — auf dieser Basis hat der Nutzer entschieden, nicht
   erst auf einen echten Entry zu warten (Order-Versand-Code ist identisch
   zu dem der schon lebenden ORB-Beine). `LIVE_LEGS` jetzt erweitert um
   gold_asb/cls_practical/ctnl_continuation/ctnl_reversal. Noch offen: der
   erste echte Entry der 4 neuen Beine ist noch nicht beobachtet — bei
   Gelegenheit gegenlesen. Details: CHANGELOG.

---

## 📋 Offene Punkte (nach Priorität)

Zusammengeführt aus "Braucht deine Bestätigung" + "Offene Aufgaben" — nach
Priorität sortiert, erledigte Punkte pro Kategorie unten. Höchste Priorität:
offene Projekte mit konkretem nächstem Schritt (aktuell keins offen — der
gold_asb-Cache-Bug oben läuft über "Als Nächstes"). Danach: Bestätigungs-
Bedarf vor generischem Aufräumen.

### 🔍 Braucht deine Bestätigung

Punkte, bei denen etwas unklar/widersprüchlich ist oder eine Annahme von mir
noch nicht von dir bestätigt wurde. Erledigte Punkte werden entfernt, nicht
abgehakt-und-liegengelassen.

- **Eskalation zum Punkt direkt darunter: `bridge_status/snapshot.json` ist
  jetzt seit fast 3 Tagen eingefroren, nicht mehr nur seit >41h** (2026-09-18,
  automatischer Bridge-Monitor-Lauf). Letzter Commit auf die Datei ist
  weiterhin `e92c754` (`generated_at` unverändert `2026-09-16T00:01:25`) —
  seit dem vorigen Monitor-Lauf (2026-09-17, der den 41h-Ausfall erstmals
  gemeldet hat) ist ein weiterer voller Handelstag (Do 09-17) plus ein Teil
  von Fr 09-18 ohne einen einzigen neuen Snapshot-Commit vergangen. Damit ist
  dieser Monitor jetzt ununterbrochen seit ~3 Tagen blind für alle drei
  Live-Bridges (echtes Geld) — es gibt von hier aus keinerlei Sichtbarkeit,
  ob EK-Portfolio-Bridge, Funded-Portfolio-Bridge oder
  FKInstantFunding-MT5-Bridge in dieser Zeit normal weitergelaufen sind,
  Fehler hatten, oder ob der Rechner/Task Scheduler selbst steht. Gleiche
  offene Frage wie im Punkt darunter, nur mit deutlich längerer Dauer — bitte
  bei Gelegenheit einmal lokal prüfen, ob der Rechner läuft und ob
  `Bridge-Watchdog` selbst noch aktiv ist.

- **`bridge_status/snapshot.json` seit Mi 2026-09-16 00:01:25 Uhr nicht mehr
  aktualisiert — Bridge-Watchdog liefert seit >41h keinen neuen Stand, obwohl
  Mi/Do normale Handelstage sind (kein Wochenende)** (2026-09-17, automatischer
  Bridge-Monitor-Lauf). Letzter Commit auf `bridge_status/snapshot.json` ist
  `e92c754` (generated_at `2026-09-16T00:01:25`, +0300). Laut Soll-Takt
  (30-Min-Trigger Mo–Fr, siehe Statustabelle/Wochenend-Pause-Abschnitt unten)
  hätten seither ca. 80 weitere Snapshot-Commits kommen müssen; es kamen null
  — auch keine der sonst üblichen Parallel-Commits von anderen Mo–Fr-Tasks
  (`FK Instant Funding Bot: Snapshot`, `OU-Modell Scanner: Snapshot`), die am
  09-15 noch mehrfach pro Stunde eingingen. Von hier aus (kein Zugriff auf den
  Windows-Rechner) nicht unterscheidbar, welcher von mehreren früher schon
  aufgetretenen Fällen vorliegt: (a) Rechner/Task Scheduler seit Di-Nacht aus
  oder im Schlaf, (b) alle Scheduled Tasks laufen lokal weiter, aber der
  Git-Push scheitert erneut (exakt dieses Muster gab es schon einmal,
  2026-09-07/08, siehe der bereits aufgelöste Punkt weiter unten — der
  damalige Fix `Sync-AndPush`/`git_sync_push.ps1` sollte das eigentlich
  verhindern), oder (c) ein anderer, neuer Fehler in `watchdog.py` selbst.
  **Ohne aktuellen Snapshot ist dieser Monitor für den gesamten Zeitraum
  blind** — insbesondere lässt sich dadurch NICHT prüfen, ob der
  CLS-Practical-Fix (`b673a68`, siehe Punkt direkt darunter) auf den Live-
  Bridges inzwischen gegriffen hat, und es gibt keine Sichtbarkeit auf
  eventuelle Fehler/Trades der letzten 1,5 Tage auf allen drei Live-Bridges
  (echtes Geld). **Frage:** Läuft der Rechner? Falls ja, bitte einmal lokal
  `bridge_status/snapshot.json` und die Watchdog-Logs gegenchecken, ob dort
  frische lokale Daten stehen (dann wäre es wieder ein reines Push-Problem
  wie 2026-09-07/08) oder ob der Watchdog selbst steht.

- **CLS-Practical-Fix von heute Abend (Commit `b673a68`, 23:08:22 Uhr) scheint auf
  den Live-Bridges noch NICHT zu wirken — mehrere Zyklen danach weiterhin exakt
  derselbe Fehler** (2026-09-16, automatischer Bridge-Monitor-Lauf). Beobachtet im
  `bridge_status/snapshot.json`-Stand von 00:01 Uhr: auf allen drei
  Funded-Portfolio-Bridge-Konten (TTP Konto 1 **echtes Geld**, TTP Konto 2 Demo, IQ
  Markets) läuft `CLS-Practical-Scan fehlgeschlagen: cannot reindex on an axis with
  duplicate labels` NACH dem Fix-Push unverändert weiter — Events um 23:13, 23:28,
  23:43 und 23:58 Uhr, wortgleich mit den Fehlern von VOR dem Fix (22:38/22:43/22:58
  Uhr). FKInstantFunding-MT5-Bridge zeigt denselben Fehlertext noch einmal um
  23:14 Uhr (6 Min. nach dem Push). Der Fix selbst
  (`cls_practical/rates.py::compute_daily_rate_score_2y`, `de_chg`/`us_chg` jetzt mit
  `keep="last"` dedupliziert) ist im Repo committet + gepusht und laut dem
  CHANGELOG-Eintrag von heute lokal reproduziert und verifiziert — nur eben nicht
  gegen den echten Live-Lauf, das stand dort schon als offen.
  **Bestbegründung, nicht bewiesen:** entweder zieht der laufende Bridge-Prozess
  Code-Änderungen nicht bei jedem Lauf frisch aus diesem Repo (anders als
  `challenge_portfolio/paper_bot.py`, das laut `CLAUDE.md` live importiert wird) und
  braucht einen manuellen Pull, oder der laufende Python-Prozess hat
  `cls_practical.rates` bereits im Speicher und bräuchte einen Neustart, damit die
  neue Modulversion greift. Von hier aus (kein Zugriff auf die laufenden
  Bridge-Prozesse) nicht weiter zu klären.
  **Fragen:** (1) Zieht Funded-Portfolio-Bridge/FKInstantFunding-MT5-Bridge
  `cls_practical/` bei jedem Lauf frisch aus dem Repo, oder liegt dort eine eigene
  Kopie, die manuell nachgezogen werden muss? (2) Falls frisch gezogen: braucht der
  laufende Task/Prozess einen manuellen Neustart, damit ein Fix wie dieser greift?
  Bis das geklärt ist, würde ich beim nächsten Monitor-Lauf einfach gegenprüfen, ob
  der Fehler im dann aktuellen Snapshot weiterhin auftritt.

- **🔴 Zwei von drei Paper-Zwillingen laufen nicht — wieder scharfstellen?**
  (2026-09-14, deine Entscheidung). Stand:
  `ek_portfolio/paper_bot.py` → Task **Disabled seit 2026-08-31**;
  `challenge_portfolio/paper_bot.py` → **nie ein Task angelegt**, `trades: {}`,
  also kein einziger simulierter Trade seit Bestehen;
  `fk_instant_funding/paper_bot.py` → läuft stündlich, 24 Trades.
  **Warum das mehr wiegt als es klingt:** ohne laufenden Zwilling lässt sich
  nicht unterscheiden, ob ein schwaches Live-Ergebnis von der *Strategie* oder
  von der *Ausführung* kommt — und genau das ist gerade die offene Frage, weil
  Funded nur 20 % und FK 0 % der Signale platziert. Der einzige echte
  Vergleich, den es gibt, zeigt das Problem in Reinform: FK-Paper steht bei
  98.981,60 (−1,02 %, 24 Trades), das FK-Live-Konto bei 100.159,75 (+0,16 %,
  **0 Trades**). Das Live-Plus kommt daher, dass nichts ausgeführt wurde — es
  sagt nichts über die Strategie.
  **Besonderheit Challenge:** `challenge_portfolio/paper_bot.py` hat als
  Simulation nie gearbeitet, wird aber zur Laufzeit von der Echtgeld-Bridge
  importiert (Scans, `LEG_RISK_PCT`, `ORB_EXIT_CFG_BY_INSTRUMENT`). Ein Commit
  daran wirkt sofort auf echtes Geld, ohne dass je ein Paper-Lauf ihn
  gegengeprüft hätte.
  **ENTSCHIEDEN 2026-09-14: Paper-Zwillinge bleiben aus.** Stattdessen soll
  das Soll aus einem **Backtest des jeweiligen Bridge-Portfolios über denselben
  Kalenderzeitraum** kommen, der dann wöchentlich/monatlich gegen die echten
  Live-Zahlen gestellt wird (Nutzerentscheid). Begründung des Nutzers: liefert
  denselben Maßstab, ohne zwei zusätzliche Dauer-Tasks — und deckt zusätzlich
  die Signale ab, die eine Bridge gar nicht erst gesehen hat. Umsetzung als
  eigener Punkt weiter unten.
  Details: [[bein-matrix-ist-soll-paper]] · [[systemlandkarte]].

- **Zwei Annahmen aus dem Funded-Fix von heute** (2026-09-13).
  (1) **Deckelwert für den neuen aggregierten Offenes-Risiko-Kill-Switch:** ich
  habe ihn an die Anbieter-Regel gebunden statt FKIFs fixe 5 % zu kopieren —
  die Hälfte des jeweiligen Drawdown-Caps, also TTP 3,5 % ($3.465) und IQ 3,0 %
  ($2.970). Begründung: bei 6–7 % Gesamt-Drawdown-Cap wären 5 % offenes Risiko
  fast der ganze Puffer. Real belegen alle Beine zusammen ~2 %, der Deckel
  bremst im Normalbetrieb also nicht. Meine Herleitung, nicht deine Vorgabe.
  (2) **Der Rates-Multiplikator erhöht das cls_practical-Risiko.** Er ist ein
  VERSTÄRKER, kein Dämpfer (gemessen über die letzten 15 Trades: Median 1,75,
  Max 3,06, 53 % der Trades ≠ 1,0). Live heißt das: $165 → bis $505 pro Trade
  (0,17 % → 0,51 % der Equity). Das ist genau das, was der Paper-Bot modelliert
  — aber es hebt die Risikosenkung, die die Parallel-Session dem Bein am
  2026-09-11 verpasst hat (`LEG_RISK_PCT` 0,015 → 0,01), im Ergebnis teilweise
  wieder auf. Falls die Senkung als ENDGÜLTIGES Live-Risiko gemeint war und
  nicht als Basiswert, müssen wir eins von beidem nachziehen.

- ~~**EK: Stop neu verankern oder auf absoluten Signal-SL umstellen?**~~ — **umgestellt 2026-09-11 auf deinen Auftrag.** Ursprünglicher Punkt:
  (2026-09-11, deine Entscheidung). EK macht es heute anders als die beiden
  anderen Bridges: `stop_price = entry_price_now - direction * sl_distance`.
  Das verhindert die Hebel-Aufblähung strukturell — **kostet aber Ergebnis**.
  Gemessen auf denselben Signalen, EK-Risiko, 0,50 Pips Kosten:

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
- **EK läuft bei 42,6 % Margin für EINE normale Position** (2026-09-11
  gemessen; Funded zum Vergleich: 7,7 %). Folge der Kalibrierung vom
  2026-09-10, keine Fehlfunktion — aber bei 8 Beinen und Tickmill-Hebel 1:30
  können zwei bis drei gleichzeitig offene Positionen die Margin ausreizen.
  Der neue Margin-Deckel steht dort deshalb auf 80 % statt 20 % und kann
  strukturell wenig ausrichten. Bewusst so gelassen, aber du solltest es wissen.

- ~~**EK-Portfolio-Bridge: ORB rechnet auf 5 Stunden alten Bars**~~ —
  **behoben 2026-09-10, Rest am 2026-09-13 mit NEIN abgeschlossen.** Die
  offene Frage war, ob EKs alte ORB-Trades (entstanden auf 5 Std. alten Bars,
  also unter falschen Voraussetzungen) rückwirkend ausgewertet werden sollen
  — **deine Entscheidung 2026-09-13: nein, nicht weiter verfolgen.** Sie
  taugen damit schlicht nicht als Leistungsnachweis; wer später ORB-Zahlen
  braucht, rechnet ab 2026-09-10 neu. Voller Befund + Fix: CHANGELOG
  2026-09-09/10 (Ursprungstext hier gekürzt 2026-09-13).

- **🔴 Kurztakt-Tasks fallen wiederkehrend für 1–2 Stunden aus — und das hat
  am 2026-09-11 nachweislich Schaden angerichtet** (hochgezogen 2026-09-13
  aus der Wochenauswertung; vorher als Einzelfall vom 2026-09-10 vermerkt und
  bewusst liegen gelassen "falls es sich häuft" — es häuft sich).
  **Vier Vorfälle bekannt:** `DataLake-Ingest-Fast5` 2026-09-07 (~45 Min.),
  `EK-Portfolio-Bridge-Fast` 2026-09-10 11:12–11:27, und am 2026-09-11 zwei
  Fenster (**00:14–02:29** und **13:16–14:38**), in denen EKs 2-Minuten-Lane
  UND `DataLake-Ingest-Fast`/`-Fast5` gemeinsam schwiegen; der Ingest kam um
  14:38:36 mit einem Lauf außerhalb des Rasters zurück (Nachhol-Lauf des Task
  Schedulers). **Belegte Folge:** genau in diesen zwei Fenstern lief der Lake
  trocken, alle drei Bridges fielen auf Live-dukascopy zurück und sammelten
  dort ihre kompletten Tages-Scan-Fehler ein (Funded Fast 09-11: 21/72/45
  Fehler in 00/01/02 Uhr + 9/69 in 13/14 Uhr, **null in allen übrigen
  Stunden** — dieselbe Verteilung bei FK). Kein Strategie- oder Code-Fehler,
  aber der Grund, warum du "einige Scan-Fehler" siehst.
  **Ursache weiter unbestätigt** (Energieverwaltung/Modern Standby bleibt die
  naheliegende Vermutung, ist aber nicht belegt — EKs 15-Minuten-Lane lief in
  denselben Fenstern weiter, was gegen reines Schlafen spricht).
  Nächster Schritt wäre, das Task-Scheduler-Verhalten der Kurztakt-Tasks
  gezielt zu instrumentieren. Priorität: Hoch — sag Bescheid, dann nehme ich
  es mir vor.

- ~~**Kostenmessung EUR/USD: vier Annahmen brauchen Bestätigung**~~ —
  **abgeschlossen 2026-09-13.** (a) Messfenster 08:00–12:30 Berlin,
  (b) alle Kostenblöcke gebündelt in `spread_bps`, (c) `risk_pct=0,25 %`:
  stehen unverändert — die darauf gebauten Entscheidungen (Pip-Boden,
  Risikosenkung, R-Detektor) sind umgesetzt und verifiziert.
  (d) **Tickmill/EK-Kosten per Vorwärts-Sampling echt messen: deine
  Entscheidung 2026-09-13 — NEIN, vorerst nicht.** Folge, bewusst
  akzeptiert: EKs Kennzahlen bleiben auf der *geschätzten* Annahme von
  0,50 Pips und sind damit optimistischer angesetzt als die gemessenen
  Challenge-Zahlen (2,05 Pips) — EK-Zahlen also nicht mit Funded/FK
  vergleichen, solange das so ist. Herleitung: `resources/broker-kostenmodell-eurusd.md`.

- **EK-Portfolio-Bridge: `CAPITAL_WEIGHT` (1/8) ist definiert, wird aber
  NIRGENDS im Code verwendet** (2026-09-09 gefunden). `config.py:57` schreibt
  die Formel `risk_dollars = CAPITAL_WEIGHT * LEG_RISK_PCT * equity` explizit
  fest (identisch zu `ek_portfolio/paper_bot.py`, das sie auch so rechnet) —
  die Bridge uebergibt aber ueberall nur `config.LEG_RISK_PCT[leg]` an
  `calc_lot_size()`. Live verifiziert im Log: OU-Modell rechnet
  `risk_amount=33.67 EUR` bei Equity 3367.90 = **exakt 1,0 %**, also die
  volle `LEG_RISK_PCT`-Stufe ohne die 1/8-Verduennung. Jedes Bein handelt
  damit ~8x groesser als dokumentiert. Gebremst wird das nur noch von
  `MAX_TOTAL_RISK_PCT = 8 %` — was erklaert, warum das Konto praktisch
  dauerhaft am Deckel klebt (heute durchgehend ~247–256 von ~269 EUR) und
  Beine sich gegenseitig aushungern: **der CLS-Practical-Entry vom 2026-09-09
  10:30 (EURUSD, den alle 3 Challenge-Konten genommen haben) wurde auf EK
  genau deswegen uebersprungen** ("offen 251.32 + neu 50.94 > Deckel 272.36").
  Wer zuerst laeuft, bekommt das Risiko — das ist kein gewolltes Portfolio-
  Verhalten.
  **BACKTEST-ANTWORT (2026-09-09, auf deinen Auftrag):** eindeutig ein Bug,
  keine Absicht. Ich habe die `ek_v2_realistic_final.json`-Studie aus den
  Bein-Kurven in `portfolio_construction/results/legs/` rekonstruiert (5 von
  6 Beinen reproduzieren die dortigen `per_leg_standalone`-Zahlen exakt, btc
  minimal ab durch die Renditen-Skalierung) und dann beide Risikologiken
  gegeneinander gerechnet:
  | Variante | CAGR | Max Drawdown |
  |---|---|---|
  | mit 1/6-Kapitalverduennung (= Studie, = `paper_bot.py`) | 75,2 % | **-16,1 %** |
  | Studie `riskopt_20dd` zum Abgleich | 76,8 % | **-19,2 %** |
  | **ohne Verduennung (= was die Live-Bridge tut)** | 1199 % | **-73,7 %** |
  Die 8 % je Bein sind also die Risikostufe INNERHALB einer Kapitalscheibe,
  nicht auf das ganze Konto. Ohne Verduennung liegt der Max Drawdown bei
  -73,7 % statt der validierten -19,2 %, gegen die auch der 20 %-Kill-Switch
  ausgelegt wurde. **Nach deinem eigenen Kriterium ("wenn die Werte deutlich
  schlechter werden muessen wir das Risiko anpassen") ist damit klar: Risiko
  anpassen, BEVOR am Deckel etwas passiert.**
  ⚠️ **Deshalb den aggregierten Deckel NICHT auf 30 % erhoeht.** Genau dieser
  8 %-Deckel ist aktuell die einzige Bremse, die das 8x-Risiko im Zaum haelt
  (er tut unfreiwillig die Arbeit der fehlenden Verduennung). Von 8 % auf
  30 % zu gehen, solange die Verduennung fehlt, wuerde die Bremse loesen
  statt das Risiko zu ordnen. Braucht deine ausdrueckliche Bestaetigung —
  siehe Vorschlag unten.
  **Offen:** mit 1/8-Verduennung faellt bei 3,4k Equity fast jedes Bein unter
  das Broker-Mindestlot (ctnl_continuation 2,10 EUR statt 16,80). Verduennung
  einbauen erfordert deshalb im selben Zug eine Neukalibrierung von
  `LEG_RISK_PCT` auf die echte Kontogroesse (Phase-6-Arbeit, eigene Session).

- **Challenge/Funded OU-Bein: der Entry-Filter haengt an einem simulierten
  Buch, das von den echten Positionen abgedriftet ist** (2026-09-09).
  Warum heute kein OU-Trade auf Challenge kam, obwohl EK APD genommen hat:
  `challenge_portfolio/paper_bot.py::_scan_ou_modell()` laesst
  `simulate_bracket_portfolio()` ueber 450 Tage durchlaufen und uebernimmt
  dessen internen `max_total_risk_pct = 5 %`-Deckel. Instrumentierter Lauf
  (2026-09-09): das SIMULIERTE S&P-Buch haelt 4 offene Positionen (RL ab
  08-27, D ab 08-28, EXPE + SYY ab 09-04) mit 4626.5 von 5727.7 Risiko —
  ein 5. Slot braucht 1145.5 und passt um ~45 nicht mehr rein. Blockiert
  wurden dadurch am 09-08 und 09-09 **alle** Kandidaten (APD, AIG, AMGN,
  DHI, LEN, SPG, TROW, UPS). Der Haken: **RL und D wurden live nie eroeffnet**
  (stehen in keinem `bridge_state_*.json`) — sie stammen aus der Zeit vor dem
  `include_open_positions=True`-Fix (2026-09-02) und belegen jetzt 2 der
  ~4 nutzbaren Risiko-Slots, bis sie simuliert per max_holding auslaufen
  (~09-16/09-17). Das Bein ist also nicht "still", sondern durch Phantom-
  Positionen blockiert.
  **Entscheidung 2026-09-13: NEIN** — der Sim-Risikodeckel bleibt vorerst,
  wie er ist (kein Umbau auf die echten offenen Positionen). Die beiden
  Phantom-Positionen (RL, D) laufen am 09-16/09-17 simuliert von selbst aus,
  danach gibt das Bein seine Slots ohne Eingriff wieder frei. Bleibt als
  bekannte Schwäche stehen: solange der Deckel gegen das simulierte Buch
  rechnet, kann dasselbe Muster jederzeit wiederkommen.

- **Restlaufzeit-Gate: eine Design-Entscheidung + eine offene Frage**
  (2026-09-09, Details CHANGELOG). Die beiden Latenz-Vorschläge von gestern
  Abend hast du freigegeben und sie sind umgesetzt (Gate in allen 3
  Portfolio-Bridges, Task-Offsets verschoben). Zwei Punkte bleiben:
  (1) **Ausgenommen habe ich `ou_modell` und `btc_ema_cross`** — reine
  Tagessignale, ein M5-SL-Berührungscheck wäre dort sinnlos. Das war meine
  Einschätzung, nicht deine Ansage.
  (2) **Der Gate hätte den CLS-Trade von heute NICHT verhindert.** Auf dem
  Broker-Feed lag das 08:25-UTC-Low 0,1 Pip ÜBER dem SL; der Stop fiel erst
  16 Sekunden nach dem Entry (siehe den parallel entstandenen
  Kostenmodell-Eintrag im CHANGELOG). Das Signal war zum Entry-Zeitpunkt also
  wirklich noch am Leben — der Gate verhält sich korrekt, greift aber bei
  dieser Verlustursache nicht. **Erledigt 2026-09-11:** die strengere
  Variante wurde als R-Detektor (`MAX_CONSUMED_R_FOR_ENTRY = 0.50`) in allen
  drei Bridges gebaut; der zugehörige Ideen-Inbox-Punkt ist damit weg.
  (3) **Ungefragt mitgemacht:** `Funded-Portfolio-Bridge/executor.py` loggte
  bei `order_send()==None` weiterhin nur „None". FK hat das heute früh
  bekommen, EK parallel über `core/order_send.py` — Funded war die letzte
  Bridge ohne. Genau dieser blinde Fleck hat heute auf zwei Bridges je Stunden
  Diagnose gekostet, deshalb habe ich `mt5.last_error()` + Request dort
  nachgezogen. Rein diagnostisch, ändert nichts daran, ob oder was gesendet
  wird — sag Bescheid, falls du das zurückgedreht haben willst.
- **dukascopy-Hang-Fix: eine Plan-Abweichung + Verifikation steht noch aus**
  (2026-09-09, Details CHANGELOG). Der freigegebene Plan sah zusätzlich vor,
  dieselben engeren Retry-Werte auch in `fk_instant_funding/paper_bot.py`s
  eigenem Paper-Loop zu setzen (der die Telegram-Meldung aus deinem
  Screenshot erzeugt). **Habe ich beim Umsetzen bewusst weggelassen**: dort
  läuft `source="live"`, also ein echter dukascopy-Netzwerkabruf — ein
  20s-Timeout würde dort legitime, nur langsame Abrufe abwürgen und die
  Meldungen eher häufiger machen statt seltener. Die Begründung für die
  engeren Werte gilt nur bei `source="lake"` (Normalfall = Millisekunden-
  Parquet-Read). Heißt konkret: **die Meldungen aus deinem Screenshot
  (Paper-Bot) werden vorerst weiter auftreten** — die Änderung wirkt nur auf
  die beiden Echtgeld-Bridges. Sag Bescheid, falls du die Paper-Meldungen
  trotzdem stummer haben willst (dann eher über eine Dedup-/Sammelmeldung
  als über kürzere Timeouts). Zweitens: verifiziert ist bisher nur die
  Syntax + die `_retry()`-Signatur — ob der Fix im echten Lauf greift,
  zeigt erst der nächste reguläre Scheduled-Task-Lauf beider Bridges
  (danach `task_run.log`/`task_run_fast.log` gegenlesen: keine
  unbehandelten Tracebacks mehr, im Fehlerfall die neue "...wird fuer
  diesen Zyklus uebersprungen"-Zeile).
- **Wiederholende-Fehlermeldung-Fix: Design-Entscheidungen waren eigenes
  Judgement** (2026-09-08, Details CHANGELOG). (1) Dedup ist 1x/TAG pro
  Signal/Order, nicht 1x fuer immer — reagiert am nächsten Tag wieder frisch.
  (2) Bei fehlgeschlagenem EXIT wird nur die Telegram-Meldung gedämpft, der
  Schliessversuch selbst läuft weiter jeden Zyklus (kein stilles Aufgeben).
  (3) Dabei einen zusätzlichen echten Bug gefunden+mitbehoben: ein
  fehlgeschlagener Exit setzte die Position bisher trotzdem auf "closed",
  obwohl sie real offen blieb (betraf FK Instant Funding + Funded-Portfolio-
  Bridge). Nur `py_compile` + isolierte Funktionstests, kein echter Live-Lauf
  mit einem echten wiederholten Fehler abgewartet.
- ~~`bridge_status/snapshot.json` seit Montag 17:01 Uhr (CEST) nicht mehr
  aktualisiert -- Bridge-Watchdog liefert seit ~18h/~30h keinen neuen
  Stand~~ — **war ein Fehlalarm, aufgeklärt 2026-09-08 (heutige Session):
  kein Bot-/Rechner-Ausfall, sondern reines Git-Push-Problem.** Der lokale
  Rechner hatte durchgehend weiterlaufende, aktuelle Snapshots (lokale
  `bridge_status/snapshot.json`/Logs zeigten beim Gegencheck Läufe bis
  wenige Minuten vor der Prüfung) — nur die Pushes zu GitHub schlugen seit
  2026-09-07 ~17:xx durchgehend fehl ("fetch first", weil die
  Auto-Commit-Skripte vor dem Push nicht pullen), nachdem eine parallele
  Cloud-Session zwischenzeitlich selbst auf `main` gepusht hatte. Dadurch
  sah GitHub/Streamlit einen eingefrorenen Stand, obwohl lokal alles lief.
  Jetzt zusammengeführt + gepusht (dieser Merge), siehe CHANGELOG
  2026-09-08 "Git-Sync-Reparatur". **Root Cause inzwischen ebenfalls behoben
  (2026-09-09, Commit `a34cb8a`)**: neue gemeinsame
  `scripts/lib/git_sync_push.ps1` (`Sync-AndPush`) fetcht+merged jetzt vor
  jedem Push, eingebunden in alle 11 `scripts/*_task.ps1` + analog in
  `C:\Users\andre\Bridge-Watchdog\watchdog.py`. Bei einem echten
  Merge-Konflikt wird der Merge abgebrochen und der Push für diesen Lauf
  ausgelassen (statt in einem kaputten Merge-Zustand zu landen). Verifiziert:
  PowerShell-Parser + `py_compile` sauber; der praktische Beweis kommt mit
  dem nächsten Push-Zyklus der geplanten Tasks.
- ~~EK-Portfolio-Bridge/ou_modell: Order fuer EXPE scheiterte am 2026-09-07
  wiederholt mit "Market closed"~~ — **wahrscheinliche Ursache gefunden
  2026-09-09** (volle Log-Auswertung `EK-Portfolio-Bridge/logs/task_run.log`).
  Um 15:54:27 Uhr, kurz VOR der ersten fehlgeschlagenen Order, meldete der
  eigene Deviation-Schutz (`legs/ou_modell/executor.py:192`)
  `entry_deviation_too_large` mit `deviation=1.0` fuer EXPE — eine Abweichung
  von exakt 100% zwischen Zielpreis (297.51) und `symbol_info_tick().ask`
  deutet auf `ask=0` hin, also KEINEN Live-Kurs fuer dieses Symbol zu dem
  Zeitpunkt (kein Rundungsfehler, ein "kein Kurs verfuegbar"-Symptom). 6
  Minuten spaeter (ab 16:00 Uhr) kam wieder ein Tick-Wert zurueck, der
  Deviation-Check liess die Order durch, aber `order_send()` wurde vom
  Broker mit `retcode=10018` (`TRADE_RETCODE_MARKET_CLOSED`) abgelehnt — ein
  echter Broker-seitiger Ablehnungscode, kein Verbindungs-/Timeout-Fehler.
  Zusammengenommen spricht das dafuer: der generische
  `_nyse_is_open()`-Handelszeiten-Gate war korrekt offen, aber die
  tatsaechliche, symbolspezifische Handelssession fuer EXPE bei Tickmill war
  zu dem Zeitpunkt noch nicht aktiv (verzoegerter Session-Start fuer dieses
  eine CFD, oder ein Symbol-seitiger Halt) — passt auch dazu, dass Zielpreis
  UND SL/TP ueber alle ~15 Wiederholungen (15:15-17:42 Uhr) identisch blieben
  (festgehaltenes Tagessignal, kein Refresh). Nicht 100% zweifelsfrei (kein
  Broker-Session-Log einsehbar), aber deutlich konkreter als der bisherige
  Stand. Kein Code-Bug, kein Handlungsbedarf — falls es sich wiederholt,
  waere Tickmills tatsaechliche Handelszeit fuer US-Aktien-CFDs (ggf.
  abweichend von den generischen NYSE-Kernzeiten) der naechste Schritt.
- ~~EK-Portfolio-Bridge: unformatiertes Log-Fragment in `recent_events`
  (Rohtext eines f-Strings statt ausgewerteter Werte)~~ — **geklaert
  2026-09-09, kein Bug.** Volle Einzel-Run-Logs
  (`logs/run_20260907_151503.log` Zeile 274ff, `run_20260907_164504.log`
  Zeile 500ff) zeigen: das ist ein ganz normaler Python-Traceback (`ERROR
  run_once: cls_practical: unerwarteter Fehler`), bei dem Python 3.14 die
  Quellzeile des `raise LakeStaleDataError(...)`-Statements woertlich mit
  ausgibt (Standard-Traceback-Format seit Python 3.11) — erklaert die "rohe
  f-String"-Optik vollstaendig. Ablauf beide Male identisch: Lake-Daten zu
  alt -> `with_live_fallback()` (erst am selben Tag, 09-07, gebaut) greift
  korrekt und versucht Live-Fetch -> Live-Fetch scheitert SEINERSEITS am
  bereits bekannten dukascopy-Bug (`_stream()` Zeile 219/242, `TypeError:
  '>' not supported between instances of 'str' and 'float'`, identisch fuer
  beide Vorkommen: EURUSD_M5 um 15:21 und USDCHF_M15 um 16:53) -> keine
  weitere Fallback-Ebene mehr -> Exception propagiert bis `_run_leg()` hoch
  und wird dort mit vollem Traceback geloggt (kein Telegram-Spam,
  Bridge-Status blieb "ok", wie schon vermutet). Kein neuer Bug — nur eine
  bisher nicht explizit beobachtete Kombination zweier bekannter Dinge
  (Lake-Staleness + dukascopy-Bug). Idee fuer spaeter (kein Auftrag):
  `with_live_fallback()` koennte einen fehlschlagenden Live-Fallback selbst
  auch abfangen und als "no_signal" statt als harten Leg-Fehler behandeln —
  aktuell nicht gebaut.
- ~~Funded-Portfolio-Bridge: wiederholte `IPC timeout`-Verbindungsfehler auf
  allen 3 MT5-Konten, seit ca. 11:52 Uhr 09-08 andauernd~~ — **war zeitlich
  begrenzt, seit 2026-09-08 12:34 Uhr durchgehend stabil** (geprueft
  2026-09-09, inkl. sauberer Laeufe den gesamten heutigen Vormittag).
  Log-Auswertung: Fehler traten durchgehend von 09:52 bis 12:24 Uhr auf
  09-08 auf (alle 3 Konten pro Zyklus gemeinsam betroffen), endeten
  schlagartig ab 12:34 Uhr. Prozessliste zeigt: der Terminal-Prozess "MT5
  Terminal - GoldFKBot" (IQ-Markets/BeyondIQCapital-Konto 16054) wurde exakt
  in diesem Fenster (12:19:36 Uhr) neu gestartet — passt zum ersten wieder
  erfolgreichen Connect fuer genau dieses Konto um 12:24 Uhr. Wahr-
  scheinlichste Ursache: `_terminal_running()` in `executor.py` prueft nur,
  OB ein Terminal-Prozess mit passendem Pfad LAEUFT (PowerShell-
  Prozessliste), nicht ob er noch reagiert — ein haengender, aber technisch
  noch laufender GoldFKBot-Prozess waere von `_ensure_terminal_running()`
  nie automatisch neugestartet worden. Da `run_once.py` alle 3 Konten
  sequenziell in EINEM Python-Prozess mit gemeinsamem MT5-IPC-Client
  abarbeitet, wuerde ein haengender Connect fuer ein Konto plausibel auch
  die beiden anderen im selben Zyklus mitreissen — passt zum beobachteten
  Muster (immer alle 3 gemeinsam betroffen). Nicht zweifelsfrei bewiesen
  (kein Log vom haengenden Prozess selbst), aber die zeitliche Deckung ist
  sehr stark. Terminals nicht angefasst, aktuell kein Handlungsbedarf, da
  stabil. Idee fuer spaeter (kein Auftrag): `_terminal_running()` um einen
  echten Health-Check erweitern statt nur Prozess-Existenz zu pruefen.
- ~~Second-Brain-Lint (wöchentliche Routine) lief heute ins Leere:
  `knowledge/scripts/lint.py` + `.claude/skills/second-brain-lint/SKILL.md`
  fehlen im Repo~~ — **Korrektur 2026-09-09: falscher Befund, beide Dateien
  waren die ganze Zeit da.** `git ls-files`/`git log` bestaetigen: beide
  wurden bereits am 2026-09-07 committet (`af96c0e`, "Second Brain:
  Handoff-Skill, Edge-Card-Workflow, PARA-Notizen, Tooling") und sind auf
  `origin/main` gepusht — der Eintrag vom 2026-09-07 beruhte auf einem
  fehlerhaften `git log`-Check der damaligen Session (Detail nicht mehr
  rekonstruierbar). Lint jetzt tatsaechlich gelaufen (erster echter
  Durchlauf seit 2026-09-01): 8 tote Wikilinks (1 davon falsch-positiv,
  `[[slug]]` in CHANGELOG.md:1008 ist literaler Beispieltext, kein echter
  Link), 6 verwaiste Seiten, 0 veraltete Statustabellen-Daten, 14
  unverarbeitete Clippings. Details/Einsortierung: CHANGELOG + unten.
- **Cross-System-Link auf eine Claude-Memory-Datei** (seit 2026-09-09,
  weiterhin offen — Lint 2026-09-14 zeigt denselben Fall unverändert:
  `resources/cross-asset-momentum-spillover.md:86`,
  `[[cls-practical-strategy-state]]` — zeigt auf die Memory-Notiz
  `cls_practical_strategy_state.md`, nicht auf eine `knowledge/`-Datei).
  Fuer Obsidian technisch ein toter Link, obwohl der referenzierte Inhalt
  existiert — reine Konventionsfrage (z.B. eigene Zitierform statt
  `[[...]]` fuer Memory-Referenzen), siehe Skill `second-brain-lint`.
  Wie soll auf Memory-Inhalte aus `knowledge/`-Notizen kuenftig verwiesen
  werden?
  **Neue Variante beim Lint 2026-09-14:** `areas/bridge-infrastruktur-
  vergleich.md:83` verlinkt `[[second-brain-lint]]` — zeigt auf den Skill
  unter `.claude/skills/second-brain-lint/SKILL.md`, ebenfalls ausserhalb
  von `knowledge/`. Gleiches Muster wie oben (Inhalt existiert, Ziel liegt
  nur ausserhalb der PARA-Struktur) — vermutlich dieselbe
  Konventionsfrage, nicht separat entscheiden.
- ~~`DataLake-Ingest-Fast5` + `FKInstantFunding-MT5-Bridge` (stündlich):
  auffällige Lücke ~14:31-15:0x Uhr~~ — **bewusst verworfen 2026-09-09
  (Nutzerentscheid)**: einmaliger ~45-Minuten-Ausreisser am 2026-09-07,
  seither nicht wiederholt, ungeprüfte Akku-/Energieverwaltungs-Vermutung
  bleibt unverifiziert. Keine weitere Untersuchung — bei erneutem Auftreten
  neu aufgreifen.
- ~~FKInstantFunding-MT5-Bridge: echter Order-Executor gebaut, wartet auf
  `DRY_RUN=False`~~ — **`DRY_RUN=False` gesetzt 2026-09-08** (expliziter
  Nutzerauftrag "Setze dry run False, damit ist orb jetzt live"). NY-Open
  ORB (SP500/US30/NASDAQ) ist damit LIVE auf echtem Geld, alle anderen 6
  Beine bleiben ueber `LIVE_LEGS` weiterhin nur geplant/geloggt. Details/
  Vorgeschichte: CHANGELOG 2026-09-07+08. Weiterhin ungetestet bis zum ersten
  echten Entry: die MT5-Live-Positions-Iteration der Offene-Risiko-Checks
  (aktuell 0 offene Positionen) — beim ersten echten Trade gegenlesen, ob
  Sizing/SL/Telegram-Meldung wie erwartet aussehen.
- ~~Funded-Portfolio-Bridge: TTP Konto 2 (Demo, #504072729) verbindet seit
  Wochenschluss nicht mehr~~ — **behoben 2026-09-07** (gefunden beim
  Log-Check nach dem Data-Lake-Fallback-Umbau, gemeinsam mit Nutzer geloest).
  Ursprünglicher Prozess-Neustart (Task Manager) half nicht wirklich weiter
  (Prozess lief laut Startzeit unveraendert weiter) — eigentliche Root
  Cause erst beim Versuch, einen komplett frischen, dedizierten
  Terminal-Ordner anzulegen (Nutzerwunsch, Kopie von "TTP MT5 Terminal
  Konto1neu" nach "...Konto2neu"): der frisch kopierte, noch nie gestartete
  Terminal scheiterte dabei zunaechst mit `IPC timeout`/`IPC send failed`
  statt "Authorization failed" -- `executor.py::_connect_once()` liess
  `mt5.initialize()` einen fehlenden Terminal-Prozess selbst starten, aber
  OHNE `/portable`-Flag, wodurch der neue Prozess mit den anderen
  gleichzeitig laufenden MT5-Terminals auf der Maschine kollidierte
  (identisches Fehlerbild + identische Ursache wie der 2026-08-28-Vorfall,
  der `FKInstantFunding-MT5-Bridge` bereits einen `_ensure_terminal_running()`
  -Schutz eingebaut hat -- Funded-Portfolio-Bridge hatte den bisher NICHT
  uebernommen). Fix: identisches `_ensure_terminal_running()`-Muster
  (Powershell-Prozess-Check + `/portable`-Vorstart) jetzt auch in
  `Funded-Portfolio-Bridge/executor.py::_connect_once()` + `test_connection.py`
  ergaenzt -- gilt automatisch fuer alle 3 Konten, da `run_once.py` dieselbe
  `executor.connect()` wiederverwendet. Verifiziert: `test_connection.py`
  verbindet jetzt sauber mit allen 3 Konten inkl. Konto 2 (Equity
  $100.102,87). Offen: `AutoTrading` zeigt bei Konto 2 noch `False` (bei den
  anderen beiden `True`) — reiner Terminal-GUI-Schalter ("Algo Trading"-
  Button), muss einmalig manuell im neuen Terminal-Fenster aktiviert werden,
  sonst koennte dieses Konto spaeter keine echten Orders senden. Alter,
  verwaister Ordner "TTP MT5 Terminal - Konto2" (Prozess lief seit Samstag
  durch) kann geschlossen werden, config.py zeigt seit dem Fix nicht mehr
  darauf.
- ~~Lokaler `main` 64 vor / 1 hinter `origin/main`~~ — **gemergt 2026-09-06**
  (Nutzer-OK): der eine fremde Commit (`7616951`) betraf nur `DASHBOARD.md`
  und stammte noch von der alten, unredesignten Dashboard-Struktur (Sept 4)
  — Merge-Konflikt manuell aufgelöst, alte Struktur verworfen (längst durch
  das Sept-6-Redesign abgelöst), aber der einzige darin noch NICHT
  anderswo erfasste Punkt unten neu aufgenommen (siehe nächster Punkt).
- ~~Funded-Portfolio-Bridge: Data-Lake-Cold-Start-Lücke vom 2026-09-04,
  Frage nie beantwortet~~ — **gebaut 2026-09-07** (Nutzerauftrag "Baue den
  Fallback"): neue `data_lake.reader.with_live_fallback()` faengt
  `LakeMissingDataError`/`LakeStaleDataError` pro Fetch-Aufruf ab und weicht
  fuer genau diesen Aufruf auf die echte Live-Fetch-Funktion aus, statt den
  Scan-Zyklus hart scheitern zu lassen. Angewendet auf alle Lake-faehigen
  Beine in allen 3 Bridges (Funded-Portfolio-Bridge, EK-Portfolio-Bridge,
  FKInstantFunding-MT5-Bridge) — bewusst NICHT auf OU-Modell (eigene,
  gewollte Skip-pro-Ticker-Logik, ein Fallback dort wuerde bei einem echten
  Cold Start den yfinance-Rate-Limit-Ansturm reproduzieren, den die eigene
  Slow-Lane vermeiden soll). Jeder Fallback loggt eine Warnung, spammt aber
  kein Telegram. Verifiziert (isolierter Wrapper-Test + unveraenderte
  Zeilenzahlen im gesunden Lake-Fall). Details: CHANGELOG.
- ~~5-Min-Fast-Trigger: 3 Engineering-Entscheidungen unbestätigt~~ —
  **bestätigt 2026-09-06** (Nutzerauftrag, echt nachgeprüft statt pauschal
  abgenickt): M15-Zusatz für SP500/US30/NASDAQ (Begründung Opening-Range-
  Timing schlüssig), `account_state_lock()` (Code gelesen — identische
  `os.O_CREAT|O_EXCL`-Technik, die unabhängig davon am selben Tag für
  `data_lake/manifest.py`s analoges Problem gebaut wurde, starkes Indiz für
  den richtigen Ansatz), Retry-Parameter 3x/3s/20s im Fast-Pfad direkt im
  Code verifiziert (`run_once_fast.py`). Alle drei sinnvoll.
- ~~Funded-Portfolio-Bridge: kein "Signal zu alt"-Schutz beim Echt-Entry~~
  — **Korrektur 2026-09-06**: war bereits längst umgesetzt
  (`MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY=60` in `_process_leg()`, gilt generisch
  für alle Beine, per Code-Check bestätigt) — der gegenteilige "noch
  offen"-Eintrag hier war ein stehengebliebener Duplikat-Stand vom selben
  Tag, jetzt entfernt.
- ~~2 neue Funded-Portfolio-Bridge-Konten (TTP #504069845, IQ 15514)
  verbanden nicht~~ — **Korrektur 2026-09-06**: war bereits am 2026-09-03
  gelöst (Status-Tabelle unten zeigt seitdem "alle 4 verbunden"), der
  "Fix in Arbeit"-Eintrag hier war stehengeblieben. Tatsächliche Ursache:
  "DLL-Importe zulassen" (eigene Einstellung, getrennt von AutoTrading) +
  ein strukturell defekter Terminal-Ordner → Konten auf funktionierende
  Ordner umgehängt.
- ~~Merge-Konflikt in diesem Abschnitt + CHANGELOG~~ — nachgeprüft
  2026-09-04, keine Widersprüche/Duplikate gefunden.
- ~~Rechner-/Task-Lücke ~9h über Nacht~~ — Ursache: Windows Modern Standby
  über AC-Display-Idle-Timeout, nicht "Rechner aus". Cache-Validierung +
  WakeToRun + neuer Bridge-Watchdog als Absicherung, 2026-09-02.
- ~~Telegram-Logik uneinheitlich zwischen den drei Portfolios~~ —
  `fk_instant_funding` auf gleiche Queue-Infrastruktur gehoben, 2026-09-02.
- ~~`fk_instant_funding/paper_bot.py`: letzte ORB-Kopie auf altem Stand~~ —
  nachgezogen 2026-09-02, alle 3 aktiven ORB-Träger jetzt gleich.
- ~~Funded-Portfolio-Bridge OU-Modell-Bein meldete nie offene Signale~~ —
  Root Cause (offene Positionen fielen unter den Tisch) + NYSE-Gate
  gefixt, 2026-09-02.
- ~~EK-Portfolio-Bridge: NASDAQ-Ticket 262117522 hing am Session-Ende-Exit~~
  — geschlossen 2026-09-04 (Comment-Feld für Tickmill zu lang, gekappt).
- ~~EK-Portfolio-Bridge: US30 "Invalid stops"~~ — zweiter Bug gefunden
  2026-09-04 (TP auf falscher Seite bei LONG), SL-Prüfung aufs TP erweitert.
- ~~2 neue Funded-Portfolio-Bridge-Konten waren bereits anderweitig
  vergeben~~ — bewusste Konsolidierung (Nutzerentscheid 2026-09-02).
- ~~`dukascopy_python` hing komplett fest, ohne Timeout~~ — neue
  `_call_with_timeout()` (90s) um jeden Retry, 2026-09-02, alle 3 Bridges.
- ~~`OU-Modell-ScannerHourly` verwaist~~ — bewusst weiterlaufen lassen
  (Streamlit-Seite braucht ihn), 2026-09-02.

### Offene Aufgaben

- **🔴 EK: `cls_practical` hat noch NIE eine Order gesendet — 104 Scan-Fehler
  seit 2026-08-31** (2026-09-14 bei der Bein-Zählung gefunden). Immer dieselbe
  Kette: Lake-Eintrag gilt als veraltet → Fallback auf Live-Dukascopy → Hang →
  90-s-Timeout → Bein fällt für den Zyklus aus. Fehlerverteilung: 51× am
  09-03, 26× am 09-04, 10× am 09-07, 6× am 09-11. Das Bein ist damit auf EK
  faktisch nicht im Portfolio, obwohl es dort mit 0,55 % Risiko/Trade
  eingeplant ist. Hängt am Frischefenster-Punkt direkt darunter.
  Priorität: Hoch. Details: [[bein-matrix-ist-soll-paper]].
- **Frischefenster des Data Lake (35 Min.) passt nicht zur 15-Min.-Kadenz**
  (2026-09-14, Vorschlag von mir — **nicht umgesetzt**, Priorität mittel).
  `data_lake/manifest.py::_STALENESS_MINUTES["fast"] = 35` verzeiht bei
  15-Minuten-Ingest genau **einen** ausgefallenen Lauf; danach gilt alles als
  veraltet. Gezählt: 774 Lake-Fallbacks bei EK, >1.400 bei Funded, 728 bei FK
  — **ausnahmslos** `LakeStaleDataError`, kein einziges „Datensatz fehlt". Der
  Ingest selbst ist gesund (585 von 587 Fast-Läufen sauber beendet); Ingest
  und Bridge setzen gemeinsam aus. Zwei Stellschrauben: (a) Fenster an die
  Kadenz koppeln (z. B. 2,5 × Ingest-Intervall statt fix 35), (b) den
  Live-Fallback bei Dukascopy hart deckeln — 90 s Hang für ein Bein, das
  ohnehin nur alle 15 Min. scannt, ist der falsche Tausch. Ergänzt den
  Kurztakt-Task-Befund vom 2026-09-13 um die Auslegungsfrage dahinter.
- **Statustabelle braucht eine Spalte „letzter echter Entry"** (2026-09-14,
  Priorität mittel). Die Modus-Spalte („LIVE — echtes Geld") hat fünf Tage
  lang verdeckt, dass FK Instant Funding seit `DRY_RUN=False` am 2026-09-08
  **null** Orders ausgeführt hat. „Läuft" und „handelt" sind nicht dasselbe,
  und nur eines davon ist im Dashboard sichtbar.
- **EKs `config.py`-Kommentar zur Kapitalscheibe widerspricht dem eigenen Log**
  (2026-09-14, Priorität niedrig, reines Aufräumen). Der Kommentar zu
  `CAPITAL_WEIGHT = 1/8` begründet sie mit „OU-Modell zählt mit (eigenes
  echtes Konto, **keine Order hier**)" — die Bridge hat 9 OU-Orders gesendet
  (D, FAST, SPG, SYY, AXP, ADI, EXPE, APD, AMGN), nachdem
  `OU-Modell-MT5-Bridge` deaktiviert wurde. Nur ein Kommentar, aber er trägt
  die Herleitung einer Risikokonstante — und genau so ein Kommentar hat am
  2026-09-09 schon einmal wochenlang etwas Falsches behauptet.
- **Live-Gegenprobe der neuen IQ-Gewichtung steht noch aus** (2026-09-13,
  Priorität mittel — erst beim nächsten planmäßigen Lauf mit echten Signalen
  prüfbar, also frühestens Montag). Seit heute fährt das IQ-Konto 5 Beine
  @ 1/3 statt 6 @ 1/6 (siehe `CHANGELOG.md`). Statisch ist alles verifiziert
  (Import, Risiko je Bein gegen beide Deckel). **Offen ist der Live-Beleg:**
  da alle drei Konten denselben Signalstrom sehen, muss die IQ-Lotgröße für
  ein und dasselbe Signal **exakt doppelt** so groß sein wie die TTP-Lotgröße,
  und es darf **kein** OU-Entry-Versuch mehr für IQ im Log auftauchen. Beides
  in `Funded-Portfolio-Bridge/logs/task_run.log` nachsehen, sobald ein Signal
  auf mehreren Konten gelaufen ist.
- **🔴 FK Instant Funding: ORB-Order vom 2026-09-11 vom Broker abgelehnt
  (`Invalid stops`)** (2026-09-13 in der Wochenauswertung gefunden). Der
  einzige echte ORB-Entry-Versuch der Woche, auf Echtgeld:
  `2026-09-11 16:03:08`, SPX500.gbe, LONG, 25,3 Lots @ 7672,0,
  **SL 7667,066270640961**, `retcode=10016`. Zwei Kandidaten, beide ungeprüft
  (braucht offene Märkte + laufendes Terminal, also frühestens Montag):
  (a) **SL nicht auf Tickgröße gerundet** — der Wert geht mit 12 Dezimalstellen
  an einen Index-CFD raus; (b) **Stopabstand zu klein** — 4,93 Punkte auf 7672
  (0,064 %) könnte unter dem Mindestabstand des Brokers liegen.
  Gegen (b) spricht nichts, gegen (a) auch nicht — eine `symbol_info`-Abfrage
  (`digits`, `trade_stops_level`) klärt beides in einer Minute.
  **Wichtig:** die vorhandene Schutzprüfung in EKs ORB-Executor greift hier
  nicht — sie prüft nur, ob SL/TP auf der *richtigen Seite* des Kurses liegen,
  nicht Rundung und nicht Mindestabstand. Priorität: Hoch.
- **🔴 FK Instant Funding: zwei Echtgeld-Entries am 2026-09-09 sind mit
  `order_send()=None` gescheitert — Verdacht Kommentarlänge** (2026-09-13
  gefunden). `10:30:16 cls_practical EURUSD.gbe` und
  `17:20:13 ctnl_continuation XAUUSD.gbe`, beide ohne Retcode. Das eigene
  SL-Sicherheitsnetz war es nicht (das loggt eine eigene Zeile, die fehlt).
  **Auffällig:** `run_once.py:484` kappt den Kommentar auf **31** Zeichen,
  das bekannte Broker-Limit liegt aber bei **16** (siehe CHANGELOG 2026-09-04
  und den EK-Fund vom 2026-09-09). `FKIF cls_practical` = 18 Zeichen,
  `FKIF ctnl_continuation` = 22 → beide über 16, beide scheiterten;
  `FKIF orb_sp500` = 14 → kam bis zu einem echten Retcode durch. Passt exakt.
  **Bedeutung, falls der Verdacht stimmt: die am 2026-09-09 freigeschalteten
  Beine (gold_asb, cls_practical, ctnl_continuation, ctnl_reversal) können auf
  FK derzeit gar nicht einsteigen** — jeder Versuch stirbt still an der
  Kommentarlänge. Belegen lässt sich das jetzt leicht: die verbesserte
  `last_error()`-Ausgabe ist seit 2026-09-09 im Code, sie fehlte nur zum
  Zeitpunkt dieser beiden Fehlschläge. Priorität: Hoch.
- **🔴 ORB handelt auf der Funded-Bridge praktisch nicht: 2 von 24 Signalen
  platziert** (2026-09-13 beim Bein-Audit gefunden). Über alle drei Konten:
  `orb_nasdaq` 0/22, `orb_sp500` 0/13, `orb_us30` 2/7. Der Grund steht wörtlich
  im Log: *„war bereits offen UND geschlossen (stop), bevor diese Bridge es je
  gesehen hat"*. Die Re-Simulation löst den Trade auf, bevor der erste Scan ihn
  sieht — es trifft also systematisch die schnellen Verlierer. Das ist KEIN
  Vorteil: die Live-Performance des Beins ist dadurch nicht mehr mit dem
  Backtest vergleichbar, und faktisch läuft die getestete Strategie nicht.
  **Ergänzt 2026-09-13 aus der Wochenauswertung (zweite Session, gleiche
  Ursache):** auf FK gilt dasselbe — 6 ORB-Signale im September, **0** Entries.
  Und es ist nicht ORB-exklusiv: `cls_practical` (09-07, 09-08) und
  `ctnl_continuation` (09-08) wurden genauso verpasst, bei ORB ist es nur die
  Regel statt der Ausnahme. Das ist zusammen die Erklärung für die
  Nutzerbeobachtung "wenige Entries".
  Nicht angefasst — das ist eine Strategie-/Timing-Entscheidung, keine
  Bugfix-Frage. ⚠️ Inhaltlich gehört es in die **parallel laufende
  ORB-Kostenprobe-Session** (Stopabstand/Entry-Verzögerung), nicht hier
  doppelt anfangen.
- ~~**OU-Modell platziert auf dem IQ-Konto nie: 0 von 7 Signalen**
  (2026-09-13)~~ — **erledigt am 2026-09-13.** Ursache geklärt: IQ Markets/
  BeyondIQCapital bietet **gar keine Einzelaktien** an (Nutzerinfo); die Ticker
  stehen zwar formal in der Symbolliste und lassen sich per `symbol_select`
  wählen, liefern aber nie einen Kurs (48x `kein Live-Kurs fuer ou_modell
  (AMGN)` im Log, ask/bid bleiben 0). Die zweite der beiden vorgeschlagenen
  Optionen ist umgesetzt: **OU für IQ bewusst abgeschaltet**, und das frei
  werdende Kapital auf die verbleibenden 5 Beine verteilt (Kapitalanteil
  1/6 → 1/3, Nutzerentscheid). Auf den beiden TTP-Konten bleibt OU unverändert.
  Siehe `CHANGELOG.md` 2026-09-13 und
  `scripts/research_challenge_iq_no_ou.py`.
- **Data Lake wird häufig zu alt und fällt auf Live-Fetch zurück** (2026-09-13).
  Häufigste Fälle über die Log-Historie: `SP500_M15` 281x, `EURUSD_M5` 264x,
  `GOLD_H1` 197x, `SP500_M5` 170x. Jeder Fallback ist ein Live-Dukascopy-Abruf
  — genau die Instabilität, für die der Lake gebaut wurde, und die Ursache der
  6 `cls_practical`-Timeouts auf EK am 2026-09-11. Ingest-Takt vs.
  Freshness-Cutoffs prüfen.
  **Zusammenhang (2026-09-13, zweite Session):** ein großer Teil dieser
  Fallbacks hat keine Cutoff-Ursache, sondern eine Ausfall-Ursache — siehe den
  Kurztakt-Task-Punkt unter "Braucht deine Bestätigung": wenn der Ingest
  1–2 Stunden gar nicht läuft, ist jeder Key danach zwangsläufig zu alt. Die
  beiden Punkte am besten gemeinsam angehen.

- **CLS-Bein auf Bewährung — Abbruchkriterium fehlt noch** (2026-09-11).
  Der Umbau ist umgesetzt und verifiziert (siehe `CHANGELOG.md` 2026-09-11
  und `projects/cls-practical-kostenvalidierung.md` Befund 7): regelkonform
  mit großem Abstand (MaxDD 1,66 % = 24 % des TTP-Budgets, Hebel max 5,7x
  statt 58,8x), Edge statistisch real (P(Ø R<0) 2,16 %, OOS +0,31 über
  IS +0,17). **Aber CAGR nur 0,78 %** — für ein Challenge-Konto mit
  +10 %-Ziel zu wenig, um seinen Sechstel-Anteil beizutragen.
  Offen: (a) ein konkretes Abbruchkriterium festlegen (nach wie vielen
  Trades / bis wann muss das Bein was liefern?), (b) **Calmar der anderen
  fünf Beine erheben** — ohne den Vergleich ist nicht entscheidbar, ob 0,47
  im Portfolio schwach oder normal ist. Priorität: Mittel.
- **Hebel-/Mindestabstand-Schutz: für CLS gebaut, für die übrigen Beine
  weiter offen** (gefunden 2026-09-09, Stand nachgezogen 2026-09-13).
  Gebaut am 2026-09-11: Margin-Deckel über `order_calc_margin()` (Funded/FK
  20 %, EK 80 %) — der greift bein-übergreifend — sowie Pip-Boden und
  R-Detektor, die **nur im CLS-Pfad** hängen. Weiter ohne Schutz: jedes
  andere Bein kann bei knappem Stopabstand beliebig große Lots ziehen,
  begrenzt nur von `min(lots, info.volume_max)` und dem Margin-Deckel; die
  Abweichungsprüfung `MAX_OU_MODELL_ENTRY_DEVIATION_PCT` gibt es nur für
  `ou_modell`. `CLS-Practical-Bridge` ist hier nicht mehr relevant (seit
  2026-09-11 als stillgelegt markiert). Priorität: Hoch — der ORB-Befund vom
  2026-09-11 unten zeigt denselben Mechanismus auf einem anderen Bein.
- **Fill-Rücklesepfad greift auf TTP nicht** (2026-09-09 gefunden).
  `Funded-Portfolio-Bridge/executor.py` speichert `entry_price: 0.0` (weder
  `result.price` noch `positions_get(ticket=…)` lieferten einen Preis); auf
  IQ funktioniert derselbe Pfad. Ohne echten Fill sind TTP-Trades
  nachträglich nicht auditierbar — die Slippage-Messung musste deshalb über
  `history_orders_get()` gehen. Priorität: Niedrig-Mittel.

**Mittel**
- **14 unverarbeitete Clippings** in `knowledge/Clippings/` (Stand
  2026-09-14-Lint, unveraendert seit 2026-09-09) — u.a. Edge-Genesis/-Decay,
  Risk-Factor-Investing, Sektor-Rotation, "Six Repos One System", "How
  system works" — noch nicht durch den CODE-Prozess.
- ~~Second-Brain/Dashboard-Struktur: Feedback nach ein paar Tagen
  einholen~~ — erhalten 2026-09-06: Nutzer sehr zufrieden mit dem neuen
  Workflow, Dashboard passt gut rein. Redesign (Prioritäten-Sortierung,
  kürzere Texte, Status-Tabellen-Split) heute umgesetzt.
- ~~5 unverarbeitete Clippings~~ — verarbeitet 2026-09-02, Ordner geleert.
- ~~EK-Portfolio-Bridge: Spread-Stunden-Pause (23:00)~~ — bewusst
  zurückgestellt 2026-09-01 (0% historische Relevanz, noch nicht lohnend
  genug) — nicht erneut vorschlagen ohne neuen Trigger.
- ~~EK-Portfolio-Bridge/NY-Open-ORB: "Invalid stops"~~ — behoben
  2026-09-02.

**Niedrig**
- `knowledge/`-Altlasten (Lint 2026-09-14, vorher 2026-09-09): tote
  Wikilinks (`[[cls-practical]]`, `[[gap-fade]]`, `[[execution-overlay]]`,
  je 2 Vorkommen, unveraendert) + 7 verwaiste Seiten (vorher 6, neu:
  `areas/paper-bot-zu-live-bridge.md`), meist unkritisch. Details:
  Lint-Output/CHANGELOG.
- **Isolierter toter Wikilink** `areas/paper-bot-zu-live-bridge.md:86` ->
  `[[risiko-kalibrierung-methodik]]` (Lint 2026-09-14, einziges
  Vorkommen) — referenziertes Konzept (Risiko-Kalibrierungs-Methodik)
  existiert noch nicht als eigene Notiz. Nur ein Vorkommen, daher
  Aufraeum-Fall, kein Entscheidungspunkt.

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld** (btc/ou_modell weiterhin direkt Dukascopy/yfinance; gold_asb/cls_practical/ctnl x2 jetzt `source="lake"`) | Ready (alle 15 Min, Mo–Fr)      | 2026-09-13      |
| EK-Portfolio-Bridge-Fast                                | Tickmill Live (55918977, geteiltes Terminal)                                             | **LIVE — echtes Geld** (3 MT5-native Beine: ORB/Gold-Silber/Trend-Pullback, kein Dukascopy)  | Ready (alle 2 Min, Mo–Fr)       | 2026-09-13      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | **LIVE — echtes Geld** (7 Beine via `LIVE_LEGS`: orb_sp500/us30/nasdaq + gold_asb/cls_practical/ctnl_continuation/ctnl_reversal seit 09-09; trend_pullback/gold_silver bleiben geplant/geloggt) | Ready (stündlich, Mo–Fr)        | 2026-09-13      |
| FKInstantFunding-MT5-Bridge-Fast                        | BeyondIQCapital (17764, geteiltes Terminal)                                              | **LIVE — echtes Geld** (ctnl_continuation + orb_sp500/us30/nasdaq + cls_practical, `source="lake"`, analog Funded-Fast) | Ready (alle 5 Min, Mo–Fr)       | 2026-09-13      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram, **nur noch trend_pullback/gold_silver** (die anderen 7 Beine laufen live über die Bridge, seit 09-09 hier entfernt) | Ready (stündlich, Mo–Fr)        | 2026-09-13      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner + Telegram (3x täglich: 15:35/18:35/21:35)                                           | Ready (Mo–Fr, US-Handelszeiten) | 2026-09-02      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator (seit 09-15: Zeitlimit 4h statt 1h, Vollständigkeitsprüfung + 3x Wiederholung alle 4h bei unvollständigem Lauf) | Ready (So 18:00 — läuft am Wochenende bewusst weiter) | 2026-09-15      |
| Bridge-Watchdog                                         | — (nur Log-Frische, kein Order-Bezug)                                                    | Heartbeat-Alarm + Status-Snapshot ins Repo                                                   | Ready (alle 30 Min, Mo–Fr)      | 2026-09-13      |
| Funded-Portfolio-Bridge (TTP 6 Beine @1/6, IQ 5 Beine @1/3) | TTP Konto 2 (504072729) + TTP Konto 1 (504069845) + BeyondIQCapital (16054) — **alle 3 verbunden** (IQ 15514 am 2026-09-07 entfernt) | **LIVE — DRY_RUN=False** (alle 6 Beine `source="lake"`; **seit 09-13 kontospezifisch: IQ ohne `ou_modell`, Kapitalanteil 1/3 statt 1/6 — IQ handelt keine Aktien**; IPC-Timeouts 09-08 09:52-12:24 Uhr, seither stabil, siehe 🔍 Bestätigung) | Ready (alle 15 Min, Mo–Fr)      | 2026-09-13      |
| Funded-Portfolio-Bridge-Fast                            | Gleiche 3 Konten (geteilte Terminals)                                                    | **LIVE — DRY_RUN=False** (ctnl_continuation + orb_sp500/us30/nasdaq + cls_practical, `source="lake"`) | Ready (alle 5 Min, Mo–Fr)       | 2026-09-13      |
| DataLake-Ingest-Fast                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt `data_lake_store/` für Funded-Portfolio-Bridge (19 Keys, 15-Min-Kadenz)                | Ready (alle 15 Min, Mo–Fr)      | 2026-09-13      |
| DataLake-Ingest-Fast5                                   | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt 8 M5/M15-Timing-kritische Keys für ctnl_continuation/orb/cls_practical (EURUSD M5 seit 2026-09-07) | Ready (alle 5 Min, Mo–Fr)       | 2026-09-13      |
| DataLake-Ingest-Slow                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt OU-Modell-Universum (~59 Ticker) via yfinance                                          | Ready (stündlich, Mo–Fr)        | 2026-09-13      |
| Dashboard-Telegram-Digest (neu)                         | — (nur Lesezugriff auf DASHBOARD.md, kein Order-Bezug)                                   | Schickt offene Punkte aus DASHBOARD.md per Telegram                                          | Ready (täglich 8:00, auch Sa/So — bewusst) | 2026-09-13      |

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

_Letzter Lint-Check (tote Wikilinks, veraltete Daten, Widersprüche,
verwaiste Seiten, unverarbeitete Clippings): **2026-09-14** (planmaessiger
woechentlicher Lauf). Ergebnis: 0 veraltete Statustabellen-Daten, 7
verwaiste Seiten (vorher 6, siehe "Offene Aufgaben"), 13 tote Wikilinks
(davon 3 Selbstverweise im Dashboard-Text + 1 literaler Beispieltext in
CHANGELOG.md als falsch-positiv rausgefiltert; von den verbleibenden echten
Funden: 2 bekannte Cross-System-Links auf Inhalte ausserhalb von
`knowledge/` — Memory-Notiz + neu ein Skill-Verweis, siehe "🔍 Braucht deine
Bestätigung" — plus 1 neuer isolierter toter Link und die bereits bekannten
`[[cls-practical]]`/`[[gap-fade]]`/`[[execution-overlay]]`-Faelle), 14
unverarbeitete Clippings (unveraendert seit 2026-09-09, siehe "Offene
Aufgaben"). Widersprüche (c) weiterhin nur stichprobenartig, nicht
vollstaendig manuell durchgegangen._

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
