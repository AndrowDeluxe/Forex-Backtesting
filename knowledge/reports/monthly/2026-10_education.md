# Monthly Checkup - Education - Oktober 2026

**Zeitraum: 01.10. bis 27.10.2026** (Synthese aus den Weeklies KW40-KW43
plus Memory und `knowledge/`-Notizen; verspaetet am Di 27.10. erzeugt).

## 1. Der Monat in einem Absatz

Der Oktober begann als **Monat der Schutzregeln** (KW40: CTNL-Kill-Switch auf
allen Bridges, Positionsdeckel, AIG-Drehtuer zu, ORB US30 pausiert) und wurde
am 05.10. zum **Monat der Pruefdisziplin**: Weil die ORB-Konfiguration auf
OOS-Zahlen ausgewaehlt worden war, kam die Overfitting-Sperre (KW41), und von
da an lief jede Idee durch Lock, Trial-Zaehlung und einmaliges Oeffnen.
Diese Sperre hat in drei Wochen mehr verworfen als bestaetigt: ORB IS-only
fiel im Tresor durch, drei Intraday-Momentum-Edges auf US-Indizes starben
gleichzeitig, alle sieben Mikrostruktur-Kandidaten scheiterten an den Kosten,
Key Levels erwiesen sich als Magnet statt Wand. KW42 fragte deshalb, ob man
den Kipp eines Live-Beins kommen sieht (nein; nur Schadensbegrenzung), und
baute die Edge-Ampel. In KW43 verschob sich der Schwerpunkt auf das
**Dachprojekt Quant x diskretionaer**: Mentor-Material (Copy-Trading-Calls,
Makro-Reports, CLS-Call) wurde ausgelesen und getestet, mit dem ernuechternden
Ergebnis, dass die Richtung allein keinen Edge hat. Daneben zog sich ein
operativer Faden durch alle vier Wochen: **Der Rechner selbst** (Standby,
Akku, Serverzeit) hat mehr Trades gekostet als jeder Code-Fehler.

## 2. Die wichtigsten Erkenntnisse des Monats

### 2.1 Wer auf dem Pruefdatensatz auswaehlt, misst am Ende sich selbst (vier Faelle, ein Muster)

**Befund:** Vier Faelle im Monat, alle mit derselben Form. (1) **ORB**: Die
Live-Konfiguration war ab Stage 2 auf OOS ausgewaehlt; neu nur auf IS
optimiert fiel sie im Tresor durch (**PF 0,52, DSR ca. 0**). (2)
**NASDAQ-Storno am SL**: ueber 10 Jahre ohne Storno **+584 R**, mit nur
**+198 R**; gewaehlt worden war es auf einem Fenster, das 2026 enthielt. (3)
**Oel-Filter fuer ORB**: der explizit an 2026 angepasste Filter macht 2026
+39/+46 R, DSR ca. 0. (4) **Copy Trading**: der beste von 124 Versuchen hatte
t 2,9, erklaert durch offene Gold-Longs bis zur angenommenen 90-Tage-Grenze.

**Mechanismus / Warum:** Jede Auswahl unter vielen Varianten bevorzugt die,
deren Rauschen zufaellig gut zum Pruefzeitraum passt. Wird derselbe Zeitraum
danach als Beleg benutzt, misst er die Auswahl, nicht den Edge. Bei
Regimewechseln (2026) ist das besonders tueckisch: Eine Regel, die nur im
Zieljahr existiert, laesst sich trivial "profitabel" filtern.

**Wie es aufgefallen ist:** Nicht durch schlechte Live-Zahlen, sondern durch
Fragen nach der Herkunft ("woher kam die Wahl eigentlich?", KW42) und durch
den Tresor als letztes, unberuehrtes Fenster. Beim Copy Trading durch die
Aufteilung nach Ausstiegsgrund.

**Lehre:** Die Overfitting-Sperre (05.10.) ist der strukturelle Fix und hat
im Monat funktioniert. Neu dazu: Entscheidungen von **vor** dem 05.10. sind
verdaechtig, bis sie mit getrennten Fenstern nachgerechnet sind, und bei
offenen Zielen gehoert die Haltegrenze zu den Parametern.
siehe Memory: `orb_auswahl_auf_oos_prozessluecke` · `nasdaq_storno_ist_2026_fit` ·
`copy_trading_is_kein_edge_offene_trades` · [[overfitting-sperre]]

