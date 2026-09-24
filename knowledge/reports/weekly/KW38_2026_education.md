# Weekly Checkup - Education - KW38/2026

> **Nachgebaut am 2026-09-25 von Hand** (Nutzerauftrag). Der geplante Lauf am
> So 20.09. fand nie statt -- Rechner im Standby, Wake-Timer auf "nur
> wichtige", Details im CHANGELOG vom 24.09. Quellen sind git-Historie der
> Woche, die acht in dieser Woche geschriebenen Memory-Eintraege und die
> beiden Abzuege, die die Automatik noch erzeugt hatte. Zahlen zur
> Performance stehen im Schwesterbericht
> [KW38 Performance](KW38_2026_performance.md).

**Abgedeckte Woche: Mo 2026-09-14 bis So 2026-09-20.**

## 1. Was stand die Woche an / Hauptfokus

**Infrastruktur, nicht Strategie.** Elf Commits von Hand, kein einziger davon
an einer Handelslogik -- die Woche ging fast vollstaendig fuer Fehlersuche an
den Bridges und am Berichtswesen drauf. Bezeichnend: **acht neue
Memory-Eintraege, aber keine einzige neue PARA-Notiz.** Es wurde nichts
Neues erforscht, es wurde repariert.

Der rote Faden durch alle acht Funde ist derselbe: **das System meldete X
und tat Y.** Ein Bein galt als aktiv und handelte nicht; ein Symbol galt als
verfuegbar und lieferte keinen Kurs; ein Filter galt als Begrenzung und
begrenzte nur die Simulation. Das ist kein Zufall von acht Einzelfehlern,
sondern ein Muster -- siehe Abschnitt 7.

## 2. Aktive Zeiten

Gearbeitet wurde **Mo-Mi vormittags** (14.09. 06:13-09:07, 15.09. 10:23-10:26,
16.09. 09:08), einmal **Di abends** (15.09. 21:08, der CLS-Crash-Fix) und
dann konzentriert **Sa nachmittags** (19.09. 14:21-14:32, vier Commits in
elf Minuten fuer den Git-Sync-Rueckstand).

**Do und Fr: kein einziger Commit** -- und genau das waren die beiden
Handelstage, an denen es teuer wurde (EK Do -94,75 EUR, TTP Do -556,93 USD
und Fr -403,02 USD). Die Bots liefen unbeaufsichtigt durch die schlechteste
Phase der Woche. Das ist keine Kritik, sondern der Normalfall bei
automatisierten Systemen -- aber es erklaert, warum die 24
Risiko-Limit-Ereignisse vom 17./18.09. erst im Nachhinein auffielen.

## 3. Meine Main Erkenntnisse

Acht Memory-Eintraege in sieben Tagen -- die dichteste Lernwoche bisher.
Vier davon haben unmittelbar mit echtem Geld zu tun:

**Ein nicht handelbares Bein ist kein Nullbeitrag, es legt Kapital still**
(14.09., Memory `iq_no_stocks_leg_weight_coupling`). IQ handelt keine
Einzelaktien. Das Aktienbein trug deshalb nicht null bei -- es hielt seinen
Anteil am Risikobudget besetzt, ohne ihn zu nutzen: **IQ fuhr fuenf Beine
mit dem Gewicht von sechs.** Behoben am selben Tag mit `bc72053`. Die
Lehre, die darueber hinausgeht: **eine Symbolliste beweist keine
Handelbarkeit, nur ein echter Tick tut das.**

**"LIVE" im Dashboard sagt nichts ueber Ausfuehrung** (14.09., Memory
`live_ist_nicht_gleich_handelt`). FK stand fuenf Tage scharf und hatte
**null Orders** platziert; bei EK hatten ueberhaupt nur 4 von 11 Beinen je
gehandelt. Die fuenf Gates sind inzwischen der dominante Effekt und
verwerfen systematisch die schnellen Verlierer. Diese Erkenntnis ist der
Grund, warum im Performance-Report die Zeile "FK: keine Daten" steht und
nicht "FK: null" -- das ist nicht dasselbe.

**Ein frisch selektiertes MT5-Symbol liefert ~0,5 Sekunden lang bid=ask=0**
(15.09., Memory `fresh_symbol_select_zero_tick`). Fuer sich genommen
harmlos. Gefaehrlich wurde es durch etwas anderes: ein Anti-Spam-Mechanismus
vom 08.09. schrieb bei so einem Nulltick einen `missed`-Eintrag in den
State -- und machte damit aus einem halbsekuendigen Aussetzer einen
**dauerhaften Signalverlust** (TROW/IVZ/DD auf TTP). Verallgemeinert:
**ein Anti-Spam-State-Eintrag darf nur bei DAUERHAFTER Ursache gesetzt
werden**, sonst friert er einen Zufall ein.

