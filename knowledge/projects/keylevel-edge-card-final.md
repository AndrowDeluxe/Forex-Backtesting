EDGE CARD

FX-Majors und -Crosses / Key Levels: Umkehr oder Durchlauf

Fertiggestellt am 16.10.2026 mit dem Nutzer nach [[edge-card-workflow]].
Den Verlauf und die Entwürfe enthält [[keylevel-edge-card]]. Der Befund,
von dem die Karte ausgeht, steht in [[smh-elite-mikrostruktur]].

Vollständige Ausgangsthese

01 IDEE

Bestimmte Kursmarken sind für sehr viele Marktteilnehmer gleichzeitig sichtbar und werden im Trading ausdrücklich als Orientierung benutzt. Das sind runde Zahlen (x.xx00), halbe Zahlen (x.xx50), das Open von D1- und H4-Engulfing-Kerzen, Hoch und Tief der Vorwoche, Hoch und Tief der zuletzt abgeschlossenen Session sowie klassische Pivot-Punkte aus Tag, Woche und Monat. Läuft der Kurs frisch auf eine solche Marke zu, ist das Verhältnis „zuerst eine Reaktionsgröße zurück“ gegen „zuerst eine Reaktionsgröße weiter“ nicht ausgeglichen. An einem beliebigen Kurs im gleichen Abstand wäre es das.

Für runde Zahlen auf EURUSD, GBPUSD, USDJPY und AUDUSD ist bereits gemessen, dass sie seltener halten als beliebige Kurse. Sie wirken wie ein Magnet, nicht wie eine Wand. Beim Engulfing-Open erwarten wir das Gegenteil: Das Level hält in Engulfing-Richtung. An Vorwochen- und Session-Hochs und -Tiefs sind je nach Kontext zwei Verläufe möglich, Sweep und Umkehr oder Durchbruch und Retest. Welcher Verlauf eintritt, soll vom Kontext abhängen: HTF-Struktur, Art des Anlaufs, Zusammentreffen mehrerer Level und Volumen am Level. In Phasen mit News, Makro-Schocks oder sehr hoher Volatilität werden Level dagegen oft ignoriert und einfach durchlaufen.

Die Level stammen aus höheren Zeiteinheiten (Tag, Woche, Monat, Session). Die Reaktion wird auf mehreren Ebenen beobachtet: auf M1 als Berührung, auf M15, H1 und H4 als Kerzenschluss am Level. Die Reaktionsgrößen reichen von 10 bis 100 Pips.

Ein kurzes Überschießen über das Level widerlegt die Idee nicht, solange die Gegenschwelle nicht erreicht ist. Widerlegt ist sie, wenn sich alle Level-Typen über alle Reaktionsgrößen verhalten wie beliebige Kurse im gleichen Abstand.

02 REGEL

Level
1. Runde Zahl: jedes Vielfache von 0,0100 (bei JPY-Paaren 1,00). Sie gilt immer.
2. Halbe Zahl: jedes Vielfache von 0,0050, das kein Vielfaches von 0,0100 ist (bei JPY-Paaren x,50). Sie gilt immer.
3. Engulfing-Open (D1 und H4): Die Vorkerze läuft in Gegenrichtung. Die direkt folgende Kerze schließt jenseits des Opens der Vorkerze, Körper umschließt also Körper. Das Level ist das Open der Engulfing-Kerze. Es gilt ab ihrem Schluss bis zur ersten Berührung, höchstens 5 Kerzen des Engulfing-Timeframes.
4. Vorwochenhoch und -tief: Eine Woche läuft von Sonntag 17:00 bis Freitag 17:00 New York. Hoch und Tief der zuletzt abgeschlossenen Woche gelten die ganze Folgewoche.
5. Session-Hoch und -Tief: Asia 00:00–08:00, London 08:00–13:00, New York 13:00–21:00 UTC. Hoch und Tief der zuletzt abgeschlossenen Session gelten 24 Stunden ab Sessionende.
6. HTF-Pivots: P = (H + L + C) / 3, R1 = 2P − L, S1 = 2P − H, R2 = P + (H − L), S2 = P − (H − L). Sie werden aus der Vortages-, Vorwochen- und Vormonatskerze berechnet (Tagesgrenze 17:00 New York) und gelten für den ganzen Folgezeitraum.
7. Fallen Level verschiedener Typen zusammen, wird der Fall bei jedem Typ gezählt und als Konfluenz markiert.

Frischer Anlauf
8. Seit das Level gilt, war der Kurs mindestens eine Reaktionsgröße G vom Level entfernt, und zwar auf der Seite, von der er jetzt anläuft. Bei runden und halben Zahlen zählt der Abstand seit der letzten Berührung.
9. Je Level, Ereignistyp und Reaktionsgröße zählt nur das erste Ereignis.

