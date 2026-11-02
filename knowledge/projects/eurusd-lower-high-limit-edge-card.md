# Project: EURUSD Lower-High-Limit (Edge Card, Arbeitsstand)

**Status**: Phase 0 von [[edge-card-workflow]], wartet auf Bestätigung durch den Nutzer. Noch kein Test,
kein Lock registriert. Ausgangspunkt ist ein händischer Trade vom 30.10.2026.

## Der Trade (Fakten)

Short EURUSD per M15-Limit: Entry 1,12028, Stop 1,12128 (10 Pips), TP 1,11702 (32,6 Pips, 3,26 R).
Preise aus den Chart-Labels, Zeiten Berlin (UTC+1), Kurse aus dem Lake (Dukascopy M5 Bid, M15 daraus gebildet).

- 02:15 Spike-Hoch 1,12148 (M15). Stop 1,12128 ist exakt das Hoch der Kerze davor (02:00), liegt also
  2 Pips UNTER dem Spike-Hoch.
- 04:00 Hoch 1,12028 = exakt der Entry. Von dort fällt der Kurs, 04:15 und 04:30 schließen unter den
  letzten M15-Swing-Tiefs.
- 07:45 Tief 1,11759, danach Rücklauf. 09:15 Hoch 1,12014 berührt das Level noch nicht.
- 11:00 erste Berührung (M5 1,12031), Höchstkurs 11:35 bei 1,12057: 2,9 Pips gegen die Position.
- Bis 13:29 höchstens +14,6 Pips (1,46 R). TP in der M5-Kerze ab 14:00, nach ECI (13:30) und deutschem
  VPI (14:00, Ist 2,8 %, Konsens 3,0 %). Tagestief 1,11362 um 15:05.

## Makro-Umfeld

- FOMC 28.10.: gehalten bei 3,75–4 %, 10:2, Cook und Hammack wollten erhöhen (Admiral Markets, Fed-Transkript
  nur als vorläufiges PDF). Passt zu „hawkish“.
- EURUSD reagierte nicht geradlinig: 28.10. 19:00 Open 1,11373, 21:00 Close 1,11526. Das Tief 1,11042 kam
  am 29.10. in der Stunde ab 14:00, danach über 100 Pips Rally bis zum Spike-Hoch. Der Entry lag rund
  40 h nach dem FOMC.

## Einordnung gegen vorhandene Befunde

- Nächste Verwandte im Plan: A1 CTNL („Einstieg im Retrace auf Höhe des ersten BOS“), A5, A8
  ([[persoenlicher-tradingplan-validierung]]). Getestet ist diese Limit-Variante auf EURUSD nicht.
- [[keylevel-edge-card-final]]: BOS-Bestätigung an sichtbaren Leveln 0/240, Level sind Magnet. Das betrifft
  andere Level und Stop-Einstiege, spricht aber dafür, den Sweep über $$$ nicht als Beleg zu nehmen.
- [[london-range-bos-retest-eurusd]]: Stop-Einstieg nach Retest auf EURUSD negativ; Breakeven schadet.
- Trade-Inventur 2025: Positionen unter 4 h PF 0,30, EURUSD ≈ 0. Dieser Trade lief rund 3 h.
- CLS-Limit-Entry: IS-Scheinsieger mit n = 12, im OOS zerfallen. Limits brauchen eine realistische
  Füllannahme (Durchstich statt Berührung).

## Häufigkeit des ersten Detektor-Entwurfs (ohne Ergebnis)

Entwurf (noch nicht bestätigt): M15-Swing-Hoch H0 (k = 2); tieferes Swing-Hoch H1 innerhalb 24 h;
Schluss unter dem letzten Swing-Tief vor H1 innerhalb 8 h; Rückkehr zu H1 innerhalb 24 h, ohne H0 zu brechen.

- Findet den Trade exakt (H0 02:15, H1 04:00, BOS 04:30, Touch 11:00).
- Zu breit: 21 Signale vom 20.–30.10.2026, davon 2 am 30.10.

**Offen und entscheidend:** Wann lag die Limit-Order im Markt? Bei Füllung an der ersten Berührung (11:00)
kam der Spike bis 1,12057 erst NACH dem Einstieg und kann keine Einstiegsbedingung sein. Die 2,9 Pips
Gegenlauf gelten nur unter dieser Annahme. Spätere Berührungen gab es um 11:40 und 12:05.
- Nur Short, 01/2016–03/2023: 4.546 Ereignisse (~627/Jahr). Mit Stop 5–20 Pips und Rücklauf ≥ 20 Pips
  1.170 (~161/Jahr), zusätzlich 07–12 UTC 428 (~59/Jahr). Gewinn und Verlust nicht ausgewertet.

Die Zählung nutzt nur die Zeit bis 03/2023. Ein Split ist noch nicht registriert ([[overfitting-sperre]]).
