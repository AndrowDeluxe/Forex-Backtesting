# Gold Confirmation Score: Nachbau + Backtest (2026-11-14)

**Status: gerechnet 14.11.2026. Ergebnis: Score als Signal kein Edge. Einziger Fund: Makro-Block als Veto auf
CTNL-Reversal (IS und OOS, p ≈ 0,0004). Tresor am 15.11. geöffnet: Richtung bestätigt (+0,31 → +0,48 R),
aber nur 5 gesperrte Trades (p 0,06). Nichts live übernommen.**
Nutzerauftrag: PDF-Framework einer Bekannten ([[gold-confirmation-framework-pdf]]) mit freien
Daten nachbauen, Bausteine einzeln prüfen, Score als Edge mit Entry-Varianten testen und mit
unseren Filtern kombinieren. Plan vorab freigegeben. Nutzerentscheide: Proxys + umgewichten,
Score als Signal **und** als Filter, Kombination mit Zins/Trend/COT/ASB-Filtern, Split IS 2010–19.

## Aufbau

- Code: `fusion_lab/gold_confirm/` (`data.py` 7 freie Quellen, `components.py` 17 Bausteine,
  `score.py` Blöcke + Score + `GoldScoreFilter`). Daten: `python -m fusion_lab.gold_confirm.data`.
- Test: `scripts/research_gold_confirm.py --stage data|single|edge|filter|combo`, Lock
  `gold_confirm_v1`: IS 2010–2019, OOS bis 10.05.2026 (frei), Tresor bis 10.11.2026 (zu).
  Ergebnisse: `fusion_lab/data/gold_confirm/results/stage*.csv`.
- Jeder Baustein nutzt nur, was am Tagesende veröffentlicht war: CFTC ab Freitag, GLD/FRED +1 Tag,
  IMF +2 Monate. Normierung über ein gleitendes 3-Jahres-Perzentil. Gehandelt wird frühestens am Folgetag.
- Kosten: 0,30 $ Round-Trip, Haltekosten pauschal 3 % p. a. (Annahme).

## Stufe 0: Was die Bausteine messen

- **Doppelzählung:** Viele Bausteine messen vor allem das 20-Tage-Momentum von Gold (Spearman):

  | Baustein | ρ zum 20-T-Momentum |
  |---|---|
  | rel. Stärke | 0,87 |
  | GDX | 0,52 |
  | Managed Money | 0,51 |
  | Realzins | 0,46 |
  | Kupfer | 0,43 |
  | Absorption | 0,40 |
  | ETF-Flows, OI | 0,38 |

  Unabhängig davon sind GVZ-Proxy, Other Reportables, Zentralbanken, Zins-Schock-Reaktion und Inflation.
- **Score zur Mitte gedrückt:** ≥ 65 an 12 % der Tage, ≤ 35 an 6 %, ≥ 80 an 0,4 %. Die
  „Extreme Confluence“ des PDFs kommt praktisch nie vor.

## Stufe 1: Einzelbausteine → Gold-Forward-Rendite (IC, IS)

Kein Baustein erreicht im IS |t| ≥ 2. Knapp darunter liegen:

| Baustein | Horizont | IS-t | OOS-t |
|---|---|---|---|
| Physical-Block | 1 T | 2,2 | −1,7 |
| China-Prämie | 1 T | 1,9 | −2,1 |
| EPU-Unsicherheit | 5 T | 1,75 | 0,05 |

Gekippt bzw. verpufft sind also alle drei. Der Score selbst hat IC +0,06 (IS, t 1,4) und 0,00 im OOS.
Gleich stabil in beiden Zeiträumen sind nur der Realzins (t ≈ 0,6) und der USD (t ≈ 0,6–0,8), beide klein.
Übertragbarkeit auf Silber (Managed Money, Other Reportables): ebenfalls kein Signal (|t| ≤ 2,0,
Vorzeichen uneinheitlich).

## Stufe 2: Score als eigener Edge (32 Varianten)

