"""Owned pure arithmetic model: at most one commutation per insertion.

The syntax, interpreter, local rewrites and attack closure precede the incidence
translation. No input hypergraph is encoded. The syndrome labeling is the
standard binary Hamming construction, used as a bounded rewrite selector.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Iterable

from woc import join_partitions, normalize_partition


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Lit:
    value: int


@dataclass(frozen=True)
class Add:
    left: Var | Lit
    right: Var | Lit


@dataclass(frozen=True)
class Return:
    expression: Var | Add


@dataclass(frozen=True)
class Let:
    name: str
    expression: Add
    body: Return


@dataclass(frozen=True)
class Procedure:
    # Tuple components have separate local scopes; no component calls another.
    components: tuple[Return | Let, ...]


def _natural(value: int, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def make_procedure(n: int, order: int = 0, naming: int = 0) -> Procedure:
    n = _natural(n, "sites")
    for value in (order, naming):
        if type(value) is not int or not 0 <= value < (1 << n):
            raise ValueError("order and naming must be n-bit integer masks")
    terms = []
    for i in range(n):
        operands = (Var(f"x{i}"), Lit(1))
        if order & (1 << i):
            operands = operands[::-1]
        expression = Add(*operands)
        terms.append(Let("t", expression, Return(Var("t")))
                     if naming & (1 << i) else Return(expression))
    return Procedure(tuple(terms))


def shape(procedure: Procedure) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Validate the finite fragment and read actual operand/naming syntax."""
    if not isinstance(procedure, Procedure) or type(procedure.components) is not tuple:
        raise ValueError("expected a procedure with tuple components")
    orders, names = [], []
    for i, term in enumerate(procedure.components):
        if isinstance(term, Let):
            if term.name != "t" or term.body != Return(Var("t")):
                raise ValueError("temporary must be local and returned unchanged")
            expression = term.expression
            names.append(1)
        elif isinstance(term, Return):
            expression = term.expression
            names.append(0)
        else:
            raise ValueError("component must be return or local let-return")
        if not isinstance(expression, Add):
            raise ValueError("component must add its own input and literal one")
        # Lit(True) must not silently stand for the grammar's integer literal 1.
        operands = (expression.left, expression.right)
        if any(isinstance(x, Lit) and type(x.value) is not int for x in operands):
            raise ValueError("integer literal required")
        if operands == (Var(f"x{i}"), Lit(1)):
            orders.append(0)
        elif operands == (Lit(1), Var(f"x{i}")):
            orders.append(1)
        else:
            raise ValueError("component must add its own input and literal one")
    return tuple(orders), tuple(names)


def evaluate(procedure: Procedure, inputs: tuple[int, ...]) -> tuple[int, ...]:
    """Return-value semantics on Boolean arguments, with mathematical addition."""
    shape(procedure)
    if len(inputs) != len(procedure.components) or any(type(x) is not int or x not in (0, 1)
                                                     for x in inputs):
        raise ValueError("one Boolean integer argument is required per component")
    environment = {f"x{i}": x for i, x in enumerate(inputs)}

    def expression_value(expression, env):
        if isinstance(expression, Var):
            return env[expression.name]
        if isinstance(expression, Lit):
            return expression.value
        return expression_value(expression.left, env) + expression_value(expression.right, env)

    values = []
    for term in procedure.components:
        local = environment.copy()
        if isinstance(term, Let):
            local[term.name] = expression_value(term.expression, local)
            term = term.body
        values.append(expression_value(term.expression, local))
    return tuple(values)


def _change(procedure: Procedure, site: int, *, commute: bool = False) -> Procedure:
    term = procedure.components[site]
    expression = term.expression
    if commute:
        expression = Add(expression.right, expression.left)
        changed = replace(term, expression=expression)
    else:
        changed = (Return(expression) if isinstance(term, Let)
                   else Let("t", expression, Return(Var("t"))))
    terms = list(procedure.components)
    terms[site] = changed
    return Procedure(tuple(terms))


def rewrite_steps(procedure: Procedure):
    """Naming steps cost zero; an operand commutation costs one."""
    shape(procedure)
    for i in range(len(procedure.components)):
        yield _change(procedure, i), 0
        yield _change(procedure, i, commute=True), 1


def reachable(procedure: Procedure) -> frozenset[Procedure]:
    """Compose naming steps, but spend at most one commutation in the whole run."""
    shape(procedure)
    seen = {(procedure, 0)}
    pending = [(procedure, 0)]
    while pending:
        current, spent = pending.pop()
        for target, cost in rewrite_steps(current):
            state = (target, spent + cost)
            if state[1] <= 1 and state not in seen:
                seen.add(state)
                pending.append(state)
    return frozenset(target for target, _ in seen)


def normalized_sites(n: int, sites: Iterable[int]) -> frozenset[int]:
    supplied = tuple(sites)
    if any(type(i) is not int or not 0 <= i < n for i in supplied):
        raise ValueError("normalization sites must be integer indices in the procedure")
    return frozenset(supplied)


def attack_targets(procedure: Procedure, sites: Iterable[int]) -> tuple[Procedure, ...]:
    """Temporary elimination and one-way right-to-left normalization at sites."""
    orders, names = shape(procedure)
    sites = normalized_sites(len(orders), sites)
    return tuple(_change(procedure, i) for i, named in enumerate(names) if named) + tuple(
        _change(procedure, i, commute=True) for i in sorted(sites) if orders[i])


def finite_instance(n: int, sites: Iterable[int] = ()):
    """Derive partitions from evaluation and detector/attack generators, then access.

    This exhaustive construction is for small models, not a scalable compiler.
    """
    n = _natural(n, "sites")
    sites = normalized_sites(n, sites)
    programs = tuple(make_procedure(n, b, t) for b, t in product(range(1 << n), repeat=2))
    inputs = tuple(product((0, 1), repeat=n))
    behavior_groups, detector_groups = {}, {}
    for p in programs:
        behavior_groups.setdefault(tuple(evaluate(p, x) for x in inputs), set()).add(p)
        detector_groups.setdefault(shape(p), set()).add(p)
    behavior = normalize_partition(behavior_groups.values())
    detector = normalize_partition(detector_groups.values())
    # Each generating attack pair is made a block in its own partition.
    operational = detector
    for p in programs:
        for q in attack_targets(p, sites):
            pair_partition = normalize_partition([{p, q}, *({x} for x in programs if x not in (p, q))])
            operational = join_partitions(operational, pair_partition)
    return behavior, operational, {p: reachable(p) for p in programs}


def syndrome(procedure: Procedure, sites: Iterable[int] = ()) -> int:
    orders, _ = shape(procedure)
    sites = normalized_sites(len(orders), sites)
    free = tuple(i for i in range(len(orders)) if i not in sites)
    r = (len(free) + 1).bit_length() - 1
    label = 0
    for column, site in enumerate(free[:(1 << r) - 1], start=1):
        if orders[site]:
            label ^= column
    return label


def embed(procedure: Procedure, message: int, sites: Iterable[int] = ()) -> Procedure:
    """Standard syndrome difference selects zero or one legal commutation."""
    orders, _ = shape(procedure)
    sites = normalized_sites(len(orders), sites)
    free = tuple(i for i in range(len(orders)) if i not in sites)
    messages = 1 << ((len(free) + 1).bit_length() - 1)
    if type(message) is not int or not 0 <= message < messages:
        raise ValueError("message outside the syndrome alphabet")
    difference = syndrome(procedure, sites) ^ message
    return procedure if difference == 0 else _change(procedure, free[difference - 1], commute=True)
