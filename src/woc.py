"""Finite models for the Watermark Observational Calculus (WOC).

The mathematical paper is primary.  This module is a dependency-free executable
sanity checker for finite instances of its quotient-capacity theorems.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product
from typing import Hashable, Iterable, Iterator, Mapping, Sequence

Element = Hashable
Block = frozenset[Element]
Partition = tuple[Block, ...]


def _key(x: Element) -> tuple[str, str]:
    return (type(x).__name__, repr(x))


def normalize_partition(blocks: Iterable[Iterable[Element]]) -> Partition:
    """Validate and canonically order a finite partition."""
    normalized = [frozenset(block) for block in blocks]
    if any(not block for block in normalized):
        raise ValueError("partition blocks must be nonempty")
    seen: set[Element] = set()
    for block in normalized:
        overlap = seen.intersection(block)
        if overlap:
            raise ValueError(f"partition blocks overlap: {overlap!r}")
        seen.update(block)
    return tuple(sorted(normalized, key=lambda b: tuple(_key(x) for x in sorted(b, key=_key))))


def universe(partition: Partition) -> frozenset[Element]:
    return frozenset().union(*partition) if partition else frozenset()


def block_index(partition: Partition) -> dict[Element, int]:
    return {element: i for i, block in enumerate(partition) for element in block}


def _same_nonempty_universe(
    first: Partition,
    second: Partition,
) -> frozenset[Element]:
    """Validate that two partitions describe one nonempty program universe."""
    first_universe = universe(first)
    if not first_universe:
        raise ValueError("a nonempty program universe is required")
    if first_universe != universe(second):
        raise ValueError("partitions must have the same universe")
    return first_universe


def _materialize_required_rows(
    relation: Mapping[Element, Iterable[Element]],
    sources: Iterable[Element],
    target_universe: frozenset[Element],
    relation_name: str,
) -> dict[Element, frozenset[Element]]:
    """Materialize every required source row without inventing missing rows.

    An explicitly supplied empty row is a legitimate row.  A missing row is an
    incomplete input contract and raises ``ValueError`` rather than being
    reinterpreted as an empty mathematical constraint.
    """
    source_items = tuple(sorted(set(sources), key=_key))
    missing = [source for source in source_items if source not in relation]
    if missing:
        raise ValueError(
            f"{relation_name} is missing source row(s): "
            f"{sorted(missing, key=_key)!r}"
        )

    rows: dict[Element, frozenset[Element]] = {}
    for source in source_items:
        try:
            row = frozenset(relation[source])
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"invalid {relation_name} row for {source!r}"
            ) from exc
        outside = row.difference(target_universe)
        if outside:
            raise ValueError(
                f"{relation_name} row for {source!r} contains elements outside "
                f"the target universe: {outside!r}"
            )
        rows[source] = row
    return rows


def is_refinement(fine: Partition, coarse: Partition) -> bool:
    """Return whether every fine block lies within one coarse block."""
    if universe(fine) != universe(coarse):
        return False
    coarse_index = block_index(coarse)
    return all(len({coarse_index[x] for x in block}) == 1 for block in fine)


def join_partitions(*partitions: Partition) -> Partition:
    """Least equivalence relation containing every supplied partition."""
    if not partitions:
        return tuple()
    u = universe(partitions[0])
    if any(universe(p) != u for p in partitions[1:]):
        raise ValueError("partitions must have the same universe")
    parent = {x: x for x in u}

    def find(x: Element) -> Element:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: Element, b: Element) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for partition in partitions:
        for block in partition:
            first = next(iter(block))
            for x in block:
                union(first, x)
    groups: dict[Element, set[Element]] = {}
    for x in u:
        groups.setdefault(find(x), set()).add(x)
    return normalize_partition(groups.values())


def quotient_cells(behavior: Partition, indistinguishability: Partition) -> tuple[tuple[Block, ...], ...]:
    """List indistinguishability cells contained in each behavior class.

    Requires a nonempty common universe and the indistinguishability partition
    to refine behavior.
    """
    _same_nonempty_universe(behavior, indistinguishability)
    if not is_refinement(indistinguishability, behavior):
        raise ValueError("indistinguishability must refine behavior")
    j_index = block_index(indistinguishability)
    return tuple(
        tuple(indistinguishability[i] for i in sorted({j_index[x] for x in b_block}))
        for b_block in behavior
    )


def exact_message_capacity(behavior: Partition, indistinguishability: Partition) -> int:
    """Worst-case exact alphabet size on a nonempty supported universe."""
    cells = quotient_cells(behavior, indistinguishability)
    return min(len(x) for x in cells)


def guaranteed_bit_capacity(behavior: Partition, indistinguishability: Partition) -> int:
    """Number of whole bits guaranteed in every behavior class."""
    messages = exact_message_capacity(behavior, indistinguishability)
    return messages.bit_length() - 1 if messages > 0 else 0


def construct_decoder(
    behavior: Partition,
    indistinguishability: Partition,
    messages: int,
) -> dict[Element, int]:
    """Construct the theorem's decoder for a finite refinement instance."""
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    cells_by_behavior = quotient_cells(behavior, indistinguishability)
    if any(len(cells) < messages for cells in cells_by_behavior):
        raise ValueError("insufficient quotient cells in at least one behavior class")
    decoder: dict[Element, int] = {}
    for cells in cells_by_behavior:
        for i, cell in enumerate(cells):
            label = i if i < messages else 0
            for x in cell:
                decoder[x] = label
    return decoder


