#!/usr/bin/env bash
# Full-project integrity entry point. Requires the paper tree and Poppler tools.
set -euo pipefail
ARTIFACT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${TOPLAS19_PROJECT_ROOT:-$(cd "$ARTIFACT_DIR/.." && pwd)}"
cd "$ARTIFACT_DIR"
export PYTHONDONTWRITEBYTECODE=1

required_paths=(
  "$PROJECT_ROOT/paper/main.tex"
  "$PROJECT_ROOT/paper/main.pdf"
  "$PROJECT_ROOT/paper/references.bib"
  "$PROJECT_ROOT/paper/statement_location_audit.json"
  "$PROJECT_ROOT/paper/provenance/CURRENT-STATE.md"
  "$PROJECT_ROOT/paper/provenance/research-plan.md"
  "$PROJECT_ROOT/artifact/project-manifest.json"
  "$PROJECT_ROOT/artifact/current-project-manifest.json"
  "$PROJECT_ROOT/artifact/current-package-metadata.json"
  "$PROJECT_ROOT/paper/current-statement-locations.json"
)
missing=()
for path in "${required_paths[@]}"; do
  [[ -f "$path" ]] || missing+=("$path")
done
if ((${#missing[@]})); then
  printf '%s\n' 'PACKAGE_CHECK_INPUT_ERROR: the full TOPLAS-19 project tree is required.' >&2
  printf 'Missing: %s\n' "${missing[@]}" >&2
  printf '%s\n' 'Run ./run-tests.sh instead for the self-contained scientific checks.' >&2
  exit 2
fi

for command in pdfinfo pdftotext; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'PACKAGE_CHECK_DEPENDENCY_ERROR: required command not found: %s\n' "$command" >&2
    printf '%s\n' 'Install Poppler command-line tools, then rerun this entry point.' >&2
    exit 2
  fi
done

python3 -m unittest tests.test_package_integrity -v
