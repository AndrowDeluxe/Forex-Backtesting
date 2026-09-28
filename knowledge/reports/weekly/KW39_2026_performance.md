# Weekly Checkup - Performance - KW39/2026

**Abgedeckte Woche: Mo 2026-09-21 bis So 2026-09-27.** Erzeugt Mo
2026-09-28 ab 02:29 durch den geplanten `Forex-Weekly-Report`-Task, der den
Sonntagslauf nachgeholt hat (der Rechner war So 18:00 nicht an). Das ist der
vierte verspaetete Lauf, diesmal hat `StartWhenAvailable` aber gegriffen.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W39.json`
(Fenster 21.09. 00:00 bis 28.09. 00:00 Serverzeit), Soll/Ist
`soll_ist_2026-W39.json`, Bridge-Logs der drei Portfolio-Bridges.

> **Der erste MT5-Abzug war falsch, und zwar still.** Um 02:35 lieferte er
> fuer **beide Funded-Konten 0 Deals** -- TTP und IQ hatten aber die ganze
> Woche gehandelt (Bridge-Log: Entries am 21., 22., 23. und 25.09.). Ursache:
> Der Rechner war erst um 02:29 hochgefahren, und die Terminals waren
> Sekunden vorher gestartet worden (TTP 02:34:17, IQ 02:34:50). Ihre
> Deal-Historie war noch nicht geladen. `history_deals_get()` gibt in diesem
> Fall eine **leere Liste ohne Fehler** zurueck. Ein Nach-Abzug um ca. 02:40
> ergab TTP 79 und IQ 66 Deals; EK und FK waren identisch. Der Nach-Abzug
> ersetzt die erste Datei, und Funded-Soll/Ist ist damit neu gerechnet.
> Memory `soll_ist_misst_nicht_was_es_behauptet` warnt bereits, dass
> "0 Deals" ein fehlgeschlagener Abzug sein kann. **Neu ist die Ursache:**
> ein kalt gestartetes Terminal.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen die ganze Woche mit echtem Geld
(`DRY_RUN = False`): **EK-Portfolio-Bridge** (Tickmill),
**Funded-Portfolio-Bridge** (TTP Konto 2 + IQ Markets 16054) und
**FK Instant Funding** (BeyondIQCapital 17764). Keine Bridge wurde gestartet
oder gestoppt, und bei keiner hat sich der `DRY_RUN`-Stand geaendert.

**Die Woche war voll mit Konfigurationsaenderungen, vor allem am Di/Mi.** Sie
sind fuer Abschnitt 5 wichtig:

- **21.09.: ORB Variante C** auf allen Bridges. Einstieg per Pending-Order
  statt Marktorder.
- **23.09.: OU-Modell auf Logik D + Signalseite** (Funded + EK, `6d46a7f`):
  Stop 8 Sigma, kein TP mehr, Ausstieg am MA20, `BB_K` 2,25.
- **23.09. abends: EK Hebel 1,2x + Einzeltrade-Deckel 3 % -> 5 %** (`4f0f151`).
- **23.09. 22:45 Berlin: EK `ctnl_reversal` auf 1 gleichzeitige Position
  gedeckelt** (E5-c, `2c85390`). Greift nachweislich ab dem 24.09.: Das Log
  zeigt durchgehend `max_concurrent_reached`.
- **23.09.: ttp1 (504069845) endgueltig ausgebaut** (aus der Funded-Config
  schon am 19.09. entfernt). Funded hat damit **2 Konten statt 3**.
- **23.09. 21:40 Berlin: Handaufraeumen durch den Nutzer** auf allen Konten
  (verwaiste OU-Solo-Positionen, ueberfaellige EK-OU-Titel, CTNL-Ueberbestand).
  Details im CHANGELOG vom 23.09.

Ab Fr 25.09. 00:43 gab es keinen Commit von Hand mehr.

## 2. Risk-Management-Compliance

**Keine Regelverletzung, kein Drawdown-Halt.** Ein Kill-Switch war allerdings
die ganze Woche aktiv, und zwar nur auf einer von drei Bridges. Das ist der
wichtigste Befund dieser Woche.

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgeloest (Woche -11,6 %, Monat ca. -19 %) |
| EK-Portfolio | Einzeltrade-Deckel 5 % / Gesamtrisiko 30 % | eingehalten; groesster Einzelverlust gold_asb -87,24 EUR (~2,8 %) |
| EK-Portfolio | `ctnl_reversal` max. 1 gleichzeitig (ab 23.09. abends) | **greift ab 24.09.**; davor bis zu 3 gleichzeitig (alte Grenze) |
| Funded / TTP Konto 2 | Offenes-Risiko-Deckel 3,5 % (Haelfte des 7%-DD-Caps) | **31 Ereignisse am 21.09.** bis zum Handaufraeumen; keine Verletzung |
| Funded / IQ Markets | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag 23.09. -984,95 USD (-0,98 %) |
| FK Instant Funding | 5%-EOD-Trailing-DD | inaktiv (Konto -0,43 % seit Start) |
| **FK Instant Funding** | **CTNL-Standalone-Kill-Switch** | **AUSGELOEST 21.09. 00:04** (Stand-alone-DD -6,70 % < Schwelle -6,60 %), **aufgehoben erst 28.09. 02:37** (-2,88 %) |

**Die Asymmetrie:** Der CTNL-Kill-Switch hielt FK die ganze Woche aus neuen
CTNL-Entries heraus. Die Soll/Ist-Zerlegung beziffert, was FK damit **nicht**
gehandelt hat: **7 Trades, -8,74 R**. Dasselbe Bein lief auf den beiden
anderen Bridges ungebremst weiter:

- **IQ Markets: `ctnl_reversal` 20 geschlossene Trades, 2 Gewinner,
  -2.473,94 USD.**
- **EK: `ctnl_reversal` 12 Trades, 0 Gewinner, -304,65 EUR.**

`ctnl_standalone_drawdown` bzw. `CTNL_KILL_SWITCH` kommen **nur** in
`FKInstantFunding-MT5-Bridge/run_once.py` und im Repo-Paper-Bot vor. In
`Funded-Portfolio-Bridge/*.py` und `EK-Portfolio-Bridge/{*.py,core/*.py}`
gibt es keinen Treffer, und das Funded-Log hat die ganze Woche keinen
einzigen Kill-Switch-Eintrag. Memory `ctnl_reversal_edge_fragility_20260903`
spricht vom Nachruesten "in alle 3 Portfolio-Bots". Gemeint waren damals die
Paper-Bots. **In den beiden Live-Bridges Funded und EK ist er offenbar nie
angekommen.** Nicht geprueft habe ich, ob Funded/EK den Check ueber einen
anderen Pfad aufrufen. Nach Code und Log sieht es nicht so aus.

**Ungeklaert ist auch der Sprung beim Aufheben:** Von -6,70 % auf -2,88 %
innerhalb der Wochenend-Pause ist viel. Der Wert kommt aus einer
Standalone-Simulation mit der aktuellen Konfiguration, kein echter
Kontostand. Ob ein rollendes Fenster oder eine der CTNL-Aenderungen vom
23.09. die Zahl verschoben hat, habe ich nicht nachgerechnet.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): die dritte Verlustwoche in Folge, und die
  groesste bisher.** -367,72 EUR bei 44 geschlossenen Positionen und 27 %
  Trefferquote. Fast alles kommt aus Gold: `ctnl_reversal` -304,65 EUR
  (12 Longs in einen fallenden Goldpreis, 4.358 -> 4.257, alle ausgestoppt,
  bis zu drei gestapelt) und `gold_asb` -87,24 EUR (ein Trade am 25.09.).
  Die Aktien- und Indexbeine waren zusammen etwa neutral. Die E5-c-Deckelung
  kam am Mi-Abend und bremste ab Do sichtbar, der Schaden war da aber
  groesstenteils schon da (22.09. -192,61, 23.09. -78,48).
- **Funded-Portfolio-Bridge (TTP + IQ): -1.696,21 USD, und die Konten liefen
  wieder weit auseinander.** TTP +916,55 USD gegen IQ -2.612,76 USD. Dieser
  Abstand ist aber **kein Exit-Divergenz-Effekt wie in KW38**. Er hat zwei
  klare Gruende:
  1. TTPs Plus kommt zu zwei Dritteln aus **Handschliessungen** (25
     Positionen, +617,08 USD, vor allem der CTNL-Ueberbestand am 21.09.).
     Laut CHANGELOG vom 22.09. hat der Nutzer das bestaetigt; es ist kein
     Bot-Ergebnis.
  2. IQ nahm nach der Freigabe am 23.09. frische `ctnl_reversal`-Entries,
     die alle ausgestoppt wurden.

  Positiv: **`cls_practical` EURUSD am 22.09.** (+694,95 TTP / +1.001,08 IQ)
  und `orb_us30`. Negativ: CTNL, `gold_asb` (-333 / -659) und `orb_nasdaq`
  (0 Gewinner auf beiden Konten).
- **FK Instant Funding: Die Bridge war im Plus, das Konto nicht.** Die
  bot-eigenen Trades brachten **+585,99 USD** (23 Trades, 52 %), getragen von
  `cls_practical` (+408) und `orb_us30` (+270). **Zwei von Hand eroeffnete
  Positionen** (EURUSD long 0,35 Lot seit 16.09., XAUUSD long 0,05 Lot seit
  14.09.) wurden am 24.09. ausgestoppt: **-576,25 USD**. Dem Kill-Switch
  verdankt FK, dass es den CTNL-Einbruch der Woche nicht mitgemacht hat.

## 4. Trades, Winrate, Gewinn - Summary

Gezaehlt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto
inkl. Kommission und Swap. % beziehen sich auf den Kontostand zu
Wochenbeginn (aktueller Balance minus Wochen-P&L).

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 44 | 27,3 % | **-367,72 EUR** | **-11,6 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 90 | 38,9 % | **-1.696,21 USD** | **-0,85 %** |
| FK Instant Funding (LIVE) | 25 | 48,0 % | **+9,74 USD** (Bot +585,99 / Hand -576,25) | **+0,01 %** |
| **Gesamt (alle 3, echtes Geld)** | **159** | **37,1 %** | **-367,72 EUR / -1.686,47 USD** | **ca. -0,70 %** |

- **Keine Summe ueber beide Waehrungen.** Die kapitalgewichtete Gesamtzahl
  ist trotzdem stabil: EK macht mit ca. 3.160 EUR rund 1 % des Gesamtbuchs
  von ca. 302.000 USD aus. Zwischen EUR/USD 1,05 und 1,25 bewegt sich die
  Zahl nur zwischen -0,69 % und -0,71 %.
- **Handeingriffe sind in den Zahlen enthalten, ohne dass sie Bot-Ergebnisse
  waeren:** TTP +617,08 USD aus 25 Handschliessungen, EK +53,43 EUR (10),
  IQ +55,58 USD (1), FK -576,25 USD aus zwei Hand-Eroeffnungen. **Nur Bot**
  laege Funded bei ca. -2.369 USD und FK bei +585,99 USD.
- Hinweis zu TTP Konto 2: `trade_mode = 0` (Demo-Server), siehe CHANGELOG
  vom 22.09. Ob es als Echtgeld zaehlt, haengt an der TTP-Kontoart. Wie in
  den Vorwochen fuehre ich es unter Echtgeld.

## 5. Soll/Ist je Bridge

Soll = Backtest ueber das Fenster 21.09. 00:00 bis 25.09. 21:00 mit Sizing
und Kostenannahme der jeweiligen Bridge. **Soll rechnet mit der Konfiguration
von HEUTE.**

| Bridge | Soll | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 9 Trades / **+3,93 %** | -367,72 EUR (-11,6 %) | 1 (+6,57 R) | 0 | 0 (+ **8 nicht_ermittelbar, +9,54 R**) |
| Funded-Portfolio | 14 Trades / **+1,23 %** | -1.626,95 USD (-0,82 %) + 4 fremde Deals -317,48 | 8 (-0,06 R) | 2 (-2,34 R) | 4 (+8,84 R) |
| FK Instant Funding | 12 Trades / **+2,47 %** | +27,44 USD (+0,03 %) + 2 fremde Deals -576,25 | 1 (+6,43 R) | **7 (-8,74 R)** | 4 (+8,84 R) |

**Pflicht-Vorbehalte:**

1. **Die Konfiguration hat sich im Fenster geaendert.** Der groesste Posten
   ist EKs `ctnl_reversal`: Das Soll kennt nur 3 Trades, weil es mit der
   heutigen Grenze von 1 gleichzeitigen Position rechnet. Live hatte EK bis
   zum Mi-Abend noch die alte Grenze 3 und nahm 12 Trades. **Diese Luecke ist
   der Konfigurationsschnitt und kein Ausfuehrungsfehler.** Dasselbe gilt fuer
   OU (Logik D erst ab 23.09.) und den EK-Hebel 1,2x.
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). Die
   8 Trades unter `nicht_ermittelbar` heissen genau das und nicht
   "nie gesehen". Positiv gegenueber KW38: Das Gold-Bein (`magic 990007`)
   erscheint diesmal in der Bein-Zuordnung.
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips). Funded (2,05) und FK
   (1,30) sind gemessen. EK-Zahlen deshalb nicht gegen die anderen beiden
   stellen.

**Was die Tabelle erklaert:** FKs `nicht_platziert` (7 Trades, -8,74 R) sind
genau die CTNL-Signale der Woche. Das ist der Kill-Switch aus Abschnitt 2 bei
der Arbeit, messbar positiv.

**Was sie vermutlich falsch darstellt (nicht verifiziert):** Die 4 als
"nie gesehen" gefuehrten Trades sind auf Funded **und** FK dieselben vier
`orb_nasdaq`-Signale. Live haben beide Bridges aber an denselben Tagen
NASDAQ gehandelt (Funded 10 Deals, FK 4). Umgekehrt hat `orb_us30` im Soll
"kein Signal", live aber 12 bzw. 6 Deals. Vermutlich erkennt die Soll/Ist-
Zuordnung die **Pending-Order-Entries von ORB Variante C (seit 21.09.)**
nicht mehr, oder das Soll-ORB kennt die aktuelle Instrumenten-Config nicht.
Besonders der Soll-Trade vom 21.09. (NASDAQ, +11,92 R bis Sessionende) steht
gegen einen Live-Verlust auf NASDAQ. **Bis das geklaert ist, sind die
ORB-Zeilen des Soll/Ist nicht belastbar.** Dasselbe gilt fuer `gold_asb`:
Soll meldet "kein Signal", obwohl alle drei Bridges am 25.09. denselben
Gold-Short platziert haben. Moeglich ist der bekannte Effekt aus Memory
`gold_asb_liquidity_filter_reproducibility`, geprueft ist es nicht.

## 6. Auffaelligkeiten / offene Punkte

**(1) Der CTNL-Kill-Switch existiert nur auf FK.** Siehe Abschnitt 2. In
dieser Woche hat das IQ ca. 2.470 USD und EK ca. 305 EUR gekostet, waehrend
FK dasselbe Bein korrekt aussetzte. Das gehoert zu dir: Soll der Kill-Switch
auch auf Funded und EK laufen, oder ist die Asymmetrie gewollt? Zur
Einordnung: Memory `ctnl_edge_nur_long` und `ctnl_ribbon_als_richtung`
beschreiben, dass das Bein in fallenden Goldphasen strukturell verliert. Die
Woche war genau so eine Phase.

**(2) Der Dashboard-Punkt "8 verwaiste OU-Solo-Positionen: immer noch offen"
ist ueberholt.** Er wurde am 25.09. wiederhergestellt, mit dem Hinweis "ob
die Positionen heute noch offen sind, nicht geprueft". Der MT5-Abzug belegt
es jetzt: DAL (EK) sowie AFL, NUE, UAL, TXT und APD (TTP) wurden am 23.09.
um 21:40 Berlin **von Hand** geschlossen (`reason=1`, leerer Kommentar),
genau wie im CHANGELOG vom 23.09. beschrieben. Das Schliess-Skript mit
`--live` wird dafuer nicht mehr gebraucht. Ich habe den Punkt im Dashboard
**nicht entfernt**, nur mit diesem Beleg versehen. Das Abhaken liegt bei
dir.

**(3) Auf dem FK-Bot-Konto wird weiter von Hand gehandelt.** Im September
waren es vier Hand-Eroeffnungen: EURUSD 0,75 / 0,62 / 0,35 Lot und XAUUSD
0,05 Lot. **Alle vier wurden ausgestoppt, zusammen -1.232,82 USD.** Die Bots
selbst stehen auf demselben Konto bei +798,39 USD. Das wurde schon in KW37
als offene Frage gestellt ("Soll auf den Bot-Konten von Hand gehandelt
werden?"). Die Handpositionen verschieben den Trailing-DD des Bots, zaehlen
aber nicht in seinem Risikodeckel. Ohne Wertung: Die Zahl ist inzwischen
groesser als der gesamte Bot-Gewinn des Monats.

**(4) EK: -19 % im September.** Nach -0,2 %, -3,1 % und -6,6 % ist KW39 mit
-11,6 % die vierte Verlustwoche in Folge, jede groesser als die davor. Der
45%-Kill-Switch ist weit weg. Der Verlauf beschleunigt sich aber, und zu
zwei Dritteln stammt er aus dem kleinsten Bein mit Mindestlot-Problem
(Memory `ek_mindestlot_kehrt_hierarchie_um`). Der Hebel wurde am 23.09. auf
1,2x **erhoeht**. Beides zusammen ist eine Frage an dich, kein Befund
gegen die Regeln.

**(5) Soll/Ist fuer ORB ist seit Variante C vermutlich blind.** Siehe
Abschnitt 5.

**(6) Der MT5-Abzug kann auf einem frisch gestarteten Terminal still leer
sein.** Siehe Kasten oben. Ohne den Abgleich mit dem Bridge-Log haette
dieser Report fuer Funded "0 Trades, 0,00 USD" gemeldet. **Vorschlag:**
`mt5_pull.py` sollte bei 0 Deals auf einem Konto mit offenen Positionen oder
mit Bridge-Log-Entries im Fenster warnen oder nach 60 s wiederholen.

**(7) Kleinere Punkte:**
- FK: `CLS-Practical-Scan fehlgeschlagen: '>' not supported between 'str'
  and 'float'`, einmal am 21.09. 00:04.
- Mehrere `LakeStaleDataError`-Fallbacks auf Live-Fetch (GBPUSD, USDJPY,
  GOLD M15/H1/H4).
- EK: ein `Authorization failed` am 23.09. 21:44, zeitgleich mit dem
  Handaufraeumen.
- EK-Fast-Ausfall am 23.09., 33 Min. (CHANGELOG 24.09.).

**(8) Nebenwirkung dieses Laufs:** Der erste Abzug hat das IQ-Terminal
(`MT5 Terminal - GoldFKBot`, PID 7800) gestartet. Ich habe es **bewusst nicht
geschlossen**: Es ist das Live-Terminal der laufenden Funded-Bridge, deren
erste Laeufe nach dem Hochfahren parallel aktiv waren. Ein `Stop-Process`
mitten in einer Echtgeld-Ausfuehrung waere das groessere Risiko als ein
offenes Fenster.