def construct_embedder(
    behavior: Partition,
    indistinguishability: Partition,
    messages: int,
    decoder: Mapping[Element, int] | None = None,
) -> dict[tuple[Element, int], Element]:
    """Choose one representative of each message in every behavior class."""
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    if decoder is None:
        decoder = construct_decoder(behavior, indistinguishability, messages)
    decoder = dict(decoder)
    expected = universe(behavior)
    if set(decoder) != set(expected) or any(
        not isinstance(label, int) or isinstance(label, bool) or not 0 <= label < messages
        for label in decoder.values()
    ):
        raise ValueError("decoder must label exactly the program universe")
    # Supplied labels must satisfy the same refinement and invariance contract
    # as labels synthesized by construct_decoder.
    quotient_cells(behavior, indistinguishability)
    if any(len({decoder[x] for x in cell}) != 1 for cell in indistinguishability):
        raise ValueError("decoder is not constant on an operational cell")
    embedder: dict[tuple[Element, int], Element] = {}
    for b_block in behavior:
        representatives: dict[int, Element] = {}
        for x in sorted(b_block, key=_key):
            label = decoder[x]
            representatives.setdefault(label, x)
        if set(representatives) != set(range(messages)):
            raise ValueError("decoder does not realize every message in a behavior class")
        for p in b_block:
            for message in range(messages):
                embedder[(p, message)] = representatives[message]
    return embedder


def validate_scheme(
    behavior: Partition,
    indistinguishability: Partition,
    messages: int,
    decoder: Mapping[Element, int],
    embedder: Mapping[tuple[Element, int], Element],
) -> tuple[bool, list[str]]:
    """Independently validate a total finite exact scheme.

    ``None`` is an ordinary hashable program value, not a missing-entry marker.
    Malformed witnesses are rejected with diagnostics instead of indexing into
    absent decoder/behavior rows or accepting a vacuous zero-message contract.
    """
    failures: list[str] = []
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        return False, ["messages must be a positive integer"]
    try:
        behavior = normalize_partition(behavior)
        indistinguishability = normalize_partition(indistinguishability)
    except (ValueError, TypeError) as exc:
        return False, [f"invalid partition: {exc}"]
    u = universe(behavior)
    if not u or u != universe(indistinguishability):
        return False, ["partitions must have the same nonempty universe"]
    if set(decoder) != set(u):
        failures.append("decoder domain must equal the program universe")
    for x, label in decoder.items():
        if not isinstance(label, int) or isinstance(label, bool) or not 0 <= label < messages:
            failures.append(f"decoder label outside the message alphabet at {x!r}")
    b_index = block_index(behavior)
    for j_block in indistinguishability:
        if any(x not in decoder for x in j_block):
            continue
        if any(decoder[x] != decoder[next(iter(j_block))] for x in j_block):
            failures.append(f"decoder is not constant on J-cell {sorted(j_block, key=_key)!r}")
    required_pairs = {(p, m) for p in u for m in range(messages)}
    if set(embedder) != required_pairs:
        failures.append("embedder domain must contain exactly all source-message pairs")
    missing = object()
    for source, message in sorted(required_pairs, key=lambda pair: (_key(pair[0]), pair[1])):
        q = embedder.get((source, message), missing)
        if q is missing:
            failures.append(f"missing embedding for {(source, message)!r}")
            continue
        try:
            in_universe = q in u
        except TypeError:
            in_universe = False
        if not in_universe:
            failures.append(f"output outside the program universe for {(source, message)!r}")
            continue
        if b_index[source] != b_index[q]:
            failures.append(f"behavior not preserved for {(source, message)!r}: {q!r}")
        if q not in decoder or decoder[q] != message:
            failures.append(f"message not recovered for {(source, message)!r}: {q!r}")
    return not failures, failures


def validate_access_scheme(
    behavior: Partition,
    indistinguishability: Partition,
    access: Mapping[Element, Iterable[Element]],
    messages: int,
    decoder: Mapping[Element, int],
    embedder: Mapping[tuple[Element, int], Element],
) -> tuple[bool, list[str]]:
    """Check preservation, decoding, and actual source-output membership.

    This validator never constructs or solves a quotient hypergraph; it checks
    the proposed program-level witness directly.
    """
    try:
        u = _same_nonempty_universe(behavior, indistinguishability)
        access_rows = _materialize_required_rows(access, u, u, "access relation")
    except ValueError as exc:
        return False, [str(exc)]

    valid, failures = validate_scheme(
        behavior, indistinguishability, messages, decoder, embedder
    )
    if not valid:
        return False, failures
    for source in sorted(u, key=_key):
        outputs = access_rows[source]
        for message in range(messages):
            if embedder[(source, message)] not in outputs:
                failures.append(f"output is not reachable for {(source, message)!r}")
    return not failures, failures


def construct_access_scheme(
    behavior: Partition,
    indistinguishability: Partition,
    access: Mapping[Element, Iterable[Element]],
    messages: int,
) -> tuple[dict[Element, int], dict[tuple[Element, int], Element]]:
    """Extract program-level decoder/embedding witnesses from an access coloring."""
    u = _same_nonempty_universe(behavior, indistinguishability)
    # Materialize once: callers may supply single-use iterators as access rows.
    access_rows = _materialize_required_rows(access, u, u, "access relation")
    edges = access_hypergraph(behavior, indistinguishability, access_rows)
    coloring = find_polychromatic_coloring(edges, len(indistinguishability), messages)
    if coloring is None:
        raise ValueError("the access constraints admit no exact scheme")
    decoder = {p: coloring[i] for i, block in enumerate(indistinguishability) for p in block}
    b_index = block_index(behavior)
    embedder: dict[tuple[Element, int], Element] = {}
    for source in sorted(u, key=_key):
        candidates = sorted((q for q in access_rows[source] if b_index[source] == b_index[q]), key=_key)
        for message in range(messages):
            embedder[(source, message)] = next(q for q in candidates if decoder[q] == message)
    return decoder, embedder


def quotient_hypergraph(behavior: Partition, indistinguishability: Partition) -> tuple[tuple[int, ...], ...]:
    """Behavior classes as hyperedges over global J-cells."""
    _same_nonempty_universe(behavior, indistinguishability)
    j_index = block_index(indistinguishability)
    return tuple(tuple(sorted({j_index[x] for x in block})) for block in behavior)


