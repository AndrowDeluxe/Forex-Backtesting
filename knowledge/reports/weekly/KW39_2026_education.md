# Weekly Checkup - Education - KW39/2026

**Abgedeckte Woche: Mo 2026-09-21 bis So 2026-09-27.** Erzeugt am Mo
2026-09-28 durch den geplanten Report-Lauf. **Diese Fassung baut auf dem
Zwischeneintrag vom 23.09. auf**, den der Nutzer vorgezogen hatte. Dessen
Inhalt (Papers, EU-Open-Fenster) steht unten weitgehend unveraendert in
Abschnitt 3 und 4. Neu hinzugekommen sind die Abschnitte 1, 2 und 5 bis 7
sowie die Erkenntnisse vom Mittwochabend bis Freitag.

## 1. Was stand die Woche an / Hauptfokus

**Die dichteste Research-Woche seit Wochen, fast alles an einem Tag.** Von
den rund 35 Commits von Hand fallen 23 auf Mittwoch, den 23.09. Inhaltlich
waren es vier Straenge:

1. **CTNL komplett durchleuchtet** (Befunde 10-17): Regime-Diagnose,
   Walk-Forward beider Beine, Struktur-gegen-Regime-Test, Long/Short-Trennung,
   MTF-Trendbestaetigung und der eigene EMA-Ribbon als Richtung. Umgesetzt
   wurde live davon nur **E5-c**: EK haelt hoechstens eine `ctnl_reversal`-
   Position. Der Rest laeuft als Schattenlauf bzw. wartet auf deine
   Entscheidung.
2. **OU-Modell umgebaut** auf Logik D + Signalseite (Funded + EK). Dazu die
   Scanner-Ausstiegsschwellen fuer alle Universumstitel.
3. **Risiko und Konten:** EK-Hebel 1,2x, ORB Variante C (Pending-Orders),
   ttp1 endgueltig ausgebaut, verwaiste Positionen von Hand geschlossen.
4. **Das Fundament repariert:** Der Git-Sync-Stash, der Arbeit frass, ist
   abgestellt; der verlorene Stand wurde aus den Stashes zurueckgeholt;
   `mt5_pull.py` hat einen Fenster-Fix; der fehlende KW38-Report wurde
   gefunden, nachgebaut und ein Waechter dafuer gebaut.

Dazu die Paper-Sichtung vom Montag/Dienstag und das EU-Open-Fenster (siehe
Abschnitt 4).

## 2. Aktive Zeiten

Commits von Hand je Tag, ohne automatische Snapshots:

| Mo | Di | Mi | Do | Fr | Sa | So |
|---|---|---|---|---|---|---|
| 2 | 2 | 23 | 3 (+3 kurz nach Mitternacht) | 0 | 0 | 0 |

**Ein Tag hat die Woche getragen.** Der Mittwoch hatte einen Vormittagsblock
(10:04-10:19) und dann einen langen Abend von 21:39 bis 23:04. Allein dort
liegen 19 Commits. Do Vormittag und die Nacht auf Freitag (00:31-00:43)
waren Nacharbeiten. **Fr bis So: nichts.** Das deckt sich mit dem Muster aus
KW36/37: Viel wird an einem intensiven Abend gesammelt committet. Neu ist,
dass das Wochenende diesmal wirklich frei war. Die Bridges hielten sich an
ihre Wochenend-Pause (Logs Fr 23:xx bis Mo 02:29 still).

## 3. Meine Main Erkenntnisse

**Ein Schutzmechanismus, der nur auf einer von drei Bridges existiert, ist
kein Schutzmechanismus fuer das Portfolio.** Das ist die wichtigste Lehre der
Woche, und sie kam aus der Live-Auswertung, nicht aus der Forschung. Der
CTNL-Kill-Switch hielt FK sieben CTNL-Trades (-8,74 R) vom Leib. IQ und EK
haben ihn nicht und verloren auf demselben Bein ca. 2.470 USD bzw. 305 EUR.
Das Muster kennen wir schon aus KW38 ("das System meldete X und tat Y"),
hier in der Form: **"nachgeruestet in alle Bots" hiess "in alle
Paper-Bots".**

