# Project: Edge Card „Copy Trading Daily Update“ (Calls aus SMH Daily Update)

**Status**: **OOS 27.10.2026 durchgefallen (A2 Ø −0,72 R, t −3,7) → als Bot-Grundlage verworfen.** **Stufe 2 (Dennis' Anweisungen) seit 28.10. im Forward-Test bis 31.03.2027; IS-Vorab negativ.** Edge Card fertig 20.10.2026 → [[copy-trading-dennis-edge-card-final]].** Diese Notiz enthält Verlauf und Entwürfe; bei Abweichung gilt die finale Karte. Nächster Schritt: Plan-Modus für den Bau (Bild-KI, Simulation, täglicher Import). Prozess: [[edge-card-workflow]]. Teil von Strang 2/5 im
[[quant-diskretionaer-fusion]]. Herkunft: Ideen-Inbox 07.10. (Copy-Trading-Bot).

## Ziel (Nutzer, 19.10.)

Ein tragfähiges Copy-Trading-Edge aus den Calls der Telegram-Gruppe „SMH Daily Update“.
Eigene Makro-Faktoren dienen als Veto: Zeigt der Makro-Agent oder die G8-Währungsstärke nach
News oder Änderungen eine rote Ampel, wird der Trade nicht genommen.

Reihenfolge der Stufen (Nutzer):

1. Nackt kopieren, ohne Nachfass-Anweisungen.
2. Mit den Nachfass-Anweisungen aus der Gruppe (BE ziehen, close, Risiko teilen).
3. Mit eigener Optimierung und dem Makro-Veto.

Erst nach validiertem Edge: täglicher Import ab 23 Uhr als geplante Aufgabe, später ggf.
stündlich.

## Datenbestand (Stand 16.10.)

- `fusion_lab/raw/telegram/SMH Daily Update__2552394198/`: 6.579 Nachrichten,
  17.03.2025–16.10.2026, ~4.500 Chartbilder (jpg/png), 162 PDFs (Makro-Reports).
- Posts kommen von Dennis (`1219398041`, ~5.000 Nachrichten) und zwei weiteren Mitgliedern
  (`5494233604`, `897798529`) sowie vom Kanal selbst. Nutzerentscheid: **alle zählen.**
- Rund 300 Nachfass-Hinweise im Text (BE ziehen, close, „invalide“, Risiko teilen).

## Phase 0 -- Entwurf Strategieverständnis

Nur aus den Nutzer-Antworten vom 19.10. und den gesichteten Posts. Alle Annahmen wurden am 19./20.10. bestätigt.

- **Markt/Asset**: Alles, wozu ein Call gepostet wird: FX-Majors und -Crosses (EU, GU, UJ, UC,
  NU, AU, AJ, EG, CHFJPY, USDCHF), Gold, Silber, US500, NAS100, US30. DXY-Charts sind nur
  Kontext und kein Call, weil DXY nicht handelbar ist.
- **HTF-Kontext**: Liegt bei Dennis (Makro, Dollar-These, Daily Closes). Wir übernehmen ihn,
  ohne ihn nachzubauen. Unser eigener Kontext ist das Makro-Veto (Stufe 3).
- **Call-Typ A, „Trade Idee“**: TradingView-Positionswerkzeug. Entry, SL und TP stehen als
  Zahlen an der Preisachse. Liegt der Entry über dem aktuellen Kurs beim Short bzw. darunter
  beim Long, handelt es sich um ein Limit.
- **Call-Typ B, „Watch“**: Graue oder farbige POI-Zone und ein gemalter Pfad, der die Richtung
  angibt. Es gibt keine Level-Zahlen. Zwei Einstiegsvarianten (Nutzer):
  - B1: Limit in der Zonenmitte.
  - B2: Einstieg nach M5-LTF-Bestätigung in der Zone (doppelter BOS).
  - SL bei Typ B, drei Varianten (Nutzer 19.10.): (a) hinter der Zone, (b) am nächsten
    HTF-Low/-High, (c) 2× ATR14 vom Entry.
  - TP bei Typ B, drei Varianten (Nutzer 19.10., je separat): (a) 2R fest, (b) Ende des
    gemalten Pfads, (c) nächstes HTF-High/-Low in Trade-Richtung (Lesart (c) bestätigt 20.10.).
  - HTF und ATR14 = Timeframe des geposteten Charts (meist H1/H4), nicht M5.
  - Variantenzahl: Typ B 2 Einstiege × 3 SL × 3 TP = 18, plus Typ A 2 Einstiege = 20. Über dem Richtwert 9,
    aber alles vorab festgelegt, nichts nachjustiert; trotzdem gezählt (`log_trials`), DSR.
- **Gültigkeit**: Ein Update gilt bis zum nächsten Update, bis zu „invalide“ oder bis Makro
  oder News ein klar anderes Bild ergeben. Das betrifft nur noch nicht ausgelöste Orders.
  Ein ausgelöster Trade läuft bis SL, TP oder bis zu einer Nachfass-Anweisung.
- **Nachfass-Anweisungen** (Stufe 2): BE ziehen, close, Risiko teilen bei korrelierten Calls
  (z. B. US30, NAS100 und US500 je 1/3 Risiko), „erneut einsteigen ist Nonsense“.
- **Wiederholung**: Postet Dennis dasselbe Symbol im nächsten Update neu, ersetzt der neue
  Chart den alten.
- **No-Trade** (Stufe 3): Rote Ampel aus dem Makro-Agenten oder der G8-Stärke.
- **Timeframes** (Nutzer 20.10.): Struktur, Zone, ATR und Kerzenschlüsse im Timeframe des
  Chartbilds (meist HTF), Bestätigung auf M5, M1 nur für die SL/TP-Reihenfolge.

## Bekannte Fallen (vor dem Test festhalten)

- **Survivorship in der Gruppe**: Gewinner werden nachgepostet („happy pips“, „Brett“),
  Verlierer kaum. Gemessen wird nur ab dem ursprünglichen Call-Bild, nie an Rückblicken.
- **Makro-Agent nur vorwärts testbar** (Memory `llm_agent_nur_vorwaerts_testbar`): Rückwirkend
  lässt sich nur das regelbasierte G8-Veto testen. G8 allein war als Einstieg kein Signal
  (Memory `g8_staerke_nachgebaut_kein_signal`, [[makro-faktoren-katalog]]), als Veto ist es eine gezählte Variante.
- **Kurzer Zeitraum**: 19 Monate. Der Tresor (letzte 12 Monate) wäre der größere Teil.
  Stufe 1 hat keine Parameter und ist daher ein einziger Test über alles. Stufe 3: IS bis 31.03.2026,
  OOS 04–10/2026, danach Forward statt Tresor ([[overfitting-sperre]], Abweichung vom
  Nutzer am 20.10. freigegeben).
- **Ausleseschritt**: Entry/SL/TP liest eine Bild-KI. Fehlerquote stichprobenartig prüfen,
  bevor gerechnet wird.

## Vergleichsquelle: verifizierter Track Record

Dennis postete am 23.09. (`media/6453_.pdf`) einen Prüfbericht von Alpha Performance
Verification für sein eigenes Konto („Quantforce Discretionary Multi-Asset Macro & Technical“,
brutto): 12.06.–31.12.2024 +423 %, 2025 +313 %, 01.01.–17.09.2026 +19 % (Mai −4,0 %,
Juni −3,2 %, Juli −1,1 %). Belegt das Konto, nicht die Gruppen-Calls. Nutzbar als Gegenprobe:
Folgen die kopierten Calls Monat für Monat seinem Konto?

## Felder 01–05

### 01 IDEE (Entwurf 19.10.)

Wir glauben beobachtet zu haben: Die Calls aus dem Daily Update laufen häufiger in die
angekündigte Richtung, als es der Zufall hergibt. Der Abstand ist so groß, dass auch ein
Nachahmer nach Kosten im Plus bleibt. Der Nachahmer steigt mit Verzögerung ein, zahlt Spread
und hat nicht Dennis' Urteil im laufenden Trade.

- **Ausgangszustand**: Meist abends zwischen 20 und 22 Uhr markiert Dennis je Markt eine Zone
  (POI) oder einen fertigen Trade für die nächsten Tage. Grundlage sind seine Makro- und
  Dollar-These und die HTF-Struktur (Charts meist H1/H4).
- **Normales Verhalten ohne diese Information**: An einer beliebigen markierten Zone reagiert
  der Kurs etwa so oft mit wie gegen die Richtung. Eigener Befund: Key Levels halten eher
  schlechter als Schein-Level.
- **Die Beobachtung**: Der Kurs erreicht die markierte Zone und dreht dort in die angekündigte
  Richtung. Die Information steckt im Paar aus Zone und Richtung.
- **Darf passieren, ohne die Idee zu widerlegen**: Die Zone wird nicht erreicht, dann gibt es
  keinen Trade. Die Reaktion fällt schwach aus. Der Kurs läuft kurz in die Zone hinein, ohne
  den SL zu treffen.
- **Darf nicht passieren**: Der SL wird erreicht, Dennis schreibt „invalide“, oder Makro und
  News drehen das Bild.
- **Ebenen**: HTF ist Dennis' These, sichtbar im Chart-Timeframe der Posts. LTF ist nur die
  M5-Bestätigung bei Variante B2.
- **Offen, und genau das sollen die Gegenproben trennen**: Kommt ein Vorteil aus der Richtung
  (Makro/Dollar) oder aus der Wahl der Zone?

### 02 REGEL (Entwurf 19.10.)

Die mit (H) markierten Punkte waren Claudes Vorschläge; der Nutzer hat sie am 20.10. bestätigt.

1. **Quelle**: Jede Nachricht der Gruppe mit Chartbild (jpg/png), Absender beliebig. Zeitpunkt
   ist die Telegram-Postzeit (UTC).
2. **Auslesen**: Eine Bild-KI liest je Bild: Symbol, Chart-Timeframe, Typ, Richtung und Level.
   - Typ A, wenn ein Positionswerkzeug mit Entry-, SL- und TP-Beschriftung zu sehen ist.
   - Typ B, wenn eine Zone mit gemaltem Pfad oder Pfeil zu sehen ist, der eine Richtung zeigt.
   - Kein Call: DXY und andere nicht handelbare Werte, Bilder ohne Zone oder Werkzeug.
3. **Rückblick ausschließen (H)**: Ein Bild ist nur dann ein Call, wenn Werkzeug oder Zone
   rechts über die letzte Kerze hinausragt und der Kurs den Entry bzw. die Zone nach dem
   Posting noch nicht erreicht hatte. Gewinner-Nachposts mit bereits gelaufenem Trade
   fallen so heraus.
4. **Update und Gültigkeit**: Ein Update ist eine Serie von Chartposts desselben Absenders mit
   höchstens 60 Minuten Abstand **(H)**. Eine nicht ausgelöste Order gilt bis zum ersten der
   folgenden Ereignisse:
   - Beginn des nächsten Updates desselben Absenders,
   - ein neuer Call zum selben Symbol (der neue ersetzt den alten),
   - eine Nachricht mit „invalide“ zu diesem Symbol (ab Stufe 2).
5. **Aktivierung (H)**: Die Order ist 5 Minuten nach der Postzeit aktiv (Reaktionszeit eines
   Nachahmers). Als Robustheitsprobe auch 60 Minuten.
6. **Typ A**: SL- und TP-Labels 1:1. Zwei Einstiege wie bei Typ B (Nutzer 20.10.: „einmal
   statisch mit Berührung, einmal über die BOS-Confi“):
   - A1: Limit am Entry-Label. Ist der Limit bei Aktivierung sofort ausführbar, wird zum
     aktuellen Kurs gefüllt.
   - A2: Der Kurs berührt das Entry-Label, danach doppelter BOS auf M5 wie in Punkt 8.
     Einstieg zum Schlusskurs der bestätigenden Kerze. SL und TP bleiben die Labels.
7. **Typ B1**: Limit-Order in der Zonenmitte.
8. **Typ B2**: Der Kurs erreicht die Zone. Danach entsteht auf M5 ein doppelter BOS in
   Call-Richtung (Definition: finale Karte, Regel 10; Nutzer 20.10.). Einstieg zum Schlusskurs der M5-Kerze,
   die den zweiten BOS abschließt. Ohne Bestätigung bis Ablauf der Gültigkeit gibt es keinen
   Trade.
9. **SL bei Typ B**: je Variante
   - (a) hinter der Zone, am gegenüberliegenden Zonenrand,
   - (b) am nächsten HTF-Low (Long) bzw. HTF-High (Short) jenseits des Entrys,
   - (c) 2× ATR14 des Chart-Timeframes vom Entry.
10. **TP bei Typ B**: je Variante
    - (a) 2R,
    - (b) Ende des gemalten Pfads,
    - (c) nächstes HTF-High (Long) bzw. HTF-Low (Short).
11. **Ausgelöste Trades**: Sie laufen bis SL oder TP, unabhängig von späteren Updates (Stufe 1).
    Treffen SL und TP in derselben Kerze, gilt der SL (konservativ). Geprüft wird auf
    M1-Daten.
12. **Risiko und Kosten**: Gemessen in R, Kosten (Spread + Kommission) je Instrument
    abgezogen.
13. **Stufe 2**: Zusätzlich gelten die Nachfass-Anweisungen ab ihrer Postzeit + 5 Minuten:
    - „BE ziehen“: SL auf Entry,
    - „close“: Schluss zum Kurs,
    - Risiko geteilt, wenn Dennis es für korrelierte Calls verlangt.
14. **Stufe 3**: Bei roter G8-Ampel zum Aktivierungszeitpunkt gibt es keinen Einstieg
    (Definition „rot“ offen). Den Makro-Agenten gibt es nur im Forward-Test.

Merksatz: Kopiert wird nur, was zum Postzeitpunkt noch vor uns lag, mit den Leveln aus dem Bild
und ohne Nachhilfe aus dem späteren Verlauf.

### 03 MECHANISMUS (Entwurf 20.10.)

Die Frage ist, warum ein Nachahmer an Dennis' Calls verdienen könnte. Kette:

1. **Richtung aus der Makro-Synthese (HTF)**: Dennis leitet die Richtung aus Dollar-These,
   Zinsen, Öl und Daily Closes ab. Hypothese: Makro-Information fließt langsam in die Kurse,
   über Tage bis Wochen. Ein Trader, der dem Makro-Fluss folgt, ist öfter auf der Seite des
   Trends als einer, der zufällig handelt. Bekannt aus der Literatur als Zeitreihen-Momentum
   und Carry in FX. Ob Dennis' Synthese mehr leistet als ein einfacher Trendfilter, ist offen.
2. **Zone als Ort, an dem der Rücksetzer endet (HTF)**: Die POI-Zone liegt gegen die Richtung,
   also im Rücksetzer. Dennis begründet sie meist mit **Fair Value** (Nutzer 20.10.): Der Kurs
   kehrt in einen Bereich zurück, den er zuvor einseitig und schnell verlassen hat. Hypothese: Dort nehmen Trend-Trader nach. Wer den Rücksetzer als Wende
   gehandelt hat, liegt dann falsch und muss schließen. Dieses Schließen treibt den Kurs in die
   Call-Richtung. Die Zone verbessert vor allem das Chance-Risiko-Verhältnis und weniger die
   Trefferquote.
3. **Bestätigung (nur B2, LTF M5)**: Zwei BOS in Call-Richtung zeigen, dass der Rücksetzer auf
   M5 vorbei ist. Hypothese: Die Rücksetzer-Trader werden erst dort sichtbar aus dem Markt
   genommen. Der Preis dafür ist ein schlechterer Entry, im Gegenzug fallen Trades weg, bei
   denen die Zone glatt durchlaufen wird.
4. **Was der Nachahmer nicht bekommt**: Dennis' Urteil im laufenden Trade (BE, Teilschluss,
   Re-Entry) und seine Auswahl, welche Calls er selbst wirklich handelt. Hypothese: Ein Teil
   seines Kontoergebnisses steckt genau dort. Deshalb trennen wir Stufe 1 (nackt) von Stufe 2
   (mit Anweisungen).
