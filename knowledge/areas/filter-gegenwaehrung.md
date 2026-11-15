# Area: Filter-Baustein „Gegenwährung“ (Zinsen × Angst)

Filter des Makro-Agenten ([[quant-diskretionaer-fusion]], Strang 3) für die Frage: **Der Dollar soll
steigen. Gegen wen?** Häfen (CHF, JPY) oder Rohstoffwährungen (AUD, NZD, CAD). Entstanden aus der
Prüfung der SMT-Reports KW47 ([[makro-agent-report-pruefung]], Beispiel 3). Nutzer 15.11.2026:
Einschränkung „klingt sinnvoll“, per Backtest prüfen, dann „das passt“, abspeichern für den Makro-Filter.

## Definition

- Code: `fusion_lab/filters/gegenwaehrung.py`
  - `korb(angst_ausloeser, jpy_eingriff_droht=False)`: Sonntags-Regel, liefert den bevorzugten Korb.
  - `wochen_regime(d2y_bp, vix_chg)`: Nachprüfung einer abgeschlossenen Woche.
  - `spread(...)`: S = Dollar-Gewinn gegen Häfen minus gegen Rohstoffwährungen.
- **Zinswoche:** US-2J (FRED DGS2) steigt Freitag gegen Freitag um ≥ 10 bp.
- **Angst:** VIX steigt in derselben Woche. Die Änderung zählt, das Niveau nicht (VIX > 20 bringt OOS nichts).

## Beleg (Lock `gegenwaehrung_angst`, 6 Versuche, `scripts/research_gegenwaehrung_angst.py`)

Wochen 2004–05/2026 (yfinance FX/VIX/S&P, FRED DGS2). IS 2004–2017, OOS 2018 bis 15.05.2026, Tresor
(letzte 6 Monate) zu.

| Zinswoche | IS: S / Anteil S > 0 / n | OOS: S / Anteil / n |
|---|---|---|
| ohne Angst | **+1,14 %** / 83 % / 41 | **+0,31 %** / 63 % / 38 |
| mit Angst | +0,68 % / – / 10 | 0,00 % / – / 31 |
| Unterschied | +0,46, p 0,20 | +0,30, p 0,24 |

- Alle Wochen (ohne Zinsfilter): Angst derselben Woche trennt stark (t 9,4 IS / 5,2 OOS). Das ist
  der bekannte Risk-on/Risk-off-Mechanismus, gleichzeitig gemessen.
- Vorwoche → Folgewoche: nichts (OOS p 0,20–0,90, auch mit S&P und VIX-Niveau).
- KW46/2026 (Anlass): Zinsen +35 bp, VIX −6,3 → „Zinsen ohne Angst“, S +0,45 (Franken −2,3 %, AUD −1,35 %).

## Regel für den Agenten

1. Dollar-These aus Zinsen → **Standard-Gegenwährung ist der Hafen** (CHF; JPY nur, wenn kein Eingriff droht).
2. **Rohstoffwährung nur bei konkretem Angst-Auslöser in der Woche** (Termin, Zahlen, Gipfel, Eskalation)
   und dann mit halber Überzeugung: Der Vorteil ist auch bei Angst nicht belegt (OOS 0,00 %).
3. Den Auslöser benennen; der VIX der Vorwoche zählt nicht als Begründung.
4. Jede Woche im Weekly prüfen: welches Regime kam wirklich, welcher Korb verlor mehr.
5. Ersetzt Leitlinie Punkt 2 („Dollar-Stärke nur gegen Rohstoffwährungen, nie gegen Häfen“) in
   [[makro-agent-report-pruefung]].

## Meine Einschätzung (15.11.2026)

- **Stärke:** Der Befund „Hafen bei Zinsen ohne Angst“ trägt in IS und OOS, ist ökonomisch sauber
  (zinsloser Hafen ohne Nachfrage = schwächstes Glied, Report SMT „Wer keinen Zins zahlt, wird
  verkauft“) und erklärt KW46.
- **Schwäche:** Es ist ein **Erklär-, kein Vorhersage-Filter**. Er sagt, was in einer Woche passiert,
  wenn man das Regime kennt. Den Wert hat er nur, wenn der Agent Angst-Ereignisse vorab richtig einschätzt.
  Das ist genau das, was vorwärts gemessen werden muss ([[overfitting-sperre]], Memory „LLM-Agent nur
  vorwärts testbar“). Der Abstand OOS ist halb so groß wie IS; n mit Angst in IS nur 10.
- **JPY ist ein Sonderfall:** Nahe der Eingriffszone (2026: 160–164) dreht der Yen per Ministerium,
  nicht per Markt. Darum `jpy_eingriff_droht`.
- **Nicht geprüft:** Schwelle 10 bp (fest, nicht optimiert), EUR/GBP als dritter Korb, Wirkung als
  Handelsregel mit Kosten (der Filter wählt nur die Gegenwährung, er erzeugt keine Trades).
- **Anwendung KW47:** Zinsen bleiben das Thema; Angst-Auslöser = Nvidia-Zahlen Di 22:20 und
  Anthropic-Börsengang Mi. Darum ist der bestehende AUD-Short vertretbar (Auslöser vorhanden), ein neuer
  Dollar-Trade würde aber eher gegen CHF gehen (JPY: Eingriff droht). Nachprüfung im Weekly KW47.

## Verwandt

[[filter-gold-zinskurve]] (Schicht Zinsen für Gold), [[regime-bestimmung-und-filter]] (Katalog),
[[makro-wirkketten-und-regeln]].
