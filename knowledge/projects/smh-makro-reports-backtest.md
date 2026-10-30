# Project: SMH-Makro-Reports backtesten (Phase 1 Makro)

**Status (21.10.2026):** IS-Bewertung fertig; Forward-/OOS-Fenster läuft bis
31.01.2027 (Lock `smh_macro_reports_v2`). Teil von [[quant-diskretionaer-fusion]]
Strang 3. Wissensbasis für den Agenten: [[makro-wirkketten-und-regeln]],
[[makro-faktoren-katalog]].

## Was getestet wurde

120 Makro-Reports des Mentors (Telegram „SMH Daily Update“, 03.08.2025–
07.10.2026, drei Format-Generationen) per Claude-Unteragenten wörtlich in
JSON übersetzt (`fusion_lab/macro_reports/`, Rohdaten gitignored). v1 wurde
nach Nutzer-Stichprobe verworfen (übersehene Sterntabellen, falsche Status-
Definition), v2 mit Nutzer-Status (aktiv/event/watch/bias/inaktiv, hedge),
Sternen, Gates, Herkunft; zwei Stichproben (11 + 4 Reports) vom Nutzer
geprüft, Event-Abgrenzung vom Nutzer festgelegt (21.10.).

Bewertungsmodus (Ausnahme in [[overfitting-sperre]]): 5 Varianten vorab
eingefroren (16.10.), nichts optimiert, alle ausgewiesen. Einstieg erste
H1-Eröffnung nach Telegram-Postzeit; Kosten 1,5–10 bps je Klasse; Kontrollen
Zufallsrichtung (Permutation) und 20-Tage-Momentum.

## Ergebnis IS (netto)

| Variante | n | Ø R | Σ R | t | Perm-p | DSR |
|---|---|---|---|---|---|---|
| A1 alle Calls, halten bis nächster Report | 604 | −0,027 | −16,1 | −0,8 | 0,55 | 0,02 |
| A2 Haupttrade je Report | 105 | +0,028 | +2,9 | 0,3 | 0,27 | 0,19 |
| B Markt-Einstieg, Stop 1,5 ATR, Ziel 2 R, 7 Tage | 605 | −0,041 | −25,0 | −1,0 | 0,67 | 0,02 |
| C Aktivierungslevel (Gen 3) | 3 | +1,14 | +3,4 | – | – | – |
| **D Rücksetzer-Limit 0,5 ATR, 3 Tage, sonst wie B** | **413** | **+0,060** | **+24,6** | **1,1** | **0,06** | **0,47** |

Momentum-Kontrolle auf A1-Fenstern: −0,016 R — die Report-Richtung ist
nicht besser als einfacher Trend.

Aufteilungen (Auswertung, keine Auswahl; >100 Zellen, t≈3 kann Zufall sein):
5 Sterne positiv in A1/B/D (D +0,20 R, n 84), 3–4 Sterne durchweg negativ;
Metalle positiv (B +0,38 R t 2,6; D +0,51 R t 2,7), FX-Kreuze negativ
(B −0,24 R t −3,7); D-Fließtext-Bias +0,44 R t 3,1; Hedges −0,18 R.

## Lesart

- Die Richtungs-Calls allein sind kein Edge (≈ Null brutto).
- Der Rücksetzer-Einstieg (Nutzerstil) dreht das Bild um ~+0,1 R/Trade bei
  gleichen Exits — einziger positiver Ansatz, aber noch kein Beleg (DSR 0,47).
- Kandidaten für den Forward-Test: (1) D als Grundregel, (2) nur 5 Sterne,
  (3) Edelmetalle, (4) FX-Kreuze meiden. Alle auf denselben Daten gefunden →
  zählen erst nach Forward-Bestätigung.
- Grenzen: 14 Monate, ein Regime; Stops/Ziele sind Standardregeln (Mentor
  nennt kaum Levels); Generation 3 (heutiges Format) nur ~80 Trades.

## Offene Punkte

- [ ] 31.01.2027: OOS (Forward-Reports 08.10.2026–31.01.2027) einmal öffnen,
  dafür die neuen Reports mit EXTRACTION.md v2 extrahieren.
- [ ] Agent soll die Kandidaten 1–4 vorwärts mitprotokollieren.
- [ ] Report 5305: drei Event-Ideen passen laut Prüfer nicht zum Report
  (laufen nicht im Richtungstest) — bei Gelegenheit nachsehen.
