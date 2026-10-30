EDGE CARD

FX, Metalle, US-Indizes / Copy Trading der Calls aus „SMH Daily Update“

Fertiggestellt am 20.10.2026 mit dem Nutzer nach [[edge-card-workflow]]. Den Verlauf, die Entwürfe und den Datenbestand enthält [[copy-trading-dennis-edge-card]]. Dachprojekt: [[quant-diskretionaer-fusion]].

Vollständige Ausgangsthese

01 IDEE

Wir glauben beobachtet zu haben: Die Calls aus der Telegram-Gruppe „SMH Daily Update“ laufen häufiger in die angekündigte Richtung, als es der Zufall hergibt. Der Abstand ist so groß, dass auch ein Nachahmer nach Kosten im Plus bleibt. Dabei steigt der Nachahmer mit Verzögerung ein, zahlt Spread und hat nicht Dennis' Urteil im laufenden Trade.

Ausgangszustand: Meist abends zwischen 20 und 22 Uhr markiert Dennis je Markt eine Zone (POI) oder einen fertigen Trade für die nächsten Tage. Die Richtung kommt aus seiner Makro-Lage (Dollar, Zinsen, Öl, Daily Closes), die Zone begründet er meist mit Fair Value. Die Charts sind in der Regel HTF (H1/H4).

Ohne diese Information würde der Kurs an einer beliebigen markierten Zone etwa so oft mit wie gegen die Richtung reagieren. Ein eigener Befund zeigt sogar, dass bekannte Key Levels eher schlechter halten als Schein-Level.

Die Beobachtung: Der Kurs erreicht die markierte Zone und dreht dort in die angekündigte Richtung. Die Information steckt im Paar aus Zone und Richtung.

Nicht widerlegt ist die Idee, wenn die Zone nicht erreicht wird (dann gibt es keinen Trade), wenn die Reaktion schwach ausfällt oder wenn der Kurs kurz in die Zone hineinläuft, ohne den SL zu treffen. Widerlegt ist ein Call, wenn der SL erreicht wird, Dennis „invalide“ schreibt oder Makro und News das Bild drehen.

Ebenen: Der HTF ist Dennis' These, sichtbar im Timeframe des geposteten Charts. Der LTF ist nur die Bestätigung auf M5.

Offen, und das sollen die Gegenproben trennen: Kommt ein Vorteil aus der Richtung (Makro) oder aus der Wahl der Zone (Fair Value)?

02 REGEL

Calls erkennen
1. Quelle sind alle Nachrichten der Gruppe mit Chartbild (jpg/png), egal welcher Absender. Maßgeblich ist die Telegram-Postzeit (UTC).
2. Eine Bild-KI liest je Bild Symbol, Chart-Timeframe, Typ, Richtung und Level aus.
   - Typ A „Trade Idee“: Positionswerkzeug mit Entry-, SL- und TP-Beschriftung an der Preisachse.
   - Typ B „Watch“: Zone mit gemaltem Pfad oder Pfeil, der die Richtung zeigt. Bei Typ B wird auch das Pfadende gelesen.
   - Kein Call: DXY und andere nicht handelbare Werte sowie Bilder ohne Zone oder Werkzeug.
3. Ein Bild zählt nur als Call, wenn Werkzeug oder Zone rechts über die letzte Kerze hinausragt und der Kurs Entry bzw. Zone beim Posting noch nicht erreicht hatte. So fallen Gewinner-Nachposts heraus.

Gültigkeit
4. Ein Update ist eine Serie von Chartposts desselben Absenders mit höchstens 60 Minuten Abstand.
5. Die Order ist 5 Minuten nach der Postzeit aktiv. Als Robustheitsprobe wird zusätzlich mit 60 Minuten gerechnet.
6. Eine noch nicht ausgelöste Order gilt bis zum ersten dieser Ereignisse: Beginn des nächsten Updates desselben Absenders, ein neuer Call zum selben Symbol (der neue ersetzt den alten) oder ab Stufe 2 eine Nachricht mit „invalide“ zu diesem Symbol.
7. Ein ausgelöster Trade läuft bis SL oder TP, unabhängig von späteren Updates.

