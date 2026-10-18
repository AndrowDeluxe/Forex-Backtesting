"""Inhalt der Notion-DB "📚 Makro-Education": je Makro-Baustein unserer Analyse
eine kurze Lernkarte. Eigene Zusammenfassung (kein Zitat) aus
knowledge/resources/makro-faktoren-katalog.md (OneNote-Inventur 12.10.2026)
plus den eigenen Bausteinen (G8-Nachbau, SMT-Report-Format). Quelle der
Wahrheit ist diese Datei; Notion spiegelt sie (fusion_lab/notion/sync_education.py).

Status: "ungetestet" = nur Material; "Baustein aktiv" = im System gebaut;
"getestet: kein Edge" / "getestet: Edge" = Ergebnis nach Overfitting-Sperre.
"""

TOPICS = [
    {
        "titel": "Zinserwartungen & Notenbank",
        "nr": 1,
        "kurz": "Der wichtigste Treiber für Währungen: nicht das Zinsniveau, sondern ob die Notenbank "
                "schneller oder langsamer handelt, als der Markt bereits eingepreist hat.",
        "wirkung": "Weniger Senkungen als erwartet stützen die Währung, mehr Senkungen schwächen sie. Wer "
                   "zuerst und stärker senkt, verliert relativ. Sind die Daten schwach, die Notenbank aber "
                   "noch hawkish, preist der Markt die Wende vorab ein.",
        "rolle": ["Regime", "Ranking", "Gate"],
        "daten": "FRED DGS2 (2-jährige US-Rendite als Erwartungs-Proxy), Leitzinsen; FedWatch/OIS "
                 "(Historie nicht frei); Notenbank-Statements, Dot Plot, Minutes.",
        "status": "ungetestet",
        "widerspruch": "Futures preisen Senkungen oft zu früh ein -- trotzdem gelten sie als Hauptmaß "
                       "der Erwartung.",
        "quellen": "Makro Education: Macro Report 20.10.2024, Top Down Teil 2, Big Makro Stuff; "
                   "Bankreports: ING, Breakdowns USD/EUR.",
        "regeln": [
            "Abweichung vom eingepreisten Pfad bewegt -- das Niveau allein nicht.",
            "Divergenz handeln: Währung der Notenbank, die später/weniger senkt, gegen die, die früher senkt.",
            "Rhetorik und Daten vergleichen: passen sie nicht zusammen, folgt der Markt den Daten.",
            "Kein EUR-Long, solange die EZB vor der Fed senkt (Gate aus den Breakdowns).",
        ],
    },
    {
        "titel": "Zinsdifferenz & Carry",
        "nr": 2,
        "kurz": "Kapital fließt dorthin, wo es mehr Rendite bekommt. Relevant ist vor allem, wie sich der "
                "Zinsabstand zweier Länder verändert.",
        "wirkung": "Steigt der Zinsabstand zugunsten einer Währung, wird sie gekauft. Hohe Zinsen bei "
                   "niedriger Volatilität ziehen Carry-Trades an; der Yen dient als Finanzierungswährung. "
                   "USDJPY folgt laut Bank stark dem Abstand 10-jährige US- gegen japanische Anleihe; ab "
                   "etwa 152 droht eine Intervention.",
        "rolle": ["Ranking", "Gate", "Kein-Trade"],
        "daten": "FRED DGS2/DGS10, Länder-Renditen (OECD/EZB/BoE), JGB (MoF Japan), implizite Volatilität.",
        "status": "getestet: kein Edge",
        "widerspruch": "Unser Zins-Spread-Indikator (Niveau) hatte keinen Edge; die Notizen sagen, die "
                       "Änderung erkläre FX besser -- das ist noch nicht getestet.",
        "quellen": "Makro Education: Macro Report 20.10.2024; Bankreports: Breakdown EUR/USD, UniCredit, "
                   "Goldman; Incentive: Hausaufgabe 2.",
        "regeln": [
            "Renditeänderungen statt Renditeniveaus betrachten.",
            "USDJPY im Interventionsgebiet nicht kaufen.",
            "Carry funktioniert bei fallender Volatilität, bricht bei Risk-off.",
        ],
    },
    {
        "titel": "Inflation",
        "nr": 3,
        "kurz": "Inflation bestimmt, wie lange die Notenbank straff bleiben muss. Entscheidend sind Kern- "
                "und Dienstleistungsinflation, nicht die Schlagzeilenzahl.",
        "wirkung": "Inflation über Erwartung führt zu höheren Zinserwartungen und stützt die Währung -- "
                   "solange die Wirtschaft nicht schwächelt. Eine fallende Gesamtinflation reicht nicht für "
                   "Senkungen, wenn Dienste und Löhne hoch bleiben. Erzeugerpreise und Inflations"
                   "erwartungen laufen voraus.",
        "rolle": ["Ranking", "Szenario", "Gate"],
        "daten": "FRED CPILFESL (Kern-CPI), PCEPILFE, PPIFIS, T10YIE (Breakeven), MICH; "
                 "Kalender mit Konsens für die Überraschung.",
        "status": "ungetestet",
        "widerspruch": "Mal gilt CPI als wichtigster Termin, mal der Arbeitsmarkt -- es hängt vom "
                       "aktuellen Marktthema ab.",
        "quellen": "Makro Education: Blueprint 2024, Inflation Angelo, Macro Report 2024; "
                   "Bankreports: Goldman CPI-Vorschau, CPI Angelo; News: CPI Analyse.",
        "regeln": [
            "Monatsrate vor Jahresrate lesen; Supercore (Dienste ohne Wohnen) beachten.",
            "Überraschung = Ist minus Konsens; nur die Überraschung bewegt.",
            "Gemischte Daten (Inflation hoch, Wachstum schwach): Gesamtbild statt Einzelzahl.",
        ],
    },
    {
        "titel": "Wachstum & Konjunkturzyklus",
        "nr": 4,
        "kurz": "Man handelt nicht Währungen, sondern Ansichten über Volkswirtschaften: die stärkere "
                "gegen die schwächere.",
        "wirkung": "Sinkendes Wachstum macht die Notenbank vorsichtiger und schwächt die Währung -- immer "
                   "relativ zum Gegenland. PMI über 50 heißt Expansion. Die Zyklusphase entscheidet, wie "
                   "Daten zu lesen sind.",
        "rolle": ["Regime", "Ranking", "Szenario"],
        "daten": "FRED GDPC1, GDPNOW, RSAFS (Einzelhandel), UMCSENT, HOUST; PMI/ISM aus dem Kalender.",
        "status": "ungetestet",
        "widerspruch": "",
        "quellen": "Makro Education: GDP, Top Down Teil 1+2, Zusammensetzung GDP, Wirtschaftszyklen; "
                   "Incentive: Wirtschaftszyklus.",
        "regeln": [
            "Zuerst die Zyklusphase bestimmen, dann die Daten deuten.",
            "Bei zwei schwachen Wirtschaften gewinnt die weniger schwache.",
            "Kette der Abschwächung: Nachfrage, Lager, PMI, Entlassungen, Kreditspreads.",
        ],
    },
    {
        "titel": "Arbeitsmarkt & Rezessionssignale",
        "nr": 5,
        "kurz": "Der Arbeitsmarkt entscheidet, ob die Notenbank senken darf, und er kippt in Rezessionen "
                "plötzlich statt allmählich.",
        "wirkung": "Starker Arbeitsmarkt: weniger Senkungen, Dollar fester. Löhne treiben die Dienste"
                   "inflation. Sahm-Regel: steigt die Arbeitslosenquote um 0,5 Prozentpunkte über ihr Tief, "
                   "beginnt meist eine Rezession; laut eigenem Muster springt sie 7-15 Monate nach dem Tief.",
        "rolle": ["Regime", "Szenario", "Gate", "Kein-Trade"],
        "daten": "FRED PAYEMS, UNRATE, ICSA (Erstanträge), SAHMREALTIME, JTSJOL, Lohnreihen.",
        "status": "ungetestet",
        "widerspruch": "",
        "quellen": "Bankreports: Rezession 05.08.2024, NFP Angelo, Breakdown USD; Makro Education: "
                   "Macro Report 20.10.2024.",
        "regeln": [
            "Erstanträge dauerhaft über etwa 250.000 = Warnsignal.",
            "Revisionen und Haushalts- gegen Unternehmensumfrage vergleichen.",
            "Bis NFP die Volatilität abwarten, nicht kurz davor einsteigen.",
        ],
    },
    {
        "titel": "Liquidität",
        "nr": 6,
        "kurz": "Wie viel Geld im System ist und was es kostet. Mehr Liquidität trägt Risiko-Assets, "
                "weniger belastet sie.",
        "wirkung": "Positiver Liquiditätsimpuls (Fed-Bilanz wächst, Reverse-Repo und Treasury-Konto "
                   "geben Geld frei) stützt Aktien, Gold und Bitcoin. Bilanzabbau entzieht erst Reserven, "
                   "wenn die Puffer aufgebraucht sind. Enge Finanzierung führt zur Flucht in Dollar und "
                   "Yen.",
        "rolle": ["Regime", "Gate"],
        "daten": "FRED WALCL (Fed-Bilanz), RRPONTSYD (Reverse Repo), WTREGEN (Treasury-Konto), WRESBAL, "
                 "M2SL, DFII10 (Realzins).",
        "status": "ungetestet",
        "widerspruch": "",
        "quellen": "Makro Education: BTC Dynamik, Trader Magazin, Bonds Liq 1, Repo; "
                   "Bankreports: Macro Breakdown NFP-Woche.",
        "regeln": [
            "Liquidität positiv: Risiko-Assets kaufen (Momentum, Rücksetzer); negativ: verkaufen.",
            "Bei Illiquidität dienen Dollar und Yen als Absicherung.",
            "Geldpolitik wirkt mit etwa zwei Jahren Verzögerung auf Rezession und Volatilität.",
        ],
    },
    {
        "titel": "Zinskurve & Anleihen",
        "nr": 7,
        "kurz": "Die Form der Zinskurve verrät, was der Markt über Wachstum, Inflation und künftige "
                "Zinsen denkt.",
        "wirkung": "Inversion (kurz über lang) drückt Bankmargen und ging Rezessionen voraus. Steigt der "
                   "Abstand 10- minus 2-jährig bei fallender 2-jähriger Rendite, sind Senkungen eingepreist "
                   "-- Dollar schwächer. Steigende positive Realzinsen belasten Aktien, Gold und Bitcoin. "
                   "Weite Kreditspreads signalisieren Rezessionsrisiko.",
        "rolle": ["Regime", "Ranking", "Szenario", "Gate"],
        "daten": "FRED T10Y2Y, T10Y3M, DGS2, DGS10, DFII10, BAMLH0A0HYM2 (High-Yield-Spread), SLOOS.",
        "status": "ungetestet",
        "widerspruch": "Vorlauf der Inversion: 12-18 Monate oder rund 2 Jahre; laut einer Notiz nur "
                       "belastbar, wenn Echtzeitdaten mitbrechen.",
        "quellen": "Makro Education: Curves, Anleihenmarkt, Macro Report 2024; "
                   "Incentive: Bond Yield Curve, Hausaufgabe 2.",
        "regeln": [
            "Steepener-Typ unterscheiden: steigt das lange Ende (Bear) oder fällt das kurze (Bull)?",
            "Die 2-jährige Rendite läuft Notenbank-Entscheidungen voraus.",
            "T-Bond-Future als Vorlauf für den Dollar-Index (Lead-Lag, ungetestet).",
        ],
    },
    {
        "titel": "Positionierung & Flows",
        "nr": 8,
        "kurz": "Wer ist schon wie positioniert? Überfüllte Positionen sind Brennstoff für Gegenbewegungen.",
        "wirkung": "Extreme Netto-Positionen der Spekulanten (COT) deuten auf Erschöpfung. Systematische "
                   "Fonds passen ihre Größe der Volatilität an. Monats- und Quartalsende-Rebalancing drückt "
                   "den Dollar vorübergehend.",
        "rolle": ["Ranking", "Gate", "Kein-Trade"],
        "daten": "CFTC COT (wöchentlich, Baustein asian_range_breakout/cot.py vorhanden), VIX; "
                 "Bank-Flussdaten und Risk Reversals meist nicht frei.",
        "status": "ungetestet",
        "widerspruch": "",
        "quellen": "Bankreports: Crédit Agricole (Positionierungsindex), Spectra, Dollar Nachfrage; "
                   "Makro Education: Algos und Flows, Goldman Hedgefunds.",
        "regeln": [
            "Extreme Positionierung als Gegenfaktor-Gate, nicht als Einstieg.",
            "Am Monatsende kurzfristige Dollar-Schwäche einplanen.",
        ],
    },
    {
        "titel": "Risiko-Stimmung & Cross-Asset",
        "nr": 9,
        "kurz": "Liest das Gesamtbild aus Aktien, Anleihen, Gold, Öl, Yen und Bitcoin: wird Risiko "
                "gesucht oder gemieden?",
        "wirkung": "Dollar-Smile: Der Dollar steigt sowohl bei starker US-Wirtschaft als auch bei Panik. "
                   "Bei Risk-on gewinnen AUD, CAD, NZD; bei Risk-off Dollar, Yen, Franken. Steigen USDJPY "
                   "und Aktien gemeinsam, ist Risikoappetit da. Das aktuelle Marktthema bestimmt, welche "
                   "Daten wirken.",
        "rolle": ["Regime", "Gate"],
        "daten": "Kurse: Aktienindizes, VIX, Gold, Öl, USDJPY, DXY; Überraschungsindizes (Eigenbau).",
        "status": "ungetestet",
        "widerspruch": "Ob Makro oder Technik im Konflikt gewinnt, ist in den Notizen widersprüchlich.",
        "quellen": "Bankreports: Citi (Dollar-Smile), Breakdown USD; Makro Education: Risk on Risk Off "
                   "Assets, BTC Dynamik, Marktschwerpunkte.",
        "regeln": [
            "Jeder Trade braucht eine Bestätigung über einen zweiten Markt (Cross-Asset-Gate).",
            "Öl steigt stark: Euro belastet.",
            "China schwach: AUD belastet, auch wenn der Rest dafür spricht.",
        ],
    },
    {
        "titel": "Regime-Schemata",
        "nr": 10,
        "kurz": "Ordnet die Lage in wenige Zustände, aus denen sich typische Gewinner und Verlierer "
                "ableiten.",
        "wirkung": "Vier Quadranten aus Wachstum und Inflation: Goldilocks (Aktien, Rohstoffe vorn, Dollar "
                   "schwach), Reflation (Rohstoffe, zyklische Aktien), Stagflation (Gold, Anleihen), "
                   "Deflation (Anleihen, Gold, Dollar). Dazu Liquidität als dritte Achse und die "
                   "Unterscheidung Risk-on/Risk-off.",
        "rolle": ["Regime"],
        "daten": "Kombination aus Wachstums-, Inflations- und Liquiditätsreihen (siehe Karten 3, 4, 6).",
        "status": "ungetestet",
        "widerspruch": "Mehrere Schemata nebeneinander (Quadranten, 5/7 Zyklusphasen, Angriff/Verteidigung) "
                       "-- der Agent braucht eins als führendes.",
        "quellen": "Makro Education: Wirtschaftszyklen und Goldilock, Macro Report 2024, Trader Magazin, "
                   "Curves.",
        "regeln": [
            "Regime zuerst festlegen, danach Ranking und Trades.",
            "Regime-Stabilität ausweisen: Was würde das Regime kippen?",
        ],
    },
    {
        "titel": "Rohstoffe & Gold",
        "nr": 11,
        "kurz": "Rohstoffe sind Frühindikator für Inflation und Wachstum; Gold zeigt Absicherungsbedarf.",
        "wirkung": "Öl treibt Inflation und belastet Importländer (Euro). Kupfer läuft der Konjunktur voraus. "
                   "Der Baltic Dry Index soll Aktien 8-12 Monate vorauslaufen. Gold auf Rekordhoch wird als "
                   "Absicherung gegen Rezession gelesen; Treiber sind Zentralbankkäufe.",
        "rolle": ["Szenario", "Gate"],
        "daten": "FRED DCOILWTICO; Kupfer- und Goldpreis; Baltic Dry Index (nicht frei).",
        "status": "ungetestet",
        "widerspruch": "",
        "quellen": "Makro Education: Trader Magazin, Big Makro Stuff, Top Down Teil 2; "
                   "Bankreports: Breakdown USD.",
        "regeln": [
            "Öl-Rückgang trotz Geopolitik als Schwächezeichen lesen.",
            "Gold nur nach Bestätigung kaufen, nicht hinterherlaufen (aus den SMT-Reports).",
        ],
    },
    {
        "titel": "G8-Währungsstärke",
        "nr": 12,
        "kurz": "Rangliste der acht Hauptwährungen nach relativer Stärke über 1 Woche, 1 Monat und "
                "3 Monate -- unser Nachbau des SMH-Modells.",
        "wirkung": "Zeigt, welche Währung gerade stark oder schwach ist, und eignet sich, die Gegenseite "
                   "eines Trades zu wählen. Als eigenständiges Signal (stark kaufen, schwach verkaufen) "
                   "2000-2017 negativ.",
        "rolle": ["Ranking"],
        "daten": "FRED-Tageskurse ab 1999, jüngste Tage Dukascopy; täglich in der DB „💱 G8-Stärke“.",
        "status": "Baustein aktiv",
        "widerspruch": "",
        "quellen": "fusion_lab/g8 (Nachbau, Rang-Korrelation 0,95 zum Original); SMHxSMT „Währungsstärke G8“.",
        "regeln": [
            "Kontext, kein Einstieg.",
            "Widerspricht der Score dem Makro-Bild, die Überzeugung senken statt einen Ansatz zu ignorieren.",
        ],
    },
    {
        "titel": "Analyse-Ablauf (Top-down)",
        "nr": 13,
        "kurz": "Die Reihenfolge, in der die Bausteine zu einer Wochenanalyse zusammengesetzt werden.",
        "wirkung": "1 Zyklus und Regime, 2 Marktthema, 3 Daten je Land mit der Frage „stützt das das "
                   "Thema?“, 4 Marktreaktion (Renditen, Gold, Öl, Aktien), 5 Notenbank, 6 Relativvergleich "
                   "stark gegen schwach, 7 Zusatzchecks (COT, Cross-Asset, Bankkonsens), 8 Gesamt- und "
                   "taktische Sicht, 9 erst dann Technik für Einstieg und Risiko.",
        "rolle": ["Regime", "Ranking", "Szenario", "Gate", "Kein-Trade"],
        "daten": "alle oben genannten.",
        "status": "ungetestet",
        "widerspruch": "Im Material gibt es kein festes Entscheidungsschema; die 5 Gates des SMT-Reports "
                       "werden im Agenten festgelegt.",
        "quellen": "Makro Education: Top Down Teil 1+2, Macro Report 20.10.2024; Incentive: Newsworkflow, "
                   "Checkliste, Wochenausblick; SMT-Macro-Desk-Reports.",
        "regeln": [
            "Frühindikatoren bereiten vor, Echtzeitdaten bestätigen -- gehandelt wird erst die Bestätigung.",
            "Kein Event isoliert handeln: Reaktion in Renditen und Kursen abwarten.",
            "Montag nicht erzwingen, wenn die wichtigen Termine Mi-Fr liegen.",
        ],
    },
]
