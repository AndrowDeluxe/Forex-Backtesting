# Dashboard

**Stand: 2026-10-01** _(wird bei jeder Session von Claude auf das aktuelle
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

- **Positionsdeckel auf 2 gesenkt (01.10., erledigt) -- EK bleibt bei 1.**
  P(MaxDD>6 %) faellt von 43,5 % auf 9,9 %, Rendite 40 % statt 58,6 %.
  **Zur Kenntnis:** alle drei Konten halten gerade 3 Positionen, also eine
  ueber dem Deckel -- neue Entries sind gesperrt, bis auf 1 abgebaut ist.
  Die bestehenden laufen mit Broker-SL normal aus, nichts wird
  zwangsgeschlossen. `max_hold` bleibt bei 96 h (ohne Grenze je Trade
  besser, in der Summe schlechter).

- **🟡 Beide seit Langem bekannten Fehlermuster sind in der Nacht 30.09./01.10.
  erstmals auch beim `gold_asb`-Bein aufgetreten -- vorher waren andere Beine
  betroffen.** (Bridge Error Monitor, 01.10., 11:01-Snapshot.) (1)
  **EK-Portfolio-Bridge** `last_error_line`: `"2026-10-01 02:21:39 ... ERROR
  run_once: gold_asb: unerwarteter Fehler"` -- dasselbe traceback-lose Muster
  wie der bereits dokumentierte `cls_practical: unerwarteter Fehler` vom
  29.09. weiter oben, nur jetzt auf `gold_asb` statt `cls_practical`;
  `recent_events` ist leer, also kein zusaetzlicher Kontext verfuegbar.
  (2) **FKInstantFunding-MT5-Bridge** `last_error_line`: `"2026-10-01
  02:15:06 gold_asb-Scan fehlgeschlagen: '>' not supported between instances
  of 'str' and 'float'"` -- derselbe, weiter unten ausfuehrlich analysierte
  `str`/`float`-Fehler (bisher `trend_pullback`/`cls_practical`), jetzt auch
  bei `gold_asb`. Beide Faelle: **kein Folgefehler seither**, Status aktuell
  wieder "ok" bei allen drei Bridges (saubere Equity-Zeilen im 10-11-Uhr-
  Lauf), also vermutlich wieder selbstheilend. **Nichts geaendert** -- die
  bereits offene Unsicherheit weiter unten (lake- vs. live-Pfad, nicht-
  atomares `to_parquet()` in `combined_strategy/data.py::CACHE_DIR`,
  geprueft: Zeile 133 ist weiterhin ohne temp+rename) ist dieselbe wie zuvor,
  jetzt nur mit einem dritten betroffenen Bein als zusaetzlichem Datenpunkt.
  **Offen fuer dich:** unveraendert dieselben zwei Fragen wie beim
  `str`/`float`-Eintrag unten -- nichts Neues zu entscheiden, nur zur
  Kenntnis, dass sich das Muster ausweitet.

- **CTNL faehrt seit 2026-09-30 nur noch `ctnl_reversal`** (beide
  Richtungen, Ribbon-gefiltert). `ctnl_continuation` ist auf allen drei
  Bridges stillgelegt -- keine Position war dabei offen, es blieb nichts
  unverwaltet zurueck. **Kein Handlungsbedarf, nur zur Kenntnis:**
  `cont_trades` wird weiter berechnet, weil der CTNL-Kill-Switch ueber die
  kombinierte Kurve urteilt; und `check_and_execute_continuation()` bleibt
  in EKs Executor stehen, damit ein Wiedereinschalten eine Zeile ist.

- **🔴 EK-Mindestlot durchgerechnet: 76 % des Verlusts kommen aus der
  Groessenverzerrung, nicht aus den Strategien (2026-09-30, Nutzerauftrag).**
  Empirisch aus den echten Deals KW38+KW39: Ist **-669,48 EUR**, bei den
  eigentlich gewollten Zielgroessen waeren es **-161,30 EUR** -- Differenz
  **-508 EUR**, davon **-397 EUR allein `ctnl_reversal`** (19 Ausstiege,
  Faktor 51x ueber Ziel). Auf ~3.389 EUR Startequity: -19,75 % statt -4,76 %.
  **Noetige Kontogroesse, damit kein Bein mehr angehoben wird:**
  `ctnl_reversal` **143.787 EUR** (bindend), `ctnl_continuation` 12.432,
  `ou_modell` 8.161, `gold_asb` 2.057, ORB 61-403. **Ohne `ctnl_reversal`
  sinkt die Anforderung auf 12.400 EUR**, ohne beide CTNL-Beine auf ~8.200.
  **Offen fuer dich, drei Wege** (Details in [[ek-risiko-kalibrierung-audit]]):
  (1) Konto auf ~12.400 bringen und `ctnl_reversal` streichen; (2) die
  CTNL-Beine auf EK abschalten und den Rest weiterlaufen lassen; (3) alles
  lassen und die invertierte Hierarchie akzeptieren. **Ich habe nichts
  geaendert.** Einschraenkung: die Spalte "bei Zielgroesse" ist keine
  erreichbare Alternative -- dort wuerden die Beine auf 0 Lot runden und gar
  nicht handeln, genau deshalb gibt es die Anhebung seit 10.09.

- **EK: der Ribbon hilft, aber die Mindestlot-Anhebung bleibt das
  dominante Risiko.** Backtest 2024-heute je Konto: die drei Funded-Konten
  liegen mit **P(MaxDD>6 %) = 0,0 %** komfortabel innerhalb ihrer Grenze
  (ttp -0,76 %, iqmarkets -1,52 %, FK -1,15 % Median-Drawdown). **EK
  nominal -0,57 %, EK REAL aber -14,00 %** mit P(>6 %) = 99,4 % -- weil das
  kleinste XAUUSD-Lot 0,86 %/Trade riskiert statt der vorgesehenen 0,019 %
  (Faktor 46, Befund 10). Der Ertrag (+156,8 %) ist das Spiegelbild davon.
  **Offen fuer dich:** EK hat keine harte DD-Grenze, das ist also zulaessig
  -- willst du es so? Die Alternativen stehen in E5 (Anhebung fuer CTNL
  abschalten = Bein verstummt auf EK, oder CTNL-Risiko anheben bis das Ziel
  ueber dem Mindestlot liegt). Ich habe nichts geaendert.

- **Gegenlesen beim naechsten CTNL-Signaltag.** Verifiziert ist der
  Code-Stand (alle fuenf Einstiegspunkte, funktionaler Test mit gefaketem
  Executor), NICHT ein echter Live-Durchlauf mit Order. Im Log sollte
  stehen: "N von M Signalen behalten; X gegen den Trend verworfen". Bleibt
  die Meldung aus, greift das Gate nicht.

- **CTNL: Spike-Filter live + Kill-Switch umgestellt -- beim nächsten Lauf
  kontrollieren** (2026-09-30, Befund 19). Nach deinen Entscheiden: (1) Der
  Kill-Switch rechnet jetzt auf dem GEHANDELTEN Satz (Ribbon + Spike, −1,10 %
  statt −7,01 %) und **hebt sich beim nächsten Lauf auf FK, TTP und IQ auf**,
  CTNL handelt dort wieder. (2) `ctnl_reversal` nimmt nur noch Signalkerzen
  ≥ 0,75 ATR. (3) Der Flacker-Fix und die FK-Log-Zeile sind drin.
  **Meine Annahmen, bitte bestätigen:** (a) Die Schwelle −6,6 %/−3,3 % bleibt
  unverändert, obwohl sie auf der ungefilterten Strategie kalibriert war. Auf dem
  Ribbon-Set hätte sie in 10 Jahren nie ausgelöst, sie ist also reine Notbremse.
  (b) Der Kerzenfilter gilt nur für reversal, nicht für continuation (dort nicht getestet).
  **Zu prüfen:** Telegram meldet „CTNL-Drawdown erholt“ je Konto, und im FK-Log
  erscheinen „Spike-Filter behaelt …“-Zeilen. Nebenbei unverändert offen:
  auf EK riskiert ein CTNL-Trade ~25 EUR = ~0,9 % Equity (Mindestlot, Befund 10).

- **CTNL-Ribbon-Gate ist seit 2026-09-30 auf allen drei Bridges scharf.**
  Long nur im Aufwaerts-, short nur im Abwaertstrend des MTF-EMA-Ribbons.
  **Was du in den naechsten Wochen sehen wirst und was NICHT
  ueberraschen darf:** rund **60 % weniger CTNL-Signale**, und kurzfristig
  **weniger Ertrag** (2024-2026 waeren es ΣR +139,3 statt +169,3 gewesen).
  Der Gewinn liegt in den schlechten Jahren -- Monte Carlo ueber zehn Jahre:
  Median-MaxDD -5,63 % statt -15,50 %, Rendite +58,0 % statt +18,8 %.
  **Offen fuer dich:** nach ein paar Wochen gegenpruefen, ob die Live-Quote
  der verworfenen Signale zur erwarteten passt (~60 %). Sag Bescheid, wenn
  ich dafuer eine geplante Auswertung anlegen soll.

- **🔴 Der Git-Sync-Stash frisst weiterhin Session-Arbeit.** Am 30.09. war
  `strategy/backtest.py` erneut aus dem Working Tree verschwunden (lag in
  `stash@{38}` vom 28.09., zurueckgeholt). Es gibt eine Handoff-Notiz
  `_handoff/GIT_STASH_KONFLIKT.md` vom selben Tag. **Der Fix vom 23.09. hat
  das Problem nicht beseitigt**, 39 Stashes sind aufgelaufen. **Offen fuer
  dich:** soll ich der Ursache nochmal nachgehen? Bisherige Notmassnahme
  (nach jeder Aenderung sofort committen) funktioniert, ist aber keine
  Loesung.

- **🟡 `'str'`/`'float'`-Fehler ist am 29.09. erneut aufgetreten -- diesmal in
  Trend-Pullback-Scan (Funded, TTP+IQ) und CLS-Practical-Scan (FK), am Tag
  NACH dem als behoben dokumentierten Fix vom 28.09.** (Bridge Error Monitor,
  29.09., 23:01-Snapshot.) Beobachtet: `Funded-Portfolio-Bridge` beide Konten
  `"2026-09-29 22:16:20 Trend-Pullback-Scan fehlgeschlagen: '>' not
  supported between instances of 'str' and 'float'"` und erneut um 22:31:19;
  `FKInstantFunding-MT5-Bridge` `"2026-09-29 22:17:44 cls_practical-Scan
  fehlgeschlagen: '>' not supported between instances of 'str' and
  'float'"` (und schon am 28.09. 18:34:22 identisch). Identischer Fehlertext
  wie der am 28.09. dokumentierte, damals als behoben geltende Fund (Fix in
  `data_lake/reader.py::_require_fresh()`).
  **Nachgeprueft, warum der Fix das offenbar nicht abdeckt:** `_scan_trend_
  pullback()`/`_scan_cls_practical()` (und alle anderen `_scan_*`) in
  `challenge_portfolio/paper_bot.py` sowie `fk_instant_funding/paper_bot.py`
  haben Default `source="live"` -- nur mit explizitem `source="lake"` (Code
  der aufrufenden Bridge, liegt ausserhalb des Repos, siehe CLAUDE.md) greift
  ueberhaupt der am 28.09. gepatchte `data_lake/reader.py`-Pfad. Ob die
  echten Bridges `source="lake"` oder den Default `"live"` verwenden, kann
  ich von hier nicht sehen.
  Falls `"live"`: der Fehler kommt aus `combined_strategy/data.py::
  fetch_timeframe()` bzw. `cls_practical/data.py`, die schon seit 09-02/03/06
  alle fuenf OHLCV-Spalten sowohl beim Cache-Read als auch beim Frisch-Fetch
  validieren (`validate_ohlc_numeric(..., ["Open","High","Low","Close",
  "Volume"])`) -- dort duerfte eine korrupte Spalte eigentlich gar nicht
  durchkommen. Auffaellig dabei: `combined_strategy/data.py::CACHE_DIR`
  (`data_cache/combined/`) ist EIN gemeinsames Verzeichnis fuer alle drei
  Bridges, und `df.to_parquet(path)` dort schreibt NICHT atomar (kein
  temp+rename, anders als `data_lake/storage.py`, das genau das per Kommentar
  ausdruecklich tut) -- zwei Bridges, die zeitgleich denselben
  Instrument/Timeframe-Cache neu befuellen, koennten sich beim Schreiben
  ueberschneiden. Die zeitliche Naehe der drei Fehlermeldungen (22:16, 22:17,
  22:31) passt zu dieser Erklaerung, beweist sie aber nicht.
  Falls `"lake"`: `data_lake/reader.py::_require_fresh()` und `data_lake/
  ingest.py::_validate()` pruefen beide nur `["Open","High","Low","Close"]`/
  `["open","high","low","close"]` per exaktem Spalten-Set-Match (kein
  `Volume`) -- fuer die hier tatsaechlich betroffenen Vergleiche
  (`mt5_trend_pullback/pipeline.py`: `df["close"] > df["ema_trend"]`,
  `df["rsi"] > rsi_oversold`) waere `close` aber mitgeprueft, das erklaert
  die Trend-Pullback-Faelle also NICHT direkt.
  **Nichts geaendert** -- zu unsicher, welche der beiden Erklaerungen
  zutrifft, um gezielt zu fixen, und beide Codepfade sind bereits mehrfach
  gepatcht (09-02/03/06/07/28). **Offen fuer dich:** (a) weisst du, ob die
  Funded-/FK-Bridges tatsaechlich mit `source="lake"` laufen? (b) soll ich
  das nicht-atomare `to_parquet()` in `combined_strategy/data.py` auf
  temp+rename umstellen (kleine, sichere Haertung, gleiches Muster wie
  `data_lake/storage.py`, faellt in Tier 1) als vorsorgliche Massnahme, auch
  ohne den genauen Beweis? Status jetzt wieder "ok" bei allen drei Bridges.

- **🟡 EK-Portfolio-Bridge: neue, andere Fehlermeldung `cls_practical:
  unerwarteter Fehler` -- kein `raise error[0]`/Lake-Traceback wie die
  beiden Punkte darunter.** (Bridge Error Monitor, 29.09., 23:01-Snapshot.)
  `last_error_line`: `"2026-09-29 22:36:22 ... ERROR run_once: cls_practical:
  unerwarteter Fehler"`. `recent_events` enthaelt dazu keinen Traceback --
  der einzige Eintrag dort ist weiterhin die alte, bereits dokumentierte
  Lake-Zeile vom 28.09. 18:34:58 aus den beiden Punkten unten. Ob dieser neue
  Fehler also derselbe Lake-Mechanismus ist (nur anders formatiert) oder
  etwas komplett anderes, kann ich anhand der verfuegbaren Snapshot-Felder
  nicht sagen -- mehr Text als die eine Zeile liefert der Snapshot nicht, und
  die EK-Portfolio-Bridge-Quelle liegt ausserhalb des Repos. **Kein
  Folgefehler seither**, Status jetzt "ok" (letzter Lauf 22:59:07, saubere
  Equity-Zeile). Nichts geaendert. **Offen fuer dich:** falls das wiederkehrt,
  waere der volle Traceback aus `EK-Portfolio-Bridge/logs/task_run.log` um
  22:36:22 hilfreich, um zu sehen ob es dieselbe Lake-Ursache ist.

- **🟡 EK-Portfolio-Bridge: unaufgefangener `LakeStaleDataError` um 02:36 Uhr --
  der Daten-Lake-Fallback hat dort offenbar NICHT gegriffen.** (Bridge Error
  Monitor, 28.09., 10:32-Snapshot.) `last_error_line`: `"2026-09-28 02:36:31
  raise error[0]"`, direkt darüber in `recent_events` die Quellzeile
  `f"Lake-Daten fuer {source}:{key}_{timeframe} zu alt
  (last_success_at={entry and entry.get('last_success_at')})"` -- das ist
  wortwörtlich die `LakeStaleDataError`-Zeile aus `data_lake/reader.py:93`
  (`_require_fresh()`), hier als Traceback-Quelltext statt interpoliert (der
  Watchdog sammelt offenbar Traceback-Frames ein). `raise error[0]` ist das
  Muster aus `_call_with_timeout()` (identisch in drei Repo-Dateien, z.B.
  `ek_portfolio/paper_bot.py:100`): ein Fehler aus einem Hintergrund-Thread
  wird nach `join()` im Hauptthread erneut geworfen.
  **Bedeutung:** für irgendein `(source, key, timeframe)` war der Lake-Eintrag
  zu alt -- eigentlich sollte genau das `data_lake/reader.py::
  with_live_fallback()` abfangen und ohne sichtbaren Fehler auf den
  Live-Fetch ausweichen.
  **Kann ich nicht abschliessend klären**, weil die EK-Portfolio-Bridge
  ausserhalb des Repos läuft (siehe CLAUDE.md) -- `ek_portfolio/paper_bot.py`
  im Repo treibt sie NICHT (das ist der pausierte Paper-Task), die Live-
  Bridge hat vermutlich eine eigene, ähnliche Kopie dieser Scan-Logik, die ich
  von hier nicht einsehen kann. Auffällig in der Repo-Kopie: `_scan_ctnl()`
  hat -- anders als `_scan_gold_asb()`/`_scan_cls_practical()` -- gar keinen
  `source`-Parameter und importiert seine vier Fetch-Funktionen immer direkt
  (nie `with_live_fallback`-gewrapped); ob die Live-Bridge dieselbe Lücke hat,
  kann ich nicht verifizieren, und die Statustabelle unten behauptet für EK
  "ctnl x2 jetzt `source=\"lake\"`" -- falls das stimmt, muss die Live-Bridge
  das anders verdrahtet haben als diese Repo-Kopie.
  **Kein Folgefehler seit 02:36:31** -- Status jetzt "ok", der 10:32-Lauf
  war sauber (aktuelle Equity-Zeile), also vermutlich einmalig/selbstheilend.
  Nichts geändert. **Offen für dich:** soll ich mir (mit deinem Zugriff) die
  tatsächliche EK-Portfolio-Bridge-Quelle ansehen, oder reicht es, das im
  Auge zu behalten, falls es wiederkehrt?

- **🟡 EK-Portfolio-Bridge: derselbe `LakeStaleDataError` ist am selben Tag
  noch einmal aufgetreten -- die "vermutlich einmalig/selbstheilend"-
  Einschaetzung im Bulletpunkt oben ist damit ueberholt.** (Bridge Error
  Monitor, 29.09., 11:01-Snapshot.) Neuer `last_error_line`: `"2026-09-28
  18:34:58     raise error[0]"`, direkt darueber in `recent_events` wieder
  die Quellzeile `f"Lake-Daten fuer {source}:{key}_{timeframe} zu alt
  (last_success_at={entry and entry.get('last_success_at')})"` -- exakt
  dasselbe Muster wie beim zuerst dokumentierten Fall um 02:36:31 Uhr
  desselben Tages (28.09.), nur ~16 Stunden spaeter. Auch hier nur ein
  einzelner Eintrag in `recent_events`, kein Folgefehler seither, und der
  aktuelle Status ist wieder "ok" (letzter Lauf heute 10:59:07 mit sauberer
  Equity-Zeile) -- also erneut vermutlich selbstheilend, aber eben NICHT
  mehr einmalig. Damit bleibt offen, ob der `with_live_fallback()`-Mechanismus
  fuer diesen Pfad auf der Live-Bridge tatsaechlich greift (siehe Analyse im
  Bulletpunkt oben) oder ob hier zweimal an einem Tag echte Live-Daten fuer
  einen Scan gefehlt haben. **Nichts geaendert** -- Root Cause liegt
  moeglicherweise in der EK-Portfolio-Bridge-eigenen Kopie der Scan-Logik
  ausserhalb des Repos, die von hier nicht einsehbar ist (siehe CLAUDE.md).
  **Offen fuer dich:** dieselbe Frage wie oben, jetzt mit einem zweiten
  Beleg -- lohnt sich ein Blick in die echte Bridge-Quelle, oder reicht
  weiteres Beobachten?

- **⬜ 8 verwaiste OU-Solo-Positionen: Aufräumen verworfen (Nutzerentscheid
  2026-09-30)** — die Positionen bleiben offen und zahlen weiter Swap, das ist
  bewusst so entschieden. Kein offener Arbeitspunkt mehr; hier nur noch als
  Sachstand. Falls es doch wieder aufgegriffen wird: das Skript
  `scripts/close_ou_solo_orphans_once.py` lief 9-mal in der VORSCHAU, nie mit
  `--live`, und erreicht seit der Entfernung von TTP Konto 1 (19.09.) nur noch
  5 der 8 Positionen — DAL, UAL und NUE auf Konto 1 sind für das Skript
  unerreichbar, es würde „5 geschlossen" melden.
- **🔴 CTNL-Kill-Switch laeuft nur auf FK, nicht auf Funded/EK -- nachziehen?**
  (Fund Weekly Checkup KW39, 28.09.) FKs Standalone-Kill-Switch war vom
  21.09. 00:04 bis 28.09. 02:37 aktiv und hielt FK aus 7 CTNL-Trades
  (-8,74 R laut Soll/Ist) heraus. Auf demselben Bein verloren in derselben
  Woche **IQ -2.473,94 USD** (20 Trades, 2 Gewinner) und **EK -304,65 EUR**
  (12 Trades, 0 Gewinner). `ctnl_standalone_drawdown`/`CTNL_KILL_SWITCH`
  kommt nur in `FKInstantFunding-MT5-Bridge/run_once.py` und im Repo-Paper-Bot
  vor, nicht in `Funded-Portfolio-Bridge` oder `EK-Portfolio-Bridge`; das
  Funded-Log hat keinen einzigen Kill-Switch-Eintrag. **Nichts geaendert**
  (Funded wirkt direkt auf echtes Geld). Offen fuer dich: nachziehen, oder
  ueber die Ribbon-Richtung (E6) loesen? Details:
  `reports/weekly/KW39_2026_performance.md` Abschnitt 2.

- **✅ ERLEDIGT 2026-09-25: beide Aufraeum-Freigaben umgesetzt.** KW38 wurde von Hand nachgebaut (`reports/weekly/KW38_2026_*.md`) und die 94 Altstashes geloescht -- vorher geprueft, dabei den faelschlich entfernten OU-Solo-Punkt gefunden und wiederhergestellt. Urspruengliche Frage:
  **(1) KW38/2026 nachbauen?** Der Report fehlt, weil der Task am So 20.09. im
  Standby lag (Details im Changelog vom 24.09.). Die Rohdaten sind noch da
  (`scripts/reports/mt5_2026-W38.json`, `soll_ist_2026-W38.json`), ein
  Nachbau ist also moeglich -- aber er zieht Bridge-/MT5-Daten fuer eine
  Woche, die vier Tage zurueckliegt, und ist ein groesseres Stueck Arbeit.
  Ich habe ihn NICHT angefangen. Sag Bescheid, ob du ihn willst.
  **(2) Die 93 Altstashes loeschen?** Ich habe alle gegen den heutigen Stand
  geprueft: **keine nicht zurueckgeholte Arbeit** drin. Sie sind reine Halde
  und machen echte Probleme unsichtbar. `git stash clear` waere der
  Einzeiler -- ich fasse das ohne dein Okay nicht an, weil es nicht
  umkehrbar ist.
  **Nicht geaendert habe ich die Systemeinstellungen**: die Windows-Wake-Timer
  (Ursache des Ausfalls) und das deaktivierte TaskScheduler-Log liessen sich
  nur mit Adminrechten bzw. einem Eingriff ins Energieprofil aendern. Der
  neue Waechter im 08:00-Digest macht kuenftige Ausfaelle sichtbar, verhindert
  sie aber nicht -- falls du die Ursache selbst beheben willst, ist der
  Hebel "Wake-Timer zulassen" in den Energieoptionen.

- **🟠 ORB-Break-Even im ALTEN Marktorder-Pfad (EK) sitzt auf dem
  SIGNAL-Preis, nicht auf dem echten Fill -- reparieren oder Pfad
  entfernen?** (Fund 2026-09-23 bei der BE-Pruefung.)
  `legs/ny_open_orb/executor.py::manage_open_positions()` schiebt den Stop
  nach dem Teilausstieg auf `state["entry_price"]`, und `_record_entry()`
  speichert dort `signal["entry_price_signal"]` -- den Ausbruchs-Level aus
  der M5-Historie, nicht den Preis, zu dem tatsaechlich gefuellt wurde.
  **Belegt am 18.09., NASDAQ Ticket 269766479:** Fill 29.486,50 (short),
  BE-Stop auf 29.497,04 gesetzt = **10,4 Punkte GEGEN die Position**; die
  Restscheibe ging mit **-0,27 USD statt 0,00** raus. Weil ORB-Entries dem
  Ausbruch hinterherlaufen, ist der Fill systematisch schlechter als der
  Signal-Level -- der "Break-Even" ist damit strukturell ein kleiner
  Verlust-Stop. **Aktuell nicht akut:** seit 2026-09-19 laufen alle
  ORB-Entries ueber `pending_executor.py`, und der nimmt den echten Fill
  (`p.price_open`, Zeile 297/379) -- ebenso die Funded-Bridge (dort schon am
  01.09. gefixt). Der alte Pfad wird aber bei **jedem** Fast-Lauf noch
  aufgerufen (`run_once_fast.py:113`) und wuerde bei einer Rueckkehr zu
  Marktorders sofort wieder falsch stoppen. **Offen fuer dich:** echten Fill
  in `_record_entry()` speichern (klein) oder den toten Marktorder-Pfad
  ganz rausnehmen (sauberer)?

- **🟢 E6 neu bewertet: dein MTF-EMA-Ribbon als Trendrichtung schlaegt alles
  bisher Gepruefte -- und macht die Short-Seite positiv.** Der Ribbon
  (`ema_ribbon.py`, aus deinem Pine-Script) war nur als DEHNUNGS-Filter
  verdrahtet, nie als Richtung. Als Richtung: short im Ribbon-Abwaertstrend
  **Ø R +0,174** (generischer EMA-Stapel: -0,161). Walk-Forward OOS
  **+243,6 gegen +143,4**. Monte Carlo `ribbon long-only`: MedDD **-4,80 %**,
  **P(MaxDD>6 %) 24,2 %** statt 99,9 %, Sharpe **1,02** statt 0,25.
  Keine Parametersuche, Script-Defaults. **Offen fuer dich:** weiter
  mitlaufen lassen (mein Vorschlag, Schattenlauf um den Ribbon ergaenzen),
  oder `ribbon long-only` fuer die Challenge-Konten / `ribbon-konform` fuer
  EK scharf schalten? Vorbehalte: -62 % Trades, verliert in starken
  Trendjahren, Gold-Baisse fehlt im Sample. Details: Befund 15.

- **EK-Mindestlot: E5-c umgesetzt, aber der Rest der Frage steht noch.**
  `ctnl_reversal` haelt auf EK jetzt hoechstens EINE Position
  (`config.CTNL_REV_MAX_CONCURRENT = 1`) -- Beitrag des Beins von 2,59 % auf
  ~0,86 % der Equity. Die Mindestlot-Anhebung bleibt wie von dir entschieden.
  **Weiterhin offen fuer dich:** (a) `ctnl_continuation` riskiert ebenfalls
  das 14-fache seines Ziels und ist NICHT gedeckelt (es ist per Konstruktion
  single-position, der Faktor bleibt aber); (b) ob dasselbe Muster
  `cls_practical` (Ziel 19,40 EUR), `ou_modell` (10,77) und die drei
  ORB-Beine (10,58) trifft -- das habe ich NICHT nachgerechnet, die Ziele
  liegen aber niedrig genug, dass eine Anhebung plausibel ist.

- **Paper-Screening 2026-09-22: ist das Zumachen der einen Tuer okay?**
  Drei Papers gesichtet (Details in
  [[24h-renditestruktur-und-informationskette]]). Zwei Dinge beruhen auf
  meiner Einschaetzung, nicht auf deiner Anweisung:
  **(1)** Ich habe den naheliegenden "Europas/Asiens Close als Richtungs-Prior
  fuer den NY-Open"-Filter **vor dem Bau verworfen** (Kinoshita: Boost +0,07 pt,
  Vorzeichenregel 48,89 % = unter Zufall, waehrend alle anderen Legs +10,6 bis
  +15,0 pt tragen). Spart einen Stage-Zyklus -- sag Bescheid, wenn du ihn
  trotzdem gemessen haben willst.
  **(2)** Delta-VIX/Overnight-Vol als ORB-Tagesfilter habe ich NICHT
  weiterverfolgt, obwohl bisher nur der VIX-*Level* getestet wurde -- weil das
  Paper die *Aenderung* nur fuer das Nachtfenster belegt und sie fuer die
  US-Session selbst insignifikant ist (t=0,5). Falls du das anders siehst, ist
  es testbar (dann aber als Risiko-Skalierung, nicht als binaerer Filter).
  Die vier ORB-Folgetests (Anteil `session_end`-Exits, Gegenprobe zur
  EMA-neutral-Mechanismushypothese, Zeit-Exit 15:45, EU-Feiertagscheck) stehen
  als Vorschlag in [[ny-open-orb-sp500]], **keiner davon ist begonnen**.
  **(3) Das EU-Open-Fenster ist am 23.09. durchgerechnet und negativ
  abgeschlossen** ([[eu-open-renditefenster]]) -- ohne 2020 liegt der Edge
  auf allen drei Instrumenten unter den Handelskosten, und ein Scan ueber
  alle 42 Tagesfenster findet nirgends mehr eine Konzentration. Ich habe das
  vorab festgelegte Abbruchkriterium angewandt und **Phase 6 bewusst nicht
  gerechnet**. Falls du trotzdem eine Monte-Carlo-Sicht darauf willst, sag
  Bescheid -- ich halte sie fuer nicht aussagekraeftig.