5. **Ausdrücklich keine Begründung**: Dass rund 1.300 Kursteilnehmer auf dieselben Level
   handeln, bewegt FX-Majors, Gold und US-Indizes nicht nennenswert. Ein selbsterfüllender
   Effekt wird nicht angenommen.

Kurzkette: Makro-Fluss (HTF-Richtung) → Rücksetzer in die Zone → Gegentrend-Trader treten ein →
Trend-Trader nehmen nach → Gegentrend-Trader müssen schließen → Bewegung in Call-Richtung.

Wichtig: Das ist eine Mechanismus-Hypothese. Wir behaupten noch nicht, dass sie bewiesen ist.

### 04 GEGENPROBE (Entwurf 20.10.)

- **Richtung**: Dieselben Calls mit gespiegelter Richtung schneiden nach Kosten nicht
  schlechter ab als das Original (vor Kosten etwa spiegelbildlich). Dann trägt Dennis'
  Richtung keine Information.
- **Makro gegen simplen Trend**: Wir ersetzen Dennis' Richtung durch einen einfachen
  Trendfilter, etwa Kurs über/unter dem 50-Tage-Schnitt, und behalten dieselben Zonen. Bringt
  das dasselbe Ergebnis, leistet die Makro-Synthese nichts über Momentum hinaus.
