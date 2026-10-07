# Executable artifact

## Self-contained scientific reproduction

Run:

```sh
./run-tests.sh
```

This is the independent-code-package entry point. It runs the retained 65 scientific tests, including the directed-source support and finite-index boundary regressions, plus six current coloring/source-binding regressions in a separate mandatory stage, and regenerates the finite scientific outputs twice in separate directories. It compares both runs with each other **and with the retained results, table, and 65-test normalized transcript**; fresh source manifests must match the separate `current-source-manifest.json`. The original `raw/run_manifest.json` remains bound to the archived source. It checks `raw/SHA256SUMS` before and after without rewriting retained evidence. It requires Python 3.10 or newer with only the standard library, Bash, and GNU core utilities (`mktemp`, `sed`, `cmp`, `sha256sum`, and `timeout`). Each Python command is limited to 180 seconds. It does **not** read the parent `paper/` directory and does not invoke PDF tools.

Raw attempts are retained in temporary directories, whose paths are printed. Set `WOC_CHECK_OUTPUT` to choose their parent. To regenerate outputs directly without replacing the archive, use `python3 -B src/run_all.py --out /path/to/separate-output`. JSON, text records, and checksum manifests use UTF-8 with LF newlines on all hosts; the CSV writer uses its explicit standard CSV line endings. The source manifest binds the three scientific driver files, not a runtime or performance measurement.

The scientific tests cover 1,943 refinement instances, 11,423 general partition instances, 38,564 source-dependent access instances, and 54 correlated list-recovery instances. Constructive checks include 128 exhaustive and 192 deterministic generated witness cases. A separate 240-instance unfiltered stress set ranges over three to five programs and compares the optimized classifications against direct program-level oracles.

The input contract is explicit. Every declared source must have an access row; directed instances require both a preservation row and an access row. A missing row is malformed input and raises `ValueError`. An explicitly supplied empty row is different: it is a valid empty constraint and makes every nonempty exact message alphabet infeasible. The boundary tests cover empty support, a missing row, a one-source empty row, and a one-source identity row.

The retained Linux workflow in `results/current/` passed all 65 tests without skips.
Both complete regenerations match each other and the retained JSON, source
manifest, capacity table and normalized test transcript byte-for-byte. These
are finite scientific checks, not new runtime-performance measurements.

The exact coloring search rechecks only edges incident to the vertex just
assigned. Every parent reached by the search has viable constraints; edges not
incident to that vertex are unchanged, and failed descendants restore their
assignments. Vertex degree order, ascending color order, and the complete leaf
check are unchanged. `tests/test_incident_pruning.py` uses full-assignment
enumeration (not incremental pruning) and a separate program-label oracle to
check first colorings and per-source witnesses, including empty constraints,
isolated vertices, duplicate inputs, iterator inputs, and validation boundaries.
Its source-binding check also verifies every archived checksum. These are
bounded correctness checks, not a measured speedup or a real-program guarantee.

## Full-project integrity checks

From this `artifact/` directory in a complete project checkout, run:

```sh
./run-package-checks.sh
```

This entry point runs 8 package-integrity tests. It requires the sibling `paper/` tree, its retained `paper/provenance/` records, the historical `artifact/project-manifest.json`, and the separate current `current-project-manifest.json`, `current-package-metadata.json`, and `paper/current-statement-locations.json`. The current manifest checks the exact current public file set, bytes, digests and actual distribution modes; it does not overwrite archived experiment bindings. Current source/PDF locations and counts are checked separately from dated audits. A host that cannot preserve the required modes cannot satisfy whole-package acceptance; there is no platform bypass. It also requires Poppler's `pdfinfo` and `pdftotext`; the script checks and reports these dependencies before running any tests. Missing assets or commands cause an explicit input/dependency error and are never converted into a scientific infeasibility result.

To run both entry points in a complete checkout:

```sh
./run-all-checks.sh
```

The combined entry point schedules 79 checks: 71 scientific (65 retained plus six current regressions) and 8 package-integrity checks. The historical baseline remains 73 checks. The two suites are reported separately because only the scientific suite is self-contained. The package checks also bind the paper build and historical audit records; they are not a substitute for the finite scientific checks.

`reference-audit-final.csv`, `citation_support.csv`, and `literature-evidence/` record bibliography status, exact entry hashes, local citation contexts, and the scope of external verification. `code-quality-audit.json`, `anti-overfitting-audit.json`, `results_manifest.csv`, and `reproduction-report.json` retain the earlier host/build measurements and source bindings (including the 56-test scientific suite and dated 2026-09-26 audits); they are historical records, not measurements of the current source. The retained finite results and archived source binding are `raw/results.json` and `raw/run_manifest.json`; the expected current source binding is `current-source-manifest.json`. The checker does not prove contextual equivalence, infer a real compiler's exact image, or replace the paper's arbitrary-set proofs.

The prepared `scientific-checks.yml` workflow runs from this directory as a flat artifact-repository root on Ubuntu 24.04 for pushes to `main` or manual dispatch. It retains failed outputs, applies a 600-second whole-run limit plus resource limits, and preserves failure exit codes. A local run is not an execution of that workflow.

## Current source-export checks

For a complete source export, run `./run-current-export-checks.sh`. It validates
the exact current inventory and actual modes, runs six in-memory role regressions,
and then runs all eight existing package checks with their unchanged Poppler
requirements. Scientific reproduction remains separate; the historical and
current 73/79-check entry points are not replaced. Scientific CI also explicitly
runs the six role regressions in a separate retained log, without requiring the
paper tree. That step does not establish full-export acceptance.

The only bibliography exception is `paper/main.bbl`, bound to its exact bytes,
the active manuscript inclusion/style, current bibliography and all 68 keys.
Arbitrary `.bbl`, `.aux`, `.blg`, missing/extra files, incorrect hashes and actual
mode mismatches remain errors. Windows mode support is an export-environment
condition, not an algorithm defect or an excuse to waive the gate.

`current-export-supplement.json` binds current metadata and identifies the
8-package/6-regression schedule. The exact current manifest includes this
supplement, its metadata and validator; only the manifest itself is excluded
to avoid self-reference. Historical manifests, experiment receipts and their
source hashes are retained unchanged.

The matching unmodified ACM 2.19 `.dtx`/`.ins` and complete original source
snapshot accompany the unchanged class. See `../paper/ACM-SOURCE-NOTICE.md` for
the CTAN release authority, original copyright/LPPL notices and exact derived
class comparison. This source packaging does not assert current portal policy
or decide whether the scientific artifact or full paper should be published.