*(Die folgenden vier Punkte wurden am 2026-09-23 aus `git stash@{71}` wiederhergestellt -- `git_sync_push` hatte sie am 21.09. beiseitegelegt.)*

- **CTNL-Reversal-Order-Flut: Ursache gefunden UND Fix gebaut (2026-09-21) --
  bitte gegenlesen.** `_cap_concurrent_reversals()` im Scan war ein
  Simulations-Filter, kein Live-Gate; Funded-Portfolio-Bridge und
  FKInstantFunding hatten keinen Deckel gegen die ECHTE Zahl offener
  Positionen. Eingebaut ist jetzt das EK-Gate (`LEG_MAX_CONCURRENT` +
  `_count_open_leg_positions()`, gegen den Broker gezaehlt). Flut vom 09-17
  nachgespielt: 32 Signale -> 3 Positionen statt 32. Details +
  Testprotokoll in `CHANGELOG.md` 2026-09-21.
  **Im Live-Betrieb bestaetigt (2026-09-23 nachgeprueft):** am 22.09. hat das
  Gate ueber den ganzen Tag gegriffen und den Korb sauber abgebaut (8 -> 6 ->
  4 -> 3 offene Positionen, jedes geblockte Signal als Sammelmeldung
  protokolliert). Der Zaehler prueft dabei wirklich gegen den Broker
  (`_count_open_leg_positions()` -> `positions_get(ticket=)`), nicht gegen den
  State -- die 37 (TTP) bzw. 51 (IQ) verwaisten State-Eintraege blaehen ihn
  also NICHT auf. Offen bleiben nur deine zwei Rueckmeldungen unten.
  **Auf meiner Annahme, nicht auf deiner Ansage:** (a) der Deckel gilt auch
  fuer `ctnl_continuation` (1) -- das Bein ist per Konstruktion
  single-position, der Deckel ist reine Absicherung gegen denselben
  `data_end`-Mechanismus; (b) ein geblocktes Signal bekommt bewusst KEINEN
  "missed"-Eintrag, wird also nach dem naechsten Exit wieder handelbar,
  statt endgueltig verworfen zu werden. Sag Bescheid, falls du eins von
  beidem anders willst.

