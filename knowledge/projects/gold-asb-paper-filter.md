# Gold ASB: Filter aus Gold-Papers + Blindtest 2010–2015 (2026-10-18)

**Status: gerechnet 18.10.2026.** Nutzerauftrag nach der Mentor-PDF
([[gold-asb-is-only-neuanalyse]]): „Können wir aus den Papers noch eine Optimierung finden?“
Plan und Hypothesen vom Nutzer vorab bestätigt. Prozess: [[overfitting-sperre]].

## Aufbau

- Skript `scripts/research_gold_asb_paper_filters.py` (`--stage quality / select / blind`),
  Lock `gold_asb_paper_filters_20261018`, Ergebnisse `asian_range_breakout/results/paper_filters_*`.
- OOS/Tresor der IS-only-Version waren schon offen. Deshalb: Auswahl auf 11/2016–09/2026,
  **Blindtest 2010–2015** (nie für Gold ASB benutzt), Forward 10/2026–03/2027.
  Dafür bekam `research_lock.py` die Stufe `blind` (`register_blind`, vor dem Freeze, einmal öffnen; Tests grün).
- Basis = eingefrorene IS-only-Konfiguration. 9 Varianten aus 4 Hypothesen, vorab fest:
  H1 Range-Kompression (Crabel NR), H2 NFP-Tage (Sobti 2024/25), H3 Exit vor dem PM-Fix
  (Caminschi & Heaney 2014), H4 Asien-Drift (Wei 2026, Jin et al. 2018).
  FOMC vor dem Lauf gestrichen: Entscheidung 14:00 NY liegt nach dem Exit 11:00.
- Auswahlregel vorab: Ø R in ≥ 2 von 3 Teilzeiträumen besser, ≥ 60 % der Trades, höchster
  t-Wert und besser als die Basis; sonst kein Filter.

## Datenfallen (vor dem Lauf festgelegt)

- Dukascopy hat XAG/USD erst ab 25.07.2014. Ersatz im Blindtest durchgehend: COMEX-Silber
  `SI=F` (yfinance), auf den Gold-Tageskalender vorgetragen. Probe 2016–26: 5-Tage-Richtung
  92,9 % gleich (98,1 % bei Bewegung > 1 %), Basis damit 305 statt 325 Trades und
  Ø +0,229 statt +0,271 R. **Messlatte im Blindtest daher +0,229.**
- Gold M5 2009–2015 sauber (volle Asien-Fenster, Range-Breite wie 2016+). 2010/11 längere
  Freitags-/Sonntagssitzungen, ohne Wirkung. Kein Jahr ausgeschlossen.

## Ergebnis Auswahl (2016–2026, TTP-Kosten)

| Variante | n | Ø R | t | zulässig |
|---|---|---|---|---|
| Basis | 325 | +0,271 | 5,01 | – |
| H1 Range ≤ 1,0× Median | 162 | **+0,385** | 4,19 | nein (< 60 % Trades) |
| H1 Range ≤ 1,2× | 220 | +0,305 | 4,07 | ja, aber t < Basis |
| H4 Drift in Richtung | 284 | +0,280 | 4,94 | ja, aber t < Basis |
| H2 / H3 | 323–325 | +0,23…+0,26 | ≤ 5,0 | nein |

**Kein Paper-Filter schlägt die Basis.** Eingefroren: Basis ohne Filter.
- H2 hat keinen Hebel: Die Basis handelt in 10 Jahren nur an 2 NFP-Tagen (erste Freitage
  kommen fast nie durch die Filter).
- H3: früher aussteigen kostet Edge, die Gewinner laufen über den Fix hinaus.
- H1 ist der interessanteste Befund: enge Ranges bringen +0,39 statt +0,27 R je Trade, aber
  halb so viele Trades. Nach der Regel verworfen. Nicht nachträglich umdeuten; als neue Idee
  nur mit eigenem Lock und Forward-Daten.

## Ergebnis Blindtest 2010–2015 (einmal geöffnet)

| | n | Ø R | t | PF | Σ R | MaxDD | Jahre + |
|---|---|---|---|---|---|---|---|
| Basis (Ersatz-Silber) | 143 | **+0,239** | 2,85 | 1,96 | +34,1 | −5,7 | 5/6 |

Jahre: 2010 +4,5 · 2011 +11,3 · 2012 +6,4 · 2013 +8,6 · 2014 +3,5 · 2015 −0,2 R.
**Der Edge der Basis hält auf sechs nie benutzten Jahren**, auf Höhe der Messlatte
(+0,229). Das ist der bisher stärkste Beleg für Gold ASB: Auswahl 2016–22, OOS, Tresor
und jetzt ein Zeitraum davor zeigen alle ein positives Vorzeichen. Der Tresor (+0,04)
bleibt die Schwachstelle; der Blindtest spricht eher für eine schwache Phase als für einen Bruch.

## Folgen

- Keine Bot-Änderung. Forward-Fenster 10/2026–03/2027 ist im Lock als „OOS“ registriert.
- Mechanismus-Kriterium der Mentor-PDF bleibt gelb (Paper-Filter brachten keinen Beleg).
- Offene Idee: H1 (Range-Kompression) als eigene Forward-Hypothese.
