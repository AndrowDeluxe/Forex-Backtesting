# Weekly Checkup - Performance - KW38/2026

> **Nachgebaut am 2026-09-25 von Hand** (Nutzerauftrag). Der geplante
> `Forex-Weekly-Report`-Lauf fand nie statt: der Rechner lag So 20.09. um
> 10:41 im Standby, der Trigger um 18:00 lief ins Leere, und `WakeToRun` am
> Task ist wirkungslos, weil die Windows-Wake-Timer auf "nur wichtige"
> stehen. Details im CHANGELOG vom 24.09.
>
> **Datenbasis** ist deshalb nicht ein frischer Abzug, sondern die beiden
> Dateien, die der Automatik-Lauf noch geschrieben hatte:
> `scripts/reports/mt5_2026-W38.json` (Abzug So 20.09. 02:23, Fenster
> 14.-21.09.) und `soll_ist_2026-W38.json` (Fenster 14.-18.09. 21:00).
> **Kein Nach-Abzug gemacht** -- ein MT5-Pull heute wuerde eine Woche
> abfragen, die fuenf Tage zurueckliegt, und die Kontostaende haben sich
> seither bewegt. Wo die beiden Quellen sich widersprechen, steht das unten
> ausdruecklich da, statt geglaettet zu werden.

**Abgedeckte Woche: Mo 2026-09-14 bis So 2026-09-20.**

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen mit echtem Geld (`DRY_RUN = False`):
**EK-Portfolio-Bridge** (Tickmill), **Funded-Portfolio-Bridge** (TTP +
IQ Markets) und **FK Instant Funding** (BeyondIQCapital, scharf seit
2026-09-08). Keine Bridge wurde in dieser Woche gestartet, gestoppt oder
auf einen anderen `DRY_RUN`-Stand gesetzt.

**Eine Konfigurationsaenderung mitten in der Woche**, und sie ist fuer den
Soll/Ist-Vergleich unten relevant: Commit `bc72053` nahm **das OU-Bein aus
dem IQ-Konto** und stellte dessen fuenf verbleibende Beine auf Kapitalanteil
1/3. Weitere Aenderungen der Woche: `b673a68` behob einen Absturz des
CLS-Practical-Scans auf der Funded-Bridge (doppelte Datums-Indizes in
`compute_daily_rate_score_2y`), `acc9240` brachte dem Weekly-Report-Task
bei, Teilabbrueche zu erkennen statt Erfolg zu melden -- was die Ironie der
Woche ist, denn der Task lief anschliessend gar nicht.

## 2. Risk-Management-Compliance

**Das ist der auffaelligste Punkt der Woche: 24 Risiko-Limit-Ereignisse auf
der Funded-Bridge**, alle am 17. und 18.09.

| Bridge / Konto | Limit-Ereignisse KW38 | Verteilung |
|---|---|---|
| Funded / IQ Markets | **16** | 17.09.: 13, 18.09.: 11 (beide Konten zusammen) |
| Funded / TTP | **8** | s.o. |
| EK-Portfolio | 0 | -- |
| FK Instant Funding | 0 | -- |

Die Meldung lautete jeweils sinngemaess: *"Offenes-Risiko-Limit erreicht:
$3.232,79 ueber 3,0 % von $99.110,64 Equity ($2.973,32, Haelfte des
6%-Drawdown-Caps) -- neue Entries fuer diesen Lauf gestoppt. Offene
Positionen laufen normal weiter."*

**Bewertung: das ist keine Verletzung, sondern ein funktionierender
Schutz.** Der Deckel liegt bewusst bei der Haelfte des 6%-Drawdown-Caps und
hat genau das getan, wofuer er gebaut ist -- neue Entries gesperrt, Bestand
weiterlaufen lassen. Kein Kill-Switch, kein Drawdown-Halt, kein Breach einer
Challenge-Regel in dieser Woche.

**Aber**: dass der Deckel an zwei aufeinanderfolgenden Tagen 24-mal greift,
heisst, dass das Portfolio ueber Stunden am Anschlag stand. Die Ursache
steht in Abschnitt 6 -- es war der Gold-Korb, nicht eine breite Belastung.

