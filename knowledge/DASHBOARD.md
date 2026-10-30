# Dashboard

**Stand: 2026-10-03** _(wird bei jeder Session von Claude auf das aktuelle
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

1. **🧩 Dachprojekt Quant × diskretionäres Trading** (gestartet 2026-10-04,
   löst "Monatsjournal + Verschmelzung" ab — Journal-Teil erledigt):
   [[quant-diskretionaer-fusion]]. Eigene Analyse reproduzieren, testen,
   automatisieren → selbstlernender Bot. 8 Stränge (0 Inventur … 7
   Selbstlernen), Code in `fusion_lab/`.
   **Trade-Inventur 2025 läuft (seit 18.10., Plan freigegeben):** alle
   händischen Trades 2025 einlesen und zeigen, welche Konten/Setups/Sessions
   den Gewinn getragen haben. Axi-Parser steht (`fusion_lab/trades/`, 6 Tests).
   Erste Auswertung steht (18.10.). **Jetzt: Edge Card „Dayli Trade mit IPDA“**
   [[htf-daily-trade-edge-card]] -- Phase 0 wartet auf deine Antworten (Fragen im
   Chat 18.10.). Parallel: Makrofaktoren einzeln gegen die echten Trades prüfen;
   den Makro-Agenten führst du weiter. Offen: 6. Konto.
   **Aktuell: Strang 0.** OneNote vollständig importiert (3.225 Seiten),
   Telegram bis auf „SMH Daily Update“ (läuft noch). **Inventur-Entwurf
   steht (09.10.):** 30 Bestandteile in A–F, siehe
   [[persoenlicher-tradingplan-validierung]] (wartet auf deine Durchsicht,
   siehe „Braucht deine Bestätigung“). Notion-Cockpit steht (07.10., eigene API-Integration):
   Seite „Trading Fusion Cockpit“ — erste Nutzung: Gruppenarbeit Mentor.
   **Neu 14.10.:** Dennis hat zwei neue Makro-Reports hochgeladen, einer
   davon mit tieferem Ansatz. Sie fließen direkt in den Makro-Agenten ein;
   vorher ist ein Telegram-Import nötig (Bestand endet am 08.10.).
   Separat geparkt bis Makro steht: [[aktien-analyse-und-bot]].
2. **🎯 SMH-Elite-Teamaufgabe „Mikrostruktur & Liquidität“: gerechnet
   07.10., alle drei Kandidaten ehrlich gescheitert.** Tresor: K1 PF 0,65,
   K2 PF 1,31 (52 Trades), K3 (Team-Kandidat) PF 0,84. Steckbrief steht auf
   der Notion-Seite in „🎓 ELITE 3“. Offen: Präsentation im nächsten Call.
   **Runde 2 (18.10.): SSRN-Screening (22 Papers) → K4–K7 gebacktestet, alle
   4 Tresore negativ, darum keine PDF** (K4 Dollar-W Europa −1,20 bps,
   K5 Tokio −2,35, K6 Periodizität −3,34, K7 Overnight Drift −0,73).
   Befund: Mikrostruktur-Prämien liegen brutto bei 0–3 bps, also unter
   unseren Kosten. [[mikrostruktur-paper-screening]]
   **K4b-Nachtest (18.10.):** eingefrorene K4-Regel auf frischen Paaren
   USDNOK/USDSEK, Tresor −3,63 bps netto, PF 0,76, durchgefallen. Der
   IS-Brutto-Gewinn war Dollar-Drift (Zufallsfenster gleich gut).
   **Key Levels (16.10.): Edge Card fertig ([[keylevel-edge-card-final]], auch
   in Notion unter 📁 Edge Cards). Stufe 1 fertig: Magnet robust (Vorwoche >
   Session ≈ runde > halbe Zahl), Pivots und Engulfing ohne Effekt. Nur
   „Vorwoche, M1, G = 20, Durchlauf“ kommt weiter. Nächster Schritt: Stufe 2
   (Kontext) auf dieser Zelle.**
   **18.10.: Doppel-BOS-Einstieg getestet – 0/240 Zellen, kein Effekt.
   19.10.: Magnet-Trade getestet – 0/16 Zellen. Gesamtfazit: Der Magnet
   wirkt nur ab der Berührung und ist nach Kosten nicht erntbar. Offen:
   Linie schließen oder als Stop-Platzierungs-Regel weiterdenken.**
   Früherer Schritt (07.10.): Key-Level-Ansatz vertiefen. Runde
   Zahlen wirken wie ein Magnet, nicht wie eine Wand. OOS und Tresor von K1
   sind schon geöffnet, deshalb braucht eine neue Regel einen eigenen Lock
   und frische Prüfdaten (andere Märkte oder Forward).
   [[smh-elite-mikrostruktur]]
3. **🥇 Gruppenarbeit: Gold ASB IS-only gerechnet (15.10.), PDF für den
   Mentor steht (18.10.):** `Claude outputs/gold_asb_profitabilitaets_kriterien_20261018.pdf`. IS +0,33 → OOS +0,18 → Tresor +0,04 R je Trade (PF 1,19,
   18 Trades), Deflated Sharpe 0,24. Der Edge hält knapp, wird aber dünner.
   **18.10. Paper-Filter:** keiner schlägt die Basis; Blindtest 2010–2015 bestanden
   (Ø +0,239 R, t 2,85, 5/6 Jahre +). [[gold-asb-paper-filter]]
   [[gold-asb-is-only-neuanalyse]]

---

## 📋 Offene Punkte (nach Priorität)

Zusammengeführt aus "Braucht deine Bestätigung" + "Offene Aufgaben" — nach
Priorität sortiert, erledigte Punkte pro Kategorie unten. Höchste Priorität:
offene Projekte mit konkretem nächstem Schritt (aktuell keins offen — der
gold_asb-Cache-Bug oben läuft über "Als Nächstes"). Danach: Bestätigungs-
Bedarf vor generischem Aufräumen.

### 🔍 Braucht deine Bestätigung

- **Copy Trading Stufe 2, 4 Annahmen von mir** (28.10.,
  `projects/copy-trading-dennis-edge-card.md` Abschnitt Stufe 2):
  1. „BE ziehen“, während der Kurs unter unserem Entry steht → wir schließen zum Kurs.
  2. Teilschluss ohne genannten Anteil → 50 %.
  3. Zeitbezug der Anweisung: heute ≤ 24 h, gestern 6 h–4 Tage, letzte Woche 2–14 Tage, ohne
     Angabe ≤ 30 Tage nach dem Call, gleiches Symbol.
  4. „Invalide“ streicht nur wartende Orders, laufende Trades laufen weiter (Regel 7).

- **Skill-Test ORB + CTNL, 6 Annahmen von mir** (28.10.,
  `projects/skill-test-orb-ctnl.md`):
  1. IS-Fenster der neuen Sperren: ORB 2019–2022 (TTP-Simulation statt Historie ab
     2016), CTNL 2019-01 bis 2024-07.
  2. Forward-Mindestzahl an Trades: ORB 150, CTNL 40.
  3. Die CTNL-Richtung habe ich aus Gold-Kursen abgeleitet (Stop-Trades zu 100 %
     konsistent).
  4. Ersatzquellen, weil FMP im Free-Tier sperrt: FRED-Kalender statt FMP-Kalender, CFTC
     statt FMP-COT.
  5. Breadth ohne Zyklus- und Perzentil-Komponente (Lookahead in den Daten).
  6. Den Drawdown-Breaker habe ich mit seinen 4 Standardregeln 1:1 nachgebildet, statt das
     Skill-Skript aufzurufen.

- **Skill `mt5-robot-tester` lokal angepasst** (28.10., eigene Annahme).
  - Deutsche Berichtsbezeichnungen ergänzt und den Zahlen-Abschneidefehler behoben (`~/.claude/skills/mt5-robot-tester/scripts/`, nicht in Git).
  - Bei einem Skill-Update gehen die Änderungen verloren.
  - Alternative: das Tester-Terminal per Ansicht → Sprache auf Englisch stellen.
  - Details [[mt5-tester-portable]].

- **Data Lake: CTNL-Daten waren durch Zeitzonen-Chaos UND Twelve-Data-Failover verfälscht**
  (28./30.10., behoben; zwei Dinge brauchen deine Bestätigung). Zeitzonen-Duplikate: siehe
  CHANGELOG 28.10. Neu am 30.10.: Der Failover schrieb pauschal 500 Kerzen (Volumen 0, eigenes
  H4-Raster, Wochenenden) rückwirkend in 11 Reihen (Gold H4/H1/M15/M5, USDJPY H4, EURUSD M5,
  5× M15-FX), ohne Logzeile. Belegt: 484 von 485 Vergleichskerzen = Twelve Data.
  **Korrektur meiner Aussage vom 28.10.:** „Live-Einstiege im Oktober nicht betroffen“ ist so
  nicht haltbar. Live-Scans rechneten nach einem Failover auf den Fremdkerzen; wann genau
  welche Kerzen im Lake lagen, ist nicht rekonstruierbar. Nachrechnung ab 21.09., Stand heute
  verfälscht vs. sauber: nur 9 gemeinsame von 23 bzw. 26 Signalen. Das ist die Obergrenze, nicht
  was live ablief. Einzelne Oktober-Trades sind nicht zugeordnet. Das Soll der Weekly Reports
  seit etwa Oktober ist unzuverlässig.
  **Bitte bestätigen:** (a) Failover darf nur noch anhängen, nie Historie ändern, und H4 von
  Twelve Data wird wegen des anderen Rasters ganz abgelehnt, bei Dukascopy-Ausfall steht H4
  also still. (b) Bereits im Lake gespeicherte Kerzen sind jetzt unveränderlich bis auf die
  letzten zwei; spätere Dukascopy-Korrekturen älterer Kerzen werden verworfen (mit Warnung).
  Offen, Niedrig: Warum der Failover ohne Logzeile lief (Vermutung: abgebrochene Läufe nach
  dem Aufwachen, Ausgabe wird erst am Ende geschrieben).

- **Residual-Edge-Check, 4 Annahmen bzw. Abweichungen von mir** (28.10.,
  `projects/residual-edge-check.md`):
  1. gold_silver aus der Tickmill-Liste `ampel` statt TTP (fehlt dort).
  2. Näherungs-Baselines: SPX für ou_modell (Aktienkorb), Gold für trend_pullback
     (Multi-Markt).
  3. Regime nach Wachstum × Inflation statt VIX: VIX endet lokal am 14.08. und deckt den
     Tresor nicht ab.
  4. Trend-Gegenprobe bei trend_pullback und CTNL entfällt, weil sie im Fenster identisch
     mit dem Basiswert ist.

- **Key Levels, Doppel-BOS-Einstieg: 4 Annahmen von mir** (18.10.,
  im Chat aufgelistet):
  1. Beobachtungsfenster 8 h ab Levelberührung.
  2. Swing-Fractal k = 2 auf M5 und M15.
  3. Volumenprofil über die letzte H4-Range.
  4. Druckschwelle z ≤ −1 (Short) bzw. ≥ +1 (Long).

  Bitte bestätigen oder ändern; jede Änderung zählt als neue Variante.
  [[keylevel-edge-card-final]]

- **K4b-Nachtest (18.10.): Kosten USDNOK 3,47 bps / USDSEK 3,10 bps je
  Rundturn sind geschätzt.** Grundlage: Dukascopy-Spread (Ask minus Bid,
  IS 2019/2021) plus der Nicht-Spread-Aufschlag von EURUSD. Am Broker ist
  das nicht gemessen. Am Urteil ändert es nichts, der Tresor ist schon
  brutto negativ. [[smh-elite-mikrostruktur]]
- **Trade-Inventur 2025 (18.10.): drei eigene Festlegungen.** (a) Axi-Buchung
  „Data Truncation DDMMYYYY“ wird als Startsaldo zum Datum im Text gewertet, nicht
  zum Buchungsdatum (bei 4667999/4690858 erst im August gebucht). Davon hängt das
  Ergebnis in % vom Konto ab. (b) Statement-„Balance“ wird nicht gegengeprüft: Sie
  ist der Stand von 07/2026, das Statement deckt nur 2025 ab. (c) Offene Position
  6059496 EURUSD Buy 1,01 Lot seit 17.06.2026 ohne SL/TP (am 21.07. −1.614 $), nur
  vermerkt, nicht angefasst. Ist sie noch offen und gewollt?
  [[quant-diskretionaer-fusion]]


- **Mikrostruktur Runde 2 (18.10.): Screening-Punkte und Kandidatenwahl
  K4–K7 sind meine Einschätzung** (Raster `smh_microstructure/screening_v2.json`).
  Bewusst getestet: Overnight Drift (K7), obwohl die Autoren selbst den
  Zerfall melden. Nicht getestet: Gold-Tageszeitmuster (nur Masterarbeit).
  Bitte bestätigen oder fehlende Papers nennen. [[mikrostruktur-paper-screening]]
- **Mikrostruktur Runde 2: Einstiege um 17:00 New York (Rollover) mit
  pauschalen Kosten gerechnet, real teurer.** Gotobi-Tage sind ohne
  japanische Feiertage bestimmt. Beides ändert kein Urteil, alle vier
  Kandidaten sind negativ. [[smh-elite-mikrostruktur]]

- **Key-Level-Backtest: Kosten der 6 frischen Paare sind geschätzt, nicht
  gemessen** (16.10.). Round-Turn in Pips: USDCAD 1,6, USDCHF 1,6, NZDUSD 1,8,
  EURGBP 1,6, EURJPY 1,8, GBPJPY 2,5. Grundlage: typische Raw-Spreads plus
  dieselbe Kommission und Slippage wie bei den gemessenen Majors.
  `smh_microstructure/costs.py`. Bitte bestätigen oder Broker-Werte nennen.
  [[keylevel-edge-card]]

- **ORB-Öl-Filter: zwei Forward-Kandidaten, Stichtag 31.03.2027** (12.10.,
  [[orb-gegenprobe-oel]]). (1) IS-Filter „Öl gegen Ausbruch“, (2) 2026-Fit
  (Korrelationsregime → Trend-Tage + Öl gegen Ausbruch), ausdrücklich kein
  Beleg. Meine Annahmen: Merkmalsfamilien und Gitter selbst gewählt; Option-2-
  Split formal (OOS = leeres Fenster 01.–11.10., nur für die Lock-Regel).
  Auswertung: `python scripts/research_orb_oel_filter.py --stage forward-evaluate`.
  Bis dahin nur ~20–25 Trades je Index → höchstens ein Hinweis.
- **CTNL-State: Altpositionen ohne Zeit-Exit + verwaiste `placed`-Einträge**
  (12.10., Weekly Checkup KW41, Performance Abschnitt 6 Punkt 1; ECHTES
  GELD, nichts angefasst). Offen ohne `max_hold`/TP: TTP 18696522 +
  18696950 (30.09., 8 Handelstage), IQ 1973249 + FK 1973231 (02.10.,
  Signal 13:00 – der 12:45-Zwilling wurde am 08.10. korrekt per `max_hold`
  geschlossen). TTP blockiert damit den CTNL-Deckel (3 offen, Grenze 2).
  Zusätzlich stehen ausgestoppte Shorts weiter als `placed` im State (FK:
  7x vom 01.10., IQ/FK: 08.10. 17:00 + 09.10. 01:45). Meine Hypothese
  (unbelegt): Signal-Schlüssel hat sich mit „eine M15-Bar früher“ (03.10.)
  verschoben. Entscheidung nötig: Altpositionen schließen? Exit-Abgleich
  gegen Broker statt Sim-Schlüssel?
  **Update 19.10. (Nutzer):** Altpositionen von Hand geschlossen, bis auf
  eine, die der Nutzer auf Break-even gesetzt hat. Offen bleibt der
  Code-Teil (Exit-Abgleich, verwaiste `placed`-Einträge).

- **📅 31.03.2027: Forward Noise-Area-Momentum Regime 2026** (Übersicht aller
  Forward-Tests: [[optimierte-edges-uebersicht]]; Nutzerentscheid
  14.10., [[zarattini-noise-area-momentum]]). Breites Raster (9.216 Varianten
  je Index) auf 10/25–03/26: Die Fade-Gewinner sind schon in OOS und Tresor
  durchgefallen (DSR ~0). Sie laufen trotzdem mit, zusammen mit K1
  Paper-Original und K2 „nur 1. Trade, halten bis 16:00“. K2 war auf NASDAQ
  2026 in allen drei Fenstern positiv (vorbelastet, n 23–80). Erfolg vorab:
  Netto-bps/Trade > 0 und besser als K1. Auswertung:
  `python scripts/research_noise_area_regime2026.py evaluate`.
  **+ Öl (14.10.):** zweiter Forward am selben Stichtag: SP500-Filter „nur
  wenn Öl ruhig“ (Lock `noise_area_oel_filter_20261014`, Auswertung
  `python scripts/research_noise_area_oel.py evaluate`). Annahmen vom
  Nutzer am 14.10. bestätigt.
  **+ Öl-Fit (14.10.):** NASDAQ K2 + Korr. 40 T. < −0,1 + Öl bewegt (Lock
  `noise_area_oel_fit2026_20261014`, `research_noise_area_oel_fit2026.py evaluate`;
  SP500-Fit formal mit, kein Kandidat).
  **+ Hauptkandidat (Nutzerentscheid 14.10.): NASDAQ K2 + Öl-Index-Korr. 60 T. < 0**
  (Lock `noise_area_oel_k60_forward_20261014`, `python scripts/forward_noise_area_k60.py
  evaluate`; Sizing 1x / dyn / 1 % Risiko). Backtest auf 100k vorbelastet:
  IS +40,6 %, OOS +9,2 %, Tresor +10,4 % (1x).
  **+ Challenge-Gewichtung (16.10., Nutzer: „so laufen lassen“):** TTP: K60 ohne Stop 1 % +
  ORB-NASDAQ 0,25 %; IQ: K60 0,75 % + ORB-NASDAQ 0,25 %; je max. 2 Trades/Tag, mit O2 und
  mit O1 (Lock `challenge_k60_orb_oel_gewichtung_20261016`, Forward ab 19.10.). Danach
  entscheiden, ob und wie das auf die Challenge-Konten geht. Kein Livegang davor.

- **Noise-Area / Challenge-Gewichtung: vor einem Livegang klären** (16.10.,
  [[zarattini-noise-area-momentum]]). (1) Kann IQ (BeyondIQCapital) NASDAQ handeln? Für TTP
  ist USTEC bekannt, für IQ ist kein Index-Symbol verifiziert (`check_symbols.py`). (2) TTP-
  Kommission auf USTEC ist mit 0 angenommen. (3) Der Optimierer rechnet additiv ohne
  Lot-Rundung; die Ereignis-Sim mit Zinseszins zeigte keine Brüche, die Lot-Rundung ist
  ungeprüft.
  **Zu (1), Beobachtung aus dem Weekly KW42 (18.10.), bitte bestätigen:** IQ handelt
  NASDAQ bereits: Die Funded-Bridge platzierte dort am 13.10. und 16.10. ORB-Orders auf
  `NAS100.gbe` (Risiko je Seite ca. 107 USD). Ob Kosten und Haltedauer bis 16:00 für K60
  passen, ist damit nicht geprüft.

- **Gold-ASB-Fill vom 15.10. fehlt in Soll/Ist und Edge-Ampel** (Weekly KW42, 18.10.).
  Live füllte die Stop-Order auf allen 4 Konten (zusammen ca. −765 USD, Zeit-Exit), das
  Soll meldet „kein Signal“, die Ampel-Liste führt als letzten Gold-ASB-Trade den 28.09.
  Meine Vermutung, ungeprüft: Liquiditätsfilter kippt beim Nachrechnen (Memory
  `gold_asb_liquidity_filter_reproducibility`) oder die Nachrechnung modelliert die
  Stop-Order-Variante nicht. Solange das offen ist, messen beide Werkzeuge das größte
  EK/TTP-Bein nicht live-getreu.

- **ORB-Gegenprobe Öl: meine Annahmen** (11.10., [[orb-gegenprobe-oel]]).
  (1) Öl-Kosten 4,0 bps Spread + Index-Slippage (~0,15 R je Trade), nicht am
  Broker gemessen. (2) April 2020 ausgelassen (WTI nahe null). (3) Öl-Uhr
  09:00–14:30 (NYMEX) als zweite Variante, selbst gewählt. (4) Lesart
  „ORB-Edge lebte vom Tag-zu-Tag-Umkehr-Regime“ ist eine Hypothese. PDF für
  den Mentor: `Claude outputs/orb_profitabilitaets_kriterien_oel_20261011.pdf`.

- **📅 31.01.2027: SMH-Makro-Reports Forward/OOS einmal öffnen** (Lock
  `smh_macro_reports_v2`, [[smh-makro-reports-backtest]]). IS 21.10.: Calls
  allein ohne Edge, Rücksetzer-Einstieg D +0,06 R (kein Beleg); Kandidaten
  D, nur 5 Sterne, Edelmetalle, keine FX-Kreuze. Vorher Reports ab 08.10.
  mit EXTRACTION.md v2 extrahieren. (Stichproben 1+2 und Datenregeln vom
  Nutzer bestätigt.)

- **📅 31.12.2026: Forward-Vergleich ORB live mit und ohne Gamma-Regler**
  (Nutzerentscheid 07.10.). Vorab registriert:
  - A = ORB-Live wie bisher.
  - B = halbes Risiko an Tagen, an denen das SPX-GEX vom Vortag im unteren
    oder oberen Fünftel liegt.
  - Je 100k ab 05.10.

  Auswertung: `python scripts/forward_orb_gamma_regler.py --stage evaluate`
  (öffnet erst ab dem Stichtag). Danach entscheiden, ob B live geht.
  [[gamma-mechanismen-gex]]

- **✅ Entschieden 16.10. (Nutzer): ORB bleibt erstmal so** — SP500 trotz roter
  Edge-Ampel weiter live, NASDAQ behält das Storno am SL (obwohl über 10 Jahre
  ohne Storno besser, siehe [[orb-order-storno-und-haltedauer]] Nachtrag 16.10.).
  Schutzmechanismen (Trailing-DD-Gate, Offenes-Risiko-Deckel) bleiben getrennt
  von der Edge-Ampel. Warnstufen laufen im Weekly Report (Schritt 5b).
- **✅ Entschieden 06.10. (Nutzer): ORB live bleibt, wie es war.** Kein Pausieren und
  keine Risikosenkung. Der echte Test ist der Forward ab 05.10. (Lock-Regel:
  ≥ 100 Trades je Index oder 31.03.2027). Hintergrund:
- **ORB: IS-only-Version fällt im Tresor durch (06.10.). Was heißt das
  für die live laufende ORB?** Details: [[orb-order-storno-und-haltedauer]]
  (Nachtrag 06.10.).
  - **Auswahl:** nur auf IS 2016–2022, 7 Punkte je Index (Richtwert max. 9),
    SP500 + NASDAQ. Long+short bzw. long, Ribbon neutral, Stop 1,0 ATR, 8R.
  - **Ergebnis:** OOS hielt (PF 1,34). Tresor 10/2025–09/2026: −87 R,
    PF 0,52. 100k-Konto bei 1 % Risiko → 40,5k (−59,5 %).
  - **Deflated Sharpe:** ~0.
  - **Live-Version zum Vergleich:** im Tresor SP500 +5 R, NASDAQ +55 R. Sie
    wurde aber mit Blick auf genau diesen Zeitraum gewählt, ist also kein
    fairer Test.
  - **Live wurde NICHT geändert.** Offen: ORB live weiterlaufen lassen,
    Risiko senken oder pausieren? Annahme bis zur Entscheidung: alles bleibt,
    wie es ist.
  - **Diagnose (06.10.):** Gekippt ist der EMA-Ribbon-Filter, nicht die
    ORB-Mechanik. „Neutral“ schlug „mit Trend“ in 16 von 18 Index-Jahren (Ausnahmen ~0);
    im Tresor dreht es sich bei beiden Indizes um. **SP500 live nutzt
    „neutral“, ist also direkt betroffen.** NASDAQ live hat keinen Ribbon.
    Details im Projekt-Nachtrag „Diagnose“.
  - **Neue-Regime-Runde (06.10.) auch durchgefallen** ([[orb-neues-regime-2026]]):
    3. Ausbruch / Fehlausbruch, IS = der Bruch → OOS −31 R / ±0, Tresor
    −8 / −13 R. **SP500 live im Backtest 2026: OOS −4,9 R, Tresor −8,5 R.**
    NASDAQ live +18 / +33 R (vorbelastet). Die Entscheidung SP500-ORB
    pausieren ja/nein bleibt offen.

- **🟡 Inventur-Entwurf Tradingplan (09.10.): bitte durchsehen.** Die
  Bestandteile-Liste in [[persoenlicher-tradingplan-validierung]] habe ich
  aus „Tradingplan 1.1 2026“, „Meine Trading Edges“ und der Daily
  Checklist 04/2026 gebaut. Dabei habe ich Folgendes angenommen:
  - Tradingplan 1.1 2026 ist der gültige Plan. Er ist zwar auf 05/2025
    datiert, liegt aber im Abschnitt „Oktober 2026“.
  - „New London Edge EU only“ (08/2026) ist dasselbe wie das archivierte
    [[london-range-bos-retest-eurusd]], also schon negativ getestet.
  - Bei der Herkunft (Plan oder Kurs) habe ich nach Seitentitel und
    Abschnitt geschätzt.
  - Acht „Final“-Edges (Midnight Spike, Pre Manipulation, NY, 16:00 Uhr …)
    bestehen nur aus Chartbildern. Ihre Regeln müsstest du diktieren.
  - Mindset, Kontensystem und Payout-Regeln (Block F) habe ich als nicht
    automatisierbar ausgeklammert.
  **Frage:** Fehlt etwas, oder ist etwas falsch einsortiert? Danach legen
  wir die Reihenfolge für Strang 1 (Edge Cards) fest.

- **🟢 Dachprojekt Quant × diskretionär (04.10.): meine Annahmen.** Details:
  [[quant-diskretionaer-fusion]].
  - Ordnername `fusion_lab/` und Notizname „quant-diskretionaer-fusion".
  - Notion-Struktur: eine Seite „Trading Fusion Cockpit" mit den Datenbanken
    Makro-Übersicht, Analysen, Entscheidungslog (Bot), Zwischenablage.
  - Telegram-Import mit deinem eigenen Konto (Telethon), weil Bots fremde
    Gruppen nicht lesen können; Zugangsdaten in `.streamlit/secrets.toml`.

- **🟡 Challenge + EK Gewichtung (04.10.): entschieden -- TTP neu
  eingespielt, IQ und EK bleiben wie gehabt.** Details: CHANGELOG 04.10.
  **Zu prüfen:** der erste TTP-Entry nach dem Umschalten. Gold ASB sollte
  ~600 $ Risiko zeigen (vorher ~333 $), ou_modell ~50 $ (vorher ~167 $).
  Danach diesen Punkt löschen.
  **Lücke Simulation vs. echte Konten -- zerlegt 04.10.:** Fast die ganze
  Lücke liegt in Beinen, deren Live-Logik im Zeitraum umgebaut wurde. Größter
  Posten ist CTNL Reversal, das live 22-75 Positionen machte, im heutigen Code
  nur 2. **Offen:** ob Gold ASB und ORB nach dem Umbau (Stop-Orders seit
  01.10. bzw. 17.09., Storno seit 03.10.) die Simulation live treffen, zeigt
  erst der wöchentliche Soll/Ist-Bericht der nächsten Wochen.
  IQ behält bewusst P(Bruch) ~8,6 %/Jahr (Nutzerentscheid).
  **Meine Annahmen, bitte bestätigen:** BTC-Kosten, Tickmill-EURUSD 0,8
  Pips, XAG/XPT/JPY-Kosten = Engine-Defaults, Kontraktgrößen für den
  Mindestlot. Außerdem: Das Modell rechnete CLS ohne Zins-Multiplikator,
  live wirkt er weiter (Median 1,75x).

- **🟡 EK-Umbau + trend_pullback 3,0 ATR -- umgesetzt 04.10. (Nutzerfreigabe),
  erster echter Lauf ausstehend.** Details: CHANGELOG 04.10.
  **Zu prüfen beim ersten Signal:**
  (a) EK gold_silver/trend_pullback-Entry **ohne TP** beim Broker, im
  Telegram „Ziel … (Kerzenschluss, kein Broker-TP)“.
  (b) Der Exit kommt als „EXIT (Ziel Kerzenschluss)“, sobald eine H1/H4-Kerze
  jenseits des Ziels schließt. Im EK-Fast-Log stehen die Zeilen
  `gold_silver_scan_exit` / `trend_pullback_scan_exit` je Lauf (leere Liste =
  nichts zu tun).
  (c) trend_pullback-SL liegt bei 3 ATR (1,5x so weit wie zuvor), das Ziel
  bei 6 ATR -- auf EK, TTP und IQ.
  Danach den Punkt löschen. Rückweg: `EK-Portfolio-Bridge/_backup_20261004_scan_exit/`,
  `mt5_trend_pullback/pipeline.py` per git.
  **Bestätigt, nichts zu tun:** gold_silver-Stop 2,0 ATR (Walk-Forward jedes
  Jahr 2,0). Funded/FK im allgemeinen Pfad baugleich.

- **🔴 FK: offene Beine + Gewichtung neu gerechnet (04.10.) -- ersetzt den
  Vorschlag vom 03.10. darunter.** Der 03.10.-Vorschlag ist durch die
  ORB-Änderungen vom 04.10. überholt: US30 ist pausiert, NASDAQ hat jetzt
  Storno am SL und kein Teilziel mehr. Mit dem heutigen Stand ist FK bereits
  deutlich sicherer: P(Bruch) 4,6 %/Jahr statt 11,9 %, 2026 +9 %.
  **Offene Beine:** gold_silver (Ø R +0,95, 8/8 Jahre positiv, Walk-Forward
  wählt es in jedem Jahr) und trend_pullback (Ø R +0,36, 2021/22 negativ,
  Walk-Forward wählt es fast nie). Beide sind zum Portfolio praktisch
  unkorreliert.
  **Vorschlag je Trade:** gold_asb 0,15 % · cls 0,30 % · ctnl_rev 0,10 % ·
  SP500 0,10 % · NASDAQ 0,10 % · gold_silver 0,25 % · trend 0,125 %.
  Ergebnis: P(Bruch) 1,5 %, MC-Median +15,9 % statt +10,6 %/Jahr.
  Walk-Forward +84 % statt +60 %.
  **✅ Entschieden 04.10.: gold_silver LIVE mit 0,20 % je Trade,
  trend_pullback bleibt Paper.** Der übrige Gewichtungsvorschlag oben ist
  NICHT eingespielt. Ausführungsprobe: CHANGELOG 04.10.
  **Zu prüfen beim ersten gold_silver-Signal:** Entry auf XAUUSD.gbe mit
  ~200 $ Risiko (Lot-Rundung kann weniger ergeben). Der Exit kommt per
  Slow-Lauf, nicht über einen Broker-TP. Danach den Punkt kürzen.
  **Klarstellung:** Der „verpasste“ Trade vom 18.09. lag nicht am
  Altersfilter, sondern an einem Datenausfall (Lake veraltet +
  Dukascopy-Hänger, alle FK-Scans fielen aus). Der gemeinsame Scan-Fehler
  `'>' not supported between 'str' and 'float'` trifft cls/gold_asb/ctnl/
  trend (Offene Aufgabe).

- **⚪ (überholt, siehe oben) FK: neue Gewichtung gerechnet (MC + Walk-Forward, 03.10.) -- NICHT
  eingespielt.** Gerechnet mit der Logik von heute, also inkl.
  ORB-Storno bei Gegenbruch und CTNL-Broker-TP. Die heutige Gewichtung hat
  P(5-%-Trailing-Bruch) **11,9 %/Jahr**. In der Ereignis-Simulation
  2019-2026 reißt sie die Grenze am 14.05.2024; 2026 bleibt sie knapp
  darunter (MaxDD −4,74 %).
  **Vorschlag CAPITAL_WEIGHT:** gold_asb 0,175 · cls_practical 0,30 ·
  ctnl_reversal 0,375 · orb_sp500 0,30 · orb_us30 **0** · orb_nasdaq 0,15.
  Ergebnis: P(Bruch) 1,1 %, MC-Median +10,8 %/Jahr (heute +11,9 %),
  2019-2026 MaxDD −2,69 % statt −6,13 %.
  **Vorbehalt:** das CLS-Gewicht springt im Walk-Forward (0,075-0,325). CLS
  läge damit bei 0,45 % Risiko je Trade, nahe am 0,5-%-Deckel.
  **Soll ich das in `fk_instant_funding/paper_bot.py` einspielen?** Wirkt
  live auf FK beim nächsten Lauf.
  ✅ Annahmen (CLS-Versatz 1 M5-Bar, Gold-ASB 30 Min., CTNL 1 M15-Bar,
  ORB-Slippage aus Funded-Fills, Swap ignoriert) vom Nutzer bestätigt
  04.10. Details: CHANGELOG 03.10.
  **Korrektur:** die erste Meldung von heute („Konto 2026 am 26.08.
  gescheitert“) galt für die ALTE ORB-Logik (Order bis 16:00).

- **🟠 CTNL: Funded/FK jetzt auf EK-Takt, aber EKs SL-Logik bewusst NICHT
  übernommen** (03.10., Befund 21 in [[ctnl-kostenvalidierung]]). Umgesetzt
  ist nur der frühere Einstieg (−14 Min.). ✅ (1) „nur Timing“ vom Nutzer
  bestätigt 03.10. ✅ Die Frage „EK auf absoluten Signal-SL?“ ist durch den
  Exit-Standard vom 03.10. erledigt (Befund 22e). **Neu zu prüfen
  Sonntagabend/Montag:** Hat der erste CTNL-Entry je Konto (EK, TTP, IQ, FK)
  einen Broker-TP, und liegt EKs SL auf dem Signal-Niveau? ✅ (2) Stop der
  vorgezogenen Zeile (ATR der Signalbar) laut Nutzer erledigt, 04.10.

- **🟡 ORB: Umstellung 04.10. — erster echter Lauf Montag 05.10. beobachten**
  ([[orb-order-storno-und-haltedauer]]). Auf allen drei Bridges: SP500/US30
  storniert wie im Backtest, NASDAQ Storno am geplanten SL + ohne Teilziel
  (eine Order je Richtung), US30 pausiert, neue Telegram-Texte. Alles offline
  getestet. **Zur Kenntnis:** Telegram meldet jetzt ggf. „Order storniert --
  Kurs erreichte den geplanten SL vor dem Einstieg“ und gelegentlich
  „gefüllt, obwohl ... -- sofort geschlossen“ (erwartet ~1× je 4 NASDAQ-Tage,
  kleiner Verlust/Gewinn). Bestätigen, wenn der erste Tag sauber lief.

- **Gold ASB laeuft seit 03.10. als Stop-Order -- erster echter Lauf Mo 05.10.
  pruefen** (07:00 Berlin Platzierung bzw. Grund fuer "keine Order" im Log,
  09:00 Storno, 17:00 Zeit-Exit; auf allen drei Bridges). Deployt vom Nutzer,
  Details CHANGELOG 03.10. und [[gold-asb-kostenvalidierung]]. Die Bridge-
  Aenderungen liegen ausserhalb von Git -- Rueckweg ueber die Backups
  `<Bridge>/_backup_20261001_gold_asb/`. Pruefbefehl, ob die Verdrahtung noch
  da ist: `grep -c manage_gold_asb_pending` in Funded/FK `run_once.py`
  (erwartet >= 2) und `ls EK-Portfolio-Bridge/legs/gold_asb/pending_executor.py`.
  **Zur Kenntnis (FK):** bei 1,5x Range rundet FK auf 0,01 Lot ab -- real
  ~60 $ statt ~120 $ Risiko, das Bein laeuft dort mit halbem Risiko. **EK:**
  0,01 Lot = ~53 EUR (1,9 % der Equity).

- **Gegenlesen beim naechsten CTNL-Signaltag.** Verifiziert ist der
  Code-Stand (alle fuenf Einstiegspunkte, funktionaler Test mit gefaketem
  Executor), NICHT ein echter Live-Durchlauf mit Order. Im Log sollte
  stehen: "N von M Signalen behalten; X gegen den Trend verworfen". Bleibt
  die Meldung aus, greift das Gate nicht.
  **Beleg (Weekly KW40, 04.10.):** Die Meldung steht seit 30.09. in den Logs
  von Funded und FK, z.B. "9 von 28 Signalen behalten; 19 gegen den Trend
  verworfen". Die Verwurfquote liegt bei 63-68 %, erwartet waren ~60 %. Echte
  Entries mit Gate gab es am 01.10. (FK) und 02.10. (IQ/FK/EK). Abhaken
  liegt bei dir.

- **CTNL: Spike-Filter live + Kill-Switch umgestellt -- beim nächsten Lauf
  kontrollieren** (2026-09-30, Befund 19). Nach deinen Entscheiden: (1) Der
  Kill-Switch rechnet jetzt auf dem GEHANDELTEN Satz (Ribbon + Spike, −1,10 %
  statt −7,01 %) und **hebt sich beim nächsten Lauf auf FK, TTP und IQ auf**,
  CTNL handelt dort wieder. (2) `ctnl_reversal` nimmt nur noch Signalkerzen
  ≥ 0,75 ATR. (3) Der Flacker-Fix und die FK-Log-Zeile sind drin.
  (a) Schwelle −6,6 %/−3,3 %: **Nutzerentscheid 04.10.: neu kalibrieren** auf
  dem gehandelten Satz (Ribbon + Spike) -- steht unter Offene Aufgaben.
  (b) Kerzenfilter nur für reversal -- erledigt, continuation ist stillgelegt.
  **Zu prüfen:** Telegram meldet „CTNL-Drawdown erholt“ je Konto, und im FK-Log
  erscheinen „Spike-Filter behaelt …“-Zeilen. Nebenbei unverändert offen:
  auf EK riskiert ein CTNL-Trade ~25 EUR = ~0,9 % Equity (Mindestlot, Befund 10).

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
  **Geklärt 19.10.: DD/EOG (und STT 16.10.) tauchen nie wieder auf.** Sie
  wurden auf dem noch laufenden Tageskurs eröffnet: Intraday lag der Kurs
  unter dem Bollinger-Band, zum Tagesschluss nicht mehr (DD 128,04 > 123,06,
  EOG 141,38 > 140,35, STT 165,72 > 164,75). Mit fertigen Tageskursen
  enthält kein Scan die Trades. Das Modell wäre ausgestiegen: DD am 22.09.
  (131,80), EOG am 05.10. (144,08, jetzt 158). **Entscheidung nötig (echtes
  Geld):** (a) DD/EOG/STT von Hand schließen oder weiterlaufen lassen?
  (b) Code-Fix in `challenge_portfolio/paper_bot.py` (wirkt sofort live):
  OU nur auf abgeschlossenen Tageskursen einsteigen lassen, wie validiert.
  **(b) erledigt 19.10.:** live seit 11:05 (`7c26f58c` + Funded-`run_once.py`,
  Details CHANGELOG 19.10.). Offen bleibt nur (a).
  **(a) teilweise erledigt 22.10. (Nutzer, bestätigt 28.10.):** DD und EOG von Hand
  geschlossen. **STT ist weiter offen**, ebenso FLEX (15.10.) und UAL (16.10.);
  ob FLEX/UAL vom Modell geführt werden, ist nicht geprüft.
  **Worauf schauen (neu, Niedrig):** Yahoo liefert `^GSPC`/`^NDX` zeitweise nicht
  (19.10. vormittags, 15.10., 12.10., 18.09.); der OU-Scan hat dann 0 Trades und
  meldet für jede offene Position „Titel fehlt im Scan“. Es wird dabei nichts
  geschlossen, es entstehen aber auch keine Einstiege. Idee: Benchmark über den
  Lake oder SPY/QQQ als Ersatz holen. Häufig läuft der Scan dabei auch ins
  20-s-Limit („OU-Modell-Scan fehlgeschlagen … 20s“, 19.10. 11:14, 18.09., 24.09.).
  Details: [[ou-modell-kostenvalidierung]].

- **🟠 Split-Schutz fehlt weiterhin — abgetrennt vom MNST-Punkt (2026-09-30).**
  Der Geldbetrag oben ist erledigt, **die Ursache nicht**: ich habe geprueft,
  in `Funded-Portfolio-Bridge`, `EK-Portfolio-Bridge` und
  `FKInstantFunding-MT5-Bridge` gibt es **keinerlei Behandlung von
  Aktiensplits** (die Treffer auf "split" sind alle `leg.split()` bzw.
  `executor.split_volume()`). Gleichzeitig handelt `ou_modell` auf Funded UND
  EK Einzelaktien — dasselbe Ereignis kann sich also jederzeit auf einem der
  aktiven Konten wiederholen. Den Punkt mit dem Konto zu schliessen waere
  bequem, aber falsch. **Nutzerentscheid 04.10.: Alarm bauen** (nur Meldung,
  keine Automatik) -- noch nicht gebaut. Erkenntnis beim Planen: ein Alarm
  NACH dem Kurssprung kommt zu spaet (MNST-SL loeste zur Eroeffnung aus), er
  muss anstehende Splits der gehaltenen Titel VORHER melden -- braucht eine
  Datenquelle fuer Split-Termine. Wird als eigenes kleines Vorhaben geplant.

### Offene Aufgaben

- **EK-CTNL: Live-Trades ohne Gegenstück in der Simulation** (gefunden 28.10.). Von
  01.10. bis 23.10. finden sich 6 von 7 echten EK-`ctnl_reversal`-Trades nicht in der
  Tickmill-Simulation (`live_trades_tickmill_ampel.csv`, ±60 Min., UTC). Die Simulation hat
  im ganzen Zeitraum 01.09.–23.10. nur 5 CTNL-Trades, live waren es 27. Vor 30.09. erklärt
  die bekannte Orderflut die Lücke, danach nicht. Prüfen, ob die EK-Bridge dieselben Gates
  nutzt wie die Simulation (Ribbon, Spike, consumed_r) und ob der Deckel 3 statt 2 ist.
  Echtes Geld, darum **Hoch**. Daten: `skill_test/results/ek_fills_orb_ctnl.csv`.
- **Forward-Auswertung der zwei Skill-Filter am 31.03.2027** (oder früher, wenn die
  Mindestzahl an Trades erreicht ist): `unseal("forward")` für
  `orb_skill_filter_20261028` (ORB-H1) und `ctnl_skill_filter_20261028`
  (News-Tag-Filter). Gefiltert gegen ungefiltert auf den Forward-Trades. Bis dahin kein
  Live-Eingriff. Niedrig (Termin).

- **Gemeinsamer Scan-Fehler `'>' not supported between instances of 'str'
  and 'float'`** (gefunden 04.10.): FK-Slow-Lauf seit 07.09. bei cls_practical
  8x, gold_asb 4x, trend_pullback 4x, ctnl 2x (von 483 Läufen). Er trifft
  mehrere Beine, die Ursache liegt also vermutlich in gemeinsam genutzten Daten
  (Lake-Spalte als Text?). Ursache suchen. Mittel.

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

- **🟠 Untersuchung: Lake veraltet → Läufe hängen bis ~1 h → Fehlerzeilen**
  (Nutzerentscheid 04.10., fasst sechs alte Einzelpunkte zusammen: str/float-
  Fehler, LakeStaleDataError ×2, „unerwarteter Fehler“ ×2, Kurztakt-Ausfälle,
  Lake-Frischefenster). **Spur:** jede grössere Lücke im EK-Fast-Takt seit
  24.09. (28.09. ~8 h, 29.09. ~1 h, 01.10. ~1 h) endet ZEITGLEICH mit einer
  dieser Fehlerzeilen. 01.10.: Lake GOLD_M15 ab ~12:25 veraltet, Live-Fallback
  (Dukascopy) ~19 s je Versuch in Schleife, Fast-Lauf 12:20 hing eine Stunde.
  **Offen:** warum hängt der Fast-Lauf (er nutzt MT5-Daten, nicht den Lake)?
  Warum fällt der Ingest aus? Danach: Frischefenster nach Timeframe staffeln?
  Geklärt: Funded läuft mit `source="lake"`. Schon gehärtet 04.10.: Cache-
  Schreiben atomar (`cbce4434`).
  **🔍 Widerspruch aus dem Weekly KW40 (04.10.), bitte bestätigen:** Die
  **28.09.-Lücke gehört nicht in diese Spur.** An dem Tag standen von 10:33 bis
  17:16 ALLE Lanes still (Funded/FK/EK, jeweils Slow und Fast) **und** der
  Watchdog. Das Windows-Ereignisprotokoll zeigt `Kernel-Power 506` um
  10:32:54 und `507` um 17:16:09, der Rechner war also im **Modern
  Standby**. Für den 01.10. zeigt das Protokoll nur Sekunden-Standby, dort
  bleibt der Hänger ein Kandidat. Offen: warum Standby trotz
  `standby-timeout-ac 0` (Akku? Deckel?). Außerdem kann der Watchdog den
  Ausfall der eigenen Maschine nicht melden. Idee: ein Totmannschalter
  außerhalb, z.B. ein Cloud-Check auf das Alter des letzten Snapshots auf
  GitHub.
  **Nachtrag Weekly KW42 (18.10.): Standby kostet jetzt ORB-Tage.** Mo 12.10.
  09:55–17:09 und Do 15.10. 14:49–15:53 (Range-Ende 15:45 → beide
  Ausbruchsseiten schon durch, keine Order). Diesmal ohne Commit-Arbeit
  tagsüber, das „Deckel/Arbeitsblock“-Muster passt also nicht. Ursache offen.
  **Geklärt 19.10.:** Der Nutzer war mit dem Notebook im Akkubetrieb unterwegs.
  Mo und Do: Zuklappen (`506 Grund: Lid`), Fr 11:36: Bildschirm-Aus nach 3 Min
  im Akku (`Idle Timeout`). Zusätzlich starteten EK-Fast und alle drei Ingests
  im Akku gar nicht, was den Lake veralten ließ und die str/float-Fehler im
  Live-Fallback auslöste. Behoben: siehe CHANGELOG 19.10. Offen bleiben
  der Totmannschalter und das 3-Min-Bildschirm-Aus im Akku (bewusst nicht geändert).
  **Rückfall 20.10. (Weekly KW43, Ursache vom Nutzer bestätigt 28.10.):** Akku leer,
  13:50–21:03 lief keine Bridge. Verpasst: ORB SP500 (Soll +5,97 R) und NASDAQ
  (−1,02 R), grob +1.500 USD auf Funded+FK. Spricht für den VPS (Ideen-Inbox 19.10.).
- **Report-Werkzeuge härten** (Weekly KW42, 18.10.). Niedrig.
  (a) `mt5_pull.py`: bei 0 Deals und offenen Positionen warten und
  wiederholen (kaltes Terminal); FK-Terminal mit `/portable` starten wie
  `executor.py` (sonst `IPC timeout`). (b) `research_live_legs.py --ampel`:
  Dukascopy-Abruf ohne Timeout, hing am 18.10. dreimal an derselben Stelle,
  die Ampel blieb auf dem Stand 16.10.
- **CTNL E1 + E4 (Research):** E1 `spread_bps` 8,0 → gemessen 0,53-2,01,
  broker-getrennt (steht im Code weiter auf 8,0); danach E4 Risikokalibrierung
  über die volle Historie. E2/E3 erledigt. Details
  `projects/ctnl-kostenvalidierung.md`.
- **CTNL-Kill-Switch-Schwelle neu kalibrieren** (Nutzerentscheid 04.10.): die
  −6,6 %/−3,3 % stammen von der ungefilterten Strategie; auf dem heute
  gehandelten Satz (Ribbon + Spike-Filter) neu ziehen. Research-Auftrag, gilt
  für alle drei Bridges.

**Mittel**
- **14 unverarbeitete Clippings** in `knowledge/Clippings/` (Stand
  2026-09-28-Lint, unveraendert seit 2026-09-09) — u.a. Edge-Genesis/-Decay,
  Risk-Factor-Investing, Sektor-Rotation, "Six Repos One System", "How
  system works" — noch nicht durch den CODE-Prozess.

**Niedrig**
- **Statustabelle: "Zuletzt geprüft" bei `OU-Modell-ScannerHourly` ist
  26 Tage alt** (Lint 28.09., Schwelle 21 Tage; Stand: 2026-09-02).
  Reiner Alters-Hinweis aus dem Lint-Skript, kein inhaltlicher Befund —
  Zeile bei Gelegenheit gegen den echten Task-Scheduler-/Scanner-Status
  nachpruefen und Datum auffrischen (CLAUDE.md Punkt 4).

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Letzter echter Entry | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld** (btc/ou_modell weiterhin direkt Dukascopy/yfinance; gold_asb/cls_practical/ctnl_reversal jetzt `source="lake"`; ctnl_continuation am 01.10. stillgelegt) | Ready (alle 15 Min, Mo–Fr)      | **16.09.** ou_modell (IVZ) | 2026-10-27      |
| EK-Portfolio-Bridge-Fast                                | Tickmill Live (55918977, geteiltes Terminal)                                             | **LIVE — echtes Geld** (3 MT5-native Beine: ORB/Gold-Silber/Trend-Pullback, kein Dukascopy; **ORB-US30 seit 04.10. pausiert**)  | Ready (alle 2 Min, Mo–Fr)       | ↑ gleiches Konto | 2026-10-27      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | **LIVE — echtes Geld** (6 Beine via `LIVE_LEGS`: orb_sp500/us30/nasdaq + gold_asb [**orb_us30 seit 04.10. pausiert**, `orb_pending.ORB_PAUSED_INSTRUMENTS`]/cls_practical/ctnl_reversal; ctnl_continuation am 01.10. stillgelegt, ctnl_reversal seit 30.09. auf der 5-Min-Lane; **gold_silver seit 04.10. LIVE** (0,20 %/Trade, Altersgrenze 150 Min.); trend_pullback bleibt geplant/geloggt) | Ready (stündlich, Mo–Fr)        | **14.09.** orb_nasdaq — erster echter Entry seit Livegang | 2026-10-27      |
| FKInstantFunding-MT5-Bridge-Fast                        | BeyondIQCapital (17764, geteiltes Terminal)                                              | **LIVE — echtes Geld** (ctnl_continuation + orb_sp500/nasdaq + cls_practical, `source="lake"`, analog Funded-Fast; **orb_us30 seit 04.10. pausiert**) | Ready (alle 5 Min, Mo–Fr)       | ↑ gleiches Konto | 2026-10-27      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram, **nur noch trend_pullback/gold_silver** (die anderen 7 Beine laufen live über die Bridge, seit 09-09 hier entfernt) | Ready (stündlich, Mo–Fr)        | — | 2026-09-13      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner + Telegram (3x täglich: 15:35/18:35/21:35)                                           | Ready (Mo–Fr, US-Handelszeiten) | — | 2026-09-02      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator (seit 09-15: Zeitlimit 4h statt 1h, Vollständigkeitsprüfung + 3x Wiederholung alle 4h bei unvollständigem Lauf) | Ready (So 18:00 — läuft am Wochenende bewusst weiter) | — | 2026-09-15      |
| Bridge-Watchdog                                         | — (nur Log-Frische, kein Order-Bezug)                                                    | Heartbeat-Alarm + Status-Snapshot ins Repo                                                   | Ready (alle 30 Min, Mo–Fr)      | — | 2026-09-13      |
| Funded-Portfolio-Bridge (TTP 6 Beine @1/6, IQ 5 Beine @1/3) | TTP Konto 2 (504072729) + BeyondIQCapital (16054) — **2 Konten** (IQ 15514 am 2026-09-07 entfernt, **TTP Konto 1 / ttp1 am 2026-09-23 vollstaendig ausgebaut**) | **LIVE — DRY_RUN=False** (alle 6 Beine `source="lake"`; **seit 09-13 kontospezifisch: IQ ohne `ou_modell`, Kapitalanteil 1/3 statt 1/6 — IQ handelt keine Aktien**; IPC-Timeouts 09-08 09:52-12:24 Uhr, seither stabil, siehe 🔍 Bestätigung) | Ready (alle 15 Min, Mo–Fr)      | **16.09.** orb_sp500 (TTP1) | 2026-10-27      |
| Funded-Portfolio-Bridge-Fast                            | Gleiche 3 Konten (geteilte Terminals)                                                    | **LIVE — DRY_RUN=False** (ctnl_continuation + orb_sp500/nasdaq + cls_practical, `source="lake"`; **orb_us30 seit 04.10. pausiert**) | Ready (alle 5 Min, Mo–Fr)       | ↑ gleiche Konten | 2026-10-27      |
| DataLake-Ingest-Fast                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt `data_lake_store/` für Funded-Portfolio-Bridge (19 Keys, 15-Min-Kadenz)                | Ready (alle 15 Min, Mo–Fr)      | — | 2026-09-13      |
| DataLake-Ingest-Fast5                                   | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt 8 M5/M15-Timing-kritische Keys für ctnl_continuation/orb/cls_practical (EURUSD M5 seit 2026-09-07) | Ready (alle 5 Min, Mo–Fr)       | — | 2026-09-13      |
| DataLake-Ingest-Slow                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt OU-Modell-Universum (~59 Ticker) via yfinance                                          | Ready (stündlich, Mo–Fr)        | — | 2026-09-13      |
| Dashboard-Telegram-Digest (neu)                         | — (nur Lesezugriff auf DASHBOARD.md, kein Order-Bezug)                                   | Schickt offene Punkte aus DASHBOARD.md per Telegram                                          | Ready (täglich 8:00, auch Sa/So — bewusst) | — | 2026-09-13      |
| G8-Notion-Sync (neu)                                    | — (nur FRED/Dukascopy-Abruf + Notion-Schreiben, kein Order-Bezug)                       | Schreibt G8-Währungsstärke (Nachbau + SMH-Tabellen) in Notion-DB „💱 G8-Stärke“ (`scripts/g8_notion_sync_task.ps1`) | Ready (täglich 07:00, auch Sa/So) | — | 2026-10-12      |
| Regime-Notion-Sync (neu)                                | — (nur FRED/ALFRED/yfinance-Abruf + Notion-Schreiben, kein Order-Bezug)                 | Regimekarte Wachstum×Inflation neu rechnen → Notion „Regime-Roadmap“ + Seite „Assets je Regime“ (`scripts/regime_notion_task.ps1`) | Ready (So 09:00, StartWhenAvailable) | — | 2026-10-28      |
| Telegram-Import-SMH-Daily                               | — (nur Telegram lesen + rechnen, kein Order-Bezug)                                       | Inkrementeller Import „SMH Daily Update“ ohne Videos; seit 28.10. zusätzlich Bild-/Anweisungs-Lesung per Claude-Abo + Forward-Stand Copy Trading Stufe 2 (`scripts/telegram_smh_daily_import_task.ps1`, Akku erlaubt) | Ready (täglich 23:00, auch Sa/So) | — | 2026-10-28      |

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
existieren jetzt, am 03.10. vom Nutzer abgehakt), 0 verwaiste Seiten,
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