**Ein Simulationsfilter ist kein Live-Gate** (19.09., Memory
`ctnl_sim_filter_is_not_live_gate`). `_cap_concurrent_reversals` kappt nur
die neu simulierte Liste; rueckwirkend verworfene Zeilen lassen echte
Positionen verwaisen -- **38 offen statt 3**, ttp1 gebreacht. Nur EK zaehlt
die echten Broker-Positionen. Der Fehler lag **drei Wochen latent**, weil
das Bein schlicht kein Signal hatte. Genau dieser Befund erklaert die
**32 offenen XAUUSD-Positionen auf TTP**, die im Performance-Report dieser
Woche auftauchen, und damit auch die 24 Risiko-Limit-Ereignisse.

**Die restlichen vier**, kuerzer:

- **Der Windows-Standortdienst ortete den PC in Diyarbakır** (17.09.,
  `lake_zeitstempel_verschiebung`). Die Auto-Zeitzone flippte auf UTC+3,
  tvDatafeed stempelt in Lokalzeit, und die Dedup auf exakten Zeitstempel
  verdoppelte daraufhin die Historie -- **792 CLS-Scans tot**. Auto-Zeitzone
  seit 17.09. aus. Mein Favorit der Woche, weil die Ursachenkette so absurd
  weit vom Symptom entfernt lag.
- **Der ORB-Edge sitzt in der ersten M5-Kerze** (17.09.,
  `orb_first_bar_and_polled_exits`): 58-65 % der Entries fallen dorthin, und
  ein alle fuenf Minuten gepollter Teilausstieg kostet NASDAQ fast den
  ganzen Edge (0,18 -> 0,06 R). Live muss broker-seitig und sekundengenau
  sein.
- **Der Auto-Mode-Klassifizierer zieht die Grenze bei Echtgeld** (16.09.,
  `auto_mode_classifier_live_money_boundary`): Code-Aenderungen und reine
  Datenaufgaben ja, direktes Starten/Planen von `DRY_RUN=False`-Skripten
  nein -- der letzte Live-Ausloeser gehoert an den Nutzer.
- **pypdf klebt Beschriftung und Wert zusammen** (19.09.,
  `pdf_textextraktion_klebt_felder_zusammen`) -- eine Wortgrenzen-Regex gab
  netto als brutto aus. Am echten Belegbestand testen, nicht am Idealfall.

## 4. Neues Wissen diese Woche (Papers/Ideen)

**Keine neue PARA-Notiz, kein neues Paper.** Das ist ehrlich so und kein
Versehen: die Woche ging vollstaendig fuer Betrieb und Fehlersuche drauf.
Geaendert wurden nur bestehende Notizen (`fx-microstructure`,
`cross-asset-momentum-spillover`, `cls-practical-kostenvalidierung`,
`bridge-infrastruktur-vergleich`, `paper-bot-zu-live-bridge`,
`edge-card-workflow`, `strategie-backlog-inventar`), im Wesentlichen als
Nachtrag zu den oben beschriebenen Funden. Neu angelegt wurden ausschliesslich
die drei KW37-Reportdateien.

**Ideen-Inbox**: ein neuer Eintrag in dieser Woche --
**"FK-CLS-Scan liefert einen Trade am Sonntag"** (17.09.,
`_scan_cls_practical`), noch unsortiert.

Erwaehnenswert, weil er diese Woche direkt bestaetigt wurde: der aeltere
Inbox-Eintrag **"TTP/IQ ORB-Exits laufen pro Konto unabhaengig auseinander"**
(02.09.) hat in KW38 sein bislang deutlichstes Beispiel bekommen -- nur
nicht auf ORB, sondern auf Gold: TTP -935,90 USD gegen IQ +1.183,69 USD in
derselben Woche, im selben Bein. Der Eintrag sollte damit von "Beobachtung"
auf "zu untersuchen" hochgestuft werden.

## 5. Verbesserungen

- **CLS-Practical-Scan-Absturz auf der Funded-Bridge behoben** (`b673a68`,
  15.09.): doppelte Datums-Indizes in `compute_daily_rate_score_2y`.
- **IQ-Kapitalgewichtung korrigiert** (`bc72053`, 14.09.): OU-Bein raus,
  fuenf Beine auf 1/3 -- die direkte Umsetzung des Funds von oben.