### 2.2 2026 ist das Jahr, in dem die Bot-Edges duenner werden, und man sieht es nicht kommen

**Befund:** ORB: Der Ribbon-Filter kippte 2026 ("neutral" schlug "Trend" in 16
von 18 Jahren, im Tresor umgekehrt). Drei Intraday-Momentum-Edges auf
US-Indizes starben gleichzeitig (Noise-Area-Tresor negativ). Gold ASB
verduennt sich treppenfoermig (**Oe R +0,33 → +0,18 → +0,04**). Fuenf
Fruehwarnsignale an 7 bekannten Bruechen: **keines warnt vor dem letzten
Hoch**; der beste Drawdown-Schalter kostet gesunde Beine im Median -3,4 R und
greift ca. 6 Monate nach dem Hoch. Gleichzeitig hast du am 18.10. gesagt:
2025 hat nur das Hand-Trading getragen (Eigenkonto +120 %, ca. 10.000 USD auf
einem 100k-Funded-Konto), und die Trade-Inventur zeigte, dass das Plus aus
Positionen ueber einem Tag kam.

**Mechanismus / Warum:** Die Live-Beine sind ueberwiegend kurzfristige
Intraday-Effekte auf denselben Maerkten (US-Indizes, Gold). Wenn sich das
Regime dreht (2026: Oel-Index-Kopplung, andere Trendstruktur), kippen sie
zusammen. Ein Kipp sieht in den ersten Wochen aus wie eine normale
Pechstraehne.

**Wie es aufgefallen ist:** Tresor-Check aller Live-Beine (14.10.),
Regimewechsel-Tests (die Bruchphase als IS faellt sofort durch), Gamma-Daten
als Gegenprobe (erklaeren den Kipp nicht). Live bestaetigt: ORB ist im
Oktober auf allen Bridges das teuerste Bein (ca. -2.040 USD).