- (28.10.) **ORB-Pivots aus `strategy-pivot-designer`:**
  1. ORB als Paar-Handel SP500 gegen NASDAQ (marktneutral, gegen das Tail-Risiko).
  2. Fade am Open statt Ausbruch. Achtung: Die Open-Reversal-Edge gab es nur im Open-Print
     (SSRN 5807282 verworfen).
  3. Pullback-Einstieg mit kürzerem Horizont.

  Jede Idee wäre eine neue Sperre. Siehe `projects/skill-test-orb-ctnl.md`.
- (28.10.) **IBD-Befund umgedreht:** ORB verdient vor allem in Distribution-Phasen (an
  NORMAL/CAUTION-Tagen Ø R ≈ 0). Das ist dieselbe Aussage wie ORB-H1. Nicht separat testen,
  solange ORB-H1 im Forward läuft.

- (27.10.) **OU-Research-Skripte auf NY+7 umstellen.** `scripts/research_ou_broker_costs.py`,
  `research_ou_execution_optimization.py` und `research_ou_intraday_pull.py` rechnen
  TTP-Zeitstempel noch mit `Europe/Helsinki` und liegen damit in ~3 Wochen pro Jahr um 1 h
  daneben. Betrifft nur Research, keinen Bot. Siehe CHANGELOG 27.10.