Timeframes
8. Zone, HTF-Hochs und -Tiefs, ATR14 und Kerzenschlüsse werden immer im Timeframe des jeweiligen Chartbilds bestimmt (meist H1/H4). Die Bestätigung läuft auf M5. M1-Daten dienen nur dazu festzustellen, ob innerhalb einer HTF-Kerze zuerst der SL oder zuerst das TP erreicht wurde. Liefert auch M1 keine Reihenfolge, gilt der SL.

Einstieg (je Typ zwei Varianten)
9. Statisch: Typ A als Limit am Entry-Label (A1), Typ B als Limit in der Zonenmitte (B1). Ist der Limit bei Aktivierung sofort ausführbar, wird zum aktuellen Kurs gefüllt.
10. Mit Bestätigung (A2, B2): Der Kurs berührt das Entry-Label bzw. die Zone. Danach entsteht auf M5 ein doppelter BOS in Call-Richtung. Beim Long schließt eine M5-Kerze über einem Swing-High, danach schließt eine Kerze über dem nächsten neu gebildeten Swing-High. Beim Short gilt das spiegelbildlich mit Swing-Lows. Ein Swing ist ein Fraktal mit je 2 Kerzen links und rechts. Es zählen nur Swings, die sich nach der ersten Berührung bilden. Eingestiegen wird zum Schlusskurs der Kerze, die den zweiten BOS abschließt. Kommt die Bestätigung nicht, solange die Order gilt, gibt es keinen Trade.

Stop und Ziel
11. Typ A: SL und TP 1:1 aus den Labels.
12. Typ B, SL je Variante: (a) am gegenüberliegenden Zonenrand, (b) am nächsten HTF-Low (Long) bzw. HTF-High (Short) jenseits des Entrys, (c) 2× ATR14 vom Entry.
13. Typ B, TP je Variante: (a) 2R, (b) Ende des gemalten Pfads, (c) nächstes HTF-High (Long) bzw. HTF-Low (Short).
14. Daraus ergeben sich 20 vorab festgelegte Varianten: Typ A mit 2 Einstiegen, Typ B mit 2 Einstiegen × 3 SL × 3 TP.
15. Gemessen wird in R, nach Spread und Kommission je Instrument.

Stufen
16. Stufe 1: nackt, wie oben beschrieben.
17. Stufe 2: Zusätzlich gelten Dennis' Nachfass-Anweisungen ab ihrer Postzeit plus 5 Minuten. Bei „BE ziehen“ wandert der SL auf den Entry. Bei „close“ wird zum Kurs geschlossen. Verlangt Dennis bei korrelierten Calls geteiltes Risiko (z. B. US30, NAS100, US500 je 1/3), wird das Risiko geteilt. Bei „invalide“ wird die offene Order gestrichen.
18. Stufe 3: eigene Optimierung und Makro-Veto. Zeigt die G8-Ampel zum Aktivierungszeitpunkt Rot, gibt es keinen Einstieg. Was „Rot“ heißt, wird vor dem IS-Test festgelegt. Der Makro-Agent kommt erst im Forward-Test dazu, weil er die Vergangenheit kennt.

Merksatz: Kopiert wird nur, was zum Postzeitpunkt noch vor uns lag, mit den Leveln aus dem Bild, auf dem Timeframe des Bilds und ohne Nachhilfe aus dem späteren Verlauf.

03 MECHANISMUS

1. Richtung aus der Makro-Lage (HTF): Dennis leitet die Richtung aus Dollar, Zinsen, Öl und Daily Closes ab. Unsere Hypothese ist, dass Makro-Information langsam in die Kurse fließt, über Tage bis Wochen. Wer diesem Fluss folgt, steht öfter auf der Seite des Trends als jemand, der zufällig handelt. Aus der Literatur ist das als Zeitreihen-Momentum und Carry bei Währungen bekannt. Offen ist, ob Dennis' Makro-Lesart mehr leistet als ein einfacher Trendfilter.
2. Fair-Value-Zone im Rücksetzer (HTF): Die Zone liegt gegen die Richtung, also im Rücksetzer. Der Kurs kehrt in einen Bereich zurück, den er zuvor einseitig und schnell verlassen hat. Unsere Hypothese: Dort nehmen Trend-Trader nach. Wer den Rücksetzer als Wende gehandelt hat, liegt falsch und muss schließen. Dieses Schließen treibt den Kurs in Call-Richtung. Die Zone verbessert vor allem das Chance-Risiko-Verhältnis, weniger die Trefferquote.
3. Bestätigung (LTF M5): Zwei BOS in Call-Richtung zeigen, dass der Rücksetzer auf M5 vorbei ist. Unsere Hypothese: Erst hier werden die Rücksetzer-Trader sichtbar aus dem Markt genommen. Der Preis dafür ist ein schlechterer Entry. Im Gegenzug fallen Trades weg, bei denen der Kurs glatt durch die Zone läuft.
4. Was der Nachahmer nicht bekommt: Dennis' Urteil im laufenden Trade (BE, Teilschluss, Re-Entry) und seine Auswahl, welche Calls er selbst handelt. Unsere Hypothese: Ein Teil seines Kontoergebnisses steckt genau dort. Deshalb werden Stufe 1 und Stufe 2 getrennt gerechnet.
5. Ausdrücklich nicht angenommen wird ein selbsterfüllender Effekt. Rund 1.300 Kursteilnehmer bewegen FX-Majors, Gold und US-Indizes nicht nennenswert.