def access_hypergraph(
    behavior: Partition,
    indistinguishability: Partition,
    access: Mapping[Element, Iterable[Element]],
) -> tuple[tuple[int, ...], ...]:
    """Program-indexed accessible J-cells for a constrained embedder.

    ``access[p]`` lists outputs the embedding mechanism is allowed to choose from
    input ``p`` before behavior preservation is imposed.  The returned edge for
    ``p`` therefore contains exactly the J-cells meeting both ``access[p]`` and
    the behavior class of ``p``.  Every source row must be present; an explicitly
    supplied empty row remains a valid empty edge and makes positive-message
    feasibility fail.
    """
    u = _same_nonempty_universe(behavior, indistinguishability)
    access_rows = _materialize_required_rows(access, u, u, "access relation")
    b_index = block_index(behavior)
    j_index = block_index(indistinguishability)
    edges: list[tuple[int, ...]] = []
    for p in sorted(u, key=_key):
        candidates = access_rows[p]
        allowed_cells = {
            j_index[q]
            for q in candidates
            if b_index[q] == b_index[p]
        }
        edges.append(tuple(sorted(allowed_cells)))
    return tuple(edges)


def access_exact_feasible(
    behavior: Partition,
    indistinguishability: Partition,
    access: Mapping[Element, Iterable[Element]],
    messages: int,
) -> bool:
    """Return whether a constrained exact scheme exists on a finite instance."""
    edges = access_hypergraph(behavior, indistinguishability, access)
    return find_polychromatic_coloring(edges, len(indistinguishability), messages) is not None


def access_message_capacity(
    behavior: Partition,
    indistinguishability: Partition,
    access: Mapping[Element, Iterable[Element]],
) -> int:
    """Largest feasible positive alphabet, or zero when an access edge is empty.

    Zero is a sentinel for the absence of any exact scheme with a nonempty
    message alphabet.  It is not an implementable empty-message scheme.  A
    one-message result, by contrast, is feasible and carries zero selected bits.
    """
    edges = access_hypergraph(behavior, indistinguishability, access)
    if any(not edge for edge in edges):
        return 0
    return polychromatic_number(edges, len(indistinguishability))


def direct_access_exact_feasible(
    behavior: Partition,
    indistinguishability: Partition,
    access: Mapping[Element, Iterable[Element]],
    messages: int,
) -> bool:
    """Independent program-level oracle for constrained exact feasibility."""
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    u = _same_nonempty_universe(behavior, indistinguishability)
    items = tuple(sorted(u, key=_key))
    b_index = block_index(behavior)
    access_rows = _materialize_required_rows(access, items, u, "access relation")
    normalized_access: dict[Element, frozenset[Element]] = {
        p: frozenset(q for q in access_rows[p] if b_index[q] == b_index[p])
        for p in items
    }

    target = set(range(messages))
    for values in product(range(messages), repeat=len(items)):
        decoder = dict(zip(items, values, strict=True))
        if any(len({decoder[x] for x in block}) != 1 for block in indistinguishability):
            continue
        if all({decoder[q] for q in normalized_access[p]} == target for p in items):
            return True
    return False



def directed_access_hypergraph(
    sources: Iterable[Element],
    targets: Partition,
    preservation: Mapping[Element, Iterable[Element]],
    access: Mapping[Element, Iterable[Element]],
) -> tuple[tuple[int, ...], ...]:
    """Source-indexed target cells satisfying both preservation and access.

    ``sources`` and target programs may be disjoint.  ``targets`` is the
    operational partition on the target side; each source edge contains the
    target blocks that meet both its directed preservation row and its access
    row.  Both mappings must contain every declared source row; explicit empty
    rows remain valid and induce an empty source constraint.
    """
    source_items = tuple(sorted(set(sources), key=_key))
    target_universe = universe(targets)
    if not target_universe:
        raise ValueError("a nonempty target universe is required")
    preservation_rows = _materialize_required_rows(
        preservation, source_items, target_universe, "preservation relation"
    )
    access_rows = _materialize_required_rows(
        access, source_items, target_universe, "access relation"
    )
    target_index = block_index(targets)
    edges: list[tuple[int, ...]] = []
    for source in source_items:
        cells = {
            target_index[q]
            for q in preservation_rows[source].intersection(access_rows[source])
        }
        edges.append(tuple(sorted(cells)))
    return tuple(edges)


def directed_access_exact_feasible(
    sources: Iterable[Element],
    targets: Partition,
    preservation: Mapping[Element, Iterable[Element]],
    access: Mapping[Element, Iterable[Element]],
    messages: int,
) -> bool:
    """Quotient-hypergraph decision procedure for directed preservation."""
    edges = directed_access_hypergraph(sources, targets, preservation, access)
    return find_polychromatic_coloring(edges, len(targets), messages) is not None


def direct_directed_access_exact_feasible(
    sources: Iterable[Element],
    targets: Partition,
    preservation: Mapping[Element, Iterable[Element]],
    access: Mapping[Element, Iterable[Element]],
    messages: int,
) -> bool:
    """Independent target-label oracle for directed preservation feasibility."""
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    source_items = tuple(sorted(set(sources), key=_key))
    target_items = tuple(sorted(universe(targets), key=_key))
    target_universe = frozenset(target_items)
    if not target_universe:
        raise ValueError("a nonempty target universe is required")
    preservation_rows = _materialize_required_rows(
        preservation, source_items, target_universe, "preservation relation"
    )
    access_rows = _materialize_required_rows(
        access, source_items, target_universe, "access relation"
    )
    admissible = {
        source: preservation_rows[source].intersection(access_rows[source])
        for source in source_items
    }

    required = set(range(messages))
    for values in product(range(messages), repeat=len(target_items)):
        decoder = dict(zip(target_items, values, strict=True))
        if any(len({decoder[q] for q in block}) != 1 for block in targets):
            continue
        if all({decoder[q] for q in admissible[source]} == required for source in source_items):
            return True
    return False



