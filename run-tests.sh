#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

python3 -m unittest discover -s tests -p 'test_*.py' -v \
  > "$tmp/tests.stdout" 2> "$tmp/tests.stderr"

python3 src/run_all.py > "$tmp/run1.stdout"
cp raw/results.json "$tmp/results1.json"
cp raw/run_manifest.json "$tmp/manifest1.json"
cp generated/capacity_table.csv "$tmp/capacity1.csv"

python3 src/run_all.py > "$tmp/run2.stdout"
cmp -s "$tmp/run1.stdout" "$tmp/run2.stdout"
cmp -s "$tmp/results1.json" raw/results.json
cmp -s "$tmp/manifest1.json" raw/run_manifest.json
cmp -s "$tmp/capacity1.csv" generated/capacity_table.csv
cmp -s "$tmp/run2.stdout" raw/run_stdout.txt
sha256sum -c raw/SHA256SUMS >/dev/null

cat "$tmp/tests.stdout"
cat "$tmp/run2.stdout"
cat "$tmp/tests.stderr" >&2
printf '%s\n' 'DETERMINISTIC_REEXECUTION: PASS' >&2
