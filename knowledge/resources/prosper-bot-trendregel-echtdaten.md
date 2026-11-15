# Resource: Prosper-AI-„Grok Trading Team“ – Trendregel auf echten Kursen

Am 2026-11-12 getestet (Nutzerauftrag: „Kannst du die Logik des Bots auf echten Daten testen?“).
Das Lernprojekt (Prosper-AI-Kurs, `C:\Users\andre\prosper-ai-grok-trading-team`, nur Simulation)
handelt auf **erfundenen** Kursen. Deren Generator (`app/market.py`) hält die Richtung zu 90 % von
Tick zu Tick bei, baut also Trends ein. Dort *muss* eine Trendregel gewinnen. Verwandte Befunde:
Memory „Agenten-Team-Vorlagen messen keinen Edge“, [[tradingagents-tauric]].

**Ergebnis: kein Edge. Verworfen. Der Tresor bleibt zu.** Auf D1 sieht die Regel positiv aus,
aber nur weil sie in steigenden Märkten long ist. Zufällige Long-Einstiege mit gleicher
Haltedauer sind im OOS besser. Als Bot-Konto 1:1 schaltet sich der Bot 2018 dauerhaft selbst ab.

## Regel (1:1 aus dem Code, Abgleich 320/320 Scores identisch)

- Score = Momentum über 20 Kerzen / max(4 × Vola20, 0,5). Bei SMA5 < SMA20 auf ≤ 0 gekappt,
  begrenzt auf ±1.
- Kauf (nur long) bei Score ≥ 0,45. Verkauf bei Score ≤ −0,45.
- Stop −5 % / Ziel +10 %, **nur auf dem Schlusskurs geprüft**.
- Konto: 5 Positionen, 15 % je Position, 30 % Krypto. Score < 0,55 wartet auf einen Menschen.
  −3 % am Tag = Pause, −10 % vom Hoch = Sperre.
- Abweichung im Test: Füllung zum nächsten Open (kein Vorgriff).
- Variante „atr“: Stop 2 × ATR14, Ziel 2 × Stopweite (Annahme von Claude, gezählt).

Daten: SP500, NASDAQ, US30, BTC, ETH, Gold, 7 FX-Majors; M15 / H1 / D1. NZDUSD fehlt auf M15,
ETH-M15 erst ab 2019. Kosten Round-Trip: FX 1,5 / Index 2 / Gold 3 / Krypto 10 bps.
Lock `prosper_bot_realdata`: IS 09/2017–2022, OOS 2023–02/2026, Tresor 03–08/2026 (zu),
6 Versuche. Code: `prosper_bot_realdata/` (`data.py`, `backtest.py`, Ergebnisse in `results/`).

## Zahlen (gepoolt über alle Märkte, Ø R netto je Trade)

| TF | Stop | IS Ø R (t) | OOS Ø R (t) | Zufalls-Long OOS | DSR OOS |
|---|---|---|---|---|---|
| D1 | fix 5 % | +0,32 (4,6) | +0,17 (2,2) | **+0,25** | 0,81 |
| D1 | ATR | +0,22 (3,3) | +0,23 (2,8) | **+0,33** | 0,93 |
| H1 | fix 5 % | +0,02 (3,8) | +0,01 (1,6) | +0,01 | 0,62 |
| H1 | ATR | +0,02 (1,1) | +0,02 (0,9) | +0,02 | 0,33 |
| M15 | fix 5 % | −0,01 (−3,3) | −0,00 (−0,6) | −0,00 | 0,03 |
| M15 | ATR | −0,08 (−8,0) | −0,08 (−6,8) | −0,07 | 0,00 |

- **D1 erfüllt das vorab gesetzte Kriterium formal** (t > 2 in IS und OOS), aber die
  Zufallskontrolle (gleiche Anzahl Long-Trades, gleiche Haltedauer, gleiche Kosten) ist im OOS
  besser. Das Plus kommt aus Krypto/Indizes/Gold-Hausse, nicht aus dem Timing. Je Markt liegt die
  Regel im OOS meist im 10.–60. Perzentil der Zufallseinstiege. FX D1 um null.
- Nur im IS schlug die Regel bei Krypto (BTC/ETH D1+H1) den Zufall deutlich (Perzentil 0,85–0,99).
  Im OOS nicht mehr. Der Trend-Vorteil bei Krypto stammt aus 2017–2021.
- H1 mit der Bot-eigenen Gebühr (0,1 % je Seite) ist negativ (−0,01 bis −0,47 R).
- 2026 (Jan–Feb) ist auf D1 deutlich negativ (−0,39 / −0,54 R).

## Bot-Konto 1:1

Alle sechs Läufe (3 TF × 2 Stops) treffen 2018 die 10-%-Drawdown-Sperre (M15 03.02.2018,
H1 Juli/Sept. 2018, D1 10.01.2019). Der Höchststand wird nur beim Konto-Reset zurückgesetzt, also
**handelt der Bot danach nie wieder**: OOS-Rendite 0,0 %, alle Kaufsignale „REJECTED“. Ohne
Dauersperre bleibt es gleich, weil das Konto ohne Trades nie wieder unter 10 % Abstand kommt.
Bis zur Sperre: M15 −0,8 / −5,8 %, H1 +24,6 / +40,6 % (Krypto-Hausse 2017), D1 +2,5 / +3,6 %.
Dazu prüft der Bot Stop und Ziel nur auf dem Schlusskurs: BTC 16.01.2021 Ausstieg bei −16 %
statt −5 % (−3,2 R). Vgl. Memory „Engine-SL auf Kerzenschluss vs. Broker intrabar“.

## Vier-Fragen-Check

1. **Warum verdient es Geld?** Gar nicht über das Timing. Auf D1 ist es Long-Beta in steigenden
   Märkten, das Kaufen und Halten bzw. Zufallseinstiege genauso liefern.
2. **Wo verliert es am meisten? (IS)** M15 und FX: Kosten fressen den Durchschnitt, Ø R brutto
   ≈ 0. Auf D1 in 2018 und 2022 (Bärenjahre, Krypto-Crash).
3. **Was ist dort anders?** Keine Drift nach oben. Ohne steigenden Markt bleibt nur das Rauschen
   und die Kosten.
4. **Welche eine Regel könnte helfen?** Keine, die nicht bloß ein Marktfilter wäre (z. B. „nur
   über SMA200“). Das ist Faber-Trend, im Repo schon getestet und bekannt. Nicht weiter verfolgt.

## Fazit

Das Prosper-Projekt taugt als Architektur-Anschauung (Strategie schlägt vor, deterministischer
Risk Manager entscheidet, Mensch gibt frei). Als Handelsregel trägt es nichts. Die
Simulationsgewinne im Dashboard entstehen durch den Trend im Kursgenerator.