- (20.10.) **Regimekarte: Automatikbetrieb erst beim Bau des Makro-Agenten**
  (Nutzerentscheid). Dann einbauen:
  1. Täglicher Lauf nach den US-Releases (`--refresh`).
  2. Wechsel-Log.
  3. Telegram-Meldung nur bei einem Wechsel.
  4. Abgleich Soll/Ist: Assets seit dem Wechsel gegen das Regime-Mittel.
  5. Regime-Block im Wochenbericht.

  Dazu die **Marktsicht zwischen den Prints** (Nutzerhinweis): Staatsanleihen
  bewegen sich laufend, also ein zweiter Layer aus Renditen und
  Erwartungen, der einen Wechsel vor dem nächsten Print anzeigt. Mögliche
  Reihen: 2y/10y, Breakeven T10YIE, GDPNow. Die Karte selbst wechselt per
  Definition nur an GDP-/CPI-Terminen. [[regimekarte-wachstum-inflation]]

- **Bridges auf einen VPS statt aufs Notebook** (19.10., aus der Akku-Analyse
  KW42): Unterwegs im Akkubetrieb schlafen alle Bridges beim Zuklappen bzw.
  laufen nur weiter, solange das Notebook offen bleibt. Ein Windows-VPS mit
  den MT5-Terminals hätte dieses Problem nicht. **Nutzer 19.10.: auf November
  verschoben** (Paket „Windows L+“ 4 vCores/8 GB, 27 € für 3 Mon., danach 42 €).
  Vorher klären: VPS/IP-Regeln bei TTP und BeyondIQ. Umzug im Plan-Modus mit
  DRY_RUN-Probebetrieb, Notebook-Tasks im selben Schritt abschalten.

