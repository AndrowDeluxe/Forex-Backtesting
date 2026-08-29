"""Gemeinsame Handelszeiten-Sperre fuer Forex/Gold/Index-Paper-Bots dieses
Repos (User-Wunsch 2026-08-29: "damit nichts unnoetig am Wochenende laeuft"
+ Pause zur taeglichen Spread-Stunde 23:00 Uhr). Zuerst in
fk_instant_funding/paper_bot.py gebaut und dort verifiziert (siehe dessen
is_market_paused()-Historie), hier fuer Wiederverwendung durch weitere Bots
extrahiert, die dasselbe Muster brauchen (ek_portfolio, gold_smc_htf_ltf).

GILT NICHT fuer 24/7-Maerkte (Krypto/BTC) -- ein Bein, das rund um die Uhr
handelt, darf diese Sperre nicht pauschal uebernehmen (siehe ek_portfolio/
paper_bot.py::scan_once(), wo der btc_ema_cross-Scan bewusst UNGESCHUETZT
bleibt)."""

import pandas as pd

LOCAL_TZ = "Europe/Berlin"
SPREAD_HOUR_LOCAL = 23  # taeglicher Broker-Rollover/Swap-Zeitpunkt, spuerbar breitere Spreads


def local_dt(end_utc_naive: pd.Timestamp) -> pd.Timestamp:
    """`end_utc_naive` muss UTC-naiv sein (Konvention aller Scan-Funktionen
    in diesem Repo, siehe je Bot _utc_naive()) -- fuer Uhrzeit-basierte
    Entscheidungen muss das nach ECHTER lokaler Zeit umgerechnet werden,
    sonst verschiebt sich jede Stunden-Schwelle um den UTC-Offset (+1/+2h,
    real gefundener Bug in fk_instant_funding/paper_bot.py am 2026-08-29:
    DAILY_SUMMARY_HOUR verglich faelschlich direkt gegen UTC-Stunde)."""
    return end_utc_naive.tz_localize("UTC").tz_convert(LOCAL_TZ)


def is_market_paused(end_utc_naive: pd.Timestamp, spread_hour_local: int = SPREAD_HOUR_LOCAL) -> bool:
    """Fuer Forex-/Gold-/Index-Instrumente: Wochenende (Samstag+Sonntag
    komplett, grosszuegige Kalendertag-Naeherung an die echten Marktzeiten)
    und die taegliche Spread-Stunde. NICHT fuer 24/7-Maerkte verwenden."""
    local = local_dt(end_utc_naive)
    if local.weekday() >= 5:  # 5=Samstag, 6=Sonntag
        return True
    if local.hour == spread_hour_local:
        return True
    return False