**EK ist der Ausreisser nach unten, ohne dass ein Limit gegriffen haette:**
realisiert **-224,96 EUR auf rund 3.389 EUR Startkapital, also -6,6 % in
einer Woche**. Kein Limit-Ereignis im Log. Bei einem Konto dieser Groesse
ist das innerhalb der Regeln, aber es ist der groesste Wochenverlust, den
diese Bridge bisher gezeigt hat, und er kam fast vollstaendig aus einem Bein.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill, echtes Geld): schlechteste Woche.**
  -224,96 EUR bei 18 geschlossenen Positionen und **16,7 % Trefferquote**.
  Der Verlust ist fast monokausal: das Gold-Bein (`magic 990007`, XAUUSD)
  allein **-153,67 EUR**, das OU-Aktienbein (`magic 990011`) weitere
  -73,41 EUR ueber sieben Titel. Die beiden Index-Beine waren praktisch
  neutral (orb_sp500 -4,04, orb_nasdaq +3,81). Der Verlauf war ein stetiges
  Abrutschen ohne Erholungstag: Mo -1,97, Di -38,63, Mi -31,53,
  **Do -94,75**, Fr -58,08.
- **Funded-Portfolio-Bridge (TTP + IQ): unterm Strich positiv, aber die
  beiden Konten liefen dramatisch auseinander.** Zusammen +501,01 USD.
  Dahinter: **TTP -900,68 USD** (Trefferquote 17,2 %) gegen **IQ +1.401,69
  USD** (Trefferquote 71,4 %) -- bei derselben Strategie. Treiber ist in
  beiden Faellen Gold: TTP verlor auf XAUUSD -935,90, IQ verdiente auf
  XAUUSD.gbe +1.183,69. Das ist keine Nuance, das sind ueber 2.100 USD
  Unterschied im selben Bein in derselben Woche (siehe Abschnitt 6).
  Die Index-Beine waren auf beiden Konten klein und uneinheitlich
  (USTEC +96,12 / NAS100 +218,00; US500 -118,54).
- **FK Instant Funding: keine Aussage moeglich.** Der MT5-Abzug scheiterte
  mit `initialize failed: (-10005, 'IPC timeout')`, `soll_ist` fand kein
  Konto. Die Bridge ist seit 08.09. scharf -- fuer eine Woche mit echtem
  Geld liegt damit **kein Ist-Ergebnis vor**. Das ist eine Luecke, kein
  Nullergebnis.

## 4. Trades, Winrate, Gewinn - Summary

Aggregiert je Bridge, alle Beine und (bei Funded) beide Konten zusammen.
Gezaehlt sind geschlossene Positionen (Ausstiegs-Deals), nicht Orders.

| Bridge | Trades | Winrate | P&L | % auf Startequity |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 18 | 16,7 % | **-224,96 EUR** | **-6,6 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 78 | 51,3 % | **+501,01 USD** | **+0,25 %** |
| &nbsp;&nbsp;davon TTP | 29 | 17,2 % | -900,68 USD | -0,91 % |
| &nbsp;&nbsp;davon IQ Markets | 49 | 71,4 % | +1.401,69 USD | +1,41 % |
| FK Instant Funding (echtes Geld seit 08.09.) | -- | -- | **keine Daten** | -- |
| **Gesamt (Echtgeld, soweit messbar)** | **96** | **44,8 %** | **-224,96 EUR / +501,01 USD** | -- |

**Zur Gesamtzeile**: bewusst **keine** zusammengefasste Zahl ueber beide
Waehrungen -- dafuer braeuchte es einen EUR/USD-Kurs zum Wochenschluss, der
in keinem der beiden Abzuege steht. Ihn zu schaetzen wuerde eine Genauigkeit
vortaeuschen, die die Datenlage nicht hergibt. FK bleibt aussen vor, weil
kein Ergebnis vorliegt (nicht, weil es null waere).

Die aggregierte Trefferquote von 44,8 % verdeckt zwei voellig
unterschiedliche Regime: IQ mit 71,4 % gegen EK und TTP mit unter 18 %.

## 5. Soll/Ist je Bridge

Soll = Backtest ueber dasselbe Fenster mit der Sizing- und Kostenannahme der
jeweiligen Bridge. Fenster hier 14.-18.09. 21:00 (enger als der MT5-Abzug).

| Bridge | Soll (Trades / Summe R) | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 15 / **-1,89 R** | -74,48 EUR (-2,37 %) | 5 (+6,30 R) | 0 | 0 |
| Funded-Portfolio | 15 / **-2,07 R** | +513,07 USD (+0,26 %) | 8 (+1,21 R) | 4 (-3,91 R) | 3 (+0,62 R) |
| FK Instant Funding | 15 / -- | **keine Daten** | 7 (+2,15 R) | 8 (-4,23 R) | 0 |

Bei EK stehen zusaetzlich **10 Trades mit -8,20 R als `nicht_ermittelbar`**.

**Drei Vorbehalte, die nicht untergehen duerfen:**