Kette: Makro-Fluss gibt die HTF-Richtung vor → Rücksetzer in die Fair-Value-Zone → Gegentrend-Trader steigen ein → Trend-Trader nehmen nach → Gegentrend-Trader müssen schließen → Bewegung in Call-Richtung.

Wichtig: Das ist eine Mechanismus-Hypothese. Wir behaupten noch nicht, dass sie bewiesen ist.

04 GEGENPROBE

• Richtung: Dieselben Calls mit gespiegelter Richtung schneiden nach Kosten nicht schlechter ab. Dann trägt Dennis' Richtung keine Information.
• Makro gegen simplen Trend: Ein einfacher Trendfilter (Kurs über/unter dem 50-Tage-Schnitt) liefert an denselben Zonen dasselbe Ergebnis. Dann leistet die Makro-Lesart nichts über Momentum hinaus.
• Zone gegen beliebiges Level: Bei gleicher Richtung bringt ein Einstieg zum Marktkurs bei Aktivierung oder an einem zufälligen Level mit gleichem Abstand dasselbe Ø R. Dann enthält die Zonenwahl keine Information.
• Fair Value: Zonen, die mit einer objektiven Fair-Value-Lücke im Chart-Timeframe zusammenfallen, schneiden nicht besser ab als Zonen ohne eine solche Lücke. Dann trägt diese Erklärung nicht.
• Regime statt Können: Das Ergebnis stammt fast nur aus USD-Short-Calls in Phasen, in denen der Dollar fiel (H1 2025), und verschwindet 2026. Dann ist es Regime-Beta und kein wiederholbarer Vorteil. Dennis' geprüftes Konto zeigt 2026 nur +19 %, Mai bis Juli jeweils im Minus.
• Bestätigung: Der BOS-Einstieg (A2/B2) senkt den Anteil der Trades, bei denen der Kurs glatt durch Zone oder Entry läuft, nicht gegenüber dem statischen Einstieg (A1/B1). Dann ist die Annahme falsch, dass dort Gegentrend-Trader aus dem Markt genommen werden.
• Calls gegen Konto: Die Monatsergebnisse der kopierten Calls hängen nicht mit Dennis' geprüften Monatsrenditen zusammen. Dann bilden die Calls nicht sein echtes Trading ab, und der Kontobericht ist kein Beleg für die Calls.

Kern: Eine gute Gegenprobe greift nicht nur die Performance an. Sie greift die angenommene Ursache an.

05 TEST

Datenquelle: Calls sind alle Chartbilder der Gruppe vom 17.03.2025 bis zum Testtag. Eine Bild-KI überträgt sie in eine Tabelle. Bevor gerechnet wird, prüft der Nutzer 50 zufällige Bilder gegen die Tabelle; das Ziel sind höchstens 5 % Lesefehler bei den Leveln. Die Nachfass-Anweisungen kommen aus dem Text und werden dem Call über Symbol und Zeit zugeordnet. Kurse: Dukascopy, aggregiert auf den Chart-Timeframe, M5 für die Bestätigung, M1 nur für die Reihenfolge. Kosten je Instrument aus den bestehenden Kostenmodellen. Die G8-Ampel kommt aus fusion_lab/g8. Noch unbekannt: ob Dennis' Chartquellen (OANDA, FXCM, Capital.com, CMC) bei Indizes spürbar von Dukascopy abweichen. Das wird vor dem Test per Stichprobe geprüft.