def _bounded_subsets(messages: int, budget: int) -> tuple[frozenset[int], ...]:
    """All message subsets of size at most ``budget`` in canonical order."""
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise ValueError("list budgets must be nonnegative integers")
    cap = min(messages, budget)
    return tuple(
        frozenset(choice)
        for size in range(cap + 1)
        for choice in combinations(range(messages), size)
    )


def max_average_list_cover(
    edges: Sequence[Sequence[int]],
    vertices: int,
    messages: int,
    budgets: Sequence[int],
    weights: Sequence[Sequence[Fraction | int]],
) -> tuple[Fraction, tuple[frozenset[int], ...]]:
    """Exact deterministic list-cover optimum for a small finite instance.

    ``edges[i]`` is the set of operational cells reachable from source row ``i``;
    ``weights[i][m]`` is the joint mass of that source-message pair.  The
    routine uses exact rational arithmetic and is intentionally exponential.
    """
    if not isinstance(vertices, int) or isinstance(vertices, bool) or vertices < 0:
        raise ValueError("vertex count must be a nonnegative integer")
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    normalized = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    if len(budgets) != vertices:
        raise ValueError("one list budget is required per vertex")
    if any(not isinstance(budget, int) or isinstance(budget, bool) or budget < 0 for budget in budgets):
        raise ValueError("list budgets must be nonnegative integers")
    if len(weights) != len(normalized):
        raise ValueError("one weight row is required per source edge")
    if any(len(row) != messages for row in weights):
        raise ValueError("each weight row must have one entry per message")
    if any(any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < vertices for v in edge) for edge in normalized):
        raise ValueError("vertices must be integer indices inside the declared universe")
    if any(not edge for edge in normalized):
        raise ValueError("source access edges must be nonempty")

    rational_weights = tuple(tuple(Fraction(value) for value in row) for row in weights)
    if any(value < 0 for row in rational_weights for value in row):
        raise ValueError("weights must be nonnegative")
    choices = tuple(_bounded_subsets(messages, budget) for budget in budgets)
    best = Fraction(-1)
    witness: tuple[frozenset[int], ...] | None = None
    for assignment in product(*choices):
        value = Fraction(0)
        for edge, row in zip(normalized, rational_weights, strict=True):
            covered: set[int] = set()
            for vertex in edge:
                covered.update(assignment[vertex])
            value += sum(row[message] for message in covered)
        if value > best:
            best = value
            witness = tuple(assignment)
    if witness is None:
        raise AssertionError("finite list assignment space must be nonempty")
    return best, witness


def direct_average_list_cover(
    behavior: Partition,
    indistinguishability: Partition,
    access: Mapping[Element, Iterable[Element]],
    messages: int,
    budgets: Sequence[int],
    weights: Mapping[tuple[Element, int], Fraction | int],
) -> tuple[Fraction, tuple[frozenset[int], ...]]:
    """Program-level oracle for average list recovery.

    This path never constructs an access hypergraph.  It enumerates one list per
    operational block, expands the lists back to program elements, filters each
    source row by behavior preservation, and evaluates the supplied joint mass.
    """
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    u = _same_nonempty_universe(behavior, indistinguishability)
    if len(budgets) != len(indistinguishability):
        raise ValueError("one list budget is required per operational block")
    if any(not isinstance(budget, int) or isinstance(budget, bool) or budget < 0 for budget in budgets):
        raise ValueError("list budgets must be nonnegative integers")
    items = tuple(sorted(u, key=_key))
    b_index = block_index(behavior)
    j_index = block_index(indistinguishability)
    access_rows = _materialize_required_rows(access, items, u, "access relation")
    normalized_access: dict[Element, frozenset[Element]] = {}
    for source in items:
        allowed = frozenset(
            q for q in access_rows[source] if b_index[q] == b_index[source]
        )
        if not allowed:
            raise ValueError("source access edges must be nonempty after behavior filtering")
        normalized_access[source] = allowed

    rational_weights = {
        (source, message): Fraction(weights.get((source, message), 0))
        for source in items
        for message in range(messages)
    }
    if any(value < 0 for value in rational_weights.values()):
        raise ValueError("weights must be nonnegative")

    choices = tuple(_bounded_subsets(messages, budget) for budget in budgets)
    best = Fraction(-1)
    witness: tuple[frozenset[int], ...] | None = None
    for assignment in product(*choices):
        program_lists = {program: assignment[j_index[program]] for program in items}
        value = Fraction(0)
        for source in items:
            covered: set[int] = set()
            for output in normalized_access[source]:
                covered.update(program_lists[output])
            value += sum(rational_weights[(source, message)] for message in covered)
        if value > best:
            best = value
            witness = tuple(assignment)
    if witness is None:
        raise AssertionError("finite list assignment space must be nonempty")
    return best, witness


def deterministic_worst_source_value(
    edges: Sequence[Sequence[int]],
    vertices: int,
    prior: Sequence[Fraction | int],
) -> tuple[Fraction, tuple[int, ...]]:
    """Exact worst-edge recovery of a deterministic single-label decoder."""
    if not isinstance(vertices, int) or isinstance(vertices, bool) or vertices < 0:
        raise ValueError("vertex count must be a nonnegative integer")
    messages = len(prior)
    if messages < 1:
        raise ValueError("the message prior must be nonempty")
    normalized = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    if not normalized or any(not edge for edge in normalized):
        raise ValueError("a nonempty family of nonempty edges is required")
    if any(any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < vertices for v in edge) for edge in normalized):
        raise ValueError("vertices must be integer indices inside the declared universe")
    mu = tuple(Fraction(value) for value in prior)
    if any(value < 0 for value in mu) or sum(mu) != 1:
        raise ValueError("the prior must be a probability distribution")
    best = Fraction(-1)
    witness: tuple[int, ...] | None = None
    for coloring in product(range(messages), repeat=vertices):
        value = min(sum(mu[m] for m in {coloring[v] for v in edge}) for edge in normalized)
        if value > best:
            best = value
            witness = tuple(coloring)
    if witness is None:
        raise AssertionError("finite coloring space must be nonempty")
    return best, witness


