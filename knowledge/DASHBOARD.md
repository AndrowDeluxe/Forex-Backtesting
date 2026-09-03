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

## ▶️ Als Nächstes

1. **M5-Scan-Frequenz fuer CTNL Continuation + NY-Open ORB**: beide nutzen
   M5-Bars fuer Entries, Funded-Portfolio-Bridge scannt aber nur alle 15 Min
   -- bis zu 3 Bars zu spaet (gleiches Muster wie der fruehe Gold-ASB-Fund).
   Nutzerentscheid 2026-09-02: separaten 5-Min-Trigger NUR fuer die
   M5-Beine bauen (nicht die ganze Bridge auf 5 Min umstellen, da OU-Modell/
   Gold ASB davon nicht profitieren wuerden) -- braucht Aufbrechen von
   `run_once.py`s "alle Beine in einem Lauf"-Struktur, kein Kleinvorgang.
2. **Manuelles Monatsjournal + Quant-System-Verschmelzung** (Nutzerwunsch
   2026-09-02 Abend, fuer morgen): Nutzer will ein haendisches Monatsjournal
   anfangen und gemeinsam mit Claude auswerten. Zusaetzlich einen Plan
   erarbeiten, wie manuelles Trading + dessen Routinen/Auswertungen und das
   Quant-System (die Portfolio-Bridges hier) sinnvoll miteinander verbunden
   werden koennen -- Ziel: eine moeglichst optimale Verbindung/Verschmelzung
   beider Seiten, nicht zwei getrennte Welten. Noch nichts Konkretes gebaut,
   nur der Wunsch/Auftrag festgehalten -- braucht als Erstes ein klaerendes
   Gespraech (Format des Journals, welche Kennzahlen, was genau
   "Verschmelzung" praktisch heissen soll), bevor irgendetwas umgesetzt wird.
   Punkt 3 unten (Redundanz-Vermeidung) ist ein erster Kandidat fuer einen
   Quant-Seite-Eintrag, sobald das Journal steht.