- **CTNL: Kostenvalidierung + Diagnose + Optimierung fertig -- vier
  Entscheidungen E1-E4 liegen bei dir** (`projects/ctnl-kostenvalidierung.md`).
  **E1 Kostenzahl korrigieren** (`spread_bps` 8,0 -> gemessen 0,53-2,01,
  broker-getrennt). **E2 Regime-Filter** auf `ctnl_reversal` -- der einzige
  Hebel, den die Optimierung gefunden hat: Monte Carlo Median MaxDD
  -15,6 % -> -8,4 % UND Median Return +18,8 % -> +32,2 %. Vorschlag: erst
  mitlaufen lassen (protokollieren, nicht handeln). **E3
  `ctnl_continuation` stilllegen** -- PF 0,94 ueber 436 Trades und 10 Jahre,
  Monte Carlo Median Return -16,4 %; keine Variante dreht das.
  **E4 Risikokalibrierung neu ziehen** -- die dokumentierten FK-Zahlen
  (Median MaxDD -3,5 %) stammen aus EINEM OOS-Jahr; ueber zehn Jahre liegt
  allein das Reversal-Bein bei -15,6 %. Reihenfolge: E1-E3 vor E4.
  **Nicht anfassen:** TP (5R sitzt auf einem flachen Plateau), SL
  (0,5R-Stop killt 49,5 % der Gewinner), Signal-Parameter (IS-Sieger in
  8/8 Jahren, verliert OOS), Ausfuehrungstakt (verkuerzbar, aber
  P&L-Gewinn nicht belegt).

