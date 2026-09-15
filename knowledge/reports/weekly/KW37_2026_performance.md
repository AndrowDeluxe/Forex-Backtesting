# Weekly Checkup - Performance - KW37/2026

**Zeitraum:** Montag 2026-09-07 bis Sonntag 2026-09-13 (Handelstage Mo-Fr,
2026-09-07 bis 2026-09-11 - seit der Wochenend-Pause vom 2026-09-13 ist
Sa/So planmäßig still, siehe Punkt 1).

> **Datenquellen dieses Laufs:** Broker-Historie read-only per
> `mt5.history_deals_get()`/`positions_get()` für EK-Portfolio-Bridge
> (Tickmill 55918977) und alle 3 Funded-Portfolio-Bridge-Konten
> (504072729 / 16054 / 504069845), ergänzt um die bridge-eigenen
> Equity-Baselines (`daily_baseline`, `risk.eod_equity`) und
> State-DBs/Logs.
>
> **Nachtrag 2026-09-14: FK Instant Funding (17764) ist jetzt ebenfalls am
> Broker gegengeprüft.** Der Lauf vom 2026-09-13 kam dort nach vier
> `mt5.initialize() (-10005, 'IPC timeout')` nicht durch und wurde nach 60
> Minuten selbst vom Task Scheduler abgeschossen (`ExecutionTimeLimit=PT1H`,
> seither auf 4h angehoben — siehe CHANGELOG 2026-09-14). Der Nachhol-Lauf
> von heute hat die Verbindung im ersten Versuch bekommen (FKs Terminal lief
> als fremder Prozess seit 2026-09-14 00:03, es musste also keine GUI
> gestartet und keine geschlossen werden). **Damit ist keine Zeile dieses
> Reports mehr unverifiziert** — und der offene Punkt 5.1 ist aufgelöst, mit
> einem anderen Ergebnis als vermutet. EK und Funded wurden nicht erneut
> gezogen (Wochenend-Pause, kein Handel seit Freitagsschluss möglich); ihre
> Zahlen stehen unverändert auf dem Broker-Pull vom 2026-09-13.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen die ganze Woche. Zwei strukturelle
Änderungen fallen in diese Woche:

