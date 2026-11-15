# Auftrag: NVIDIA-Analyse nach den Quartalszahlen, per Telegram

Du läufst unbeaufsichtigt (geplanter Task, Dienstag 17.11.2026, 23:45 Uhr deutscher Zeit, also kurz nach der
Veröffentlichung der Zahlen und während des nachbörslichen Handels). Der reguläre Kurs ist der Schluss vom 17.11.;
die Reaktion auf die Zahlen ist bisher nur nachbörslich sichtbar. Sage das in der Nachricht klar.
Niemand kann Rückfragen beantworten. Keine Orders, keine Broker, keine Bridges, keine Commits.
Schreibe auf Deutsch, einfache Sprache, keine Anlageberatung.

## Ausgangslage (Analyse vom 15.11.2026, Schluss 13.11.)

- Kurs 162,85 $. Hoch 243,37 $ (06.10.), Tief 148,80 $ (12.11.). RSI 24,9, ATR 11,0 $ (6,8 %).
  SMA20 198,7 / SMA50 214,6 / SMA200 203,9.
- Jensen Huang am 12.11. als CEO zurückgetreten, Colette Kress Interims-CEO. China-Schmuggel-Ermittlungen.
- Prognose Q3 FY27: Umsatz 108 Mrd. $ ±2 %, Bruttomarge 74,0 % ±0,5 Pp., ohne China. Konsens ~109 Mrd. $, EPS ~2,47.
- Warnzeichen Q2: Forderungen 38,5 → 63,1 Mrd. $, Lager 21,4 → 31,6 Mrd. $, operativer Cashflow mehr als halbiert.
- Szenarien vom 15.11.: **A** Rücksetzer 149–158 $, Stopp unter 145 $. **B** Ausbruch über 172 $ (Tagesschluss),
  Stopp unter 158 $. **C** Abwarten. Ziele 180–182 $, dann 199–204 $.
- Der Nutzer hat am 13.11. zwischen 158 und 170 $ gekauft.

## Schritte

1. Prüfe per WebSearch, ob NVIDIA die Q3-Zahlen (FY2027) veröffentlicht hat (erwartet 17.11. nach Börsenschluss,
   einzelne Quellen nennen den 18.11.). Falls **noch nicht**: Schicke eine kurze Nachricht „Zahlen noch nicht
   veröffentlicht“ mit dem neuen Termin und dem aktuellen Kurs, sonst nichts weiter.
2. Hole die Zahlen: Umsatz, Rechenzentren, Bruttomarge, EPS gegen Prognose und Konsens, Ausblick Q4,
   Aussagen zu China, Führung (Kress, Nachfolgesuche), Forderungen/Lager/Cashflow, Aktienrückkauf.
   Nur Zahlen nennen, die in den Quellen stehen. Bei Widersprüchen zwischen Quellen die Firmenmitteilung nehmen
   und den Widerspruch kurz nennen.
3. Hole Reaktion und Stimmung: nachbörsliche Kursbewegung am 17.11. (Kurs und Prozent, Quelle mit Uhrzeit),
   erste Aussagen aus der Telefonkonferenz (läuft ab 23:00 Uhr), erste Analysten-Reaktionen, wichtigste
   Schlagzeilen. Preisbereiche aus Schritt 5 beziehen sich auf den Tageschart bis 17.11.; ordne den
   nachbörslichen Kurs darin ein (in welcher Zone/über welcher Marke er gerade liegt).
4. Technik **selbst rechnen**: `python scripts/reports/stock_technicals.py NVDA` (Bash). Keine Indikatorwerte
   von Webseiten übernehmen.
5. Leite neue Preisbereiche aus den gerechneten Marken ab (Swing-Hochs/-Tiefs, SMAs, Volumenprofil, ATR):
   - Rücksetzer-Zone mit Stopp etwa 1 ATR unter der Zone
   - Bestätigungs-Marke mit Stopp
   - Ziele
   - Chance-Risiko je Szenario. Nur Szenarien mit Chance-Risiko ≥ 2 als Einstieg nennen.
6. Vergleiche mit dem 15.11.: Was ist von A/B/C eingetreten? Waren die Bereiche brauchbar?
   Lag die Einschätzung zu den Warnzeichen richtig?
7. Schreibe die Nachricht nach `fusion_lab/data/screener/nvda_followup_2026-11-17.txt`
   (Ordner bei Bedarf anlegen). Höchstens ~3500 Zeichen, reiner Text ohne Markdown-Tabellen
   (Telegram), mit Emojis als Gliederung. Aufbau:
   - 📊 NVIDIA nach den Zahlen (Datum, Kurs, Tagesbewegung)
   - 🧾 Zahlen gegen Erwartung (5–7 Zeilen)
   - 🗞️ Reaktion und Stimmung (3–4 Zeilen)
   - 📈 Technik (Trend, RSI, ATR, wichtige Marken)
   - 🎯 Neue Preisbereiche: Szenario A / B / C mit Zone, Stopp, Ziel, Chance-Risiko
   - 🔁 Vergleich mit dem 15.11. (was eingetreten ist)
   - 💼 Für deine Position (Kauf 158–170 $): sachlich, welche Marke entscheidend ist. Keine Kauf- oder
     Verkaufsempfehlung als Befehl.
   - Fazit in 2 Sätzen + Hinweis „Analyse, keine Anlageberatung“
   - Quellen: 3–5 Domains
8. Versende: `python scripts/reports/send_telegram_text.py fusion_lab/data/screener/nvda_followup_2026-11-17.txt`
9. Antworte am Ende mit einer Zeile: versendet ja/nein und der Dateipfad.