- **Broker-History von ttp1 konnte ich nicht ziehen** -- der Zugriff auf die
  Zugangsdaten im Bridge-Backup wurde vom Auto-Mode-Classifier blockiert.
  Die exakte realisierte CTNL-P/L auf dem gebreachten Konto ist damit offen;
  meine Zahlen stammen aus Bridge-Log + State + Goldkurs. **Offen fuer
  dich:** entweder im MT5-Terminal selbst nachsehen (Konto 504069845,
  16.-19.09., Symbol XAUUSD) oder mir die Berechtigung geben.

- **OU-Modell: Ticker in S&P UND Nasdaq-100 landen auf der Variante OHNE TP --
  welche Config soll gelten?** (Fund 2026-09-23, nichts geaendert.)
  `ou_paper_backtest/scanner.py` schreibt je Universum eine eigene Zeile; das
  validierte 1:1,5-TP gilt laut Code-Kommentar NUR fuer S&P, nasdaq100/dax
  bleiben bewusst auf "kein TP". Steht ein Ticker in beiden Indizes (MDLZ,
  PEP), stehen beide Zeilen als `tradeable=True` in `scanner_signals.csv`, und
  EK nimmt faktisch die Nasdaq-Zeile: der erste Versuch scheitert am 0-Tick
  frisch selektierter Symbole (`entry_deviation_too_large, deviation=1.0`), der
  zweite geht durch. **Real passiert bei ADI (02.09.) und MDLZ (22.09.)** --
  exakt die einzigen zwei der 21 EK-Positionen ohne TP. **Offen fuer dich:**
  soll bei doppelten Tickern die S&P-Zeile (mit validiertem TP) gewinnen, oder
  ist "kein TP" die gewollte konservative Variante?

