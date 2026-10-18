# Gold ASB: nur auf IS neu optimiert, dann OOS und Tresor (2026-10-15)

**Status: gerechnet 15.10.2026. PDF vorerst verworfen (Nutzer 16.10.).**
Nutzerauftrag: Gold ASB „nochmal nach unserem Standardprozess für die
Gruppenarbeit“ analysieren, genauso wie ORB am 05.10.
([[orb-order-storno-und-haltedauer]], PDF `orb_profitabilitaets_kriterien_20261005.pdf`).
Prozess: [[overfitting-sperre]]. Vorgeschichte: [[gold-asb-kostenvalidierung]]
(Live-Config am 01.10. auf allen Daten gewählt), [[live-strategien-tresor-check]].

## Aufbau

- Skript `scripts/research_gold_asb_is_only_reopt.py` (`--stage grid` / `--stage evaluate`),
  Lock `gold_asb_is_reopt_20261015`, Ergebnisse `asian_range_breakout/results/is_reopt_*`.
- Split wie ORB (Nutzerentscheid): IS 2016–2022, OOS 01/2023–09/2025,
  Tresor 10/2025–09/2026. Wegen der SMA200-Vorlaufzeit startet IS faktisch am 02.11.2016.
- M5-Ausführung mit ruhender OCO-Stop-Order ab 01:00 NY (Simulation aus
  `research_gold_asb_optimization.py`), Kosten TTP 2,08 bps Round-Trip (teuerster Broker).
- Suchraum mit 9 Punkten, also allen Live-Stellschrauben: Stop 1,0/1,5/2,0x Range,
  Storno 02:00/02:30/03:00/04:00, Exit 10/11/12 Uhr NY, ADX aus/15/20/25,
  Trend-SMA aus/100/200, Silber aus/3/5/10 Tage, Liquidität aus/Quantil 0,5/⅔/0,8,
  Richtung beide/long/short. Das ergibt **20.736 Versuche**, alle gezählt.
- Die Auswahlregel war vorab festgelegt (wie ORB): ≥100 IS-Trades, PF > 1,3, beide IS-Hälften
  positiv. Gewählt wurde nach dem t-Wert, geglättet über die Stop- und Storno-Nachbarn.

## IS-Gewinner (eingefroren)

Stop **2,0x** Range, Storno **02:30**, Exit 11:00, ADX ≥ 15, **kein Trendfilter**,
Silber 5 Tage, Liquiditätsquantil **0,5**, beide Richtungen.

Das IS-Plateau ist breit: Die Top 12 liegen alle bei t 4,2–4,4. Fast alle nutzen Silber
plus Liquiditätsquantil 0,5, keine braucht den SMA-Trendfilter. Der Stop 2,0 liegt am
Rand des Gitters, und Stop 1,0 bzw. 1,5 liegen gleichauf. Die Stopweite ist also ein
Plateau und kein Optimum.

## Ergebnis (TTP-Kosten, Ø R je Trade)

| | IS 2016–22 | OOS 2023–09/25 | Tresor 10/25–09/26 |
|---|---|---|---|
| **IS-only** n / PF / Ø R / Σ R | 211 / 2,32 / +0,33 / +69,9 | 96 / 1,71 / +0,18 / +17,6 | 18 / 1,19 / **+0,04** / +0,8 |
| Live-Config (auf allen Daten gewählt) | 174 / 1,89 / +0,32 / +55,4 | 78 / 1,87 / +0,25 / +19,8 | 29 / 1,94 / +0,17 / +4,8 |

- **Deflated Sharpe 0,24**, Ziel ist > 0,95. Gegen 20.736 Versuche ist der Edge
  statistisch nicht belegt (zum Vergleich: ORB ~0).
- **Nicht durchgefallen, aber ausgelaufen:** Ø R fällt stufenweise von +0,33 über +0,18 auf
  +0,04. Alle 11 Jahre sind positiv, 2026 nur noch knapp (+1,2 R). Anders als bei ORB
  (Tresor PF 0,52) bricht hier nichts, der Edge verdünnt sich.
- Im Tresor gibt es nur 18 Trades statt sonst ~35 pro Jahr: Das Quantil 0,5 filtert im
  volatilen Gold-Jahr 2025/26 mehr Tage heraus. Die Short-Seite im Tresor (6 Trades,
  −1,3 R) ist bei dieser Anzahl Rauschen.
- Die Live-Config sieht im Tresor besser aus (+0,17 R). Sie wurde aber auf Daten
  einschließlich OOS und Tresor gewählt und ist deshalb kein Beleg. Der Trendfilter
  macht sie in OOS fast reinrassig long (74 von 78 Trades).

## Folgen

- Keine Bot-Änderung. Gold ASB bleibt im Frühwarnsystem ([[edge-fruehwarnung-kill-switch]])
  auf „beobachten“. Die Abschwächung deckt sich mit dem Tresor-Check (+0,33 → +0,18).
- Für die Gruppe: Der Prozess zeigt beides, einen Edge, der den Holdout knapp
  übersteht, und dass 20k Versuche ohne Deflated Sharpe > 0,95 keinen Beweis ergeben.
- PDF (6 Seiten, Layout wie ORB) vorerst verworfen (Nutzer 16.10.). Bei Bedarf
  liegen alle Daten dafür in `asian_range_breakout/results/is_reopt_*`.