- **Zone gegen beliebiges Level**: Wir behalten die Richtung und steigen zur Aktivierung zum
  Marktkurs ein oder an einem zufälligen Level mit gleichem Abstand. Bringt das dasselbe Ø R,
  enthält die Zonenwahl keine Information.
- **Fair Value**: Zonen, die mit einer objektiven Fair-Value-Lücke im Chart-Timeframe
  zusammenfallen, schneiden nicht besser ab als Zonen ohne eine solche Lücke. Dann trägt die
  Fair-Value-Erklärung nicht.
- **Regime statt Können**: Das Ergebnis stammt fast nur aus USD-Short-Calls in Phasen, in
  denen der Dollar fiel (H1 2025), und verschwindet 2026. Dann ist es Regime-Beta und kein
  wiederholbarer Vorteil. Passt zum Kontobericht: 2026 nur +19 %, Mai bis Juli im Minus.
- **Rücksetzer-Mechanismus (BOS-Einstieg gegen statisch, A2/A1 und B2/B1)**: Der doppelte BOS senkt den Anteil der Trades nicht,
  bei denen der Kurs die Zone glatt durchläuft. Dann ist die Annahme falsch, dass dort
  Gegentrend-Trader herausgenommen werden.
- **Calls gegen Konto**: Die Monatsergebnisse der kopierten Calls hängen nicht mit Dennis'
  geprüften Monatsrenditen zusammen. Dann bilden die Calls nicht sein echtes Trading ab, und
  der Kontobericht ist kein Beleg für die Calls.

