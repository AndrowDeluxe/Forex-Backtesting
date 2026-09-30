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

import logging

import pandas as pd

from .ema_ribbon import compute_ribbon

log = logging.getLogger(__name__)

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


# --------------------------------------------------------------- Bridge-Anbindung


def _lade_bars(start: str, end: str, source: str):
    """H4 + D1, je nach Bridge aus dem Lake (mit Live-Fallback) oder direkt.

    Gleiches Muster wie challenge_portfolio/paper_bot.py::_scan_ctnl -- der
    Lake-Pfad faellt bei veralteten Daten automatisch auf den Live-Fetch
    zurueck, statt das Bein stillzulegen.
    """
    from .data import fetch_gold_d1 as live_d1, fetch_gold_h4 as live_h4
    if source == "lake":
        import data_lake.reader as _lake
        h4_fn = _lake.with_live_fallback(_lake.fetch_gold_h4, live_h4)
        d1_fn = _lake.with_live_fallback(_lake.fetch_gold_d1, live_d1)
    else:
        h4_fn, d1_fn = live_h4, live_d1
    return h4_fn(start, end, force_refresh=False), d1_fn(start, end, force_refresh=False)


# Vorlauf fuer den Ribbon: die langsamste EMA ist D1-200, dazu W1-50 (= 350
# Kalendertage). 900 Tage geben beiden reichlich Einschwingzeit -- zu kurz
# gewaehlt liefert der Ribbon am linken Rand Unsinn, und das faellt live
# nicht auf, weil nur der letzte Wert gelesen wird.
RIBBON_LOOKBACK_DAYS = 900


def filter_trades(trades: pd.DataFrame, *, source: str = "lake",
                  leg: str = "ctnl") -> tuple[pd.DataFrame, str]:
    """Behaelt nur trendkonforme Zeilen: long im Aufwaerts-, short im
    Abwaertstrend. Rueckgabe: (gefilterte Trades, Log-Zeile).

    Fuer Funded-Portfolio-Bridge und FKInstantFunding-MT5-Bridge, die mit
    Trade-TABELLEN arbeiten. EK geht ueber allows(), weil es je Signal
    entscheidet.

    DREI ZUSTAENDE, NICHT ZWEI (Fund 2026-09-30 beim Test gegen echte Daten):
      trendkonform      -> behalten
      gegen den Trend   -> verworfen, das ist die Risikoregel
      KEIN RIBBON-WERT  -> ebenfalls verworfen, aber SEPARAT gemeldet
    Der dritte Fall ist kein Strategie-Urteil, sondern eine Datenluecke. Er
    darf nicht als "nicht trendkonform" durchgehen: der Lake haelt nur ~4
    Monate H4 (gemessen 2026-09-30: 1.060 Bars ab 2026-05-26), und ohne
    diese Trennung haette das Gate 96 % der Signale aus dem FALSCHEN Grund
    verworfen, ohne dass es auffaellt.

    Deckt der Lake die angefragte Spanne nicht ab, wird EINMAL auf den
    Live-Fetch ausgewichen, bevor blockiert wird.
    """
    if trades is None or trades.empty:
        return trades, ""

    # Richtungsspalte zuerst pruefen -- eine Spalte voller None ist NICHT None
    # (Fund 2026-09-30: `trades.get("direction")` lieferte eine None-Spalte,
    # die stillschweigend zu "short" gemappt wurde).
    if "direction" not in trades.columns:
        return trades.iloc[0:0], f"{leg}: Trade-Tabelle ohne Spalte 'direction' -- alle Entries blockiert"
    roh = trades["direction"]
    if roh.isna().any():
        return trades.iloc[0:0], (
            f"{leg}: {int(roh.isna().sum())} von {len(trades)} Zeilen ohne Richtung "
            "-- alle Entries blockiert (fail-safe)")
    d = roh.map(lambda x: 1 if x in (1, "long") else -1).to_numpy()

    t = pd.to_datetime(trades["entry_time"])
    t_naive = t.dt.tz_convert(None) if t.dt.tz is not None else t
    start = (t_naive.min() - pd.Timedelta(days=RIBBON_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = (t_naive.max() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")

    stand = None
    for versuch in ([source, "live"] if source == "lake" else [source]):
        try:
            h4, d1 = _lade_bars(start, end, versuch)
            richtung = ribbon_direction(h4, d1)
            r_idx = pd.to_datetime(richtung.index)
            richtung.index = r_idx.tz_convert(None) if r_idx.tz is not None else r_idx
            kandidat = richtung.reindex(t_naive, method="ffill")
            if not kandidat.isna().any():
                stand = kandidat.to_numpy()
                break
            fehlend = int(kandidat.isna().sum())
            log.warning("%s: Ribbon deckt %d von %d Signalen nicht ab (Quelle %s, "
                        "Historie ab %s)", leg, fehlend, len(trades), versuch, richtung.index.min())
            stand = kandidat.to_numpy()   # als Fallback behalten, falls "live" auch nicht reicht
        except Exception as e:
            log.warning("%s: Ribbon aus Quelle %s nicht berechenbar (%s: %s)",
                        leg, versuch, type(e).__name__, e)
    if stand is None:
        return trades.iloc[0:0], (
            f"{leg}: Ribbon aus keiner Quelle berechenbar -- ALLE Entries blockiert "
            "(fail-safe, siehe ribbon_gate.py)")

    ohne_wert = pd.isna(stand)
    konform = (~ohne_wert) & (((d == 1) & (stand > 0)) | ((d == -1) & (stand < 0)))
    behalten = trades[konform]

    teile = []
    gegen = int((~ohne_wert).sum() - konform.sum())
    if gegen:
        teile.append(f"{gegen} gegen den Trend verworfen (Risikoregel, kein Fehler)")
    if ohne_wert.any():
        teile.append(f"{int(ohne_wert.sum())} OHNE Ribbon-Wert blockiert -- DATENLUECKE, "
                     "nicht Strategie (Lake-Historie zu kurz?)")
    hinweis = f"{leg}: {len(behalten)} von {len(trades)} Signalen behalten; " + "; ".join(teile) if teile else ""
    return behalten, hinweis


def allows_now(direction: int, *, source: str = "live",
               leg: str = "ctnl") -> tuple[bool, str]:
    """Wie allows(), holt die Daten aber selbst -- fuer Bridges, die je
    SIGNAL entscheiden statt ueber eine Trade-Tabelle (EK-Portfolio-Bridge).

    Fuer die Live-Entscheidung zaehlt nur der JUENGSTE Ribbon-Wert; der
    Vorlauf muss lediglich reichen, damit D1-EMA200 und W1-EMA50
    eingeschwungen sind. RIBBON_LOOKBACK_DAYS deckt beides mit Reserve.

    FAIL-SAFE wie ueberall: bei Datenproblemen False (kein Entry).
    """
    import pandas as _pd
    ende = _pd.Timestamp.now(tz="UTC")
    start = (ende - _pd.Timedelta(days=RIBBON_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = (ende + _pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    for versuch in ([source, "live"] if source == "lake" else [source]):
        try:
            h4, d1 = _lade_bars(start, end, versuch)
            erlaubt, grund = allows(direction, h4, d1)
            return erlaubt, f"{leg}: {grund}"
        except Exception as e:
            log.warning("%s: Ribbon aus Quelle %s nicht abrufbar (%s: %s)",
                        leg, versuch, type(e).__name__, e)
    return False, f"{leg}: Ribbon-Daten nicht abrufbar -- Entry blockiert (fail-safe)"
