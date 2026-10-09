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
    python -m fusion_lab.ingest.onenote --notebook "Finanzielle Freiheit Neu" --section "Smart Money Trading"
"""

import argparse
import hashlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

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
    def __init__(self, token_fn):
        # token_fn statt fertigem Token: der Access-Token laeuft nach ~1 h ab,
        # bei langen Drossel-Pausen mitten im Lauf (gemessen: 401 nach 429-Serie).
        self.token_fn = token_fn
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token_fn()}"
        # Gemeinsame Pause fuer alle Threads: drosselt Graph einen, warten alle
        # (sonst feuern die anderen weiter und verlaengern die Sperre).
        self._pause_until = 0.0
        self._lock = threading.Lock()

    def get(self, url: str, **kw) -> requests.Response:
        if url.startswith("/"):
            url = GRAPH + url
        for attempt in range(12):
            delay = self._pause_until - time.time()
            if delay > 0:
                time.sleep(delay)
            try:
                r = self.s.get(url, timeout=60, **kw)
            except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
                # Graph setzt bei langen Laeufen gelegentlich die Verbindung
                # zurueck (gemessen: 10054 nach ~1.000 Seiten) -> wiederholen.
                print(f"  Verbindung unterbrochen ({type(e).__name__}), neuer Versuch ...", flush=True)
                time.sleep(min(120, 5 * 2 ** attempt))
                continue
            if r.status_code in (429, 503, 504):
                wait = int(r.headers.get("Retry-After", min(300, 15 * 2 ** attempt)))
                with self._lock:
                    if time.time() + wait > self._pause_until:
                        self._pause_until = time.time() + wait
                        print(f"  Graph drosselt ({r.status_code}), alle warten {wait}s ...", flush=True)
                continue
            if r.status_code == 401 and attempt < 11:
                with self._lock:
                    self.s.headers["Authorization"] = f"Bearer {self.token_fn()}"
                continue
            r.raise_for_status()
            return r
        raise requests.HTTPError(f"{url}: nach 12 Versuchen aufgegeben")

    def list(self, url: str, page_size: int = 100) -> list[dict]:
        """Alle Eintraege einer Liste. Die OneNote-API liefert mit $expand/$select
        oft KEIN @odata.nextLink, sondern bricht still bei $top ab (gemessen:
        exakt 100 von >100 Abschnitten) -- daher selbst per $skip weiterblaettern."""
        sep = "&" if "?" in url else "?"
        items, skip = [], 0
        while True:
            data = self.get(f"{url}{sep}$top={page_size}&$skip={skip}").json()
            batch = data.get("value", [])
            items.extend(batch)
            if len(batch) < page_size:
                return items
            skip += page_size


def walk_group(g: Graph, group_id: str, prefix: tuple[str, ...]):
    """Abschnitte einer Abschnittsgruppe rekursiv; liefert (Pfad, Abschnitt)."""
    base = f"/me/onenote/sectionGroups/{group_id}"
    for sec in g.list(f"{base}/sections"):
        yield prefix + (sec["displayName"],), sec
    for grp in g.list(f"{base}/sectionGroups"):
        yield from walk_group(g, grp["id"], prefix + (grp["displayName"],))


def iter_sections(g: Graph, notebook: dict, wanted: list[str] | None = None):
    """Abschnitte eines Notizbuchs inkl. verschachtelter Abschnittsgruppen;
    liefert (Pfad, Abschnitt).

    Mit `wanted`: nur Abschnitte/Gruppen der OBERSTEN Ebene, deren Name einen
    der Texte enthaelt, und alles darunter -- andere Gruppen werden gar nicht
    erst durchlaufen (spart die Abfragen, die OneNote sonst drosselt).
    Ohne `wanted`: zwei flache Sammelabfragen ueber alle Notizbuecher."""
    if wanted:
        nb_url = f"/me/onenote/notebooks/{notebook['id']}"
        root = (notebook["displayName"],)
        hit = lambda name: any(w in name.lower() for w in wanted)  # noqa: E731
        for sec in g.list(f"{nb_url}/sections"):
            if hit(sec["displayName"]):
                yield root + (sec["displayName"],), sec
        for grp in g.list(f"{nb_url}/sectionGroups"):
            if hit(grp["displayName"]):
                yield from walk_group(g, grp["id"], root + (grp["displayName"],))
        return

    exp = "$expand=parentNotebook,parentSectionGroup"
    groups = {grp["id"]: grp for grp in g.list(f"/me/onenote/sectionGroups?{exp}")}

    def group_path(gid: str) -> tuple[str, ...]:
        grp = groups.get(gid)
        if not grp:
            return ()
        parent = (grp.get("parentSectionGroup") or {}).get("id")
        return group_path(parent) + (grp["displayName"],) if parent else (grp["displayName"],)

    out = []
    for sec in g.list(f"/me/onenote/sections?{exp}"):
        if (sec.get("parentNotebook") or {}).get("id") != notebook["id"]:
            continue
        gid = (sec.get("parentSectionGroup") or {}).get("id")
        out.append(((notebook["displayName"],) + (group_path(gid) if gid else ()) + (sec["displayName"],), sec))
    yield from sorted(out, key=lambda x: x[0])


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


def page_stem(page: dict) -> str:
    """Dateiname je Seite. NICHT das ID-Ende nehmen: OneNote-Seiten-IDs enden
    auf die ID des ABSCHNITTS ("0-<seite>!1-<abschnitt>") -- gleichnamige
    Seiten eines Abschnitts haben sich so gegenseitig ueberschrieben (89 Faelle)."""
    digest = hashlib.sha1(page["id"].encode()).hexdigest()[:10]
    return safe_name(page.get("title") or "ohne Titel") + "__" + digest


def save_page(g: Graph, page: dict, folder) -> int:
    html = g.get(f"/me/onenote/pages/{page['id']}/content",
                 params={"includeIDs": "false"}).text
    stem = page_stem(page)
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
    ap.add_argument("--section", action="append",
                    help="nur Abschnitte/Abschnittsgruppen, deren Name diesen Text enthaelt "
                         "(inkl. aller Unterabschnitte)")
    ap.add_argument("--workers", type=int, default=2, help="parallele Seiten-Downloads")
    args = ap.parse_args(argv)

    cfg = load_onenote_config()
    g = Graph(lambda: get_token(cfg))
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
    lock = threading.Lock()
    sections_wanted = [s.lower() for s in (args.section or [])]

    def fetch(page, folder, path, idx):
        try:
            n_img = save_page(g, page, folder)
        except requests.HTTPError as e:
            with lock:
                stats["fehler"] += 1
            print(f"    FEHLER bei '{page.get('title')}': {e}", flush=True)
            return
        with lock:
            stats["bilder"] += n_img
            stats["neu/geaendert"] += 1
            manifest[page["id"]] = {"modified": page.get("lastModifiedDateTime"),
                                    "path": "/".join(path), "title": page.get("title"),
                                    "order": idx, "level": page.get("level", 0),
                                    "file": page_stem(page)}
            save_json(MANIFEST, manifest)  # nach jeder Seite: Abbruch verliert nichts
            done = stats["neu/geaendert"] + stats["fehler"]
        if done % 25 == 0:
            print(f"    {done} Seiten geladen ...", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for nb in notebooks:
            print(f"Notizbuch: {nb['displayName']}", flush=True)
            for path, sec in iter_sections(g, nb, sections_wanted):
                if sections_wanted and not any(w in p.lower() for w in sections_wanted for p in path[1:]):
                    continue
                folder = OUT_DIR.joinpath(*[safe_name(p) for p in path])
                pages = g.list(f"/me/onenote/sections/{sec['id']}/pages"
                               "?$select=id,title,createdDateTime,lastModifiedDateTime,level,order")
                print(f"  {' / '.join(path[1:])}: {len(pages)} Seiten", flush=True)
                futures = []
                for idx, page in enumerate(pages):
                    if manifest.get(page["id"], {}).get("modified") == page.get("lastModifiedDateTime"):
                        stats["unveraendert"] += 1
                        continue
                    futures.append(pool.submit(fetch, page, folder, path, idx))
                for f in futures:
                    f.result()
    print("Fertig:", ", ".join(f"{k} {v}" for k, v in stats.items()))
    return 1 if stats["fehler"] else 0


if __name__ == "__main__":
    sys.exit(main())