- ~~**Magnet-Trade Richtung Key Level**~~ (getestet 19.10.: kein Effekt, siehe [[keylevel-edge-card]]) (18.10., aus der Key-Level-Edge-Card):
  Der Magnet wirkt an und vor der Berührung, nicht nach einer BOS-
  Bestätigung. Idee: Liegt der Kurs X Pips vor einem Vorwochen- oder
  Session-Level oder einer runden Zahl, in Richtung Level einsteigen, Ziel
  Level + Durchlauf. Das wäre ein neuer gezählter Versuch im Lock
  `keylevels_v1`, nur IS. [[keylevel-edge-card]]

- (18.10.) **Dollar-W nach dem Tokio-Fix (K5) nur mit Limit-Orders als Maker
  handelbar?** IS brutto +1,6 bps (t 4,8), aber zerfallend (OOS +0,24,
  Tresor −0,55). Bezug [[smh-elite-mikrostruktur]] Runde 2. Eher verwerfen.

- (16.10.) **Automatischer Drawdown-Schalter je Live-Bein** (Nutzer: „interessant“).
  Gemeinsames Modul nach dem Muster `gold_smc_htf_ltf/ctnl_kill_switch.py`
  (Schattenkonto, Hysterese, fail-open), Schwelle je Bein per Bootstrap aus
  `edge_monitor/`. Wirkt auf echtes Geld in allen drei Bridges → eigener Plan +
  Freigabe. Würde heute orb_sp500 pausieren. [[edge-fruehwarnung-kill-switch]]
