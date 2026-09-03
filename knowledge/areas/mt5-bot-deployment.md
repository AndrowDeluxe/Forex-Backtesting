# Area: Live-/Paper-Bot-Aufsetzung (MT5)

Laufende Verantwortlichkeit ohne Enddatum -- jede neue Strategie, die live
oder papierbasiert über eine MT5-Bridge/einen Scheduled Task läuft,
durchläuft denselben Aufsetzungs-Prozess, bevor der Task auf "Enabled"
bleibt.

**Grundregel**: ein eigenes, dediziertes MT5-Terminal (eigene Installation/
eigenes Verzeichnis, analog `C:\Users\andre\MT5-Terminals\MT5 Terminal -
FK1` / `- FK2` / `TTP MT5 Terminal - Konto2`) pro Bot/Konto. Nie mehrere
Bots/Bridges über dieselbe gerade laufende Terminal-Instanz fahren.

**Warum (zwei reale Incidents, nicht hypothetisch)**:
1. ORB-Forward-Test hat sich wochenlang mit dem falschen Konto verbunden
   (`connected to account 15514`/`5053949028, expected 110209087`,
   `orb_forward_test_logs/task_run.log`) -- `MetaTrader5`-Python's
   `initialize()` hängt sich an irgendein gerade offenes Terminal, wenn kein
   fester Terminal-Pfad hinterlegt ist, nicht zwingend an das richtige.
2. Gold-ASB-Order wurde am 2026-08-20 zweimal abgelehnt (`retcode=10027,
   comment='AutoTrading disabled by client'`, `gold_asb_logs/task_run.log`)
   -- AutoTrading ist ein Terminal-weiter Schalter; bei geteilten Terminals
   wirkt sich ein deaktivierter Schalter unbemerkt auf alle Bots aus, die
   darüber laufen.

