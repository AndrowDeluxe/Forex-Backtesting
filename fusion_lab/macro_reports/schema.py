"""JSON-Schema fuer extrahierte SMH-Makro-Reports (Phase 1, Schritt 2).

Grundregel der Extraktion (Lookahead-Schutz): WOERTLICH uebersetzen, nichts
ergaenzen. Jedes inhaltliche Feld einer Idee bekommt ein Textzitat als Beleg;
was im Report nicht steht, bleibt None. Luecken (fehlender Stop, fehlendes
Ziel) fuellt spaeter backtest.py nach vorab registrierten Standardregeln --
nie der Extrahierende.

Eine Datei je Report: fusion_lab/data/macro_reports/extracted/<msg_id>.json
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Direction = Literal["long", "short"]
Role = Literal["main", "secondary", "event", "bias", "hedge"]
# v2 (Nutzerdefinition 16.10.): aktiv = Makro klar, Einstieg nach technischer Bestaetigung (bevorzugt
# Ruecksetzer); event = wartet auf ein bestimmtes Makro-Ereignis; watch = Makro unklar, beobachten;
# bias = nur Richtung ohne Trade-Charakter; inaktiv = nicht handeln. "vorbereitet" nur noch fuer v1-Dateien.
Status = Literal["aktiv", "event", "watch", "bias", "inaktiv", "vorbereitet"]
Section = Literal["trade_tabelle", "finales_buch", "setup_abschnitt", "waehrungsabschnitt", "fliesstext"]
Confidence = Literal["hoch", "mittel-hoch", "mittel", "mittel-niedrig", "niedrig"]

# Report-Schreibweisen -> Instrument-Keys (Dukascopy, combined_strategy/data.py:INSTRUMENTS,
# plus Kreuze, die backtest.py bei Bedarf ergaenzt). DXY bleibt DXY (nicht direkt handelbar,
# backtest.py bildet es ueber den USD-Korb ab oder ueberspringt es).
_ALIASES = {
    "XAUUSD": "GOLD", "GOLD": "GOLD", "XAU": "GOLD",
    "XAGUSD": "SILVER", "SILBER": "SILVER", "SILVER": "SILVER", "XAG": "SILVER",
    "WTI": "OIL", "USOIL": "OIL", "OIL": "OIL", "OEL": "OIL", "ÖL": "OIL", "CRUDE": "OIL",
    "BRENT": "BRENT", "UKOIL": "BRENT",
    "US500": "SP500", "SPX": "SP500", "SP500": "SP500", "S&P500": "SP500", "SPX500": "SP500", "ES": "SP500",
    "NAS100": "NASDAQ", "NASDAQ": "NASDAQ", "NDX": "NASDAQ", "US100": "NASDAQ", "NQ": "NASDAQ",
    "US30": "US30", "DOW": "US30", "DJI": "US30", "DJIA": "US30",
    "DAX": "DAX", "GER40": "DAX", "DE40": "DAX",
    "BTC": "BTCUSD", "BTCUSD": "BTCUSD", "BITCOIN": "BTCUSD",
    "COPPER": "COPPER", "KUPFER": "COPPER",
    "DXY": "DXY", "USDX": "DXY", "DOLLARINDEX": "DXY",
}
_CCY = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}


def normalize_instrument(raw: str) -> str:
    """'EUR/USD', 'eurusd', 'Gold', 'US500' -> 'EURUSD', 'GOLD', 'SP500'."""
    s = re.sub(r"[\s/_\-.]", "", raw).upper()
    if s in _ALIASES:
        return _ALIASES[s]
    if len(s) == 6 and s[:3] in _CCY and s[3:] in _CCY:
        return s
    raise ValueError(f"unbekanntes Instrument {raw!r} -- in schema._ALIASES ergaenzen")


class Idea(BaseModel):
    instrument: str
    direction: Direction
    role: Role
    status: Status
    confidence: Confidence | None = None
    entry_zone: tuple[float, float] | None = None   # (von, bis), wie genannt
    stop: float | None = None
    targets: list[float] = Field(default_factory=list)
    activation_text: str | None = None
    activation_price: float | None = None            # nur wenn numerisch genannt
    activation_side: Literal["above", "below"] | None = None
    invalidation_price: float | None = None
    horizon_days: int | None = None
    quote: str                                        # Belegstelle fuer Richtung/Status
    level_quote: str | None = None                    # Belegstelle fuer Zahlen (Stop/Ziel/Aktivierung)
    stars: int | None = Field(default=None, ge=1, le=6)   # Sterne/Gewichtung wie im Report (roh)
    gates_met: int | None = Field(default=None, ge=0)     # z. B. 4 bei "4/5 Gates"
    gates_total: int | None = Field(default=None, ge=1)
    section: Section | None = None                    # woher die Idee stammt
    event: str | None = None                          # Makro-Ereignis, an dem die Idee haengt (z. B. "Kanada-CPI")

    @field_validator("instrument", mode="before")
    @classmethod
    def _norm(cls, v: str) -> str:
        return normalize_instrument(v)

    @model_validator(mode="after")
    def _levels_need_quote(self):
        has_levels = any(x is not None for x in (self.stop, self.activation_price, self.invalidation_price,
                                                  self.entry_zone)) or self.targets
        if has_levels and not self.level_quote:
            raise ValueError(f"{self.instrument}: Zahlen ohne level_quote")
        if (self.activation_price is None) != (self.activation_side is None):
            raise ValueError(f"{self.instrument}: activation_price und activation_side nur gemeinsam")
        return self


class Ranking(BaseModel):
    currency: str
    rank: int | None = None
    bias: str | None = None          # Wortlaut, z. B. "STARK / Event-Risiko", "bearish"
    score: float | None = None       # Zahl aus dem Report (z. B. Quant- oder SMT-Score)


class Report(BaseModel):
    msg_id: int
    posted_utc: str                  # Telegram-Postzeit, ISO
    report_date: str | None = None   # Datum im PDF, falls abweichend
    generation: Literal[1, 2, 3]
    regime: str | None = None
    ranking: list[Ranking] = Field(default_factory=list)
    no_trade_rules: list[str] = Field(default_factory=list)
    ideas: list[Idea] = Field(default_factory=list)
    notes: str | None = None         # Auffaelligkeiten bei der Extraktion (z. B. "Titel falsch datiert")


def load(path) -> Report:
    from pathlib import Path
    return Report.model_validate_json(Path(path).read_text(encoding="utf-8"))
