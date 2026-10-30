# Makro-Wirkketten und Entscheidungsregeln (Wissensbasis Makro-Agent)

Grundlage für den Makro-Agenten (Dachprojekt [[quant-diskretionaer-fusion]],
Strang 3). Ergänzt den Faktor-Katalog [[makro-faktoren-katalog]] (WAS es an
Faktoren gibt) um das WIE: in welchen Ketten Faktoren wirken, woran man sieht,
dass eine Kette läuft, was sie stoppt, und nach welchen Regeln aus einer Kette
ein Trade wird. Nichts hier ist getestet; jede Regel ist eine Hypothese unter
der [[overfitting-sperre]] (vorwärts messen, siehe Memory „LLM-Agent nur vorwärts testbar“
).

## Capture

- SMT Macro Desk Mittwochsreport + Deep Dive vom 21.10.2026 (Telegram „SMH
  Daily Update“, msg 6759/6760; Rohmaterial gitignored unter
  `fusion_lab/raw/telegram/`). Ab diesem Datum führt Dennis Positionierung und
  Zinspricing fest im Report.
- Nutzer-Stichproben 16.10. und 21.10. (Status-Definition aktiv/event/watch).
- Faktor-Katalog aus OneNote (12.10.).

## Organize

Tags: Makro, Wirkkette, Gate, Positionierung, Zinspricing, Szenario, Agent.
Verwandt: [[makro-faktoren-katalog]], [[quant-diskretionaer-fusion]],
[[bond-yield-spread-indikator]], [[overfitting-sperre]].

## Distill

### 1. Das Format einer Wirkkette

Jede These wird als Kette geführt, nicht als Schlagzeile:

| Feld | Inhalt |
|---|---|
| Kette | A verändert B, B verändert C (Mechanismus in 1–3 Schritten) |
| So läuft sie | Die Schritte in Worten |
| Woran man sieht, dass sie läuft | Messbare Zeichen mit aktuellen Zahlen (Kurs, Rendite, Pricing, Modell) |
| Was sie stoppt | Konkrete Widerlegung mit Schwelle |

Wer die Kette kennt, weiß auch, was sie bricht. Der Agent soll jede aktive
Idee mit genau diesen vier Feldern begründen.

### 2. Beispielketten (Stand 21.10.2026)

| Kette | Läuft, sichtbar an | Stoppt bei |
|---|---|---|
| Öl + Inflation → BoC-Erwartung → CAD stärker | USD/CAD fällt, CAD-10Y steigt, SMT-CAD vorn, BoC-Pricing springt | Brent < 105 (Iran-Einigung), BoC hebt nicht oder signalisiert Ende |
| Defizit → Anleihe-Spread → (nicht) Euro | OAT-Bund-Spread steigt, EUR/USD flach, EUR schwach nur gegen CHF/GBP | Haushalt kommt durch, Rating bestätigt → Short-Eindeckung |
| KI-Schulden → Kreditaufschlag → Aktien (verzögert) | HY-Spread steigt bei fallendem VIX, Chips fallen, Dow stark | Gute Capex-Guidance, HY < 315 |
| Öl-Prämie: Angriff vs. Menge | Angriffe hoch, Exportmengen über Umwege normal | Waffenruhe/Einigung nimmt eine Angriffsprämie schneller weg als eine Mengenkrise |

Weitere Ketten (aus OneNote) stehen als Wenn-Dann-Regeln im
[[makro-faktoren-katalog]], z. B. Inflation über Erwartung → Zinserwartung →
Währung; Zinskurve steiler bei fallender 2y → Senkungen eingepreist → Dollar
schwächer; Liquidität → Risiko-Assets.

### 3. Entscheidungsregeln (neu seit 21.10. im SMT-Report)

1. **Eingepreist ist bezahlt.** Ist ein Zinsschritt zu ≥ 75 % eingepreist, ist
   die Sitzung kein Grund für einen Trade mehr, sondern ein Risiko für einen
   laufenden (kein Aufstocken in die Sitzung).
2. **Die Veränderung ist das Signal, nicht der Stand.** Entscheidend ist, wie
   sich die eingepreiste Wahrscheinlichkeit in einer Woche verändert hat
   (Beispiel BoC 30 → 79 %). Früh erkennen, bevor es gepreist ist.