**Die CTNL-Forschung vom Mittwoch hat genau diese Woche vorhergesagt.** Der
Edge liegt auf der Long-Seite. Er ist im Kern eine Wette auf steigendes Gold,
keine Struktur (Memory `ctnl_edge_nur_long`). Der eigene MTF-EMA-Ribbon war
nur als Dehnungsfilter verdrahtet, obwohl er als **Trendrichtung** der
staerkste Hebel ist (Memory `ctnl_ribbon_als_richtung`). Und Gold fiel von
Mo bis Do um ca. 100 Dollar. Die Long-Reversals, die dabei ausgestoppt
wurden, sind das Lehrbuchbeispiel fuer das, was der Ribbon-Filter verhindern
soll. **Die Erkenntnis lag Mittwochabend vor, die Verluste liefen Mi/Do
weiter.** Das ist kein Vorwurf. Es zeigt nur, wie lang der Weg von "Befund"
zu "live" ist, wenn die Freigabe bewusst beim Nutzer liegt.

**Erst pruefen, ob vorhandene Bausteine richtig verwendet werden, dann
Parameter suchen.** Die Walk-Forward-Optimierung verwarf fast alle
TP/SL/Signal-Parameter; nur der Effizienz-Regime-Filter hielt stand (Memory
`ctnl_regime_filter_einziger_hebel`). Den groessten Hebel fand erst der Blick
auf die **Verdrahtung** eines schon vorhandenen Bausteins (Ribbon).

**Auf einem kleinen Konto dreht der Mindestlot die Risiko-Hierarchie um.**
0,01 Lot XAUUSD riskiert auf EK schon das 46-fache dessen, was
`ctnl_reversal` riskieren sollte (Memory `ek_mindestlot_kehrt_hierarchie_um`).
Das kleinste Bein wird dadurch zum groessten Risiko. Diese Woche war der
Beweis: 12 Mindestlot-Trades machten 83 % des EK-Verlusts.

**Die Reporting-Kette kann still luegen, an drei verschiedenen Stellen:**
- `mt5_pull.py` verlor die letzten Stunden des Tages. Behoben am 23.09.
  (Memory `mt5_pull_fenster_kappt_tagesende`).
- `git show stash@{N}` versteckt gestashte Zeilen. Richtig ist
  `git diff stash@{N}^ stash@{N}` (Memory `git_stash_recovery_show_vs_diff`).
- **Neu in diesem Lauf:** Ein frisch gestartetes Terminal liefert eine leere
  Deal-Historie ohne Fehlermeldung (Performance-Report, Kasten oben).

Gemeinsamer Nenner: **"Keine Zeilen" ist kein Befund, solange die Quelle
nicht bewiesen hat, dass sie geantwortet hat.**

**Git-Sync hat eine Woche lang Arbeit gefressen.** Die Auto-Tasks stashten
den gemeinsamen Working Tree und machten bei Konflikten `reset --hard`
(93 Stashes). Am 23.09. behoben (Memory `git_sync_stash_frisst_sessionarbeit`),
am 24.09. nachverifiziert. **Die Nebenwirkung wirkt aber nach:** Der am 25.09.
"wiederhergestellte" Dashboard-Punkt zu den OU-Solo-Waisen war da bereits
erledigt. Er wurde zurueckgeholt, weil der Beleg fehlte, dass er geschlossen
war (siehe Performance-Report, Punkt 6.2).

**Aus dem Zwischeneintrag vom 23.09. (unveraendert gueltig):**

