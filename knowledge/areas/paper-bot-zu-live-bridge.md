# Standardprozess: Paper-Bot → Live-Bridge

**Status:** aktiv seit 2026-09-10 · **Typ:** Area (Dauerverantwortung)
**Anlass:** [[dashboard]] · siehe CHANGELOG 2026-09-09/10

---

## Warum es diesen Prozess gibt

Am 2026-09-09 kam heraus, dass `EK-Portfolio-Bridge` (Tickmill, **echtes Geld**) die
Kapitalverdünnungsformel zwar im `config.py`-Docstring festschrieb, sie aber
**nirgends im Code anwendete**. Jedes Bein handelte ~8x größer als validiert.

Der Backtest-Beleg: mit Verdünnung −16,1 % Max-Drawdown, ohne −73,7 %. Gebremst
wurde das nur zufällig durch einen aggregierten Risikodeckel, der eigentlich als
Reserve gedacht war — mit der Nebenwirkung, dass die Beine sich gegenseitig
aushungerten (ein realer verpasster CLS-Entry am 2026-09-09 10:30).

Im selben Zug fiel auf: die Bridge hatte **überhaupt keinen Portfolio-Kill-Switch**,
obwohl `ek_portfolio/paper_bot.py::check_trailing_dd()` seit jeher einen hat.

Beides sind keine Tippfehler, sondern **Auslassungen beim Übertragen** vom
Paper-Bot in die Live-Bridge. Genau die soll dieser Prozess künftig unmöglich machen.

## Die Regel

> Eine Live-Bridge ist **keine Neuimplementierung** der Strategie, sondern eine
> Übertragung des Paper-Bots auf echte Order-Ausführung. Alles, was die
> Positionsgröße oder das Risiko bestimmt, wird **übernommen und gegengeprüft** —
> nicht neu erfunden und nicht selektiv weggelassen.

Weglassen ist erlaubt, aber nur **explizit und begründet**: als Kommentar an der
Stelle, wo der Wert stünde, plus Eintrag in `DASHBOARD.md` unter „🔍 Braucht deine
Bestätigung". Stillschweigend weglassen ist der Fehler, den es zu verhindern gilt.

## Checkliste (vor jedem DRY_RUN=False)

Für jeden Punkt gilt: **Zeile im Paper-Bot zeigen, Zeile in der Bridge zeigen.**
„Ist sinngemäß drin" reicht nicht — genau das war der Fehlermodus.

| # | Was | Referenz im Paper-Bot |
|---|---|---|
| 1 | **Risiko-Formel vollständig**, inkl. aller Faktoren (Kapitalverdünnung!) | `CAPITAL_WEIGHT * LEG_RISK_PCT * equity` |
| 2 | **Risikostufen je Bein** stimmen zahlenweise mit der validierten Studie überein | `portfolio_construction/results/*.json` |
| 3 | **Aggregierter Risikodeckel** vorhanden und begründet | — |
| 4 | **Kill-Switch / Drawdown-Grenze** portiert | `check_trailing_dd()` |
| 5 | **Kill-Switch-Grenze passt zum Risikoziel** (siehe Fallstrick unten) | — |
| 6 | **Exit-/Management-Logik** vollständig (Teilausstiege, BE-Shift, Max-Holding) | je Strategie |
| 7 | **Mindestlot-Verhalten** bewusst entschieden: überspringen oder anheben | `FKInstantFunding-MT5-Bridge/sizing.py` |
| 8 | **Sizing über `order_calc_profit()`**, nie manuell aus tick_value | jede Bridge-`sizing.py` |

## Die Probe

`knowledge/scripts/bridge_risk_audit.py` vergleicht automatisiert alle Live-Bridges
gegen diese Checkliste — welche Risikokonstanten sie definieren, ob sie definierte
Konstanten auch tatsächlich **benutzen** (der EK-Fehlermodus), und ob ein
Kill-Switch existiert.

```
python knowledge/scripts/bridge_risk_audit.py
```

Findet insbesondere den Fall „Konstante definiert, aber nie gelesen" — genau die
Signatur des EK-Bugs. Läuft rein lesend, keine MT5-Verbindung.

## Fallstricke (real passiert, nicht theoretisch)

**Kill-Switch-Grenze muss zum Risikoziel passen.** Ein 20-%-Kill-Switch auf einem
Portfolio mit −26 % Monte-Carlo-Median-Drawdown löst im *Normalbetrieb* aus und legt
den Bot still. Beim Ändern des Risikoziels immer beide Zahlen zusammen anfassen
(EK 2026-09-10: Ziel −40 % → Kill-Switch 45 %).

**Ein Fix pro Bein ist kein Fix.** Der Order-Kommentar-Bug vom 2026-09-04 wurde nur
in `legs/ny_open_orb/executor.py` behoben und schlug am 2026-09-09 in
`legs/ctnl_edge/` erneut zu — eine Live-Position hing 4 Stunden fest. Härtungen
gehören in den **gemeinsamen Engpass** (`core/order_send.py`), nicht ins Bein.
Siehe [[mt5-bot-deployment]].

**Der aggregierte Deckel ist keine Risikoformel.** Wenn er dauernd greift, ist das
kein funktionierendes Risikomanagement, sondern ein Symptom falscher Sizing-Formel.
Symptom: Beine bekommen Risiko nach Scan-Reihenfolge statt nach Design.

**Backtest-Zahlen nie aus der Beschriftung ablesen.** Ob „8 % Risiko/Trade" das
Risiko *innerhalb einer Kapitalscheibe* oder *auf das Gesamtkonto* meint, entscheidet
über Faktor 8. Immer gegen ein publiziertes Szenario rückrechnen, bevor eine Zahl in
eine Live-Config wandert — siehe Memory `backtest_zahlen_gegen_szenario_pruefen.md`.

## Verwandt

[[mt5-bot-deployment]] · [[edge-card-workflow]] · [[paper-bot-architecture]] · [[dashboard]]
