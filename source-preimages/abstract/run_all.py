#!/usr/bin/env python3
"""Run every deterministic finite check and generate paper-facing data."""
from __future__ import annotations

import csv
import argparse
import hashlib
import json
import random
import sys
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from witness_checks import run_witness_checks, run_larger_stress_checks

from woc import (
    access_exact_feasible,
    access_hypergraph,
    direct_average_list_cover,
    deterministic_worst_source_value,
    coordinate_product_edges,
    exact_message_capacity,
    exhaustive_access_check,
    exhaustive_general_check,
    exhaustive_refinement_check,
    find_polychromatic_coloring,
    general_exact_feasible,
    guaranteed_bit_capacity,
    incidence_access_instance,
    incidence_partitions,
    max_average_list_cover,
    is_refinement,
    normalize_partition,
    polychromatic_number,
    private_recovery_value,
    quotient_hypergraph,
    shared_recovery_dual_bound,
    shared_recovery_value,
    transversal_number,
)

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(output_root: Path = ROOT) -> int:
    """Regenerate evidence separately from the retained records when requested."""
    RAW = output_root / "raw"
    GEN = output_root / "generated"
    RAW.mkdir(parents=True, exist_ok=True)
    GEN.mkdir(parents=True, exist_ok=True)

    exhaustive = exhaustive_refinement_check(max_universe_size=5)
    general_exhaustive = exhaustive_general_check(max_universe_size=5)
    access_exhaustive = exhaustive_access_check(max_universe_size=3)

    behavior = normalize_partition([range(8)])
    scenarios = [
        ("no_attack_identifies_variants", [[i] for i in range(8)]),
        ("paired_attack_orbits", [[0, 1], [2, 3], [4, 5], [6, 7]]),
        ("four_way_attack_orbits", [[0, 1, 2, 3], [4, 5, 6, 7]]),
        ("complete_semantic_closure", [range(8)]),
    ]
    capacity_rows = []
    for order, (name, blocks) in enumerate(scenarios):
        indist = normalize_partition(blocks)
        capacity_rows.append(
            {
                "order": order,
                "scenario": name,
                "program_variants": 8,
                "quotient_cells": len(indist),
                "exact_messages": exact_message_capacity(behavior, indist),
                "guaranteed_bits": guaranteed_bit_capacity(behavior, indist),
            }
        )

    # A crossing-J instance where each behavior class sees two J-cells, yet a
    # binary universal scheme is impossible: triangle edges require a proper
    # 2-coloring with both colors on every edge.
    general_behavior = normalize_partition([
        {"a0", "a1"}, {"b0", "b1"}, {"c0", "c1"}
    ])
    general_j = normalize_partition([
        {"a0", "c1"}, {"a1", "b0"}, {"b1", "c0"}
    ])
    edges = quotient_hypergraph(general_behavior, general_j)
    general = {
        "name": "triangle_crossing_indistinguishability",
        "behavior_partition": [sorted(map(str, b)) for b in general_behavior],
        "indistinguishability_partition": [sorted(map(str, b)) for b in general_j],
        "quotient_hyperedges": [list(e) for e in edges],
        "each_edge_size": [len(e) for e in edges],
        "two_message_coloring": find_polychromatic_coloring(edges, len(general_j), 2),
        "two_message_feasible": general_exact_feasible(general_behavior, general_j, 2),
    }

    # The Fano plane is a 3-uniform non-2-colorable hypergraph.  Incidence
    # realization turns it into a crossing pair of program equivalences.
    fano_edges = [
        {0, 1, 2}, {0, 3, 4}, {0, 5, 6}, {1, 3, 5},
        {1, 4, 6}, {2, 3, 6}, {2, 4, 5},
    ]
    fano_behavior, fano_j = incidence_partitions(fano_edges)
    fano = {
        "name": "fano_plane_incidence_realization",
        "program_incidences": len(set().union(*fano_behavior)),
        "behavior_classes": len(fano_behavior),
        "operational_classes": len(fano_j),
        "each_edge_size": [len(e) for e in quotient_hypergraph(fano_behavior, fano_j)],
        "two_message_feasible": general_exact_feasible(fano_behavior, fano_j, 2),
    }

    # Even with one behavior class and J equal to identity, source-dependent
    # embedding access can induce the same odd-cycle obstruction.
    access_behavior = normalize_partition([{0, 1, 2}])
    access_j = normalize_partition([{0}, {1}, {2}])
    access_relation = {
        0: {0, 1},
        1: {1, 2},
        2: {0, 2},
    }
    access_edges = access_hypergraph(access_behavior, access_j, access_relation)
    access_triangle = {
        "name": "source_dependent_access_triangle",
        "behavior_classes": len(access_behavior),
        "operational_classes": len(access_j),
        "operational_refines_behavior": is_refinement(access_j, access_behavior),
        "access_is_reflexive": all(p in access_relation[p] for p in access_relation),
        "access_hyperedges": [list(edge) for edge in access_edges],
        "each_edge_size": [len(edge) for edge in access_edges],
        "two_message_coloring": find_polychromatic_coloring(access_edges, len(access_j), 2),
        "two_message_feasible": access_exact_feasible(
            access_behavior, access_j, access_relation, 2
        ),
    }

    # The same Fano constraints can be realized with all programs behaviorally
    # equivalent and a reflexive source-dependent access relation.  Thus the
    # hard combinatorics does not require J to cross behavior.
    access_fano_behavior, access_fano_j, access_fano_relation = incidence_access_instance(
        fano_edges
    )
    access_fano_edges = access_hypergraph(
        access_fano_behavior, access_fano_j, access_fano_relation
    )
    access_fano = {
        "name": "fano_plane_access_realization",
        "program_incidences": len(set().union(*access_fano_behavior)),
        "behavior_classes": len(access_fano_behavior),
        "operational_classes": len(access_fano_j),
        "operational_refines_behavior": is_refinement(access_fano_j, access_fano_behavior),
        "access_is_reflexive": all(
            p in access_fano_relation[p] for p in access_fano_relation
        ),
        "distinct_access_hyperedges": len(set(access_fano_edges)),
        "each_edge_size": sorted({len(edge) for edge in access_fano_edges}),
        "two_message_feasible": access_exact_feasible(
            access_fano_behavior, access_fano_j, access_fano_relation, 2
        ),
    }

    triangle_edges = ((0, 1), (1, 2), (0, 2))
    triangle_square_edges = coordinate_product_edges(triangle_edges, 3, triangle_edges, 3)
    triangle_square_coloring = tuple((vertex // 3 + vertex % 3) % 3 for vertex in range(9))
    triangle_square_target = {0, 1, 2}
    if not all(
        {triangle_square_coloring[vertex] for vertex in edge} == triangle_square_target
        for edge in triangle_square_edges
    ):
        raise AssertionError("triangle-square cyclic coloring is not polychromatic")

    triangle_fourth_edges = coordinate_product_edges(
        triangle_square_edges, 9, triangle_square_edges, 9
    )

    def fourth_label(vertex: int) -> int:
        left, right = divmod(vertex, 9)
        i0, i1 = divmod(left, 3)
        i2, i3 = divmod(right, 3)
        return 3 * ((i0 + i1) % 3) + ((i2 + i3) % 3)

    fourth_target = set(range(9))
    if not all(
        {fourth_label(vertex) for vertex in edge} == fourth_target
        for edge in triangle_fourth_edges
    ):
        raise AssertionError("triangle fourth-power nine-label witness failed")


    # Average bounded-list recovery is checked by two structurally different
    # exact procedures: a cell-level list-cover optimizer and a direct program-
    # level oracle that filters each source row by behavior preservation.
    list_triangle_weights = tuple((Fraction(1, 6), Fraction(1, 6)) for _ in triangle_edges)
    list_triangle_value, list_triangle_witness = max_average_list_cover(
        triangle_edges, 3, 2, (1, 1, 1), list_triangle_weights
    )

    rng = random.Random(0x4C495354)
    list_agreements = 0
    list_trials = 54
    list_value_numerators: list[int] = []
    list_value_denominators: list[int] = []
    for _trial in range(list_trials):
        items = tuple(range(4))
        behavior_labels = [rng.randrange(1, 3) for _ in items]
        indist_labels = [rng.randrange(1, 4) for _ in items]
        trial_behavior = normalize_partition([
            {item for item, label in zip(items, behavior_labels) if label == value}
            for value in sorted(set(behavior_labels))
        ])
        trial_indist = normalize_partition([
            {item for item, label in zip(items, indist_labels) if label == value}
            for value in sorted(set(indist_labels))
        ])
        trial_b_index = {
            x: i for i, block in enumerate(trial_behavior) for x in block
        }
        trial_access = {}
        for source in items:
            row = {source}
            for output in items:
                if trial_b_index[source] == trial_b_index[output] and rng.random() < 0.55:
                    row.add(output)
            trial_access[source] = row
        trial_messages = rng.choice((2, 3))
        trial_budgets = tuple(
            rng.randrange(0, min(2, trial_messages) + 1) for _ in trial_indist
        )
        raw_weights = {
            (source, message): rng.randrange(1, 8)
            for source in items
            for message in range(trial_messages)
        }
        total_weight = sum(raw_weights.values())
        trial_weights = {
            key: Fraction(value, total_weight) for key, value in raw_weights.items()
        }
        trial_edges = access_hypergraph(trial_behavior, trial_indist, trial_access)
        trial_matrix = tuple(
            tuple(trial_weights[(source, message)] for message in range(trial_messages))
            for source in items
        )
        hyper_value, _ = max_average_list_cover(
            trial_edges,
            len(trial_indist),
            trial_messages,
            trial_budgets,
            trial_matrix,
        )
        direct_value, _ = direct_average_list_cover(
            trial_behavior,
            trial_indist,
            trial_access,
            trial_messages,
            trial_budgets,
            trial_weights,
        )
        if hyper_value != direct_value:
            raise AssertionError("list-cover optimizer and program-level oracle disagree")
        list_agreements += 1
        list_value_numerators.append(hyper_value.numerator)
        list_value_denominators.append(hyper_value.denominator)

    uniform_prior = (Fraction(1, 2), Fraction(1, 2))
    det_triangle_value, det_triangle_coloring = deterministic_worst_source_value(
        triangle_edges, 3, uniform_prior
    )
    private_triangle_value = private_recovery_value(
        triangle_edges,
        uniform_prior,
        (
            (Fraction(1), Fraction(0)),
            (Fraction(1, 2), Fraction(1, 2)),
            (Fraction(0), Fraction(1)),
        ),
    )
    nonconstant_colorings = [
        coloring
        for coloring in __import__("itertools").product((0, 1), repeat=3)
        if coloring not in {(0, 0, 0), (1, 1, 1)}
    ]
    shared_distribution = {
        coloring: Fraction(1, 6) for coloring in nonconstant_colorings
    }
    shared_triangle_value_exact = shared_recovery_value(
        triangle_edges, uniform_prior, shared_distribution
    )
    shared_triangle_dual = shared_recovery_dual_bound(
        triangle_edges,
        uniform_prior,
        (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)),
        3,
    )
    if shared_triangle_value_exact != shared_triangle_dual:
        raise AssertionError("shared triangle primal and dual certificates do not match")

    randomized_recovery = {
        "name": "bounded_list_and_worst_source_recovery",
        "average_unit_list_triangle": {
            "value": f"{list_triangle_value.numerator}/{list_triangle_value.denominator}",
            "witness": [sorted(cell_list) for cell_list in list_triangle_witness],
        },
        "correlated_heterogeneous_budget_trials": list_trials,
        "program_level_oracle_agreements": list_agreements,
        "value_fraction_numerators": list_value_numerators,
        "value_fraction_denominators": list_value_denominators,
        "worst_source_triangle": {
            "deterministic": f"{det_triangle_value.numerator}/{det_triangle_value.denominator}",
            "deterministic_witness": list(det_triangle_coloring),
            "private_witness": f"{private_triangle_value.numerator}/{private_triangle_value.denominator}",
            "shared_primal": f"{shared_triangle_value_exact.numerator}/{shared_triangle_value_exact.denominator}",
            "shared_dual": f"{shared_triangle_dual.numerator}/{shared_triangle_dual.denominator}",
        },
    }

    composition = {
        "name": "triangle_coordinate_products",
        "triangle": {
            "vertices": 3,
            "edges": len(triangle_edges),
            "polychromatic_number": polychromatic_number(triangle_edges, 3),
        },
        "square": {
            "vertices": 9,
            "edges": len(triangle_square_edges),
            "polychromatic_number": polychromatic_number(triangle_square_edges, 9),
            "transversal_number": transversal_number(triangle_square_edges, 9),
            "cyclic_coloring": list(triangle_square_coloring),
        },
        "fourth_power": {
            "vertices": 81,
            "edges": len(triangle_fourth_edges),
            "constructed_messages": 9,
            "witness_valid": True,
        },
    }

    with (GEN / "capacity_table.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(capacity_rows[0]))
        writer.writeheader()
        writer.writerows(capacity_rows)

    result = {
        "schema": "WOC_FINITE_CHECK_V7",
        "constructive_witness_checks": run_witness_checks(),
        "larger_unfiltered_stress_checks": run_larger_stress_checks(),
        "exhaustive_refinement_theorem": asdict(exhaustive),
        "exhaustive_general_theorem": asdict(general_exhaustive),
        "exhaustive_access_theorem": asdict(access_exhaustive),
        "capacity_scenarios": capacity_rows,
        "general_hypergraph_counterexample": general,
        "fano_plane_counterexample": fano,
        "access_hypergraph_counterexample": access_triangle,
        "access_fano_counterexample": access_fano,
        "randomized_recovery": randomized_recovery,
        "joint_contract_composition": composition,
    }
    result_path = RAW / "results.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    manifest = {
        "command": "python3 src/run_all.py",
        "inputs": {
            "src/woc.py": sha256(ROOT / "src" / "woc.py"),
            "src/run_all.py": sha256(ROOT / "src" / "run_all.py"),
            "src/witness_checks.py": sha256(ROOT / "src" / "witness_checks.py"),
        },
        "outputs": {
            "raw/results.json": sha256(result_path),
            "generated/capacity_table.csv": sha256(GEN / "capacity_table.csv"),
        },
        "determinism_contract": {
            "scientific_outputs_exclude_runtime_metadata": True,
            "json_keys_sorted": True,
        },
    }
    (RAW / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    stdout = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (RAW / "run_stdout.txt").write_text(stdout, encoding="utf-8", newline="\n")
    paths = [result_path, RAW / "run_manifest.json", RAW / "run_stdout.txt", GEN / "capacity_table.csv"]
    # The normalized test transcript is maintained by the release verifier;
    # it is included when present, never silently fabricated by this generator.
    if (RAW / "run_stderr.txt").exists():
        paths.append(RAW / "run_stderr.txt")
    (RAW / "SHA256SUMS").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(output_root).as_posix()}\n" for p in paths), encoding="utf-8", newline="\n"
    )
    print(stdout, end="")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT,
                        help="output root (use a separate directory to preserve retained evidence)")
    raise SystemExit(main(parser.parse_args().out.resolve()))
