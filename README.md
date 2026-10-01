# Executable artifact

## Self-contained scientific reproduction

Run:

```sh
./run-tests.sh
```

This is the independent-code-package entry point. It runs 56 scientific tests, regenerates the finite scientific outputs twice, compares their exact bytes, and verifies `raw/SHA256SUMS`. It requires Python 3 with only the standard library, Bash, and ordinary core utilities (`mktemp`, `sed`, `cp`, `cmp`, and `sha256sum`). It does **not** read the parent `paper/` directory and does not invoke PDF tools.

The scientific tests cover 1,943 refinement instances, 11,423 general partition instances, 38,564 source-dependent access instances, and 54 correlated list-recovery instances. Constructive checks include 128 exhaustive and 192 deterministic generated witness cases. A separate 240-instance unfiltered stress set ranges over three to five programs and compares the optimized classifications against direct program-level oracles.

The input contract is explicit. Every declared source must have an access row; directed instances require both a preservation row and an access row. A missing row is malformed input and raises `ValueError`. An explicitly supplied empty row is different: it is a valid empty constraint and makes every nonempty exact message alphabet infeasible. The boundary tests cover empty support, a missing row, a one-source empty row, and a one-source identity row.

## Full-project integrity checks

From this `artifact/` directory in a complete project checkout, run:

```sh
./run-package-checks.sh
```

This entry point runs 8 package-integrity tests. It requires the sibling `paper/` tree, `CURRENT-STATE.md`, `research-plan.md`, and the project manifest. It also requires Poppler's `pdfinfo` and `pdftotext`; the script checks and reports these dependencies before running any tests. Missing assets or commands cause an explicit input/dependency error and are never converted into a scientific infeasibility result.

To run both entry points in a complete checkout:

```sh
./run-all-checks.sh
```

The combined public total is 64 checks: 56 scientific and 8 package-integrity checks. The two counts are reported separately because only the scientific suite is self-contained.

`reference-audit-final.csv`, `citation_support.csv`, and `literature-evidence/` record bibliography status, exact entry hashes, local citation contexts, and the scope of external verification. `code-quality-audit.json`, `anti-overfitting-audit.json`, `results_manifest.csv`, and `reproduction-report.json` state the bounded nature of the executable evidence. The checker does not prove contextual equivalence, infer a real compiler's exact image, or replace the paper's arbitrary-set proofs.
