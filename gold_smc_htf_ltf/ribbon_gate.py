"""Richtungs-Gate fuer die CTNL-Beine auf Basis des MTF-EMA-Ribbons.

EINE Stelle fuer alle drei Bridges (Funded-Portfolio-Bridge,
FKInstantFunding-MT5-Bridge, EK-Portfolio-Bridge). Bewusst hier im Repo und
nicht je Bridge kopiert: die drei sind schon einmal auseinandergelaufen
(siehe Memory `three_bridges_not_same_state`), und ein Richtungsfilter, der
auf zwei Konten anders entscheidet als auf dem dritten, waere genau dieselbe
Falle nochmal.

WAS ES TUT
Der Ribbon (H4-EMA50, D1-EMA50, D1-EMA200, W1-EMA50 -- aus dem eigenen
Pine-Script des Nutzers, siehe ema_ribbon.py) wird als TRENDRICHTUNG gelesen:
Preis ueber allen vier EMAs = Aufwaerts (+1), unter allen = Abwaerts (-1),
dazwischen = neutral (0). Erlaubt sind dann nur trendkonforme Einstiege --
long im Aufwaerts-, short im Abwaertstrend.

WARUM
knowledge/projects/ctnl-kostenvalidierung.md Befund 15: als Dehnungsfilter
(`require_ribbon_stretch`, die bisher einzige Verdrahtung) ist der Ribbon
wertlos (SigmaR +24,5 gegen +136,7 der Baseline). Als Richtung gelesen ist er
der staerkste gepruefte Hebel: SigmaR +330,6, PF 1,87, Anker-Walk-Forward
OOS +243,6 gegen +153,2. Er ist ausserdem die einzige Variante, unter der die
SHORT-Seite positiv wird (+0,174 Ø R gegen -0,161 mit einem generischen
EMA-Stapel).

W1 WIRD AUS D1 ABGELEITET
Der Data Lake fuehrt GOLD_D1, aber kein GOLD_W1. Statt eine neue
Ingest-Quelle samt neuem Ausfallmodus aufzumachen, wird W1 aus D1
resampled -- ein W1-EMA50 auf resampelten Tagesbars ist dieselbe Groesse.
Die Gleichwertigkeit ist gegen die gefetchten W1-Daten geprueft (siehe
CHANGELOG 2026-09-25).

FAIL-SAFE: BLOCKIEREN, NICHT DURCHLASSEN
Fehlen Daten oder ist der Ribbon nicht berechenbar, gibt `allows()` False
zurueck -- der Entry unterbleibt. Die Gegenrichtung (im Zweifel handeln)
waere gefaehrlicher: das Gate ist genau dafuer da, die verlustbringende
Haelfte der Signale zu verwerfen. Ein Datenausfall darf nicht dazu fuehren,
dass sie wieder durchkommt.
"""

from __future__ import annotations

import pandas as pd

from .ema_ribbon import compute_ribbon

_EMA_COLS = ("ema_h4", "ema_d1_fast", "ema_d1_slow", "ema_w1")


def w1_aus_d1(d1_df: pd.DataFrame) -> pd.DataFrame:
    """Wochenbars aus Tagesbars. Siehe Modul-Docstring."""
    return d1_df.resample("W").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


def ribbon_direction(h4_df: pd.DataFrame, d1_df: pd.DataFrame,
                     w1_df: pd.DataFrame | None = None) -> pd.Series:
    """+1 Aufwaerts, -1 Abwaerts, 0 neutral -- indiziert auf die H4-Bars.

    Ausschliesslich rueckwaertsgerichtet: compute_ribbon() verschiebt jede
    HTF-EMA um ihre eigene Barlaenge, bevor sie auf den H4-Index gelegt wird
    (No-Lookahead-Konvention des Pakets).
    """
    if w1_df is None:
        w1_df = w1_aus_d1(d1_df)
    rib = compute_ribbon(h4_df, d1_df, w1_df)
    px = rib["close"]
    stack = rib.loc[:, list(_EMA_COLS)]
    oben = px > stack.max(axis=1)
    unten = px < stack.min(axis=1)
    richtung = pd.Series(0, index=rib.index, dtype="int8")
    richtung[oben] = 1
    richtung[unten] = -1
    richtung[stack.isna().any(axis=1)] = 0
    return richtung


def allows(direction: int, h4_df: pd.DataFrame, d1_df: pd.DataFrame,
           w1_df: pd.DataFrame | None = None,
           at: pd.Timestamp | None = None) -> tuple[bool, str]:
    """Darf ein Entry in `direction` (+1 long, -1 short) jetzt stattfinden?

    Rueckgabe: (erlaubt, Begruendung) -- die Begruendung geht ins Log, damit
    im Nachhinein nachvollziehbar ist, warum ein Signal nicht gehandelt wurde.
    """
    try:
        richtung = ribbon_direction(h4_df, d1_df, w1_df)
    except Exception as e:  # Daten fehlen/unbrauchbar -> blockieren, siehe Docstring
        return False, f"Ribbon nicht berechenbar ({type(e).__name__}: {e}) -- Entry blockiert"
    if richtung.empty:
        return False, "Ribbon leer (keine H4-Daten) -- Entry blockiert"

    if at is not None:
        gueltig = richtung.loc[:at]
        if gueltig.empty:
            return False, f"kein Ribbon-Wert bis {at} -- Entry blockiert"
        stand = int(gueltig.iloc[-1])
        zeit = gueltig.index[-1]
    else:
        stand = int(richtung.iloc[-1])
        zeit = richtung.index[-1]

    if stand == 0:
        return False, f"Ribbon neutral (Preis zwischen den EMAs, Stand {zeit}) -- kein trendkonformer Entry"
    if stand == direction:
        return True, f"Ribbon {'aufwaerts' if stand > 0 else 'abwaerts'} (Stand {zeit}) -- trendkonform"
    return False, (f"Ribbon {'aufwaerts' if stand > 0 else 'abwaerts'} (Stand {zeit}), "
                   f"Signal {'long' if direction > 0 else 'short'} -- gegen den Trend, verworfen")
