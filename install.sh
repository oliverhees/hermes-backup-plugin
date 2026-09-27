#!/usr/bin/env bash
# Installiert Hermes Backup in eine lokale Hermes-Installation.
#
#   ./install.sh    Plugin installieren/aktualisieren
#
# Idempotent: mehrfaches Ausfuehren ist sicher. Update-Flow:
#   git pull && ./install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd)"
HERMES_HOME_DIR="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_LIVE="$HERMES_HOME_DIR/plugins/hermes-backup"

# --- Remote-Bootstrap: laeuft das Skript ausserhalb eines Repo-Clones ------
# (z. B. via `curl -sL .../install.sh | bash`), laedt es sich das Repo als
# Tarball in ein Temp-Verzeichnis und fuehrt das dortige install.sh aus.
if [ ! -f "$REPO_DIR/scripts/backup_runner.py" ]; then
  echo "Kein lokaler Repo-Clone gefunden - lade das Plugin von GitHub ..."
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  TARBALL_URL="https://github.com/oliverhees/hermes-backup-plugin/archive/refs/heads/main.tar.gz"
  if command -v curl >/dev/null 2>&1; then
    curl -sL "$TARBALL_URL" | tar -xz -C "$TMP_DIR"
  else
    wget -qO- "$TARBALL_URL" | tar -xz -C "$TMP_DIR"
  fi
  INNER="$(find "$TMP_DIR" -maxdepth 2 -name install.sh | head -1)"
  if [ -z "$INNER" ]; then
    echo "FEHLER: Download fehlgeschlagen." >&2
    exit 1
  fi
  chmod +x "$INNER"
  exec bash "$INNER" "$@"
fi

if [ ! -d "$HERMES_HOME_DIR" ]; then
  echo "FEHLER: $HERMES_HOME_DIR existiert nicht. Ist Hermes installiert?" >&2
  exit 1
fi

echo "Installiere Hermes Backup nach $PLUGIN_LIVE ..."
mkdir -p "$PLUGIN_LIVE/dashboard" "$PLUGIN_LIVE/desktop" "$HERMES_HOME_DIR/scripts" "$HERMES_HOME_DIR/aiianer"

# Agent-Halfte: plugin.yaml + Backend-Route.
cp "$REPO_DIR/plugin.yaml" "$PLUGIN_LIVE/plugin.yaml"
cp "$REPO_DIR/dashboard/manifest.json" "$PLUGIN_LIVE/dashboard/manifest.json"
cp "$REPO_DIR/dashboard/plugin_api.py" "$PLUGIN_LIVE/dashboard/plugin_api.py"
rm -rf "$PLUGIN_LIVE/dashboard/__pycache__"

# Desktop-Halfte: eigenstaendige Seite, opt-in wie jedes unified package
# (Settings -> Plugins zeigt sie an, bleibt aber aus, bis du sie einschaltest).
cp "$REPO_DIR/desktop/plugin.js" "$PLUGIN_LIVE/desktop/plugin.js"

# Der eigentliche Backup-Runner, von Cron aufgerufen.
install -m 0755 "$REPO_DIR/scripts/backup_runner.py" "$HERMES_HOME_DIR/scripts/aiianer-backup-runner.py"

if [ ! -e "$HERMES_HOME_DIR/aiianer/backup-state.json" ]; then
  umask 077
  printf '%s\n' '{"schemaVersion":1,"enabled":false,"target_dir":"","schedule":"manual","retention":{"enabled":false,"keep":5},"state":"never_run","lastRun":null,"lastArchive":null,"lastErrorCode":null}' > "$HERMES_HOME_DIR/aiianer/backup-state.json"
fi

echo ""
echo "Fertig. Naechste Schritte:"
echo "  1. In Hermes Desktop: Einstellungen -> Plugins -> 'Hermes Backup' aktivieren (Desktop-Halfte, standardmaessig aus)"
echo "  2. Python-Halfte in $HERMES_HOME_DIR/config.yaml unter plugins.enabled eintragen: hermes-backup"
echo "  3. Hermes komplett neu starten"
echo "  4. Im 'Backups'-Eintrag der Seitenleiste den Zielordner festlegen"