- (09.10.) **Sechs-Bot-Architektur als Zielbild für den Makro-Agenten**
  (Vorlage „Six-Bot AI Trading Team With Grok“: Scout/News/Sentiment/
  Charts/Risk/Decision, JSON je Bot, Risk-Gate nur verschärfend). Eigene
  Abwandlung: Scout = G8-Nachbau, Sentiment = COT, Charts/Risk als Code,
  nur Analyst + Trade-Übersetzer als LLM, zusätzlich Kontroll-Baustein;
  Claude statt Grok. Erst nach Phase 1 (Test der alten SMH-Reports),
  gehört zu [[quant-diskretionaer-fusion]] Strang 3/6.
  Ergänzung (09.10.): Leitfaden „SebAI — 6 Claude Agents Trading Team“
  geprüft. Als System nicht übernehmen: Sechs Chats, die man per Hand
  verbindet, je Lauf eine Entscheidung und kein Backtest. Die „historische“
  Übung ist ein Lookahead (siehe Memory `llm-agent-nur-vorwaerts-testbar`).
  Übernehmen: Status INCOMPLETE neben REJECT/APPROVE, Felder „fehlende
  Infos“ und „Fakten vs. Analyse“ im Agenten-JSON, „Regeln befolgt“ und
  abgelehnte Setups im Notion-Entscheidungslog, die „Quick Fixes“ als
  Testfälle für den Kontroll-Baustein.

