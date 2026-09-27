# Deployment & Betrieb

## Standard-Installation (Hermes Desktop, lokal)

Ein Befehl, kein `git` nötig:

```bash
curl -sL https://raw.githubusercontent.com/oliverhees/hermes-backup-plugin/main/install.sh | bash
```

Oder klassisch per Clone (praktisch für Updates via `git pull`):

```bash
git clone https://github.com/oliverhees/hermes-backup-plugin.git
cd hermes-backup-plugin
./install.sh
```

Der Installer legt zwei Dinge an:

1. Das eigentliche Plugin unter `$HERMES_HOME/plugins/hermes-backup/`
   (`plugin.yaml`, `dashboard/plugin_api.py`, `desktop/plugin.js`) — das
   „unified package" nach Hermes' Desktop-Plugin-SDK.
2. Den Cron-Runner unter `$HERMES_HOME/scripts/aiianer-backup-runner.py`
   sowie eine leere Ausgangs-Statusdatei unter
   `$HERMES_HOME/aiianer/backup-state.json`.

### Zwei Schalter, beide standardmäßig aus

- **Desktop-Hälfte**: Hermes Desktop → Einstellungen → Plugins →
  „Hermes Backup" einschalten.
- **Python-Hälfte**: `hermes-backup` in `plugins.enabled` in
  `$HERMES_HOME/config.yaml` eintragen, sonst importiert der Gateway
  `dashboard/plugin_api.py` nicht und die Oberfläche bekommt nur Fehler
  von `ctx.rest(...)` zurück.

Beide Schalter zusammen: „Backups" erscheint in der Seitenleiste, die
Backend-Routen antworten unter `/api/plugins/hermes-backup/`.

## Routen

| Methode | Pfad | Zweck |
| --- | --- | --- |
| GET | `/api/plugins/hermes-backup/status` | Aktueller Status |
| GET | `/api/plugins/hermes-backup/config` | Wie `/status`, für die Ersteinrichtung |
| PUT | `/api/plugins/hermes-backup/settings` | Zielordner, Zeitplan, Aufbewahrung speichern |
| POST | `/api/plugins/hermes-backup/browse` | Ordner-Browser (server-seitig, innerhalb `HERMES_HOME` gesperrt) |
| GET | `/api/plugins/hermes-backup/archives` | Liste der vorhandenen Archive im Zielordner |
| POST | `/api/plugins/hermes-backup/run` | Backup sofort auslösen |
| POST | `/api/plugins/hermes-backup/restore/prepare` | Schritt 1 der Wiederherstellung: Token + Bestätigungstext anfordern |
| POST | `/api/plugins/hermes-backup/restore/confirm` | Schritt 2: mit exaktem Token/Text bestätigen, führt `hermes import --force` aus |

## Updates

```bash
cd hermes-backup-plugin
git pull
./install.sh
```

Hermes Desktop danach neu starten.

## Troubleshooting

| Symptom | Erste Anlaufstelle |
| --- | --- |
| „Backups" erscheint nicht in der Seitenleiste | Desktop-Hälfte in Settings → Plugins eingeschaltet? |
| API-Aufrufe liefern Fehler, obwohl die Seite lädt | Python-Hälfte in `plugins.enabled` in `config.yaml` eingetragen? Gateway neu gestartet? |
| „TARGET_INSIDE_HERMES_HOME" | Zielordner darf nicht innerhalb von `HERMES_HOME` liegen — bewusste Sperre |
| Wiederherstellung lässt sich nicht bestätigen | Bestätigungssatz muss exakt (inklusive Archivname) eingetippt werden, Checkbox muss gesetzt sein |
