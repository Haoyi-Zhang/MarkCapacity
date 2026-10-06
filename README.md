# Executable artifact

## Self-contained scientific reproduction

Run:

```sh
./run-tests.sh
```

This is the independent-code-package entry point. It runs 65 scientific tests, including the directed-source support and finite-index boundary regressions, and regenerates the finite scientific outputs twice in separate directories. It compares both runs with each other **and with the retained results, source manifest, table, and normalized test transcript**; it checks `raw/SHA256SUMS` before and after without rewriting retained evidence. It requires Python 3.10 or newer with only the standard library, Bash, and GNU core utilities (`mktemp`, `sed`, `cmp`, `sha256sum`, and `timeout`). Each Python command is limited to 180 seconds. It does **not** read the parent `paper/` directory and does not invoke PDF tools.

Raw attempts are retained in temporary directories, whose paths are printed. Set `WOC_CHECK_OUTPUT` to choose their parent. To regenerate outputs directly without replacing the archive, use `python3 -B src/run_all.py --out /path/to/separate-output`. JSON, text records, and checksum manifests use UTF-8 with LF newlines on all hosts; the CSV writer uses its explicit standard CSV line endings. The source manifest binds the three scientific driver files, not a runtime or performance measurement.

The scientific tests cover 1,943 refinement instances, 11,423 general partition instances, 38,564 source-dependent access instances, and 54 correlated list-recovery instances. Constructive checks include 128 exhaustive and 192 deterministic generated witness cases. A separate 240-instance unfiltered stress set ranges over three to five programs and compares the optimized classifications against direct program-level oracles.

The input contract is explicit. Every declared source must have an access row; directed instances require both a preservation row and an access row. A missing row is malformed input and raises `ValueError`. An explicitly supplied empty row is different: it is a valid empty constraint and makes every nonempty exact message alphabet infeasible. The boundary tests cover empty support, a missing row, a one-source empty row, and a one-source identity row.

The Linux workflow in `results/current/` passes all 65 tests without skips.
Both complete regenerations match each other and the retained JSON, source
manifest, capacity table and normalized test transcript byte-for-byte. These
are finite scientific checks, not new runtime-performance measurements.

## Full-project integrity checks

From this `artifact/` directory in a complete project checkout, run:

```sh
./run-package-checks.sh
```

This entry point runs 8 package-integrity tests. It requires the sibling `paper/` tree, its retained `paper/provenance/` records, and `artifact/project-manifest.json`. It also requires Poppler's `pdfinfo` and `pdftotext`; the script checks and reports these dependencies before running any tests. Missing assets or commands cause an explicit input/dependency error and are never converted into a scientific infeasibility result.

To run both entry points in a complete checkout:

```sh
./run-all-checks.sh
```

The combined entry point schedules 73 checks: 65 scientific and 8 package-integrity checks. The two counts are reported separately because only the scientific suite is self-contained. The package checks also bind the paper build and historical audit records; they are not a substitute for the finite scientific checks.

`reference-audit-final.csv`, `citation_support.csv`, and `literature-evidence/` record bibliography status, exact entry hashes, local citation contexts, and the scope of external verification. `code-quality-audit.json`, `anti-overfitting-audit.json`, `results_manifest.csv`, and `reproduction-report.json` retain the earlier host/build measurements and source bindings (including the 56-test scientific suite and dated 2026-09-26 audits); they are historical records, not measurements of the current source. The current finite results and source bindings are `raw/results.json` and `raw/run_manifest.json`. The checker does not prove contextual equivalence, infer a real compiler's exact image, or replace the paper's arbitrary-set proofs.

The prepared `scientific-checks.yml` workflow runs from this directory as a flat artifact-repository root on Ubuntu 24.04 for pushes to `main` or manual dispatch. It retains failed outputs, applies a 600-second whole-run limit plus resource limits, and preserves failure exit codes. A local run is not an execution of that workflow.
