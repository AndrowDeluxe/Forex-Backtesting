# Edelmetalle HTF: Score-Bausteine + Makro auf 4–26 Wochen

Stand 18.11.2026. Teil des Dachprojekts [[quant-diskretionaer-fusion]], Anlass: Rohstoff-Screener
[[aktien-analyse-und-bot]] mit ungeprüften Gewichten. Vorwissen: [[gold-confirmation-score]] (1–5 Tage kein Edge).
Plan am 18.11. am Handy freigegeben, umgesetzt am PC.

## Ergebnis in einem Satz

**Kein Merkmal trägt die Richtung von Gold, Silber oder Platin auf 4–26 Wochen stabil.** 0 von 285 Merkmal-Varianten
erfüllen die vorab registrierte Kandidaten-Regel. Keine Screener-Variante schlägt „immer long“, und die
Short-Seite verliert im OOS bei allen drei Metallen. Als Filter bringt der Bias auf den Live-Gold-Edges nichts Neues.

## Methode (Vorab-Registrierung `fusion_lab/metals_htf/spec.py`, Commit `56a49a99`)

- **Lock `metals_htf_v1`:** IS 2004–2017, OOS bis 10.05.2026 (frei), Tresor 11.05.–13.11.2026 (**zu**, nichts eingefroren).
  336 gezählte Varianten.
- **Wochen-Frame:** Freitagsschluss. Jede Quelle wird erst ab ihrer Veröffentlichung genutzt:
  - FRED ab dem nächsten Werktag
  - CFTC ab Dienstag + 3 Tage
  - GLD ab dem nächsten Werktag
  - IMF ab Monatsende + 2 Monate

  Lücken werden nicht über Wochen fortgeschrieben.
- **Normierung:** gleitendes Perzentil über 156 Wochen (mindestens 52), gedreht mit dem erwarteten Vorzeichen.
- **Stufe 1:** Spearman-IC je Merkmal × Lookback {4, 13, 26} × Metall × Horizont {4, 13, 26}, Newey-West-t.

  Ein Merkmal ist Kandidat nur, wenn alle drei Bedingungen gelten:
  - IS-t ≥ 2 mit dem erwarteten Vorzeichen
  - positiv in beiden IS-Teilzeiten 2004–10 und 2011–17
  - gleiches Vorzeichen bei mindestens 2 Metallen
- **Stufe 2:** Regime-Regel: oberes Drittel long, unteres short, sonst flat.
  - Kosten je Seite: Gold 5, Silber 10, Platin 15 bps (Nutzer 18.11.)
  - Kontrollen: „immer long“, Faber und Zufalls-Timing mit gleicher Exposure (1.000 Läufe)
- **Datenqualität:** Yahoo PL=F hat 2006–09 monatelange Lücken. Platin läuft deshalb erst ab 2010, sein IS ist
  effektiv 2011–17.

## Stufe 1: IC (`results/stage1_ic.csv`)

- **Stärkste positive IS-Werte, alle unter t 2:**

  | Merkmal | Metall, Horizont | IS-t | OOS-t |
  |---|---|---|---|
  | COT contra | Platin, 4 W | 1,87 | 2,11 |
  | rel. Stärke 26 W | Silber | 1,71 | – |
  | Gold/Silber-Ratio | Silber | 1,62 | 1,66 |

  Bei COT contra und dem Gold/Silber-Ratio gilt die Bedingung „mindestens 2 Metalle“ nicht (gsr hat nur Silber
  mit erwartet +).
- **Signifikant waren nur Gegenrichtungen:**
  - rel. Stärke und Trend bei Platin (IS-t −2,2 bis −3,0): Mean-Reversion in der Platin-Baisse 2011–17
  - Breakeven 13 W bei Gold (−2,2)
- **Makro kippt zwischen IS und OOS** (mittlerer t je Merkmal):

  | Merkmal | IS-t | OOS-t |
  |---|---|---|
  | Realzins-Abstand | −0,44 | +2,32 |
  | 2J-Rendite | +0,20 | +2,25 |
  | Realzins Δ | +0,06 | +1,46 |
  | Zentralbanken 12 M | +1,05 | −2,31 |

  Die klassischen Makro-Ketten wirken also nur 2018–26 und stimmen 2004–17 nicht. Das ist ein Regime, keine Regel
  (passt zu den Memory-Befunden „Makro-Filter hilft Edges nicht“ und „Regime → Richtung je Asset überangepasst“).
