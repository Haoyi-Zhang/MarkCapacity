# Executable artifact

Run `./run-tests.sh` from this directory. The suite contains 61 tests and regenerates the scientific outputs twice before comparing exact bytes. Python's standard library is sufficient; no network service, trained model, GPU, external dataset, or compiler installation is required for the finite checks.

The exhaustive checks cover 1,943 refinement instances, 11,423 general partition instances, 38,564 source-dependent access instances, and 54 correlated list-recovery instances. Constructive checks include 128 exhaustive and 192 deterministic generated witness cases. A separate 240-instance unfiltered stress set ranges over three to five programs and compares both general and access classifications against direct program-level oracles; every positive access instance is returned as a concrete encoder/decoder witness and validated independently.

`reference-audit-final.csv`, `citation_support.csv`, and `literature-evidence/` record bibliography status, exact entry hashes, local citation contexts, and the scope of external verification. They distinguish formal publications from status-labelled preprints and do not claim a perpetual guarantee against future corrections or retractions.

`code-quality-audit.json`, `anti-overfitting-audit.json`, `results_manifest.csv`, and `reproduction-report.json` describe the bounded executable evidence and its limitations. The checker does not prove contextual equivalence, instantiate a real compiler, or replace the paper's arbitrary-set proofs.
