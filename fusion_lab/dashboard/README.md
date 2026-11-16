# Trading Cockpit: Cloudflare (eingerichtet 16.11.2026)

**Adresse:** https://next-level-journal.pages.dev (Login per E-Mail-Code, Cloudflare Access)

Das Dashboard ist eine statische Seite. Nach jedem Screener-Lauf baut der PC sie neu und lädt sie über die
Pages-Direct-Upload-API hoch (`fusion_lab/dashboard/deploy.py`, reines Python). Der PC muss nur zur Rechenzeit
an sein; ansehen geht jederzeit, auch am Handy.

## Wie es eingerichtet ist

- **Pages-Projekt** `next-level-journal` (Direct Upload, kein Git). Konto-ID steht in `secrets.toml`.
- **Zero Trust Free** (0 $, bis 50 Nutzer; Zahlungsmethode nur zur Prüfung hinterlegt).
- **Access-Anwendung** `next-level-journal`, Ziele `next-level-journal.pages.dev` und
  `*.next-level-journal.pages.dev` (Vorschau-Adressen), Regel **„Nur Ich“** (Allow, nur die eigene E-Mail).
- **Token** „Cockpit Upload“, nur Recht *Account → Cloudflare Pages → Edit*, in `.streamlit/secrets.toml`:

```toml
[cloudflare]
api_token = "..."
account_id = "..."
project = "next-level-journal"
url = "https://next-level-journal.pages.dev"
```

## Bewusst nicht gemacht

- **Eigene Domain** `andre-gierhold.de`: nicht auf Cloudflare umgestellt. Strato schaltet bei eigenen
  Nameservern die Strato-E-Mail ab, und die wird genutzt. Die angefangene Domain-Einrichtung bei Cloudflare
  ist ungenutzt („pending“).
- **wrangler**: läuft auf Windows-ARM64 nicht (`workerd` „Unsupported platform: win32 arm64“). Deshalb
  eigener Upload über die API.

## Weitere Bereiche (Journal, persönliches Dashboard)

Kommen als eigene Bereiche in dieselbe App und liegen damit automatisch hinter demselben Login. Für
Schreibzugriff (Journal): Pages Functions + D1 im selben Projekt.

## Am Handy (Android)

Seite in Chrome öffnen, anmelden, Menü ⋮ → **„Zum Startbildschirm hinzufügen“**.

## Prüfen

`python -m fusion_lab.dashboard` → „Hochgeladen … Deployment …“. Ohne Login muss jede Adresse auf
`…cloudflareaccess.com` umleiten (HTTP 302).