def private_recovery_value(
    edges: Sequence[Sequence[int]],
    prior: Sequence[Fraction | int],
    vertex_distributions: Sequence[Sequence[Fraction | int]],
) -> Fraction:
    """Evaluate a supplied private-decoder random strategy exactly."""
    messages = len(prior)
    mu = tuple(Fraction(value) for value in prior)
    if any(value < 0 for value in mu) or sum(mu) != 1:
        raise ValueError("the prior must be a probability distribution")
    q = tuple(tuple(Fraction(value) for value in row) for row in vertex_distributions)
    if any(len(row) != messages or any(value < 0 for value in row) or sum(row) != 1 for row in q):
        raise ValueError("every vertex row must be a message distribution")
    normalized = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    if not normalized or any(not edge for edge in normalized):
        raise ValueError("a nonempty family of nonempty edges is required")
    if any(any(not 0 <= v < len(q) for v in edge) for edge in normalized):
        raise ValueError("vertex out of range")
    return min(
        sum(mu[m] * max(q[v][m] for v in edge) for m in range(messages))
        for edge in normalized
    )


def shared_recovery_value(
    edges: Sequence[Sequence[int]],
    prior: Sequence[Fraction | int],
    coloring_distribution: Mapping[Sequence[int], Fraction | int],
) -> Fraction:
    """Evaluate a supplied shared-random coloring distribution exactly."""
    messages = len(prior)
    mu = tuple(Fraction(value) for value in prior)
    if any(value < 0 for value in mu) or sum(mu) != 1:
        raise ValueError("the prior must be a probability distribution")
    distribution = {tuple(coloring): Fraction(weight) for coloring, weight in coloring_distribution.items()}
    if any(weight < 0 for weight in distribution.values()) or sum(distribution.values()) != 1:
        raise ValueError("coloring weights must form a probability distribution")
    if not distribution:
        raise ValueError("at least one coloring is required")
    vertices = len(next(iter(distribution)))
    if any(len(coloring) != vertices for coloring in distribution):
        raise ValueError("all colorings must have the same length")
    if any(any(not 0 <= color < messages for color in coloring) for coloring in distribution):
        raise ValueError("color out of range")
    normalized = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    if not normalized or any(not edge for edge in normalized):
        raise ValueError("a nonempty family of nonempty edges is required")
    if any(any(not 0 <= v < vertices for v in edge) for edge in normalized):
        raise ValueError("vertex out of range")
    edge_values = []
    for edge in normalized:
        value = Fraction(0)
        for coloring, weight in distribution.items():
            value += weight * sum(mu[m] for m in {coloring[v] for v in edge})
        edge_values.append(value)
    return min(edge_values)


def shared_recovery_dual_bound(
    edges: Sequence[Sequence[int]],
    prior: Sequence[Fraction | int],
    edge_weights: Sequence[Fraction | int],
    vertices: int,
) -> Fraction:
    """Upper bound shared recovery by a distribution over source constraints.

    For every strategy, its minimum edge value is at most any convex combination
    of edge values.  Maximizing that combination over deterministic colorings
    therefore gives a valid dual certificate for shared-random recovery.
    """
    if not isinstance(vertices, int) or isinstance(vertices, bool) or vertices < 1:
        raise ValueError("vertex count must be a positive integer")
    messages = len(prior)
    mu = tuple(Fraction(value) for value in prior)
    alpha = tuple(Fraction(value) for value in edge_weights)
    normalized = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    if not normalized or any(not edge for edge in normalized):
        raise ValueError("a nonempty family of nonempty edges is required")
    if any(any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < vertices for v in edge) for edge in normalized):
        raise ValueError("vertices must be integer indices inside the declared universe")
    if len(alpha) != len(normalized) or any(value < 0 for value in alpha) or sum(alpha) != 1:
        raise ValueError("edge weights must be a probability distribution")
    if any(value < 0 for value in mu) or sum(mu) != 1:
        raise ValueError("the prior must be a probability distribution")
    best = Fraction(-1)
    for coloring in product(range(messages), repeat=vertices):
        weighted = sum(
            alpha[i] * sum(mu[m] for m in {coloring[v] for v in edge})
            for i, edge in enumerate(normalized)
        )
        best = max(best, weighted)
    return best


def incidence_partitions(edges: Sequence[Iterable[Element]]) -> tuple[Partition, Partition]:
    """Realize a finite hypergraph as behavior and operational partitions.

    One program is created for every edge-vertex incidence.  Behavior blocks group
    incidences by hyperedge, while operational blocks group incidences by vertex.
    Isolated vertices are immaterial because they occur in no hyperedge.
    """
    normalized_edges = [frozenset(edge) for edge in edges]
    if not normalized_edges:
        raise ValueError("the hypergraph must contain at least one edge")
    if any(not edge for edge in normalized_edges):
        raise ValueError("hyperedges must be nonempty")

    behavior_blocks: list[set[Element]] = []
    by_vertex: dict[Element, set[Element]] = {}
    for edge_index, edge in enumerate(normalized_edges):
        block: set[Element] = set()
        for vertex in edge:
            incidence: Element = (edge_index, vertex)
            block.add(incidence)
            by_vertex.setdefault(vertex, set()).add(incidence)
        behavior_blocks.append(block)
    return normalize_partition(behavior_blocks), normalize_partition(by_vertex.values())