- **Git-Sync-Rueckstand aufgeloest** (19.09.): 242 Commits, die lokal lagen
  und GitHub/Streamlit Cloud nie gesehen hatte, gingen raus.
- **Weekly-Report-Task erkennt jetzt Teilabbrueche** statt Erfolg zu melden
  (`acc9240`, 15.09.).
- **Windows-Auto-Zeitzone abgeschaltet** (17.09.) -- beseitigt die Ursache
  der Lake-Zeitstempel-Verschiebung.

## 6. Verschlechterungen / offene Probleme

**Zwei Reparaturen dieser Woche haben den jeweils naechsten Ausfall erzeugt
bzw. nicht abgedeckt. Das ist die unangenehmste Beobachtung des Berichts.**

1. **`ee55b0a` (19.09.) -- "Git-Sync: offene Aenderungen stashen statt Push
   blockieren"** loeste das Push-Problem und schuf dabei ein neues: schlaegt
   der spaetere `stash pop` fehl, setzt das Skript hart zurueck und laesst
   die Arbeit im Stash liegen. Aus Sicht einer laufenden Session verschwindet
   sie spurlos. Bis zum 23.09. waren daraus **93 Stashes** geworden; am
   22.-25.09. hat es nachweislich dreimal Arbeit gekostet. Behoben erst am
   23./25.09. (`a57de64`, `bf06bfc`: kein Stash mehr ohne eingehende
   Commits, plus Handoff-Markerdatei).
2. **`acc9240` (15.09.) -- "Teilabbrueche erkennen statt Erfolg melden"**
   deckte genau den Fall nicht ab, der fuenf Tage spaeter eintrat: der Task
   brach nicht teilweise ab, **er lief gar nicht.** Ein Task, der nicht
   startet, kann sich auch nicht ueber einen Teilabbruch beschweren. Deshalb
   haengt der Waechter seit 24.09. im taeglichen Digest und nicht im Task
   selbst.

Weiter offen aus dieser Woche:

- **32 offene XAUUSD-Positionen auf TTP** -- Folge des Sim-Filter-Funds vom
  19.09., zum Zeitpunkt des Abzugs noch nicht bereinigt.
- **FK Instant Funding ohne Ist-Daten** fuer eine volle Echtgeld-Woche
  (`IPC timeout` beim Abzug).
- **EKs Soll/Ist-Zerlegung uebersieht das Gold-Bein** und zeigt damit nur
  32 % des tatsaechlichen Wochenverlusts.

## 7. Optimierungsmoeglichkeiten

**Der gemeinsame Nenner der acht Funde ist eine Klasse, kein Zufall.** In
sieben von acht Faellen war die Ursache dieselbe Form: *eine
Zustandsangabe wurde fuer eine Tatsache gehalten.* Das Dashboard sagte
"LIVE", die Symbolliste sagte "verfuegbar", der Simulationsfilter sagte
"gedeckelt", der Task sagte "erfolgreich" -- und in keinem dieser Faelle
war das durch eine Messung am echten System gedeckt.

Die naheliegende Konsequenz waere, die wichtigsten dieser Zusicherungen
**einmal gegen die Wirklichkeit zu pruefen statt sie zu glauben**: hat ein
als "live" gefuehrtes Bein in den letzten N Tagen tatsaechlich eine Order
platziert? Liefert ein als handelbar gefuehrtes Symbol tatsaechlich einen
Tick? Entspricht die Zahl offener Positionen dem, was der Filter erlaubt?
Drei Pruefungen, die alle gegen Daten laufen, die ohnehin vorliegen.

Konkret und klein genug fuer den naechsten Anlauf:

1. **Bein-Zuordnung in `soll_ist.py` vervollstaendigen** -- solange EKs
   Gold-Bein in `per_leg` fehlt, ist der Soll/Ist-Bericht fuer EK
   systematisch zu freundlich. Das ist die guenstigste der drei, weil die
   Daten schon da sind.
2. **Die TTP/IQ-Divergenz auf Gold untersuchen** -- ueber 2.100 USD
   Unterschied im selben Bein in einer Woche ist zu gross, um es als
   Sizing-Effekt abzutun.
3. **Positionszahl gegen Filtergrenze pruefen**, nicht nur die Simulation
   deckeln -- das ist die eigentliche Lehre aus
   `ctnl_sim_filter_is_not_live_gate`, und sie ist noch nicht umgesetzt.