1. **Soll rechnet mit der HEUTE gueltigen Konfiguration**, nicht mit der, die
   im Fenster live war. In genau dieser Woche lag mit `bc72053` (OU-Bein raus
   aus IQ, Kapitalanteil auf 1/3) eine Konfigurationsaenderung -- ein Teil
   der Soll/Ist-Luecke auf der Funded-Bridge ist damit ein wirksamer
   Konfigurationsschnitt und **kein Ausfuehrungsfehler**.
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). Die
   10 Trades unter `nicht_ermittelbar` heissen genau das -- **nicht**
   "nie gesehen". Sie enthalten unter anderem die ctnl_reversal-Trades vom
   17.09.
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips), Funded (2,05) und FK
   (1,30) sind gemessen. EK-Zahlen deshalb nicht gegen die anderen beiden
   stellen.

**Und ein vierter, der in der Vorlage nicht steht, aber hier zaehlt:** EKs
Ist-Wert in dieser Tabelle (-74,48 EUR) **stimmt nicht mit dem MT5-Abzug
ueberein** (-224,96 EUR). Siehe Abschnitt 6.

## 6. Auffaelligkeiten / offene Punkte

**(1) Dasselbe Gold-Bein, zwei Konten, 2.100 USD Unterschied.** TTP verlor
auf XAUUSD -935,90 USD, IQ verdiente auf XAUUSD.gbe +1.183,69 USD -- in
derselben Woche, mit derselben Strategie. Der Tagesverlauf zeigt, dass es
nicht nur Sizing ist: IQ machte Fr 18.09. **+2.243,17**, TTP am selben Tag
-403,02. Das ist dasselbe Muster, das Memory
`orb_per_account_exit_divergence_20260902` fuer ORB beschreibt (jedes Konto
simuliert seine Exits eigenstaendig), hier aber auf dem Gold-Bein und in
deutlich groesserer Dimension. **Sollte untersucht werden** -- entweder
divergieren die Exits, oder die Konten sahen unterschiedliche Signale.

**(2) 32 offene XAUUSD-Positionen auf TTP** beim Abzug (von 41 offenen
insgesamt), dazu 3 auf EK. Das ist exakt das in Memory
`ctnl_sim_filter_is_not_live_gate` beschriebene Bild: der Simulationsfilter
kappt nur die neu simulierte Liste, nicht den echten Bestand. Die
24 Risiko-Limit-Ereignisse aus Abschnitt 2 sind die direkte Folge --
das Portfolio stand am Anschlag, weil ein Bein den Korb fuellte.

**(3) FK Instant Funding: eine Woche Echtgeld ohne Ist-Daten.** Der Abzug
scheiterte an `IPC timeout`. Die Bridge ist seit 08.09. scharf. Ein
Echtgeld-Konto, fuer das eine ganze Woche kein Ergebnis vorliegt, ist ein
Zustand, der nicht stehenbleiben sollte -- der naechste regulaere Lauf muss
zeigen, ob das ein Einmalfehler war.

**(4) EKs Soll/Ist-Zerlegung uebersieht zwei Drittel des Verlusts.**
`soll_ist` weist als Ist -74,48 EUR aus (orb_sp500, orb_nasdaq, ou_modell),
der MT5-Abzug -224,96 EUR. Die Differenz von 150,48 EUR ist praktisch
vollstaendig das Gold-Bein `magic 990007` (-153,67), das in der
`per_leg`-Zuordnung **gar nicht auftaucht**. Der Soll/Ist-Bericht fuer EK
zeigt damit ein deutlich freundlicheres Bild als die Realitaet -- **68 % des
Wochenverlusts sind darin unsichtbar.** Das ist kein Rundungsfehler,
sondern eine Luecke in der Bein-Zuordnung, die gefixt werden sollte, bevor
EK-Soll/Ist-Zahlen weiter als Entscheidungsgrundlage dienen.

**(5) Der Report selbst fehlte.** Dass dieser Ausfall neun Tage lang
unbemerkt blieb, war die eigentliche Schwachstelle. Seit 24.09. meldet der
taegliche 08:00-Digest einen fehlenden Weekly-Report
(`dashboard_digest.py::_missing_weekly_reports`, Commit `3692f76`).

**Nicht geprueft** (ehrlich, statt es zu behaupten): ob die
Limit-Ereignisse vom 17./18.09. einzelne Signale tatsaechlich verhindert
haben und wie viel R das gekostet hat. Dafuer braeuchte es den Abgleich der
gesperrten Laeufe gegen die Signal-Ledger, und der MT5-Abzug dieser Woche
reicht dafuer nicht.