def incidence_access_instance(
    edges: Sequence[Iterable[Element]],
) -> tuple[Partition, Partition, dict[Element, frozenset[Element]]]:
    """Realize hypergraph constraints as source-dependent embedding access.

    Programs are edge--vertex incidences.  All programs share one behavior class,
    J-cells group incidences by vertex, and each incidence may embed to any
    incidence of its own edge.  The access relation is reflexive, every program
    belonging to edge ``e`` induces edge ``e``, and J therefore refines behavior.
    """
    normalized_edges = [frozenset(edge) for edge in edges]
    if not normalized_edges:
        raise ValueError("the hypergraph must contain at least one edge")
    if any(not edge for edge in normalized_edges):
        raise ValueError("hyperedges must be nonempty")

    edge_blocks: list[frozenset[Element]] = []
    by_vertex: dict[Element, set[Element]] = {}
    for edge_index, edge in enumerate(normalized_edges):
        block = frozenset((edge_index, vertex) for vertex in edge)
        edge_blocks.append(block)
        for incidence in block:
            by_vertex.setdefault(incidence[1], set()).add(incidence)

    all_programs = frozenset().union(*edge_blocks)
    behavior = normalize_partition([all_programs])
    indistinguishability = normalize_partition(by_vertex.values())
    access = {
        incidence: block
        for block in edge_blocks
        for incidence in block
    }
    return behavior, indistinguishability, access



def product_partition(first: Partition, second: Partition) -> Partition:
    """Cartesian product of two finite partitions."""
    if not first or not second:
        return tuple()
    return normalize_partition(
        {(x, y) for x in first_block for y in second_block}
        for first_block in first
        for second_block in second
    )


def coordinate_product_edges(
    first_edges: Sequence[Sequence[int]],
    first_vertices: int,
    second_edges: Sequence[Sequence[int]],
    second_vertices: int,
) -> tuple[tuple[int, ...], ...]:
    """Coordinate product of two finite hypergraphs with integer vertices."""
    if first_vertices < 0 or second_vertices < 0:
        raise ValueError("vertex counts must be nonnegative")
    normalized_first = tuple(tuple(dict.fromkeys(edge)) for edge in first_edges)
    normalized_second = tuple(tuple(dict.fromkeys(edge)) for edge in second_edges)
    for edge in normalized_first:
        if not edge or any(not 0 <= v < first_vertices for v in edge):
            raise ValueError("first hypergraph has an empty or invalid edge")
    for edge in normalized_second:
        if not edge or any(not 0 <= v < second_vertices for v in edge):
            raise ValueError("second hypergraph has an empty or invalid edge")
    return tuple(
        tuple(v * second_vertices + w for v in edge_h for w in edge_k)
        for edge_h in normalized_first
        for edge_k in normalized_second
    )


def disjoint_union_edges(
    first_edges: Sequence[Sequence[int]],
    first_vertices: int,
    second_edges: Sequence[Sequence[int]],
    second_vertices: int,
) -> tuple[tuple[int, ...], ...]:
    """Disjoint union of finite integer-vertex hypergraphs."""
    if first_vertices < 0 or second_vertices < 0:
        raise ValueError("vertex counts must be nonnegative")
    first = tuple(tuple(dict.fromkeys(edge)) for edge in first_edges)
    second = tuple(
        tuple(first_vertices + v for v in dict.fromkeys(edge))
        for edge in second_edges
    )
    if any(not edge for edge in first + second):
        raise ValueError("hyperedges must be nonempty")
    if any(any(not 0 <= v < first_vertices for v in edge) for edge in first):
        raise ValueError("first hypergraph has an invalid vertex")
    if any(
        any(not first_vertices <= v < first_vertices + second_vertices for v in edge)
        for edge in second
    ):
        raise ValueError("second hypergraph has an invalid vertex")
    return first + second


def polychromatic_number(edges: Sequence[Sequence[int]], vertices: int) -> int:
    """Exact polychromatic number of a small finite nonempty-edge hypergraph."""
    normalized = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    if not normalized or any(not edge for edge in normalized):
        raise ValueError("a nonempty family of nonempty edges is required")
    upper = min(len(edge) for edge in normalized)
    for messages in range(upper, 0, -1):
        if find_polychromatic_coloring(normalized, vertices, messages) is not None:
            return messages
    raise AssertionError("one color must be feasible for nonempty edges")


def transversal_number(edges: Sequence[Sequence[int]], vertices: int) -> int:
    """Exact minimum transversal size for a small finite hypergraph."""
    normalized = tuple(frozenset(edge) for edge in edges)
    if not normalized or any(not edge for edge in normalized):
        raise ValueError("a nonempty family of nonempty edges is required")
    vertex_set = tuple(range(vertices))
    if any(any(not 0 <= v < vertices for v in edge) for edge in normalized):
        raise ValueError("vertex out of range")
    for size in range(vertices + 1):
        for candidate in combinations(vertex_set, size):
            selected = set(candidate)
            if all(selected.intersection(edge) for edge in normalized):
                return size
    raise AssertionError("the full vertex set is always a transversal")

def find_polychromatic_coloring(edges: Sequence[Sequence[int]], vertices: int, messages: int) -> tuple[int, ...] | None:
    """Backtracking solver with validation before every infeasibility shortcut.

    Empty edges are valid infeasible constraints. An empty edge family has no
    coverage obligations; malformed vertex identifiers are never treated as a
    negative scientific result.
    """
    if not isinstance(vertices, int) or isinstance(vertices, bool) or vertices < 0:
        raise ValueError("vertex count must be a nonnegative integer")
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    edges = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    if any(any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < vertices for v in edge) for edge in edges):
        raise ValueError("vertices must be integer indices inside the declared universe")
    if any(len(edge) < messages for edge in edges):
        return None
    incident: list[list[int]] = [[] for _ in range(vertices)]
    for e_i, edge in enumerate(edges):
        for v in edge:
            if not 0 <= v < vertices:
                raise ValueError("vertex out of range")
            incident[v].append(e_i)
    order = sorted(range(vertices), key=lambda v: (-len(incident[v]), v))
    colors = [-1] * vertices

    def viable() -> bool:
        for edge in edges:
            used = {colors[v] for v in edge if colors[v] >= 0}
            uncolored = sum(colors[v] < 0 for v in edge)
            if messages - len(used) > uncolored:
                return False
        return True

    def search(pos: int) -> bool:
        if pos == len(order):
            return all({colors[v] for v in edge} == set(range(messages)) for edge in edges)
        v = order[pos]
        for color in range(messages):
            colors[v] = color
            if viable() and search(pos + 1):
                return True
        colors[v] = -1
        return False

    return tuple(colors) if search(0) else None


