"""VORAB-REGISTRIERUNG (18.11.2026, vor dem ersten Test committet). Nach dem ersten Lauf nicht mehr aendern;
jede Aenderung waere eine neue, gezaehlte Variante und gehoert in eine neue Lock-Version.

Merkmale mit Wirkkette und erwartetem Vorzeichen je Metall (+1 = hoher Wert bullisch, -1 = bearisch,
None = fuer dieses Metall nicht anwendbar). `lb=True`: Veraenderung ueber L Wochen, L aus LOOKBACKS ist der
EINZIGE optimierte Punkt (Richtwert Overfitting-Sperre: <= 9). `info=True`: nur berichtet, nie Kandidat.
"""

from __future__ import annotations

LOCK_NAME = "metals_htf_v1"
SPLIT = ("2004-01-01", "2017-12-31", "2026-05-10", "2026-11-13")   # IS / OOS-Ende / Tresor-Ende
IS_SUB = (("2004-01-01", "2010-12-31"), ("2011-01-01", "2017-12-31"))

METALS = ("GOLD", "SILVER", "PLATINUM")
COST_BPS = {"GOLD": 5.0, "SILVER": 10.0, "PLATINUM": 15.0}   # je Seite und Positionseinheit (Nutzer 18.11.)
SWAP_PA = 0.03          # nur Robustheits-Probe: Haltekosten 3 % p. a. je Einheit Exposure (Annahme)
LOOKBACKS = (4, 13, 26)
HORIZONS = (4, 13, 26)
PCT_WINDOW, PCT_MIN = 156, 52     # gleitendes Perzentil (Wochen)
COT_WINDOW, COT_MIN = 156, 26     # COT-Index wie im Screener (Berichte)
UPPER, LOWER = 2 / 3, 1 / 3       # Regime: oberes Drittel long, unteres short, sonst flat
N_RANDOM = 1000                   # Zufalls-Timing-Laeufe
T_MIN = 2.0                       # Kandidat: IS-t >= 2 mit erwartetem Vorzeichen
RANDOM_PCT_MIN = 95.0             # Erfolg Stufe 2: Zufalls-Perzentil >= 95 UND Sharpe > immer long, IS und OOS

ALL = {"GOLD": 1, "SILVER": 1, "PLATINUM": 1}
NEG = {"GOLD": -1, "SILVER": -1, "PLATINUM": -1}

FEATURES: dict[str, dict] = {
    # --- Screener-Bausteine (Rohstoff-Screener 1.0)
    "trend":       {"gruppe": "Screener", "lb": False, "vorz": ALL,
                    "kette": "Kurs ueber SMA50/200 und steigende SMA50 -> Trend setzt sich fort"},
    "momentum":    {"gruppe": "Screener", "lb": False, "vorz": ALL,
                    "kette": "126-T-Rendite ohne letzten Monat, vola-skaliert (Zeitreihen-Momentum)"},
    "rel_staerke": {"gruppe": "Screener", "lb": True, "vorz": ALL,
                    "kette": "Metall staerker als der Rohstoffkorb (DBC) -> eigene Nachfrage"},
    "lage_52w":    {"gruppe": "Screener", "lb": False, "vorz": ALL,
                    "kette": "nahe am 52-W-Hoch = Trend (Hochs ziehen weitere Hochs nach sich)"},
    "cot_mit":     {"gruppe": "Screener", "lb": False, "vorz": ALL,
                    "kette": "Managed Money hoch netto long = Fluss laeuft mit dem Preis (gold_confirm-Befund)"},
    "cot_contra":  {"gruppe": "Screener", "lb": False, "vorz": NEG,
                    "kette": "Managed Money extrem long = ueberdehnt, Umkehr (Screener-1.0-Annahme)"},
    # --- Makro
    "real_delta":  {"gruppe": "Makro", "lb": True, "vorz": NEG,
                    "kette": "Realzins 10J steigt -> Opportunitaetskosten zinsloser Metalle steigen"},
    "real_gap":    {"gruppe": "Makro", "lb": False, "vorz": NEG,
                    "kette": "Realzins ueber seinem 52-W-Mittel -> restriktiv fuer Edelmetalle"},
    "usd_delta":   {"gruppe": "Makro", "lb": True, "vorz": NEG,
                    "kette": "Dollar steigt -> Metalle in USD teurer fuer den Rest der Welt"},
    "be_delta":    {"gruppe": "Makro", "lb": True, "vorz": ALL,
                    "kette": "Inflationserwartung steigt -> Nachfrage nach Sachwerten"},
    "us2_delta":   {"gruppe": "Makro", "lb": True, "vorz": NEG,
                    "kette": "2J-Rendite steigt = Markt erwartet straffere Fed"},
    "curve_delta": {"gruppe": "Makro", "lb": True, "vorz": ALL,
                    "kette": "Kurve 10J-2J wird steiler = Lockerung/Reflation"},
    "gld_flow":    {"gruppe": "Makro", "lb": True, "vorz": ALL,
                    "kette": "GLD-Bestand waechst = physische Investmentnachfrage"},
    "cb_12m":      {"gruppe": "Makro", "lb": False, "vorz": ALL,
                    "kette": "Zentralbanken kaufen netto Gold (IMF, 12 Monate)"},
    "gvz":         {"gruppe": "Makro", "lb": False, "vorz": ALL, "info": True,
                    "kette": "Gold-Vola-Regime (nur Info, kein Vorzeichen erwartet)"},
    # --- Relativ
    "gsr_z":       {"gruppe": "Relativ", "lb": False, "vorz": {"GOLD": -1, "SILVER": 1, "PLATINUM": None},
                    "kette": "Gold/Silber-Ratio hoch (z 52 W) -> Silber billig, holt auf"},
    "cu_au":       {"gruppe": "Relativ", "lb": True, "vorz": {"GOLD": None, "SILVER": 1, "PLATINUM": 1},
                    "kette": "Kupfer/Gold steigt = Wachstum -> Industriemetall-Anteil von Silber/Platin profitiert"},
    "faber":       {"gruppe": "Relativ", "lb": False, "vorz": ALL,
                    "kette": "Kurs ueber 10-Monats-SMA (Faber) = langfristiger Trend"},
}


def applicable(feature: str, metal: str) -> bool:
    return FEATURES[feature]["vorz"].get(metal) is not None


def variants() -> list[tuple[str, int | None]]:
    """(Merkmal, Lookback) -- Lookback None fuer Niveau-Merkmale."""
    out = []
    for f, s in FEATURES.items():
        out += [(f, L) for L in LOOKBACKS] if s["lb"] else [(f, None)]
    return out


def name(feature: str, L: int | None) -> str:
    return feature if L is None else f"{feature}_{L}w"
