# Edge Card: Quantum Valkyrie (gekaufter Gold-EA)

Stand 2026-10-30. Abweichung vom Workflow in [[edge-card-workflow]]: Quelle ist ein gekaufter EA, kein händischer Handel. Die Regeln sind aus drei MT5-Berichten hergeleitet und nicht vom Anbieter bestätigt. Herleitung: [[quantum-valkyrie-nachbau]].

**Urteil: Der Nachbau hat keinen handelbaren Edge. Der EA selbst bleibt auf echten Ticks im Plus, aber sein Auslöser ist nicht nachbaubar.**

## 01 Idee
Nach einem kräftigen M15-Impuls eine Stop-Order auf das letzte Swing-Extrem legen und den Ausbruch mit einem sehr engen Trailing-Stopp absichern. Viele kleine Gewinne (rund 3,70 $) stehen gegen seltene volle Stops (mindestens 15 $).

## 02 Regel
| Element | Regel | Treffer gegen MT5 |
|---|---|---|
| Zeitpunkt | Zur Eröffnung einer M15-Kerze | 100 % |
| Auslöser | Körper > 0 und 4-Kerzen-Bewegung > 1 ATR, je Pivot eine Order | **36 % der Orders, feuert 5× zu oft** |
| Level | max(jüngstes Pivot 12/6, Ask + 0,30 $); Short gespiegelt | 80 % auf den Cent |
| SL | clamp(3,5 × ATR(M15, 100), 15, 60 $) | Streuung 4 % |
| TP | 50 $; selten 8/12/22 $ | 91 % |
| Trailing bei TP 50 | Start bei 0,22 × SL, Abstand 0,50 $, Schritt > 0,10 $ | zusammen mit den Sonder-TPs 94–95 % der Ausstiege (±1 Min.) |
| Trailing bei TP 12 / 22 | Start bei 8 $ / 20 $, Abstand 0,80 $ | 88 % / 78 % der Ausstiegskurse |
| Trailing bei TP 8 | Start ~5,5 $, Abstand 0,80 $ | nur 11 Fälle, unsicher |
| Ablauf | 29,75 h | |
| Filter | Spread ≤ 0,30 $; NFP und Feiertage laut Eingaben, nicht geprüft | |
| Lot | 0,01 je 1.000 $, nach Verlust ×2 (eine Stufe) | |

Der Replay der echten Orders durch die Engine korreliert zu 0,996–0,9996 mit der MT5-Kapitalkurve (57,6 gegen 56,8 R und 101,5 gegen 108,5 R).

**Der Auslöser bleibt offen.** 111 Einzelregeln und deren Paare erreichen höchstens 7 % Präzision. Ein Klassifikator erkennt das Umfeld (Test-AUC 0,94), aber nicht die Kerze: bei 50 % Recall 11–14 % Präzision.

## 03 Mechanismus
Kein belegter Mechanismus. Die Asymmetrie aus enger Absicherung erzeugt die hohe Trefferquote, aber noch keinen Edge. Im OHLC-Modell überschätzt sie den Gewinn, weil vier Ticks je Minute den Verlauf innerhalb der Minute glätten.

## 04 Gegenprobe
Zufällige Kerze statt Auslöser, gleiche Pivots und gleiche Orderzahl. Bei einem echten Auslöser-Edge müsste die Kontrolle deutlich schlechter sein. Das ist sie nur im Blindtest und schwächer in IS und OOS, im Tresor nicht.

## 05 Test
Sperre `valkyrie_klon_20261030`, 1 gezählte Variante (keine Auswahl auf Gewinn). Kriterium vor dem ersten Lauf: Blindtest, OOS und Tresor je Ø R > 0 und t ≥ 2 nach 0,30 $ Kosten. Skript: `scripts/research_valkyrie.py`. Alle Stufen laufen auf dem OHLC-Modell.

| Stufe | Klon brutto Ø R (t) | Klon nach 0,30 $ Ø R (t) | Kontrolle brutto Ø R (t) | Kriterium |
|---|---|---|---|---|
| IS 2020–23 | +0,030 (4,1) | +0,011 (1,4) | +0,022 (2,9) | zählt nicht |
| **Blindtest 2018–01/2020** | +0,020 (2,0) | **−0,000 (−0,0)** | +0,003 (0,3) | **nicht bestanden** |
| OOS 01/2024–10/2025 | +0,059 (5,4) | +0,041 (3,7) | +0,044 (3,9) | bestanden |
| Tresor 10/2025–10/2026 | +0,068 (4,3) | +0,059 (3,7) | +0,070 (4,4) | bestanden |

**Gesamt: nicht bestanden.**

Nachträgliche Einordnung, keine Auswahl:

| Tresor auf echten Ticks | Ø R brutto (t) | Ø R nach 0,30 $ (t) |
|---|---|---|
| Klon | −0,001 (−0,0) | −0,010 (−0,7) |
| Kontrolle | +0,010 (0,7) | +0,001 (0,1) |

Das Tresor-Plus des Klons entsteht also fast vollständig im Tick-Modell.

**Der EA selbst, echte Orders auf echten Ticks** (05/2025–10/2026, 326 Trades, keine Kosten): Ø +0,067 R, t 2,74, PF 1,47; im OHLC-Modell +0,104 R. Mit 0,30 $ Kosten je Trade (gerechnet mit 15 $ SL) +0,047 R, t 1,92. Das sind 17 Monate, und der Anbieter kann seine Einstellungen auf diese Zeit angepasst haben.

## Vier-Fragen-Check
1. **Warum verdient es Geld?** Im Modell vor allem durch das enge Trailing auf vier Ticks je Minute; beim EA zusätzlich durch einen Auslöser, den wir nicht kennen.
2. **Wo verliert es am meisten?** Bei den vollen Stops, die rund 15 % der Trades treffen.
3. **Was ist dort anders?** Auf IS-Daten nicht untersucht, weil der Klon schon am Kriterium scheitert.
4. **Welche eine Regel könnte helfen?** Keine getestet. Eine weitere Regel würde das Modellproblem nicht lösen.