Ereignis
10. M1 (Berührung): Bei Anlauf von unten erreicht das Bid-Hoch das Level, bei Anlauf von oben das Bid-Tief. Die Messung startet am Level-Preis. Gemessen wird Umkehr gegen Durchlauf, ohne Signalrichtung.
11. M15, H1, H4 (Kerzenschluss): Eine Kerze erreicht das Level, und die Vorkerze schloss auf der Anlaufseite. Schließt die Kerze wieder auf der Anlaufseite, ist das Level respektiert (Sweep), und das Signal zeigt gegen den Anlauf. Schließt sie jenseits des Levels, ist es gebrochen, und das Signal zeigt mit dem Anlauf. Die Messung startet am Schlusskurs der Signalkerze.
12. Durchbruch und Retest: Nach einem Schluss jenseits des Levels entfernt sich der Kurs mindestens G vom Level. Innerhalb von 5 Kerzen des Signal-Timeframes kehrt er erstmals von der neuen Seite zum Level zurück. Die Retest-Kerze berührt das Level und schließt auf der Durchbruchseite. Das Signal zeigt in Durchbruchrichtung, die Messung startet am Schlusskurs.
13. Beim Engulfing-Open zählt „respektiert in Engulfing-Richtung“ als Treffer. D1-Engulfings werden mit den Kombinationen von H1 und H4 gemessen, H4-Engulfings mit denen von M15 und H1.

Messung
14. Ab dem Startpreis wird minutengenau verfolgt. Erreicht der Kurs zuerst +G in Signal- bzw. Umkehrrichtung, ist das ein Treffer. Erreicht er zuerst −G, ist das ein Fehlschlag. Passiert bis zum Fensterende keins von beiden, gilt der Fall als unentschieden und wird mit dem Schlusskurs am Fensterende bewertet. Werden +G und −G in derselben M1-Kerze erreicht, zählt der Fall als Fehlschlag.
15. Kombinationen:
    - M1 mit G = 10 oder 20 Pips, Fenster 1 Tag
    - M15 mit 20 oder 30 Pips, Fenster 2 Tage
    - H1 mit 30 oder 50 Pips, Fenster 5 Tage
    - H4 mit 50 oder 100 Pips, Fenster 10 Tage

Kontext (Stufe 2, je Faktor einzeln, Richtung vorab festgelegt)
16. HTF-Struktur: Der Anlauf läuft mit oder gegen die D1/W1-Struktur. Erwartung: gegen die Struktur eher Sweep und Umkehr, mit der Struktur eher Durchbruch und Retest.
17. Art des Anlaufs: impulsiv oder auslaufend. Erwartung: impulsiv eher Durchbruch, auslaufend eher Sweep.
18. Konfluenz: Das Level fällt mit einem Level eines anderen Typs zusammen. Erwartung: Die Reaktion fällt stärker aus.
19. Volumen: Wir bilden ein Fixed Range Volume Profile aus Tick-Volumen über die letzte Range auf dem Signal-Timeframe, also vom letzten Swing-Hoch bis zum letzten Swing-Tief vor dem Ereignis. Ein Swing ist eine Kerze, die die 3 Kerzen davor und danach überragt. Er gilt erst nach Schluss der 3 Folgekerzen. Das Level liegt in einer High-Volume-Zone, wenn seine Preisstufe (Breite G/10) zu den oberen 20 % nach Volumen gehört oder der POC höchstens G/4 entfernt liegt. Erwartung: High-Volume-Zone eher Umkehr, Low-Volume-Zone eher Durchlauf.
20. COT-Positionierung (wöchentlich) als grober Kontext.

Ausschlüsse
21. Keine Ereignisse zwischen 21:00 und 23:00 UTC (Rollover).
22. News-Fenster: 30 Minuten vor bis 2 Stunden nach High-Impact-Terminen einer der beiden Währungen. Das sind US-CPI, NFP, Retail Sales und GDP, Eurostat sowie FOMC, EZB, BoE, BoJ, RBA, BoC und SNB. Bei H4-Signalen und bei Terminen ohne bekannte Uhrzeit ist der ganze Tag ausgeschlossen.
23. Hochvola-Regime: Die 20-Tage-Volatilität liegt über dem 90. Perzentil des Vorjahres, gemessen bis zum Vortag.
24. Läuft ein Fenster über das Wochenende, wird ein Gap zum Montags-Eröffnungskurs bewertet.

Die nach 22 und 23 ausgeschlossenen Ereignisse werden als Kontrollgruppe mitgemessen.

