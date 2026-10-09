# Project: Persönlicher Tradingplan -- Validierung

**Ziel**: Jeden Bestandteil des aktuellen persönlichen Tradingplans einzeln
durchgehen, backtesten und validieren. Was robust funktioniert wird
übernommen und als geprüfter Baustein (Parameter/Filter/Modell) festgehalten
-- am Ende eine handverlesene Sammlung, auf die man händisch zugreifen kann,
statt eines ungeprüften Regelwerks im Kopf.

**Status**: Setup -- Bestandteile-Liste wird gerade erstellt, noch nichts
validiert.

**Vorgehen pro Bestandteil**:
1. Bestandteil isolieren + präzise definieren (Regel/Parameter/Schwelle,
   nicht nur vage Idee)
2. Backtest bauen/laufen lassen (bestehende Infrastruktur wiederverwenden,
   wo möglich -- Instrument/Zeitraum an bereits gecachte Daten anpassen)
3. Validieren: robust über Zeit (IS/OOS-Split) und ggf. über Instrumente?
   Kein Overfitting auf eine Teilperiode?
4. Validiert -> in `resources/persoenlicher-tradingplan.md` als Baustein
   festhalten, mit Link zum Ergebnis (Commit/Streamlit-Seite).
5. Nicht validiert -> als verworfen dokumentieren (mit Grund), nicht
   stillschweigend löschen -- verworfene Ideen sind auch Erkenntnis.

**Seit 2026-10-04**: Die Bestandteile-Liste wird aus Strang 0 (Inventur)
des Dachprojekts [[quant-diskretionaer-fusion]] befüllt -- hier, nicht
doppelt dort gepflegt.

## Bestandteile-Checklist

**Entwurf vom 09.10.2026 (Inventur, Strang 0). Noch nicht vom Nutzer
bestätigt.** Hauptquelle ist die OneNote-Seite „⭕️Tradingplan 1.1 2026“
(Abschnitt „Oktober 2026“, inhaltlich gleich mit „Final Tradingplan
2025/2026“). Ergänzt wird sie durch den Abschnitt „Meine Trading Edges“,
die „Dayli Checklist und Great Reset“ (Stand 04/2026) und „Elite 3/Tracking“.
Das Inhaltsverzeichnis aller 3.225 Seiten liegt in
`fusion_lab/raw/onenote/_toc.md` und `_pages.csv` (gitignored). Erzeugt
wird es mit `python -m fusion_lab.inventory.onenote_toc`.

Legende Herkunft: **Plan** = eigener Tradingplan; **Kurs** = Mentor-
Material, mit Kursnamen. Legende Stand: ✅ im Repo getestet, ⛔ getestet und
negativ, ◐ verwandt, aber nicht dasselbe getestet, ○ offen.
„Nur Chartbild“ heißt: Die Regeln stehen nur als Annotationen im Screenshot,
die OCR liefert sie nicht. Dort muss der Nutzer die Regel diktieren (Edge
Card, Phase 0).

### A Setups (Einstieg)

Im Plan bekommt jedes Setup einen Punktestand, aus dem das Risiko folgt
(siehe Abschnitt C).

- [ ] **A1 CTNL Basic Entry H1** (Kurs: Come to the Next Level). Range,
  Inducement/Early Ones, drei BOS (Power of Three), Einstieg im Retrace auf
  Höhe des ersten BOS. ✅ Live als `ctnl_reversal`, siehe
  [[gold-ctnl-edge-portfolio]]. `ctnl_continuation` ist seit 01.10.
  stillgelegt.
- [ ] **A2 Asia Edge** (Plan): 01:00–02:00 Uhr, interner Liquiditätsspike,
  dann Aufkauf/Abverkauf. Dazu Seite „Asia Session Edge (Gold Edition)“
  (leer) und „Asian Sweep Entry Strategie“ (2024). ◐ Gold ASB ist ein
  Ausbruch, A2 dagegen eine Umkehr nach dem Spike.
- [ ] **A3 London Edge** (Plan; „London Edge mit Jazmin“, „Time and Price
  Edge“, „Final Pre Range London Manipulation Edge“): Pre-London- oder
  Asia-Liquiditätsspike, Asia-Range-Retracement, Tageshoch/-tief geprintet,
  Settlement-Aktion. SL unter das Asia-Tief bzw. den Spike, Ziel-POI
  11–12 Uhr. Die Time-and-Price-Statistik des Nutzers lag 04/2025 bei 56 %
  Trefferquote und RR 1:4,8. ⛔ Zwei Ausbruchsvarianten sind archiviert:
  [[london-cls-breakout-eurusd]] und [[london-range-bos-retest-eurusd]].
  Letztere ist identisch mit „New London Edge EU only“ (Elite 3, 08/2026);
  dort hat der Nutzer selbst notiert, sie sei 6 Monate profitabel und
  kippe dann. ○ Die Manipulations-/Spike-Umkehr selbst ist ungetestet.