Varianten: Schwelle 65/35 und 80/20 × täglich/wöchentlich × Entry E1 Market, E2 Limit am
0,5-ATR-Rücksetzer, E3 Asia-Range-Break auf H1 (HTF-Bias + LTF-Trigger wie im PDF),
E4 Schwellen-Kreuzung × Exit 2R-Ziel oder nur Score/Zeit.

- Schwelle 80 liefert 1–5 Trades in 10 Jahren und ist damit nicht testbar.
- Bester IS-Wert: **65 täglich, E2 Limit, 2R:** IS n 76, +0,335 R, t 2,08. OOS n 45, +0,025 R.
- **Short verliert in IS und OOS**, bei allen Entries. Long allein: IS +0,51 R (n 57), OOS +0,36 R (n 23).
- **Entscheidende Kontrolle:** „Immer long“ mit derselben Limit-Mechanik bringt IS +0,22 und
  **OOS +0,43 R** (n 126). Zufällige Long-Tage: OOS-Mittel +0,24, 95. Perzentil +0,43. Im IS wählt
  der Score bessere Tage aus als der Zufall, im OOS nicht. Der „Edge“ ist Golds Drift plus Limit-Preis.
- Die Entry-Varianten bestätigen [[htf-daily-trade-edge-card]] (C2-Edge liegt im Limit-Preis): Limit (E2) schlägt Market (E1),
  den LTF-Trigger (E3) und die Kreuzung (E4).

## Stufe 3: Score/Blöcke als Veto auf bestehende Gold-Edges

| Edge | Variante | IS n / Ø R | OOS n / Ø R |
|---|---|---|---|
| Gold ASB | Basis | 274 / +0,285 | 187 / +0,236 |
| Gold ASB | Score-Veto (nicht gegen 65/35) | 258 / +0,283 | 174 / +0,241 |
| Gold ASB | MACRO „nur mit“ | 54 / +0,455 | 41 / +0,274 |
| Gold ASB | PHYSICAL „nur mit“ | 108 / +0,429 | 39 / +0,165 |
| C2-Gold | Basis | 16 / +0,03 | 13 / +0,15 |
| CTNL-Reversal (Live-Konfig., TP 5R, Lag 1) | Basis | 908 / +0,004 | 490 / +0,212 |
| CTNL-Reversal | Score-Veto | 876 / +0,030 | 476 / +0,241 |
| CTNL-Reversal | **MACRO-Veto** (nicht gegen 65/35) | **799 / +0,099** | **421 / +0,370** |

- **Das Score-Veto ist auf ASB wirkungslos:** Es sperrt nur 16 bzw. 13 Trades.
- **MACRO „nur mit“** ist in beiden Zeiträumen besser, behält aber nur 20 % der Trades und hat den
  schlechteren t-Wert (3,1/2,2 statt 4,7/3,4). Nach der ASB-Regel (≥ 60 % der Trades) unzulässig.
- **C2-Gold** hat zu wenige Trades für eine Aussage.
- **CTNL + MACRO-Veto, einziger echter Fund:** Die gesperrten Trades verlieren IS Ø −0,69 R (n 109) und
  OOS Ø −0,75 R (n 69).
  - Zufälliges Wegnehmen: p 0,0004 / 0,0002.
  - Wirkt auf beiden Seiten. Long + Veto bringt OOS +0,75 statt +0,55 R, ist also kein Abbild von
    „CTNL nur long“.
  - Gesperrte Trades negativ in 12 von 14 Jahren.
  - Treiber sind Realzins und USD (Einzel-Veto Realzins OOS behalten +0,37). Inflation/EPU allein
    sperren eher Gewinner.
  - Mechanismus: Ein Reversal gegen eine Gold-Bewegung, die von Realzins und Dollar getragen wird, scheitert.
  - Passt zu [[htf-daily-trade-edge-card]] (Zinsfilter wirkt auf Einstiege), erweitert den
    Makro-Filter-Test vom 12.11., der CTNL nicht enthielt.

## Stufe 4: Kombination mit bisherigen Filtern (45 Zellen)

