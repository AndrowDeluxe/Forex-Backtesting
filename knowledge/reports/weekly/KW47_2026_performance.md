# Weekly Checkup - Performance - KW47/2026

**Abgedeckte Woche: Mo 2026-11-16 bis So 2026-11-22.** Erzeugt am So 22.11. durch den geplanten
`Forex-Weekly-Report`-Task.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W47.json` (16.11. 00:00 bis 23.11. 00:00
Serverzeit), Soll/Ist `scripts/reports/soll_ist_2026-W47.json`, die Logs der drei Portfolio-Bridges
(Funded `task_run*.log`, FK `task_run*.log`, EK `logs/run_*.log`), `knowledge/CHANGELOG.md`, Task Scheduler.

> **Zum Abzug: diesmal auf Anhieb vollständig.** Alle vier Terminals liefen schon vor dem Abzug (EK, TTP,
> IQ, FK). Der Abzug hat also kein Terminal kalt gestartet, und es blieb kein Fenster zurück. Endstand minus
> Wochen-P&L trifft den KW46-Endstand **auf allen vier Konten auf den Cent** (EK 2.520,44 EUR, TTP 99.759,42,
> IQ 97.621,51, FK 99.661,71 USD). Die Falle aus KW46 (Sonntag, kalte Terminals, still 0 Deals) trat nicht auf.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen mit echtem Geld: **EK-Portfolio-Bridge** (Tickmill 55918977),
**Funded-Portfolio-Bridge** (TTP 504072729 + IQ Markets 16054) und **FK Instant Funding**
(BeyondIQCapital 17764). Alle sechs Bridge-Tasks stehen auf `Bereit`, die Einzel-Bots und
`EK-Portfolio-Paper` bleiben `Deaktiviert`. Neu im Scheduler: `Signal-Hub-Scan`/`Signal-Hub-Listener`
(seit 19.11.). Sie platzieren keine Orders und gehören zu keiner Bridge.

**Live-Änderungen in der Woche:**

- **Mo 16.11., alle drei Bridges: ORB-SP500 pausiert**, nur noch Forward-Test (Nutzerentscheid). Die Logs
  zeigen ab Montag in jedem Lauf `SP500=paused, US30=paused`. NASDAQ-ORB läuft weiter.
- **Mi 18.11., alle drei Bridges: NASDAQ-ORB steigt per Market ein statt `breakout_passed`** zu melden. Das gilt,
  wenn bei der Platzierung genau eine Seite schon gebrochen ist, ihr SL unberührt ist und das Range-Ende höchstens
  120 s zurückliegt. **Diese Woche trat der Fall nie ein.** Do und Fr wurden beide Seiten normal platziert. Der
  Market-Zweig ist also live weiter ungetestet.
- **So 15.11. abends (wirkt ab Mo): CTNL-Makro-Sperre** (kein Reversal-Long bei Gold-MACRO ≤ 35). Gold fiel in
  der Woche um 8,9 % (3.883 → 3.538). CTNL hatte weder im Soll noch live einen Trade. Eine Log-Zeile „gesperrt“
  habe ich in den Bridge-Logs nicht gefunden, die Wirkung ist also nicht direkt belegt.
- **Mi 18.11.:** `soll_ist.py` ordnet ORB-Trades jetzt über Bein, Datum und Richtung zu und nennt den Grund aus dem
  Bridge-State (`a2c42324`). Diese Woche läuft der neue Abschnitt 5a zum ersten Mal.

**Störungen:** keine relevanten. Vier Tracebacks auf FK-Fast in der Nacht So/Mo 00:04 und 00:08 (Lake-Daten vom
Freitag „zu alt“, Wochenende). Danach lief FK normal. Kein Kill-/Halt-Eintrag in den Logs.

## 2. Risk-Management-Compliance

**Keine Regelverletzung der Bots. Kein Kill-Switch, kein Drawdown-Halt.** Der größte Bot-Verlust der Woche
war der NASDAQ-Stopp vom 16.11. mit ca. 1,1 R je Konto (TTP −111,69 bei 99,77 Plan-Risiko, IQ −117,53 bei
108,47). Der Rest über 1 R ist Slippage am Stopp.

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgelöst; Balance **2.451,27 EUR (−2,74 % in der Woche)**, Equity 2.351,45 (offene Handtrades −99,82) |
| EK-Portfolio | Einzeltrade-Deckel 5 % / Gesamtrisiko 30 % | Bots eingehalten (NASDAQ-ORB 0,36 % je Seite, beide Tage storniert). **Offen: zwei Hand-Longs Gold + Silber mit zusammen ca. 400 EUR Risiko = ca. 16 % des Kontos** (Abschnitt 6.1) |
| EK-Portfolio | CTNL-Kill-Switch | nie ausgelöst (kein CTNL-Trade) |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag Mo 16.11. −111,69 USD; Balance 99.636,43 = −0,36 % seit Start |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; einziger Trade Mo 16.11. −117,53 USD. Balance **97.503,98 USD = −2,50 % seit Start, ca. 3.504 USD Abstand** zur 6-%-Grenze (KW46: 3.622) |
| Funded (beide) | CTNL-Kill-Switch | nie ausgelöst |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; schlechtester Tag Di 17.11. −490 USD (Handtrades EUR/USD), Balance 98.989,99 USD (−1,01 % seit Start) |
| FK Instant Funding | CTNL-Kill-Switch | nicht ausgelöst |

**Zur Kenntnis:** Wie in KW46 kommt das Wochenergebnis auf EK und FK überwiegend aus **Handtrades** (MT5
`reason` 1 = Mobile, Magic 0). Auf FK sind es 6 Handpositionen, auf EK 4. Die Bot-Limits gelten für diese Trades
nicht. Auf EK liegen die zwei offenen Metall-Longs aber jeweils über dem 5-%-Einzeltrade-Deckel der Bots.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): −69,17 EUR (−2,74 %) bei 4 Trades, davon Bots +1,41 EUR (+0,06 %).**
  Die Bots haben nur die beiden OU-Positionen SYY (+1,57) und OXY (−0,16) per Max-Hold geschlossen. NASDAQ-ORB
  wurde Mo und Di platziert und beide Male storniert, bevor eine Seite füllte. Das hat am Montag den Verlierer
  gespart, den Funded und FK hatten. Das Minus kommt aus zwei Handtrades: EUR/USD Long (−51,47) und Gold Long (−19,11).
- **Funded-Portfolio-Bridge (TTP + IQ): −240,52 USD (−0,12 %) bei 4 Trades.** Fast alles stammt vom NASDAQ-ORB am
  Mo 16.11. Der Long füllte um 15:45:17 MEZ und wurde 21 Sekunden später gestoppt (TTP −111,69, IQ −117,53). An
  Di, Do und Fr strich das Storno beide Seiten („SL vor Einstieg“), Mi war `filtered_out` (Mittwoch). OU auf TTP:
  SYY +1,02, OXY −12,32. **STT ist seit 16.10. weiter offen** (Abschnitt 6.3).
- **FK Instant Funding: −671,72 USD (−0,67 %) bei 4 Trades, davon Bots −134,46 USD (−0,13 %).** Der Bot-Teil ist
  derselbe NASDAQ-ORB-Stopp vom Montag. Der Rest sind Handtrades: zwei EUR/USD-Longs am Di (4 Lot −272, 2 Lot −218),
  ein Gold-Long (−19,75) und Teilschließungen bei MU (−33,81) und SPX500 (+6,30).

**Muster der Woche:** **Die Bots verlieren fast nichts, die Handtrades kosten.** Bot-Seite über alle Konten:
7 Trades, +1,41 EUR und −374,98 USD. Der einzige echte Bot-Verlust ist ein ORB-Stopp nach 21 Sekunden. Das Storno
hat an drei Tagen je einen Verlierer verhindert. Die Handtrades liegen diese Woche **gegen** die Richtung, die die
eigene Makro-Prüfung und Dennis vertraten: EUR/USD long statt short, Gold long in einem Markt, der 8,9 % fiel.
Ergebnis −608 USD auf FK und −71 EUR auf EK.

## 4. Trades, Winrate, Gewinn - Summary

Gezählt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto inkl. Kommission und Swap.
Teilschließungen zählen nicht als eigener Trade, ihr realisierter Betrag ist aber im P&L enthalten (FK: MU, SPX500).
Prozente beziehen sich auf den Kontostand zu Wochenbeginn. Handtrades sind enthalten, die Spalte „davon Bots“
zeigt den Bot-Anteil.

| Bridge | Trades | Winrate | P&L | % | davon Bots |
|---|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 4 | 25,0 % | **−69,17 EUR** | **−2,74 %** | 2 Trades, +1,41 EUR (+0,06 %) |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 4 | 25,0 % | **−240,52 USD** | **−0,12 %** | alle 4 |
| FK Instant Funding (LIVE, echtes Geld) | 4 | 0,0 % | **−671,72 USD** | **−0,67 %** | 1 Trade, −134,46 USD (−0,13 %) |
| **Gesamt (alle 3, echtes Geld)** | **12** | **16,7 %** | **−69,17 EUR / −912,24 USD** | **ca. −0,33 %** | 7 Trades, +1,41 EUR / −374,98 USD (ca. −0,12 %) |

- **Keine Summe über beide Währungen.** Für die Gesamt-Prozentzahl ist EK mit ca. 2.779 USD (Kurs 1,1025 zu
  Wochenbeginn) in ein Buch von ca. 299.820 USD eingerechnet, der EK-Verlust mit 1,0966 (Wochenschluss).
- Je Konto: TTP 3 Trades **−122,99 USD (−0,12 %)**, IQ 1 Trade **−117,53 USD (−0,12 %)**.
- **Noch offen:** EK USD/JPY Short (Hand, Stop inzwischen 159,716 = im Gewinn), **EK Gold Long + Silber Long (Hand,
  seit Do 23:53)**; TTP STT (OU, seit 16.10.); FK USD/JPY Short (Hand, Stop 162,00), MU 3 Stück und SPX500 1,6 Lot (Hand).
  IQ flach.
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server), das IQ-Konto heißt laut Log „BeyondIQCapital
  **Demo** Challenge“. Die Einordnung „echtes Geld“ übernehme ich unverändert aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest über das Fenster 16.11. 00:00 bis 20.11. 21:00 (UTC) mit Sizing und Kostenannahme der
jeweiligen Bridge und der Konfiguration von HEUTE.

| Bridge | Soll | Ist (nur Bot) | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 6 Trades / **−0,09 %** | +1,41 EUR (+0,06 %) | - | - | - (**6 nicht_ermittelbar, −2,12 R**) |
| Funded-Portfolio | 6 Trades / **−0,34 %** | −240,52 USD (−0,12 %) | 0 | 4 (−4,06 R) | 2 (−2,06 R) |
| FK Instant Funding | 6 Trades / **−0,76 %** | −134,46 USD (−0,13 %) | 0 | 4 (−4,06 R) | 2 (−2,06 R) |

(Das Werkzeug zeigt für FK als Ist „−641,67 USD“. Darin steckt ein Teil der Handtrades, wie schon in KW46.
Ich nehme die Bein-Summe des Bots.)

**Hauptaussage: Diesmal liegt Ist ÜBER dem Soll.** Auf Funded und FK verliert das Soll ca. 6 R, live je Konto nur
1 R. Zwei Gründe, beide bekannt: (a) Das Soll zählt SP500 und US30 mit, obwohl beide pausiert sind (−2,06 R).
(b) Das Soll zählt an drei NASDAQ-Tagen einen Stopp, an denen die Bridge die Orders storniert hat, „weil der Kurs
den SL vor dem Einstieg erreichte (wie im Backtest)“ (−3,05 R).

**Pflicht-Vorbehalte:**

1. **Konfiguration:** Soll rechnet mit dem Stand von heute. In der Woche änderten sich zwei Dinge. Die SP500-Pause
   gilt seit Montag, sie gilt also im Soll und live für die ganze Woche. Der NASDAQ-Market-Rückfall kam am Mittwoch,
   er griff live aber nie. Keine der beiden Änderungen erklärt eine Lücke als Ausführungsfehler.
2. **EK lässt sich nur grob zerlegen** (SQLite statt Signal-Ledger). „6 nicht_ermittelbar“ heißt genau das,
   nicht „nie gesehen“. Laut EK-Log wurde NASDAQ Mo und Di platziert und beide Seiten nach einer Minute storniert.
3. **EKs Kostenannahme ist geschätzt** (0,50 Pips), Funded (2,05) und FK (1,30) sind gemessen. EK-Zahlen
   deshalb nicht gegen die anderen beiden stellen. Auffällig ist trotzdem: Das EK-Soll für `orb_nasdaq` steht bei
   −0,06 R für dieselben 4 Tage, an denen Funded/FK −4,06 R stehen. Das ist mehr als ein Kostenunterschied. Nicht
   geklärt, siehe 6.4.
4. **`⚠️ ZUORDNUNG` für `orb_nasdaq` auf Funded und FK (zuerst gelesen):** „4 Soll-Trades, Ist-Deals, aber 0 als
   platziert erkannt“. Nach den Logs ist der Abgleich diesmal **nicht** kaputt. Für jeden der vier Tage liefert das
   Werkzeug einen Grund aus dem Bridge-State. Der einzige gehandelte Tag (16.11.) war live ein **Long**, das Soll
   ein **Short**. Die Zuordnung geht über die Richtung, deshalb gibt es keinen Treffer. Die Warnung ist hier ein
   Fehlalarm der Heuristik, kein neues State-Key-Format. Ich lese die Lücke deshalb auch nicht als
   Ausführungsfehler.

**5a. ORB je Tag** (Funded und FK identisch):

| Tag | Bein | Soll R | Grund laut Bridge-State | Log |
|---|---|---|---|---|
| Mo 16.11. | NASDAQ | −1,01 (Short) | Gegenseite zuerst gefüllt | Short storniert, Long gefüllt 15:45:17, Stop 15:45:38 (−1 R live) |
| Di 17.11. | NASDAQ | −1,02 | `sl_touched_before_fill` | beide Seiten 15:48 storniert, danach `breakout_passed` (Orders schon weg, stimmig) |
| Di 17.11. | SP500 | −1,03 | keine ORB-Order | `SP500=paused` (Pause seit 16.11.) |
| Di 17.11. | US30 | −1,03 | keine ORB-Order | `US30=paused` (seit 04.10.) |
| Mi 18.11. | NASDAQ | - | - | `filtered_out (Wednesday)`, im Soll nicht enthalten |
| Do 19.11. | NASDAQ | −1,02 | `sl_touched_before_fill` | beide Seiten storniert |
| Fr 20.11. | NASDAQ | −1,01 | `sl_touched_before_fill` | beide Seiten storniert |

**Kein Tag mit Soll-R ≥ +2 R wurde verpasst**, alle Soll-Trades der Woche sind Verlierer. `breakout_passed` erscheint
nur in den Läufen nach dem Storno, nie im Platzierungs-Pass. Das ist keine Auffälligkeit im Sinn der neuen Regel.
Fürs Protokoll bleibt der Widerspruch aus KW46: Das Log sagt „wie im Backtest“, das Soll zählt aber einen Stopp.
An drei Tagen dieser Woche ist das zusammen ca. 3 R Soll-Verlust, den es live nicht gab.

**Gold ASB:** kein Trade, weder im Soll noch live. Das Filter-Protokoll meldet **Filter-Drift an 1 von 5 Tagen**
(18.11.). KW46 waren es 2 von 3 Tagen.

## 5b. Edge-Warnstufen je Live-Bein

**Zum ersten Mal seit fünf Wochen frisch.** `research_live_legs.py tickmill --ampel` lief ohne Hänger durch, danach `research_edge_monitor.py --stage status`. Die Liste `live_trades_tickmill_ampel.csv` ist vom 22.11.,
**letzter Trade gesamt 17.11.**

| Bein | Warnstufe | Drawdown R / Schwelle R | Signal |
|---|---|---|---|
| orb_sp500 | **ROT** (pausiert seit 16.11.) | **25,6** / 15,2 | alle fünf rot |
| orb_us30 | **ROT** (pausiert seit 04.10.) | 26,3 / 13,2 | alle fünf rot |
| gold_silver | GELB | 2,7 / 4,9 | roll_mean streng rot; cusum, sprt jetzt gelb |
| btc_ema_cross | GELB | 2,0 / 5,4 | roll_mean, cusum, sprt streng rot |
| gold_asb, ctnl_reversal, cls_practical, orb_nasdaq, ou_modell, trend_pullback | grün | - | - |

- **orb_sp500 (ROT):** Drawdown 23,2 → 25,6 R gegenüber dem letzten frischen Stand (Liste bis 23.10.). Seit 16.11.
  **pausiert** (Nutzerentscheid), nur noch Forward-Test. Kein neuer Dashboard-Eintrag.
- **orb_us30 (ROT):** pausiert seit 04.10., Drawdown 24,5 → 26,3 R (nur Simulation).
- **gold_silver (GELB):** etwas schlechter: Drawdown 1,7 → 2,7 R, zwei weitere Signale gelb. Neu in der Liste sind Trades bis
  11.11., darunter vermutlich der live gestoppte Long vom 09./10.11. (nicht einzeln abgeglichen). Beobachten.
- **btc_ema_cross (GELB):** unverändert (letzter Trade 15.10.).
- **orb_nasdaq:** Drawdown 8,3 → 1,0 R, erholt durch den 05.11.
- **Vorbehalt Gold ASB:** Der letzte Gold-ASB-Trade in der Liste ist der **30.09.**, live gab es danach Trades (z. B.
  13.11.). Das passt zur bekannten Datenfalle „ASB-Dateien enden 01.10.“ (siehe Memory: `gesamtportfolio_backtest_2016`).
  Die grüne Ampel für Gold ASB sieht Oktober und November also nicht. Die Schwelle sprang außerdem von 4,4 auf 9,4 R.
  Das ist nicht geklärt.
- Eine Warnung ist ein Grund hinzusehen, kein Grund, einen Bot zu ändern.

## 6. Auffälligkeiten / offene Punkte

**(1) EK: zwei offene Hand-Longs Gold + Silber mit zusammen ca. 16 % Kontorisiko.**
Eröffnet Do 19.11. 23:53 Serverzeit per Handy, jeweils 0,01 Lot:

| Position | Einstieg | Stop | Risiko bis Stop | Stand Fr-Schluss |
|---|---|---|---|---|
| XAU/USD Long | 3.626,41 | 3.404,79 | ca. 222 USD ≈ 202 EUR (8,2 %) | −81,69 EUR |
| XAG/USD Long | 42,935 | 38,50 | ca. 222 USD ≈ 202 EUR (8,2 %) | −79,87 EUR |

- Beide Trades haben denselben Treiber (Edelmetalle). Nach der eigenen Leitlinie zählen sie deshalb als **ein Risiko von
  ca. 16 %** auf einem Konto mit 2.451 EUR. Das Bot-Maximum je Bein liegt bei ca. 3 %. Die Kontrakt-Annahme lautet
  1 Lot XAU = 100 oz und 1 Lot XAG = 5.000 oz. Sie passt zum offenen P&L bei den Lake-Kursen, ist aber nicht beim
  Broker nachgeschlagen.
- Gold schloss am Freitag bei ca. 3.538, also ca. 133 USD über dem Stop. EK hat in drei Wochen ca. 13 % verloren
  (2.811 → 2.451 EUR, Equity 2.351).
- **Kein Bot-Regelverstoß**, aber ein Vielfaches des Risikos, das die Bots auf diesem Konto fahren dürfen. Der
  offene Dashboard-Punkt „Handtrades auf EK/FK“ (KW46) ist um diese Zahl ergänzt. **Weil hier echtes Geld in
  dieser Größe offen über das Wochenende liegt, steht es auch im Telegram-Text.**

**(2) Handtrades gegen die eigene Makro-Sicht.** Die Agent-Prüfung (Report 18.11.) und Dennis waren EUR/USD short
und Gold „gesperrt, auch long“. Live liefen EUR/USD Long auf EK (0,5 Lot) und FK (4 + 2 Lot) sowie Gold Long auf
beiden Konten. Alle fünf wurden gestoppt, zusammen −71 EUR und −510 USD. Das ist kein Urteil über die Trades, aber
Soll/Ist, Ampel und Makro-Bilanz sehen sie nicht. Die Spalte „Nutzer real“ in der Makro-Notiz ist nachgeführt
(Education 4c).

**(3) TTP-OU: STT ist weiter offen (seit 16.10., 37 Tage).** Am 10.11. hast du „bei US-Börsenöffnung schließen“
entschieden. SYY und OXY wurden diese Woche normal geschlossen, STT nicht. Zweite Woche in Folge ohne Ausführung.

**(4) Soll/Ist-Werkzeug, drei bekannte und ein neuer Punkt.**
- `orb_us30` **und jetzt auch `orb_sp500`** zählen im Soll, obwohl pausiert (−2,06 R in dieser Woche).
- Storno-Tage zählen im Soll als Stopp (ca. 3 R), obwohl die Bridge „wie im Backtest“ storniert.
- FK-Kopfzeile enthält Handtrades.
- Neu: Die Zuordnungswarnung schlägt an, wenn live die Gegenseite füllt (16.11.). Vorschlag (nicht umgesetzt):
  Tage mit gefüllter Gegenseite nicht als „0 erkannt“ zählen. Dazu kommt das EK-`orb_nasdaq`-Soll von −0,06 R
  gegen −4,06 R auf Funded/FK.

**(5) Gold-Zinskurven-Filter steht die dritte Woche gegen den Markt.** Bestätigt „Goldilocks“ (nur long) bis 19.11.,
roh pendelte er zwischen Inflation und Twist. Gold fiel in KW47 um 8,9 %. Der Filter ist kein Live-Gate. Er betrifft
die Makro-Prüfung und den Signal-Hub (Makro-Ampel), nicht die Bridges.

**(6) Kleineres.**
- Der NASDAQ-Market-Rückfall (seit 18.11.) ist live weiter ungetestet. Den ersten echten Fall im Log prüfen.
- FK warnt weiter in jedem Lauf „Kontostand weicht von STARTING_EQUITY=100.000 ab“ (bekannt).
- Dieser Report committet `knowledge/reports/`, die Makro-Notiz (Pflicht aus 4c), CHANGELOG und Dashboard.