- **In unserem ORB-Handelsfenster gibt es keine Risikopraemie zu ernten, und
  das ist eine gute Nachricht.** Bondarenko/Muravyev: Die US-Cash-Session
  09:30-16:15 ET bringt nur +3,44 % p.a. bei **t=0,89**. Die gesamte
  Aktienrendite entsteht nachts. Der Einwand "long-only erntet nur Beta"
  greift beim [[ny-open-orb-sp500]] also nachweislich nicht; der Vorteil
  muss konditional sein (Memory `us_cash_session_hat_keine_risikopraemie`).
- **Der ORB hat nach fast zwei Monaten immer noch keinen dokumentierten
  Mechanismus.** Der EMA-neutral-Filter (Sharpe 0,56 -> 1,05) steht auf
  reiner Backtest-Evidenz, und [[edge-card-workflow]] Regel 4 sagt dazu:
  "Ein Backtest ist KEIN Mechanismus." Kinoshitas Opening-Gap-Befund liefert
  einen Kandidaten. **Das ist eine Hypothese, kein Befund.**
- **Wer einen Cross-Market-Filter misst, muss gegen Eigenmomentum
  kontrollieren.** Kinoshitas Europa->NY-Leg fiel von scheinbar 72 %
  Trefferquote auf +0,07 Punkte (Vorzeichenregel 48,89 %, also unter
  Zufall).
- **Eine ueberraschend grosse Zahl ist zuerst ein Bug-Verdacht, kein Fund.**
  Die Paarung von Mitternachtsfenstern ueber den Kalendertag ergab eine
  Scheinrendite von -13 bis -19 % p.a.

## 4. Neues Wissen diese Woche (Papers/Ideen)

**Drei externe Papers (22.09.), nach Phase 2+3 gesichtet, kein Code, kein
Eingriff in laufende Bots.**

- [[24h-renditestruktur-und-informationskette]] (neu, 22.09.): New York
  **produziert** Information (Kinoshita) und **erntet keine Risikopraemie**
  (Bondarenko/Muravyev). Europa erntet die Praemie und liefert NY keine
  Information.
- [[eu-open-renditefenster]] (neu 22.09., **am 23.09. negativ
  abgeschlossen**): Das Paper ist sauber (15/15 Jahre positiv, White-RC,
  Bonferroni), **aber das Sample endete 2018**. Ohne 2020 liegt der Edge
  unter dem Spread (0,26 bps Edge gegen 0,39 bps Kosten). Phase 6 bewusst
  nicht gerechnet. **Positiver Nebenbefund:** Die Nacht-Spreads unserer
  Index-CFDs sind so eng wie tagsueber (Tickmill 0,23-0,39 bps). Details in
  Memory `eu_open_edge_zerfallen`.
- **Bewusst nicht uebernommen:** Richtungsfilter Europa/Asien fuer den
  NY-Open (Leg tot), Delta-VIX als ORB-Filter (fuer die US-Session t=0,5),
  Beta-Law (versagt auf Index-Ebene).

**Geaenderte PARA-Notizen der Woche** (Forschungsstand, keine neuen Papers):
- [[gold-ctnl-edge-portfolio]] und [[ctnl-kostenvalidierung]]: Befunde 10-17
  der CTNL-Untersuchung.
- [[ou-modell-kostenvalidierung]]: Logik D + Signalseite, BB_K als einziger
  Hebel.
- [[ek-risiko-kalibrierung-audit]]: Die 7,8 % gegen 33,9 % sind zwei
  Zeithorizonte, kein Fehler.
- [[orb-exit-logik-neubewertung]] und [[ny-open-orb-sp500]]: Variante C und
  Paper-Einordnung.
- [[bein-matrix-ist-soll-paper]], [[realkosten-und-ausfuehrungs-probe]],
  [[systemlandkarte]].

