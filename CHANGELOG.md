# Changelog

Alle nennenswerten Änderungen an diesem Plugin stehen hier, neueste zuerst.
Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [1.0.0] - 2026-09-27

### Hinzugefügt
- Erste eigenständige Veröffentlichung als `hermes-backup-plugin`. Zuvor
  Teil von `aiianer-hermes-extensions` (`extensions/aiianer-backup` für
  den Runner, Backend-Routen und Oberfläche eingebettet im Marktplatz-Hub
  selbst unter `dashboard/plugin_api.py` und `desktop/plugin.js`).
- Vollständiger Port als „unified package" (`plugin.yaml` + `dashboard/` +
  `desktop/` in einem Ordner): eigene Backend-Routen unter
  `/api/plugins/hermes-backup/`, eigene Seite in der Seitenleiste, statt
  eines Tabs innerhalb des Hubs.
- Alle Sicherheitsprüfungen 1:1 übernommen: Pfad-Traversal-Schutz,
  Sperre für Ziele innerhalb von `HERMES_HOME`, zweistufige
  Wiederherstellungs-Bestätigung mit serverseitigem Token, Archiv-Namens-
  Validierung, ZIP-Gültigkeitsprüfung.
