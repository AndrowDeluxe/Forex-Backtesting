# Resource: Wirkketten-Katalog und Geopolitik-Framework (Makro-Agent v3)

Stand 12.11.2026, erweitert 24.11.2026. Code: `fusion_lab/macro_agent/chains.py` (Ketten), `geo_framework.py` (Exposure-Matrix,
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

## Katalog (25 Ketten, seit 24.11.; Education-Ketten und Rangliste unten)

Öl→Fed→Gold · Öl→BoC→CAD (SMT) · Öl→Importeure · Defizit→OAT-Bund→EUR (SMT) · KI-Schulden→HY→Aktien (SMT, seit 15.11. HYG/IEF, nur bei ruhigem VIX) ·
Öl-Prämie Angriff vs. Menge (SMT) · Zölle→Inflationserwartung · Ukraine→Gas→EUR · Stress→Häfen · KI-Gewinne→KOSPI→AUD (seit 15.11. KOSPI statt Nasdaq) ·
US-Zinsen→Dollar · China→Kupfer→AUD · Fed-Druck→Gold · KI-Chips→Korea-Exporte→AUD/Nasdaq · Speicherchips→China-Preise→2J→Gold · KI-Ausbau→Kupfer→AUD (die letzten drei aus Danske, ohne Vorlauf im Backtest, nur Vorwärts-Prüfung im Ledger). Status je Lauf: aktiv / umgekehrt (seit 24.11.) / anlaufend / gestoppt / ruhend;
Beleg „belegt“ nur, wenn der letzte Schritt in der Exposure-Matrix stabil ist.

## Befunde 15.11. (Danske-KI-Ketten, Lock `ai_wirkketten`)

Details und Zahlen in [[danske-ai-investment-tracker]]. Vom Nutzer bestätigt und in `chains.py` umgesetzt (15.11.).
- **`ki_schulden_hy`:** Bedingungslos läuft der Kredit-Spread nicht vor den Aktien. Es ist umgekehrt: Nasdaq →
  BAA10Y in der Folgewoche, t −3,1 / −2,9. Nur bei VIX < 20 zeigt die Richtung schwach in die erwartete Richtung
  (HYG/IEF-Ersatz, t −1,4 / −1,2). FRED-HY gibt es nur ab 11/2023.
- **`risiko_an_ki` / AUD:** Seit 2025 liegt AUD~Nasdaq nur bei +0,21. AUD~KOSPI liegt bei +0,54. Die Tech-Kopplung des AUD
  läuft über Asien.
- **`china_kupfer`:** Kupfer hat keinen Vorlauf für den AUD (OOS t −1,6), der Gleichlauf schwächer (+0,34).
- Kein Vorlauf haben außerdem: Korea-Exporte → AUD/Nasdaq und China-Importpreise → 2J/Gold.

## Befunde 22.11. (VIX / Zinsen / DXY → S&P und Gold, Lock `vix_zins_wirkkette`)

Anlass: Dennis im Call 22.11. („Fallen VIX und Zinsen, ist das gut für Gold und Indizes“, 2J-Pfad in 4,30–4,50
bis ~04.12.) und Signal 1 des SMT-Gold-Reports. Skript `scripts/research_vix_zins_wirkkette.py`, IS 2005–2017,
OOS 2018–21.05.2026, Tresor zu. Gold = GLD (Schluss 16:00 ET wie S&P/VIX), 2J = FRED DGS2. 50 Versuche gezählt.

| Frage | Ergebnis |
|---|---|
| Gleichlauf (Wochen, IS / OOS) | S&P~VIX −0,81 / −0,75. Gold~DXY −0,47 / −0,45. Gold~2J −0,18 / −0,24 (fast jedes Jahr negativ). **Gold~VIX +0,02 / −0,12, Vorzeichen wechselt je Jahr.** |
| Quadranten (Ø Woche) | Gold folgt den Zinsen, nicht dem VIX: Zins fällt → +0,5…+0,8 % (am besten mit *steigendem* VIX), Zins steigt → −0,1…−0,3 %. S&P folgt dem VIX: VIX fällt → +1,2…+1,6 %, egal was die Zinsen tun. |
| Vorlauf (Woche t → t+1 bzw. t+1..t+4) | Keiner. Alle \|t\| < 1,6. dVIX, d2J und dDXY sagen S&P und Gold nicht voraus. |
| VIX-Schluss > 30 → S&P | IS +20T −0,6 % (t −0,7), OOS +4,9 % (t 4,1). Nach Jahren: 2008 −4,9 %, 2010/11 negativ, ab 2018 durchweg positiv. Regime, keine Regel. Gold: nichts. |
| VIX und 2J fallen beide (5 T) → vorwärts | S&P OOS +20T +1,8 % (t 2,6), IS nichts. Gold nichts (OOS Δ 0,0). Mit VIX vorher > 30: S&P OOS +6,2 % (t 4,2), IS −0,6 %; 2008 −4,5 %, 2020/25 +8…+9 %. |
| Gold-Bodensignal „Stresstag“ (GLD grün, S&P ≤ −1 %) | Allein kein Edge (IS/OOS Δ ≈ 0). Mit Gold ≥ 10 % unter dem Hoch: +60T IS +2,5 % vs +0,9 % (t 1,1), OOS t 1,4, n 15. Mit ≥ 20 %: IS +20T +4,2 % vs +1,1 % (t 1,8), aber nur 2008 und 2013/14 (zwei Episoden, 2013 kein Boden), OOS kein Fall. **Nicht belegt, nicht widerlegt.** |

**Lesart für den Agenten:** Die Kette „Zinsen fallen → Gold steigt“ und „VIX fällt → Indizes steigen“ stimmt
als Gleichlauf und steht schon als stabiler Kanal oben (12.11.). Sie ist kein Signal: Wer den 2J-Pfad richtig
vorhersagt, verdient, nicht wer auf vergangene Bewegungen reagiert. Den VIX für Gold nicht verwenden. „VIX > 30
= Kaufgelegenheit“ gilt nur in Phasen mit schneller Fed-Hilfe (2018–2025), 2008–2011 war es falsch; welches Regime
gerade läuft, ist die eigentliche Frage. Das Gold-Bodensignal bleibt Vorwärts-Beobachtung (Report-Signal 1).

## Befunde 24.11. (Rückwärts-Erkennung, Education-Ketten, Rangliste, Lock `wirkketten_ranking_v1`)

Nutzerauftrag 24.11.: Ketten auch rückwärts erkennen, fehlende Ketten aus der OneNote-„Makro Education“
([[makro-faktoren-katalog]], Regeln 1–25) ergänzen, mit den Fact-Sheet-Daten prüfen, welche Ketten am besten
funktionieren.

- **Neuer Status „umgekehrt“:** 21 von 25 Ketten haben Umkehr-Schritte (meist der gespiegelte Auslöser). Läuft eine
  Kette rückwärts, zeigt das Blatt die Wirkung gedreht, und das Ledger prüft die gedrehte Richtung (20 T). Am 24.11.
  liefen 5 Ketten rückwärts (Brent −22 %, Kupfer −17 %, KOSPI −14 % in 20 T). Öl → Fed → Gold stand nur auf
  „gestoppt“, weil die 2J kaum fiel (−6 bp): Brent fällt allein ist noch kein Gold-Rückenwind.
- **9 neue Ketten** (Schwellen von Claude vorab gesetzt, nicht optimiert): Liquidität → Aktien/Gold (Regel 19),
  Realzins positiv und steigend → Nasdaq/Gold runter (18), Bull-Steepener → Dollar schwach (15), Funding-Stress →
  JPY als Hafen (21), Arbeitsmarkt-Abschwung (5/8/23, Sahm), US-Daten-Überraschung → Dollar (1/5/6), UST-JGB →
  USDJPY (Testkandidat 7), Laufzeitprämie → Gold (Desk-Abgleich, Hypothese), USDJPY + Aktien → AUD/Kupfer (20).
  China schwach → AUD (17) und Öl → EUR (16) stecken schon in `china_kupfer` und `oel_importeure`.

**Rangliste 2007–2026** (`scripts/research_wirkketten_ranking.py`, IS 2007–16, OOS bis 24.05.2026, Tresor zu,
176 Versuche). Kriterium vorab: Vorlauf 20 T in der Mehrheit der Assets IS t ≥ 2 und OOS t ≥ 1 gleichgerichtet.

| Urteil | Ketten (Arm) |
|---|---|
| Trägt (Vorlauf) | **keine** |
| Gleichlauf, kein Vorlauf (IS und OOS t ≥ 2) | Stress → Häfen (beide), KOSPI → AUD (beide), US-2J → Dollar (beide), China/KI → Kupfer → AUD (beide), Korea-Exporte (beide), UST-JGB → USDJPY (beide), Öl → CAD (beide), USDJPY + Aktien (nur rückwärts) |
| Trägt nicht | Öl → Fed → Gold, Öl → Importeure, Liquidität, Realzins, Bull-Steepener, Funding-Stress, Arbeitsmarkt, Daten-Überraschung, Laufzeitprämie, KI-Schulden |
| Zu wenig Daten / nur vorwärts | OAT-Bund (OECD-Monatswerte), China-Preise aktiv; vier Schlagzeilen-Ketten |

Auffällig, aber kein Beleg (bei 176 Versuchen erwartbar ~1 Zufallstreffer):
- **USDJPY + Aktien steigen → AUD und Kupfer fallen danach** (Gegenrichtung zu Regel 20): AUD 20 T IS −1,4 % (t −2,4),
  OOS −1,3 % (t −2,3); Kupfer −3,2 % (t −3,6) / −3,1 % (t −2,1). Stabil in beiden Hälften, aber nicht vorab als
  Richtung getestet → neue Hypothese (Ideen-Inbox), eigener Test nötig.
- **Liquidität steigt → Aktien** nur 2017–26: S&P +2,6 % (t 4,5), Nasdaq +3,2 % (t 4,2); 2007–16 negativ (t −1,6).
  Regimewechsel, keine Regel.
- **Funding-Stress → S&P** war 2007–16 ein Kaufsignal (+4,5 % gegenüber dem Rest, t 2,4), wie VIX > 30 (22.11.).
- KOSPI → AUD (aktiv) einzeln IS t 2,1 / OOS t 2,1, Kupfer nicht → keine Mehrheit.

**Lesart:** Wirkketten beschreiben zuverlässig, was gleichzeitig passiert (12 Arme belegt), aber keine sagt die
nächsten 4 Wochen voraus. Das Fact Sheet zeigt das Urteil je Kette in der Spalte „Test 2007–26“; das Ledger prüft
weiter vorwärts.

## Befunde 26.11. (CPI/NFP-Ereignisstudie, [[ereignisstudie-cpi-nfp]])

- CPI gegen NFP hängt am Regime: bis 2018 bewegte NFP USD/2J 3–5× stärker, 2021–23 CPI 3–4×, seit 2024 gleich.
  Der Markt reagiert auf die Zahl, die das aktuelle Fed-Problem misst.
- Core schlägt Headline nur bis 2018; Inflationsüberraschung mit/ohne Wachstumsschwäche liefert keine Drift (0/6).
- Termine sind Reaktion, keine Kette mit Vorlauf: erste Stunde mit der Überraschung, danach nichts Handelbares.

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