Geprüft wurden Zinskurven-Regime, SMA200, Ribbon, Faber, Weekly EMA 9/21, COT-Fluss (4 Berichte)
und Silber 5 T (ASB-Filter):
- **Score-Long + Weekly-EMA 9/21:** IS +0,56 R (n 45), OOS +0,52 R (n 18). Die Kontrolle „immer long +
  Weekly-EMA“ bringt OOS +0,51 R über **98** Trades. Der Score fügt also nichts hinzu.
- **Zinskurve** hebt den Score-Edge im IS auf +0,60 R (t 3,1), im OOS auf +0,01. Typischer IS-Scheinsieger.
- **ASB + Trendfilter** (Faber, Weekly-EMA): IS ≈ +0,35, OOS ≈ +0,32–0,35 bei gut der Hälfte
  der Trades. Das ist ein ASB-Befund, kein Score-Befund, siehe Ideen-Inbox.

## Stufe 5: Robustheit, nur CTNL + MACRO-Veto

Score-Edge und ASB-Veto bestehen ihre Kontrolle nicht.

| Prüfung | Ergebnis |
|---|---|
| Jahresreihe Σ R | in 11 von 18 Jahren besser, in 3 schlechter (max. −6 R, 2025) |
| Bootstrap Ø R 5–95 % | IS −0,05…+0,26, OOS +0,16…+0,59 |
| Monte-Carlo-Max-DD OOS | Median −34,5 → −25,9 R, 5 %-Quantil −54 → −40 R |
| Deflated Sharpe | 0,43 (181 Varianten) |

Die DSR bewertet CTNL insgesamt, das 2010–19 bei ≈ 0 R liegt. Das Veto selbst ist signifikant.

## Tresor (geöffnet 15.11.2026, Nutzerentscheid)

Eingefroren: CTNL-Reversal live (tp_r 5,0, REV_KWARGS) + „kein Trade gegen MACRO-Block vom Vortag“
(≥ 65 kein Short, ≤ 35 kein Long). Tresor 11.05.–10.11.2026; Daten reichen bis 30.10., letzter
Trade 27.10. Ergebnis: `fusion_lab/data/gold_confirm/results/tresor_ctnl_macro_veto.csv`.

| | n | Ø R | Σ R | max DD R |
|---|---|---|---|---|
| CTNL Basis | 47 | +0,31 | +14,5 | −19,6 |
| mit Veto behalten | 42 | **+0,48** | +20,3 | −18,3 |
| gesperrt | 5 | **−1,16** | −5,8 | |

- Alle 5 gesperrten Trades waren Longs bei MACRO 15–30 (07.07., 10.07., 12.10.), alle Verluste.
- Zufällige Wegnahme von 5 Trades: p 0,06, wegen n = 5 nicht signifikant für sich allein.
- Im Tresor stand MACRO nie ≥ 65, das Veto konnte also nur Longs sperren. CTNL selbst war im
  Tresor fast nur short (38 von 47) und dort profitabel; die übrigen 4 Longs verloren auch.
- **Lesart:** Richtung und Größe passen zu IS und OOS (gesperrte Trades −0,69 / −0,75 / −1,16 R),
  der Tresor allein ist aber dünn. Bestanden im Sinne „nicht widerlegt“, kein eigenständiger Beweis.
  Nächster Schritt wäre ein Forward-/Paper-Gate, keine direkte Live-Änderung.

**Short-Seite (15.11. nachgerechnet):** gesperrte Shorts (MACRO ≥ 65) IS −1,02 R (n 32, p 0,005),
OOS −0,65 R (n 35, p 0,08), Tresor kein Fall. Negativ in 7 von 9 Jahren. Bausteine gespeichert:
[[gold-bausteine-fuer-andere-edges]].

## Vier-Fragen-Check

1. **Warum sollte es Geld verdienen?** Echte Kapitalflüsse sollen einen Gold-Move bestätigen. In
   den freien Daten laufen Flows aber zeitgleich mit dem Preis (Momentum), statt ihm vorauszugehen.
2. **Wo verliert es am meisten?** Auf der Short-Seite (IS −0,18…−0,24 R je Trade), weil Gold
   2010–26 strukturell steigt.