**Ideen-Inbox:** In dieser Woche kam **kein neuer Eintrag** hinzu. Die
verwertbaren Straenge sind direkt als PARA-Notiz oder Dashboard-Rueckfrage
gelandet. Der aelteste unsortierte Punkt ("FK-CLS-Scan liefert einen Trade am
Sonntag", 17.09.) ist weiterhin nicht untersucht.

## 5. Verbesserungen

- **EK `ctnl_reversal` auf 1 gleichzeitige Position gedeckelt** (E5-c). Live
  wirksam ab 24.09., im Log nachweisbar.
- **Git-Sync stasht nicht mehr, wenn es nichts zu mergen gibt**
  (`a57de64`, `bf06bfc`). Die Ursache der verlorenen Arbeit ist damit weg.
- **Verlorener Arbeitsstand aus den Stashes zurueckgeholt** (`fd3809d`,
  `26ffea3`).
- **`mt5_pull.py` Fenster-Fix:** Tagesabzuege verlieren die letzten Stunden
  nicht mehr.
- **Waechter fuer fehlende Weekly-Reports** im 08:00-Digest (`3692f76`).
- **OU-Modell auf die validierte Logik D umgestellt**: von "verliert
  zuverlaessig" auf "verdient wenig" (OOS PF 0,83 -> 1,08).
- **Alle verwaisten Positionen geschlossen** (Handaufraeumen am 23.09.).
  Keine Position mehr ueber dem Haltelimit.
- **Soll/Ist ordnet auf EK das Gold-Bein wieder zu** (in KW38 unsichtbar).

## 6. Verschlechterungen / offene Probleme

- **CTNL-Kill-Switch nur auf FK**: Funded/EK handelten das Bein ungebremst
  durch eine Gold-Schwaeche. Neu entdeckt, nicht behoben.
- **EK: vierte Verlustwoche in Folge, -19 % im September.** Parallel wurde
  der Hebel auf 1,2x erhoeht.
- **Soll/Ist fuer ORB seit Variante C vermutlich blind:** Pending-Order-
  Entries werden als "nie gesehen" gefuehrt, und `orb_us30` hat im Soll kein
  Signal.
- **Handtrades auf dem FK-Bot-Konto:** September -1.232,82 USD aus 4
  Positionen. Die Frage aus KW37 ist offen.
- **MT5-Abzug still leer auf kalt gestartetem Terminal.** In diesem Lauf
  aufgefallen und umgangen, aber nicht im Code abgesichert.
- **Dashboard-Punkt "OU-Solo-Waisen offen" ist ueberholt**, steht aber noch
  drin (wartet auf deine Bestaetigung).
- **Report-Lauf erneut verspaetet** (Mo 02:29 statt So 18:00). Die
  Wake-Timer-Ursache ist unveraendert.

## 7. Optimierungsmoeglichkeiten

Nach Gewicht sortiert:

1. **Entscheiden, ob der CTNL-Kill-Switch auf Funded und EK nachgezogen
   wird.** Der Code liegt in `FKInstantFunding-MT5-Bridge/run_once.py`
   fertig vor, und die Woche hat seinen Wert in Dollar gezeigt. Auf Funded
   wirkt ein Commit an `challenge_portfolio/paper_bot.py` sofort auf echtes
   Geld, deshalb ist das eine Nutzerentscheidung.
2. **Die offene Ribbon-Frage (E6) entscheiden.** Sie adressiert genau das
   Verlustmuster dieser Woche (Long-Reversals gegen den Trend).
3. **EK-Risiko als Ganzes ansehen:** Mindestlot, Hebel 1,2x und vier
   Verlustwochen gehoeren zusammen betrachtet, nicht Bein fuer Bein.
4. **Soll/Ist fuer ORB Variante C reparieren**, bevor der naechste Report
   darauf aufbaut. Ausserdem **`mt5_pull.py` gegen leere Historie
   absichern** (Retry oder Warnung bei 0 Deals trotz offener Positionen).
5. **Die Handtrade-Frage fuer die Bot-Konten klaeren.** Entweder eigene
   Konten fuer Handtrades, oder die Handpositionen im Risikodeckel mitzaehlen.
6. **Den Wake-Timer freigeben** (Energieoptionen), damit der Report wieder
   am Sonntag laeuft statt montags um halb drei.