**Lehre:** Bei Live-Beinen nicht auf ein Fruehwarnsignal hoffen, sondern den
Preis eines Schalters festlegen. Und den Fokus dorthin verschieben, wo der
belegte Ertrag liegt (diskretionaer, mehrtaegig; Edge Card "Dayli Trade mit
IPDA").
siehe Memory: `edge_kipp_nicht_vorhersagbar` · `orb_ribbon_filter_kippt_2026` ·
`intraday_momentum_us_indizes_stirbt_2025` · `gold_asb_verduennt_statt_bruch` ·
`diskretionaer_2025_traegt_funded_fokus` · [[edge-fruehwarnung-kill-switch]]

### 2.3 Live wird eine andere Strategie, sobald Kerze, Zeitpunkt oder Reihenfolge nicht stimmen

**Befund:** Fuenf Faelle in vier Wochen. AIG-Drehtuer (KW40: drei Runden an
einem Tag, weil live erlaubt war, was der Backtest gratis ausschloss).
Fill-Bar-Stop (KW40: der Stop wurde in der Fuellkerze nicht geprueft, eine
ganze Trade-Klasse fehlte im Backtest). Engine-SL auf Kerzenschluss gegen
Broker-SL intrabar (live ca. **0,1 R je Trade** schlechter). OU-Einstieg auf
der laufenden Tageskerze (KW43: drei verwaiste Echtgeld-Positionen ueber
Wochen). Der Positionsdeckel, der bestimmt, welche Trades ueberhaupt
existieren (KW40/42: TTP nahm wochenlang keinen CTNL-Trade, weil drei
Altpositionen den Deckel belegten).

**Mechanismus / Warum:** Ein Backtest sieht nur fertige Kerzen, fuehrt jeden
Ausstieg sofort aus und kennt keine Nebenbedingungen zwischen Konten. Live
laeuft der Kurs weiter, Laeufe kommen alle 5 bis 60 Minuten, und
Positionen aus der Vergangenheit blockieren die Gegenwart.

**Wie es aufgefallen ist:** Fast immer ueber eine Log-Zeile, die nicht zur
Erwartung passte ("Titel fehlt im Scan", "max_concurrent_reached", drei
Einstiege je Titel und Tag), und dann ueber den Vergleich mit den
Broker-Deals.

**Lehre:** Jede Annahme des Backtests (fertige Kerze, Ausstiegszeitpunkt,
Exklusivitaet) muss live ausdruecklich erzwungen werden. Soll/Ist ist das
Werkzeug dafuer, hat aber selbst noch Luecken (ORB-Storno, ORB-Fills).
siehe Memory: `ou_einstieg_auf_laufendem_tageskurs` ·
`orb_fill_bar_stop_and_live_order_gap` · `engine_schlusskurs_sl_vs_broker_intrabar` ·
`backtest_prueft_ein_und_ausstieg_auf_demselben_balken`

### 2.4 Kosten setzen die Untergrenze, und die Messgenauigkeit auch

**Befund:** Sieben Mikrostruktur-Kandidaten (07.10. und 18.10.), alle netto
negativ; der staerkste (Dollar-W nach dem Tokio-Fix) brutto **+1,6 bps, t
4,8**, bei Kosten von 1,1-1,3 bps. Beim gekauften EA OmniGold (KW43) haengt
die Rendite am Tick-Modell: **2026 lot-neutral +492 USD je Unze mit echten
Ticks, -212 mit OHLC**.

**Mechanismus / Warum:** Mikrostruktur-Praemien bezahlt der, der sofort
handeln muss; verdienen kann sie nur der Maker. Unsere Bridges sind Taker.
Und ein Edge von 1-3 USD je Trade ist kleiner als die Unschaerfe zwischen
Datenquellen (Dukascopy vs. MT5: 0,2-0,5 USD).

**Wie es aufgefallen ist:** Durch den Abgleich der Brutto-Effektgroesse mit
`smh_microstructure/costs.py` und durch denselben EA-Lauf mit zwei
Tick-Modellen.

**Lehre:** Unter ca. 3x Rundturn-Kosten gar nicht erst testen, ausser eine
Maker-Ausfuehrung ist realistisch; und ein Edge, der kleiner ist als die
Datenunschaerfe, ist nicht messbar.
siehe Memory: `mikrostruktur_praemie_gehoert_dem_maker` ·
`omnigold_edge_haengt_am_tickmodell` · [[smh-elite-mikrostruktur]]

### 2.5 Die Maschine ist Teil der Strategie: Verfuegbarkeit und Uhrzeit

**Befund:** Vier Ausfaelle in der Handelszeit (28.09. ca. 7 h, 12.10. 7 h,
15.10. 1 h genau ueber dem ORB-Fenster, 20.10. 7 h mit leerem Akku). Am
20.10. ging ein ORB-Gewinner von +5,97 R verloren. Am 26./27.10. fiel ORB auf
drei Konten aus, weil die Bridges eine falsche Serverzeit-Regel hatten.

**Mechanismus / Warum:** Das Notebook schlaeft unterwegs (Deckel,
Bildschirm-Aus, Akku), und der Watchdog laeuft auf derselben Maschine.
Zeitpunktgebundene Beine (ORB) holen nichts nach. Die Serverzeit-Regel
"Helsinki" war im Sommer nicht von "NY + 7" zu unterscheiden.

**Wie es aufgefallen ist:** Lueckensuche ueber alle Logs (alle Lanes still =
Maschine), dann das Ereignisprotokoll; bei der Serverzeit die
Sicherheitspruefung, die den Scan lieber abbrach als falsch handelte.

**Lehre:** Ausfallerkennung gehoert ausserhalb des Rechners, und
zeitpunktgebundene Beine brauchen eine Maschine, die nicht unterwegs ist.
Zeitregeln je Broker an der Historie belegen, nicht an einer Sommermessung.
siehe Memory: `standby_watchdog_schlaeft_mit` · `broker_serverzeit_ny_plus_7`

## 3. Muster ueber die Wochen

| Muster | Faelle im Oktober | Struktureller Fix? |
|---|---|---|
| **Auswahl auf belasteten Daten** | ORB-OOS-Auswahl (KW41), NASDAQ-Storno (KW42), Oel-2026-Fit (KW42), Copy-Trading-t-Wert (KW43) | **Ja**: Overfitting-Sperre seit 05.10.; offen: Altentscheide vor dem 05.10. nachrechnen |
| **Backtest-Annahme live nicht erzwungen** | AIG-Drehtuer, Fill-Bar-Stop (KW40), Engine-SL (KW40/41), OU-Tageskerze (KW43) | **Teilweise**: jeder Fall einzeln behoben; Soll/Ist als Detektor, aber mit eigenen ORB-Luecken |
| **Maschine schlaeft** | 28.09., 12.10., 15.10., 20.10. | **Nein**: Akku-Fix verschiebt nur; VPS auf November gelegt |
| **Zeitkonventionen** | Lake-Stempel (Sept.), MT5-Tester EET (20.10.), Broker NY+7 (27.10.) | **Ja fuer die Bridges** (27.10.); Research-Skripte `research_ou_*` offen |
| **Ausgelesenes Material ist fehlerhaft** | SMH-Reports v1, Copy-Trading 9/50, PDF-Text (Sept.) | **Ja als Regel**: Nutzer-Stichprobe vor dem Einfrieren |
| **Edges duenner 2026** | ORB, Intraday-Momentum, EU-Open, Gold ASB | **Nein, nur Anzeige**: Edge-Ampel; Schalter-Idee in der Inbox |
| **Kosten > Effekt** | Mikrostruktur K1-K7, OmniGold-Mikroausstiege | **Ja als Regel**: 3x-Kosten-Schwelle |

## 4. Research-Bilanz

| Quelle / Kandidat | Behauptung | Unser Ergebnis (entscheidende Zahl) | Status |
|---|---|---|---|
| ORB IS-only (eigene Live-Strategie) | ORB-Edge mit Filtern robust | Tresor PF 0,52, DSR ca. 0 | live unveraendert (Entscheid 16.10.), Ampel ROT bei SP500 |
| ORB NASDAQ-Storno am SL | Storno verbessert | 10 J.: ohne +584 R, mit +198 R | live bleibt Storno (Entscheid) |
| ORB + Oel-Filter | Oel erklaert ORB-Tage | IS-Filter Tresor -0,68 / -0,18 R; 2026-Fit DSR ca. 0 | Forward bis 31.03.2027 |
| Zarattini Noise-Area-Momentum | robustes Intraday-Momentum | Tresor negativ; nur NASDAQ K2 + Oel-Korr. (K60) in allen Fenstern positiv (vorbelastet) | Forward bis 31.03.2027, Challenge-Gewichtung eingefroren |
| Echte Gamma-Daten (SqueezeMetrics) | Dealer-Gamma steuert Intraday-Trend | Mechanismus robust, erklaert den ORB-Kipp nicht | Kontext |
| Mikrostruktur K1-K7 (Fixings, Periodizitaet, Overnight Drift, ...) | dokumentierte FX/Index-Praemien | alle Tresore netto negativ; bester K7 -0,73 bps | verworfen |
| Key Levels (eigene Edge Card) | sichtbare Level halten | Magnet statt Wand (z bis -7,8); Doppel-BOS 0/240, Magnet-Trade 0/16 | Linie geschlossen 19.10. |
| Gold ASB IS-only + Paper-Filter | Asia-Range-Breakout in Gold | Oe R +0,33 → +0,18 → +0,04, DSR 0,24; Blindtest 2010-15 +0,239 R; kein Filter schlaegt die Basis | live, beobachten |
| Edge-Fruehwarnung (5 Signale) | Kipp vorher erkennbar | 0 von 5 warnen vor dem Hoch; DD-Schalter 7/7 Brueche besser, -3,4 R Normalfallkosten | Anzeige im Weekly |
| G8-Waehrungsstaerke (Nachbau) | Staerke als Signal | kein Signal | Kontext-Baustein |
| Copy Trading "SMH Daily Update" | kopierbarer Track Record | IS: Artefakt offener Trades; A2 eingefroren, OOS 70 Trades Oe -0,72 R, t -3,65 | verworfen (27.10.) |
| SMH-Makro-Reports v2 | Richtungs-Calls | Richtung -0,027 R; Ruecksetzer +0,060 R, DSR 0,47 | Forward bis 31.01.2027 |
| SMH CLS-Praxis-Call | drei Abweichungen besser | V1 OOS +0,15 (Basis +0,31), V2/V3 im IS schlechter | verworfen |
| Quantum OmniGold (gekaufter EA) | 100k → 1,4 Mio. | haengt am Tick-Modell; 2026 lot-neutral mit OHLC negativ | in Arbeit (Schritt 3/6) |
| Monatstrend (Faber-SMA) auf Funded | Trendfolge als Beimischung | ca. 0,5 % p.a. auf TTP | pausiert 07.10. |
| Regimekarte Wachstum x Inflation | Assets je Regime verschieden | Nachbau kalibriert (+-1,5 pp) | Baustein Makro-Agent |

**Was der Monat ueber Edge-Arten lehrt:** Kein einziger neuer Kandidat hat
den Oktober als handelbarer Edge ueberlebt. Es sterben zuverlaessig (a)
kleine Intraday-Effekte, die wir als Taker ernten muessten, (b) Filter und
Regeln, die ein bestimmtes Jahr beschreiben, und (c) fremdes Material ohne
eigene Statistik. Was traegt, ist duenn und alt (Gold ASB, CTNL long-seitig)
oder nicht bot-foermig: der Hinweis "Ruecksetzer statt Markt" und "mehrtaegig
statt Scalp" taucht unabhaengig in den SMH-Reports und in deiner
Trade-Inventur 2025 auf, und genau das ist die naechste Edge Card.

## 5. Vertiefung des Monats: Das erwartete Maximum - warum der beste von vielen Versuchen fast immer luegt

Die Weeklies haben den Deflated Sharpe (KW41) und den Block-Bootstrap (KW40)
erklaert. Hier der Kern, der beide und den ganzen Monat verbindet.

**Die Idee:** Testet man N Varianten ohne echten Edge, ist jede t-Statistik
ungefaehr standardnormal verteilt. Das Maximum von N solchen Zahlen ist aber
nicht null, sondern waechst mit N, ungefaehr wie **Wurzel(2 x ln N)**. Bei 10
Versuchen sind das ca. 2,1, bei 100 ca. 3,0, bei 1.000 ca. 3,7. Ein "t von 3"
ist also nach 100 Versuchen genau das, was reiner Zufall liefert.

**Mit unseren Zahlen:**
- **Copy Trading:** 124 gezaehlte Versuche → erwartetes Zufallsmaximum ca.
  **3,1**. Der beste gefundene Wert war **t 2,9**. Er lag also sogar leicht
  unter dem, was man ohne jeden Edge erwartet, und die Zerlegung zeigte dann
  auch den Grund (offene Gold-Longs). Das OOS bestaetigte es am 27.10.:
  t -3,65.
- **Key Levels:** 482 Versuche → ca. **3,5**. Die eine Zelle, die netto
  "knapp trug", hatte t 0,9. Kein Kandidat, voellig konsistent mit dem
  Verwerfen der Linie.
- **Mikrostruktur K5 (Tokio-Fix):** t **4,8** brutto im IS bei wenigen
  Dutzend Versuchen. Das liegt deutlich ueber dem Zufallsmaximum: Der Effekt
  ist echt. Er scheitert nicht an der Statistik, sondern an den Kosten.
- **Gold ASB IS-only:** 20.736 Varianten → ca. **4,5**. Daher die Treppe
  +0,33 → +0,18 → +0,04 R: Der IS-Wert enthaelt die Auswahl, OOS und Tresor
  zeigen, was uebrig bleibt. Der Deflated Sharpe von 0,24 sagt genau das.

**Warum Tresor und Trial-Zaehlung zusammengehoeren:** Die Trial-Zahl sagt,
wie hoch die Latte liegen muss (erwartetes Maximum). Der Tresor misst, wie
viel vom IS-Wert nach der Auswahl noch da ist. Die Treppe IS → OOS → Tresor
ist deshalb normal; alarmierend ist nur, wenn der Tresor ins Negative faellt
(ORB PF 0,52) oder wenn ein Fenster benutzt wurde, um auszuwaehlen, und dann
nochmals, um zu bestaetigen (ORB vor dem 05.10., NASDAQ-Storno).

**Was das fuer unsere Bots heisst:** Jede neue Live-Regel braucht drei Zahlen:
die Zahl der Versuche, den IS-Wert im Verhaeltnis zum Zufallsmaximum, und den
Tresor. Fehlt eine davon, ist die Regel ein Fund, kein Edge. Fuer
Forward-Tests gilt dasselbe in anderer Form: Ein Forward-Kandidat aus einem
2026-Raster (Oel-Fit, Noise-Area-Regime) muss im Forward nicht nur positiv
sein, sondern besser als das, was die Auswahl allein erklaert. Deshalb
stehen die Erfolgskriterien vorab im Lock.

## 6. Netto-Bilanz

**Verbesserungen:**
- Overfitting-Sperre als Routine (seit 05.10.; Locks fuer ORB, Noise-Area,
  Gold ASB, Key Levels, Mikrostruktur, Copy Trading, SMH-Reports, CLS-Call).
- Schutzregeln live: CTNL-Kill-Switch auf allen Bridges, Positionsdeckel 2,
  AIG-Drehtuer zu, Fill-Bar-Stop/ORB-Order-Luecke behoben, ORB US30 pausiert.
- Edge-Ampel im Weekly, Tresor-Check aller Live-Beine als Skript.
- OU nur auf fertigen Tageskerzen (19.10.), Akku-Flags (19.10.),
  Serverzeit NY+7 (27.10.).
- Altpositionen geraeumt, TTP-CTNL wieder handlungsfaehig.
- Neue Bausteine fuer den Makro-Agenten (Regimekarte, Wirkketten,
  Faktor-Katalog, G8-Sync, SMH-Import).

**Verschlechterungen / Rueckschlaege:**
- Vier Ausfaelle des Rechners in der Handelszeit, einer davon nach dem Fix.
- Drei Live-Entscheidungen auf nachweislich schwachem Grund bewusst
  belassen (ORB SP500 ROT, NASDAQ-Storno, Gold ASB duenn).
- ORB-Serverzeitfehler (2 Tage, drei Konten).
- Research der zweiten Monatshaelfte grossteils nicht committet.
- Monatsergebnis aller Bridges ca. -0,36 %; Funded nur durch
  Handschliessungen knapp im Plus.

## 7. Offen in den naechsten Monat

1. **VPS fuer die Bridges** (von dir auf November gelegt). Naechster Schritt:
   VPS/IP-Regeln bei TTP und BeyondIQ klaeren, dann Umzug im Plan-Modus mit
   DRY_RUN-Probebetrieb.
2. **Research committen** (Copy Trading, OmniGold, Key Levels, Locks,
   Notizen). Naechster Schritt: ein Sammel-Commit, bevor ein Auto-Task den
   Working Tree anfasst.
3. **Edge Card "Dayli Trade mit IPDA"**: Phase 0 wartet seit 18.10. auf deine
   Antworten. Naechster Schritt: die Fragen aus dem Chat vom 18.10.
   beantworten.
4. **ORB-Entscheid erneut ansehen, wenn die Ampel ROT bleibt**: orb_sp500 ist
   seit 14.10. ROT, ORB ist das teuerste Bein des Monats. Naechster Schritt:
   nur mit Forward-Daten, nicht auf altem OOS (Overfitting-Sperre Punkt 6).
5. **Soll/Ist fuer ORB reparieren** (Storno modellieren, Fills zuordnen) und
   die CTNL-Zeitversetzung klaeren.
6. **TTP-OU STT/FLEX/UAL pruefen** und den Boersenzeiten-Gate fuer
   OU-Ausstiege entscheiden (echtes Geld).
7. **Forward-Stichtage im Blick:** SMH-Reports 31.01.2027, ORB-Oel und
   Noise-Area/K60 31.03.2027.
