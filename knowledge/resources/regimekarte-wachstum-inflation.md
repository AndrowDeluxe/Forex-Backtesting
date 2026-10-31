# Regimekarte Wachstum × Inflation (First Prints)

Quelle: Alexandre Landi, „Reading the growth–inflation map“, educational brief,
Stand 20.09.2026 (PDF vom Nutzer, 20.10.2026). Nachgebaut am 20.10.2026 als
Baustein für den Makro-Agenten (Strang 3 in [[quant-diskretionaer-fusion]]).
Verknüpfung mit Strategien/Trades folgt später (Nutzer).

Code: `fusion_lab/macro_regime/` · Lauf: `python -m fusion_lab.macro_regime [--refresh]`
· Ausgabe: `fusion_lab/data/macro_regime/` (`current.json` für den Agenten,
`regime_map.md` lesbar, `calibration.md` Abgleich mit dem PDF).

## Idee

Jeder Handelstag bekommt ein Regime aus US-Wachstum (reales BIP, YoY) und
US-Inflation (Headline-CPI, YoY), und zwar **so, wie es am Release-Morgen
veröffentlicht wurde** (ALFRED-Vintages, keine heutigen revidierten Werte).
Zwei Fragen je Größe:

1. Ist die YoY-Rate positiv oder negativ?
2. Ist sie höher oder niedriger als die der Vorperiode? (accel/slow)

Drei Linsen: nur Vorzeichen (zu einseitig, ~93 % „beide positiv“), nur
Tempo (vier etwa gleich große Zustände), gemeinsam (vier große + neun dünne
Zustände). Ein Print gilt ab der folgenden Sitzung. Je Regime: Rendite,
Vola und Sharpe von SPX, UST, Gold, Kupfer, Öl, Weizen, DXY gegen Cash.

Abgrenzung: Das Bridgewater-All-Weather-Viereck datiert Regime über
Überraschungen gegen Erwartungen; hier zählt der realisierte Wert. Damit
ergänzt die Karte die Quad-Schemata im [[makro-faktoren-katalog]], ohne
Konsensdaten zu brauchen (dort der Engpass).

## Nachbau und Abweichungen

| Baustein | Original | Nachbau |
|---|---|---|
| Wachstum / Inflation | ALFRED First Prints | gleich (FRED-API, GDPC1 / CPIAUCNS, alle Vintages) |
| „Vorprint“ beim BIP | nicht genau definiert | YoY jüngstes Quartal vs. Vorquartal aus **derselben Vintage**; die Alternative (Revisionsrichtung) passte deutlich schlechter zu den PDF-Tageszahlen |
| SPX, DXY | Bloomberg | yfinance `^SP500TR`, `DX-Y.NYB` |
| UST | Bloomberg US Treasury TR | synthetische 5y-Par-Anleihe aus FRED DGS5 |
| Gold, Kupfer, Öl, Weizen | Gold Spot, S&P GSCI Excess Return | yfinance-Front-Monat, **erst ab Aug. 2000, ohne Rollrendite** |
| Cash | 3M T-Bill | FRED DTB3 |

Die Annahmen in dieser Tabelle hat der Nutzer am 20.10.2026 bestätigt.

## Kalibrierung (Stichtag 18.09.2026)

- Regime am Stichtag identisch: **g↑·slow × π↑·accel**.
- Tage im aktuellen Regime 1.690 (20,6 %) vs. PDF 1.721 (20,5 %); die vier
  großen Zustände weichen um höchstens 1,5 Prozentpunkte ab.
- Asset-Werte im aktuellen Regime: gleiche Vorzeichen und gleiche
  Rangfolge (UST führt beim Sharpe, Rohstoffe negativ). Rohstoffe liegen
  höher als im PDF, weil die Rollrendite fehlt (Weizen −8 % statt −36 %).
  Gold liegt höher, weil 1994–2000 fehlt.