Merksatz: Ein frischer Anlauf auf ein vorher definiertes, sichtbares Level, ein objektives Ereignis (Berührung, Kerzenschluss oder Retest), und dann die Frage, was zuerst kommt: G in die eine Richtung oder G in die andere.

03 MECHANISMUS

1. Runde und halbe Zahlen sowie HTF-Pivots: Viele Teilnehmer legen Orders bewusst auf diese frei sichtbaren Preise. Das sind Take-Profits, Limit-Einstiege und, als Hypothese, Options-Barrieren. Stop-Orders sammeln sich knapp hinter der Marke.
2. Kurzfristige Händler kennen diese Ballung. Sie haben einen Anreiz, den Kurs in die Stops zu drücken, denn ausgelöste Stops sind Market-Orders. Das erzeugt den Sog zum Level und durch das Level hindurch.
3. Die ausgelösten Stops beschleunigen den Kurs kurz, bringen aber keine neue Information. Ist die Ballung abgearbeitet, fehlt der Grund für einen weiteren Lauf. Ein Durchstechen ist deshalb wahrscheinlich, ein nachhaltiger Weiterlauf nicht. Es verliert der Stop-Halter, der zum schlechtesten Preis aus dem Markt genommen wird.
4. Vorwochen- und Session-Hochs und -Tiefs: Hinter offensichtlichen Hochs und Tiefs liegen die Stops der Positionen aus diesem Zeitraum (externe Liquidität). Der Kurs wird zu ihnen gezogen.
   - Sweep und Umkehr: Die Stops werden abgeholt und dienen der Gegenseite als Liquidität für ihren Einstieg. Ohne neue Information dreht der Kurs. Es verlieren die Ausgestoppten und die Ausbruchskäufer im Sweep.
   - Durchbruch und Retest: Nach einem echten Durchbruch sind die Trader gefangen, die auf ein Halten gesetzt haben. Bei der Rückkehr zum Level stehen sie bei plus minus null und steigen aus. Dazu steigen Trader ein, die den Durchbruch verpasst haben. Beides erzeugt Gegenfluss am Level in Durchbruchrichtung.
5. Engulfing-Open: Die Vorkerze lockt Trader in ihre Richtung, die Engulfing-Kerze fängt sie im Minus. Kehrt der Kurs zum Open der Engulfing-Kerze zurück, also ungefähr zu ihrem Einstieg, steigt ein Teil von ihnen bei plus minus null aus. Gleichzeitig steigen dort Trader ein, die den Move verpasst haben. Das Level hält in Engulfing-Richtung, umso eher, je mehr Trader die Vorkerze angelockt hat. Es verliert der gefangene Vorkerzen-Trader. Der Mechanismus ist derselbe wie bei Durchbruch und Retest.
6. Volumen: Viel bereits gehandeltes Volumen in der Zone um das Level bedeutet viele offene Positionen mit Einstieg dort. Sie werden bei der Rückkehr verteidigt oder bei plus minus null geschlossen, deshalb kommt es eher zur Umkehr. Wenig Volumen bedeutet wenig Gegenwehr, deshalb eher Durchlauf.
7. News und Hochvola: Neue Information führt zu Neubewertungen, und dieser Strom ist um ein Vielfaches größer als die Orders am Level. Das Level verliert dann seine Wirkung und wird durchlaufen.

Wichtig: Das ist eine Mechanismus-Hypothese. Wir behaupten noch nicht, dass sie bewiesen ist.

04 GEGENPROBE

• Verhalten sich zufällig verschobene Schein-Level beim jeweiligen Level-Typ gleich, sind Sichtbarkeit und Orderballung nicht der Grund.
• Ist der Kurs direkt hinter einem Magnet-Level nicht schneller als hinter einem Schein-Level, oder beschleunigt er schon davor, ist die Stop-Erklärung falsch.
• Hält das Open einer gewöhnlichen Kerze ohne Engulfing genauso gut, ist die Falle nicht der Grund. Halten Kerzenmitte oder Close genauso gut wie das Open, spielt der Plus-minus-null-Punkt keine Rolle. Hält das Level nach einer kleinen Vorkerze genauso gut wie nach einer großen, ist „je mehr Gefangene, desto stärker“ widerlegt.
• Läuft ein Retest nach dem Durchbruch eines Schein-Levels genauso gut, ist der Rollentausch nicht levelspezifisch. Dann war es nur Ausbruchs-Momentum.
• Verhalten sich Durchbruch-und-Retest und Engulfing-Open grundverschieden, ist die gemeinsame Erklärung „Gefangene steigen bei plus minus null aus“ unwahrscheinlich.
• Wirken Pivots aus der vorletzten Kerze, die keine Plattform anzeigt, genauso gut wie die aus der Vorkerze, ist Sichtbarkeit nicht der Grund.
• Halten Level in High-Volume-Zonen nicht häufiger als in Low-Volume-Zonen, wirkt Volumen nicht. Halten beliebige Preise in High-Volume-Zonen ohne Key Level genauso gut, ist es ein reiner Volumen-Effekt und kein Key-Level-Effekt.
• Kommt es gegen die HTF-Struktur nicht häufiger zum Sweep als mit ihr, erklärt der Kontext nichts. Liefert ein reiner Handel mit dem HTF-Trend ohne Level gleich gute Ergebnisse, sind die Level überflüssig.
• Wirken die Level in News- und Hochvola-Phasen genauso wie in ruhigen Phasen, erklärt die Orderballung den Effekt nicht.
• Taucht ein Effekt nur in einer einzigen der 40 Kombinationen aus Timeframe und Größe auf und nicht bei den Nachbargrößen, ist er wahrscheinlich Zufall.

