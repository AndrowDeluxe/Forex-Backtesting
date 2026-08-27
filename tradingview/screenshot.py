"""Chart-Screenshot von TradingView per Playwright, fuer visuelle Analyse durch
Claude (Read-Tool liest Bilder direkt). Gleiches Chromium-Muster wie
OU-Modell-MT5-Bridge/scanner.py (dort: externe Scan-Website scrapen) -- hier:
TradingView-Chart aufrufen + Screenshot speichern.

Login-Strategie (2026-08-12, dritter Anlauf): der TradingView-Account des Users
verifiziert sich ueber Google. Zwei automatisierte Login-Versuche wurden von
Google aktiv blockiert ("Dieser Browser ist moeglicherweise nicht sicher") --
sowohl im Playwright-Test-Chromium als auch in echtem, per channel="msedge"
gestartetem Edge, weil Playwright JEDEN von ihm gesteuerten Browser per CDP
(Chrome DevTools Protocol) mit erkennbaren Automatisierungs-Signalen versieht,
unabhaengig vom Browser-Branding. Ein direkter Zugriff auf das echte
Haupt-Edge-Profil des Users (wo er taeglich eingeloggt ist) wurde bewusst NICHT
automatisiert -- zu invasiv (Zugriff auf saemtliche anderen gespeicherten
Logins/Passwoerter/Verlauf in diesem Profil).

Stattdessen: ein NEUES, leeres, isoliertes Edge-Profilverzeichnis
(.tradingview_edge_profile/, gitignored, enthaelt NUR TradingView-Session-Daten,
sonst nichts) wurde per normalem `msedge.exe --user-data-dir=...`-Aufruf OHNE
Playwright geoeffnet -- der User loggt sich dort manuell in einem echten,
nicht-automatisierten Fenster ein (keine Google-Bot-Erkennung, da kein CDP
involviert ist). capture_chart() oeffnet danach GENAU dieses Profilverzeichnis
per Playwrights launch_persistent_context() wieder -- das ist zwar wieder
CDP-automatisiert, aber es findet dabei kein Sign-in-Vorgang mehr statt (die
Session-Cookies sind schon da), also gibt es nichts, was Google blockieren
koennte."""

from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_DIR = Path(__file__).resolve().parents[1]
EDGE_PROFILE_DIR = REPO_DIR / ".tradingview_edge_profile"

CHART_URL_TMPL = "https://www.tradingview.com/chart/?symbol={exchange}:{symbol}"
_INTERVAL_PARAM = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D", "1w": "W"}


def capture_chart(
    symbol: str, exchange: str, out_path: str | Path, interval: str = "1d",
    login: bool = True, wait_ms: int = 4000, headless: bool = True,
) -> Path:
    """Speichert einen PNG-Screenshot des TradingView-Charts fuer symbol/exchange
    unter out_path (z.B. "AAPL", "NASDAQ") und gibt den Path zurueck.

    login=True (Default): oeffnet das isolierte Edge-Profil
    (.tradingview_edge_profile/) per launch_persistent_context() -- setzt
    voraus, dass sich der User dort vorher EINMALIG manuell eingeloggt hat
    (siehe Modul-Docstring). Wirft FileNotFoundError mit Anleitung, falls das
    Profilverzeichnis noch nicht existiert.
    login=False: ruft den Chart in einem frischen, anonymen Kontext auf (kein
    gespeichertes Layout, aber ohne jede Vorbereitung nutzbar)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    chart_url = CHART_URL_TMPL.format(exchange=exchange, symbol=symbol)
    tv_interval = _INTERVAL_PARAM.get(interval)
    if tv_interval:
        chart_url += f"&interval={tv_interval}"

    with sync_playwright() as p:
        if login:
            if not EDGE_PROFILE_DIR.exists():
                raise FileNotFoundError(
                    f"{EDGE_PROFILE_DIR} nicht gefunden -- zuerst ein isoliertes Edge-Profil "
                    f"anlegen und dort manuell bei TradingView einloggen (siehe Modul-Docstring)."
                )
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(EDGE_PROFILE_DIR), channel="msedge",
                headless=headless, viewport={"width": 1600, "height": 900},
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(chart_url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(out_path))
            finally:
                context.close()
        else:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            try:
                page.goto(chart_url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(out_path))
            finally:
                browser.close()

    return out_path
