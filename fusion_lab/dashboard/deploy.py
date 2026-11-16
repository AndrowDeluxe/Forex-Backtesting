"""Upload nach Cloudflare Pages ueber die Direct-Upload-API (reines Python, kein wrangler: wrangler/workerd laeuft
nicht auf Windows-ARM64, Befund 16.11.2026).

Zugangsdaten aus .streamlit/secrets.toml, Abschnitt [cloudflare] (git-ignoriert): api_token (Recht
"Cloudflare Pages: Edit"), account_id, project, url. Fehlt der Abschnitt -> Upload uebersprungen.
Den Login vor der Seite macht Cloudflare Access (Zero-Trust-Anwendung "next-level-journal", Regel "Nur Ich") --
hier werden keine Passwoerter gespeichert.

Ablauf wie wrangler: Upload-JWT holen -> fehlende Datei-Hashes abfragen -> nur diese hochladen -> Hashes
bestaetigen -> Deployment mit Manifest anlegen. Schluessel je Datei = 32 Hex-Zeichen aus SHA-256 ueber
Base64-Inhalt + Dateiendung (wrangler nutzt BLAKE3; Cloudflare verwendet den Wert nur als Inhalts-Schluessel).
"""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
from pathlib import Path

import requests

from fusion_lab._secrets import _section

API = "https://api.cloudflare.com/client/v4"
SPECIAL = {"_headers", "_redirects", "_routes.json", "_worker.js"}
BATCH_BYTES = 40 * 1024 * 1024
BATCH_FILES = 1000


def config() -> dict | None:
    try:
        return _section("cloudflare", ("api_token", "account_id", "project"))
    except (FileNotFoundError, ValueError):
        return None


def public_url() -> str | None:
    c = config()
    return c.get("url") if c else None


def _check(r: requests.Response, what: str) -> dict:
    try:
        data = r.json()
    except ValueError:
        raise RuntimeError(f"{what}: HTTP {r.status_code} {r.text[:200]}") from None
    if not r.ok or not data.get("success", False):
        raise RuntimeError(f"{what}: HTTP {r.status_code} {data.get('errors')}")
    return data


def file_key(content: bytes, name: str) -> str:
    ext = Path(name).suffix.lstrip(".")
    return hashlib.sha256(base64.b64encode(content) + ext.encode()).hexdigest()[:32]


def _files(dist: Path) -> dict[str, Path]:
    out = {}
    for p in sorted(dist.rglob("*")):
        if p.is_file() and p.name not in SPECIAL:
            out["/" + p.relative_to(dist).as_posix()] = p
    return out


FEED_FILES = ("aktien.json", "krypto.json", "makro.json", "meta.json")


def deploy_kv(dist: Path, c: dict) -> str:
    """Lebensjournal-Modus (seit 16.11.2026): Die Seite gehoert dem Lebensjournal (C:\\Users\\andre\\Lebensjournal,
    Cockpit unter /trading/, Daten per Pages Function aus Workers KV). Hier nur die vier Daten-Dateien in KV
    schreiben -- NIE die ganze Seite hochladen, sonst waere das Journal ueberschrieben.
    Token braucht zusaetzlich das Recht "Workers KV Storage: Edit"."""
    url = f"{API}/accounts/{c['account_id']}/storage/kv/namespaces/{c['kv_namespace_id']}/values"
    auth = {"Authorization": f"Bearer {c['api_token']}"}
    done = []
    for name in FEED_FILES:
        p = dist / "data" / name
        if not p.exists():
            continue
        _check(requests.put(f"{url}/{name}", headers=auth, files={"value": (None, p.read_bytes()),
                                                                     "metadata": (None, "{}")}, timeout=120),
               f"KV {name}")
        done.append(name)
    return f"KV aktualisiert ({', '.join(done)}) · Lebensjournal unter {c.get('url', '')}/trading/"


def deploy(dist: Path) -> str:
    c = config()
    if not c:
        return "Upload übersprungen: kein vollständiger [cloudflare]-Abschnitt in .streamlit/secrets.toml"
    if c.get("kv_namespace_id"):
        return deploy_kv(dist, c)
    acc, proj = c["account_id"], c["project"]
    auth = {"Authorization": f"Bearer {c['api_token']}"}
    s = requests.Session()

    jwt = _check(s.get(f"{API}/accounts/{acc}/pages/projects/{proj}/upload-token", headers=auth, timeout=60),
                 "upload-token")["result"]["jwt"]
    jh = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}

    files = _files(dist)
    meta = {}
    for path, p in files.items():
        content = p.read_bytes()
        meta[path] = {"key": file_key(content, p.name), "content": content,
                      "type": mimetypes.guess_type(p.name)[0] or "application/octet-stream"}
    keys = sorted({m["key"] for m in meta.values()})
    missing = set(_check(s.post(f"{API}/pages/assets/check-missing", headers=jh, data=json.dumps({"hashes": keys}),
                                timeout=60), "check-missing")["result"])
    todo = [m for m in {m["key"]: m for m in meta.values()}.values() if m["key"] in missing]
    batch, size = [], 0

    def flush():
        nonlocal batch, size
        if batch:
            _check(s.post(f"{API}/pages/assets/upload", headers=jh, data=json.dumps(batch), timeout=300), "upload")
        batch, size = [], 0

    for m in todo:
        b64 = base64.b64encode(m["content"]).decode()
        if batch and (size + len(b64) > BATCH_BYTES or len(batch) >= BATCH_FILES):
            flush()
        batch.append({"key": m["key"], "value": b64, "metadata": {"contentType": m["type"]}, "base64": True})
        size += len(b64)
    flush()
    _check(s.post(f"{API}/pages/assets/upsert-hashes", headers=jh, data=json.dumps({"hashes": keys}), timeout=60),
           "upsert-hashes")

    manifest = {path: m["key"] for path, m in meta.items()}
    form = {"manifest": (None, json.dumps(manifest)), "branch": (None, "main")}
    for special in SPECIAL:
        sp = dist / special
        if sp.exists():
            form[special] = (special, sp.read_bytes(), "application/octet-stream")
    dep = _check(s.post(f"{API}/accounts/{acc}/pages/projects/{proj}/deployments", headers=auth, files=form,
                        timeout=300), "deployment")["result"]
    return (f"Hochgeladen: {c.get('url') or dep.get('url')} · {len(files)} Dateien, {len(todo)} neu · "
            f"Deployment {dep.get('id', '')[:8]}")