- (07.10.) **→ OOS 27.10. durchgefallen (Ø −0,72 R), als Bot-Grundlage verworfen; Stufe 2 (Dennis' Anweisungen) seit 28.10. im Forward-Test bis 31.03.2027 (IS-Vorab: Anweisungen senken Ø R von +0,47 auf +0,08); Edge Card fertig 20.10.,
  [[copy-trading-dennis-edge-card-final]]. Nächster Schritt: Plan-Modus für den Bau, danach
  täglicher Telegram-Import ab 23 Uhr als geplante Aufgabe.** **Copy-Trading-Bot aus den täglichen Marktupdates des Mentors**
  (eigene Telegram-Gruppe, Nutzeridee). Vor jedem Bau: die Calls der
  Vergangenheit aus dem Telegram-Verlauf extrahieren und nachtesten
  (Trefferquote, R, Kosten, Verzögerung) — erst ein belegter Edge
  rechtfertigt Automatisierung, live wäre es Gate 3. Gehört zum Dachprojekt
  [[quant-diskretionaer-fusion]] (Strang 2/5).

- (07.10.) ~~Gamma als Risikoregler~~ → **einsortiert:** vorab registriert
  im Forward-Test (`scripts/forward_orb_gamma_regler.py`, Lock
  `orb_live_gamma_forward_20261007`), Auswertung am 31.12.2026 (siehe
  „Braucht deine Bestätigung“).

- (07.10.) **Faber-Trend, falls wieder aufgenommen:** Rotation in ein Ersatz-Asset nur mit Deckel testen (z.B. höchstens ein Slot bzw. 5 % Risiko im Ersatz-Asset). Ohne Deckel landen alle Cash-Slots gleichzeitig im selben Markt (Öl: −20 %-Tage). Projekt pausiert, siehe [[faber-gtaa-10-monats-sma]].
- (05.10.) **ORB-Mechanismus testen:** Ist der Edge an Tagen mit großem
  Eröffnungs-Ungleichgewicht (großer Gap, hohes Volumen der ersten
  15 Min.) größer? Das würde Feld 1/2 (Flows/Unterreaktion) stützen. Kommt
  aus der Kriterien-PDF `Claude outputs/orb_profitabilitaets_kriterien_20261005.pdf`,
  wo „Mechanismus erklärbar“ nur gelb ist. Literatur fand genau das:
  Gao et al. (JFE 2018, stärker an Volumen-/News-Tagen) und Zarattini/Barbon/Aziz
  (SSRN 2024, „Stocks in Play“ +0,38 R gegen −0,02 R).
- (05.10.) **ORB-Gamma-Regime-Filter:** Baltussen et al. (JFE 2021) führen
  Intraday-Momentum auf Short-Gamma-Hedging zurück. Eine Blog-Messung
  (FirmTape, SPX 2022–26) findet seit 0DTE nur noch an Short-Gamma-Tagen
  einen Effekt (t = 3,1). Prüfen, ob es GEX-Historie gibt, die man als
  Filter testen könnte. Quelle: Seite 3 der Kriterien-PDF.

- (04.10.) ~~CLS als ruhende Stop-Order~~ -- **am selben Tag gerechnet und
  verworfen** (CHANGELOG 04.10.): Ø R sinkt sogar, ΣR gleich. Die heutigen
  Gates filtern die schnellen Verlierer, die eine Stop-Order mitnehmen würde.

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
- **Geplante Auswertung der Ribbon-Verwurf-Quote** (2026-10-03, beim
  Dashboard-Aufraeumen ohne Entscheid abgehakt): nach ein paar Wochen pruefen,
  ob live ~60 % der CTNL-Signale vom Ribbon verworfen werden wie erwartet.
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
