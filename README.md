<h1 align="center">Hermes Backup</h1>

<p align="center"><strong>Vollständige, lokale Hermes-Backups in einen externen Ordner. Keine Uploads, kein GitHub.</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/Lizenz-AGPL--3.0%20%2B%20Kommerziell-red" alt="Lizenz" />
  <img src="https://img.shields.io/badge/Nur%20f%C3%BCr-Hermes%20Desktop-red" alt="Nur für Hermes" />
  <a href="https://aiianer.de"><img src="https://img.shields.io/badge/Community-AIIANER-black" alt="AIIANER Community" /></a>
</p>

---

## Was ist das?

Hermes Backup (V1) sichert deine komplette Hermes-Installation in einen
externen, lokalen Ordner. Der Runner ruft dafür ausschließlich den
offiziellen `hermes backup`-Befehl per argv auf, veröffentlicht ZIPs atomar
und kann optional eigene Archive im Ziel-Root begrenzt aufbewahren. V1 lädt
nichts hoch, verändert keine globalen Hermes-Einstellungen und spielt
Backups nicht automatisch zurück.

**Teil des AIIANER-Ökosystems:** Bei [AIIANER](https://aiianer.de) bauen wir
ein KI-Betriebssystem, das [Hermes Desktop](https://github.com/NousResearch/hermes-agent)
als Grundlage nutzt. Hermes selbst ist ein Open-Source-Projekt von
**Nous Research** — dieses Plugin ist eine unabhängige Community-Erweiterung
dafür und steht in keiner offiziellen Verbindung zu Nous Research.

## Features

- **Lokal, extern, sicher** — Zielordner liegt außerhalb von `HERMES_HOME`
  (dorthin lässt sich absichtlich nicht sichern), im Ordner-Browser wählbar
  oder als absoluter Pfad (praktisch für NAS/USB)
- **Zeitplan direkt in der Seitenleiste** — aus, täglich oder wöchentlich,
  jeweils mit Uhrzeit und, bei wöchentlichen Läufen, Wochentag; erst nach
  „Speicherort & Plan sichern" legt das Plugin den Hermes-Cron-Zeitplan an
- **Bestätigte Wiederherstellung** — Restore ist ein expliziter,
  zweistufiger Vorgang mit serverseitigem Bestätigungs-Token; ohne exakt
  eingetippten Bestätigungssatz und Checkbox passiert nichts
- **Nur Datei-Verlust-Schutz, kein Rollback-Ersatz** — Deinstallation
  entfernt nur den lokalen Runner und Zeitplan; externe Archive und die
  Laufhistorie bleiben erhalten

## Setup

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

**Wichtig, zwei Schalter:** Dieses Plugin ist ein „unified package" (Python-
Backend + Desktop-Oberfläche in einem Ordner). Beide Hälften sind
standardmäßig **aus**, unabhängig voneinander:

1. **Desktop-Hälfte**: Hermes Desktop → Einstellungen → Plugins →
   „Hermes Backup" einschalten.
2. **Python-Hälfte**: `hermes-backup` in `plugins.enabled` in
   `~/.hermes/config.yaml` eintragen (der Installer erinnert dich daran).

Erst wenn beide an sind, erscheint „Backups" in der Seitenleiste und die
API dahinter antwortet. Danach im Ordner-Browser einen Zielordner wählen —
ohne Zielordner läuft keine automatische Sicherung.

## Deployment

Läuft überall dort, wo Hermes Desktop oder die Hermes-CLI lokal installiert
sind — direkt in deine lokale Hermes-Installation kopiert, ein eigener
Server ist nicht nötig. Details: [docs/DEPLOY.md](docs/DEPLOY.md).

> 🎓 **Schritt-für-Schritt-Tutorials, Setups und Support** gibt es exklusiv in der
> [AIIANER Community](https://aiianer.de).

## Status

Dieses Plugin war zuvor Teil von `aiianer-hermes-extensions` (dort als
`aiianer-backup`, mit UI und Backend eingebettet im Marktplatz-Hub selbst)
und wird ab sofort als eigenständiges, vollständiges Plugin geführt und
gepflegt — Backend-Routen und Oberfläche laufen jetzt komplett in diesem
Repo, nicht mehr im Hub.

Offen: Backup **beim Schließen von Hermes** ist noch nicht auswählbar —
dafür braucht es einen verlässlichen App-Shutdown-Hook, damit ein
laufendes ZIP nicht abgebrochen wird.

---

## 🌍 Das AIIANER-Universum

| | |
| --- | --- |
| 🏠 **Community** | [aiianer.de](https://aiianer.de) — Kurse, Labs, Tutorials, KI-Coaches |
| 📺 **YouTube** | [youtube.com/@aiianer](https://www.youtube.com/@aiianer) — Tools, Tests, Deep-Dives |

## Lizenz

Dual lizenziert: **AGPL-3.0** (privat, Selbsthoster, Forschung) oder
**Kommerzielle Lizenz** (geschlossene Produkte/Dienste, keine Offenlegung).
Details: [LICENSING.md](LICENSING.md). Anfragen über die
[AIIANER Community](https://aiianer.de) oder **support@aiianer.de**.

## Sicherheit

Sicherheitslücken bitte **nicht** als öffentliches Issue melden.
Siehe [SECURITY.md](SECURITY.md).

## Marken

„AIIANER" ist ein Kennzeichen von Oliver Hees aka Aiianer. Die Lizenz des
Quellcodes gewährt **keine** Rechte an diesem Namen oder Logo. Forks müssen
unter eigenem Namen auftreten.

„Hermes" ist ein Open-Source-Projekt von **Nous Research**
([github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)).
Dieses Plugin ist ein unabhängiges Community-Projekt und steht in keiner
offiziellen Verbindung zu Nous Research.

---

<p align="center">
  © 2026 <strong>Oliver Hees aka Aiianer</strong> ·
  <a href="https://aiianer.de">aiianer.de</a> ·
  Made with 🖤 im AIIANER-Universum
</p>