Zeitraum und Sperre: Stufe 1 und 2 haben keine freien Parameter. Gerechnet wird einmal über den ganzen Zeitraum, 2025 und 2026 werden getrennt ausgewiesen. Alle 20 Varianten werden vorab registriert und gezählt, die Deflated Sharpe wird ausgewiesen. Für Stufe 3 gilt der Split IS bis 31.03.2026 und OOS April bis Oktober 2026. Statt eines Tresors folgt ab dem Einfrieren ein Forward-Test über den täglichen Import. Das ist eine bewusste Abweichung von der Overfitting-Sperre: 19 Monate reichen nicht für einen Tresor von 12 Monaten, und es handelt sich um einen speziellen Backtest (Nutzerentscheid 20.10.).

Fallzahl: Was ein Call ist, ergibt sich aus der Tabelle und Regel 3, nicht aus einer Auswahl von Hand. Eine Variante wird nur bewertet, wenn sie mindestens 100 ausgelöste Trades hat. Sonst wird sie nur beschrieben.

Erfolgskriterium (vorab festgelegt): Stufe 1 hat nach Kosten ein Ø R über 0 mit t > 2, und die Gegenproben „Richtung“ und „Regime“ greifen nicht.

Vergleich: Original gegen gespiegelte Richtung. Dennis' Richtung gegen Trendfilter an denselben Zonen. Zone gegen Markt- bzw. Zufallseinstieg. Zonen mit gegen ohne Fair-Value-Lücke. USD-Short gegen übrige Calls, 2025 gegen 2026. BOS-Einstieg gegen statischen Einstieg beim Anteil glatt durchlaufener Zonen. Monatsergebnis der Calls gegen Dennis' geprüfte Monatsrenditen.

Noch keine Ergebnisse.

Ergänzung 21.10.2026 (Nutzerentscheid nach der Bild-Stichprobe)

Die Nutzer-Stichprobe zeigte: Bei Watch-Charts ist die Zone nicht immer der Einstieg. Oft ist sie das Ziel des laufenden Trades, und die Umkehr kommt erst danach (z. B. „Short aktiv bis 1,159“). Watch-Charts werden deshalb in zwei Lesarten getestet. Die Bild-KI liest nur, was gezeichnet ist: Richtung des ersten Pfadschenkels, Umkehrpunkt, Pfadende, Zone.

Lesart 1, Pfad-Trade (P): Einstieg zum Marktpreis bei Aktivierung in Richtung des ersten Schenkels. Ziel ist der Umkehrpunkt, sonst der nahe Zonenrand, sonst das Pfadende. Nur gültig, wenn das Ziel beim Posten noch vor dem Kurs lag und noch nicht erreicht war.

Lesart 2, Zonen-Trade (B, wie Regel 9–13): Umkehr in der Zone in Richtung des letzten Schenkels. Die Zone gilt nur, wenn der Umkehrpunkt in ihr liegt (Toleranz ein Viertel der Zonenbreite), sonst Limit am Umkehrpunkt. Die Zone muss auf der Rücksetzer-Seite des Kurses liegen.

Außerdem: Setups, die bereits aktiv oder nur Info sind, sind keine Calls. Stop-Orders („Buy Stop über …“) gehören nicht zur Karte und werden nur gezählt. Ein erneut geposteter, noch laufender Trade ist kein neuer Call, nach seinem Schluss höchstens Re-Entry.

Ergänzung 28.10.2026 (Stufe 2, Nutzerentscheid)

Regel 17 wird so umgesetzt: Gemessen wird A2 nackt gegen A2 mit Anweisungen auf denselben Trades. Die Variante „fest“ nimmt nur verbindliche Anweisungen, die Variante „alle“ auch weiche. Weich ist, was optional formuliert ist („könnte“, „bei Bedarf“) oder an eine künftige Bedingung geknüpft ist („closen wenn 1h Close > …“). Rückblicke („ich hoffe, ihr habt BE gezogen“) sind keine Anweisung. Steht der Kurs bei „BE ziehen“ unter dem Entry, wird geschlossen. Ein Teilschluss ohne Anteil gilt als 50 %. Weil das OOS schon durch A2 verbraucht ist, wird Stufe 2 nur auf IS beschreibend und vorwärts gemessen (17.10.2026–31.03.2027).

Ergebnis: Eine vollständige, falsifizierbare und testbare Ausgangsthese.