Kern: Eine gute Gegenprobe greift nicht nur die Performance an. Sie greift die angenommene Ursache an.

05 TEST

Datenquelle: Dukascopy M1 Bid (UTC) mit Tick-Volumen. Daraus werden M15, H1, H4, D1, W1 und Monat gebildet. Die Kosten je Paar stammen aus den TTP/IQ-Messungen, News- und Notenbank-Kalender sowie COT aus dem Repo. Einschränkungen: Das Tick-Volumen stammt aus nur einem Feed, und eine historische Spread-Zeitreihe fehlt.

Zeitraum:
- IS 01/2016–03/2023 auf EURUSD, GBPUSD, USDJPY und AUDUSD sowie auf den frischen Paaren USDCAD, USDCHF, NZDUSD, EURJPY, GBPJPY und EURGBP.
- OOS 04/2023–09/2025 auf allen zehn Paaren. Bei runden und halben Zahlen auf den vier bekannten Paaren ist das OOS nur ein Vergleich, kein Beleg, weil es bereits gesehen wurde.
- Tresor 10/2025 bis heute, nur auf den sechs frischen Paaren.
- Enthaltene Phasen: Brexit 2016, die ruhigen Phasen 2017 und 2019, Corona-Crash 2020, USD-Trend 2022.
- Vor dem ersten Lauf werden fixiert: alle Definitionen und Annahmen dieser Karte, die 40 Kombinationen, die Richtung jedes Kontextfaktors und die Weitergabe-Kriterien. Alles wird in der Overfitting-Sperre registriert.

Fallzahl: Jedes Ereignis, das die Regel erfüllt, wird erfasst, ohne Auswahl von Hand. Eine Kombination wird nur ausgewertet, wenn sie im IS mindestens 100 Ereignisse hat.

Vergleich: Jeder Level-Typ gegen Schein-Level. Geschwindigkeit hinter dem Level gegen Schein-Level. Engulfing-Open gegen normales Kerzen-Open, Kerzenmitte, Close und kleine Vorkerze. Retest an echten Leveln gegen Schein-Level. Durchbruch-und-Retest gegen Engulfing-Open. Pivots der Vorkerze gegen die der vorletzten Kerze. High-Volume-Zone gegen Low-Volume-Zone und gegen beliebige Preise in High-Volume-Zonen. Anlauf mit der HTF-Struktur gegen Anlauf gegen sie, dazu HTF-Trend ohne Level. News- und Hochvola-Phasen gegen ruhige Phasen.

Stufe 1: Verglichen wird die Trefferquote mit der an Schein-Leveln. Eine Kombination kommt weiter, wenn drei Bedingungen erfüllt sind: t > 3, die Nachbargrößen haben dasselbe Vorzeichen, und das 1:1-Ergebnis nach Kosten ist positiv. Bei G = 10 sind dafür etwa 56 % Trefferquote nötig.

Stufe 2: Die Kontextfaktoren werden einzeln geprüft, nur auf den weitergegebenen Kombinationen. Jede Kombination zählt als Versuch, die Deflated Sharpe wird ausgewiesen. OOS und Tresor werden je genau einmal geöffnet.

Heute noch nicht: Open Interest, Retail-Sentiment, Orderbuch und minutengenaue Uhrzeiten für Nicht-US-Daten.

Festgelegte Annahmen (vom Nutzer pauschal bestätigt, 16.10.):
- Engulfing gültig 5 Kerzen
- Session-Level gültig 24 Stunden
- Retest innerhalb von 5 Kerzen
- Swing k = 3
- High-Volume-Zone = obere 20 % bzw. POC ≤ G/4
- News-Fenster −30 Minuten bis +2 Stunden
- Hochvola = 90. Perzentil
- Floor-Pivots P/R1/S1/R2/S2

Ergebnis: Eine vollständige, falsifizierbare und testbare Ausgangsthese.
