"""OneNote-Import ueber Microsoft Graph (Strang 0 des Dachprojekts).

Zieht Notizbuecher -> Abschnittsgruppen -> Abschnitte -> Seiten nach
fusion_lab/raw/onenote/<Notizbuch>/<Abschnitt>/ -- je Seite das Original-HTML,
eine Textfassung (.md) und die eingebetteten Bilder. Inkrementell: eine Seite
wird nur neu geladen, wenn sich ihr lastModifiedDateTime geaendert hat
(Manifest raw/onenote/_manifest.json).

Login: Device-Code-Flow (persoenliches Microsoft-Konto, Scope Notes.Read).
Beim ersten Lauf zeigt das Skript einen Code + URL, der Token wird danach in
fusion_lab/.auth/ gecacht.

    python -m fusion_lab.ingest.onenote --list            # nur Notizbuecher zeigen
    python -m fusion_lab.ingest.onenote                   # alle Notizbuecher
    python -m fusion_lab.ingest.onenote --notebook "Trading"
"""

import argparse
import sys
import time

import requests
from bs4 import BeautifulSoup

from fusion_lab._secrets import AUTH_DIR, RAW_DIR, load_onenote_config
from fusion_lab.ingest.common import load_json, safe_name, save_json

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["Notes.Read"]
OUT_DIR = RAW_DIR / "onenote"
MANIFEST = OUT_DIR / "_manifest.json"
TOKEN_CACHE = AUTH_DIR / "msal_cache.bin"


def get_token(cfg: dict) -> str:
    import msal  # erst hier, damit --help ohne Paket laeuft

    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE.exists():
        cache.deserialize(TOKEN_CACHE.read_text(encoding="utf-8"))
    app = msal.PublicClientApplication(
        cfg["client_id"],
        authority=cfg.get("authority", "https://login.microsoftonline.com/consumers"),
        token_cache=cache,
    )
    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Device-Flow fehlgeschlagen: {flow}")
        print(flow["message"], flush=True)
        result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"Login fehlgeschlagen: {result.get('error_description', result)}")
    if cache.has_state_changed:
        TOKEN_CACHE.write_text(cache.serialize(), encoding="utf-8")
    return result["access_token"]


class Graph:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"

    def get(self, url: str, **kw) -> requests.Response:
        if url.startswith("/"):
            url = GRAPH + url
        for attempt in range(6):
            r = self.s.get(url, timeout=60, **kw)
            if r.status_code in (429, 503, 504):
                wait = int(r.headers.get("Retry-After", 2 ** attempt * 5))
                print(f"  Graph drosselt ({r.status_code}), warte {wait}s ...", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        r.raise_for_status()
        return r

    def list(self, url: str) -> list[dict]:
        items = []
        while url:
            data = self.get(url).json()
            items.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
        return items


def iter_sections(g: Graph, parent_url: str, prefix: tuple[str, ...]):
    """Abschnitte rekursiv inkl. Abschnittsgruppen; liefert (Pfad, Abschnitt)."""
    for sec in g.list(f"{parent_url}/sections"):
        yield prefix + (sec["displayName"],), sec
    for grp in g.list(f"{parent_url}/sectionGroups"):
        yield from iter_sections(g, f"/me/onenote/sectionGroups/{grp['id']}",
                                 prefix + (grp["displayName"],))


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "li", "td", "img"]):
        if el.name == "img":
            lines.append(f"[Bild: {el.get('alt') or el.get('data-fullres-src', '')[:40]}]")
            continue
        txt = el.get_text(" ", strip=True)
        if not txt:
            continue
        if el.name in ("h1", "h2", "h3"):
            lines.append("#" * int(el.name[1]) + " " + txt)
        elif el.name == "li":
            lines.append("- " + txt)
        else:
            lines.append(txt)
    return "\n\n".join(lines)