3. **Was ist dort anders?** Kurze Gegenbewegungen in einem langfristigen Aufwärtsmarkt. Der Score
   fällt dort, weil das Momentum fällt.
4. **Welche eine Regel könnte helfen?** „Nur long“ (gezählt). Hilft, schlägt aber „immer long“ nicht.

## Was wir von den Bausteinen für andere Edges nutzen können

| Baustein | Taugt als | Begründung |
|---|---|---|
| GLD-Bestand (ETF-Flow) | Kontext im Makro-Agent | täglich frei ab 2004, misst Anleger-Nachfrage; OOS-IC positiv (t 1,3–1,75), IS negativ, also kein Signal |
| China-Prämie (SGE) | Kontext | einzige frei verfügbare physische Reihe; IS positiv, OOS negativ |
| CFTC Managed Money / Other | nichts Neues | bestätigt [[makro-gates-evidenz]]: läuft mit dem Preis |
| Absorption (USD/Realzins-Residuum) | nichts | ρ 0,40 zum Momentum, IC ≈ 0 |
| Realzins, USD (20 T) | schwacher Kontext | einziges stabiles Vorzeichen in IS und OOS, aber t < 1 |
| Zentralbanken (IMF) | Regime-Kontext | nur gemeldete Käufe, keine Vorhersagekraft auf Tage/Wochen |
| **Makro-Block (Realzins + USD + Inflation + EPU)** | **Veto für Reversal-Einstiege (CTNL)** | einziger Fund, siehe Stufe 3/5 |
| `GoldScoreFilter` | Werkzeug | gleiche Schnittstelle wie die anderen Filter, sofort in Filter-Matrizen nutzbar |

Verwandte Befunde: [[makro-wirkketten-katalog]] (Makro-Filter-Test, Lock `macro_filter_v1`), [[makro-scorecard-v2]],
[[regimekarte-wachstum-inflation]], [[htf-daily-trade-edge-card]] (C2-Edge liegt im Limit-Preis).

## Stufe 6: Risikoskalierung nach MACRO (15.11., Nutzerauftrag)

Eigene Sperre `gold_confirm_v2_sizing` (6 gezählte Varianten), `--stage sizing`,
`results/stage6_sizing.csv`. Tresor ist hier **nicht unabhängig** (die Idee stammt aus dem
Tresor-Ergebnis). Kennzahl: Summe R / 95-%-Monte-Carlo-Drawdown.

| Variante | IS Σ R | IS Σ/DD95 | OOS Σ R | OOS Σ/DD95 | OOS DD95 |
|---|---|---|---|---|---|
| B Veto (Referenz) | +82 | 0,96 | +156 | 3,85 | −40 |
| C Veto + 2× mit Makro, beide Seiten | +91 | 0,78 | +195 | 3,50 | −56 |
| D Veto + 2× nur Longs mit Makro | +141 | 1,56 | +189 | 3,94 | −48 |
| E Veto + 2× nur Shorts mit Makro | +33 | 0,28 | +162 | 3,32 | −49 |
| F nur Trades mit Makro, beide | +9 | 0,17 | +40 | 1,40 | −28 |
| G nur Longs mit Makro | +59 (Ø +0,72 R) | 2,85 | +33 (Ø +0,49 R) | 1,75 | −19 |
| H 2× mit Makro ohne Veto | +16 | 0,11 | +144 | 2,06 | −70 |

- **Shorts mit bärischem Makro verdoppeln: verworfen.** IS verlieren diese Shorts −0,45 R je Trade
  (n 110); das +1,24 R im Tresor war ein guter Abschnitt, kein Muster.
- **D (Longs mit bullischem Makro 2×):** IS klar besser, OOS je Risikoeinheit kaum (+0,387 statt
  +0,370 R), Drawdown +18 %. Mehr Rendite gegen proportional mehr Drawdown, kaum Effizienzgewinn.
- **Nur mit Makro handeln:** pro Trade besser (Long-only), verliert aber den Großteil der Summe.
- Fazit: Veto behalten, nicht skalieren.

