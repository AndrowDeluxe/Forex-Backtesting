"""Education-Track: Buchzusammenfassung *Quantitative Trading* (Ernest P. Chan).

Ausgelagert aus `education.py` (2026-08-10), das jetzt eine Hub-Seite mit
Kacheln ist. Nach Themen/Frameworks gebuendelte, ins Deutsche uebersetzte
Zusammenfassung als Nachschlagewerk fuer die eigene Weiterbildung -- folgt
nicht 1:1 der Kapitelreihenfolge des Originals, sondern buendelt inhaltlich
zusammengehoerige Konzepte neu. Statische Lerninhalte, kein Backtest.
"""

import streamlit as st

st.set_page_config(
    page_title="Education -- Quantitative Trading (Chan)", page_icon=":material/menu_book:", layout="wide"
)

st.page_link("app_pages/education.py", label="Zurueck zu Education", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/menu_book: Buchzusammenfassung: *Quantitative Trading* (Ernest P. Chan)")
st.caption(
    "Quelle: Ernest P. Chan, *Quantitative Trading -- How to Build Your Own "
    "Algorithmic Trading Business*, 2. Auflage, Wiley 2021. Nach Themen/Frameworks "
    "gebuendelte, ins Deutsche uebersetzte Zusammenfassung als Nachschlagewerk fuer "
    "die eigene Weiterbildung -- folgt nicht 1:1 der Kapitelreihenfolge des Originals, "
    "sondern buendelt inhaltlich zusammengehoerige Konzepte neu."
)

st.space("small")

BOOK_SECTIONS: list[tuple[str, str, str]] = [
    (
        "auto_stories",
        "A. Grundlagen: Was ist quantitatives Trading und wer kann es betreiben?",
        """
Quantitatives Trading (auch algorithmisches Trading) bezeichnet den Handel von
Wertpapieren ausschliesslich auf Basis computergestuetzter Kauf-/Verkaufsentscheidungen,
die zuvor anhand historischer Daten backgetestet wurden. Chan grenzt dies bewusst von
reiner technischer Analyse ab: Chartmuster wie "Kopf-Schulter-Formationen" zaehlen nicht
dazu, weil sie subjektiv und nicht quantifizierbar sind, waehrend computergestuetzt
verarbeitete Fundamentaldaten (Umsatz, Cashflow, Verschuldungsgrad) oder sogar
News-Sentiment sehr wohl dazugehoeren, solange sie sich in Zahlen uebersetzen lassen.
Der Fokus des Buchs liegt auf Statistical Arbitrage: Handel der einfachsten Instrumente
(Aktien, Futures, gelegentlich Devisen), nicht auf komplexen Derivaten.

Ein zentrales Argument des Buchs: Man braucht keinen Doktortitel in Physik oder
Mathematik, um profitabel zu handeln. Chan selbst hat als Physik-PhD mit fortgeschrittener
Mathematik bei institutionellen Banken jahrelang Verluste eingefahren, wurde aber
profitabel, sobald er auf einfache, robuste Strategien umstieg ("Make everything as
simple as possible. But not simpler." -- Einstein-Zitat). Wichtiger als akademische
Qualifikation sind: ausreichend Ersparnisse, um Verlustphasen ohne Verkaufsdruck
durchzustehen, eine gute Balance zwischen Angst und Gier, und die Bereitschaft,
systematisch statt intuitiv zu entscheiden.

Geschaeftlich unterscheidet sich quantitatives Trading fundamental von anderen
Kleinunternehmen in drei Punkten: (1) Skalierbarkeit -- eine profitable Strategie laesst
sich fast beliebig durch Hebel (Leverage) vergroessern, ohne dass man Kapitalgeber
ueberzeugen muss, weil Broker den Hebel bereitstellen; (2) geringer Zeitaufwand im
operativen Betrieb, sobald automatisiert -- der Zeitaufwand verschiebt sich auf die
kreative Recherche- und Entwicklungsphase; (3) praktisch keine Notwendigkeit fuer
Marketing, weil die Gegenpartei am Markt ausschliesslich preisbasiert entscheidet (es sei
denn, man verwaltet fremdes Geld). Das macht den Einstieg fuer Einzelpersonen mit
begrenztem Kapital grundsaetzlich attraktiver als z. B. die Gruendung einer klassischen
Firma.
""",
    ),
    (
        "travel_explore",
        "B. Strategien finden: Quellen und Passung zur eigenen Situation",
        """
Die Ideenfindung ist laut Chan nicht der Engpass -- es gibt tausende oeffentlich
zugaengliche Strategieideen aus akademischen Papers (SSRN, NBER, Quantpedia als
Aggregator), Finanzblogs/Podcasts, Trader-Foren (Elite Trader, Wealth-Lab) und sozialen
Medien/Twitter. Akademische Strategien sind oft zu komplex, veraltet (bereits
wegarbitriert) oder auf teure/illiquide Small-Caps zugeschnitten; Forums-Strategien halten
selten der eigenen Nachpruefung stand, lassen sich aber haeufig durch kleine Variationen
(z. B. kuerzere Haltedauer, andere Ein-/Ausstiegszeitpunkte) profitabel machen. Der
eigentliche Wert liegt nicht im "Geheimnis" der Grundidee, sondern in den eigenen
Anpassungen und Variationen.

Ob eine Strategie zur eigenen Situation passt, haengt laut Chan von vier Faktoren ab, die
man vor jedem Backtest klaeren sollte: (1) Zeitbudget -- Teilzeit-Trader sollten
Strategien bevorzugen, die Positionen ueber Nacht halten oder komplett automatisiert
laufen, statt Intraday-Strategien mit manueller Ueberwachung; (2) Programmierkenntnisse --
wer keine Programmiersprache beherrscht, sollte sich auf wenige Instrumente/taegliche
Rebalancierung beschraenken (Excel-tauglich), waehrend Hochfrequenz- oder grosse
Portfolio-Strategien fundierte Programmierkenntnisse erfordern; (3) Kapitalverfuegbarkeit
-- unter 50.000-100.000 USD raet Chan von quantitativem Trading grundsaetzlich ab, da
geringes Kapital den erreichbaren Hebel (Regulation T: 2x ueber Nacht, 4x Intraday,
ausser bei Prop-Firmen), den Instrumentenzugang (Futures/Devisen bieten mehr Hebel bei
weniger Kapital) und die leistbare Datenqualitaet (survivorship-bias-freie Daten,
Echtzeitdaten, Nachrichtenfeeds) einschraenkt; (4) Ziel -- regelmaessiges monatliches
Einkommen erfordert kurze Haltedauern und viele gleichzeitig laufende, gestaffelte
Positionen, waehrend fuer reines langfristiges Vermoegenswachstum ueberraschenderweise
nicht die "Buy-and-Hold"-Strategie mit dem hoechsten Return optimal ist, sondern jene mit
der hoechsten Sharpe Ratio bei ausreichendem Hebelzugang.
""",
    ),
    (
        "flag",
        "C. Strategie-Vorpruefung: Red Flags, bevor man ueberhaupt backtestet",
        """
Bevor man Zeit in einen vollstaendigen Backtest investiert, empfiehlt Chan eine Reihe
schneller Plausibilitaetschecks. Erstens der Benchmark-Vergleich: Eine reine
Long-Strategie mit 10 % Jahresrendite ist nicht beeindruckend, wenn ein Indexfonds
dasselbe leistet -- relevanter Vergleichsmassstab ist bei Long-Only-Strategien der
passende Marktindex (Information Ratio), bei marktneutralen Long-Short-Strategien
dagegen der risikofreie Zins (Sharpe Ratio). Zweitens die Konsistenz der Renditen ueber
die Volatilitaet: Als Faustregel gilt eine Sharpe Ratio unter 1 als fuer sich genommen
nicht handelbar, ab ca. 2 ist man in der Naehe monatlicher Konsistenz, ab ca. 3 nahezu
taeglicher Konsistenz.

Drittens Drawdown-Tiefe und -Dauer: Bereits an einem groben Blick auf die Equity-Kurve
laesst sich abschaetzen, ob eine Strategie ueberhaupt eine attraktive Sharpe Ratio haben
kann -- tiefe (> 10 %) oder lange (> 4 Monate) Drawdowns deuten meist auf eine niedrige
Sharpe Ratio hin, und man sollte vorab festlegen, welchen maximalen Drawdown man
persoenlich psychologisch und finanziell verkraften kann. Viertens die
Transaktionskosten-Sensitivitaet: Strategien mit hoher Handelsfrequenz koennen vor
Kosten exzellent aussehen und nach Abzug realistischer Kosten (Kommission,
Bid-Ask-Spread, Marktimpact, Slippage) komplett unprofitabel werden -- ein Beispiel im
Buch zeigt eine Bollinger-Band-Strategie mit Sharpe 3 vor Kosten, die nach Abzug von nur
1 Basispunkt auf Sharpe -3 kippt.

Fuenftens Survivorship-Bias in den zugrundeliegenden Daten: Historische Datensaetze, die
insolvente oder delistete Aktien nicht enthalten, blaehen besonders "Value"-Strategien
(die guenstige Aktien kaufen) kuenstlich auf, weil genau jene Aktien fehlen, die
guenstig waren, weil sie kurz vor der Pleite standen. Sechstens die zeitliche
Entwicklung der Performance: Strategien, die vor 10+ Jahren gut funktioniert haben, aber
in den letzten Jahren nachlassen, sollten mit besonderem Fokus auf die juengste
Performance bewertet werden, da fruehere Perioden oft durch Survivorship-Bias und
geringere Konkurrenz kuenstlich attraktiv wirken. Siebtens Data-Snooping-Bias: Je mehr
Parameter/Regeln eine Strategie hat, desto wahrscheinlicher wurde sie unbewusst an
historisches Rauschen angepasst statt an ein echtes Muster. Und schliesslich achtens die
"Nischen-Tauglichkeit": Anders als institutionelle Fonds, die Kapazitaet (viel Geld
unterbringen) brauchen, sollten Privatanleger gezielt nach Strategien mit geringer
Kapazitaet suchen, die "unter dem Radar" grosser Institutioneller fliegen, weil diese
Nischen noch nicht wegarbitriert sind.
""",
    ),
    (
        "query_stats",
        "D. Backtesting-Handwerk: Plattformen, Daten, Kennzahlen",
        """
Fuer das Backtesting selbst vergleicht Chan Excel (WYSIWYG, kaum
Look-Ahead-Bias-Risiko, aber nur fuer einfache Modelle geeignet), MATLAB (sein
bevorzugtes Werkzeug: schnell, gut dokumentiert, ideal fuer grosse Portfolios, aber
kostenpflichtig), Python (heute De-facto-Standard dank NumPy/Pandas, aber mit
Versionskonflikten und laut Chan schwaecheren Statistik-Paketen) und R (stark bei
klassischer Statistik/Oekonometrie) sowie fertige Plattformen wie QuantConnect oder
Blueshift, die Backtesting und Live-Handel nahtlos verbinden.

Bei den Daten selbst sind drei Qualitaetsfragen entscheidend: Sind die Kurse split- und
dividendenbereinigt (sonst erzeugt jeder Aktiensplit einen kuenstlichen Kurssprung, der
Fehlsignale ausloest)? Sind die Daten survivorship-bias-frei (bei kleinem Budget
zumindest moeglichst aktuelle Daten verwenden, um den Effekt zu minimieren)? Und wie
verlaesslich sind Tageshoch/-tief-Werte -- diese sind deutlich verrauschter als
Eroeffnungs-/Schlusskurse, weil ein einzelner fehlerhafter Tick oder eine sehr kleine
Order genuegt, um sie zu erzeugen, weshalb Strategien, die auf Intraday-Extremen
basieren, vorsichtiger zu bewerten sind. Als Performance-Kennzahlen empfiehlt Chan
primaer drei Groessen statt der von Privatanlegern oft bevorzugten Gesamtrendite: die
annualisierte Sharpe Ratio (Verhaeltnis von durchschnittlicher Ueberschussrendite zu
deren Standardabweichung), den maximalen Drawdown (groesster Verlust vom bisherigen
Hoechststand) sowie die MAR-Ratio (Verhaeltnis von Rendite zu maximalem Drawdown) --
diese drei sind robuster vergleichbar ueber verschiedene Strategien und Hebelgrade
hinweg als die nominale Rendite allein.
""",
    ),
    (
        "bug_report",
        "E. Backtesting-Fallen: Look-Ahead-Bias, Data-Snooping, Transaktionskosten",
        """
Der gefaehrlichste und haeufigste Programmierfehler ist der Look-Ahead-Bias: die
versehentliche Verwendung von Informationen, die zum Handelszeitpunkt noch gar nicht
bekannt sein konnten (z. B. "kaufe, wenn der Kurs nahe am Tagestief liegt" -- das
Tagestief steht aber erst nach Handelsschluss fest). Chan empfiehlt einen expliziten
Test: das Backtest-Programm einmal mit den vollstaendigen Daten und einmal mit um N Tage
gekuerzten Daten laufen lassen -- unterscheiden sich die daraus resultierenden
historischen Positionen fuer den gemeinsamen Zeitraum, steckt ein Look-Ahead-Fehler im
Code.

Data-Snooping-Bias -- die unbewusste Ueberanpassung eines Modells an zufaelliges
historisches Rauschen statt an ein echtes, wiederkehrendes Muster -- laesst sich nie
vollstaendig vermeiden, aber durch drei Techniken eindaemmen: ausreichende
Stichprobengroesse (Chan zitiert konkrete Mindestlaengen: bei Sharpe Ratio 1 braucht man
mindestens rund 681 Handelstage/2,7 Jahre, um statistisch sicher zu sein, dass die
"wahre" Sharpe Ratio ueber null liegt), Out-of-Sample-Tests (Trainings- und Testperiode
strikt trennen, Parameter nur auf dem Trainingsset optimieren) sowie
Sensitivitaetsanalysen (kleine Variationen der Parameter duerfen die Performance nicht
drastisch einbrechen lassen -- bricht sie ein, ist das Modell zu fein auf historisches
Rauschen kalibriert). Als Faustregel sollten nicht mehr als etwa fuenf freie Parameter
in einer Strategie stecken.

Transaktionskosten duerfen im Backtest nicht fehlen, da sie ueber Erfolg und Misserfolg
entscheiden koennen -- Chan zeigt anhand einer einfachen taeglichen
Mean-Reversion-Strategie auf dem S&P 500, wie aus einer beeindruckenden Sharpe Ratio
nach Beruecksichtigung von 5 Basispunkten Kosten ein tief negativer Wert wird, waehrend
dieselbe Grundidee mit einer minimalen Anpassung (Handel zur Eroeffnung statt zum
Schluss) wieder profitabel wird. Bei der Verfeinerung bestehender, bekannter Strategien
(z. B. Pair-Trading) gilt: Variationen sollten immer eine nachvollziehbare oekonomische
Begruendung haben (z. B. Ausschluss von Pharma-Aktien wegen News-Sensitivitaet, andere
Ein-/Ausstiegszeitpunkte) statt reiner Trial-and-Error-Anpassung an die Testdaten.
""",
    ),
    (
        "storefront",
        "F. Geschaeftsaufbau: Retail-Konto vs. Prop-Trading-Firma, Broker, Infrastruktur",
        """
Fuer die rechtliche und geschaeftliche Struktur stehen zwei Wege offen: ein
Retail-Brokerage-Konto (volle Freiheit, aber Hebel begrenzt durch Regulation T, dafuer
SIPC-versichert) oder Mitgliedschaft bei einer Prop-Trading-Firma (deutlich hoeherer
Hebel moeglich, oft mit Coaching, aber Series-7-Pruefung noetig, keine
Einlagensicherung, und das eigene Kapital haftet nur begrenzt bei entsprechender
Rechtsform). Chan raet dringend zur Gruendung einer Kapitalgesellschaft (LLC/S-Corp)
fuer das Handelskonto, weil private Broker-Konten bei extremen Marktereignissen (z. B.
Franken-Entkopplung 2015) eine unbegrenzte persoenliche Nachschusspflicht ausloesen
koennen -- mit einer LLC ist die Haftung auf das eingesetzte Kapital begrenzt. Beide
Kontoarten lassen sich parallel fuehren, um Ausfuehrungsqualitaet und Kostenstruktur zu
vergleichen.

Bei der Brokerwahl zaehlt neben der reinen Kommission vor allem: Zugang zu
Dark-Pool-Liquiditaet und Ausfuehrungsgeschwindigkeit (oft wichtiger als die nominale
Kommission), eine brauchbare API fuer Datenabruf und Orderaufgabe (ohne API ist
Hochfrequenzhandel unmoeglich), ein Paper-Trading-Konto zum gefahrlosen Testen der
eigenen Automatisierung sowie -- im Fall von Prop-Firmen -- eine solide Bilanz und gute
Reputation (pruefbar ueber FINRA BrokerCheck und Trader-Foren), da das eigene Kapital
sonst durch schlechte Trades anderer Mitglieder gefaehrdet sein kann. Die physische
Infrastruktur kann in der Startphase minimal bleiben: ein normaler PC, schnelles
Internet und eine unterbrechungsfreie Stromversorgung reichen fuer wenige tausend
Dollar Investition; erst mit wachsendem Kapital lohnen sich ein Virtual Private Server
(VPS) fuer latenzarme, ausfallsichere Ausfuehrung sowie kostenpflichtige
Echtzeit-Datenfeeds.
""",
    ),
    (
        "precision_manufacturing",
        "G. Execution-Systeme: Automatisierung, Kostenminimierung, Paper-Trading",
        """
Chan unterscheidet zwei Automatisierungsgrade: semi-automatisierte Systeme (Order-Liste
wird z. B. in MATLAB/Python generiert und dann manuell oder halbautomatisch ueber einen
Basket-/Spread-Trader beim Broker hochgeladen -- geeignet fuer wenige Order-Wellen pro
Tag und bietet die Moeglichkeit, Order vor dem Absenden zu plausibilisieren) und
vollautomatisierte Systeme (durchgaengige Schleife, die Daten abruft, Signale erzeugt
und Order direkt ueber die Broker-API sendet -- notwendig fuer hochfrequente
Strategien, aber ohne den "Sanity Check" vor dem Versand riskanter, wie der
440-Millionen-Dollar-Softwarefehler von Knight Capital 2012 zeigt). Wer selbst nicht
programmieren kann oder will, kann Programmier-Consultants engagieren (oft
1.000-5.000 USD pro Projekt); Vertraulichkeit laesst sich durch Aufteilung der Arbeit
auf mehrere Consultants (einer baut die Infrastruktur, ein anderer die eigentliche
Strategie-Logik, keiner kennt beides) sowie durch NDAs absichern.

Zur Minimierung von Transaktionskosten empfiehlt Chan: keine Aktien unter 5 USD handeln
(hohe relative Spreads), Orders auf maximal etwa 1 % des durchschnittlichen
Tagesvolumens begrenzen, und die Positionsgroesse nicht linear, sondern eher mit der
vierten Wurzel der Marktkapitalisierung skalieren, um Diversifikation ueber Small- und
Large-Caps hinweg zu erhalten, ohne bei Small-Caps uebermaessigen Marktimpact zu
erzeugen. Paper-Trading vor dem Livegang ist unverzichtbar: Es deckt Softwarefehler,
uebersehenen Look-Ahead-Bias sowie operative Probleme auf (z. B. wie lange das
morgendliche Datenladen tatsaechlich dauert) und liefert intuitives Gefuehl fuer
Volatilitaet und Kapitalauslastung der eigenen Strategie, bevor echtes Geld involviert
ist.

Zuletzt beschreibt Chan systematisch, wie man vorgeht, wenn Live-Performance hinter dem
Backtest zurueckbleibt: zunaechst Software-Bugs und erhoehte Ausfuehrungskosten
ausschliessen, dann pruefen, ob Data-Snooping-Bias vorliegt (Vereinfachung des Modells
testen -- bricht die Backtest-Performance dabei komplett ein, war das Modell
ueberangepasst), und schliesslich Regimewechsel in Betracht ziehen -- konkret nennt er
die Dezimalisierung der US-Aktienkurse 2001 (reduzierte strukturell die Profitabilitaet
vieler Statistical-Arbitrage-Strategien) und die Abschaffung/Wiedereinfuehrung der
Uptick-Rule fuer Leerverkaeufe (2007-2010) als historische Beispiele, bei denen sich die
Marktstruktur selbst veraendert hat.
""",
    ),
    (
        "calculate",
        "H. Money & Risk Management: Die Kelly-Formel",
        """
Das zentrale mathematische Werkzeug fuer Kapitalallokation und Hebelwahl ist die
Kelly-Formel. Unter der Annahme normalverteilter Renditen maximiert sie die
langfristige, geometrisch verzinste Wachstumsrate des Kapitals. Fuer eine einzelne
Strategie lautet sie f = m/s^2 (optimaler Hebel = erwartete Ueberschussrendite geteilt
durch die Varianz der Renditen); fuer mehrere Strategien gleichzeitig ergibt sich der
optimale Kapitalallokationsvektor aus der inversen Kovarianzmatrix multipliziert mit dem
Vektor der erwarteten Renditen. Eine wichtige, kontraintuitive Erkenntnis daraus: Bei
einem echten Random Walk mit +1 %/-1 % Wahrscheinlichkeit je 50 % verliert man
langfristig trotzdem Geld (Rate ca. -0,005 % pro Periode), weil die geometrische
(verzinste) Rendite gleich der arithmetischen Rendite minus der halben Varianz ist --
Risiko senkt also grundsaetzlich die langfristige Wachstumsrate, was die zentrale
Rechtfertigung fuer aktives Risikomanagement liefert.

Da echte Renditen nicht normalverteilt sind, sondern "Fat Tails" (deutlich haeufigere
Extremereignisse als die Normalverteilung vorhersagt) aufweisen, empfiehlt Chan in der
Praxis nur den halben Kelly-Hebel ("Half-Kelly") zu nutzen und zusaetzlich den
historisch schlechtesten Einzelperiodenverlust heranzuziehen, um zu pruefen, ob selbst
Half-Kelly noch zu aggressiv waere (sein Beispiel: Der Schwarze Montag 1987 mit -20,47 %
an einem Tag haette selbst bei Half-Kelly-Hebel auf den S&P 500 ein untragbares
Verlustereignis bedeutet). Die praktische Konsequenz der Kelly-Formel ist unbequem, aber
wichtig: Nach Verlusten muss die Positionsgroesse reduziert werden (auch wenn das
bedeutet, Verluste zu realisieren), nach Gewinnen darf sie erhoeht werden -- genau
dieses systematische De-Leveraging vieler Fonds gleichzeitig gilt als eine Erklaerung
fuer "Finanzansteckung" (z. B. beim Quant-Crash im August 2007 oder beim
GameStop-Short-Squeeze im Januar 2021).

Neben Kelly nennt Chan vier weitere Risikokategorien: Modellrisiko (die Strategie
selbst ist fehlerhaft oder durch Konkurrenz/Regimewechsel wertlos geworden --
Gegenmittel ist eine unabhaengige Nachvollziehung des Backtests durch Dritte sowie eine
schrittweise statt abrupte Reduktion des Hebels), Software-Risiko (das Live-System
weicht vom Backtest ab -- Gegenmittel ist der Abgleich der tatsaechlich generierten
Trades mit dem theoretischen Backtest-Output), Naturkatastrophen-/Infrastrukturrisiko
(Internet-/Stromausfall mitten in einer offenen Position) sowie explizit die Frage, ob
Stop-Loss-Orders sinnvoll sind: Chan argumentiert, dass Stop-Loss nur in echten
Momentum-Regimen (Preisbewegung durch fundamentale News/Anpassung an neues
Gleichgewicht) sinnvoll ist, in Mean-Reversion-Regimen (Preisbewegung durch temporaere
Liquiditaetsereignisse) dagegen aktiv schadet, weil man genau am unguenstigsten Punkt
verkauft, statt die erwartete Rueckkehr zum Mittelwert abzuwarten.
""",
    ),
    (
        "psychology",
        "I. Psychologie: Verlustaversion, Verzweiflung, Gier",
        """
Ein eigener Buchabschnitt widmet sich der Psychologie, weil selbst perfekt
automatisierte Systeme durch manuelle Eingriffe des Traders sabotiert werden koennen.
Wichtig ist Chans Umdeutung der "Verlustaversion" aus der Verhaltensoekonomie:
Klassische Oekonomen (z. B. Kahneman) werten es als irrationalen Bias, eine Wette mit
positivem Erwartungswert abzulehnen (z. B. Muenzwurf: -100 USD bei Zahl, +110 USD bei
Kopf). Chan zeigt jedoch mathematisch (basierend auf Arbeiten von Ole Peters und Murray
Gell-Mann), dass dies nur bei einem "Ensemble-Durchschnitt" ueber unendlich viele
parallele Spieler irrational erscheint -- fuer einen einzelnen Trader, der dasselbe
Spiel wiederholt mit begrenztem Kapital spielt (Zeit-Durchschnitt statt
Ensemble-Durchschnitt), ist eine solche Wette bei fortlaufender Wiederholung
tatsaechlich ruinoes, weil ein Totalverlust das Spielende bedeutet. Verlustaversion ist
demnach in der Praxis oft rational, nicht irrational -- eine wichtige Rechtfertigung
dafuer, Risiko konsequent zu begrenzen, statt "im Erwartungswert zu denken".

Andere relevante Verzerrungen: der "Representativeness Bias" verleitet dazu, nach einem
grossen Verlust die Strategie ueberstuerzt zu veraendern, um genau diesen einen
vergangenen Verlust zu vermeiden -- dabei riskiert man, kuenftige, andersartige
Verluste zu provozieren oder profitable Gelegenheiten zu eliminieren; Modelllaenderungen
sollten immer erneut ueber einen langen Backtest-Zeitraum validiert werden, nicht nur
gegen die letzten Wochen. "Verzweiflung" (Despair) in Drawdown-Phasen fuehrt entweder
zum ueberstuerzten Abschalten eines Modells oder -- gefaehrlicher -- zur Verdopplung
des Einsatzes in der Hoffnung auf Erholung; "Gier" (Greed) nach Gewinnphasen fuehrt zu
schnellem, unkontrolliertem Ueberhebeln. Beide Reaktionen widersprechen der
disziplinierten, formelbasierten Steuerung ueber Kelly, und Chan berichtet aus eigener
Erfahrung von zwei selbst erlittenen sechs- bzw. siebenstelligen Verlusten genau durch
dieses Muster. Sein Rat: klein anfangen, Position schrittweise nach der Kelly-Formel
skalieren, und emotionale Reife im Umgang mit taeglichen P&L-Schwankungen aktiv
trainieren, bevor man das Kapital erhoeht.
""",
    ),
    (
        "show_chart",
        "J. Mean-Reversion vs. Momentum & Regimewechsel (Conditional Parameter Optimization)",
        """
Handelsstrategien sind nur profitabel, wenn Kurse entweder zum Mittelwert
zurueckkehren (Mean-Reversion) oder trendieren (Momentum) -- bei reinem Random Walk ist
jede Strategie zwecklos. Mean-Reversion einzelner Aktien (Time-Series Mean-Reversion)
ist selten; deutlich haeufiger ist Cross-Sectional Mean-Reversion bei
Portfolios/Spreads mehrerer Wertpapiere (klassisches Pair-Trading). Momentum entsteht
typischerweise durch drei Mechanismen: langsame Diffusion neuer Informationen (z. B.
Post-Earnings-Announcement-Drift, PEAD -- Kurse reagieren erst allmaehlich auf
ueberraschende Quartalszahlen), schrittweise Ausfuehrung grosser institutioneller Orders
(der haeufigste Grund fuer kurzfristiges Momentum) sowie Herdenverhalten von
Investoren, die die (womoeglich zufaelligen) Kaufentscheidungen anderer als
"Information" fehlinterpretieren. Konkurrenz zwischen Tradern wirkt auf beide
Strategietypen unterschiedlich: Bei Mean-Reversion sinkt tendenziell die Anzahl
profitabler Arbitragegelegenheiten gegen null, bei Momentum verkuerzt sich die optimale
Haltedauer, weil das neue Gleichgewicht immer schneller erreicht wird.

Da sich Marktregime (z. B. mean-revertierend vs. trendierend, oder allgemeiner Bullen-
vs. Baerenmarkt) ueber die Zeit veraendern, hat Chan mit "Conditional Parameter
Optimization" (CPO) eine eigene Methode entwickelt: Statt Strategie-Parameter nur
selten und traege auf einem historischen Trainingsfenster zu optimieren ("Unconditional
Optimization"), wird ein Machine-Learning-Modell (Random Forest mit Boosting) darauf
trainiert, die kuenftige Tagesrendite der Strategie in Abhaengigkeit von den gewaehlten
Parametern UND einem breiten Satz aktueller Marktbedingungs-Indikatoren
(Bollinger-Band-Z-Score, Money Flow, Force Index, Donchian Channel, ATR, Awesome
Oscillator, ADX -- jeweils ueber mehrere Lookback-Fenster) vorherzusagen. Fuer jeden
neuen Handelstag werden dann alle moeglichen Parameterkombinationen durch das Modell
"durchprobiert" und diejenige mit der hoechsten vorhergesagten Rendite gewaehlt. In
Chans Beispiel (Bollinger-Band-Mean-Reversion-Strategie auf GLD/GDX) verbesserte CPO
gegenueber klassischer Optimierung die annualisierte Rendite von 17,3 % auf 19,8 % und
die Sharpe Ratio von 1,95 auf 2,33 im Out-of-Sample-Test. Wichtig: CPO sagt nicht
direkt die Marktrendite vorher (was extrem schwer ist, da alle Welt das versucht),
sondern die Rendite der EIGENEN, bereits bestehenden Strategie -- dieses Prinzip nennt
Chan "Metalabeling" und haelt es fuer den entscheidenden Kunstgriff, um Machine Learning
im Trading sinnvoll (statt als Blackbox-Fehlschlag) einzusetzen.
""",
    ),
    (
        "link",
        "K. Stationaritaet & Kointegration (Pair-Trading)",
        """
Eine Zeitreihe ist "stationaer", wenn sie sich nie dauerhaft von ihrem Ausgangswert
entfernt -- die meisten einzelnen Aktienkurse sind das nicht (geometrischer Random
Walk). Findet man jedoch zwei (oder mehr) Wertpapiere, sodass eine bestimmte
Long-Short-Kombination ihrer Kurse stationaer ist, nennt man sie "kointegriert" --
genau das ist die mathematische Basis von Pair-Trading. Der Standardtest dafuer ist der
(augmentierte) Cointegrating-Dickey-Fuller-Test; das optimale Mischungsverhaeltnis
(Hedge Ratio) ergibt sich aus einer linearen Regression der beiden Preisreihen. Ein
zentraler, oft verwechselter Punkt: Kointegration ist NICHT dasselbe wie Korrelation.
Korrelation beschreibt, ob sich die taeglichen RENDITEN zweier Wertpapiere
gleichgerichtet bewegen -- das sagt nichts darueber aus, ob sich ihre PREISE langfristig
auseinanderentwickeln. Umgekehrt koennen zwei Aktien stark kointegriert (Preisdifferenz
bleibt stationaer), aber an einzelnen Tagen voellig unkorreliert sein. Chans
Praxisbeispiel: Coca-Cola und Pepsi sind trotz naheliegender Branchenverwandtschaft
NICHT kointegriert, aber ihre taeglichen Renditen sind mit rund 0,48 statistisch hoch
signifikant korreliert -- ein Beleg dafuer, dass "gleiche Branche" allein keine
Kointegration garantiert und man sie stets explizit testen muss, bevor man auf eine
Pair-Trading-Strategie setzt.

Ist eine Mean-Reversion-Strategie ueber Kointegration bzw. Stationaritaet mathematisch
fundiert, laesst sich die optimale Haltedauer robust ueber die
Ornstein-Uhlenbeck-Gleichung schaetzen: Man regressiert die taegliche Veraenderung des
Spreads gegen den (um seinen Mittelwert bereinigten) Spread selbst, erhaelt daraus den
Rueckkehr-Koeffizienten Theta, und die "Halbwertszeit" ln(2)/Theta gibt an, wie lange es
im Mittel dauert, bis sich eine Abweichung zur Haelfte zurueckgebildet hat (im
GLD/GDX-Beispiel rund 7,8 Handelstage). Dieser Ansatz ist statistisch robuster als die
Schaetzung der Haltedauer allein aus den wenigen historischen Trades einer
Backtest-Simulation, weil er die gesamte Zeitreihe nutzt, nicht nur die Signaltage.
""",
    ),
    (
        "insights",
        "L. Faktormodelle (Arbitrage Pricing Theory)",
        """
Faktormodelle zerlegen die Ueberschussrendite eines Wertpapiers formal in R = X*b + u:
eine Matrix X von "Faktor-Exposures" (Sensitivitaeten des Wertpapiers gegenueber
bestimmten Renditetreibern), einen Vektor b von "Faktorrenditen" (den gemeinsamen,
marktweiten Renditetreibern selbst) sowie einen unternehmensspezifischen Rest-Term u.
Das bekannteste Beispiel ist das Fama-French-Dreifaktorenmodell: Markt-Beta, der
SMB-Faktor (Small-minus-Big, Rendite eines Long-Small-Cap/Short-Large-Cap-Portfolios)
und der HML-Faktor (High-minus-Low, Rendite eines Long-Value/Short-Growth-Portfolios
anhand des Buch-zu-Marktwert-Verhaeltnisses). Man unterscheidet Time-Series-Faktoren
(Faktorrendite ueber Regression der Aktienrenditen gegen bekannte Faktor-Zeitreihen wie
SMB/HML geschaetzt) und Cross-Sectional-Faktoren (Faktor-Exposure direkt beobachtbar,
z. B. das KGV einer Aktie; die zugehoerige Faktorrendite wird stattdessen periodenweise
aus einer Querschnitts-Regression ueber alle Aktien gewonnen). Eine besondere,
"modellfreie" Variante sind Statistische Faktoren via Principal Component Analysis
(PCA): Hier werden weder Exposures noch Faktorrenditen vorab spezifiziert, sondern
beide rein aus der historischen Kovarianzstruktur der Renditen selbst extrahiert (die
Eigenvektoren mit den groessten Eigenwerten bilden die Faktoren).

Wichtig fuer die praktische Anwendung: Faktormodelle sind per Konstruktion
"contemporaneous" (gleichzeitig, nicht vorhersagend) -- man kann eine Faktorrendite erst
aus abgeschlossenen Renditen berechnen. Fuer Handelszwecke nutzbar werden sie nur unter
der Annahme, dass Faktorrenditen ein gewisses Momentum haben (der aktuelle Wert bleibt
fuer die naechste Periode ungefaehr gueltig). Ein grundsaetzliches Risiko von
Faktormodellen: Sie funktionieren nur, solange Investoren mit demselben
Bewertungsmassstab weiterhin argumentieren -- in Phasen, in denen der Markt z. B.
Wachstumswerte statt Substanzwerten bevorzugt (Dotcom-Blase 1999, 2007, 2017-2020,
waehrend Covid-19), kann der HML-Faktor ueber laengere Zeit negativ werden, was zu
ausgedehnten Drawdowns fuehrt. Abschliessend eine praktische Erkenntnis zur
Portfoliokonstruktion: Bei gleicher erwarteter Rendite ist ein hoch gehebeltes
Portfolio aus Low-Beta-Aktien einem ungehebelten Portfolio aus High-Beta-Aktien
ueberlegen, weil High-Beta-Aktien systematisch unterbewertet hoeheres Risiko tragen
(Sharpe Ratio niedriger) -- die langfristige Wachstumsrate haengt gemaess Kelly-Formel
vom Quadrat der Sharpe Ratio ab, nicht von der nominalen Rendite.
""",
    ),
    (
        "logout",
        "M. Exit-Strategien, saisonale Strategien & High-Frequency-Trading",
        """
Exit-Signale lassen sich auf vier Grundtypen zurueckfuehren: feste Haltedauer (Standard
bei Momentum- wie Mean-Reversion-Strategien, wobei die Ornstein-Uhlenbeck-Halbwertszeit
bei Mean-Reversion eine robuste Schaetzgrundlage liefert), Zielkurs/Profit-Cap (bei
Mean-Reversion der geschaetzte Mittelwert, bei Momentum nur mit fundierter
fundamentaler Kursziel-Schaetzung sinnvoll), das jeweils neueste Entry-Signal als
Exit-Trigger (bei Momentum-Modellen faktisch ein rational begruendeter "Stop-Loss ohne
fixe Schwelle": dreht das Signal, hat sich die Trendrichtung geaendert) sowie explizite
Stop-Preise (siehe Abschnitt H -- bei Mean-Reversion meist kontraproduktiv).

Saisonale Strategien (Kalendereffekte) haben laut Chan in Aktienmaerkten in den letzten
Jahren stark an Kraft verloren -- der klassische "Januar-Effekt" (im Vorjahr schlecht
performende Small Caps erholen sich im Januar wegen nachlassenden
Steuerverkaufsdrucks) sowie ein Jahr-ueber-Jahr-Momentum-Effekt (Aktien, die im selben
Kalendermonat im Vorjahr am besten liefen, kaufen) zeigen im Backtest ueber die letzten
Jahre negative statt positive Renditen -- Chans eigene Tests bestaetigen den
Wirkungsverlust nach 2002. Ganz anders bei Rohstoff-Futures, wo saisonale Muster nach
wie vor durch "echte" physische Nachfrage getrieben und daher robuster sind: Ein Kauf
des Mai-Benzin-Futures Mitte April mit Verkauf Ende April war in 19 von 21 Jahren
profitabel (getrieben von der bevorstehenden US-Sommer-Fahrsaison), ein analoger
Erdgas-Trade (Kauf Ende Februar, Verkauf Mitte April, getrieben von steigender
Klimaanlagen-Nachfrage im Sommer) war in den meisten der letzten Jahre profitabel, aber
deutlich volatiler -- Chan warnt hier ausdruecklich vor Uebergewichtung, da
Erdgas-Futures historisch fuer spektakulaere Fondszusammenbrueche (Amaranth Advisors,
-6 Mrd. USD) verantwortlich waren.

High-Frequency-Trading (im Buch pragmatisch definiert als jede Strategie ohne
Uebernachthaltung) erzielt seine hohe Sharpe Ratio primaer durch das "Gesetz der
grossen Zahlen": Bei hunderten oder tausenden Trades pro Tag mittelt sich die
prozentuale Renditeabweichung stark heraus, was einen deutlich hoeheren, statistisch
abgesicherten Hebel erlaubt als bei laengerfristigen Strategien. Backtesting ist hier
allerdings ungleich anspruchsvoller (Geld-Brief-Spanne, nicht nur Schlusskurse, sind
zwingend noetig; oft sind sogar historische Orderbuchdaten oder Live-Tests
unumgaenglich), und die Ausfuehrungsgeschwindigkeit selbst (Sprache C statt Python,
Serverstandort nahe der Boerse) wird zum entscheidenden Erfolgsfaktor -- fuer
Einzelanleger ambitioniert, aber laut Chan ein sinnvolles langfristiges Ausbauziel,
sobald Kapital und Infrastruktur mitwachsen.
""",
    ),
    (
        "emoji_events",
        "N. Fazit: Koennen unabhaengige Trader institutionelle Fonds schlagen?",
        """
Das Schlusskapitel beantwortet die titelgebende Frage des Buchs mit einem klaren Ja --
mit einer praezisen Begruendung: dem Konzept der Kapazitaet. Die meisten wirklich
profitablen, einfachen Strategien haben eine geringe Kapazitaet (sie funktionieren nur
mit ueberschaubaren Betraegen, oft als eine Art kurzfristiger
Liquiditaetsbereitstellung), sind fuer Multi-Milliarden-Fonds also uninteressant oder
sogar unbrauchbar -- genau das ist die strukturelle Nische unabhaengiger Trader. Grosse
Fonds muessen dagegen selbst als Liquiditaetsnachfrager auftreten, halten Positionen
daher zwangslaeufig laenger, sind damit staerker Regime-Risiken ausgesetzt, geraten
durch Konkurrenzdruck in immer komplexere (und damit data-snooping-anfaelligere)
Modelle, landen wegen aehnlicher zugrunde liegender Ineffizienzen oft in aehnlichen
Positionen (Ansteckungsgefahr bei Marktstress) und unterliegen zusaetzlich
hausgemachten, oft nicht-quantitativen Restriktionen durch das Management (Verbot
bestimmter Strategietypen, Umsetzungsdruck bei ersten Gewinnen,
Panik-Liquidation bei ersten Verlusten). Hinzu kommt ein Anreizproblem: Wer fremdes
Geld verwaltet, traegt selbst kaum das volle Abwaertsrisiko (schlimmstenfalls
Kuendigung), was zu strukturell riskanterem Verhalten verleitet, wie die Faelle
Societe Generale (Jerome Kerviel, 7,1 Mrd. USD Verlust) eindruecklich zeigen.

Fuer das eigene Wachstum jenseits der durch die Kelly-Formel vorgegebenen
Kapitalgrenze empfiehlt Chan: neue, unkorrelierte Strategien statt reiner
Hebelerhoehung (z. B. hoeherfrequente Strategien mit entsprechender
Infrastruktur-Investition, oder umgekehrt laengerfristig haltende Strategien mit
geringerer Sharpe Ratio, aber hoeherer Kapazitaet), Erweiterung auf neue
Anlageklassen (Futures, Devisen), Zusammenarbeit mit anderen Tradern/Subadvisoren zur
Diversifikation der Ideenquellen, sowie fortlaufende Automatisierung, um die eigene
Zeit auf Forschung statt Betrieb zu konzentrieren. Strategien verlieren ueber die Zeit
an Wirksamkeit ("Alpha Decay"), sobald mehr Marktteilnehmer dieselbe Ineffizienz
erkennen, und groessere Regimewechsel treten laut Chan im Schnitt etwa einmal pro
Jahrzehnt auf -- kontinuierliche Forschung ist daher kein optionaler Zusatz, sondern
die Grundvoraussetzung, um langfristig im Geschaeft zu bleiben.
""",
    ),
]

for icon, title, content in BOOK_SECTIONS:
    with st.expander(title, icon=f":material/{icon}:"):
        st.markdown(content)
