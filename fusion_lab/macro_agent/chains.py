"""Wirkketten-Katalog (Meridian "Mechanismus-Register", Phase-2-Schritt 3, 12.11.2026).

Eine Kette = Ausloeser -> Schritte -> betroffene Assets, jeder Schritt mit messbarer Bedingung, dazu eine
Stopp-Bedingung und der Beleg-Status. Quelle der ersten vier Ketten: SMT-Report 21.10.
(knowledge/resources/makro-wirkketten-und-regeln.md §2); die anderen aus dem Geo-Framework und der Literatur.

Status je Lauf:
- "aktiv":     alle Schritte erfuellt, Stopp nicht erfuellt
- "umgekehrt": alle Umkehr-Schritte erfuellt: die Kette laeuft rueckwaerts (z. B. Brent faellt, 2J faellt ->
               Gold-Rueckenwind); Wirkung mit umgedrehtem Vorzeichen (seit 24.11.2026, Nutzerentscheid)
- "anlaufend": erster Schritt erfuellt, spaetere noch nicht
- "gestoppt":  Stopp-Bedingung erfuellt, ohne dass die Kette rueckwaerts laeuft
- "ruhend":    sonst
Beleg: "belegt" heisst, der letzte Schritt (Treiber -> Asset) ist in der Exposure-Matrix stabil
(gleiches Vorzeichen 2007-16, 2017-26, heute); die frueheren Schritte sind Annahmen, solange nicht anders
vermerkt. Aktive und umgekehrte Ketten gehen als Aussage ins Forecast-Ledger (Asset-Richtung, 20 Handelstage).
Ketten seit 24.11. aus der OneNote-"Makro Education" (knowledge/resources/makro-faktoren-katalog.md, Regeln
1-25 und Testkandidaten); Rangliste "welche Kette traegt" in scripts/research_wirkketten_ranking.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

M = dict  # Messwerte: Name -> Zahl (None = fehlt)


@dataclass
class Step:
    text: str
    check: Callable[[M], bool | None]
    zeigt: str  # Messwert(e) fuer die Anzeige


@dataclass
class Chain:
    id: str
    name: str
    quelle: str
    schritte: list[Step]
    stopp: Step
    assets: dict[str, int]                      # Asset -> erwartete Richtung, wenn die Kette laeuft
    beleg: list[tuple[str, str]] = field(default_factory=list)  # (Asset, Treiber) in der Exposure-Matrix
    hinweis: str = ""
    umkehr: list[Step] | None = None            # Rueckwaerts-Lauf: alle erfuellt -> Wirkung umgedreht


def _gt(name, x):
    return lambda m: None if m.get(name) is None else m[name] > x


def _lt(name, x):
    return lambda m: None if m.get(name) is None else m[name] < x


def _all(*fs):
    def f(m):
        vals = [g(m) for g in fs]
        return None if any(v is None for v in vals) else all(vals)
    return f


def _any(*fs):
    def f(m):
        vals = [g(m) for g in fs]
        return True if any(v is True for v in vals) else (None if any(v is None for v in vals) else False)
    return f


def _eq(name, x):
    return lambda m: None if m.get(name) is None else m[name] == x


CHAINS = [
    Chain("oel_fed_gold", "Ölschock → Fed-Erwartung → Realzins/Dollar → Gold schwach", "Geo-Framework 12.11.",
          [Step("Brent steigt (20 T > +5 %)", _gt("brent_20d", 5), "brent_20d"),
           Step("Öl greift auf die Fed-Erwartung durch (2J je Brent +10 % über früherem Niveau)",
                _eq("fed_kanal", True), "fed_kanal"),
           Step("US-2J steigt (20 T > +10 bp)", _gt("us_2y_20d_bp", 10), "us_2y_20d_bp")],
          Step("Brent fällt (20 T < −5 %) oder Fed-Kanal aus", _any(_lt("brent_20d", -5), _eq("fed_kanal", False)),
               "brent_20d"),
          {"gold": -1, "USDJPY": +1, "EURUSD": -1}, [("gold", "us_2y"), ("USDJPY", "us_2y"), ("EURUSD", "us_2y")],
          "Historisch hob Öl Gold (Inflationsschutz); nur bei Fed-Durchgriff negativ."),
    Chain("oel_cad", "Öl + Inflation → BoC-Erwartung → CAD stärker", "SMT 21.10.",
          [Step("Brent steigt (20 T > +3 %)", _gt("brent_20d", 3), "brent_20d"),
           Step("CA-Pricing steigt (1J − Leitzins, Woche > 0)", _gt("ca_pricing_1w_bp", 0), "ca_pricing_1w_bp")],
          Step("Brent fällt (20 T < −5 %)", _lt("brent_20d", -5), "brent_20d"),
          {"USDCAD": -1, "CADJPY": +1}, [("USDCAD", "brent")]),
    Chain("oel_importeure", "Öl hoch → Importeure (JPY, EUR) schwächer", "Lehrbuch (Terms of Trade)",
          [Step("Brent steigt (20 T > +5 %)", _gt("brent_20d", 5), "brent_20d")],
          Step("Brent fällt (20 T < −5 %)", _lt("brent_20d", -5), "brent_20d"),
          {"EURUSD": -1, "USDJPY": +1}, [("EURUSD", "brent"), ("USDJPY", "brent")],
          "Eigener Test: EURUSD/USDJPY reagieren auf Brent nicht stabil – eher Hypothese."),
    Chain("defizit_oat", "Defizit Frankreich → OAT-Bund-Spread → EUR nur gegen CHF/GBP schwach", "SMT 21.10.",
          [Step("OAT-Bund über 80 bp", _gt("oat_bund_bp", 80), "oat_bund_bp"),
           Step("Spread steigt (20 T > +10 bp)", _gt("oat_bund_20d_bp", 10), "oat_bund_20d_bp")],
          Step("Spread fällt (20 T < −10 bp)", _lt("oat_bund_20d_bp", -10), "oat_bund_20d_bp"),
          {"EURCHF": -1, "EURGBP": -1}, [], "Kein Treiber in der Exposure-Matrix: Hypothese."),
    Chain("ki_schulden_hy", "KI-Schulden → Kreditaufschlag → Aktien (verzögert, nur bei ruhigem VIX)",
          "SMT 21.10., Test 15.11.",
          [Step("Kredit verschlechtert sich (HYG/IEF 20 T < −2 % oder HY-Spread 20 T > +25 bp)",
                _any(_lt("hyg_ief_20d", -2), _gt("hy_20d_bp", 25)), "hyg_ief_20d"),
           Step("VIX noch ruhig (< 20)", _lt("vix", 20), "vix")],
          Step("Kredit erholt (HYG/IEF 20 T > 0)", _gt("hyg_ief_20d", 0), "hyg_ief_20d"),
          {"ndx": -1, "spx": -1}, [("ndx", "vix"), ("spx", "vix")],
          "Test 15.11.: Bedingungslos laufen Aktien vor dem Spread (Nasdaq → BAA10Y, t −3), nicht umgekehrt. "
          "Nur bei VIX < 20 schwacher Vorlauf (HYG/IEF, NDX 20 T −0,6 % statt +1,0/+1,4 %, t −1,4/−1,2). "
          "FRED-HY reicht nur bis 11/2023 zurück, daher HYG/IEF."),
    Chain("oel_praemie", "Öl-Prämie: Angriff statt Menge", "SMT 21.10.",
          [Step("Iran/Hormuz laut Schlagzeilen eskalierend", _eq("lage_iran_hormuz", "eskalation"), "lage_iran_hormuz"),
           Step("Brent über dem 20-Tage-Mittel", _gt("brent_vs_20d", 0), "brent_vs_20d")],
          Step("Entspannung gemeldet", _eq("lage_iran_hormuz", "entspannung"), "lage_iran_hormuz"),
          {"brent": +1}, [],
          "Eine Angriffsprämie verschwindet bei Waffenruhe schneller als eine echte Mengenkrise (Tanker ~70 %)."),
    Chain("zoelle_inflation", "Zölle → Importpreise → Inflationserwartung → Rohstoffwährungen", "Geo-Framework 12.11.",
          [Step("Zölle laut Schlagzeilen eskalierend", _eq("lage_zoelle_trump", "eskalation"), "lage_zoelle_trump"),
           Step("Inflationserwartung 10J steigt (20 T > +10 bp)", _gt("breakeven_20d_bp", 10), "breakeven_20d_bp")],
          Step("Zölle laut Schlagzeilen entspannt", _eq("lage_zoelle_trump", "entspannung"), "lage_zoelle_trump"),
          {"AUDUSD": +1, "USDCAD": -1}, [("AUDUSD", "breakeven"), ("USDCAD", "breakeven")]),
    Chain("ukraine_gas", "Ukraine/Energie → Europa-Gas → EUR, DAX schwächer", "SMT/Lehrbuch",
          [Step("Ukraine/Russland laut Schlagzeilen eskalierend", _eq("lage_ukraine_russland", "eskalation"),
                "lage_ukraine_russland")],
          Step("Entspannung gemeldet", _eq("lage_ukraine_russland", "entspannung"), "lage_ukraine_russland"),
          {"EURUSD": -1, "dax": -1}, [], "Ohne TTF-Historie nicht messbar: Hypothese."),
    Chain("risiko_aus_hafen", "Stress → Flucht in Häfen (USD, JPY, CHF) gegen Rohstoffwährungen", "Leitlinie 08.11.",
          [Step("VIX über 24", _gt("vix", 24), "vix"),
           Step("S&P 500 fällt (5 T < −3 %)", _lt("spx_5d", -3), "spx_5d")],
          Step("VIX unter 18", _lt("vix", 18), "vix"),
          {"AUDUSD": -1, "USDCAD": +1, "spx": -1}, [("AUDUSD", "vix"), ("USDCAD", "vix"), ("spx", "vix")],
          "Test 22.11. (Lock vix_zins_wirkkette): VIX > 30 ist kein Kaufsignal. S&P danach nur 2018–26 im Plus "
          "(+5 % in 20 T), 2005–17 im Minus (2008 −5 %): Regime-Frage (hilft die Fed schnell?). Gold reagiert nicht "
          "auf den VIX (Korrelation ≈ 0, Vorzeichen wechselt je Jahr)."),
    Chain("risiko_an_ki", "KI-Gewinne → Asiens Chipbörsen (KOSPI) → Risikoappetit → AUD stärker",
          "Geo-Framework 12.11., Test 15.11.",
          [Step("KOSPI steigt (20 T > +5 %)", _gt("kospi_20d", 5), "kospi_20d"),
           Step("VIX fällt (20 T < 0)", _lt("vix_20d", 0), "vix_20d")],
          Step("KOSPI fällt (20 T < −5 %)", _lt("kospi_20d", -5), "kospi_20d"),
          {"AUDUSD": +1, "kupfer": +1}, [("AUDUSD", "vix"), ("kupfer", "vix")],
          "Seit 15.11. KOSPI statt Nasdaq: AUD~Nasdaq 2025/26 nur +0,21, AUD~KOSPI +0,54 (Wochen, Gleichlauf)."),
    Chain("us_zins_dollar", "US-Zinsen steigen relativ → Dollar stärker (vor allem gegen JPY)", "Fed-Note 2017",
          [Step("US-2J steigt (20 T > +15 bp)", _gt("us_2y_20d_bp", 15), "us_2y_20d_bp")],
          Step("US-2J fällt (20 T < −15 bp)", _lt("us_2y_20d_bp", -15), "us_2y_20d_bp"),
          {"USDJPY": +1, "EURUSD": -1, "gold": -1}, [("USDJPY", "us_2y"), ("EURUSD", "us_2y"), ("gold", "us_2y")],
          "Test 22.11.: Gold folgt 2J und Dollar nur im Gleichlauf (Woche: Gold~2J −0,2, Gold~DXY −0,47), kein "
          "Vorlauf. „VIX und Zinsen fallen“ hebt Gold nur über die Zinsen; der Gewinn liegt in der Prognose des "
          "2J-Pfads, nicht im Nachlaufen."),
    Chain("china_kupfer", "China-Nachfrage → Kupfer → AUD stärker", "Lehrbuch",
          [Step("Kupfer steigt (20 T > +5 %)", _gt("kupfer_20d", 5), "kupfer_20d")],
          Step("Kupfer fällt (20 T < −5 %)", _lt("kupfer_20d", -5), "kupfer_20d"),
          {"AUDUSD": +1}, [], "Kupfer ist in der Exposure-Matrix kein Treiber: Hypothese."),
    # Danske „AI Investment Tracker" (19.10.2026), getestet 15.11. (scripts/research_ai_wirkketten.py):
    # kein Vorlauf im Backtest. Gespeichert auf Nutzerwunsch, damit das Ledger sie vorwärts prüft.
    Chain("ki_chips_korea", "KI-Chipboom → Korea-Exporte → AUD/Nasdaq stärker", "Danske 19.10., Test 15.11.",
          [Step("Korea-Exporte J/J beschleunigen (3 M > +5 Pp.)", _gt("korea_exporte_yoy_3m", 5),
                "korea_exporte_yoy_3m"),
           Step("KOSPI steigt (20 T > 0)", _gt("kospi_20d", 0), "kospi_20d")],
          Step("Korea-Exporte J/J bremsen (3 M < −5 Pp.)", _lt("korea_exporte_yoy_3m", -5), "korea_exporte_yoy_3m"),
          {"AUDUSD": +1, "ndx": +1}, [],
          "Backtest 15.11.: kein Zusammenhang, auch gleichzeitig nicht (|t| < 1). Nur Vorwärts-Prüfung."),
    Chain("china_preise_inflation", "Speicherchips → China-Exportpreise → US-Güterinflation → US-2J → Gold schwach",
          "Danske 19.10., Test 15.11.",
          [Step("US-Importpreise aus China J/J positiv", _gt("china_importpreise_yoy", 0), "china_importpreise_yoy"),
           Step("… und steigend (3 M > +1 Pp.)", _gt("china_importpreise_yoy_3m", 1), "china_importpreise_yoy_3m"),
           Step("US-2J steigt (20 T > +10 bp)", _gt("us_2y_20d_bp", 10), "us_2y_20d_bp")],
          Step("Importpreise drehen (3 M < −1 Pp.)", _lt("china_importpreise_yoy_3m", -1), "china_importpreise_yoy_3m"),
          {"gold": -1, "USDJPY": +1}, [("gold", "us_2y"), ("USDJPY", "us_2y")],
          "Backtest 15.11.: Kern-Güter-CPI folgt nur OOS (t 2,8, ohne 2021/22 t 1,65); kein Vorlauf für 2J/Gold. "
          "Der letzte Schritt (2J → Gold) ist belegt."),
    Chain("kupfer_aud_ki", "KI-Ausbau → Kupfer → AUD stärker", "Danske 19.10., Test 15.11.",
          [Step("Kupfer steigt (20 T > +5 %)", _gt("kupfer_20d", 5), "kupfer_20d"),
           Step("KOSPI steigt (20 T > 0)", _gt("kospi_20d", 0), "kospi_20d")],
          Step("Kupfer fällt (20 T < −5 %)", _lt("kupfer_20d", -5), "kupfer_20d"),
          {"AUDUSD": +1}, [],
          "Backtest 15.11.: Kupfer ohne Vorlauf für AUD (OOS t −1,6), Gleichlauf 2025/26 nur +0,34."),
    Chain("fed_druck", "Druck auf die Fed → Glaubwürdigkeit → Dollar schwach, Gold stark", "Literatur",
          [Step("Fed-Druck laut Schlagzeilen eskalierend", _eq("lage_fed_unabhaengigkeit", "eskalation"),
                "lage_fed_unabhaengigkeit"),
           Step("5J-in-5J-Inflationserwartung steigt (Woche > +5 bp)", _gt("fwd_5y5y_1w_bp", 5), "fwd_5y5y_1w_bp")],
          Step("Entspannung gemeldet", _eq("lage_fed_unabhaengigkeit", "entspannung"), "lage_fed_unabhaengigkeit"),
          {"gold": +1, "EURUSD": +1}, [("gold", "dollar")]),
    # OneNote-"Makro Education" (24.11.2026, Nutzerauftrag "fehlende Wirkketten"); Schwellen von Claude gesetzt,
    # vor dem Ranking-Test festgelegt (Lock wirkketten_ranking_v1), nicht optimiert.
    Chain("liquiditaet_risiko", "Liquidität (Fed-Bilanz − TGA − Reverse Repo) steigt → Aktien und Gold getragen",
          "Education Regel 19, Testkandidat 4",
          [Step("Net Liquidity steigt (13 W > +150 Mrd.)", _gt("net_liq_13w", 150), "net_liq_13w")],
          Step("Net Liquidity fällt (13 W < −150 Mrd.)", _lt("net_liq_13w", -150), "net_liq_13w"),
          {"spx": +1, "ndx": +1, "gold": +1}, [],
          umkehr=[Step("Net Liquidity fällt (13 W < −150 Mrd.)", _lt("net_liq_13w", -150), "net_liq_13w")]),
    Chain("realzins_risiko", "Realzins steigt und ist positiv → Risiko-Assets und Gold fallen",
          "Education Regel 18, Testkandidat 10",
          [Step("US-Realzins 10J positiv", _gt("real_10y", 0), "real_10y"),
           Step("Realzins steigt (20 T > +20 bp)", _gt("real_10y_20d_bp", 20), "real_10y_20d_bp")],
          Step("Realzins fällt (20 T < −20 bp)", _lt("real_10y_20d_bp", -20), "real_10y_20d_bp"),
          {"ndx": -1, "gold": -1}, [("gold", "realzins"), ("ndx", "realzins")],
          umkehr=[Step("Realzins fällt (20 T < −20 bp)", _lt("real_10y_20d_bp", -20), "real_10y_20d_bp")]),
    Chain("kurve_dollar", "Bull-Steepener (2J fällt, Kurve steiler) → Fed-Senkungen eingepreist → Dollar schwach",
          "Education Regel 15 (Hausaufgabe 2)",
          [Step("US-2J fällt (20 T < −10 bp)", _lt("us_2y_20d_bp", -10), "us_2y_20d_bp"),
           Step("Kurve 10J−2J steiler (20 T > +5 bp)", _gt("us_kurve_20d_bp", 5), "us_kurve_20d_bp")],
          Step("US-2J steigt (20 T > +10 bp)", _gt("us_2y_20d_bp", 10), "us_2y_20d_bp"),
          {"EURUSD": +1, "AUDUSD": +1, "USDJPY": -1, "USDCHF": -1}, [("EURUSD", "us_2y"), ("USDJPY", "us_2y")],
          umkehr=[Step("US-2J steigt (20 T > +10 bp)", _gt("us_2y_20d_bp", 10), "us_2y_20d_bp"),
                  Step("Kurve flacher (20 T < −5 bp)", _lt("us_kurve_20d_bp", -5), "us_kurve_20d_bp")]),
    Chain("funding_stress", "Liquiditätsengpass (SOFR über IORB, MOVE hoch) → Risikoprämien steigen → JPY als Hafen",
          "Education Regel 21 (Bonds Liq 1)",
          [Step("Funding angespannt (SOFR − IORB > 5 bp) oder MOVE > 120",
                _any(_gt("sofr_iorb_bp", 5), _gt("move", 120)), "sofr_iorb_bp"),
           Step("VIX über 20", _gt("vix", 20), "vix")],
          Step("SOFR − IORB < 2 bp und MOVE < 100", _all(_lt("sofr_iorb_bp", 2), _lt("move", 100)), "move"),
          {"USDJPY": -1, "AUDJPY": -1, "spx": -1}, [("USDJPY", "vix"), ("spx", "vix")]),
    Chain("arbeitsmarkt_abschwung",
          "Nachfrage ↓ → Entlassungen (Erstanträge) ↑ → Fed lockert → 2J, Dollar, Aktien runter, Gold rauf",
          "Education Regeln 5, 8, 23; Testkandidat 5 (Sahm)",
          [Step("Erstanträge 4W > 15 % über 52W-Tief", _gt("erstantraege_vs_tief_pct", 15), "erstantraege_vs_tief_pct"),
           Step("Sahm-Regel ≥ 0,3 (Warnzone)", _gt("sahm", 0.29), "sahm")],
          Step("Erstanträge zurück (< 5 % über Tief)", _lt("erstantraege_vs_tief_pct", 5), "erstantraege_vs_tief_pct"),
          {"USDJPY": -1, "spx": -1, "gold": +1}, [("USDJPY", "us_2y"), ("gold", "us_2y")]),
    Chain("daten_ueberraschung_usd", "US-Daten über Konsens (ohne Wachstumsschwäche) → weniger Senkungen → Dollar stark",
          "Education Regeln 1, 5, 6",
          [Step("US-Überraschungen 60 T > +2", _gt("usd_ueberraschung", 2), "usd_ueberraschung"),
           Step("GDPNow > 1 % (keine Schwäche)", _gt("gdpnow", 1), "gdpnow")],
          Step("US-Überraschungen 60 T < 0", _lt("usd_ueberraschung", 0), "usd_ueberraschung"),
          {"EURUSD": -1, "USDJPY": +1, "gold": -1}, [("EURUSD", "us_2y"), ("USDJPY", "us_2y")],
          umkehr=[Step("US-Überraschungen 60 T < −2", _lt("usd_ueberraschung", -2), "usd_ueberraschung")]),
    Chain("ust_jgb_usdjpy", "Zinsabstand USA − Japan (10J) wächst → USDJPY steigt", "Education Testkandidat 7 (Bankreport)",
          [Step("UST−JGB 10J steigt (20 T > +15 bp)", _gt("ust_jgb_20d_bp", 15), "ust_jgb_20d_bp")],
          Step("UST−JGB 10J fällt (20 T < −15 bp)", _lt("ust_jgb_20d_bp", -15), "ust_jgb_20d_bp"),
          {"USDJPY": +1}, [("USDJPY", "us_2y")],
          "Bank: ~90 % Korrelation im Niveau; Niveau-Korrelation täglich kann Scheinkorrelation sein (Katalog).",
          umkehr=[Step("UST−JGB 10J fällt (20 T < −15 bp)", _lt("ust_jgb_20d_bp", -15), "ust_jgb_20d_bp")]),
    Chain("laufzeitpraemie_gold", "Laufzeitprämie steigt (Haushalt/Fed-Zweifel) → Dollar schwach, Gold stark",
          "Desk-Abgleich 24.11. (Graham/BIS 2026), Hypothese",
          [Step("ACM-Prämie 10J steigt (20 T > +15 bp)", _gt("praemie_20d_bp", 15), "praemie_20d_bp"),
           Step("… stärker als die Zinserwartung", _gt("praemie_minus_erwartung_bp", 0), "praemie_minus_erwartung_bp")],
          Step("Prämie fällt (20 T < −15 bp)", _lt("praemie_20d_bp", -15), "praemie_20d_bp"),
          {"gold": +1, "EURUSD": +1}, [],
          umkehr=[Step("Prämie fällt (20 T < −15 bp)", _lt("praemie_20d_bp", -15), "praemie_20d_bp")]),
    Chain("carry_risiko", "USDJPY und Aktien steigen → Risikoappetit (Carry) → AUD, Kupfer stärker",
          "Education Regel 20 (BTC-Dynamik)",
          [Step("USDJPY steigt (20 T > +2 %)", _gt("usdjpy_20d", 2), "usdjpy_20d"),
           Step("S&P 500 steigt (20 T > +3 %)", _gt("spx_20d", 3), "spx_20d")],
          Step("USDJPY fällt (20 T < −2 %)", _lt("usdjpy_20d", -2), "usdjpy_20d"),
          {"AUDUSD": +1, "kupfer": +1}, [("AUDUSD", "vix")],
          umkehr=[Step("USDJPY fällt (20 T < −2 %)", _lt("usdjpy_20d", -2), "usdjpy_20d"),
                  Step("S&P 500 fällt (20 T < −3 %)", _lt("spx_20d", -3), "spx_20d")]),
]

# Rueckwaerts-Lauf der bestehenden Ketten (24.11.2026): meist der gespiegelte Ausloeser. Keine Umkehr fuer
# Ketten, deren Gegenteil der Normalzustand ist (KI-Schulden, Fed-Druck).
UMKEHR = {
    "oel_fed_gold": [Step("Brent fällt (20 T < −5 %)", _lt("brent_20d", -5), "brent_20d"),
                     Step("US-2J fällt (20 T < −10 bp)", _lt("us_2y_20d_bp", -10), "us_2y_20d_bp")],
    "oel_cad": [Step("Brent fällt (20 T < −3 %)", _lt("brent_20d", -3), "brent_20d"),
                Step("CA-Pricing fällt (Woche < 0)", _lt("ca_pricing_1w_bp", 0), "ca_pricing_1w_bp")],
    "oel_importeure": [Step("Brent fällt (20 T < −5 %)", _lt("brent_20d", -5), "brent_20d")],
    "defizit_oat": [Step("Spread fällt (20 T < −10 bp)", _lt("oat_bund_20d_bp", -10), "oat_bund_20d_bp")],
    "oel_praemie": [Step("Iran/Hormuz laut Schlagzeilen entspannt", _eq("lage_iran_hormuz", "entspannung"),
                         "lage_iran_hormuz"),
                    Step("Brent unter dem 20-Tage-Mittel", _lt("brent_vs_20d", 0), "brent_vs_20d")],
    "zoelle_inflation": [Step("Zölle laut Schlagzeilen entspannt", _eq("lage_zoelle_trump", "entspannung"),
                              "lage_zoelle_trump"),
                         Step("Inflationserwartung fällt (20 T < −10 bp)", _lt("breakeven_20d_bp", -10),
                              "breakeven_20d_bp")],
    "ukraine_gas": [Step("Ukraine/Russland laut Schlagzeilen entspannt", _eq("lage_ukraine_russland", "entspannung"),
                         "lage_ukraine_russland")],
    "risiko_aus_hafen": [Step("VIX fällt (20 T < −5 Punkte)", _lt("vix_20d", -5), "vix_20d"),
                         Step("S&P 500 steigt (5 T > +2 %)", _gt("spx_5d", 2), "spx_5d")],
    "risiko_an_ki": [Step("KOSPI fällt (20 T < −5 %)", _lt("kospi_20d", -5), "kospi_20d"),
                     Step("VIX steigt (20 T > 0)", _gt("vix_20d", 0), "vix_20d")],
    "us_zins_dollar": [Step("US-2J fällt (20 T < −15 bp)", _lt("us_2y_20d_bp", -15), "us_2y_20d_bp")],
    "china_kupfer": [Step("Kupfer fällt (20 T < −5 %)", _lt("kupfer_20d", -5), "kupfer_20d")],
    "ki_chips_korea": [Step("Korea-Exporte J/J bremsen (3 M < −5 Pp.)", _lt("korea_exporte_yoy_3m", -5),
                            "korea_exporte_yoy_3m"),
                       Step("KOSPI fällt (20 T < 0)", _lt("kospi_20d", 0), "kospi_20d")],
    "china_preise_inflation": [Step("Importpreise drehen (3 M < −1 Pp.)", _lt("china_importpreise_yoy_3m", -1),
                                    "china_importpreise_yoy_3m"),
                               Step("US-2J fällt (20 T < −10 bp)", _lt("us_2y_20d_bp", -10), "us_2y_20d_bp")],
    "kupfer_aud_ki": [Step("Kupfer fällt (20 T < −5 %)", _lt("kupfer_20d", -5), "kupfer_20d"),
                      Step("KOSPI fällt (20 T < 0)", _lt("kospi_20d", 0), "kospi_20d")],
}
for _c in CHAINS:
    if _c.umkehr is None and _c.id in UMKEHR:
        _c.umkehr = UMKEHR[_c.id]


def _ret(s: pd.Series, n: int) -> float | None:
    s = s.dropna()
    return None if len(s) <= n else float(100 * (s.iloc[-1] / s.iloc[-1 - n] - 1))


def _chg(s: pd.Series, n: int, scale: float = 100) -> float | None:
    s = s.dropna()
    return None if len(s) <= n else float(scale * (s.iloc[-1] - s.iloc[-1 - n]))


def _yoy_monthly(s: pd.Series) -> pd.Series:
    """Monatsreihe (in der Tagestabelle nur am Monatsersten gefüllt) -> J/J-Rate in %."""
    s = s.dropna()
    return (100 * (s / s.shift(12) - 1)).dropna()


def measures(daily: pd.DataFrame, macro_w: pd.DataFrame, sheet: dict) -> M:
    d = daily
    col = lambda c: d[c] if c in d else pd.Series(dtype=float)
    mw = lambda k: macro_w[k] if k in macro_w else pd.Series(dtype=float)
    b = col("brent").dropna()
    m: M = {
        "brent_20d": _ret(b, 20), "brent_vs_20d": None if len(b) < 20 else float(100 * (b.iloc[-1] / b.iloc[-20:].mean() - 1)),
        "us_2y_20d_bp": _chg(col("us_2y"), 20), "breakeven_20d_bp": _chg(col("breakeven_10y"), 20),
        "vix": None if col("vix").dropna().empty else float(col("vix").dropna().iloc[-1]),
        "vix_20d": _chg(col("vix"), 20, 1), "spx_5d": _ret(col("spx"), 5), "ndx_20d": _ret(col("ndx"), 20),
        "kupfer_20d": _ret(col("kupfer"), 20), "kospi_20d": _ret(col("kospi"), 20),
        "hyg_ief_20d": _ret((col("hyg") / col("ief")).dropna(), 20) if "hyg" in d and "ief" in d else None,
        "hy": None if mw("MKT.hy_spread").dropna().empty else float(mw("MKT.hy_spread").dropna().iloc[-1]),
        "hy_20d_bp": _chg(mw("MKT.hy_spread"), 20), "fwd_5y5y_1w_bp": _chg(mw("US.fwd_5y5y"), 5),
    }
    for name in ("korea_exporte", "china_importpreise"):
        yoy = _yoy_monthly(col(name))
        m[f"{name}_yoy"] = None if yoy.empty else float(yoy.iloc[-1])
        m[f"{name}_yoy_3m"] = _chg(yoy, 3, 1)
    fr, de = mw("FR.10y").dropna(), mw("DE.10y").dropna()
    spread = (fr - de).dropna() * 100
    m["oat_bund_bp"] = None if spread.empty else float(spread.iloc[-1])
    m["oat_bund_20d_bp"] = _chg(spread, 20, 1)
    geo = sheet.get("geopolitik") or {}
    m["fed_kanal"] = (geo.get("oel_durchgriff") or {}).get("fed_kanal")
    for card in geo.get("themen", []):
        m[f"lage_{card['thema']}"] = card["lage"] if card["lage"] != "n.v." else None
    ca = ((sheet.get("taktisch") or {}).get("notenbanken") or {}).get("CA") or {}
    m["ca_pricing_1w_bp"] = ca.get("chg_1w_bp")
    # Education-Ketten (24.11.2026): Realzins, Kurve, UST-JGB, USDJPY/Aktien aus Tagesreihen ...
    real = col("real_10y").dropna()
    m["real_10y"] = None if real.empty else float(real.iloc[-1])
    m["real_10y_20d_bp"] = _chg(real, 20)
    m["usdjpy_20d"], m["spx_20d"] = _ret(col("USDJPY"), 20), _ret(col("spx"), 20)
    m["us_kurve_20d_bp"] = _chg((mw("US.10y") - mw("US.2y")).dropna(), 20)
    m["ust_jgb_20d_bp"] = _chg((mw("US.10y") - mw("JP.10y")).dropna(), 20)
    tp, ex = _chg(mw("US.term_premium_10y"), 20), _chg(mw("US.expected_10y"), 20)
    m["praemie_20d_bp"] = tp
    m["praemie_minus_erwartung_bp"] = None if tp is None or ex is None else tp - ex
    # ... und aus den v4-Bloecken des Fact Sheets
    desk = sheet.get("desk") or {}
    lq, zv, wa = (desk.get(k) or {} for k in ("liquiditaet", "zinsvol", "wachstum"))
    m["net_liq_13w"], m["sofr_iorb_bp"], m["move"] = lq.get("chg_13w_mrd"), lq.get("sofr_iorb_bp"), zv.get("move")
    m["gdpnow"], m["sahm"] = wa.get("gdpnow"), wa.get("sahm")
    c4, low = wa.get("erstantraege_4w_tsd"), wa.get("erstantraege_52w_tief_tsd")
    m["erstantraege_vs_tief_pct"] = None if not c4 or not low else 100 * (c4 / low - 1)
    usd = ((sheet.get("scorecard") or {}).get("waehrungen") or {}).get("USD") or {}
    m["usd_ueberraschung"] = usd.get("ueberr_60t")
    return {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in m.items()}


def _fmt_measure(v):
    if v is None:
        return "n.v."
    if isinstance(v, bool):
        return "ja" if v else "nein"
    return f"{v:.1f}".replace(".", ",") if isinstance(v, float) else str(v)


RANKING = Path(__file__).resolve().parents[1] / "data" / "macro_agent" / "wirkketten_ranking.csv"


def ranking(path: Path = RANKING) -> dict[tuple[str, str], str]:
    """Urteil aus scripts/research_wirkketten_ranking.py je (Kette, Arm); fehlt die Datei: leer."""
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    return {(k, a): u for (k, a), u in df.groupby(["kette", "arm"])["urteil"].first().items()}


def evaluate(m: M, exposure: dict | None, tests: dict | None = None) -> list[dict]:
    from .geo_framework import label
    tests = ranking() if tests is None else tests
    out = []
    for c in CHAINS:
        steps = [s.check(m) for s in c.schritte]
        stop = c.stopp.check(m)
        rev = [s.check(m) for s in c.umkehr or []]
        if rev and all(v is True for v in rev):
            status = "umgekehrt"
        elif stop:
            status = "gestoppt"
        elif steps and all(v is True for v in steps):
            status = "aktiv"
        elif steps and steps[0] is True:
            status = "anlaufend"
        else:
            status = "ruhend"
        beleg = []
        for asset, drv in c.beleg:
            x = ((exposure or {}).get(drv) or {}).get("assets", {}).get(label(asset))
            if x:
                beleg.append({"asset": label(asset), "treiber": drv, "status": x["status"], "heute": x["heute"], "oos": x["oos"]})
        stable = [b for b in beleg if b["status"] == "belegt"]
        out.append({
            "id": c.id, "name": c.name, "quelle": c.quelle, "status": status,
            "schritte": [{"text": s.text, "erfuellt": v, "wert": _fmt_measure(m.get(s.zeigt))} for s, v in zip(c.schritte, steps)],
            "stopp": {"text": c.stopp.text, "erfuellt": stop},
            "assets": {label(a): ("steigt" if s > 0 else "fällt") for a, s in c.assets.items()},
            "beleg": "belegt" if stable and len(stable) == len(c.beleg) else ("teilweise" if stable else "Hypothese"),
            "beleg_details": beleg, "hinweis": c.hinweis,
            "test": tests.get((c.id, "umgekehrt" if status == "umgekehrt" else "aktiv"),
                              tests.get((c.id, "–"), "ungetestet")),
            "umkehr": [{"text": s.text, "erfuellt": v, "wert": _fmt_measure(m.get(s.zeigt))}
                       for s, v in zip(c.umkehr or [], rev)],
            # Richtung, die das Ledger prueft: umgekehrte Kette = umgedrehtes Vorzeichen
            "ledger_assets": {a: (-s if status == "umgekehrt" else s) for a, s in c.assets.items()},
        })
    return out