def save_page(g: Graph, page: dict, folder) -> int:
    html = g.get(f"/me/onenote/pages/{page['id']}/content",
                 params={"includeIDs": "false"}).text
    stem = safe_name(page.get("title") or "ohne Titel") + "__" + page["id"][-8:]
    folder.mkdir(parents=True, exist_ok=True)

    # Bilder liegen hinter Graph-URLs mit Login -> herunterladen, lokal verlinken
    soup = BeautifulSoup(html, "html.parser")
    n_img = 0
    for i, img in enumerate(soup.find_all("img")):
        src = img.get("data-fullres-src") or img.get("src")
        if not src or not src.startswith("https://graph.microsoft.com"):
            continue
        ext = (img.get("data-fullres-src-type") or img.get("data-src-type") or "image/png").split("/")[-1]
        local = folder / f"{stem}_img{i}.{ext}"
        try:
            local.write_bytes(g.get(src).content)
            img["src"] = local.name
            n_img += 1
        except requests.HTTPError as e:
            print(f"    Bild {i} nicht ladbar: {e}", flush=True)

    (folder / f"{stem}.html").write_text(str(soup), encoding="utf-8")
    header = (f"# {page.get('title') or 'ohne Titel'}\n\n"
              f"_erstellt {page.get('createdDateTime')}, geaendert "
              f"{page.get('lastModifiedDateTime')}_\n\n")
    (folder / f"{stem}.md").write_text(header + html_to_text(str(soup)), encoding="utf-8")
    return n_img


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="nur Notizbuecher auflisten")
    ap.add_argument("--notebook", action="append",
                    help="nur dieses Notizbuch (mehrfach moeglich, Teilstring, ohne Gross/Klein)")
    args = ap.parse_args(argv)

    g = Graph(get_token(load_onenote_config()))
    notebooks = g.list("/me/onenote/notebooks")
    if args.list:
        for nb in notebooks:
            print(f"- {nb['displayName']}  (geaendert {nb.get('lastModifiedDateTime')})")
        return 0
    if args.notebook:
        wanted = [w.lower() for w in args.notebook]
        notebooks = [nb for nb in notebooks if any(w in nb["displayName"].lower() for w in wanted)]
        if not notebooks:
            print("Kein passendes Notizbuch -- erst mit --list pruefen.", file=sys.stderr)
            return 1

    manifest = load_json(MANIFEST, {})
    stats = {"neu/geaendert": 0, "unveraendert": 0, "bilder": 0, "fehler": 0}
    for nb in notebooks:
        print(f"Notizbuch: {nb['displayName']}", flush=True)
        for path, sec in iter_sections(g, f"/me/onenote/notebooks/{nb['id']}", (nb["displayName"],)):
            folder = OUT_DIR.joinpath(*[safe_name(p) for p in path])
            pages = g.list(f"/me/onenote/sections/{sec['id']}/pages"
                           "?$select=id,title,createdDateTime,lastModifiedDateTime&$top=100")
            print(f"  {' / '.join(path[1:])}: {len(pages)} Seiten", flush=True)
            for page in pages:
                if manifest.get(page["id"], {}).get("modified") == page.get("lastModifiedDateTime"):
                    stats["unveraendert"] += 1
                    continue
                try:
                    stats["bilder"] += save_page(g, page, folder)
                    manifest[page["id"]] = {"modified": page.get("lastModifiedDateTime"),
                                            "path": "/".join(path), "title": page.get("title")}
                    stats["neu/geaendert"] += 1
                    save_json(MANIFEST, manifest)  # nach jeder Seite: Abbruch verliert nichts
                except requests.HTTPError as e:
                    stats["fehler"] += 1
                    print(f"    FEHLER bei '{page.get('title')}': {e}", flush=True)
    print("Fertig:", ", ".join(f"{k} {v}" for k, v in stats.items()))
    return 1 if stats["fehler"] else 0


if __name__ == "__main__":
    sys.exit(main())
