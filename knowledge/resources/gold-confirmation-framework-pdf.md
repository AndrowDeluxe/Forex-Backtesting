# Gold Confirmation Framework (PDF, 14.11.2026)

**Quelle:** „XAU/USD – Institutionelles Confirmation Framework“, 5 Seiten, von einer Bekannten des
Nutzers („interne Research-Arbeitsgrundlage“). Geteilt am 14.11.2026. Nachbau und Test:
[[gold-confirmation-score]].

## Kernpunkte des Originals

1. **Vier Blöcke, gewichtet:**

   | Block | Gewicht | Inhalt |
   |---|---|---|
   | FLOW | 40 % | COMEX-OI/Volumen, Optionen, ETF-Flows, CFTC |
   | PHYSICAL | 25 % | China-/Indien-Prämie, Deliveries/Lager, Zentralbanken |
   | PRICE RESPONSE | 20 % | Absorption, relative Stärke, News-Reaktion |
   | MACRO | 15 % | Realzins, USD, Inflation, Liquidität, Geopolitik |

2. **Kernidee:** Makro erklärt, *warum* Gold laufen könnte. Flows zeigen, *ob echtes Kapital*
   kommt. Die Preisreaktion zeigt, *ob der Markt die Story annimmt*. Erst die Kombination ergibt
   hohe Conviction.
3. **Top-10-Bestätigungen:**
   - S+: Preisreaktion/Absorption; COMEX Preis + OI + Volumen
   - S: Optionen (Skew, Strike-OI, IV-Kurve); ETF-Flows; CFTC inkl. Gegenseite; Shanghai-/India-Prämie; COMEX Deliveries/Lager
   - A+: Zentralbanken (Regime, kein Intraday-Signal); Futures-Basis
   - A: GDX/Silber/Kupfer als Querbestätigung, kein Primärsignal
4. **Lesart Preis × OI:**

   | Preis | OI | Lesart |
   |---|---|---|
   | ↑ | ↑ | neue Longs |
   | ↓ | ↑ | neue Shorts |
   | ↑ | ↓ | Short-Covering, schwächere Rally |
   | ↓ | ↓ | Long-Liquidation, Korrektur statt Trendwende |

5. **Absorption:** Gold bekommt bärische Inputs (USD rauf, Realzins rauf), fällt aber kaum und
   holt sich das Niveau zurück → wertvolle bullische Information. Umgekehrt ist es relative
   Schwäche.
6. **Score 0–100:**
   - ≥ 80 „Extreme Confluence“ (nur bei passender Price Action/Location handeln)
   - 65–79 starker Bias
   - 50–64 neutral
   - < 35 Gegen-Conviction

   Entry **nur mit HTF-Location + LTF-Trigger**. Das PDF sagt selbst, dass es „noch kein
   statistisch kalibriertes Modell“ ist.
7. **Täglicher Ablauf:** COMEX-Flow → Optionen → ETF/CFTC → Physisch → Price Response →
   erst zuletzt Makro → Score → Entry.

## Was davon frei nachbaubar ist

| PDF-Baustein | Nachbau | Status |
|---|---|---|
| COMEX Preis+OI+Volumen | CFTC-OI **wöchentlich** + GC=F-Volumen als Verstärker | Proxy (täglich nicht frei) |
| Optionen | GVZ-Änderung in Preisrichtung | Proxy; Skew/Risk Reversals/Strike-OI **nicht frei** |
| ETF-Flows | GLD-Bestand in Tonnen, täglich ab 2004 (SPDR-Archiv) | 1:1 |
| CFTC + Gegenseite | Managed Money + Other Reportables (Disaggregated ab 2006) | 1:1 |
| Shanghai-Prämie | SGE-PM-Benchmark × USDCNY gegen XAUUSD, ab 04/2016 | 1:1 ab 2016 (Discount 2020 und Rekordprämie 2023 korrekt sichtbar) |
| India-Prämie | – | entfällt |
| COMEX-Lager/Deliveries | – | entfällt (CME nur Tageswert) |
| Zentralbanken | IMF IRFCL, alle Länder, 12 Monate netto, 2 Monate Lag | Proxy: nur **gemeldete** Käufe (2023: 271 t statt ~1.000 t laut WGC) |
| Futures-Basis | – | entfällt (Yahoo-Endloskontrakt + andere Schlusszeit = Rauschen; GOFO seit 2015 eingestellt) |
| GDX/Silber/Kupfer | yfinance, 20-Tage-Verhältnisse | 1:1 |
| Absorption/rel. Stärke | Gold-Rendite minus rollierende USD/Realzins-Erwartung (250 T, nur Vergangenheit) | 1:1 |
| News-Reaktion | Reaktion an Zins-Schocktagen (\|Δ2J\| > 2× Median) gegen die Erwartung | Proxy ohne Kalender |
| Makro | DFII10, DXY, Breakeven 10J, EPU | 1:1 |

Fallen ganze Bausteine weg, werden die übrigen innerhalb ihres Blocks anteilig neu gewichtet.
Code: `fusion_lab/gold_confirm/` (data, components, score).

## Bewertung

Eine durchdachte diskretionäre Checkliste, die zu dem passt, was Desks lesen. Zwei Schwächen
zeigt der Nachbau sofort:
- Viele Bausteine messen **dasselbe Gold-Momentum** (Spearman zum 20-T-Momentum: rel. Stärke
  0,87, Miner 0,52, Managed Money 0,51, Realzins 0,46, Kupfer 0,43, Absorption 0,40). Das ist
  dasselbe Muster wie [[makro-gates-evidenz]].
- Der Mittelwert aus 17 schwach korrelierten Bausteinen drückt den Score zur Mitte: ≥ 80 kam
  2010–2026 an 0,4 % der Tage vor, ≥ 65 an 12 %. Die „Extreme Confluence“ gibt es praktisch nicht.

Testergebnisse: [[gold-confirmation-score]].