def general_exact_feasible(behavior: Partition, indistinguishability: Partition, messages: int) -> bool:
    edges = quotient_hypergraph(behavior, indistinguishability)
    return find_polychromatic_coloring(edges, len(indistinguishability), messages) is not None


def direct_general_exact_feasible(
    behavior: Partition,
    indistinguishability: Partition,
    messages: int,
) -> bool:
    """Independent exhaustive decoder search for very small finite instances.

    Unlike ``find_polychromatic_coloring``, this routine assigns labels to program
    elements directly, then separately checks operational invariance and per-behavior
    reachability of every message.  It is intentionally exponential and is used only
    as a bounded correspondence oracle.
    """
    if not isinstance(messages, int) or isinstance(messages, bool) or messages < 1:
        raise ValueError("messages must be a positive integer")
    u = _same_nonempty_universe(behavior, indistinguishability)
    items = tuple(sorted(u, key=_key))
    target = set(range(messages))
    for values in product(range(messages), repeat=len(items)):
        decoder = dict(zip(items, values, strict=True))
        if any(len({decoder[x] for x in block}) != 1 for block in indistinguishability):
            continue
        if all({decoder[x] for x in block} == target for block in behavior):
            return True
    return False


def set_partitions(items: Sequence[Element]) -> Iterator[Partition]:
    """Generate each finite set partition exactly once."""
    if not items:
        yield tuple()
        return
    first, rest = items[0], items[1:]
    for partition in set_partitions(rest):
        yield normalize_partition([{first}, *partition])
        for i in range(len(partition)):
            blocks = [set(block) for block in partition]
            blocks[i].add(first)
            yield normalize_partition(blocks)


def refinements(coarse: Partition) -> Iterator[Partition]:
    """Generate all partitions that refine a given coarse partition."""
    choices = [tuple(set_partitions(sorted(block, key=_key))) for block in coarse]
    for selected in product(*choices):
        yield normalize_partition(block for local in selected for block in local)


@dataclass(frozen=True)
class ExhaustiveSummary:
    max_universe_size: int
    behavior_partitions: int
    refinement_pairs: int
    message_instances: int
    constructive_passes: int
    impossibility_checks: int


def exhaustive_refinement_check(max_universe_size: int = 5) -> ExhaustiveSummary:
    """Exhaustively validate the finite refinement theorem through size n.

    Positive instances are independently checked by constructing and validating
    a decoder/embedder.  Negative instances are checked by the pigeonhole fact
    that one behavior class has fewer J-cells than messages; the raw manifest
    reports the exact witness counts.
    """
    b_count = pair_count = inst_count = pos_count = neg_count = 0
    for n in range(1, max_universe_size + 1):
        for behavior in set_partitions(tuple(range(n))):
            b_count += 1
            for indist in refinements(behavior):
                pair_count += 1
                capacity = exact_message_capacity(behavior, indist)
                for messages in range(1, len(indist) + 2):
                    inst_count += 1
                    if messages <= capacity:
                        decoder = construct_decoder(behavior, indist, messages)
                        embedder = construct_embedder(behavior, indist, messages, decoder)
                        ok, failures = validate_scheme(behavior, indist, messages, decoder, embedder)
                        if not ok:
                            raise AssertionError(f"constructive theorem failed: {failures}")
                        pos_count += 1
                    else:
                        cells = quotient_cells(behavior, indist)
                        if not any(len(local) < messages for local in cells):
                            raise AssertionError("missing pigeonhole witness")
                        neg_count += 1
    return ExhaustiveSummary(
        max_universe_size=max_universe_size,
        behavior_partitions=b_count,
        refinement_pairs=pair_count,
        message_instances=inst_count,
        constructive_passes=pos_count,
        impossibility_checks=neg_count,
    )

@dataclass(frozen=True)
class GeneralExhaustiveSummary:
    max_universe_size: int
    behavior_partitions: int
    operational_partitions: int
    partition_pairs: int
    message_instances: int
    feasible_instances: int
    infeasible_instances: int
    agreement_checks: int
    operational_refinement_pairs: int
    operational_monotonicity_checks: int
    behavior_refinement_pairs: int
    behavior_monotonicity_checks: int


