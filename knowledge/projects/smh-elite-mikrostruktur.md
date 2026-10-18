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
