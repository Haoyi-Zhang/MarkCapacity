#!/usr/bin/env bash
# Full current source-export checks; does not replace scientific reproduction.
set -euo pipefail
ARTIFACT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${TOPLAS19_PROJECT_ROOT:-$(cd "$ARTIFACT_DIR/.." && pwd)}"
cd "$ARTIFACT_DIR"
export PYTHONDONTWRITEBYTECODE=1
arguments=(--root "$PROJECT_ROOT" --run-checks)
if [[ -n "${TOPLAS19_EXPORT_ARCHIVE:-}" ]]; then
  arguments+=(--archive "$TOPLAS19_EXPORT_ARCHIVE")
fi
python3 -B current_export.py "${arguments[@]}"
printf '%s\n' 'CURRENT_EXPORT_CHECKS: 8 package + 7 export regressions; scientific reproduction is separate'
