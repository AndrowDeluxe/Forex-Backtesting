# SMH Elite 3 – Teamaufgabe „Mikrostruktur & Liquidität“

Gruppenarbeit aus dem Elite-Call-Briefing vom 06.10.2026 („Wir bauen eine
profitable Strategie“). Unser Team hat das Feld Mikrostruktur und Liquidität.
Gerechnet am 07.10.2026. Code liegt in `smh_microstructure/`, der Runner in
`scripts/research_smh_microstructure.py`, die Ergebnisse in
`smh_microstructure/results/`. Fortschritt und Steckbrief stehen auf der
Notion-Seite in der Datenbank „🎓 ELITE 3“ (ID in
`smh_microstructure/notion_page.json`).
Verwandt: [[fx-microstructure]], [[overfitting-sperre]],
[[baltussen-tagesend-momentum]], [[overnight-reversal-erste-halbe-stunde]].

## Material
Telegram „SMH Elite 3“, Thema Material/Pdfs, Nachrichten 1438–1467 (30 PDFs).
Für das Feld relevant ist vor allem Execution-Literatur: GS Market Structure
2009, die Algo-Guides von JPM, SG und SunGard, die HSBC-FX-Algos, Lehalle
„Navigating Liquidity“, Sofianos zu Dark Pools und Barry Johnson. Daraus
ergibt sich der Mechanismus „wer vorhersehbar handeln muss, zahlt“. Fertige
Signale enthält das Material nicht.

## Aufbau
- **Split (Nutzervorgabe):** IS 04/2018–03/2023 (5 Jahre, doppelt so lang
  wie OOS), OOS 04/2023–09/2025 (2,5 Jahre), Tresor ab 01.10.2025.
  Registriert in `knowledge/_research_lock/smh_k*.json`.
- **Ablauf vorab festgelegt:**
  1. Je Kandidat die beste IS-Variante einfrieren.
  2. OOS öffnen und den Team-Kandidaten nach OOS wählen, bevor der Tresor
     geöffnet wird.
  3. Den Tresor für alle drei Kandidaten einmal öffnen.
- **Kosten:**
  - FX (Pips je Rundturn): EURUSD 1,2, USDJPY 1,4, AUDUSD 1,5, GBPUSD 1,6.
  - Indizes: SP500 2,6 bps, NASDAQ 2,3 bps.
- **Versuche:** 27 insgesamt (K1 11, K2 7, K3 9).

## Ergebnis: alle drei gescheitert

| Kandidat | IS | OOS | Tresor |
|---|---|---|---|
| K1 Runde Zahlen, Fade (Osler), 4 FX | PF 0,69, t −16 | PF 0,65, t −13 | PF 0,65, t −7 |
| K2 Fix, nur Monatsende (Evans, Melvin/Prins) | PF 0,97 | PF 0,71 | PF 1,31 (52 Trades, t 0,8) |
| K3 Liquiditäts-Reversal, hohe Vola (Nagel), SP500/NASDAQ | PF 0,85 | PF 1,22 (fast nur 2024) | PF 0,84 |

## Erkenntnisse
- **Runde Zahlen wirken wie ein Magnet, nicht wie eine Wand.** Brutto
  verliert der Fade an x.xx00 −0,054 R (t −5,8). An sechs Schein-Leveln
  liegt er zwischen −0,012 R und +0,015 R. Oslers Abprall-Befund (2003)
  dreht sich auf FX 2018–2023 also um. Daraus wird trotzdem keine
  Kaskaden-Strategie: Auch Ausbrüche hinter der Zahl laufen auf M1 zurück.
- **Der Fix-Effekt ist real, aber kleiner als die Kosten.** Am Monatsende
  liegt er brutto bei +1,3 bps, die Kontrollzeiten liegen bei −1,6 bzw.
  +0,3 bps. An normalen Tagen ist er null.
- **Eine Intraday-Liquiditätsprämie ist auf den Index-CFDs nicht messbar.**
  Ohne z-Filter ist das Ergebnis genauso gut oder besser.
- **Prozessfehler, im Lock-Protokoll vermerkt:** Die Daten der jeweiligen
  Stufe wurden ohne Vorlauf abgeschnitten. Dem Vola-Filter von K3 fehlten
  dadurch 120 Tage, im ersten Tresor-Lauf gab es nur 30 Trades. Mit
  unveränderter Regel wurde neu gerechnet (`reeval`). Der Runner lädt jetzt
  400 Tage Vorlauf aus der Vergangenheit und filtert die Trades auf das
  Stufenfenster. Grundsatz: Bei Indikatoren mit langem Fenster nie exakt an
  der Stufengrenze schneiden.