3. ~~Funded-Portfolio-Bridge: redundante Scans vermeiden~~ -- **erledigt
   2026-09-03**, siehe CHANGELOG. Kurzfassung: MT5 als Datenquellen-Ersatz
   geprueft und verworfen (die 4 TTP/IQ-Konten decken laut `symbol_map` nur
   9 der ~30 in `combined_strategy/data.py` gebrauchten Instrumente ab --
   kein VIX/Oil/GBPUSD/USDCHF/AUDUSD/USDCAD/die ~13 FX-Kreuze -- und wuerde
   den ohnehin fragilen MT5-IPC-Kanal zusaetzlich belasten statt entlasten).
   Stattdessen `run_once.py` umgebaut: `run_shared_scans()` fuehrt alle 6
   Scans EINMAL pro Bridge-Lauf aus (vorher 1x PRO KONTO), `main()` reicht
   das Ergebnis an alle 4 Konten durch. Nebenbei zweiter Fund/Fix dabei:
   `tvDatafeed`-Pro-Login (`cls_practical/rates.py`'s Zinsfilter) erzeugte
   seit 2026-09-01 in praktisch jedem Lauf `error while signin` (TradingView
   verlangt seit einiger Zeit ein von der Bibliothek nicht loesbares Captcha,
   offenes Upstream-Issue) -- Login entfernt, laeuft jetzt direkt anonym
   (nachweislich ausreichend). Beides nur per Smoke-Test verifiziert (kein
   echter Live-Lauf ueber Task Scheduler abgewartet).

---

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld**                                                                       | Ready (alle 15 Min, Mo–Fr)      | 2026-09-02      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | DRY_RUN                                                                                      | Ready (stündlich)               | 2026-09-02      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram                                                                             | Ready (stündlich)               | 2026-09-01      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner + Telegram (3x täglich: 15:35/18:35/21:35)                                           | Ready (Mo–Fr, US-Handelszeiten) | 2026-09-02      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator                                                                             | Ready                           | 2026-09-02      |
| **Bridge-Watchdog**                                     | — (nur Log-Frische, kein Order-Bezug)                                                    | Heartbeat-Alarm + Status-Snapshot ins Repo                                                   | Ready (alle 30 Min)             | 2026-09-02      |
| **Funded-Portfolio-Bridge** (TTP+IQ Markets, 6 Beine)   | TTP Konto 2 (504072729) + TTP Konto 1 (504069845) + BeyondIQCapital (16054) + BeyondIQCapital (15514) — **alle 4 verbunden** | **LIVE — DRY_RUN=False**                                       | Ready (alle 15 Min, Mo–Fr)      | 2026-09-03      |
| Challenge Portfolio (Paper-Bot, `challenge_portfolio/`) | — (reine Simulation)                                                                     | Paper-Bot fertig entwickelt                                                                  | Noch kein Task angelegt         | 2026-09-01      |
| BTC-EMA-Cross-Bridge/-Scan                              | Binance / BeyondIQCapital (15514, geteilt mit GoldASB)                                   | **aufgelöst** — Konto 15514 jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS_MT5` leer            | Disabled                        | 2026-09-02      |
| CLS-Practical-Bridge/-Scan                              | —                                                                                        | **aufgelöst** — Logik steckt bereits in allen drei Portfolio-Bots (`paper_bot.py`)           | Disabled                        | 2026-09-02      |
| CTNL-Edge-FK-Paper                                      | —                                                                                        | **aufgelöst** — Logik steckt bereits in allen drei Portfolio-Bots (`paper_bot.py`)           | Disabled                        | 2026-09-02      |
| CTNL-Edge-MT5-Bridge                                    | BeyondIQCapital (16054)                                                                  | **aufgelöst** — Konto/Terminal bereits bei Funded-Portfolio-Bridge live                       | Disabled                        | 2026-09-01      |
| Gold-ASB-Scan / GoldASB-MT5-Bridge                      | BeyondIQCapital (15514)                                                                  | **aufgelöst** — Konto 15514 jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` leer                | Disabled                        | 2026-09-02      |
| OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat               | —                                                                                         | **aufgelöst** — Konto 1 jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` komplett leer           | Disabled                        | 2026-09-02      |
| EK-Portfolio-Paper                                      | —                                                                                        | pausiert (Paper-Zwilling von EK-Portfolio-Bridge, gehört zum Portfolio, nicht "Einzelstrategie") | Disabled                     | 2026-09-01      |

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

- **EK-Portfolio-Bridge (Echtgeld): neue, vage Fehlerzeile "cls_practical:
  unerwarteter Fehler"** — laut Snapshot vom 2026-09-03 17:01
  (`bridge_status/snapshot.json`) `last_error_line`: "2026-09-03 16:54:31
  2026-09-03 16:54:15,602 ERROR run_once: cls_practical: unerwarteter
  Fehler", `recent_events` dabei leer (keine weiteren Details). Bridge
  selbst läuft trotzdem normal weiter (`status: ok`, letzter Lauf nur 1,4
  Min. vor dem Snapshot). Dieser exakte Text ("unerwarteter Fehler") kommt
  NICHT aus diesem Repo (kein Treffer für den String in irgendeiner
  `.py`-Datei hier) — muss also aus dem für mich unsichtbaren
  `EK-Portfolio-Bridge`-Ordner selbst stammen. Könnte derselbe
  dukascopy_python-Fund vom 2026-09-02 sein (nur hinter einem
  generischeren Catch-Block statt der spezifischen Hang-/KeyError-Meldung),
  oder etwas Neues — ohne Log-Zugriff vor Ort kann ich weder Root Cause
  noch Häufigkeit einschätzen, und will hier nichts erfinden. Kannst du
  kurz in `C:\Users\andre\EK-Portfolio-Bridge\logs\task_run.log` um
  16:54:15 Uhr nachsehen, was den Fehler wirklich auslöst?

- [x] ~~Zwei neue Funded-Portfolio-Bridge-Konten (TTP 504069845 / IQ 15514)
  waren bereits anderweitig vergeben~~ — Nutzerentscheid 2026-09-02:
  bewusst gewollte Konsolidierung, kein Verwechsler. Beide jetzt in
  `Funded-Portfolio-Bridge/config.py::ACCOUNTS` (`ttp1`/`iqmarkets2`),
  aus `OU-Modell-MT5-Bridge`/`GoldASB-MT5-Bridge`/`BTC-EMA-Cross-Bridge`
  entfernt. Details siehe CHANGELOG.
- **Zwei neue Konten (TTP Konto 1/504069845, IQ 15514) verbinden weiterhin
  nicht — Root Cause jetzt gefunden: kopierte statt echt installierte
  Terminals.** Die urspruengliche "File → Login to Trade Account"-Theorie
  war falsch — ausfuehrliche Tests (isolierter Prozess, sequenzielles
  Starten, `portable=True`, bis 60s Timeout, Terminal-Ersatz FK2->CLSPractical)
  zeigen: das Terminal-Fenster loggt sich korrekt ein UND AutoTrading ist an
  (einmal sogar per `account_info()` bestaetigt, NACHDEM `login()` faelschlich
  "fehlgeschlagen" meldete — der Login hatte tatsaechlich geklappt, nur die
  Bestaetigung kam zu spaet zurueck) — die Python-IPC-Anbindung selbst bleibt
  trotzdem unzuverlaessig. Die 2 URSPRUENGLICHEN Konten (504072729, 16054)
  verbinden dagegen bei jedem Test sofort. Vermutung: eine echte
  MT5-Installation registriert etwas fuers Python-IPC, das eine reine
  Verzeichnis-Kopie (wie `TTP MT5 Terminal - Konto3`/`IQ MT5 Terminal -
  Konto2`, urspruenglich aus den ruhenden FK1/FK2-Installationen kopiert)
  nicht mitbringt. **Kein Order wurde die ganze Zeit riskiert** — auch der
  ueber Stunden durchgehende `IPC timeout` in `logs/task_run.log` (14:54 bis
  mind. 21:57) war immer ein sauberer Verbindungsfehler, nie eine falsche
  Order; das OU-Modell-Bein haette am 2026-09-02 wegen Handelsschluss/
  Alters-Bremse ohnehin keinen Entry mehr platziert. Die zwei bestehenden
  Live-Beine sind komplett unberuehrt. **Fix in Arbeit**: Nutzer installiert
  gerade selbst zwei ECHTE MT5-Terminals per `mt5setup.exe` (mein
  Silent-Install-Versuch per `/auto /dir=` schlug fehl) — sobald fertig,
  Pfade in `Funded-Portfolio-Bridge/config.py` eintragen und erneut testen.
  `symbol_map` fuer beide Konten ausserdem nur vom Schwesterkonto
  uebernommen, nicht per `check_symbols.py` selbst verifiziert.

- [x] ~~`dukascopy_python`-Datenabruf haengt seit heute Nachmittag komplett
  fest, ohne Timeout~~ — gefunden 2026-09-02 ~21:50 (23 `python.exe`-Prozesse,
  `Funded-Portfolio-Bridge/run_once.py` UND `fk_instant_funding/paper_bot.py`,
  seit 15:45 im 15-Min-Takt gestartet, keiner kam je zum Ende). Zusaetzlicher
  Fund beim Nachgehen der TTP-vs-IQ-Tagesabschluss-Frage (Nutzeranfrage
  "wieso TTP voller Fehler, IQ nicht"): dieselbe Instabilitaet zeigt sich auch
  als schnellere, abfangbare Exceptions statt komplettem Hang -- TTP Konto2
  hatte heute 5 Scan-Fehler ueber 5 Beine, IQ Markets 0, reiner Zufall im
  Timing, da jedes der 4 Konten dieselben 6 Scans unabhaengig neu zieht.
  Nutzerentscheid: alle 3 `_retry()`-Kopien fixen (EK+Challenge+FK Instant
  Funding, nicht nur die 2 nachweislich haengenden). Fix: neue
  `_call_with_timeout()`-Funktion (Daemon-Thread + `join(timeout)`,
  `timeout_seconds=90.0` pro Versuch) um jeden `_retry()`-Versuch gelegt --
  ein haengender Versuch zaehlt jetzt wie jeder andere Fehlversuch, blockiert
  aber nie wieder den ganzen Prozess. Per synthetischem Smoke-Test
  (`hangs_forever()`) verifiziert: sauberer `TimeoutError`-Abbruch nach
  exakt erwarteter Zeit, normales Retry-Verhalten unveraendert, Prozess
  beendet sich trotz weiterlaufendem Hang-Thread sofort sauber (kein
  Ressourcen-Leck). Alte, mit ungefixtem Code gestartete haengende Prozesse
  beendet. **Kein echter Live-Lauf mit echtem dukascopy-Hang seitdem
  abgewartet** (nur der synthetische Test) — erster echter Beweis kommt mit
  dem naechsten Mal, dass die Bibliothek wirklich haengt.
- [x] ~~`OU-Modell-ScannerHourly` läuft noch (Ready), ist aber jetzt
  verwaist~~ — Nutzerentscheid 2026-09-02: erstmal weiterlaufen lassen, die
  Streamlit-Seite (`app_pages/ou_scanner.py`) braucht ihn noch. Zusätzlich:
  3 der 8 täglichen Läufe (15:35/18:35/21:35) senden jetzt eine
  Telegram-Zusammenfassung (siehe CHANGELOG) statt den Task zu deaktivieren.
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

- **OU-Modell-Scanner evtl. irgendwann komplett auf Telegram umstellen**
  (2026-09-02): Website-Ansicht bleibt vorerst (siehe Status-Tabelle, jetzt
  MIT Telegram fuer die 3 Tagesscans), aber "ganz auf Telegram umstellen und
  die Streamlit-Seite aufgeben" war eine genannte Alternative — nicht
  entschieden, nur festgehalten.
- **PDFs/Bücher bulk-einbinden** (2026-09-01): viele Bücher/PDFs vorhanden,
  die sinnvoll integriert werden könnten, ohne sie einzeln in den Chat
  schicken zu müssen. Prüfen, ob `paper_dropbox/`/`paper_research/`
  (bestehende "PDF rein, Extraktion + Auto-Backtest raus"-Pipeline, siehe
  README.md) dafür wiederverwendbar ist, oder ob Bücher (anders als
  Research-Paper) einen eigenen Weg brauchen. Noch nicht bearbeitet.
- **TTP/IQ Markets ORB-Exits laufen pro Konto unabhaengig auseinander**
  (2026-09-02, Fund beim Nachpruefen des US30-ORB-Trades): TTP und IQ
  Markets scannen denselben ORB-Trade in _separaten_ `run_once.py`-Laeufen
  je Konto -- jeder Lauf ruft `simulate()` neu mit frisch gezogenen Daten
  auf. Beim heutigen US30-Long (Entry ~16:22 CEST) fuehrte das dazu, dass
  TTP den Exit bei 53175.04 (+$10,39) fand, IQ Markets aber erst 9,5 Min.
  spaeter bei 53107.00 (-$9,84) -- derselbe Signal-Trade, gegensaetzliches
  Vorzeichen. Kein Bug im engeren Sinn (beide folgen korrekt ihrer je
  aktuellen `rvol_fade`-Exit-Regel), aber noch nicht bewertet, ob das
  system-immanent so bleiben soll oder ob Exits kontoübergreifend
  synchronisiert werden sollten. Noch nicht bearbeitet.
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
