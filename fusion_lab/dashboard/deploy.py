"""Upload nach Cloudflare Pages ueber wrangler (Node). Zugangsdaten aus .streamlit/secrets.toml, Abschnitt
[cloudflare] (git-ignoriert): api_token, account_id, project, url. Fehlt der Abschnitt -> Upload uebersprungen.
Den Login vor der Seite macht Cloudflare Access (Einrichtung siehe README.md) -- hier werden keine Passwoerter
gespeichert."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from fusion_lab._secrets import _section

WRANGLER = "wrangler@3.114.0"


def config() -> dict | None:
    try:
        return _section("cloudflare", ("api_token", "account_id", "project"))
    except (FileNotFoundError, ValueError):
        return None


def public_url() -> str | None:
    c = config()
    return c.get("url") if c else None


def deploy(dist: Path) -> str:
    c = config()
    if not c:
        return "Upload übersprungen: kein [cloudflare]-Abschnitt in .streamlit/secrets.toml (siehe fusion_lab/dashboard/README.md)"
    npx = shutil.which("npx")
    if not npx:
        return "Upload übersprungen: npx (Node.js) nicht gefunden"
    env = {**os.environ, "CLOUDFLARE_API_TOKEN": c["api_token"], "CLOUDFLARE_ACCOUNT_ID": c["account_id"]}
    res = subprocess.run([npx, "--yes", WRANGLER, "pages", "deploy", str(dist), "--project-name", c["project"],
                          "--branch", "main", "--commit-dirty=true"], env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=600)
    tail = (res.stdout + res.stderr).strip().splitlines()[-3:]
    if res.returncode != 0:
        raise RuntimeError(f"wrangler rc={res.returncode}: {' | '.join(tail)}")
    return f"Hochgeladen: {c.get('url') or c['project']} ({' | '.join(tail)})"