- **Nachtrag 16.10. – Zeiteinheiten-Fehler in K1:** Pandas 3 speichert den
  Dukascopy-M1-Index in Millisekunden. `round_numbers.py` rechnete die Lücke
  aber in Nanosekunden (`> 60*60*1e9`). Die Schwelle lag damit bei rund
  41 Tagen statt bei einer Stunde, Wochenend-Lücken wurden nie als Lücke
  erkannt.
  - Ereignisse in der ersten Montagskerze wurden deshalb mitgezählt.
  - Der Effekt auf das K1-Urteil ist vermutlich vernachlässigbar (t −16,
    wenige Montagsfälle). K1 wurde nicht neu gerechnet, weil es abgeschlossen
    und eingefroren ist.
  - Gefunden und behoben im Key-Level-Code (`keylevels/`, überall `as_unit("ns")`).

## Runde 2 (18.10.2026): Paper-Screening SSRN → K4–K7, alle gescheitert

Nutzerauftrag: SSRN systematisch nach dem Feld Mikrostruktur durchsuchen
(Briefing Folie 5/6), filtern, extrahieren und backtesten. Eine PDF soll nur
entstehen, wenn ein Tresor positiv ist. Screening (22 Papers + arXiv) mit
Raster `smh_microstructure/screening_v2.json`, Details in
[[mikrostruktur-paper-screening]].

- **Kandidaten:**
  - K4 Dollar-W Europa (Krohn/Mueller/Whelan JF 2024, Variante Breedon/Ranaldo),
    EURUSD/GBPUSD/USDCHF.
  - K5 Dollar-W Tokio (dasselbe Paper, Variante Gotobi nach Ito/Yamada),
    USDJPY/AUDUSD/NZDUSD/EURUSD.
  - K6 Halbstunden-Periodizität (Heston/Korajczyk/Sadka JF 2010), SP500/NASDAQ.
  - K7 Overnight Drift nach Abverkauf (Boyarchenko/Larsen/Whelan, NY Fed),
    SP500/NASDAQ.
- **Split und Kosten wie Runde 1:** Locks `smh_k4…k7_*`, Tresor bis
  16.10.2026. Je 4 deklarierte Varianten, 34 Versuche in Runde 2, 61 über
  beide Runden. Der Deflated Sharpe wird über alle 61 Versuche gerechnet.
- **Code:** `smh_microstructure/fix_windows.py`, `periodicity.py`,
  `overnight_drift.py`. Runner `scripts/research_smh_microstructure.py`
  (K4–K7 ergänzt).
- **Team-Kandidat** nach OOS, vor dem Tresor festgelegt: K4
  (`results/runde2_team_kandidat.json`).

Netto-Ø in bps je Trade (in Klammern brutto):

| Kandidat (eingefroren) | IS | OOS | Tresor |
|---|---|---|---|
| K4 nur vor EZB-Fix | −0,38 (+0,94), n 3.897 | −1,04 (+0,35) | −1,20 (+0,21), PF 0,87, n 810 |
| K5 nur nach Tokio-Fix | −0,18 (+1,60, t 4,8) | −1,60 (+0,24) | −2,35 (−0,55), PF 0,72 |
| K6 L40 | −3,08 (−0,64) | −2,70 (−0,26) | −3,34 (−0,89), PF 0,68 |
| K7 starker Abverkauf | −0,09 (+2,36), n 361 | −3,56 (−1,10) | −0,73 (+1,71), n 76 |

Ergebnis: **kein Tresor positiv, also keine PDF** (Nutzervorgabe).

### Erkenntnisse
- **Das Dollar-W gibt es, aber es zerfällt und bleibt unter den Kosten.**
  - Nach dem Tokio-Fix ist es brutto im IS klar da (+1,6 bps, t 4,8). Die um
    ±4 bzw. +8 Stunden verschobenen Kontrollfenster liegen bei +0,35 bis
    −0,9 bps.
  - Vor dem EZB-Fix liegt es bei +0,9 bps.
  - Brutto zerfällt der Effekt über OOS auf den Tresor nahezu auf null.
    Die Autoren zeigen selbst einen Knick nach 2013.
  - Die Kosten von 1,1–1,3 bps je Rundturn fressen den Rest. Das Paper sagt
    das selbst: positiv erst bei halbem Spread.