- [ ] **A4 NY- und Killzone-Edge** (Plan; „Final NY Continuation/Reversal
  Entry Edge“, Seiten „16:00 Uhr Continuation/Reversal“, „NY Entry Model
  mit Tim“): London holt externe Liquidität, NY-Liquiditätsspike,
  Tagesrange beachten. ◐ [[ny-open-orb-sp500]] und
  [[overnight-reversal-erste-halbe-stunde]] sind Indizes und Ausbrüche,
  nicht dasselbe. Die Final-Seiten sind nur Chartbilder.
- [ ] **A5 HTF Entry (Inducement + Fib)** (Plan): M15–H4, Trend mit
  mindestens 2 BOS, nur der dritte Impuls, Premium/Discount-Fib in einem
  POI, Inducement mit direkter Reaktion, Limit oder Stop nach Spike. Ziel
  ist die nächste Liquidität bzw. der nächste POC. ◐ Ähnlich wie
  [[mt5-haupt-bot-trend-pullback]], aber nicht dasselbe.
- [ ] **A6 H4 Entry** (Kurs/Plan, „H4 Entry Strategie Jakob“): Bias, dann
  mindestens 2 H4-Kerzen ausmanipuliert (großer Docht). Einstieg zum
  Schlusskurs oder eine Kerze später, SL hinter der Manipulation. Die
  Beispiel-Trades für EU 2023 liegen nur als Chartbilder vor. ○
- [ ] **A7 Daily Entry Advanced** (Plan): IPDA-Shift (Tag 8/14),
  Makro-Bias, 3 Daily-Kerzen ausmanipuliert (für Fortsetzung) oder ein
  Fractal (für Wende), Einstieg nach dem Daily-Close. ⛔ Der IPDA-Teil ist
  negativ ([[ipda-zyklus-eurusd]]). ○ Die Manipulationsregel selbst ist
  ungetestet.
- [ ] **A8 Spike-/Manipulations-Edges** (Plan, alle mit „Final“
  markiert): Midnight Spike, Liquiditätsspike in sentimentalen Zeiten, Pre
  Continuation, Pre Manipulation. ○ Nur Chartbilder, der Nutzer muss die
  Regeln diktieren.
- [ ] **A9 Settlement-Edges** (Kurs: Elite 2, „Settlements Ficker Edge“
  13 kB, „Edge-Erweiterung Settlements und Nadaraya/Bollis“): Ablauf
  Pre-Settlement Akkumulation, dann Manipulation, dann Expansion. ◐ Liegt
  nahe an `cls_practical` (live, auf Bewährung,
  [[cls-practical-kostenvalidierung]]).
- [ ] **A10 Uhrzeit-Statistik** (Plan): Uhrzeiten mit der höchsten
  Wahrscheinlichkeit für Tageshoch/-tief, z. B. Hoch um 1:00 Uhr 14 %, um
  9:00 Uhr 10,5 %; Tief um 16:00 Uhr 12,4 %. Herkunft der Zahlen ist
  unklar. ○ Lässt sich mit Daten direkt nachzählen.

### B Bestätigungen (Confis)

Diese Bausteine stecken in mehreren Setups. Sie werden einzeln als Filter
getestet, nicht als eigenes Setup.

- [ ] **B1 Indikator-Ausschläge**: Nadaraya-Watson-/Bollinger-Ausbruch,
  Stoch-RSI M15, RSI-/Multi-RSI-Cross, MA-Cross M30, MACD-/Volumen-
  Divergenz. ○
- [ ] **B2 Fib Premium/Discount, Pivots, POI/POC (Volumenprofil)**. ○
- [ ] **B3 Runde Zahlen („Wholelevel“)**. ⛔ Als Fade negativ: Sie wirken
  eher als Magnet ([[smh-elite-mikrostruktur]], K1).
- [ ] **B4 Einstieg erst nach Kerzenschluss**, doppelter BOS M5,
  CHOCH/BOS. ◐ Teilweise in der CTNL- und CLS-Fractal-Logik enthalten.