## Live-Einbau und Gegenprobe auf dem Live-Set (15.11., Nutzerentscheid)

Die Tests oben liefen auf dem **ungefilterten** CTNL-Set (1.505 Trades). Live laufen zusätzlich
Ribbon-Gate und Spike ≥ 0,75 ATR. Gegenprobe auf diesem Live-Set 2016–10/2026
(`scripts/research_ctnl_macro_live.py`, Ergebnis `results/ctnl_live_*.csv`):

- 257 Trades, davon 12 gesperrt — **alle Longs**, Ø −1,13 R, p 0,0035 (IS 2 Trades, OOS 10, Tresor 0).
- Shorts werden nie gesperrt: Das Ribbon lässt Shorts nur im Abwärtstrend zu, dort ist MACRO fast nie ≥ 65.
- Die Sperre wirkt live also viel seltener als im Rohset, weil das Ribbon viele Gegen-Makro-Trades
  schon aussortiert. Sie bleibt aber in die richtige Richtung signifikant.

Backtest 1 % Risiko je Trade, täglich verzinst, Start 99.650 $:

| | Basis (Ribbon+Spike) | mit Makro-Sperre |
|---|---|---|
| Trades (je Jahr) | 257 (23,0) | 245 (21,9) |
| Trefferquote | 39,7 % | 41,2 % |
| Ø R / Profit Factor | +0,96 / 2,30 | +1,06 / 2,48 |
| CAGR | 22,1 % | 23,6 % |
| Sharpe / Sortino | 1,17 / 3,46 | 1,24 / 3,83 |
| Max DD | −19,4 % | −19,4 % |
| MC-DD Median / 95 % | 18,9 % / 30,9 % | 17,3 % / 28,7 % |

Eingebaut als `gold_smc_htf_ltf/macro_gate.py` in alle drei Bridges, Daten über Task
`Forex-Gold-Makro-Gate-Refresh`.

### Nachtrag 15.11.: mit Kill-Switch und Swap

Kosten im Live-Set: 2,01 bps Round-Trip (TTP gemessen inkl. Spread, Slippage, Kommission; teuerster
der vier Broker), 15 Min. Einstiegsverzögerung, R-Detektor 0,50 R. **Neu:** Swap 1,5 bps je Nacht
(Mittwoch 3×, Annahme, nicht gemessen; Ø 0,08 R je Trade). **Neu:** Kill-Switch wie live seit 30.09.
(`_dd_gehandelt`: Cont + Rev Ribbon-konform, Rev mit Spike, 8 bps, 90 Tage, 100k mit 0,5 %/0,15 %,
−6,6 % / Aufhebung −3,3 %). Er greift 2016–10/26 einmal (2020, 6 Trades, Summe −0,6 R).

| 1 % Risiko, Swap 1,5 bps | Basis | + Kill-Switch | + Makro | **Kill-Switch + Makro (live)** |
|---|---|---|---|---|
| Trades | 257 | 251 | 245 | **239** |
| Ø R / PF | +0,88 / 2,15 | +0,90 / 2,19 | +0,98 / 2,32 | **+1,01 / 2,37** |
| CAGR | 19,9 % | 20,0 % | 21,5 % | **21,6 %** |
| Sharpe / Sortino | 1,09 / 3,08 | 1,10 / 3,13 | 1,17 / 3,45 | **1,18 / 3,51** |
| Max DD | −19,9 % | −19,9 % | −19,9 % | **−19,9 %** |
| MC-DD 95 % | 32,8 % | 31,9 % | 30,3 % | **29,7 %** |

Swap-Empfindlichkeit (live-Variante): 0 bps Sharpe 1,25 / CAGR 23,7 %; 3 bps Sharpe 1,10 / CAGR 19,6 %.
Falle beim Nachbau: der Kill-Switch auf ungefilterten Schattentrades (Stand vor 30.09.) wäre 2/3 der
Zeit aktiv gewesen (173 von 257 Trades gesperrt) — live misst er seit 30.09. nur den gehandelten Satz.
