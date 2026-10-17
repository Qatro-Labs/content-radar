#!/usr/bin/env bash
# Programa scripts/collect.sh cada 2 h con launchd (macOS).
#
#   scripts/schedule-local.sh install     # instala y arranca
#   scripts/schedule-local.sh uninstall   # lo quita
#   scripts/schedule-local.sh status
#
# Si el Mac está dormido a la hora programada, launchd lo ejecuta al despertar.
# Requiere Docker con la DB levantada (docker compose up -d).
set -euo pipefail

LABEL="com.qatrolabs.content-radar.collect"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-7200}"

case "${1:-}" in
  install)
    mkdir -p "$HOME/Library/LaunchAgents" "$REPO_DIR/backend/logs"
    cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$REPO_DIR/scripts/collect.sh</string></array>
  <key>StartInterval</key><integer>$INTERVAL_SECONDS</integer>
  <key>StandardOutPath</key><string>$REPO_DIR/backend/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>$REPO_DIR/backend/logs/launchd.log</string>
</dict>
</plist>
EOF
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "✓ instalado: collect cada $((INTERVAL_SECONDS / 60)) min · logs en backend/logs/collect.log"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✓ desinstalado"
    ;;
  status)
    launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|last exit|run interval" \
      || echo "no instalado"
    ;;
  *)
    echo "uso: $0 install|uninstall|status" >&2
    exit 1
    ;;
esac
