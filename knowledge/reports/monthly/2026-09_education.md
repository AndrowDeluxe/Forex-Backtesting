# Monthly Checkup - Education - September 2026

Synthese aus den vier Weeklies KW36-KW39 und dem, was der Monat in Memory
und `knowledge/` hinterlassen hat. Der Monat ist bis 27.09. erfasst.

## 1. Was stand den Monat an / Hauptthemen

**Der September war der Monat, in dem die Portfolio-Bridges echtes Geld
bekamen. Seine eigentliche Arbeit war herauszufinden, was sie tatsaechlich
tun.**

- **Anfang (KW36):** Konsolidierung auf drei Portfolio-Bridges
  abgeschlossen, Data Lake als Datenquelle fuer Funded, Dashboard/Changelog
  als Cockpit etabliert.
- **KW37:** FK geht live. Der Befund des Monats beginnt: **"Live" heisst
  nicht "handelt"** (5 Tage scharf, 0 Orders; `CAPITAL_WEIGHT` dokumentiert,
  aber nie angewendet).
- **KW38:** reine Infrastruktur-Woche. Acht Funde mit demselben Kern: **Das
  System meldete X und tat Y** (Sim-Filter ist kein Live-Gate, 0-Tick nach
  `symbol_select`, IQ handelt keine Aktien, Lake-Zeitstempel durch
  Windows-Standortdienst).
- **KW39:** die Forschungs-Woche. CTNL, OU und die Papers wurden
  durchleuchtet; daneben lief die Reparatur des Git-Sync und der
  Report-Kette.

## 2. Aktive Zeiten

Das Muster ueber den Monat ist stabil: **lange Abende (21-24 Uhr), dazu
einzelne Vormittagsbloecke, und an Arbeitstagen oft gesammeltes Committen
spaet abends oder am Wochenende.** KW39 hatte die extremste Verdichtung (23
Commits an einem Mittwoch) und das erste wirklich freie Wochenende. Drei der
vier Weekly-Laeufe kamen verspaetet oder fielen aus, weil der PC am
Sonntagabend nicht lief.

## 3. Die 3 groessten Learnings des Monats

**1. Status ist keine Ausfuehrung, und ein Schutz ist nur so gut wie seine
schwaechste Bridge.** Der Faden zieht sich durch den ganzen Monat:
- FK war "LIVE" und handelte nicht (KW37).
- Ein Sim-Filter "begrenzte" nur die Simulation (KW38).
- Ein Kill-Switch war "in alle Bots nachgeruestet", aber nur in die
  Paper-Bots und in FK (KW39).

Die Konsequenz fuer die Denkweise: **Jede Aussage ueber das System braucht
einen Beleg aus der Ausfuehrungsschicht** (Broker-Deal, Log-Zeile), nicht
aus Config oder Doku. Memory `live_ist_nicht_gleich_handelt`,
`ctnl_sim_filter_is_not_live_gate`.

**2. Kosten und Struktur zuerst pruefen, dann Parameter.** Drei
Forschungslinien endeten im September mit derselben Lehre:
- Beim OU-Modell frisst die Reibung den Edge, und nur die Einstiegstiefe
  hilft (Memory `ou_modell_edge_eaten_by_costs`).
- Bei CTNL waren die Kosten *ueber*schaetzt, der Edge liegt nur long, und
  der groesste Hebel war die falsch verdrahtete Ribbon-Richtung (Memory
  `ctnl_kosten_ueberschaetzt_gate_traegt`, `ctnl_edge_nur_long`,
  `ctnl_ribbon_als_richtung`).
- Beim EU-Open-Paper endete das Sample 2018 (Memory
  `eu_open_edge_zerfallen`).

In keinem der Faelle war die Parametersuche der Durchbruch.

**3. Stille Fehler in der eigenen Werkzeugkette sind gefaehrlicher als
laute im Bot.** Im September haben sich vier Mechanismen selbst unsichtbar
gemacht:
- `git_sync_push` frass per Stash + `reset --hard` Arbeit.
- `mt5_pull` kappte das Tagesende.
- Der Report-Task lief im Standby ins Leere.
- Ein kaltes Terminal lieferte leere Historie.

Jeder wurde nur durch einen Gegencheck gegen eine zweite Quelle entdeckt.
**Die Lehre ist eine Gewohnheit: Nullergebnisse gegen eine unabhaengige
Quelle pruefen, bevor man sie glaubt.**

## 4. Neues Wissen (Papers/Ideen) im Monat

- **Papers:** drei Papers am 22.09. gesichtet ->
  [[24h-renditestruktur-und-informationskette]]; ein Edge-Kandidat
  ([[eu-open-renditefenster]]) sauber getestet und negativ abgeschlossen.
- **Forschungsnotizen:** [[gold-ctnl-edge-portfolio]],
  [[ctnl-kostenvalidierung]], [[ou-modell-kostenvalidierung]],
  [[ek-risiko-kalibrierung-audit]], [[orb-exit-logik-neubewertung]].
- **Ideen-Inbox:** Im Monat kam wenig Neues hinein. Der Punkt "FK-CLS-Scan
  am Sonntag" (17.09.) ist unsortiert. Der Clippings-Stapel (14 laut Lint
  vom 21.09.) ist weiter unverarbeitet.

## 5. Verbesserungen (netto)

- Drei Portfolio-Bridges mit echtem Geld, alle nachweislich ausfuehrend.
  FK seit KW39 auch profitabel auf Bot-Ebene.
- Ausfuehrungsqualitaet: Restlaufzeit-Gate, Pending-Order-ORB (Variante C),
  0-Tick-Fix, Kommentar-Laenge-Fix. Seit KW38 keine Order-Rejects mehr in
  den Logs.
- Risiko: Offenes-Risiko-Deckel auf Funded, E5-c auf EK, CTNL-Kill-Switch
  auf FK. Alle haben im Monat nachweislich gegriffen.
- OU-Modell auf eine validierte Konfiguration umgestellt.
- Werkzeugkette: Git-Sync-Fix, `mt5_pull`-Fenster-Fix, Soll/Ist als festes
  Modul, Waechter fuer fehlende Reports.

## 6. Verschlechterungen / offen in den Oktober

- **EK -19,4 % im Monat, beschleunigend**, bei erhoehtem Hebel.
- **CTNL-Kill-Switch fehlt auf Funded/EK.** Ribbon-Entscheidung (E6) offen.
- **Handtrades auf dem FK-Bot-Konto** (-1.232,82 USD).
- **Gold-Klumpenrisiko:** Drei von sechs Beinen handeln XAUUSD.
- **Soll/Ist fuer ORB seit Variante C unzuverlaessig.**
- **Report-Automatik haengt am Wake-Timer.**
- 93 Altstashes warten auf Loeschfreigabe; die ORB-BE-Frage im alten
  Marktorder-Pfad ist offen.

## 7. Optimierungsmoeglichkeiten fuer Oktober

1. CTNL-Schutz vereinheitlichen, entweder per Kill-Switch oder per
   Ribbon-Richtung. Eine Entscheidung loest beides.
2. EK-Risiko als Ganzes neu bewerten: Mindestlot, Hebel, Gold-Anteil.
3. Gold-Klumpen im Portfolio messen: Korrelation der drei Gold-Beine live.
4. Die Reporting-Kette gegen stille Nullen haerten (Retry/Warnung in
   `mt5_pull`, ORB-Zuordnung im Soll/Ist).
5. Die Handtrade-Regel fuer die Bot-Konten festlegen.