### C Punktesystem und Risiko

- [ ] **C1 Konfluenz-Score → Risikostufe**: Je Setup wird gezählt, wie
  viele Confis erfüllt sind, daraus folgt die Stufe C/B/A/A+ mit 0,5 bis
  2 % (Daily bis 5 %). Mindestzahl an Confis zwischen 5 und 10. ○ **Für den
  Bot zentral.** Zu prüfen ist, ob ein höherer Score die Erwartung pro
  Trade überhaupt steigert. Wenn nicht, hat die Risikostaffel keine
  Grundlage.
- [ ] **C2 Basisrisiko je Zeitebene**: LTF 0,5 %, HTF 1 %, Makro/IPDA 5 %.
  Tagesstopp LTF bei 2 %, Wochenstopp bei 5 %; HTF 5 % bzw. 10 %; offenes
  Risiko höchstens 10 %. Laut Daily Checklist 04/2026 strenger: 2 % am
  Tag, 5 % in der Woche, 10 % im Monat. ○
- [ ] **C3 Risiko aus Gewinnen**: Es werden höchstens 50 % der Gewinne aus
  Tag, Woche oder Monat neu riskiert, im Drawdown wird nie aufgestockt (im
  HTF ist es erlaubt). ◐ Bei CTNL brachten Serienstopp und Halbierung
  nichts ([[ctnl-serienstopp-vs-risikohalbierung]]).
- [ ] **C4 Handelslimits**: höchstens 2 Ideen und 2 SL pro Tag, 6 Trades
  pro Woche, 20 pro Monat, 3 Handelstage pro Woche. „SL SL Stopp / TP TP
  Stopp“, 3 h Pause nach 2 Trades. ○ Lässt sich als Portfolio-Simulation
  über bestehende Trade-Listen prüfen.

### D Trade-Management und Ausstieg

- [ ] **D1 Twin-Trade**: zwei Positionen mit je halbem Risiko, eine mit
  festem CRV 1:2 bis 1:3, eine als Läufer bis zur externen Liquidität. ○
- [ ] **D2 Teilgewinne**: 1/3 an POIs; 50 % schließen bei 50 % Drawdown,
  wenn die Lage unklar wird. ○
- [ ] **D3 Breakeven ab 1:1**. ⛔ BE verschlechterte jede getestete
  London-Konfiguration ([[london-range-bos-retest-eurusd]]).
- [ ] **D4 Ziel = externe Liquidität bzw. Zeitfenster 11–12 Uhr**, dazu
  Pip-Erwartung von Tag und Session (ADR). ○

### E Makro und Off-Chart-Basis

Strang 3 des Dachprojekts.

- [ ] **E1 News-Workflow „Fundamentals Edge“** (Kurs: Incentive/Elite):
  Vorlaufindikatoren (PMI, UoM, Renditen, Zinskurve, Rohstoffe) werden mit
  Echtzeitdaten bestätigt (NFP, CPI, GDP) und dann mit
  Zentralbank-Reaktionen abgeglichen. Handeln erst nach der Bestätigung.
  ◐ Der Zins-Spread allein war negativ ([[bond-yield-spread-indikator]]).
- [ ] **E2 Weekly-IPDA, Regimeshift, ZB1!, Inflation, Taylor-Regel**
  („DIE BASIS“ im Plan; „Taylor Zins Regel“ unter Makro Education).
  ⛔ IPDA-Zyklus negativ. ○ Der Rest ist offen.
- [ ] **E3 G8-Währungsstärke und SMT Macro Desk** (Kurs: SMHxSMT bzw. SMH
  Daily Update, Telegram). Lässt sich nachbauen, siehe
  [[quant-diskretionaer-fusion]]. ○
- [ ] **E4 Gatekeeping-Prozess / endogene und exogene Analyse** (Kurs:
  Incentive 3, „Aufarbeitung GS Prozess“, 100 kB). ○ Noch nicht gesichtet.

### F Nicht automatisierbar

Emotions- und Mindset-Checklisten, Pre-Trading-Routine, Kontensystem und
Payout-Regeln. Ein Bot kann sie nicht übernehmen. Sie bleiben im
händischen Plan und werden nicht gebacktestet. Den Nutzen der Handelslimits
(C4) misst die Simulation trotzdem.

**Verknüpfung**: [[paper-verarbeitung]] (ähnlicher Prozess, hier ist die
Quelle aber der eigene Tradingplan statt ein externes Paper)
