# Trading Cockpit: Einrichtung Cloudflare (einmalig, ca. 1 Stunde)

Das Dashboard ist eine statische Seite. Der PC baut sie nach jedem Screener-Lauf und lädt sie zu Cloudflare
Pages hoch. Cloudflare Access schützt sie mit einem Login (Code per E-Mail). Der PC muss nur zur Rechenzeit
an sein; ansehen geht jederzeit, auch am Handy. Kostenlos (Pages + Access bis 50 Nutzer).

Bis die Schritte erledigt sind, läuft alles lokal: `fusion_lab/data/dashboard_dist/index.html`.
Zum lokalen Ansehen: `python -m http.server 8765 -d fusion_lab/data/dashboard_dist`, dann
http://127.0.0.1:8765 öffnen.

## 1. Domain zu Cloudflare (ca. 15 Min. + Wartezeit)

1. Konto auf https://dash.cloudflare.com anlegen (kostenlos).
2. „Add a domain“ → deine Domain eingeben → Plan **Free**.
3. Cloudflare zeigt zwei Nameserver an. Beim Domain-Anbieter die Nameserver auf diese zwei ändern.
4. Warten, bis Cloudflare „Active“ meldet (Minuten bis einige Stunden).

## 2. Pages-Projekt anlegen

1. Workers & Pages → Create → **Pages** → „Upload assets“ (Direct Upload).
2. Projektname z. B. `trading-cockpit`. Einen beliebigen Ordner hochladen, z. B.
   `fusion_lab/data/dashboard_dist` (wird später automatisch ersetzt).
3. Im Projekt → Custom domains → z. B. `cockpit.<deine-domain>` hinzufügen.

## 3. Zugang schützen (Cloudflare Access)

1. Zero Trust (linkes Menü) → beim ersten Mal ein Team-Namen wählen, Plan **Free**.
2. Access → Applications → Add → **Self-hosted**.
3. Domain: `cockpit.<deine-domain>` **und** `trading-cockpit.pages.dev` (beide Adressen schützen,
   sonst ist die pages.dev-Adresse offen).
4. Policy: Action **Allow**, Include → **Emails** → deine E-Mail-Adresse.
5. Login-Methode: „One-time PIN“ (Code per E-Mail) ist voreingestellt. Optional Google-Login.
6. Session-Dauer z. B. 1 Monat, damit du dich am Handy nicht ständig neu anmelden musst.

## 4. Token für den automatischen Upload

1. Profil → API Tokens → Create Token → Vorlage **„Edit Cloudflare Workers“** oder eigenes Token mit
   Recht *Account → Cloudflare Pages → Edit*.
2. Account-ID steht rechts unten auf der Übersicht deiner Domain.
3. In `.streamlit/secrets.toml` (git-ignoriert) eintragen:

```toml
[cloudflare]
api_token = "..."
account_id = "..."
project = "trading-cockpit"
url = "https://cockpit.<deine-domain>"
```

4. Test: `python -m fusion_lab.dashboard` → meldet „Hochgeladen“.

## Am Handy (Android)

Seite in Chrome öffnen, anmelden, Menü ⋮ → **„Zum Startbildschirm hinzufügen“**. Startet dann wie eine App.
