#!/usr/bin/env bash
# Self-contained scientific reproduction entry point.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if ! python3 -m unittest tests.test_woc tests.test_witness_boundaries -v \
    > "$tmp/tests.stdout" 2> "$tmp/tests.stderr"; then
  cat "$tmp/tests.stdout"
  cat "$tmp/tests.stderr" >&2
  exit 1
fi

# Remove the nondeterministic wall-clock duration before freezing the transcript.
sed -E 's/^Ran ([0-9]+) tests in [0-9.]+s$/Ran \1 tests/' \
  "$tmp/tests.stderr" > "$tmp/tests.normalized.stderr"
{
  cat "$tmp/tests.normalized.stderr"
  printf '%s\n' 'DETERMINISTIC_SCIENTIFIC_REEXECUTION: PASS'
} > raw/run_stderr.txt

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
cat raw/run_stderr.txt >&2