**Standardablauf pro neuem Bot (vor dem ersten produktiven Task-Lauf)**:
1. Neues MT5-Terminal-Verzeichnis unter `C:\Users\andre\MT5-Terminals\`
   anlegen, mit dem Zielkonto einloggen, Pfad fest in der Bridge-Config
   hinterlegen -- nie auf "irgendein laufendes Terminal" verlassen.
2. Im neuen Terminal: AutoTrading-Button aktivieren (grün) UND Extras ->
   Optionen -> Experts -> "Automatisierten Handel zulassen" **UND
   "DLL-Importe zulassen"** anhaken (2026-09-03 ergaenzt -- zwei getrennte
   Haken, leicht zu uebersehen: AutoTrading kann bereits an sein, waehrend
   DLL-Importe noch aus sind. Ohne DLL-Importe verbindet sich das Terminal
   im Broker/GUI ganz normal, aber `MetaTrader5`-Python (nutzt eine
   DLL-Bruecke) bekommt nur `mt5.initialize() (-10005, 'IPC timeout')` --
   sieht wie ein Netzwerk-/Verbindungsproblem aus, ist aber ein reines
   Terminal-Einstellungsproblem. Kostete am 2026-09-02/03 fast 24h
   Fehlersuche fuer 2 neue Funded-Portfolio-Bridge-Konten, weil alle
   bisherigen Terminals dieses Projekts das schon laengst gesetzt hatten und
   niemand mehr daran dachte, es fuer ein BRANDNEUES Terminal zu pruefen).
   Beide Haken verifizieren, bevor der Task live geht.
3. Bridge/Executor: Kontonummer nach Connect gegen die erwartete
   Kontonummer prüfen und bei Abweichung hart sichtbar machen/failen
   (Pattern wie ORB's "connected to account X, expected Y" -- als Standard
   in jede neue Bridge übernehmen, nicht nur ins Log schreiben und
   ignorieren).
4. Ersten produktiven Order-Send im Log auf `retcode`/Erfolg prüfen, bevor
   der Scheduled Task dauerhaft aktiv bleibt.
5. Scheduled-Task-Trigger-Frequenz muss zur Bar-Größe der Strategie passen
   (z.B. Daily-Bar-Strategie = 1x/Tag, keine Wiederholung alle 30 Min
   innerhalb des Tages). Mehrfache Same-Day-Läufe können zustandsbehaftete
   Positions-Logik verfälschen -- gefunden 2026-08-20 im BTC-EMA-Cross-Bot
   (`btc_ema_cross/live_scan.py`): ein Same-Day-Rerun verglich den frisch
   berechneten Stop gegen den Low des VORTAGS (der schon vor dem Entry
   feststand) und löste dadurch zweimal einen fiktiven Stop-Hit aus, ohne
   dass sich der Kurs bewegt hätte. Fix: Exit-/Entry-Logik pro Kalendertag
   nur einmal auswerten (`state["last_scan_date"]`-Guard).

**Grundregel Ende**: kein Bot geht live (auch nicht papierbasiert mit
echter MT5-Order-Kette), bevor Schritt 1-5 einmal durchlaufen und im Log
verifiziert wurden.

## Ergaenzung 2026-08-29 (EK-Portfolio-Bridge-Aufsetzung)

Fuenf weitere, in der Praxis getroffene Probleme + ihre Standard-Loesung --
alle jetzt Teil des Aufsetzungs-Prozesses, nicht nur einmalige Fixes:

6. **AutoTrading-Check jetzt automatisiert statt nur manuell (Schritt 2/3
   oben)**: `connect()` prueft bei JEDEM Lauf `mt5.terminal_info().
   trade_allowed` UND `mt5.account_info().trade_allowed/trade_expert` und
   bricht mit klarer Fehlermeldung ab, statt erst beim ersten echten
   Order-Versand mit `retcode=10027` stumm zu scheitern (siehe Incident 2
   oben). In jede neue Bridge uebernehmen, nicht nur pruefen und vergessen.

7. **`copy_rates_from_pos()` hat eine harte Bar-Anzahl-Grenze pro Aufruf**
   (`Invalid params`, empirisch getroffen bei ~48.000 Bars/Aufruf). Fix:
   `copy_rates_range()` (Datums-Spanne statt Bar-Anzahl) verwenden -- aber
   auch das hat eine Grenze (getroffen bei ~144.000 Bars M5/500 Tage, bei
   ~32.000 Bars M15/500 Tage noch nicht). Faustregel: nur so viel Historie
   anfragen, wie die Strategie TATSAECHLICH braucht (z.B. RVOL-Lookback
   20 Tage statt derselben Tiefe wie ein 200-Tage-EMA-Ribbon-Filter --
   unterschiedliche Timeframes/Berechnungen im selben Signal brauchen oft
   unterschiedlich viel Historie, nicht pauschal die groesste Anforderung
   auf alles anwenden). Reicht das nicht, jahresweise chunken (Vorbild:
   `ny_open_orb/data.py::_fetch_chunked_by_year`, dort urspruenglich gegen
   einen anderen Dukascopy-Bug gebaut, aber dieselbe Technik).
   `copy_rates_range()` braucht ausserdem tz-NAIVE `datetime`-Objekte
   (tz-aware -> `Invalid params`) und `date_to` darf nicht in der Zukunft
   liegen (auch das -> `Invalid params`, leicht zu uebersehen, wenn man
   "bis morgen" puffert wie es andere Datenquellen in diesem Repo tun).

8. **MT5-Zeitstempel sind Server-Wallclock, NICHT UTC** -- epoch-kodiert
   ALS OB UTC, aber tatsaechlich die lokale Uhrzeit des Broker-Servers
   (bei den bisher genutzten Brokern EET/EEST, UTC+2/+3, DST-Wechsel wie
   die EU). Strategien mit festen lokalen Session-Grenzen (z.B. NY-Open
   ORB: 09:30/16:00 America/New_York) brauchen eine korrekte Konvertierung
   -- NIEMALS einen festen Stunden-Offset hart hinterlegen (driftet beim
   naechsten DST-Wechsel unbemerkt um eine Stunde). Stattdessen: echte
   IANA-Zeitzone (`zoneinfo.ZoneInfo("Europe/Helsinki")` o.ae., beliebige
   EU-DST-Zone liefert dieselben Offsets) fuer `tz_localize()` verwenden
   UND bei jedem Lauf empirisch verifizieren (Vergleich eines frischen
   Tick-Zeitstempels eines 24/7-Instruments wie BTCUSD gegen die echte
   `datetime.now(timezone.utc)`, Toleranz wenige Minuten) statt der
   Annahme blind zu vertrauen -- ein Broker-Wechsel der Server-TZ-
   Konvention faellt sonst nie auf, verschiebt aber jede Session-Grenze
   lautlos.

9. **Geteiltes Konto mit einem bereits laufenden Bot** (z.B. ein zweiter
   Bot auf demselben Tickmill-Konto wie OU-Modell-MT5-Bridge): siehe
   Grundregel oben (eigenes Terminal PRO Bot) -- gilt unveraendert auch
   wenn beide auf dasselbe Konto zielen, denn das Risiko ist die geteilte
   Terminal-INSTANZ (Prozess), nicht das Konto selbst (mehrere Terminal-
   Instanzen gleichzeitig auf einem Konto sind brokerseitig normal).
   Zusaetzlich noetig: ein kontoweiter, UNGEFILTERTER Risiko-Deckel
   (`calc_open_risk()` summiert ALLE offenen Positionen des Kontos, auch
   die des anderen Bots), damit der neue Bot nie blind Risiko auf das
   stapelt, was der andere gerade offen haelt. Umgekehrt muss jede
   Positions-VERWALTUNG (Schliessen, SL-Modifikation) strikt nach der
   eigenen `magic`-Nummer filtern, damit sie nie eine fremde Position
   anfasst -- diese beiden Filterregeln sind bewusst gegensaetzlich
   (Risiko-Blick kontoweit offen, Verwaltungs-Zugriff eng gefiltert) und
   beide noetig.

10. **Positionsgroessen-Berechnung**: immer `mt5.order_calc_profit()` fuer
    Verlust/Lot nutzen, nie `trade_tick_size`/`trade_tick_value` von Hand
    verrechnen (ignoriert Kontowaehrung-vs-Symbol-Profitwaehrung-
    Umrechnung, war schon einmal um Faktor 8,6 daneben). Zwei
    Architektur-Varianten je nach Exit-Stil der Strategie: (a) fester
    SL/TP bei Entry, danach keine aktive Verwaltung noetig (Broker
    schliesst selbststaendig) -- generischer "Bracket-Executor" reicht;
    (b) Teilausstieg/Break-Even-Verschiebung/Session-Ende-Notausgang
    noetig -- braucht eigene Positions-Verwaltungslogik, die bei jedem
    Lauf alle offenen Positionen der eigenen `magic`-Nummer durchgeht.
    Nicht (b) fuer (a) ueberbauen oder umgekehrt (a) fuer (b) unterbauen.

## Ergaenzung 2026-09-02 (Funded-Portfolio-Bridge-Erweiterungsversuch)

11. **Vom Nutzer genannte MT5-Login-Nummer IMMER gegen alle Schwester-
    Bridge-Configs cross-checken, BEVOR sie in eine `ACCOUNTS`-Liste mit
    `DRY_RUN=False` geschrieben wird** -- auch wenn der Nutzer die Zugangs-
    daten direkt liefert und explizit "ohne Vorab-Test sofort eintragen"
    sagt. Konkreter Fund: zwei als "neu" gemeldete Konten waren tatsaechlich
    bereits vergeben -- ein TTP-Login gehoerte zu `OU-Modell-MT5-Bridge`'s
    echtem Live-Geld-Konto ("Konto 1"), ein IQ-Markets-Login war das von
    `GoldASB-MT5-Bridge`/`BTC-EMA-Cross-Bridge` bereits geteilte Demo/Eval-
    Konto. Beide waeren sonst innerhalb der naechsten 15 Minuten (Bridge-
    Task-Intervall) live gehandelt worden -- entweder gegen ein fremdes
    Echtgeld-Konto oder doppelt gegen ein bereits von zwei anderen Bots
    genutztes Konto, ohne dass irgendeine der beiden Seiten von der anderen
    weiss (kein gemeinsames Risiko-/Magic-Number-Handling zwischen
    unabhaengigen Bridges). Ein einfaches `grep -r "<login>" ~/*-Bridge/
    config.py` VOR dem Eintragen haette beide Faelle sofort aufgedeckt.
    "Risiko akzeptiert, sofort eintragen" bezieht sich auf das Ueberspringen
    von `check_symbols.py`/End-to-End-Dry-Run -- NICHT auf das Ueberspringen
    des Kollisions-Checks gegen andere Konten.

12. **"DLL-Importe zulassen" separat von AutoTrading pruefen** -- siehe
    Schritt 2 oben, ergaenzt nach fast 24h Fehlersuche (2026-09-02/03) fuer
    die beiden neuen Funded-Portfolio-Bridge-Konten. Zusaetzlicher, nie ganz
    aufgeklaerter Nebenfund: von zwei am selben Tag ueber `mt5setup.exe`
    frisch installierten Terminal-Ordnern verbindet sich EINER zuverlaessig
    per Python, der ANDERE zuverlaessig NICHT -- unabhaengig davon, welches
    Konto gerade darin eingeloggt ist (empirisch mehrfach mit vertauschten
    Konten bestaetigt). Der Ordner-NAME sagt nichts darueber aus, welcher
    der beiden "gesund" ist. Falls ein neu installiertes Terminal trotz
    korrektem Login + beiden Haken (AutoTrading, DLL-Importe) weiter
    `IPC timeout` wirft, ANDERES Konto testweise in denselben Ordner
    einloggen (oder umgekehrt) -- verbindet es dann sauber, liegt es am
    Ordner selbst, nicht am Konto. Pragmatischer Fix: Konto einfach dem
    Ordner zuweisen, der nachweislich funktioniert, statt weiter zu
    debuggen (Config-Kommentar bei `Funded-Portfolio-Bridge/config.py`s
    `ttp1`/`iqmarkets2` als Beispiel).