- CPI-YoY im PDF (Juli 3,3 %, Aug. 3,4 %) liegt unter CPIAUCNS (3,52 / 3,69).
  Die Richtung ist gleich, daher stimmt das Label. Ursache ungeklärt.

## Stand 20.10.2026

Unverändert **g↑·slow × π↑·accel** (seit 14.09.): BIP Q2 2,19 % nach 2,64 %
(3. Schätzung 30.09.), CPI Sept. 4,0 % nach 3,7 %. Im Nachbau führen in
diesem Regime UST (Sharpe 0,76) und Gold/SPX (~0,45), Rohstoffe und DXY sind
negativ. Nächste Prints: GDP advance 29.10., CPI 10.11.

## Vier-Fragen-Check

1. **Warum verdient es Geld?** Die Karte selbst ist kein Edge. Sie
   beschreibt, welche Risikoprämie (Duration, Aktienbeta, Rohstoffe) in
   welchem Wachstums-Inflations-Zustand historisch bezahlt wurde.
2. **Wo verliert es am meisten?** In den dünnen Regimen (unter ~150 Tage),
   deren Mittelwerte reines Rauschen sind, und direkt nach Wendepunkten, weil
   das BIP-Label bis zu drei Monate hinterherläuft.
3. **Was ist dort anders?** Offen; erst nach der Verknüpfung mit
   Strategien/Trades messbar, und nur auf IS-Daten. Verknüpfung mit den
   Live-Beinen am 28.10. gemacht: kein Bein regimeabhängig, siehe [[edges-je-regime]].
4. **Welche eine Regel könnte helfen?** Offen. Jede Regel aus der Karte
   (z. B. „Bein X nur in Regime Y“) ist eine gezählte Variante unter der
   [[overfitting-sperre]].

## Stand 30.10.2026

Nach dem GDP-Advance-Print vom 29.10. bleibt das Regime unverändert:
**g↑·slow × π↑·accel** (seit 14.09.). BIP Q3 liegt bei 2,07 % nach 2,19 %. Nächste
Prints: CPI 10.11., GDP 25.11.

## Für den Makro-Agenten

**Zwei Ebenen (Nutzerentscheid 20.10.):**
- Die **Karte ist die Bestätigung.** Sie wechselt nur an GDP- und
  CPI-Terminen.
- Die **Marktsicht ist die Frühwarnung.** Staatsanleihen-Renditen
  (2y/10y), Breakevens und GDPNow bewegen sich laufend und können einen
  Wechsel zwischen den Prints anzeigen, bevor der nächste Print ihn bestätigt.
  Der Bau folgt zusammen mit dem Agenten.

Notion: Eintrag „Regime-Roadmap — Wachstum × Inflation“ in der DB
🌍 Makro-Übersicht, aktualisieren mit `python -m fusion_lab.notion.sync_regime`
(nach `python -m fusion_lab.macro_regime`).

- `current.json` liefert Zustand, Prints, „seit“-Datum, nächste Termine und
  die Kennzahlen des aktuellen Regimes. Das ist der Regime-Kontext (Rolle **R**
  im Katalog).
- Die Karte ist eine Karte der Vergangenheit, keine Prognose. Nur die vier
  großen Zustände der gemeinsamen Sicht sind belastbar.
- Nach jedem GDP-/CPI-Print neu laufen lassen (`--refresh`).
- **Später, beim Bau des Agenten** (Nutzerentscheid 20.10.):
  - Automatikbetrieb mit täglichem Lauf, Wechsel-Log, Telegram bei Wechsel,
    Soll/Ist-Abgleich und Wochenblock.
  - Dazu ein Markt-Layer zwischen den Prints: Staatsanleihen-Renditen,
    Breakevens und GDPNow bewegen sich laufend und können einen Wechsel
    ankündigen, bevor der nächste Print ihn bestätigt. Details in der
    Ideen-Inbox in `DASHBOARD.md`.
