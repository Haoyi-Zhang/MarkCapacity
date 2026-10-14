# Executable pure-source realization

The source stage lowers the existing component-local arithmetic grammar into
ordinary function-local CPython syntax. Distinct fresh `v_i` temporaries preserve
the local bindings; actual AST operand swaps and temporary rewrites implement
the same insertion-wide one-commutation budget. The parser admits only positional
`x_i` arguments, integer literal one, addition, fresh one-use assignments and a
tuple return. It does not execute general Python, effects, callbacks, annotations
or default expressions. Calls require an exact integer Boolean tuple. This is
an admission grammar, not a sandbox for arbitrary code.

The source theorem is a round-trip, evaluation and step correspondence under
return-value-only contexts. Python reflection, timing, function objects,
overloaded addition, other numeric types and production compiler passes are
outside that context contract. Cube domatic capacities, syndrome labels and
the coordinate-product exponent remain known combinatorics. The new execution
path checks source-realizable representatives; function-call counts are not
capacity estimates or evidence of novelty.

Run from the artifact directory, with a fresh output path:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B src/run_source.py --out /path/to/fresh-output
```

The fixed campaign covers every order/naming procedure through three sites,
every normalization subset, every requested syndrome and every Boolean input.
At seven sites it covers all 128 order vectors but only the all-direct and
all-named forms, every eight-message request and all 128 Boolean inputs. Other
seven-site naming combinations are not represented as executed data.

`results/source-execution/rows.jsonl` retains actual per-input native returns,
reference returns and source/output IDs. `programs/<sha256>.py` stores the exact
owned source text. `summary.json` binds four executed sources (relative to
`src/`), counts actual calls/compilations and describes the host. The two execution
command records distinguish repeated execution from a single result. The
scientific rows and all program files matched in both complete runs.

The binding negative executes a fixed benign reuse of `t` on input `(0,1)` and
gets `(2,2)` rather than the model's `(1,2)`; the admitted parser rejects that
source. This is a lowering counterexample, not an old renderer bug (the frozen
artifact had no ordinary-source renderer). The excluded-normalization negative
preserves returned values but erases a requested label. Both remain in
`negative.json`.

`results/partition-admission/` separately retains five before/after observations
and their command/source bindings. An overlapping/empty block family is not an
equivalence just because its union matches another partition. Both decision
routes now reject malformed blocks before class indexing or empty-product
shortcuts, while preserving valid block order and valid empty-access obstructions.

The original abstract census and all historical evidence stay unchanged.
`results/abstract-reexecution/` records two complete current-source runs; their
scientific JSON, table and stdout match the old data. Current source manifests
are distinct from the historical source manifest. Windows CPython 3.12.14 ran
all 88 scientific tests; the POSIX launchers, package/export mode checks, older
Python versions and remote CI were not executed by that Windows run.