- **FK Instant Funding ist seit 2026-09-08 kein Paper-Bot mehr.**
  `DRY_RUN=False` auf expliziten Nutzerauftrag ("Setze dry run False, damit
  ist orb jetzt live"), zunächst nur mit den 3 NY-Open-ORB-Beinen in
  `LIVE_LEGS`; am 2026-09-09 auf 7 der 9 Beine erweitert (zusätzlich
  gold_asb, cls_practical, ctnl_continuation, ctnl_reversal;
  trend_pullback/gold_silver bleiben bewusst geplant/geloggt). Damit ist die
  Zeile "FK Instant Funding = Paper" aus allen vorherigen Weekly Checkups
  **überholt** - es sind jetzt drei Echtgeld-Bridges, nicht zwei. Der
  repo-interne `FK-Instant-Funding-Paper`-Task wurde am 09-09 auf die zwei
  verbliebenen Nicht-Live-Beine reduziert, um Doppelmeldungen zu vermeiden.
- **Wochenend-Pause eingerichtet (2026-09-13, Commit `56d36f7`).** Sieben
  handelsbezogene Tasks liefen bis dahin mit 7-Tage-Trigger (u.a.
  `EK-Portfolio-Bridge-Fast` alle 2 Minuten rund um die Uhr, allein ~1.440
  Leerläufe pro Wochenende); drei weitere liefen wegen `P1D`-Wiederholung
  noch Minuten in den Samstag hinein. Alles auf Mo-Fr gekappt, deklarativ
  hinterlegt in `scripts/weekend_pause.ps1`. Bewusst in Kauf genommen: die
  erste Handelsstunde So 23:00-24:00 entfällt. **Ein leerer Sa/So-Log ist
  ab jetzt kein Ausfall.**

Weitere Änderungen mit direkter Wirkung auf echtes Geld, alle in dieser
Woche gelandet:

- **EK-Portfolio-Bridge (Tickmill, echtes Geld)**: am **09-10** wurde
  `CAPITAL_WEIGHT = 1/8` erstmals tatsächlich angewendet - bis dahin
  handelte jedes Bein ~8x größer als validiert (siehe Memory:
  `ek_capital_weight_never_applied`, Verifikationsmethode in Memory:
  `backtest_zahlen_gegen_szenario_pruefen`). Im selben Zug: Mindestlot-
  Sizing, Portfolio-Kill-Switch (`TRAILING_DD_PCT = 0.45`),
  `MAX_TOTAL_RISK_PCT` 8 % → 30 %, `MAX_SINGLE_TRADE_RISK_PCT = 3 %`.
  Ebenfalls 09-10: der **Bar-Fenster-Bug** in allen 3 MT5-nativen Beinen
  behoben (`core/mt5_bars.py`, Commit `90ee97a`) - ORB rechnete zuvor auf
  **5 Stunden alten Bars**. Am 09-11 kamen Pip-Boden, R-Detektor
  (cls_practical) und ein 80-%-Margin-Deckel dazu.
- **Funded-Portfolio-Bridge (TTP + IQ Markets, 3 Konten, echtes Geld)**: am
  **09-11** `min_sl_pips=5` im CLS-Scan, `LEG_RISK_PCT["cls_practical"]`
  0,015 → 0,010, R-Detektor `MAX_CONSUMED_R_FOR_ENTRY = 0.50` und harter
  Margin-Deckel `MAX_MARGIN_PCT_OF_EQUITY = 0.20`. Am **09-13** (nach
  Wochenschluss) Rates-Multiplikator ins Live-Sizing durchgereicht und ein
  aggregierter Offenes-Risiko-Kill-Switch nachgerüstet (TTP 3,5 %, IQ 3,0 %).
- **Alle drei Bridges** bekamen am **09-09** ein Restlaufzeit-Gate gegen
  bereits tote Signale plus verschobene Task-Offsets (Ingest läuft jetzt
  vor dem Scan, nicht danach) - Herleitung siehe Memory:
  `bridge_signal_latency_vs_trade_lifetime`.

Kontostand: EK 3.354,39 € (Fr-Schluss), Funded 293.954,90 $ über 3 Konten,
FK 100.134,25 $ Equity bei **99.996,25 $ Kontostand** (am Broker bestätigt
2026-09-14; die Differenz ist die schwebende Handposition aus Punkt 5.1, der
Bot selbst hat den Kontostand die ganze Woche nicht bewegt). Das zweite
IQ-Konto (15514) ist seit 2026-09-07 raus (Nutzerauftrag), Funded fährt
weiterhin 3 Konten.

## 2. Risk-Management-Compliance

**Kein Kill-Switch und kein Drawdown-Halt hat diese Woche ausgelöst. Keine
Regelverletzung gegen die jeweils zum Handelszeitpunkt geltende Konfiguration.**
Im Detail:

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio-Bridge | Trailing-DD-Kill-Switch (45 %, neu seit 09-10) | Nicht ausgelöst. Wochenverlust −3,07 %, Abstand zur Schwelle sehr groß. |
| EK-Portfolio-Bridge | Aggregierter Risikodeckel (bis 09-10: 8 %, danach 30 %) | **Griff mehrfach korrekt** - `orb_stale_NASDAQ` am 09-08 übersprungen, am 09-09 `ou_modell_AIG` und `ou_modell_EXPE` per `risk_cap` abgelehnt, und der cls_practical-EURUSD-Entry vom 09-09 10:30 wurde mit `status='risk_cap'` gar nicht erst gesendet (`bracket_executions`-Tabelle). Siehe Punkt 3 - genau dieser Skip war diese Woche bares Geld wert. |
| EK-Portfolio-Bridge | Einzeltrade-Cap 3 %, Margin-Deckel 80 % (beide neu 09-10/09-11) | Eingehalten. Größte offene Einzelposition (AMGN) ~1,2 % Risiko; Margin zum Wochenschluss 1.059,86 € von 3.351,63 € Equity = **31,6 %**. |
| Funded / TTP Konto 2 (`ttp`) | TTP: 3 % Tagesverlust, 7 % Gesamt-DD, `risk.kill_switch_active` | `False`. Schlechtester Tag 09-09: −1,03 %. Abstand zum Höchststand (100.151,39 $) zum Wochenschluss: **−1,27 %**. |
| Funded / TTP Konto 1 (`ttp1`) | TTP: dieselben Grenzen | `False`. Schlechtester Tag 09-09: −0,86 %. Abstand zum Höchststand: **−1,04 %**. |
| Funded / IQ Markets (`iqmarkets`) | IQ: 1 %/Position, 6 % Gesamt-DD | `False`. Schlechtester Tag 09-09/09-10: −0,77 %. Abstand zum Höchststand: **−0,81 %**. |
| Funded (alle 3) | Aggregierter Offenes-Risiko-Kill-Switch (TTP 3,5 % / IQ 3,0 %) | **Existiert erst seit 2026-09-13, nach Wochenschluss gebaut** - war diese Handelswoche noch nicht scharf und ist bisher nur offline getestet (7 Testfälle), nicht live erprobt. |
| FK Instant Funding | Trailing-DD-Gate + `ctnl_kill_switch_active` + aggregierter Deckel (5 % / CTNL 1 %) | `ctnl_kill_switch_active: false`, kein Trigger - **aber ohne Aussagekraft**: die Bridge hat diese Woche keine einzige Order platzieren können (Punkt 3), das Risikogerüst wurde also nie belastet. **Nachtrag 09-14:** das Trailing-DD-Gate lief diese Woche trotzdem nicht auf der Bot-Equity, sondern auf einer Equity inklusive einer fremden Handposition - siehe Punkt 5.11. Ohne Folge (Abstand zum Floor sehr groß), aber die Grundlage stimmt nicht. |

**Zwei Einordnungen, die nicht in der Tabelle verschwinden sollen:**

1. **Die 20,8-Lot-EURUSD-Position auf `ttp` (09-09 11:30 UTC) war
   regelkonform, aber nur knapp.** Bei 1,16 EUR/USD und Hebel 1:100 band sie
   rund **24 % der Konto-Equity an Margin** - über dem
   `MAX_MARGIN_PCT_OF_EQUITY = 0.20`, der genau wegen dieses Trades zwei Tage
   später (09-11) eingebaut wurde. Das Einzeltrade-Risiko (0,58 % realisiert)
   lag dagegen sauber unter der 1-%-Regel. Die Position wäre unter der
   *heutigen* Konfiguration nicht zustande gekommen; unter der damaligen war
   sie zulässig. Kein Verstoß, aber der Anlass für die Regel.
2. **EK hat diese Woche kein Risiko wegen einer Regel verloren, sondern wegen
   einer noch nicht behobenen Verzerrung Geld gespart.** Der 8-%-Deckel, der
   bis 09-10 unfreiwillig die Arbeit der fehlenden Kapitalverdünnung
   erledigte, klebte permanent am Anschlag - deshalb wurde der
   cls_practical-EURUSD-Entry am 09-09 auf EK übersprungen. Alle drei
   Challenge-Konten nahmen ihn und verloren zusammen **−1.363 $**. Das ist
   Glück aus einem Bug, kein funktionierender Portfolio-Mechanismus (siehe
   Memory: `ek_capital_weight_never_applied`).

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge** — Woche klar negativ (−106,23 € / −3,07 %), aber
  der Verlust kommt fast ausschließlich aus dem **OU-Modell-Aktienbein**:
  fünf Stop-outs (EXPE, GE, FAST, LEN, D) summieren sich auf **−72,49 €**,
  also 80 % des realisierten Wochenverlusts, davon vier aus Alt-Positionen,
  die noch vor dieser Woche eröffnet wurden. Der einzige Netto-Gewinner der
  gesamten Woche war ein CTNL-Continuation-Gold-Trade am 09-09
  (**+6,92 €**) - genau die Position, die laut Memory:
  `mt5_comment_length_order_reject` vier Stunden lang nicht geschlossen
  werden konnte, bis der Kommentar-Truncation-Fix in
  `core/order_send.py` griff; sie ist der Live-Beleg, dass der Fix wirkt.
  **Auffällig auf der ORB-Seite:** EK platzierte fünf echte ORB-Entries
  (09-07 NASDAQ, 09-10 SP500+NASDAQ, 09-11 NASDAQ+SP500) - **alle fünf
  Verlierer**, zusammen aber nur **−7,63 €**, weil ORB nach der
  09-10-Kalibrierung effektiv nur noch 0,042 % der Equity je Trade riskiert
  (~1,40 € - siehe Punkt 5.4). Drei der vier Nach-Fix-ORB-Trades wurden
  **innerhalb von 11 bis 75 Sekunden** ausgestoppt.
- **Funded-Portfolio-Bridge** — schlechteste Woche seit Live-Gang:
  **−2.999,11 $ / −1,01 %**, 9 geschlossene Trades, **kein einziger
  Gewinner**. Der Verlust ist fast vollständig ein **Ein-Tages-Ereignis**:
  am 09-09 liefen dreimal `cls_practical` (EURUSD, auf allen 3 Konten,
  Stop **16 Sekunden nach Entry**, zusammen −1.363 $) und dreimal
  `ctnl_continuation` (XAUUSD, Stop ~3,5 Minuten nach Entry, zusammen
  −779 $) ins Messer. Dazu drei Stop-outs alter OU-Aktienpositionen
  (EXPE, CCL, GE, zusammen −636 $). Die 16-Sekunden-Stops sind exakt das
  Muster aus Memory: `cls_entry_lag_dominates_costs` und
  `bridge_signal_latency_vs_trade_lifetime` - und genau der Anlass, aus dem
  am 09-11 Pip-Boden, R-Detektor und Margin-Deckel eingebaut wurden. **Die
  Gegenprobe fällt positiv aus:** seit dem Umbau am 09-11 hat kein neues
  cls_practical-Signal mehr die Filter passiert. Das ORB-Bein platzierte auf
  Funded **0 von 6 Signalen** (× 3 Konten = 18 Slots, alle "missed") - was
  diese Woche zufällig ein Vorteil war, weil dieselben Signale auf EK
  fünfmal verloren.
- **FK Instant Funding (jetzt LIVE)** — **operativ die schwächste Bridge der
  Woche: 9 Signale, 0 platzierte Orders.** Acht Signale liefen als "missed"
  durch (der Trade war beim ersten Scan schon eröffnet UND geschlossen), ein
  ctnl_continuation-Signal wurde nur geplant. Der **erste echte Order-Versuch
  über den neuen MT5-Datenpfad** am 09-11 16:03:08 (SPX500.gbe, 25,3 Lots,
  SL 7667,066270640961) wurde vom Broker mit `retcode=10016 "Invalid stops"`
  abgelehnt - der Datenpfad trägt also, die Order-Ebene nicht. Zwei weitere
  Entries am 09-09 starben still an `order_send() = None`. Ergebnis: eine
  Bridge, die seit 09-08 echtes Geld handeln darf und in fünf Handelstagen
  keinen einzigen Trade zustande gebracht hat. **Am Broker gegengeprüft
  (2026-09-14):** der Kontostand stand die ganze Woche unverändert bei
  100.000,00 $; die einzige Bewegung auf dem Konto war eine **von Hand**
  eröffnete EUR/USD-Position (Punkt 5.1). Das Konto sah damit fünf Tage lang
  nach "+0,13 %" aus, obwohl der Bot exakt nichts getan hat — genau der
  Trugschluss aus Memory: `live_ist_nicht_gleich_handelt`.

## 4. Trades, Winrate, Gewinn ($/%) - Summary

Nur **geschlossene** Trades zählen in Trades/Winrate; Winrate nach
**Netto**-Ergebnis (inkl. Kommission und Swap). Die $/%-Spalte ist die volle
Equity-Veränderung Montag-Start bis Freitag-Schluss (inkl. Floating-P&L auf
noch offenen Positionen) - Realisiertes und Equity können deshalb
auseinanderlaufen.

| Bridge | Konto(n) | Währung | Trades | Winrate | PnL | PnL (%) |
|---|---|---|---|---|---|---|
| **EK-Portfolio-Bridge** | Tickmill 55918977 | EUR | 12 | 8,3 % (1/12) | −106,23 € | −3,07 % |
| **Funded-Portfolio-Bridge** | TTP + IQ Markets, 3 Konten | USD | 9 | 0,0 % (0/9) | −2.999,11 $ | −1,01 % |
| **FK Instant Funding** (LIVE seit 09-08) | BeyondIQCapital 17764 | USD | **0** | — | **0,00 $ durch die Bridge** (Konto: +134,25 $, fremde Position) | **0,00 %** Bot / +0,13 % Konto |
| **Grand Total** (alle 3, echtes Geld) | — | EUR/USD gemischt | **21** | **4,8 % (1/21)** | s. Hinweise | **−0,78 %** (Bot-zurechenbar) / −0,75 % (Kontoebene) |

Hinweise zur Tabelle:

- **EK (€) und Funded/FK ($) werden nicht zu einer einzigen Summe addiert**
  (unterschiedliche Kontowährungen, keine belastbare EUR/USD-Umrechnung in
  diesem Lauf). Die kapitalgewichtete Gesamtprozentzahl ist trotzdem robust:
  EKs Konto (~3.460 €) macht bei einem Gesamtbuch von ~401.000 $ nur rund
  1 % aus, und über die gesamte plausible Kursspanne (1,05 bis 1,25) bewegt
  sich der Gesamtwert nur zwischen −0,777 % und −0,780 %. (Ohne FK, also nur
  EK+Funded wie im ursprünglichen Lauf gerechnet: −1,04 %.)
- **Die beiden Gesamtzahlen unterscheiden sich nur durch FK** und sind beide
  verifiziert - der Unterschied ist keine Unsicherheit mehr, sondern eine
  Zurechnungsfrage: **−0,78 %** ist das, was die drei Bots gemacht haben
  (FK trägt exakt 0,00 % bei, weil es keinen einzigen Trade platziert hat);
  **−0,75 %** ist die Kontoebene inklusive einer **manuell eröffneten
  EUR/USD-Position auf dem FK-Konto, die die Bridge nicht platziert hat**
  (Punkt 5.1). Für die Bewertung des Systems ist die erste Zahl die
  richtige.
- **Aufteilung Funded:** `ttp` −1.224,71 $ (−1,22 %, 4 Trades), `ttp1`
  −1.006,32 $ (−1,04 %, 3 Trades), `iqmarkets` −768,08 $ (−0,77 %, 2 Trades).
  Bei `iqmarkets` stimmt die Equity-Veränderung auf den Cent mit der Summe
  der realisierten Trades überein (keine offenen Positionen) - das ist der
  Gegencheck, der die Methodik für die anderen beiden Konten stützt.
- **EK zusätzlich:** zwei Nicht-Trade-Kontobewegungen am 09-09 (+4,05 €) und
  09-11 (+0,63 €) mit kryptischen Kommentar-Codes (`KOKXXP5QV1HYTFYY`,
  `KEJ2766VB3CWBIGP`) - vermutlich Swap-/Rebate-Gutschriften, in der
  Trades-Zeile nicht mitgezählt, in der Equity-Zahl enthalten. Dasselbe
  Muster wie in KW36; weiterhin nicht zugeordnet.
- **EKs einziger Netto-Gewinner** ist der CTNL-Gold-Trade (+6,92 €). Ein
  zweiter Trade (D, Alt-Position) schloss brutto mit +0,14 €, rutschte durch
  −1,59 € Swap aber ins Minus - nach Brutto-Betrachtung wäre die EK-Winrate
  16,7 % (2/12).
- **FK Instant Funding steht mit 0 Trades im Grand Total**, weil es seit
  09-08 kein Paper-Bot mehr ist. Die 0 ist hier kein "hat nichts gefunden",
  sondern "konnte nichts ausführen" (Punkt 3). Der Broker bestätigt das
  jetzt hart: **auf dem Konto gab es in der gesamten Woche genau einen
  einzigen Deal - und der kam nicht von der Bridge** (Punkt 5.1). Der
  Kontostand stand von Montag bis Freitag unverändert auf 100.000,00 $ und
  ging nur durch die 3,75 $ Kommission dieses einen fremden Trades auf
  99.996,25 $.

## 5. Auffälligkeiten / offene Punkte

**5.1 — AUFGELÖST (2026-09-14): Die Equity-Bewegung auf dem FK-Konto stammt
aus einer manuell eröffneten Position, die die Bridge nicht platziert hat -
und sie ist immer noch offen.**
Der ursprüngliche Befund lautete: die Bridge hat nachweislich kein einziges
echtes Ticket eröffnet, trotzdem bewegte sich die Konto-Equity am 09-11 von
100.000,00 $ auf bis zu 100.264,75 $ und schloss bei 100.134,25 $. Vier
`mt5.initialize()`-Versuche gegen Login 17764 waren am 09-13 an
`(-10005, 'IPC timeout')` gescheitert, der Punkt blieb offen. **Der
Nachhol-Lauf von heute hat die Verbindung bekommen. Die Broker-Historie ist
eindeutig:**

| | |
|---|---|
| Deals 2026-09-06 bis 09-14 | **genau 1** |
| Position | EURUSD.gbe, **LONG 0,75 Lots**, Ticket 1491080 |
| Eröffnet | 2026-09-11 **14:31:46 Berlin** (15:31:46 Serverzeit Helsinki) |
| Entry / SL / TP | 1,15758 / 1,15437 / 1,17179 |
| Order-Kommentar | **leer** |
| Status heute | **immer noch offen**, aktuell **−145,50 $** |

**Drei Dinge belegen unabhängig voneinander, dass das kein Bridge-Trade ist:**
(a) Der Kommentar ist leer - die Bridge schreibt ausnahmslos `FKIF <bein>`
hinein (genau diese Kommentare sind der Gegenstand der Punkte 5.2/5.5).
(b) Fünf Minuten vorher, um 14:26:32, lag auf demselben Symbol eine
**stornierte** Order über dieselben 0,75 Lots zu einem anderen Preis
(1,15665, SL 1,148) - stornieren und mit anderem Preis/SL neu setzen ist ein
Handgriff aus der Terminal-GUI, kein Verhalten dieses Codes.
(c) Das SL/TP-Verhältnis (32 Pips Risiko, 142 Pips Ziel, ~4,4 R) entspricht
keinem der neun Bein-Profile.
**Die frühere Vermutung "Zeitwidersprüche zwischen Log und Order" war ein
Zeitzonen-Artefakt:** MT5 liefert Deal-Zeiten in **Server**zeit
(BeyondIQCapital = Europe/Helsinki, UTC+3), die Bridge loggt in Berliner
Zeit. Nach Umrechnung passt alles lückenlos zusammen - der Kontostand steht
schon im 15:14-Log um exakt die 3,75 $ Kommission dieses Trades niedriger.
**Konsequenz für Punkt 4:** FKs "+0,13 % in KW37" war nie ein Ergebnis des
Bots, sondern unrealisierter Buchgewinn eines Handtrades. Er hat sich
inzwischen gedreht: Montag 09-14 09:14 steht das Konto bei 99.843,66 $
(−0,16 %). Dasselbe Muster wie der nicht zuordenbare EURUSD-Trade aus KW34
(siehe Memory: `weekly_checkup_kw34_2026_findings`) - dort blieb es
ungeklärt, hier ist es geklärt. **Kein Bug, keine Fehlfunktion** - aber der
Report muss Hand- und Bot-Trades auf demselben Konto trennen können, sonst
misst er die falsche Sache (siehe dazu neu Punkt 5.11).

**5.2 — FK kann seit dem Live-Gang keine Orders platzieren; drei Versuche,
drei verschiedene Fehlerbilder, null Fills.**
Der Reihe nach: 09-09 10:30 `cls_practical` und 09-09 17:20
`ctnl_continuation` starben an `order_send() = None` (Verdacht laut
CHANGELOG: `run_once.py:484` kappt den Kommentar auf 31 Zeichen, das echte
Broker-Limit liegt bei 16 - `FKIF cls_practical` = 18 Zeichen,
`FKIF ctnl_continuation` = 22, während `FKIF orb_sp500` = 14 durchkam; genau
die Klasse aus Memory: `mt5_comment_length_order_reject`, die auf EK bereits
zentral in `core/order_send.py` behoben ist und auf FK offenbar nicht).
09-11 16:03 `orb_sp500` erreichte den Broker und wurde mit
`retcode=10016 "Invalid stops"` abgewiesen - SL mit 12 Nachkommastellen und
4,93 Punkte Stopabstand (0,064 %) sind die beiden ungeprüften Kandidaten.
**Praktische Folge: eine Echtgeld-Bridge, deren gesamter Live-Rollout
(7 von 9 Beinen seit 09-09) bisher nur auf dem Papier existiert.** Steht im
DASHBOARD, hier wiederholt, weil es die einzige Bridge-Ebene ist, auf der
diese Woche gar nichts funktioniert hat.

**5.3 — Der CHANGELOG-Eintrag von heute sagt "EK: kein einziger Entry" -
das stimmt nicht.**
Der parallel entstandene Wochenauswertungs-Eintrag vom 2026-09-13 hält fest,
EK habe diese Woche keinen Entry gehabt. Die Broker-Historie und EKs eigene
`orb_positions`-Tabelle zeigen **fünf echte ORB-Markt-Entries** (Tickets
263484451, 265611336, 265611343, 266307594, 266316110, alle `dry_run=0`),
**zwei ctnl_continuation-Gold-Entries** und **acht neue
OU-Modell-Aktienpositionen** - insgesamt 15 Eröffnungen und 12 Schließungen.
Die Feststellung "Equity fiel trotzdem von 3.460,62 auf 3.313,61" stimmt,
die Begründung "kommt aus den vorher eröffneten OU-Positionen" nur teilweise.
Kein Schaden entstanden, aber der Eintrag sollte korrigiert werden, bevor er
als Ausgangspunkt für die nächste Auswertung dient.

**5.4 — EKs ORB-Bein riskiert nach der 09-10-Kalibrierung 0,042 % je Trade
und ist damit faktisch wirkungslos.**
Gemessen an den echten Fills: `orb_sp500` am 09-10 mit 0,33 Lots und 4,81
Punkten Stopabstand = **1,59 $ Risiko** auf ein Konto von ~3.355 €. Rechnung
aus der Config: `ORB_COMBINED_RISK_PCT = 0.01`, geteilt durch 3 Instrumente,
mal `CAPITAL_WEIGHT = 1/8` → **0,0417 % der Equity je Trade**. Zum Vergleich
im selben Konto: `gold_asb` effektiv 2,93 %, `trend_pullback` 1,83 %,
`ou_modell` 0,37 %. Das ist **kein Bug** - die 1/8-Verdünnung wirkt korrekt
und einheitlich. Der Effekt entsteht daraus, dass ORBs Basiswert
unverändert von FKs konservativer Kalibrierung übernommen wurde und der
2,20x-Hochskalierung vom 09-10 nicht unterlag, während sechs andere Beine
sie bekamen. Praktisch heißt das: **alle fünf ORB-Trades dieser Woche
zusammen bewegten EKs Equity um −7,63 €**, ein einziger OU-Stop-out um
−32,23 €. Wenn ORB auf EK etwas beitragen soll, braucht es eine eigene
Kalibrierungsentscheidung; wenn nicht, kostet es nur Ausführungsrisiko.
Herleitung im Config-Kommentar selbst, siehe [[paper-bot-zu-live-bridge]].

**5.5 — Zwei von vier EK-ORB-Entries kamen mit ~50-56 % des Risikos bereits
verbraucht an - EK hat als einzige Bridge keinen R-Detektor auf diesem Bein.**
Aus Signal-Stop und echtem Fill nachgerechnet:
09-10 `orb_sp500` Signal-Entry 7600,56 / Stop 7595,75 (R = 4,81), Fill
7598,15 → **50,1 % von R verbraucht**, Stop 12 Sekunden später.
09-10 `orb_nasdaq` Signal-Entry 29172,05 / Stop 29139,86 (R = 32,19), Fill
29153,96 → **56,2 % verbraucht**, Stop 11 Sekunden später.
Die beiden Entries vom 09-11 waren unauffällig (5,8 % bzw. −5,1 %) und
überlebten 75 Sekunden bzw. 6 Minuten. Funded und FK haben seit 09-11 genau
dafür `MAX_CONSUMED_R_FOR_ENTRY = 0.50`; auf EK wurde er bewusst nur für
`cls_practical` eingebaut, weil dieses Bein seinen Stop früher am Live-Kurs
neu verankerte. **ORB verankert nicht neu** - es setzt den absoluten
Signal-Stop, ist also strukturell derselben Aufblähung ausgesetzt, gegen die
der Detektor gebaut wurde. Beide Trades hätten ihn gerissen. Kleines Geld
(0,042 % Risiko, Punkt 5.4), aber die Lücke ist echt und wird teuer, sobald
ORB auf EK je hochkalibriert wird.

**5.6 — Der Weekly-Report-Task selbst ist heute 3 Stunden 21 Minuten zu spät
gestartet - dasselbe Muster wie die Kurztakt-Task-Ausfälle.**
Trigger: `So 18:00`, `StartWhenAvailable = True`; tatsächlicher Start
2026-09-13 **21:21:25** (`LastRunTime`, bestätigt im eigenen
`scripts/reports/task_run.log`). Damit ist der im DASHBOARD auf Priorität
Hoch stehende Punkt "Kurztakt-Tasks fallen wiederkehrend aus, Task Scheduler
holt sie außerhalb des Rasters nach" **nicht mehr auf Kurztakt-Tasks
beschränkt** - er trifft auch einen wöchentlichen Task. Das ist ein
zusätzliches Indiz gegen die bisherige Arbeitshypothese (Energieverwaltung/
Modern Standby während der Nacht) und spricht eher für ein generelles
Task-Scheduler-Verhalten. Für die Diagnose des offenen Punkts relevant.

**5.7 — Ein Research-Skript läuft seit heute 14:42 Uhr, also seit rund sieben
Stunden, ohne Ergebnis.**
`scripts/research_orb_cost_probe.py` (untracked, aus der parallelen
ORB-Kostenprobe-Session) hängt in zwei Python-Prozessen (PID 15972/19076)
seit 14:42:24. Kein MT5-Bezug, also keine Order-Gefahr - aber das
Fehlerbild passt zum bekannten `dukascopy_python::_stream()`-Hang, gegen
den die Bridges am 09-09 Retry-Limits bekamen und den ein reines
Research-Skript nicht hat. Nicht angefasst (fremde Session), nur
festgehalten.

**5.8 — Scan-Fehler der Woche konzentrieren sich exakt auf zwei Tage, und
zwar auf allen drei Bridges gleichzeitig.**
Funded: 09-07 116-132 Fehler je Konto, 09-10 genau 2, 09-11 106 je Konto,
09-08/09-09 null. FK: 09-07 9, 09-10 16, 09-11 33. EK: 09-07 11, 09-11 6.
Sämtliche Funded-Fehler sind als "known" klassifiziert (also der bekannte
dukascopy-Bug, kein neues Fehlerbild). Die Verteilung deckt sich mit den im
CHANGELOG dokumentierten Kurztakt-Task-Ausfällen (09-07 Fast5 ~45 Min.,
09-11 zwei Fenster 00:14-02:29 und 13:16-14:38) - **keine neue Ursache,
aber diese Woche der zweite unabhängige Beleg dafür, dass der Lake-Ausfall
und nicht die Strategie-Logik die Fehler erzeugt.**

**5.9 — Lokaler `main` liegt 5 Commits vor `origin/main`.**
`origin/main` steht auf `c49f202` (2026-09-13 14:01), lokal fünf Commits
weiter. Deutlich harmloser als die 64-Commit-Divergenz aus KW36 (die
`Sync-AndPush`-Reparatur vom 09-09, Commit `a34cb8a`, wirkt offenbar), aber
die fünf heutigen Commits - darunter die komplette CLS-Kostenvalidierung und
die Wochenend-Pause - sind noch nicht auf GitHub gesichert. Dieser
Report-Lauf committet weisungsgemäß nur lokal.

**5.10 — Nebenbeobachtung zum Lauf selbst: parallele MT5-Nutzung.**
Um 21:22-21:23, also eine Minute nach dem Start dieses Reports, hat ein
anderer Prozess (`python -`) vier MT5-Terminals gestartet. Das hat die
ersten Verbindungsversuche dieses Laufs blockiert (IPC-Timeouts auf EK und
FK) und ist der Grund, warum EKs Historie erst im vierten Anlauf kam. Kein
Schaden - aber ein Hinweis darauf, dass parallele Sessions und der
Report-Lauf sich um dieselbe MT5-IPC-Schnittstelle streiten. Der
FK-Terminal-Prozess, den dieser Lauf selbst gestartet hat, wurde am Ende
wieder geschlossen (siehe Memory: `weekly_checkup_stray_terminals_20260901`);
die vier fremden Terminals blieben unangetastet.
**Nachtrag 2026-09-14:** der Nachhol-Lauf hat gar kein Terminal gestartet -
alle fünf liefen bereits als fremde Prozesse (seit 09-13 21:22 bzw. 09-14
00:03), es wurde also auch keines geschlossen.

**5.11 — NEU (2026-09-14): Eine Handposition auf einem Bot-Konto verschiebt
den Kill-Switch des Bots, taucht in seinem Risikodeckel aber nicht auf.**
Direkte Folge aus 5.1, und der eigentlich wichtige Teil daran. Die FK-Bridge
behandelt fremde Positionen in ihren beiden Schutzmechanismen
**gegensätzlich**:

- `_check_trailing_dd_gate()` bekommt `info.equity` - also **inklusive** des
  schwebenden Gewinns/Verlusts der Handposition. Der 5-%-Trailing-Drawdown-
  Floor des Bots wird damit von einem Trade mitbewegt, den der Bot weder
  kennt noch schließen kann. Dasselbe gilt für das Sizing: jedes Bein rechnet
  `CAPITAL_WEIGHT * LEG_RISK_PCT * equity`.
- `_aggregate_open_risk_dollars()` läuft dagegen über die **eigenen**
  State-Einträge der Bridge (`positions_get(ticket=…)` je selbst platziertem
  Ticket). Die 32 Pips Risiko der Handposition (~240 $) tauchen im
  Offenes-Risiko-Deckel also **nicht** auf.

Heißt konkret: eine fremde Position kann den Bot in Richtung Kill-Switch
schieben, ohne dass sein Risikodeckel sie je sieht. **Der Bot hat es selbst
gemeldet und es hat niemand gelesen** - seit 09-11 15:14 steht in jedem
Stundenlauf die Zeile *"Kontostand $99.996,25 weicht von
STARTING_EQUITY=$100.000,00 ab -- beeinflusst den Trailing-DD-Floor"*. Das
ist exakt dieser Effekt, nur über die Kommission statt über den Buchverlust.
Akut ist der Betrag harmlos (−145 $ von 100.000 $, der 5-%-Floor liegt
Welten entfernt) und es ist **kein Fehlverhalten** - die Bridge kann nicht
wissen, dass sie sich ein Konto teilt. Die Frage dahinter gehört dem Nutzer:
**soll auf den Bot-Konten von Hand gehandelt werden?** Wenn ja, sollte die
Trailing-DD-Basis um fremde Positionen bereinigt werden, sonst kann ein
Handtrade den ganzen Bot stilllegen. Wenn nein, war dieser Trade ein
Versehen. **Nicht angefasst** - das ist eine Nutzerentscheidung, keine
Bugfix-Frage. Für die nächste Wochenauswertung ist die praktische Lehre
kleiner und härter: **Kontostand ≠ Bot-Ergebnis**, sobald ein Mensch
Zugriff auf dasselbe Login hat.
