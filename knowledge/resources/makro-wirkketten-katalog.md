# Resource: Wirkketten-Katalog und Geopolitik-Framework (Makro-Agent v3)

Stand 12.11.2026. Code: `fusion_lab/macro_agent/chains.py` (Ketten), `geo_framework.py` (Exposure-Matrix,
Öl-Durchgriff, Themen-Karten), `news_digest.py` (Schlagzeilen + Einordnung), `ledger.py` (Vorwärts-Prüfung).
Fact Sheet §5 und §6. Baut auf [[makro-wirkketten-und-regeln]] §2 (vier SMT-Ketten), [[makro-gates-evidenz]] und
[[makro-scorecard-v2]] auf. Anlass: Meridian-Vergleich (Freund des Nutzers) und Nutzerauftrag „Geopolitik,
News abseits des Kalenders, Richtung und Einfluss für Rohstoffe, Währungen, Indizes“.

Tags: Makro, Geopolitik, Wirkkette, Öl, Gold, Realzins, Agent.

## Grundsatz

Das Framework misst und erklärt, es gibt keine Richtung vor. Eine Kette sagt: „Wenn das läuft, bewegt sich X
so.“ Ob sie läuft, entscheiden Messwerte; ob die Aussage stimmt, prüft das Forecast-Ledger vorwärts.

## Befunde 12.11. (eigene Rechnung, Wochenrenditen)

| Frage | Ergebnis |
|---|---|
| Öl steigt → Gold schwer? | Nur über den Fed-Kanal. Gold je Brent +10 %: 2007–16 +1,4 % (t 5,8), 2017–26 +0,2 %, letzte 26 Wochen −0,9 %. 2026 hebt Brent +10 % die US-2J um 5,4 bp (früher 2,3/3,6) → Realzins/Dollar hoch → Gold runter. |
| Was trägt Gold stabil? | Realzins 10J +25 bp → Gold −1,2 % (IS) / −2,0 % (OOS); Dollar-Index +2 % → Gold −2,1 %. |
| Bewegt Geopolitik an sich Märkte? | Nein. 67 (IS) und 75 (OOS) Spitzen im Geopolitical Risk Index, keine signifikante Reaktion an Tag 0/+1/+5 (Lock `geo_framework_v1`). Geopolitik wirkt über Kanäle: Ölangebot, Zinsen, Gas. |
| Stabile Kanäle (belegt in IS, OOS und heute) | Brent → USDCAD/AUDUSD; Realzins/2J → USDJPY, EURUSD, Gold; Dollar → alle USD-Paare, Gold, Indizes; VIX → Indizes, AUD; Inflationserwartung → AUD, CAD, Kupfer, S&P. |
| Gekippt 2026 | Brent → Aktien (DAX, Nasdaq, Nikkei) früher positiv, heute negativ (Öl als Angebotsschock statt Nachfragesignal). |

## Themen und ihre Kanäle (Annahmen, im Fact Sheet so markiert)

| Thema | Kanal | Messgröße |
|---|---|---|
| Iran / Hormuz | Ölangebot → Brent; 2026 weiter über Fed-Erwartung | Brent, Öl-Durchgriff |
| Zölle / Trump | Importpreise → Inflationserwartung; Dollar uneinheitlich | Breakeven 10J |
| Ukraine / Russland | Energie → Europa-Gas → EUR, DAX | TTF (ohne freie Historie) |
| China / Taiwan | Exportkontrollen → Risikoappetit, Chips | VIX, Nasdaq |
| Druck auf die Fed | Glaubwürdigkeit → Inflationserwartung, Dollar schwach | 5J-in-5J |

## Katalog (13 Ketten)

Öl→Fed→Gold · Öl→BoC→CAD (SMT) · Öl→Importeure · Defizit→OAT-Bund→EUR (SMT) · KI-Schulden→HY→Aktien (SMT) ·
Öl-Prämie Angriff vs. Menge (SMT) · Zölle→Inflationserwartung · Ukraine→Gas→EUR · Stress→Häfen · KI-Gewinne→AUD ·
US-Zinsen→Dollar · China→Kupfer→AUD · Fed-Druck→Gold. Status je Lauf: aktiv / anlaufend / gestoppt / ruhend;
Beleg „belegt“ nur, wenn der letzte Schritt in der Exposure-Matrix stabil ist.

## Daten und Lücken

- Realzinsen: FRED DFII10/DFII5, T10YIE/T5YIE, T5YIFR; andere Länder nur 2J minus Kern-Inflation (ex post).
- Geopolitical Risk Index (Caldara/Iacoviello) täglich, ~10 Tage Verzug.
- Schlagzeilen: Google-News-RSS je Thema, Einordnung durch lokalen Claude Code (keine Zahlen, nur Lage).
- GDELT-Nachrichtenvolumen: Abruf gebaut, IP seit 12.11. gesperrt (429) → nicht im Tageslauf.
- TTF-Gas: Yahoo nur Tageswert, keine Historie.
- Earnings: Megacaps über Yahoo, Saisonzahlen von Hand aus FactSet (`fusion_lab/data/macro_agent/earnings_season.json`).

## Quellen

- [Caldara, Iacoviello: Measuring Geopolitical Risk (Daten)](https://www.matteoiacoviello.com/gpr.htm)
- [CNN 11.11.2026: Öl fällt auf Iran-Hoffnung](https://www.cnn.com/2026/11/11/economy/oil-price-iran-trump)
- [Forbes 13.10.2026: Krieg, Ölschock – und Gold fiel trotzdem](https://www.forbes.com/sites/jasonkirsch/2026/10/13/a-war-an-oil-shock-and-gold-still-fell-what-that-teaches-investors-about-hedges/)
- [CNBC 11.11.2026: Zölle treiben Kosten](https://www.cnbc.com/2026/11/11/canada-ambassador-trump-tariffs-investments.html)
- [FactSet Earnings Insight 06.11.2026](https://insight.factset.com/sp-500-earnings-season-update-november-6-2026)
