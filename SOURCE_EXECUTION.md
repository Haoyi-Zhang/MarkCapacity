# Executable pure-source realization

## Source-facing single-step receipts

`src/source_witness.py` adds `encode_with_receipt(text, message, normalized)`
and `verify_receipt(text, output, receipt, normalized)` for this same admitted grammar.
Unlike the retained historical encoder, the adapter applies an actual AST
commutation without invoking the model embedder. The receipt binds both source
texts, the normalization contract, requested message, source site and budget.
The verifier replays the AST effect and uses the retained decoder, rejecting a
correctly decoded output reached by two swaps, an extra naming edit, and changed
source bindings. Its trusted normalization policy is supplied separately and
must match the receipt; the receipt cannot weaken its own attack contract.
Hashes bind the handoff; they are not proof of reachability.

Run `python -B -m unittest discover -s tests -p test_source_witness.py -v`.
The check covers the existing 1,213 through-three-site source/request pairs and
their Boolean inputs; it does not enlarge the claimed language or capacity.
The original source encoder, campaigns and historical records are unchanged.
Both paths trust the same strict source admission/parser; this is a separate
algorithmic representation of the edit obligation, not independent authorship.

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

## Read-only retained-record validation after source maintenance

Run `python -B src/check_source.py --out results/source-execution` from this
checkout. This is a checkout-root data consumer, not an installation/wheel CLI.
It requires the complete fixed four-producer source map. For the historical
map it reads the exact byte-verified `source-preimages/source-execution/` files,
including the parser before its reserved-target repair. These sources are never
loaded or executed. This retained-protocol consumer rejects any different map,
even a map matching repaired current code: relabeling an old receipt cannot
establish that the repaired code was measured. A future protocol/source era
would need its own explicit binding rather than changing these saved identities.

The consumer binds and parses both fixed negative cases, checks their typed
inputs and returns, derives their values only as bounded data, and compares all
protocol/count fields. It does not execute negative source text. A success keeps
the recorded 290,997 calls and 5,820 compilations unchanged and reports
`data_only_derivation_no_native_replay`; it is not a new measurement or native
replay. Original summary/environment/timing/row/source-map bytes remain intact.
The bounded four-method source-record regression suite also exercises omitted
bindings, corrupt/missing preimages, altered negatives and contradictory summary
fields under both ordinary Python and `-O`.

`source_language.inspect_source` rejects Python's reserved `__debug__` assignment
target before source/receipt admission. This remains an owned finite grammar,
not an arbitrary-code sandbox; the generated `v_i` source contract is unchanged.
