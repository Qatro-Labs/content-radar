#!/usr/bin/env bash
# Ciclo periódico del Signal Engine: refresca métricas (snapshot) y trae piezas nuevas.
# Lo ejecuta launchd cada 2 h (scripts/schedule-local.sh) o a mano.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO_DIR/backend/logs"
mkdir -p "$LOG_DIR"

# launchd arranca con un PATH mínimo.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

cd "$REPO_DIR/backend"
{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) collect --days ${COLLECT_DAYS:-7}"
  uv run python -m app.jobs.collect --days "${COLLECT_DAYS:-7}"
} >>"$LOG_DIR/collect.log" 2>&1