Kern: Eine gute Gegenprobe greift nicht nur die Performance an. Sie greift die angenommene
Ursache an.

### 05 TEST (Entwurf 20.10.)

- **Datenquelle**:
  - Calls: alle Chartbilder der Gruppe, 17.03.2025–16.10.2026. Eine Bild-KI liest sie aus
    (Symbol, Timeframe, Typ, Richtung, Level, Pfadende) in eine Tabelle.
  - Vor jeder Rechnung prüft der Nutzer 50 zufällige Bilder gegen die Tabelle. Ziel: höchstens
    5 % Lesefehler bei den Leveln.
  - Nachfass-Anweisungen (Stufe 2) aus dem Text, Zuordnung zum Call über Symbol und Zeit.
  - Kurse: Dukascopy M1 für FX, Gold, Silber, US500, NAS100, US30. Kosten je Instrument aus
    den bestehenden Kostenmodellen. G8-Ampel aus `fusion_lab/g8`.
  - Offen: Weichen Dennis' Chartquellen (OANDA, FXCM, Capital.com, CMC) bei Indizes spürbar
    von Dukascopy ab? Stichprobe vorab.
- **Zeitraum und Sperre**:
  - Stufe 1 und 2 haben keine freien Parameter. Wir rechnen einmal über den ganzen Zeitraum
    und zeigen 2025 und 2026 getrennt (Regime).
  - Die 20 Varianten (2 bei Typ A, 18 bei Typ B) werden vor dem Test registriert und mit
    `log_trials` gezählt. Ausgewiesen werden alle, mit Deflated Sharpe.
  - Stufe 3 (eigene Optimierung, G8-Veto): 19 Monate reichen nicht für einen Tresor von
    12 Monaten. **Vorschlag**: IS bis 31.03.2026, OOS 04–10/2026, als Tresor-Ersatz einen
    Forward-Test ab dem Einfrieren (täglicher Import). Das weicht von der Regel ab und braucht
    deine Entscheidung.
