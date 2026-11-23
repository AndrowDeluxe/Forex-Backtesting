# Project: EURUSD Lower-High-Limit (Edge Card, Arbeitsstand)

**Status**: Phase 0 am 02.11.2026 vom Nutzer bestätigt, Feld 01/02 in Arbeit (Fragenkatalog gestellt).
Noch kein Test, kein Lock registriert. Ausgangspunkt ist ein händischer Trade vom 30.10.2026.

## Nutzerangaben 02.11.

- Die Zusammenfassung aus Phase 0 stimmt. Der Edge liegt sehr nahe am CTNL-Edge (Plan A1,
  `gold_smc_htf_ltf/reversal_cascade.py`).
- Das Limit lag vor 11:00 im Markt. Folge: Spike über $$$ (bis 1,12057) und Reaktion kamen nach der Füllung,
  sie sind keine Einstiegsbedingung. Das „Lower High“ ist H1 (04:00) gegenüber H0 (02:15) und stand ab dem
  BOS um 04:30 fest. Gegenlauf 2,9 Pips gilt damit.
- Unterschied zu CTNL (Code): CTNL verlangt H4-Doppel-Sweep, H1-Doppel-BOS und auf M15 Sweep-and-Reject als
  Einstieg. Hier ein M15-Limit ohne Bestätigung.

## IS-Beispiele zur Beurteilung durch den Nutzer (ohne Ergebnis, UTC)

Zufallsstichprobe (seed 7) aus 230 Treffern 2019–2022 des Entwurfs mit Stop 5–20 Pips, Rücklauf ≥ 20 Pips,
Berührung 07–12 UTC. Nur IS, damit die Regelfindung den Tresor nicht berührt.

| H0 | H1 = Entry | BOS | Berührung |
|---|---|---|---|
| 26.08.2019 14:30 1,11219 | 26.08.2019 16:30 1,11155 | 17:00 | 27.08.2019 08:45 |
| 22.07.2020 13:30 1,16013 | 22.07.2020 14:45 1,15951 | 17:45 | 23.07.2020 07:00 |
| 11.09.2020 09:45 1,18741 | 11.09.2020 13:00 1,18574 | 14:45 | 14.09.2020 07:15 |
| 28.01.2021 19:30 1,21399 | 28.01.2021 22:15 1,21276 | 29.01. 00:15 | 29.01.2021 10:15 |
| 24.01.2022 00:45 1,13406 | 24.01.2022 04:30 1,13312 | 05:00 | 24.01.2022 08:30 |
| 18.03.2022 16:15 1,10722 | 18.03.2022 17:45 1,10640 | 18:00 | 21.03.2022 09:00 |
| 17.06.2022 02:45 1,05394 | 17.06.2022 04:15 1,05300 | 06:00 | 17.06.2022 07:30 |
| 09.12.2022 13:30 1,05663 | 09.12.2022 18:45 1,05557 | 20:45 | 12.12.2022 09:30 |

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