- **Verwaiste State-Eintraege nach dem manuellen CTNL-Aufraeumen -- soll ich
  sie nachziehen?** (2026-09-23.) Der Nutzer hat am 21.09. 18 CTNL-Positionen
  von Hand geschlossen (bestaetigt). Im State stehen dadurch 37 (TTP) bzw. 51
  (IQ) `ctnl_reversal`-Eintraege auf `status="placed"` ohne offene Position.
  Fuer die Konkurrenzgrenze harmlos -- `_count_open_leg_positions()` prueft
  gegen `positions_get()` --, aber als Historie/Soll-Ist-Grundlage unbrauchbar.

- **🔴 EK-Hebel: welcher Zeithorizont soll gelten?** (2026-09-23, komplette
  Nachrechnung, nichts geaendert). Die 7,8 % der Kalibrierung und meine 33,9 %
  sind beide richtig -- verschiedene Horizonte: 40 % Drawdown reissen binnen
  1 Jahr 3,6 %, binnen 2 Jahren 7,8-9,8 % (= die dokumentierte Zahl), ueber die
  volle 6-Jahres-Historie 39,3 %. **Faehrst du EK ueber Jahre, ist die hohe
  Zahl die relevante** -- ein 20-%-Rueckgang ist dann praktisch sicher
  (P = 100 %). Staffel: 100 % Hebel -> CAGR 228 %, P(DD>40 %) 39,3 % | 85 % ->
  179 %, 17,9 % | **70 % -> 136 %, 4,6 %** | 60 % -> 111 %, 1,1 %.
  **Zusatzbefund:** `ou_modell` laeuft mit Faktor 4,40x statt dokumentierter
  2,20x -- soll ich es zurueckziehen? Details:
  [[ek-risiko-kalibrierung-audit]].