- **Fallzahl**: Aus der Tabelle ergibt sich, welche Bilder Calls sind, nicht aus Auswahl von
  Hand. Ziel sind mindestens 100 ausgelöste Trades je Variante, sonst wird die Variante nur
  beschrieben und nicht bewertet.
- **Erfolgskriterium (vorab festgelegt)**: Ø R nach Kosten > 0 mit t > 2 in Stufe 1. Dazu
  dürfen die Gegenproben „Richtung“ und „Regime“ nicht greifen.
- **Kontrollgruppen**, direkt aus Feld 04:
  1. gespiegelte Richtung,
  2. Trendfilter statt Dennis' Richtung,
  3. Markt- oder Zufallseinstieg statt Zone,
  4. mit gegen ohne Fair-Value-Lücke,
  5. USD-Richtung und 2025 gegen 2026,
  6. BOS-Einstieg gegen statischen Einstieg (A2/A1, B2/B1) beim Anteil glatt durchlaufener
     Zonen,
  7. Monatskorrelation mit dem geprüften Konto.

Noch keine Ergebnisse.

## Probelauf Stufe 1 (16.07.–16.10.2026, gerechnet 21.10.)

Vorläufig, kleine Fallzahl: keine Variante erreicht 100 Trades, also nichts bewertet.
Code `fusion_lab/copy_trading/`, Ergebnisse `fusion_lab/data/copy_trading/results/`.

