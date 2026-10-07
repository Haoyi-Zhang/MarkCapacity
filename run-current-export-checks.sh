#!/usr/bin/env bash
# Full current source-export checks; does not replace scientific reproduction.
set -euo pipefail
ARTIFACT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${TOPLAS19_PROJECT_ROOT:-$(cd "$ARTIFACT_DIR/.." && pwd)}"
cd "$ARTIFACT_DIR"
export PYTHONDONTWRITEBYTECODE=1
python3 -B current_export.py --root "$PROJECT_ROOT"
python3 -B -m unittest discover -s regressions -p test_current_export.py -v
./run-package-checks.sh
printf '%s\n' 'CURRENT_EXPORT_CHECKS: 8 package + 6 role regressions; scientific reproduction is separate'