- **✅ ERLEDIGT 2026-09-23 (Eintrag am 30.09. nachgezogen): ttp1 wurde vollstaendig ausgebaut.** Auf deinen Entscheid aus allen Systemen entfernt (Bridge-Config bereits am 19.09., dann Scripts + Reports), Challenge als abgeschlossen gewertet -- siehe CHANGELOG 2026-09-23. **Dieser Punkt stand bis heute faelschlich als offenes 🔴 im Dashboard**: die damalige Korrektur ging durch den `git_sync_push`-Stash verloren, der CHANGELOG-Eintrag ueberlebte. Der urspruengliche Text zur Dokumentation:

  > 🔴 ttp1 (Echtgeld, TTP Konto 1) darf seit 2026-09-18 09:58 nicht mehr
  > handeln -- bitte beim Anbieter klaeren. `trade_allowed=False` vom Server,
  9 abgelehnte Entries (`10026 "AutoTrading disabled by server"`). Keine
  eigene Regelverletzung erkennbar: Equity 94.711,78 (−2,0 % seit Kontostart,
  Tagesverlust −0,99 %, Peak-DD −2,2 %), Kill-Switch inaktiv; das TTP-**Demo**
  am selben Server handelt normal. 7 Positionen offen, alle mit SL. Ich habe
  nichts geaendert. **Offen fuer dich:** TTP-Dashboard/Mail pruefen (Konto
  gesperrt, Challenge beendet, Regel-Review?). **Offen fuer mich, auf deine
  Freigabe:** eine Sammelwarnung "Konto darf nicht mehr handeln" einbauen --
  heute faellt so etwas nur als einzelne Entry-Fehler auf.

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