- **Auslesung**: 639 Chartbilder (ohne Link-Vorschauen) → 392 Calls / 424 Setups (60 Typ A,
  ~135 Typ B in den ersten 280, Rest analog). Ratenlimit des Abos nach ~25 Min. Dauerlauf,
  Skript wartet seitdem 5/10/20 Min. 5 bekannte Bilder von Hand geprüft: fehlerfrei.
  Nutzer-Stichprobe (50 Bilder, `stichprobe.html`) steht aus.
- **Feeds**: Chart-Schlusskurs gegen Dukascopy, Median-Abweichung < 0,01 % bei allen
  Instrumenten inkl. Indizes; nur USOIL teils > 0,3 %.
- **Verworfen**: 26 Setups nach Regel 3 (Entry/Zone schon vor dem Post erreicht), 9 nicht
  handelbare Symbole, 14 Lesefehler/fehlende Level. 375 simuliert.
- **Typ A (Dennis' exakte Level)**: nur 33 von 133 Trade-Ideen werden gefüllt, bevor das nächste
  Update kommt. A1: 35 Trades, Treffer 31 %, Ø −0,27 R netto (t −1,3), 6 noch offen.
  A2 (BOS): 30 Trades, Ø −0,24 R.
- **Typ B**: bestes Ø R hat B1 SLc/TPa (2× ATR, 2R) mit +0,18 R (t 1,0, n 66). SL (b) am
  nächsten HTF-Tief ist netto stark negativ, weil der Stop oft sehr nah liegt und die Kosten
  in R explodieren (ein Viertel > 0,77 R Kosten). TP (b) Pfadende trifft selten (6–10 %).
- **Reaktionszeit 60 statt 5 Min.**: praktisch dasselbe Bild.
- **Auffällig, noch offen**:
  1. Ein bereits laufender Trade, den Dennis am nächsten Abend neu postet, wird als neuer Call
     gezählt (US30 6141/6158). Karte sagt nur „neuer Call ersetzt alten“.
  2. Die geringe Füllquote bei Typ A: Gültigkeit „bis zum nächsten Update“ schneidet viele
     Limits ab. Eine längere Gültigkeit wäre eine neue, gezählte Variante.

## Entscheidungen 21.10. + Stufe 3 (Ausstiege)

- SL vor Einstieg: betrifft nur den BOS-Einstieg (Kurs berührt Zone, läuft vor dem doppelten
  BOS durch die Invalidierung → kein Trade). Beim Limit unmöglich (Nutzerfrage geklärt). In
  Stufe 3 gilt als Invalidierung die Struktur (A: SL-Label, B: ferner Zonenrand).
- 30-Min.-Fenster für Regel 3 ohne Chartzeit: bestätigt (Zeit steht meist im Bild).
- Repost eines laufenden Trades: **kein neuer Call**, höchstens Re-Entry (nach Schluss des
  früheren Trades). Gleiches Level = innerhalb 0,15 %.
- Gültigkeit zusätzlich 1, 2, 3, 5 Handelstage testen (neben „bis zum nächsten Update“).
- Nutzerauftrag: auf Basis von Trade-Idee und Bias SL-, TP-, BE- und Trailing-Varianten testen.
  Umsetzung `fusion_lab/copy_trading/grid.py` + `exits.py`, **nur IS** (Calls bis 31.03.2026),
  schrittweise je Einstiegstyp (A1/A2/B1/B2): Gültigkeit (5) → SL (Struktur, Swing, 1/1,5/2×ATR)
  → TP (Struktur, 1/2/3R, ohne) → BE (aus, +0,5R, +1R) → Trailing (aus, 1,5×/2,5×ATR ab +1R,
  Swing). 22 Versuche je Typ, 88 gesamt, alle im Lock gezählt; Auswahl nach t-Wert, mind.
  30 Trades. Danach einfrieren, Deflated Sharpe, OOS einmal öffnen.
- Ehrlich vermerkt: Der Probelauf (Stufe 1, 20 Varianten) lag im OOS-Zeitraum. Einige
  Raster-Punkte decken sich mit dort gesehenen Varianten (z. B. 2×ATR + 2R war im Probelauf
  vorn). Das OOS ist für Stufe 3 also nicht völlig unberührt; Auswahl trotzdem nur auf IS,
  festes Suchschema vor dem ersten Lauf.
- Trades ohne Ausstieg werden nach 90 Tagen bewertet (ANNAHME).

## Nutzer-Stichprobe 21.10. + Anweisung v2/v3

- 50 zufällige Calls aus dem Probezeitraum: **41 stimmen, 9 falsch (18 %)**. In die Trades
  gelangten davon 2 (5744: neue Long-Zone nicht erkannt, 15 falsche Trades; 6716: „Buy Stop
  über 4200 oder Buy Limit 4143“ als Zone 4170–4177 gelesen, 12 falsche Trades). Der Rest fiel
  über Regel 3, Symbol oder fehlende Füllung heraus.
- Fehlerarten: aktiver Trade als neuer Call, Info-Chart, Richtung beim Positionswerkzeug
  vertauscht (5814), Zielzone als Einstieg (6099), Stop-Order-Alternativen.
- Kern-Befund: Bei Watch-Charts liest der Nutzer die Zone oft als **Ziel** des laufenden Trades
  (6312 „Short aktiv bis 1,159“), die Karte las sie als Einstieg. Nutzerentscheid: **beide
  Lesarten testen** (Ergänzung in der finalen Karte).
- Anweisung v3 (`extract.py`, `PROMPT_VERSION = 3`): Status je Setup (neu/aktiv/Info),
  Ordertyp, Alternativ-Gruppe, Richtung beim Positionswerkzeug nur aus den Farben, bei
  Watch-Charts nur Objektives (erster Schenkel, Umkehrpunkt, Pfadende). Test an den 9 Bildern:
  5814, 6019, 6626 jetzt richtig, 6312 liefert beide Lesarten; zusätzliche Einstiege (5744,
  5791) werden weiter übersehen (fehlende Calls, keine falschen Trades); 6716 bleibt mehrdeutig.
- Alle Bilder (17.03.2025–16.10.2026) werden mit v3 neu gelesen, damit IS und OOS gleich
  gelesen sind. Raster um Einstiegstyp P1 (Pfad-Trade) erweitert: 16 weitere Versuche.

## Stufe 3 IS-Raster (gerechnet 26.10., nur Calls 17.03.2025–31.03.2026)

2.784 IS-Setups (Anweisung v3), 104 Raster-Versuche, Lock jetzt 124 Versuche. Ergebnisse
`fusion_lab/data/copy_trading/results/stufe3_is_*`. **Nichts eingefroren, OOS nicht geöffnet.**

- **Scheinbare Gewinner sind ein Artefakt**: Die „besten“ Konfigurationen haben fast alle
  TP „ohne“ (A1 Ø +1,08 R, B1 +1,22 R, B2 mit BE 1R +1,74 R, t 2,9) bei 5–12 % Gewinnern.
  Das Plus stammt aus Trades ohne SL/TP, die erst nach der angenommenen Höchstdauer von 90
  Tagen bewertet werden: Gold-/Silber-/US500-Longs 2025 mit sehr engem ATR-Stop (Einzeltrade
  bis +181 R). Ohne die 5 größten Gewinner: A1 −0,20 R, B1 −0,32 R; Median ≈ −1 R.
  Ohne offene Trades: A1 ΣR −162, B1 −328, B2 −94.
- **Gegenprobe „Regime statt Können“ greift**: Longs +, Shorts − (A1 Shorts Ø −0,71 R,
  B1 −1,13 R); Plus nur 2025, Jan–Mär 2026 ≈ 0 bzw. negativ.
- **Mit begrenztem Ziel** (Label-TP, 1/2/3R) bestes Ergebnis A1 (Label-TP, SL 2× ATR)
  +0,32 R, t 1,6 und A2 (BOS, SL 1× ATR, Label-TP) +0,44 R, t 1,4; beide nicht signifikant,
  nach 124 Versuchen Deflated Sharpe nahe 0. A2 ist das sauberste: Long und Short positiv,
  ohne offene Trades unverändert.
- **Pfad-Trade (P1, Zone als Ziel)**: durchgehend negativ (n ≈ 700, 1R-TP t −2,2, Swing-SL
  t −8). Die Lesart „Trade läuft in die Zone“ trägt nicht.
- Gültigkeit 1–5 Tage statt „bis Update“: kein Unterschied.
- Break-even und Trailing verschlechtern fast überall.

## Eingefroren + OOS (27.10., Nutzerentscheid)

- Eingefroren: A2 = BOS-Einstieg, SL 1× ATR, Dennis' TP-Label, Gültigkeit bis zum nächsten
  Update, ohne BE/Trailing (Hash 71a02c43…). Code `fusion_lab/copy_trading/oos.py`.
- IS: 142 Trades, Ø +0,47 R, t 1,44, Treffer 20 %, Median −1,05 R; die 5 größten Gewinner
  (+69,6 R) tragen mehr als die Summe (+66,9 R). **Deflated Sharpe 0,09** (124 Versuche).
- **OOS 01.04.–16.10.2026 (einmalig geöffnet): 70 Trades, Ø −0,72 R, t −3,65, ΣR −50,6,
  Treffer 6 %.** Long −0,60 R, Short −0,91 R, keine offenen Trades.
- Urteil: Copy-Trading der Calls ist mit den getesteten Regeln **kein Edge**; das IS-Plus war
  Ausreißer/Regime (Metall-Rallye 2025). Passt zu Dennis' eigenem Kontobericht (2026 schwach).
- Offen bleibt nur Stufe 2 (Dennis' Nachfass-Anweisungen) als ungetestete Hypothese; die
  Forward-Stufe der Sperre ist für A2 ohne Sinn. Täglicher Import läuft weiter (Daten für den
  Makro-Agenten und mögliche spätere Prüfung).

## Stufe 2: Dennis' Anweisungen (28.10., Nutzerentscheid)

Basis ist A2 nackt gegen A2 mit Anweisungen, auf denselben Trades. Es gibt zwei Varianten:
„fest“ setzt nur verbindliche Anweisungen um, „alle“ auch weiche (könnte, bei Bedarf,
bedingt „closen wenn …“). Code: `fusion_lab/copy_trading/instructions.py` (Lesung,
`PROMPT_VERSION = 2`) und `stage2.py`. Die Sperre `copy_trading_stufe2_20261028` hat
2 Versuche, das OOS ist gesperrt (schon durch A2 verbraucht). Forward läuft vom 17.10.2026
bis 31.03.2027 mit min. 100 Trades, darunter wird nur beschrieben. Eingefroren ist Hash
6c6ce4d1….

- **Lesung:** 410 Kandidaten-Nachrichten (IS und Forward, OOS-Fenster nicht gelesen). Daraus
  234 Anweisungen im IS: BE 162, Teilschluss 42, Close 25, Invalide 5, Re-Entry-Hinweis 8.
  199 sind fest, 16 ohne Symbol. Die Nutzer-Stichprobe ergab 20/20 richtig. Die Grenzfälle
  wurden in v2 geregelt: bedingte Anweisungen gelten als weich, Rückblicke wie „ich hoffe,
  ihr habt BE gezogen“ zählen nicht.
- **Ergebnis IS-Vorab (beschreibend):**

  | Variante | Trades | Ø R | t |
  |---|---|---|---|
  | nackt | 142 | +0,47 | 1,44 |
  | fest | 142 | +0,08 | 0,34 |
  | alle | 142 | −0,04 | −0,15 |

  - **fest:** 28 Trades verändert, ΣΔ −55 R, Median Δ +0,94 R.
  - **Gewinner/Verlierer:** Bei 17 Verlierern wurde BE gezogen, statt voll in den SL zu laufen
    (+19,6 R). Dafür verloren 11 TP-Gewinner ihr Plus (−74,7 R): 24 R, 12 R, 8 R wurden zu
    BE/Teil.
- **Lesart:** Dennis' Management verbessert den typischen Trade, kappt aber die wenigen großen
  Gewinner, von denen A2 lebt. Bei A2s engem 1×-ATR-Stop ist ein Ziel von 10–20 R üblich,
  während Dennis' Trade schon früher „in Profit“ ist. Insgesamt rettet Stufe 2 den Call-Copy
  nicht. Die Entscheidung fällt vorwärts.
- **Annahmen:**
  - BE unter Entry = schließen zum Kurs.
  - Teilschluss ohne Anteil = 50 %.
  - Zeitbezug: heute ≤ 24 h, gestern 6 h–4 Tage, letzte Woche 2–14 Tage, ohne Angabe
    ≤ 30 Tage.
  - Invalide streicht nur wartende Orders.
- **Täglicher Lauf (23:00):** Import → neue Bilder → neue Anweisungen → `stage2 --forward`. Das
  schreibt `results/forward_stufe2_trades.csv` und `forward_stufe2_stand.json`. R-Zahlen
  werden erst am Stichtag angeschaut. Erster Stand 28.10.: 6 Trades, davon 5 geschlossen,
  4 Anweisungen zugeordnet.

