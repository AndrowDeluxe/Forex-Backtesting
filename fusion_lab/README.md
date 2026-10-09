# fusion_lab — Quant × diskretionäres Trading

Code zum Dachprojekt [`knowledge/projects/quant-diskretionaer-fusion.md`](../knowledge/projects/quant-diskretionaer-fusion.md).
Strikt getrennt von den Live-Bridges (kein Import in beide Richtungen).

| Ordner | Inhalt | Git |
|---|---|---|
| `ingest/` | Strang 0: Material-Import (OneNote, Telegram) | ja |
| `raw/` | importiertes Rohmaterial (private Notizen/Chats) | **nein** |
| `.auth/` | Login-Caches (Microsoft-Token, Telegram-Session) | **nein** |

## Einmalige Einrichtung (machst du, ~15 Min.)

### 0. Pakete

    pip install msal telethon

### 1. OneNote: App in Azure registrieren (kostenlos)

1. <https://entra.microsoft.com> → mit deinem Microsoft-Konto (dem von OneNote) anmelden.
   Falls ein persönliches Konto keinen Zugriff bekommt: <https://portal.azure.com> → „App-Registrierungen“.
2. **Neue Registrierung**: Name `fusion-lab-onenote`,
   Kontotypen: **„Nur persönliche Microsoft-Konten“** → Registrieren.
3. Die **Anwendungs-ID (Client-ID)** kopieren.
4. Links **Authentifizierung** → „Öffentliche Clientflows zulassen“ auf **Ja** → Speichern.
5. Links **API-Berechtigungen** → Microsoft Graph → Delegiert → `Notes.Read` hinzufügen
   (wird beim ersten Login ohnehin abgefragt).

### 2. Telegram-API-Zugang

1. <https://my.telegram.org> → mit deiner Telefonnummer einloggen → **API development tools**.
2. App anlegen (Name egal, z.B. `fusion-lab`) → **api_id** und **api_hash** notieren.
   Wie ein Passwort behandeln.

### 3. In `.streamlit/secrets.toml` eintragen (gitignored)

```toml
[onenote]
client_id = "<Anwendungs-ID aus Schritt 1>"

[telegram]
api_id = 1234567
api_hash = "<api_hash aus Schritt 2>"
chats = []   # nach dem ersten "--list" die IDs der Gruppen eintragen, z.B. [-1001234567890]
```

### 4. Notion (eigene Integration, damit auch geplante Bot-Läufe schreiben können)

1. <https://www.notion.so/profile/integrations> → **Neue Integration**: Name `Trading Fusion`,
   Typ **Intern**, dein Workspace → Speichern → **Internes Integrations-Secret** kopieren.
2. In Notion eine leere Seite **„Trading Fusion Cockpit“** anlegen →
   oben rechts `•••` → **Verbindungen** → `Trading Fusion` hinzufügen.
3. In `.streamlit/secrets.toml`:

```toml
[notion]
token = "<Integrations-Secret, beginnt mit ntn_>"
root_page = "<Link der Seite Trading Fusion Cockpit>"
```

4. `python -m fusion_lab.notion.setup_cockpit --test` legt Übersicht + Datenbanken an.

## Import ausführen (aus dem Repo-Ordner)

    python -m fusion_lab.ingest.onenote --list        # erster Lauf: Login-Code im Browser bestätigen
    python -m fusion_lab.ingest.onenote --notebook "Trading"

    python -m fusion_lab.ingest.telegram --list       # erster Lauf: Telefonnummer + Code eingeben
    python -m fusion_lab.ingest.telegram              # Chats aus secrets.toml

Beide Skripte laufen inkrementell: ein zweiter Lauf lädt nur Neues bzw. Geändertes.
Sie lesen nur, sie senden oder ändern nichts.
