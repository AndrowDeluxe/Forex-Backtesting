# Trading Cockpit: Cloudflare (eingerichtet 16.11.2026)

**Adresse:** https://next-level-journal.pages.dev/trading/ (Login per E-Mail-Code, Cloudflare Access)

Seit 16.11.2026 23:00 gehört die Seite dem **Lebensjournal** (`C:\Users\andre\Lebensjournal\`). Dessen Build kopiert
`fusion_lab/dashboard/static/` nach `/trading/`, die Daten liefert eine Pages Function aus Workers KV
(`functions/trading/data/[name].ts`).

Nach jedem Screener-Lauf baut der PC die Daten neu (`python -m fusion_lab.dashboard`) und schreibt **nur die
Daten-Dateien** (`aktien.json`, `krypto.json`, `rohstoffe.json` (seit 18.11.), `makro.json`, `meta.json`) per REST-API in KV
(`deploy.py::deploy_kv`). Die Seite selbst wird dabei nie hochgeladen, sonst wäre das Journal überschrieben.
Änderungen am Cockpit-Code (`static/`) erscheinen erst nach dem nächsten Journal-Build + Deploy.

## Wie es eingerichtet ist

- **Pages-Projekt** `next-level-journal` (Direct Upload, kein Git), Deploy aus dem Journal-Repo.
- **Zero Trust Free** (0 $, bis 50 Nutzer; Zahlungsmethode nur zur Prüfung hinterlegt).
- **Access-Anwendung** `next-level-journal`, Ziele `next-level-journal.pages.dev` und
  `*.next-level-journal.pages.dev`, Regel **„Nur Ich“** (Allow, nur die eigene E-Mail).
- **Token** „Cockpit Upload“, Rechte *Cloudflare Pages: Edit* + *Workers KV Storage: Edit*, in
  `.streamlit/secrets.toml` (git-ignoriert):

```toml
[cloudflare]
api_token = "..."
account_id = "..."
project = "next-level-journal"
url = "https://next-level-journal.pages.dev"
kv_namespace_id = "..."   # gesetzt -> nur KV-Upload; fehlt -> ganze Seite per Direct Upload (alter Modus)
```

## Bewusst nicht gemacht

- **Eigene Domain:** nicht auf Cloudflare umgestellt. Strato schaltet bei eigenen Nameservern die Strato-E-Mail ab,
  und die wird genutzt. Die angefangene Domain-Einrichtung bei Cloudflare ist ungenutzt („pending“).
- **wrangler**: läuft auf Windows-ARM64 nicht (`workerd` „Unsupported platform: win32 arm64“). Deshalb eigener
  Upload über die API.

## Am Handy (Android)

Seite in Chrome öffnen, anmelden, Menü ⋮ → **„Zum Startbildschirm hinzufügen“**.

## Prüfen

`python -m fusion_lab.dashboard` → „KV aktualisiert (aktien.json, …)“. Ohne Login muss jede Adresse auf
`…cloudflareaccess.com` umleiten (HTTP 302). Lokal ansehen: `python -m fusion_lab.dashboard --local`.

## Rohstoffe (seit 18.11.2026)

Der Tab „Rohstoffe“ liest `data/rohstoffe.json` (Tageslauf + neueste Wochen-Tiefenanalyse je Rohstoff). Einmalig im
**Lebensjournal** nötig: Falls `functions/trading/data/[name].ts` erlaubte Namen prüft, `rohstoffe` ergänzen; danach
Journal-Build + Deploy, damit der neue Tab (`static/`) erscheint.

Tasks auf dem PC anlegen (Muster wie `Forex-Screener-Aktien`, StartWhenAvailable):
- `Forex-Screener-Rohstoffe`: Mo–Fr 23:15, `powershell -File scripts\screener_task.ps1 rohstoffe`
- `Forex-Rohstoff-Tiefenanalyse`: So 18:00, `powershell -File scripts\commodity_deep_task.ps1`
