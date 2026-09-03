# Dashboard

**Stand: 2026-09-03** _(wird bei jeder Session von Claude auf das aktuelle
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

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld**                                                                       | Ready (alle 15 Min, Mo–Fr)      | 2026-09-02      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | DRY_RUN                                                                                      | Ready (stündlich)               | 2026-09-02      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram                                                                             | Ready (stündlich)               | 2026-09-01      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner                                                                                      | Ready (Mo–Fr, US-Handelszeiten) | 2026-09-01      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator                                                                             | Ready                           | 2026-09-02      |
| **Bridge-Watchdog**                                     | — (nur Log-Frische, kein Order-Bezug)                                                    | Heartbeat-Alarm + Status-Snapshot ins Repo                                                   | Ready (alle 30 Min)             | 2026-09-02      |
| **Funded-Portfolio-Bridge** (TTP+IQ Markets, 6 Beine)   | TTP Konto 2 (504072729) + BeyondIQCapital (16054) + **neu: TTP Konto 1 (504069845, echtes Geld) + BeyondIQCapital (15514)** — die zwei neuen verbinden erst seit 2026-09-03 12:37, noch kein einziger Entry darauf (siehe unten) | **LIVE — DRY_RUN=False**                                                                     | Ready (alle 15 Min, Mo–Fr)      | 2026-09-03      |
| Challenge Portfolio (Paper-Bot, `challenge_portfolio/`) | — (reine Simulation)                                                                     | Paper-Bot fertig entwickelt                                                                  | Noch kein Task angelegt         | 2026-09-01      |
| BTC-EMA-Cross-Bridge/-Scan                              | Binance                                                                                  | LIVE (war), aktuell pausiert                                                                 | **Disabled**                    | 2026-09-01      |
| CLS-Practical-Bridge/-Scan                              | —                                                                                        | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| CTNL-Edge-FK-Paper                                      | —                                                                                        | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| CTNL-Edge-MT5-Bridge                                    | BeyondIQCapital (16054)                                                                  | **abgelöst durch Funded-Portfolio-Bridge**, Konto/Terminal jetzt dort live                   | Disabled                        | 2026-09-01      |
| Gold-ASB-Scan / GoldASB-MT5-Bridge                      | BeyondIQCapital (16054)                                                                  | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat               | TTP Konto1 (Konto 2 komplett aus `ACCOUNTS` entfernt, jetzt bei Funded-Portfolio-Bridge) | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| EK-Portfolio-Paper                                      | —                                                                                        | pausiert                                                                                     | Disabled                        | 2026-09-01      |

Live-Status aller drei Portfolio-Bridges jetzt auch als Streamlit-Seiten
(„Portfolio-Bridges" in der Sidebar) — lesen `bridge_status/snapshot.json`,
das der Bridge-Watchdog alle 30 Min. committet.

_Letzter Lint-Check (tote Wikilinks, veraltete Daten, Widersprüche,
verwaiste Seiten, unverarbeitete Clippings): 2026-09-01, `knowledge/scripts/lint.py`
um Clippings-Check erweitert (siehe Skill `second-brain-lint`). Ergebnis: 0
veraltete Statustabellen-Daten, 8 verwaiste Seiten, mehrere tote Wikilinks,
**5 unverarbeitete Clippings** (Details unten). Widersprüche (c) nicht
vollständig manuell durchgegangen, nur stichprobenartig._

## 🔍 Braucht deine Bestätigung

Punkte, bei denen etwas unklar/widersprüchlich ist oder eine Annahme von mir
noch nicht von dir bestätigt wurde. Erledigte Punkte werden entfernt, nicht
abgehakt-und-liegengelassen.

- **Keine OU-Entries auf den beiden neuen Konten (TTP Konto 1 / 504069845, IQ
  15514) — sollen Alt-Signale nachgezogen werden?** Befund 2026-09-03 (rein aus
  der `bridge_status/snapshot.json`-Historie, der Bridge-Code liegt ausserhalb
  des Repos und war von hier aus nicht einsehbar):
  1. **Bis 12:04 heute lief auf beiden neuen Konten gar nichts** — jeder Lauf
     seit 2026-09-02 19:27 endete mit `mt5.initialize() fehlgeschlagen:
     (-10005, 'IPC timeout')`, ab 12:04 mit `(-6, 'Terminal: Authorization
     failed')`. Erste erfolgreiche Verbindung: **2026-09-03 12:37:03** (beide
     Konten, Equity-Zeilen seitdem in jedem Snapshot). Das war die im CHANGELOG
     als offen vermerkte Terminal-/AutoTrading-Baustelle; sie ist damit
     erledigt, aber niemand hat es bisher irgendwo festgehalten.
  2. **Seit 12:37 verbinden beide sauber, haben aber trotzdem nichts
     gehandelt.** Der bisher einzige OU-Entry der Bridge (`2026-09-03 15:42:39
     [TTP] ENTRY ou_modell (FAST) FAST BUY lots=40.0 risk=$166.79`) ging NUR auf
     TTP Konto 2. Auf den beiden neuen Konten steht zu diesem Lauf weder ein
     Entry noch eine Fehlerzeile — sie waren zu genau diesem Zeitpunkt
     verbunden (gleiche 15:42:39-Equity-Zeile).
  3. **Wahrscheinlichste Ursache (Annahme, nicht im Code verifiziert): das
     `account_start`-Gating** aus `run_once.py`/`bridge_state_<id>.json`
     ("verhindert faelschliches Nacheroeffnen von Alt-Signalen beim ersten
     Lauf", siehe [[challenge-portfolio-ttp-icapital]]). Das FAST-Signal traegt
     `scan_date=2026-09-02`, liegt also VOR dem `account_start` der neuen Konten
     (= erster erfolgreicher Lauf, 2026-09-03 12:37) und wird darum bewusst
     nicht nachgeholt. Auf Konto 2 (`account_start` vom 2026-09-01) greift das
     Gate nicht — genau das erklaert den Unterschied.
  4. **Nebeneffekt, falls das Gate wirklich Zeitstempel gegen Zeitstempel
     vergleicht**: OU-Signale tragen als Zeit den Vortages-Schlusskurs
     (Datum, 00:00). Ein morgen frisch entstehendes Signal traegt dann
     `2026-09-03 00:00` — immer noch VOR `account_start` (12:37). Die neuen
     Konten wuerden dann erst ab 2026-09-05 OU-Entries bekommen, nicht ab
     morgen.

  **Zum Nachpruefen auf dem Rechner** (ich komme von hier nicht dran):
  `type C:\Users\andre\Funded-Portfolio-Bridge\bridge_state_ttp1.json` (bzw.
  `bridge_state_iqmarkets2.json`) → steht dort ein `account_start` vom
  2026-09-03 ~12:37? Und im Log des 15:42-Laufs der Block der neuen Konten:
  taucht `ou_modell`/`FAST` dort mit einer Skip-Begruendung auf?

  **Deine Entscheidung**: (a) so lassen — die neuen Konten steigen erst bei
  frischen Signalen ein und laufen dauerhaft leicht hinter den alten her, oder
  (b) `account_start` der beiden neuen Konten einmalig zurueckdatieren, damit
  sie die aktuell offenen Signale (FAST, SPG) noch mitnehmen. (b) heisst auf
  Konto 1 **echtes Geld** in eine Position, die schon einen Tag gelaufen ist —
  mache ich nicht von selbst.

  **Separater Befund am Rande**: auch IQ Markets 16054 (altes Konto, kein
  `account_start`-Problem) hat den FAST-Entry nicht bekommen. Das OU-Bein hat
  dort also eine eigene Ursache — passt zum bekannten offenen Punkt "OU-Modell-
  Handelbarkeit auf BeyondIQCapital nur stichprobenartig geprueft" (`.gbe`-
  Suffix). Noch nicht untersucht.

- [x] ~~CLS Practical auf EK-Portfolio-Bridge (Echtgeld) scheitert wiederholt
  an dukascopy_python~~ — Nutzerentscheid 2026-09-02: mehr Retries statt
  Fallback-Datenquelle. Alle drei `_retry()`-Kopien (`ek_portfolio/
  paper_bot.py`, `challenge_portfolio/paper_bot.py`, `fk_instant_funding/
  paper_bot.py` — identischer Code, von allen drei echten Bridges genutzt)
  von 3 Versuchen/5s Pause auf 6 Versuche/8s Pause erhoeht. Root Cause blieb
  wie dokumentiert ein Bug in der Drittanbieter-Bibliothek selbst
  (`dukascopy_python/__init__.py::_stream()` Zeile 219), nicht behebbar,
  nur die Toleranz dagegen erhoeht. Nur `py_compile`-geprueft, kein echter
  Live-Lauf abgewartet.
- [x] ~~Funded-Portfolio-Bridge (TTP/IQ) hatte keinen "Signal zu alt"-Schutz
  beim Echt-Entry~~ — Nutzerentscheid 2026-09-02: einbauen. Neue Pruefung in
  `_process_leg()` (`MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY = 60`): ist die
  Signalzeit (`entry_time`) mehr als 60 Min. in der Vergangenheit, wird das
  Signal als "missed" vermerkt statt real zum laengst gelaufenen Kurs zu
  jagen — exakt das Muster, das beim ersten Gold-ASB-Entry (05:15 UTC
  Signal, 09:30 UTC Fill) passiert ist. Einfacher als der ORB-Fix (dort
  SL-Seite gegen Live-Preis, hier reine Signalzeit, da `_process_leg()`
  generisch fuer alle Beine/Richtungen gilt). Nur `py_compile`-geprueft.

- [x] ~~Rechner/Scheduled Tasks hatten heute Nacht eine ~9h-Lücke~~ — Ursache
  gefunden (2026-09-02, NICHT "Rechner aus", wie zuerst vermutet — Nutzer
  bestaetigt PC war an): Windows Modern Standby (S0), ausgeloest ueber die
  AC-Display-Idle-Timeout-Kette (war auf 5 Min. gestellt, sah von aussen wie
  "PC an, nur Bildschirm aus" aus, ging aber in den echten Standby). Der
  erste Catch-up-Lauf danach baute frische, sehr breite Cache-Dateien neu
  auf und produzierte dabei auf FKInstantFunding-MT5-Bridge UND
  Funded-Portfolio-Bridge zeitgleich denselben Fehler in 5 Beinen:
  `'>' not supported between instances of 'str' and 'float'` — bei
  Funded-Portfolio-Bridge selbst geheilt (naechster Lauf sauber). Nicht live
  reproduziert (Netzwerk beim Nachpruefen schon wieder stabil), aber
  wahrscheinlichster Kandidat gefunden UND gehaertet: `combined_strategy/
  data.py::fetch_timeframe()` cachte die Dukascopy-Antwort bisher ungeprueft
  — validiert jetzt vor dem Cachen auf numerische OHLC-Spalten (siehe
  CHANGELOG). Absicherung zusaetzlich umgesetzt: AC-Display/Standby-Timeout
  auf "Nie" gestellt, alle 5 Bridge-/Scanner-Tasks auf `WakeToRun`+
  `StartWhenAvailable`, neuer **Bridge-Watchdog** (eigener Task, alle 30
  Min, Telegram-Alarm bei Log-Stillstand) — siehe CHANGELOG fuer Details.
- [x] ~~Telegram-Logik NICHT auf demselben Stand bei allen drei Portfolios~~
  — nachgezogen 2026-09-02 (Nutzerauftrag): `fk_instant_funding` nutzt jetzt
  dieselbe `queue_message()`/`flush_queued_messages()`-Infrastruktur wie
  EK-Portfolio-Bridge/Funded-Portfolio-Bridge (neues `telegram_format.py` +
  Ergaenzung in `telegram_notify.py`). Sichtbares Ergebnis unveraendert,
  nur `py_compile` + Smoke-Test (Queue sammelt/leert korrekt), kein echter
  Live-Lauf abgewartet.

- [x] ~~`fk_instant_funding/paper_bot.py` letzte ORB-Kopie auf altem Stand~~
  — nachgezogen 2026-09-02 (Nutzerauftrag, "voller Umfang"): `ORB_EXIT_CFG`
  durch `ORB_EXIT_CFG_BY_INSTRUMENT` ersetzt, NASDAQ `target_mode=None`
  (EOD-Exit) PLUS Stage-6-Teilausstieg (1.5R/2R, 50%, Rest auf Breakeven)
  fuer alle drei Instrumente — anders als bei `challenge_portfolio/paper_bot.py`
  hier OHNE Einschraenkung, da dieses Modul nur FKInstantFunding-MT5-Bridge
  (reiner Order-Planer, kein echter Order-Versand) und FK-Instant-Funding-Paper
  (reine Simulation) treibt, keine echte Position also nicht auseinanderlaufen
  kann. Per Smoke-Test verifiziert (gecachte Daten): NASDAQ zeigt keinen
  `exit_reason="target"` mehr, `had_partial_exit`-Rate 34-45% je Instrument,
  keine NaN-r_multiple. Damit sind jetzt ALLE drei aktiven ORB-Traeger
  (EK-Portfolio-Bridge, Funded-Portfolio-Bridge/Challenge, FK Instant Funding)
  auf demselben Stand. (`ek_portfolio/paper_bot.py` bewusst NICHT nachgezogen
  — Nutzerentscheid 2026-09-02: bleibt pausiert/Disabled, da EK-Portfolio-Bridge
  bereits live mit echtem Geld dieselbe Logik faehrt.)

- [x] ~~Funded-Portfolio-Bridge OU-Modell-Bein meldete nie ein offenes Signal~~
  — Root Cause gefunden UND behoben 2026-09-02 (nicht nur die vermutete
  Config-Divergenz): `ou_portfolio.simulate_bracket_portfolio()` liess jede
  noch OFFENE Position beim Rueckgabe-Zeitpunkt still unter den Tisch fallen,
  nur GESCHLOSSENE Trades kamen in `trades` an — das Bein konnte dadurch
  STRUKTURELL nie "data_end" (= aktuell offen/handelbar) melden, unabhaengig
  von Config oder Kriterien. Fix: neuer `include_open_positions`-Parameter
  (additiv, Default `False`, kein anderer Aufrufer betroffen). Verifiziert an
  FAST/SPG/SYY (denselben 3 Tickern, die der Standalone-Scanner um 21:35
  fand) — erscheinen nach dem Fix korrekt mit `entry_date=2026-08-31,
  reason=data_end`. Naechster Live-Lauf von Funded-Portfolio-Bridge wird
  dadurch voraussichtlich 3 neue echte Entries (TTP+IQ) platzieren. Die
  Frage "eigene Implementierung vs. gemeinsame CSV-Quelle wie EK" bleibt
  trotzdem offen, jetzt aber nicht mehr dringend (Bein funktioniert wieder).
  **Sofortiger Folgefund** (00:05 Uhr, direkt nachdem das Bein zum ersten
  Mal feuerte): ohne NYSE-Handelszeiten-Gate versuchte die Bridge um
  Mitternacht echte Aktien-Entries (ADI/FAST) — TTP "Market closed",
  IQMARKETS "no_tick". Ebenfalls 2026-09-02 gefixt (`run_once.py::
  _nyse_is_open()`, identisches Muster zu EK), nur neue Entries gegated,
  Exits laufen weiter uneingeschraenkt. Nur `py_compile`-geprueft.

- **Funded-Portfolio-Bridge (TTP/IQ) hat noch keinen "Signal zu alt"-Schutz**
  beim Echt-Entry (`_process_leg()`), anders als der ORB-Fix heute in
  EK-Portfolio-Bridge. Der erste reale Gold-ASB-Entry heute ist genau daran
  hängen geblieben: Signal um 05:15 UTC, aber real erst 09:30 UTC gefüllt
  (~4h15 später, weil die Bridge da überhaupt zum ersten Mal live ging) —
  zu dem Zeitpunkt war der Kurs schon ~55-58 Punkte weiter gelaufen, der
  Short kam praktisch erst nach der Bewegung rein. Einmaliger Umstiegs-
  Effekt (Bridge lief vorher gar nicht), kein wiederkehrender Bug — aber
  falls die Bridge künftig mal länger pausiert/ausfällt, würde sich das
  exakt wiederholen. Soll ich denselben Alters-Check wie bei ORB (Signal
  überspringen statt zum längst gelaufenen Kurs zu jagen) hier ebenfalls
  einbauen? Nicht selbständig gemacht, weil das echtes Geld + eine gerade
  offene Position betrifft.

- **4 Claude-Workflow-Ideen aus dem "Everlast AI"-Clipping** (2026-09-02,
  siehe `resources/second-brain-methodik.md`) noch nicht übernommen, da
  jeweils eine Architekturentscheidung statt einer expliziten Anweisung:
  1. Handoff-Skill statt Auto-Compact/`/clear` bei vollem Kontextfenster
     (schreibt Learnings/Fehlannahmen als Markdown auf Platte statt in den
     Chatverlauf).
  2. `/prime`-Command(s) für `knowledge/`, um nicht bei jeder Session das
     gesamte Second Brain lesen zu müssen.
  3. Periodischer `/doctor`-Check auf ungenutzte, aber Kontext kostende
     Skills/MCP-Einträge.
  4. `CLAUDE.md` ggf. auf Englisch umstellen (spart laut Quelle ~30% Tokens
     bei reinen KI-Betriebsanleitungen) — Konflikt: `DASHBOARD.md`/
     `CHANGELOG.md` bleiben bewusst Deutsch (für dich lesbar), nur
     `CLAUDE.md` wird ausschließlich von Claude gelesen, wäre also isoliert
     änderbar. Sag Bescheid, welche (falls überhaupt) umgesetzt werden sollen.

## 💡 Ideen-Inbox (unsortiert, später einordnen)

Kurz einfangen, was gerade auftaucht, ohne das aktuelle Thema zu verlassen —
wird bei Gelegenheit einsortiert (in Offene Aufgaben, PARA-Struktur, oder
bewusst verworfen), nicht hier für immer liegen gelassen. Genau der Ort für
"das könnte auch noch interessant sein", ohne dass es das gerade laufende
Thema verdrängt oder verloren geht.

- **PDFs/Bücher bulk-einbinden** (2026-09-01): viele Bücher/PDFs vorhanden,
  die sinnvoll integriert werden könnten, ohne sie einzeln in den Chat
  schicken zu müssen. Prüfen, ob `paper_dropbox/`/`paper_research/`
  (bestehende "PDF rein, Extraktion + Auto-Backtest raus"-Pipeline, siehe
  README.md) dafür wiederverwendbar ist, oder ob Bücher (anders als
  Research-Paper) einen eigenen Weg brauchen. Noch nicht bearbeitet.
- **Stocks-in-Play 5-Min-ORB als neue Asset-Klasse** (2026-09-01, aus Paper
  "A Profitable Day Trading Strategy For The U.S. Equity Market",
  Zarattini/Barbon/Aziz 2024, siehe [[opening-range-breakout]]): 5-Min-ORB
  auf einem breiten US-Aktien-Universum (~7.000 Titel), gefiltert auf die
  Top-20-Relative-Volume-Aktien pro Tag, zeigte im Paper Sharpe 2.81/Alpha
  36%/Jahr - deutlich staerker als der reine Index-ORB-Ansatz
  ([[ny-open-orb-sp500]]). Braucht eine neue Datenquelle (breites,
  survivorship-bias-freies US-Aktienuniversum) und eigene Selektionslogik -
  kein einfaches Filter-Add-on zur bestehenden Strategie, daher eigenstaendige
  Idee statt Teil des laufenden Projekts. Noch nicht bearbeitet.

## Offene Aufgaben

**Mittel**
- [x] ~~5 unverarbeitete Clippings warten~~ — 2026-09-02 auf Nutzerauftrag
  ("leg los") verarbeitet: 3 Claude-Workflow-Clips als neue CODE-Einträge in
  `resources/second-brain-methodik.md`, Trading-Clip als neue
  `resources/order-flow-trading.md`. Duplikat (`Der einfachste Einstieg in
  Second Brains! 1.md`) bestätigt identisch zum bereits verarbeiteten Clip.
  `Clippings/`-Ordner danach auf Nutzerwunsch geleert (Rohdateien sind
  git-versioniert, jederzeit wiederherstellbar).
- [ ] Second-Brain/Dashboard-Struktur (dieses Dokument) — nach ein paar
  Tagen Nutzung Feedback einholen, ob Format/Umfang passt.
- [x] ~~EK-Portfolio-Bridge: Spread-Stunden-Pause (23:00)~~ — am 2026-09-01
  bewusst zurückgestellt. Backtest über alle 7 Strategien (704 historische
  Trades) zeigt 0,0% Entries in der Stunde 23:00 Europe/Berlin bei jeder
  einzelnen — die Pause hätte historisch nichts gekostet, wäre aber bei den
  aktuellen Edges nach Nutzereinschätzung noch nicht sinnvoll genug, um sie
  einzubauen. Nicht wieder von selbst vorschlagen, außer neue Legs mit
  potenziell später Entry-Zeit kommen dazu.
- [x] ~~EK-Portfolio-Bridge / NY-Open-ORB: SP500/US30-Entries "Invalid stops"~~
  — behoben 2026-09-02 (Details CHANGELOG.md), nur `py_compile`-geprüft,
  nächster echter Live-Lauf verifiziert es noch nicht endgültig.

**Niedrig**
- [ ] `knowledge/`-Altlasten (Lint-Check 2026-09-01, Details s. Skript-Output
  `python knowledge/scripts/lint.py`):
  - Tote Wikilinks ohne größeren Zusammenhang: `[[cls-practical]]`
    (`archive/london-range-bos-retest-eurusd.md`), `[[gap-fade]]` und
    `[[execution-overlay]]` (beide `resources/fx-microstructure.md`).
  - 8 verwaiste Seiten ohne eingehende Wikilinks: `archive/ipda-zyklus-eurusd.md`,
    `archive/london-cls-breakout-eurusd.md`,
    `archive/london-range-bos-retest-eurusd.md`,
    `areas/paper-bot-architecture.md`,
    `projects/challenge-portfolio-ttp-icapital.md`,
    `projects/persoenlicher-tradingplan-validierung.md`,
    `projects/strategie-backlog-inventar.md`,
    `resources/second-brain-methodik.md`. Meiste unkritisch (Projects
    verlinken oft nur raus), aber `challenge-portfolio-ttp-icapital` könnte
    noch einen Rücklink von einer verwandten Resource/Area vertragen.
    (`ny-open-orb-sp500` 2026-09-01 aufgelöst: neue Resource
    `resources/opening-range-breakout.md` verlinkt jetzt dorthin.)
  - Neu seit 2026-09-02, noch nicht durch erneuten Lint-Lauf bestätigt:
    `resources/order-flow-trading.md` vermutlich ebenfalls verwaist (nur
    ausgehende Links zu `ny-open-orb-sp500`/`opening-range-breakout`,
    keine eingehenden) — unkritisch, gleiche Kategorie wie
    `second-brain-methodik.md`.

## Letzte Aktivität

_(Auszug — vollständiges Log in [CHANGELOG.md](CHANGELOG.md))_

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