- **🟢 OU-Modell: Logik D läuft live, Wiedereinstiegs-Drehtür geschlossen**
  (Umbau 23.09., Fix 30.09.). Stop 8 Sigma, kein Breakeven, kein TP, Ausstieg
  am MA20, `BB_K` 2,25, `max_hold` 10 (schließt jetzt wirklich).
  **Live bewährt:** beide Bridges steigen aus (EK per MA20-Ausstieg, Funded per
  Abgleich „Modell ist ausgestiegen").
  **Gefunden und behoben 30.09.:** AIG wurde **6× eröffnet und 6× geschlossen**,
  am 29.09. dreimal in 30 Minuten. Ursache: im Backtest werden Ein- und
  Ausstieg auf demselben Tagesschluss geprüft und schließen sich damit aus —
  live kam der Ausstieg vom Live-Tick, der Einstieg vom Vortagessignal. Jetzt
  zwei Sperren im EK-Executor: Einstieg prüft dieselbe MA20-Marke wie der
  Ausstieg, und höchstens ein Einstieg je Titel und Signaltag. Gegen die echten
  Kurse vom 29.09. nachgespielt. Funded war nicht betroffen (geprüft).
  **Unter Beobachtung (Entscheid 30.09.):** Stopdeckel und Preisfilter
  bewusst verworfen — weiter mit der aktuellen Risikologik. Damit akzeptiert:
  **7,70 % offenes Risiko statt 4,76 %** auf EK (Mindestlot-Anhebung, AXP
  allein 2,30 %). Zwei Funded-Positionen (**DD**, **EOG**) laufen seit dem
  23.09. bzw. 21.09. ohne Modellführung nur mit Broker-SL, bewusst nicht
  geschlossen. **Worauf schauen:** ob die Drehtür wirklich weg ist (Einstiege
  je Titel ≤ 1 pro Tag), ob das offene Risiko über 8 % steigt, und ob DD/EOG
  wieder im Scan auftauchen.
  Details: [[ou-modell-kostenvalidierung]].
- **✅ EK/OU: Max-Holding schliesst jetzt wirklich** (offen seit 2026-09-17,
  **behoben 2026-09-23 im Logik-D-Umbau** — `manage_open_positions()` ruft
  `_close_position(pos, "maxhold")` statt nur CRITICAL zu loggen; dazu neu der
  MA20-Ausstieg. Der Text unten beschreibt den Stand VOR dem Umbau). Der Rueckstand ist weg -- der Nutzer hat am 23.09.
  gegen 21:41 alle 9 ueberfaelligen Positionen von Hand geschlossen (DAL 33
  Tage, ADI/DHI/GRMN 20, AMGN/EXPE 12, LEN/COF/GIS 11; zusammen **+20,56 EUR**,
  am Broker als `reason=1` belegt). **Die Ursache ist unveraendert:**
  `legs/ou_modell/executor.py::manage_open_positions()` loggt nur CRITICAL und
  schliesst nie -- der naechste Schwung altert genauso zu, bis das jemand
  wieder von Hand aufraeumt. Gehoert zur OU-Optimierung, nicht still geaendert. `legs/ou_modell/executor.py::
  manage_open_positions()` loggt nur CRITICAL. Weicht vom Backtest ab und
  verlaengert den Swap -- gehoert zur OU-Optimierung, nicht still geaendert.
- **✅ ERLEDIGT 2026-09-30: MNST-Split abgeschlossen (Nutzerauftrag).** Die
  −2.492,56 $ lagen auf **TTP Konto 1 (ttp1)** — genau dem Konto, das am
  2026-09-23 auf deinen Entscheid vollstaendig ausgebaut und als abgeschlossen
  gewertet wurde. Die Forderung gehoert damit zum abgeschriebenen Konto; eine
  Support-Anfrage waere eine Anfrage zu einer beendeten Challenge. **Nicht
  weiterverfolgt.** Vorgang zur Dokumentation: Tickmill buchte die Position
  beim 2:1-Split korrekt um, TTP nicht — der alte SL loeste zum halbierten
  Kurs aus, ohne Ausgleichsbuchung.

- **🟠 Split-Schutz fehlt weiterhin — abgetrennt vom MNST-Punkt (2026-09-30).**
  Der Geldbetrag oben ist erledigt, **die Ursache nicht**: ich habe geprueft,
  in `Funded-Portfolio-Bridge`, `EK-Portfolio-Bridge` und
  `FKInstantFunding-MT5-Bridge` gibt es **keinerlei Behandlung von
  Aktiensplits** (die Treffer auf "split" sind alle `leg.split()` bzw.
  `executor.split_volume()`). Gleichzeitig handelt `ou_modell` auf Funded UND
  EK Einzelaktien — dasselbe Ereignis kann sich also jederzeit auf einem der
  aktiven Konten wiederholen. Den Punkt mit dem Konto zu schliessen waere
  bequem, aber falsch. **Offen fuer dich:** soll ich einen Split-Check bauen
  (Vergleich Positionspreis gegen aktuellen Kurs bei Einzelaktien, Alarm statt
  Automatik)? Ich habe nichts geaendert.
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

- **Kurztakt-Task-Ausfälle (1–2 h, 09-07 bis 09-11) beobachten bis ~2026-09-24**
  (Nutzerentscheid 2026-09-17). Die Ausfälle lagen VOR den Zeitzonen-Sprüngen
  (ab 09-15), Ursache also offen. Tritt nach dem Zeitzonen-Fix erneut eine
  Lücke auf: Task-Scheduler-Verhalten gezielt instrumentieren. Sonst löschen.
  **Zwischenstand 2026-09-23 (gemessen):** 1.275 Fast-Läufe seit 09-17, **keine
  einzige Lücke** außer der Wochenendpause (Fr 18.09. 23:58 -> Mo 21.09. 00:03)
  und den 65 Min am 17.09. 04:13-05:18, also am Fix-Tag selbst. Läuft morgen
  ohne neue Lücke durch, kann der Punkt weg.
  **🟠 Nachgemessen 2026-09-24 (Stichtag): der Punkt kann NICHT weg -- am
  23.09. selbst gab es eine Lücke.** `EK-Portfolio-Bridge-Fast` (2-Min-Takt)
  fehlt am 23.09. von **09:48:13 bis 10:21:07 = 33 Min., ~16 ausgefallene
  Läufe**. Der 09:48-Lauf endete sauber (`FAST-Task beendet`), danach hat der
  Task Scheduler schlicht nicht mehr gefeuert -- **kein hängender Prozess,
  kein Absturz, keine Log-Zeile**. Die Zwischenstands-Messung vom 23.09. hat
  das nicht gesehen (vermutlich vor 09:48 gezogen). **Nicht maschinenweit:**
  die EK-Slow-Lane lief im selben Fenster normal (09:59, 10:14), ebenso die
  5-Min-Lanes von Funded und FK (09:53/09:58/10:03/10:08/10:13) -- **nur der
  2-Min-Task fiel aus**. **Ein Nebenbefund als Spur:** der Funded- UND der
  FK-Fast-Lauf um 10:18 brauchten statt 8 Sek. rund **2 Min.** (erste
  Log-Zeile erst 10:20:11 bzw. 10:20:09) -- ein Lastberg auf der Maschine
  genau am Ende des Lücken-Fensters, und am Vormittag des 23.09. liefen die
  CTNL-Ribbon-Backtests. **Heute (24.09.) bis 10:10: 306 Läufe, lückenlos.**
  Damit ist die 09-11-Ursache weiter offen und der vorab vereinbarte
  Abschluss hinfällig. **Offen für dich:** gezielt instrumentieren (wie am
  17.09. vereinbart -- Task-Scheduler-Event-Log `TaskScheduler/Operational`
  auf `Missed`/`LaunchFailure` für die Fast-Tasks auswerten), oder erst die
  Lastspur verfolgen (schwere Backtests nicht parallel zu den Live-Takten
  laufen lassen)? Nichts geändert.

- **Lint 09-21: zwei mehrfach verlinkte, aber nie angelegte Notizen —
  anlegen und wo?** `[[bein-matrix-ist-soll-paper]]` (referenziert von
  `areas/bridge-infrastruktur-vergleich.md` 2x + `reports/weekly/
  KW37_2026_education.md`) und `[[systemlandkarte]]` (referenziert von
  denselben zwei Dateien) zeigen beide ins Leere — kein Tippfehler, beide
  klingen nach eigenständigen, wiederholt referenzierten Konzepten (Soll-
  Ist-Vergleich der Beine je Bridge vs. Paper-Bot bzw. eine Gesamt-
  Systemübersicht "wo die Kette verliert"). Ob/wo diese Notizen angelegt
  werden (`areas/` vermutlich), liegt bei dir — nicht selbst angelegt.
  **✅ Nachtrag Lint 28.09.: beide Notizen existieren jetzt**
  (`areas/bein-matrix-ist-soll-paper.md`, `areas/systemlandkarte.md`) — der
  aktuelle Lint-Lauf findet 0 tote Wikilinks. Nicht geprueft, wer/wann sie
  angelegt hat oder ob das deine urspruengliche Frage (ob/wo) beantwortet.
  Bitte bestaetigen, dann kann der Punkt raus.


### Offene Aufgaben



- **FK SP500 „Invalid stops“: behoben 2026-09-17** (SL aufs Tick-Raster).
  Nur noch: ersten echten SP500-Entry im FK-Log gegenlesen, dann Punkt löschen.
  **Stand 2026-09-23: noch kein Gegenbeweis moeglich** -- letzter Fehlschlag
  16.09. 15:53, seit dem Fix ist schlicht kein SP500-Signal mehr aufgetreten
  (21./22.09. beide `filtered_out (Bias 1.0)`). Punkt bleibt bis zum ersten
  echten Entry offen.

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
  2026-09-28-Lint, unveraendert seit 2026-09-09) — u.a. Edge-Genesis/-Decay,
  Risk-Factor-Investing, Sektor-Rotation, "Six Repos One System", "How
  system works" — noch nicht durch den CODE-Prozess.