- **COT-Vorzeichen:** Weder „mit“ noch „contra“ ist signifikant. Contra liegt bei Platin und Silber leicht vorn,
  bei Gold im OOS hinten (−1,0 bis −2,0). Die Vermutung „COT läuft mit dem Preis“ aus `gold_confirm` (1–5 Tage)
  bestätigt sich auf Wochen **nicht**. COT-Gewicht 0 bleibt damit richtig.

## Stufen 2 + 3: Regime und Screener-Nachbau (`results/stage3_komposit.csv`)

Ohne Kandidaten gibt es keine Regime-Läufe und kein Komposit. Nachgebaut wurde der echte Screener-Score als
Wochenreihe, mit ≥ 65 long und ≤ 35 short.

| Variante | Gold IS / OOS | Silber IS / OOS | Platin IS / OOS |
|---|---|---|---|
| immer long | **0,44 / 0,95** | **0,22 / 0,56** | −0,31 / **0,27** |
| Screener 1.0 (COT contra 20) | 0,30 / 0,63 | −0,12 / 0,04 | −0,23 / 0,01 |
| Screener 1.1 (COT 0) | 0,04 / 0,75 | −0,19 / 0,07 | −0,42 / −0,23 |
| nur Trend | 0,03 / 0,63 | −0,20 / −0,34 | −0,33 / −0,52 |

Sharpe nach Kosten. Die Short-Seite ist im OOS bei allen Varianten und Metallen negativ (−0,19 bis −0,77).

## Stufe 4: Filter auf Live-Gold-Edges (`results/stage4_filter.csv`)

- **ASB:** Kein Veto ist signifikant (Zufalls-p ≥ 0,06). „Nur mit Screener 1.0“ ergibt im OOS +0,42 statt
  +0,27 R, p 0,056, im IS aber p 0,28.
- **C2:** zu wenige Trades (14 IS, 15 OOS).
- **CTNL (breite Liste, nach Live-Makro-Sperre):**
  - OOS: „kein Trade gegen den Bias“ behält +0,46 R und sperrt −0,30 R (p 0,000).
  - IS: umgekehrt (0,09 gegen 0,12).
  - Gegenprobe auf dem **Live-Set** (Ribbon + Spike): Dort sperrt dieselbe Regel nur 0–2 Trades. Der Ribbon-Filter
    hat die Gegen-Trend-Trades schon entfernt (Memory „Ribbon ist ein Trendexistenz-Filter“). Neu ist hier nichts.

## Stufe 5: Robustheit (`results/stage5_robust.csv`, `stage5_jahre.csv`)

Gold, IS + OOS 2004–05/2026:

| Variante | Sharpe | 90-%-KI | MaxDD |
|---|---|---|---|
| immer long | 0,62 | 0,30–0,96 | −57 |
| Screener 1.0 | 0,42 | 0,12–0,78 | −28 |
| Screener 1.1 | 0,29 | −0,04–0,64 | −56 |

- MaxDD in Log-Prozentpunkten.
- DSR (336 Versuche): immer long 0,49, Screener 1.0 0,18, Screener 1.1 0,06.
- Screener 1.0 halbiert den Drawdown, kostet aber Rendite und Sharpe.

## Vier-Fragen-Check (auf das, was am ehesten trug: Screener 1.0 auf Gold)

1. **Warum verdient es Geld?** Fast nur über den Long-Anteil in Golds Aufwärtsdrift. Das ist Beta, keine eigene Prämie.
2. **Wo verliert es am meisten?** Short-Phasen in Gold-Haussen und Long-Phasen nach Trendbrüchen (z. B. 2013).
3. **Was ist dort anders?** Die Trendbausteine reagieren auf Wochen zu spät, Rücksetzer in einer Hausse werden
   als Trendwende gelesen.
4. **Welche eine Regel könnte helfen?** Keine Shorts bei Edelmetallen (long/flat). Das wäre eine neue, gezählte
   Variante; geprüft ist sie nicht.

## Folgerungen

- Screener-Gewichte nicht „optimieren“: Es gibt nichts, worauf man optimieren könnte. Version 1.1 bleibt.
- **Vorschlag, noch zu entscheiden:** VERKAUFEN-Signale bei Edelmetallen im Screener nur als Warnung zeigen und
  nicht ins Ledger als Short schreiben.
- Makro (Realzins, 2J, Kurve) nur als Kontext für das aktuelle Regime nutzen, nicht als Regel. Ihr Vorzeichen ist
  zwischen 2004–17 und 2018–26 gekippt.
- Tresor nicht geöffnet, weil kein Kandidat existiert, den man einfrieren könnte.

Code: `fusion_lab/metals_htf/` (spec, data, features, backtest), `scripts/research_metals_htf.py`,
Tests `tests/test_metals_htf.py`.