- **Mikrostruktur-Prämien gehören dem, der Liquidität stellt.**
  - Das zeigen 7 von 7 Kandidaten über zwei Runden.
  - Jeder dokumentierte Effekt lag brutto bei 0–3 bps, also in der
    Größenordnung des Spreads.
  - Wer per Market-Order einsteigt, zahlt genau die Prämie, die er ernten will.
- **K6:** Die Halbstunden-Fortsetzung kehrt sich auf den Index-CFDs um
  (brutto t −2,7 im IS). Die Regel wurde nicht nachträglich umgedreht, das
  wäre ein neuer, ungezählter Versuch.
- **K7:** Der IS-Brutto-Effekt nach starkem Abverkauf ist nicht
  fenster-spezifisch. 12–13 Uhr ist gleich gut, der Mechanismus ist also
  nicht belegt.
- **Datenfalle, behoben vor dem ersten gezählten Lauf:** Ausstiege um
  17:00 New York fielen freitags weg, weil der Wochenschluss keine Bar mehr
  liefert. Rückfall jetzt: Schluss der letzten Bar höchstens 5 Minuten davor.
- **Ausführungsannahme:** Einstiege um 17:00 New York (Rollover, breitester
  Spread) sind pauschal kostengerechnet, real wären sie teurer. Das betrifft
  nur das ohnehin verworfene Vor-Tokio-Bein.
- **Prüfliste Folie 8:**
  - 5 Tresor-Trades von K4 per Hand nachgerechnet: 5 von 5 identisch.
  - Jeder Lock zeigt genau ein Öffnen für OOS und eines für den Tresor.

## K4b-Nachtest (18.10.2026): eingefrorene K4-Regel auf frischen Paaren, Tresor durchgefallen

Nutzerauftrag: sauberer Test mit neuen Währungspaaren. Vorregistriert vor
jedem Datenblick in `smh_microstructure/k4b_vorregistrierung.json`, Lock
`smh_k4b_fix_europa_neu`, Skript `scripts/research_smh_k4b.py`.

- **Aufbau:**
  - Regel 1:1 die eingefrorene K4-Regel: Long USD Frankfurt 08:00 → 14:15,
    jetzt auf USDNOK und USDSEK. Beide sind G9-Paare im Paper und waren bei
    uns noch nie gerechnet.
  - USDCAD bleibt draußen, weil es Tresor-Paar des Key-Level-Tests ist.
  - 6 gezählte Versuche (Regel, 4 Nachbarwerte, Kosten ×2), 67 über alle
    Runden.
- **Kosten (Annahme):**
  - Dukascopy-Median-Spread, nur IS 2019/2021: USDNOK 2,67 bps,
    USDSEK 2,30 bps (EURUSD zum Vergleich 0,25 bps).
  - Dazu der EURUSD-Aufschlag von 0,80 bps.
  - Ergibt einen Rundturn von **3,47 bzw. 3,10 bps**, gut dreimal so viel
    wie bei EURUSD.

| Stufe | n | netto Ø bps | brutto Ø | PF | Zufallsfenster besser |
|---|---|---|---|---|---|
| IS | 2.598 | −1,72 | +1,57 | 0,90 | 22 % (Zufall Ø +1,02) |
| OOS | 1.296 | −1,68 | +1,60 | 0,90 | 3,7 % (Zufall Ø +0,03) |
| Tresor | 540 | **−3,63** | −0,34 | 0,76 | 59 % |

Ergebnis: Durchgefallen, nach Vorgabe keine PDF. Auch beide Hälften sind
in jeder Stufe negativ.

### Erkenntnisse
- **Der IS-Brutto-Gewinn war Dollar-Drift, kein Fix-Effekt.** Die USD-Stärke
  gegen die Skandinavier 2018–23 erntet jedes Long-USD-Fenster: Zufall
  +1,02 bps, um −3 bzw. +6 Stunden verschobene Fenster +2,5 / +3,3 bps.
  Ohne Zufallstest hätte +1,57 brutto wie eine Bestätigung ausgesehen.
- **Im OOS war das Fenster einmal wirklich fix-spezifisch** (p ≈ 0,04
  gegen Zufall). Im Tresor ist auch das weg. Das passt zum Zerfall in K4.
- **Kosten:** NOK und SEK haben den dreifachen Spread der Majors. Selbst
  ein echter Effekt von 1–2 bps wäre dort nie handelbar.
- **Prüfliste:** 5 Tresor-Trades per Hand nachgerechnet, 5 von 5
  identisch. Genau ein Öffnen für OOS und eines für den Tresor.