def exhaustive_general_check(max_universe_size: int = 5) -> GeneralExhaustiveSummary:
    """Cross-check the hypergraph solver and both monotonicity laws.

    Every ordered pair of partitions on the same universe is considered, including
    crossing pairs. Message counts run from one through one beyond the number of
    operational cells. For each universe, capacities are then compared across all
    refinement-related operational and behavior partitions.
    """
    behavior_count = operational_count = pair_count = instance_count = 0
    feasible_count = infeasible_count = agreement_count = 0
    refinement_pair_count = operational_monotonicity_count = 0
    behavior_refinement_pair_count = behavior_monotonicity_count = 0
    for n in range(1, max_universe_size + 1):
        partitions = tuple(set_partitions(tuple(range(n))))
        behavior_count += len(partitions)
        operational_count += len(partitions)
        capacities: dict[tuple[Partition, Partition], int] = {}
        for behavior in partitions:
            for indist in partitions:
                pair_count += 1
                capacity = 0
                for messages in range(1, len(indist) + 2):
                    instance_count += 1
                    optimized = general_exact_feasible(behavior, indist, messages)
                    direct = direct_general_exact_feasible(behavior, indist, messages)
                    if optimized != direct:
                        raise AssertionError(
                            "general theorem correspondence failed for "
                            f"behavior={behavior!r}, J={indist!r}, messages={messages}"
                        )
                    agreement_count += 1
                    if optimized:
                        capacity = max(capacity, messages)
                        feasible_count += 1
                    else:
                        infeasible_count += 1
                capacities[(behavior, indist)] = capacity

        comparable = tuple(
            (fine, coarse)
            for fine in partitions
            for coarse in partitions
            if is_refinement(fine, coarse)
        )
        refinement_pair_count += len(comparable)
        for behavior in partitions:
            for fine, coarse in comparable:
                operational_monotonicity_count += 1
                if capacities[(behavior, coarse)] > capacities[(behavior, fine)]:
                    raise AssertionError(
                        "operational monotonicity failed for "
                        f"behavior={behavior!r}, fine={fine!r}, coarse={coarse!r}"
                    )

        behavior_refinement_pair_count += len(comparable)
        for indist in partitions:
            for fine_behavior, coarse_behavior in comparable:
                behavior_monotonicity_count += 1
                if capacities[(fine_behavior, indist)] > capacities[(coarse_behavior, indist)]:
                    raise AssertionError(
                        "behavior monotonicity failed for "
                        f"fine={fine_behavior!r}, coarse={coarse_behavior!r}, J={indist!r}"
                    )
    return GeneralExhaustiveSummary(
        max_universe_size=max_universe_size,
        behavior_partitions=behavior_count,
        operational_partitions=operational_count,
        partition_pairs=pair_count,
        message_instances=instance_count,
        feasible_instances=feasible_count,
        infeasible_instances=infeasible_count,
        agreement_checks=agreement_count,
        operational_refinement_pairs=refinement_pair_count,
        operational_monotonicity_checks=operational_monotonicity_count,
        behavior_refinement_pairs=behavior_refinement_pair_count,
        behavior_monotonicity_checks=behavior_monotonicity_count,
    )


@dataclass(frozen=True)
class AccessExhaustiveSummary:
    max_universe_size: int
    behavior_partitions: int
    operational_partitions: int
    partition_pairs: int
    access_relation_instances: int
    message_instances: int
    feasible_instances: int
    infeasible_instances: int
    agreement_checks: int
    access_inclusion_pairs: int
    access_monotonicity_checks: int


def _access_from_mask(items: Sequence[Element], mask: int) -> dict[Element, frozenset[Element]]:
    """Decode a row-major binary relation mask into an access mapping."""
    n = len(items)
    return {
        p: frozenset(q for j, q in enumerate(items) if mask & (1 << (i * n + j)))
        for i, p in enumerate(items)
    }


def _access_inclusion_masks(bits: int) -> Iterator[tuple[int, int]]:
    """Yield every ordered pair (smaller, larger) with smaller subset larger."""
    for states in product(range(3), repeat=bits):
        smaller = larger = 0
        for bit, state in enumerate(states):
            if state == 1:
                larger |= 1 << bit
            elif state == 2:
                smaller |= 1 << bit
                larger |= 1 << bit
        yield smaller, larger


def exhaustive_access_check(max_universe_size: int = 3) -> AccessExhaustiveSummary:
    """Exhaustively validate constrained-access feasibility and monotonicity.

    Through the requested universe size, this checker considers every ordered
    behavior/operational partition pair and every directed access relation.  It
    compares the quotient access-hypergraph solver with a direct program-label
    oracle for every message count, then checks every inclusion-related pair of
    access relations.  Size three already covers arbitrary crossing partitions,
    empty access rows, reflexive and non-reflexive relations, and all 512 directed
    relations on a three-element universe.
    """
    behavior_count = operational_count = partition_pair_count = 0
    access_relation_count = message_count = feasible_count = infeasible_count = 0
    agreement_count = inclusion_pair_count = monotonicity_count = 0

    for n in range(1, max_universe_size + 1):
        items = tuple(range(n))
        partitions = tuple(set_partitions(items))
        behavior_count += len(partitions)
        operational_count += len(partitions)
        masks = tuple(range(1 << (n * n)))
        comparable_masks = tuple(_access_inclusion_masks(n * n))

        for behavior in partitions:
            for indist in partitions:
                partition_pair_count += 1
                capacities: dict[int, int] = {}
                for mask in masks:
                    access_relation_count += 1
                    access = _access_from_mask(items, mask)
                    capacity = 0
                    for messages in range(1, len(indist) + 2):
                        message_count += 1
                        optimized = access_exact_feasible(behavior, indist, access, messages)
                        direct = direct_access_exact_feasible(behavior, indist, access, messages)
                        if optimized != direct:
                            raise AssertionError(
                                "access theorem correspondence failed for "
                                f"behavior={behavior!r}, J={indist!r}, "
                                f"mask={mask}, messages={messages}"
                            )
                        agreement_count += 1
                        if optimized:
                            capacity = max(capacity, messages)
                            feasible_count += 1
                        else:
                            infeasible_count += 1
                    capacities[mask] = capacity

                inclusion_pair_count += len(comparable_masks)
                for smaller, larger in comparable_masks:
                    monotonicity_count += 1
                    if capacities[smaller] > capacities[larger]:
                        raise AssertionError(
                            "access expansion monotonicity failed for "
                            f"behavior={behavior!r}, J={indist!r}, "
                            f"smaller={smaller}, larger={larger}"
                        )

    return AccessExhaustiveSummary(
        max_universe_size=max_universe_size,
        behavior_partitions=behavior_count,
        operational_partitions=operational_count,
        partition_pairs=partition_pair_count,
        access_relation_instances=access_relation_count,
        message_instances=message_count,
        feasible_instances=feasible_count,
        infeasible_instances=infeasible_count,
        agreement_checks=agreement_count,
        access_inclusion_pairs=inclusion_pair_count,
        access_monotonicity_checks=monotonicity_count,
    )

