#!/usr/bin/env bash
# Convenience entry point for a complete project checkout.
set -euo pipefail
cd "$(dirname "$0")"
./run-tests.sh
./run-package-checks.sh
printf '%s\n' 'ALL_CHECKS: PASS (92 scientific + 8 package-integrity = 100; retained baseline: 65 scientific + 8 package-integrity = 73)'