3. **Positionierung (F-Gate):** Profis (Leveraged Funds, CFTC TFF) extrem in
   unsere Richtung = Konflikt, die Bewegung ist weitgehend gelaufen; extrem
   gegen uns = Treibstoff, aber nur mit einem Ereignis, das zum Eindecken
   zwingt. Kleinanleger ≥ 75 % auf unserer Seite = Abschlag.
4. **Ereignis-Disziplin:** Keine Aktivierung 15 Minuten um wichtige Daten;
   Aktivierung nur per Tagesschluss; nicht nachlaufen (Rücklauf abwarten).
5. **Ein Faktor, ein Trade:** Zwei Ideen mit demselben Treiber (z. B. EUR/USD-
   und EUR/GBP-Short über Frankreich) nicht gleichzeitig.

### 4. Die fünf Gates (M/R/P/B/F)

| Gate | Frage |
|---|---|
| M | Gibt es einen Grund aus Wirtschaft oder Notenbank? (≥ 75 % gepreist zählt nicht) |
| R | Laufen die Zinsen/Zinserwartungen in die richtige Richtung? |
| P | Hat der Kurs die Richtung bestätigt? |
| B | Bestätigt das G8-Stärkemodell die Währungsstärke? (unser Nachbau: `fusion_lab/g8`) |
| F | Steht die Positionierung nicht schon überlaufen auf unserer Seite? |

Regel: mindestens 4 von 5 PASS und kein dominantes FAIL.

### 5. Status einer Idee (Nutzerdefinition)

- **aktiv:** Makro-Richtung klar; Einstieg nach technischer Validierung,
  bevorzugt auf Rücksetzer (Longs etwas tiefer, Shorts etwas höher). Ein
  Ereignis, das die Richtung nur bestätigt, ändert daran nichts.
- **event:** das Ereignis entscheidet über den Trade.
- **watch:** hängt von der weiteren Makro-Entwicklung ab.
- **hedge:** Absicherung (z. B. Gold), getrennt bewertet.

### 6. Szenarien mit Schwellen (Zustandsmaschine)

Drei Zustände mit messbaren Übergängen statt Wahrscheinlichkeiten:
BASE (Lage hält), ALT (Entlastung), TAIL (Stress). Übergänge sind an Zahlen
gebunden, z. B. TAIL wenn zwei von: OAT-Bund-Spread > 180, VIX > 28,
HY-Spread > 350, Brent > 120; Dollar wird wieder sicherer Hafen, wenn der DXY
an einem Tag mit S&P < −1,5 % und VIX > 24 steigt. Das ist direkt
programmierbar.

### 7. Datenbedarf (abgeleitet aus den genutzten Quellen)

| Baustein | Quelle bei SMT | Frei verfügbar? |
|---|---|---|
| Zinserwartung je Notenbank (OIS) | Prime Market Terminal | nein; Näherung über 2y-Renditen/Futures nötig |
| Positionierung Profis | CFTC TFF | ja (cftc.gov, wöchentlich, Stand Dienstag) |
| Positionierung Kleinanleger | Broker-Stichprobe | teilweise |
| HY/IG-Spreads, Renditen, VIX | FRED, TradingEconomics | ja (FRED) |
| Öl, Lager | EIA, Kpler | EIA ja |
| Bank-Research-Zählung | Prime Market Terminal | nein |
| G8-Stärke | SMT-Modell | ja, eigener Nachbau |

### 8. Eigene Scorecard von SMT (seit 23.09.2026)

Richtung 10 richtig / 3 falsch, aber nur 2 umgesetzte Trades in vier Wochen;
Dennis' eigener Schluss: die Rücklauf-Regel ist zu streng. Genau diese Frage
prüft Variante D im Report-Backtest (`smh_macro_reports_v2`).

## Express

[Anm.] Für den Agenten: jede Idee mit Kette (4 Felder), Gates (M/R/P/B/F),
Status (aktiv/event/watch/hedge) und Zustand (BASE/ALT/TAIL) führen; Regeln
3.1–3.5 als harte Filter vor jeder Freigabe. Offene Datenfrage: OIS-Pricing
ohne kostenpflichtigen Anbieter.
