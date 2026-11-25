# Resource: Endogene Analyse, exogene Analyse, Gatekeeping (eigene Recherche)

Stand 25.11.2026. Anlass: Die Kursseiten „Endogene Analyse“ (10), „Exogene Analyse“ (5) und „Gatekeeping
Prozess“ (3) aus dem Incentive-Kurs 2025 sind im OneNote-Import leer (keine Bilder, ~90 Zeichen Text, Inhalt
vermutlich Video/Ink). Nutzerauftrag: eigene Recherche statt Kursinhalt. Die eigenen Aufarbeitungen
(„Aufarbeitung GS Prozess“, Journal-Seite „Gatekeeping“) werden mit `fusion_lab/inventory/makro_education_extract.py`
ausgelesen, sobald die Abo-Grenze es zulässt. Verwandt: [[makro-faktoren-katalog]], [[makro-wirkketten-katalog]],
[[makro-scorecard-v2]], [[quant-diskretionaer-fusion]].

Tags: Makro, FX, Prozess, Zahlungsbilanz, Gatekeeping.

## Begriffe, wie der Kurs sie gliedert (aus den Seitentiteln)

| Baustein | Kursseiten | Inhalt laut Literatur |
|---|---|---|
| **Endogen** (Binnenwirtschaft) | CPI, Zinsen, M2, Baugenehmigungen, Konsumklima, ISM-/Dienste-PMI, „Der Makro-Prozess“ | Konjunktur- und Inflationszyklus des Landes → Notenbank-Reaktion → Zinserwartung. Zeithorizont Wochen bis Monate; einzelne Termine wirken als Überraschung. |
| **Exogen** (Außenwirtschaft) | Zahlungsbilanz, Balancing Item, Kapitalflüsse vs. Handelsbilanz, BIP, Carry/Zinsdifferenzen | Wer finanziert wen: Leistungsbilanz, Netto-Auslandsvermögen, Kapitalströme, Zinsdifferenz (Carry). Bewertung über BEER/FEER (realer Wechselkurs gegen Fundamentaldaten). Zeithorizont Monate bis Jahre. |
| **Gatekeeping** | Technische Analyse, COT-Analyse, Gatekeeping | Qualifizierung einer Idee vor der Ausführung: Positionierung, Kursbestätigung, Ereignis-/Risiko-Filter. Trennung „lohnt sich die Idee?“ von „wie steige ich ein?“. |

## Was die Forschung dazu belegt

- **Makro sagt Währungsrenditen im Querschnitt voraus, kaum in der Zeit.** Menkhoff/Sarno/Schmeling/Schrimpf:
  Signale aus Makrodaten bringen bis ~6 % p. a.; die Vorhersagekraft kommt fast ganz aus den **Unterschieden
  zwischen Ländern zum selben Zeitpunkt**, die zeitliche Veränderung eines Landes trägt wenig bei.
  → Deckt sich mit unserer Wirkketten-Rangliste (24.11.): Ketten erklären, keine sagt die nächsten 20 Tage voraus.
- **Bewertung (realer Wechselkurs) ist eigenständig** neben Carry und Momentum (Menkhoff et al., RFS 2017);
  stärker, wenn man den Teil herausrechnet, den die Fundamentaldaten erwarten lassen (BEER-Gedanke).
- **Netto-Auslandsvermögen / globale Ungleichgewichte** erklären Währungsprämien: Schuldnerländer zahlen eine
  Prämie, besonders in Stressphasen (Della Corte/Riddiough/Sarno, „Currency Premia and Global Imbalances“).
- **Kurzfristige Vorhersage bleibt schwer**, Gleichgewichtsmodelle taugen eher für mittelfristige Positionierung
  (EZB-Bulletin 2021, MacDonald/Clark IMF WP 98/67).
- Praktiker-Prozesse (Macro Ops, Global Macro Method) gliedern: Ziel/Stil → Ideen → Validierung → Ausführung →
  Nachbereitung; Funding/Liquidität validieren die Makro-Sicht. „Gatekeeping“ als Begriff ist nicht verbreitet,
  entspricht aber der Validierungs-/Qualifizierungsstufe (bzw. Gates vor dem Einstieg).

## Abgleich mit unserem System

| Baustein | Bei uns | Stand |
|---|---|---|
| Endogen | Scorecard-Faktoren Zins-Momentum, Überraschungen; Länderprofile; Fact Sheet v4 (Wachstum, Liquidität) | getestet: kein Edge (Scorecard IS/OOS Sharpe −0,30/−0,18) |
| Exogen | Carry, Value (REER), Handelsbilanz in den Profilen; Carry/Vol im Fact Sheet | **fehlt: Leistungsbilanz/Netto-Auslandsvermögen als Faktor** |
| Gatekeeping | Gates R/P/F (Carry+Zins-Momentum, Preis, COT-Veto), Kalender, Makro-Veto | Veto-Regeln teils getestet ([[makro-gates-evidenz]]) |

## Testkandidaten (ungetestet, unter Overfitting-Sperre)

1. **Netto-Auslandsvermögen/Leistungsbilanz als Querschnitts-Faktor** (Schuldner short, Gläubiger long, Monat),
   allein und als sechster Scorecard-Faktor. Daten: IMF/BIS bzw. FRED-Leistungsbilanz je Land.
2. **Gatekeeping auf die eigenen Hand-Trades** (Inventur): Hätten COT-/Technik-Gates die Verlierer 2025
   ausgefiltert, ohne die Gewinner zu kosten? Nur IS, Regel aus der eigenen Aufarbeitung übernehmen, sobald gelesen.

## Quellen

- [Menkhoff, Sarno, Schmeling, Schrimpf: Currency Risk Premia and Macro Fundamentals](https://faculty.washington.edu/ss1110/IF/Sarno%20Currency%20Risk%20Premia%20and%20Macro%20Fundamentals%202013%20(1).pdf)
- [Menkhoff et al.: Currency Value (RFS 2017, Working Paper)](https://openaccess.city.ac.uk/id/eprint/14851/13/FXVALUE_Rev3_cepr.pdf)
- [Della Corte, Riddiough, Sarno: Currency Premia and Global Imbalances (CEPR DP 9549)](https://repec.cepr.org/repec/cpr/ceprdp/DP9549.pdf)
- [EZB Wirtschaftsbericht 7/2021: Gleichgewichtswechselkurse](https://www.ecb.europa.eu/press/economic-bulletin/articles/2021/html/ecb.ebart202107_01~e584b31d1a.en.html)
- [MacDonald, Clark: BEERs und FEERs (IMF WP 98/67)](https://www.imf.org/en/Publications/WP/Issues/2016/12/30/Exchange-Rates-and-Economic-Fundamentals-A-Methodological-Comparison-of-BEERs-and-FEERs-2592)
- [Macro Ops: The Meta Process](https://operators.macro-ops.com/wp-content/uploads/2017/08/The-Macro-Ops-Meta-Process.pdf)
- [Global Macro Method: Trade Creation Methodology](https://globalmacromethod.substack.com/p/trade-creation-methodology)