**Niedrig**
- **✅ `[[ou-modell-kostenvalidierung]]` war nie tot, nur nie committet**
  (Lint 09-21, erledigt 09-23 mit `1fc8645`). Die Notiz existierte seit dem
  17.09. nur im Arbeitsverzeichnis — untracked, daher kein Treffer in der
  Git-Historie. Jetzt getrackt, zusammen mit drei weiteren Research-Notizen.
- **Statustabelle: "Zuletzt geprüft" bei `OU-Modell-ScannerHourly` ist
  26 Tage alt** (Lint 28.09., Schwelle 21 Tage; Stand: 2026-09-02).
  Reiner Alters-Hinweis aus dem Lint-Skript, kein inhaltlicher Befund —
  Zeile bei Gelegenheit gegen den echten Task-Scheduler-/Scanner-Status
  nachpruefen und Datum auffrischen (CLAUDE.md Punkt 4).

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
| Funded-Portfolio-Bridge (TTP 6 Beine @1/6, IQ 5 Beine @1/3) | TTP Konto 2 (504072729) + BeyondIQCapital (16054) — **2 Konten** (IQ 15514 am 2026-09-07 entfernt, **TTP Konto 1 / ttp1 am 2026-09-23 vollstaendig ausgebaut**) | **LIVE — DRY_RUN=False** (alle 6 Beine `source="lake"`; **seit 09-13 kontospezifisch: IQ ohne `ou_modell`, Kapitalanteil 1/3 statt 1/6 — IQ handelt keine Aktien**; IPC-Timeouts 09-08 09:52-12:24 Uhr, seither stabil, siehe 🔍 Bestätigung) | Ready (alle 15 Min, Mo–Fr)      | **16.09.** orb_sp500 (TTP1) | 2026-09-13      |
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

_Letzter Lint-Durchlauf: **2026-09-28** (geplant, `second-brain-lint`).
Ergebnis: 0 tote Wikilinks (die beiden am 09-21 gefundenen Notizen
existieren jetzt, siehe Bestätigungspunkt oben), 0 verwaiste Seiten,
1 veraltete Statustabellen-Zeile (`OU-Modell-ScannerHourly`, → Niedrig);
14 unverarbeitete Clippings unverändert seit 09-09. Verweise nach
außerhalb von `knowledge/` als Pfad in Backticks (siehe `README.md`)._

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

- **CTNL: Engine-Pfad und Live-Pfad laufen nach der ersten Welle auseinander**
  (2026-09-30). Am 29.09. um 17:00–17:30 UTC sind sie deckungsgleich, danach
  handelt die Engine 19:15–19:45 und am 30.09. 08:15–08:45, live dagegen
  18:15–18:45, 07:00–07:30 und 12:45/13:00. Vermutlich sind die 3er-Kappung
  (Sim) und die echten Positionen/Stops verschieden. Eine Zeitzone ist es nicht.

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
