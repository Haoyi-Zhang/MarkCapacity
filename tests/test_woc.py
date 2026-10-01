from pathlib import Path
from fractions import Fraction
from itertools import product
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from woc import (
    access_exact_feasible,
    access_hypergraph,
    construct_decoder,
    construct_embedder,
    coordinate_product_edges,
    direct_access_exact_feasible,
    direct_directed_access_exact_feasible,
    direct_average_list_cover,
    direct_general_exact_feasible,
    disjoint_union_edges,
    deterministic_worst_source_value,
    directed_access_exact_feasible,
    directed_access_hypergraph,
    exact_message_capacity,
    exhaustive_access_check,
    exhaustive_general_check,
    exhaustive_refinement_check,
    find_polychromatic_coloring,
    general_exact_feasible,
    guaranteed_bit_capacity,
    incidence_access_instance,
    incidence_partitions,
    is_refinement,
    join_partitions,
    max_average_list_cover,
    normalize_partition,
    polychromatic_number,
    private_recovery_value,
    product_partition,
    quotient_hypergraph,
    shared_recovery_dual_bound,
    shared_recovery_value,
    set_partitions,
    transversal_number,
    validate_scheme,
)


class WatermarkObservationalCalculusTests(unittest.TestCase):
    def test_join_and_capacity(self):
        behavior = normalize_partition([{0, 1, 2, 3}])
        detector = normalize_partition([{0, 1}, {2}, {3}])
        attacks = normalize_partition([{0}, {1, 2}, {3}])
        joined = join_partitions(detector, attacks)
        self.assertEqual(joined, normalize_partition([{0, 1, 2}, {3}]))
        self.assertEqual(exact_message_capacity(behavior, joined), 2)
        self.assertEqual(guaranteed_bit_capacity(behavior, joined), 1)

    def test_constructive_scheme(self):
        behavior = normalize_partition([{0, 1, 2, 3}, {4, 5, 6}])
        indist = normalize_partition([{0}, {1, 2}, {3}, {4, 5}, {6}])
        decoder = construct_decoder(behavior, indist, 2)
        embedder = construct_embedder(behavior, indist, 2, decoder)
        ok, failures = validate_scheme(behavior, indist, 2, decoder, embedder)
        self.assertTrue(ok, failures)

    def test_triangle_crossing_is_infeasible(self):
        behavior = normalize_partition([{"a0", "a1"}, {"b0", "b1"}, {"c0", "c1"}])
        indist = normalize_partition([{"a0", "c1"}, {"a1", "b0"}, {"b1", "c0"}])
        self.assertFalse(general_exact_feasible(behavior, indist, 2))


    def test_crossing_four_cycle_is_feasible(self):
        behavior = normalize_partition([{"a0", "a1"}, {"b0", "b1"}])
        indistinguishability = normalize_partition(
            [{"a0", "b0"}, {"a1", "b1"}]
        )
        self.assertFalse(is_refinement(indistinguishability, behavior))
        self.assertFalse(is_refinement(behavior, indistinguishability))
        self.assertEqual(
            quotient_hypergraph(behavior, indistinguishability),
            ((0, 1), (0, 1)),
        )
        self.assertTrue(
            general_exact_feasible(behavior, indistinguishability, 2)
        )
        class_complete_access = {
            "a0": {"a0", "a1"},
            "a1": {"a0", "a1"},
            "b0": {"b0", "b1"},
            "b1": {"b0", "b1"},
        }
        self.assertTrue(
            access_exact_feasible(
                behavior, indistinguishability, class_complete_access, 2
            )
        )

    def test_crossing_operational_coarsening_can_destroy_a_bit(self):
        behavior = normalize_partition([{"a0", "a1"}, {"b0", "b1"}, {"c0", "c1"}])
        fine = normalize_partition([{x} for x in {"a0", "a1", "b0", "b1", "c0", "c1"}])
        coarse = normalize_partition([{"a0", "c1"}, {"a1", "b0"}, {"b1", "c0"}])
        self.assertTrue(is_refinement(fine, coarse))
        self.assertTrue(general_exact_feasible(behavior, fine, 2))
        self.assertFalse(general_exact_feasible(behavior, coarse, 2))

    def test_crossing_behavior_refinement_can_destroy_a_bit(self):
        coarse_behavior = normalize_partition([{0, 1, 2, 3}])
        fine_behavior = normalize_partition([{0, 1}, {2, 3}])
        indist = normalize_partition([{0, 1, 2}, {3}])
        self.assertTrue(is_refinement(fine_behavior, coarse_behavior))
        self.assertTrue(general_exact_feasible(coarse_behavior, indist, 2))
        self.assertFalse(general_exact_feasible(fine_behavior, indist, 2))

    def test_incidence_realization_preserves_hyperedges(self):
        source_edges = [{"x", "y"}, {"y", "z", "w"}, {"x", "w"}]
        behavior, indist = incidence_partitions(source_edges)
        quotient_edges = quotient_hypergraph(behavior, indist)
        index_to_vertex = {
            i: next(iter(block))[1]
            for i, block in enumerate(indist)
        }
        realized = {frozenset(index_to_vertex[i] for i in edge) for edge in quotient_edges}
        self.assertEqual(realized, {frozenset(edge) for edge in source_edges})

    def test_fano_plane_crossing_is_infeasible(self):
        fano_edges = [
            {0, 1, 2}, {0, 3, 4}, {0, 5, 6}, {1, 3, 5},
            {1, 4, 6}, {2, 3, 6}, {2, 4, 5},
        ]
        behavior, indist = incidence_partitions(fano_edges)
        self.assertTrue(all(len(edge) == 3 for edge in quotient_hypergraph(behavior, indist)))
        self.assertFalse(general_exact_feasible(behavior, indist, 2))

    def test_source_dependent_access_triangle_is_infeasible(self):
        behavior = normalize_partition([{0, 1, 2}])
        indist = normalize_partition([{0}, {1}, {2}])
        access = {
            0: {0, 1},
            1: {1, 2},
            2: {0, 2},
        }
        self.assertTrue(all(p in access[p] for p in access))
        self.assertFalse(access_exact_feasible(behavior, indist, access, 2))

    def test_access_expansion_can_create_but_not_destroy_a_bit(self):
        behavior = normalize_partition([{0, 1}])
        indist = normalize_partition([{0}, {1}])
        narrow = {0: {0}, 1: {1}}
        wide = {0: {0, 1}, 1: {0, 1}}
        self.assertFalse(access_exact_feasible(behavior, indist, narrow, 2))
        self.assertTrue(access_exact_feasible(behavior, indist, wide, 2))

    def test_access_underapproximation_can_create_false_impossibility(self):
        behavior = normalize_partition([{0, 1, 2}])
        indist = normalize_partition([{0}, {1}, {2}])
        underapprox = {0: {0}, 1: {1}, 2: {2}}
        actual = {0: {0, 1, 2}, 1: {0, 1, 2}, 2: {0, 1, 2}}
        self.assertFalse(access_exact_feasible(behavior, indist, underapprox, 2))
        self.assertTrue(access_exact_feasible(behavior, indist, actual, 2))

    def test_detector_coarsening_can_create_false_impossibility(self):
        behavior = normalize_partition([{0, 1}])
        actual_detector = normalize_partition([{0}, {1}])
        weakened_detector = normalize_partition([{0, 1}])
        self.assertTrue(is_refinement(actual_detector, weakened_detector))
        self.assertTrue(general_exact_feasible(behavior, actual_detector, 2))
        self.assertFalse(general_exact_feasible(behavior, weakened_detector, 2))

    def test_attack_overapproximation_can_create_false_collapse(self):
        behavior = normalize_partition([{0, 1}])
        detector = normalize_partition([{0}, {1}])
        actual_attacks = normalize_partition([{0}, {1}])
        overapprox_attacks = normalize_partition([{0, 1}])
        actual_join = join_partitions(detector, actual_attacks)
        overapprox_join = join_partitions(detector, overapprox_attacks)
        self.assertTrue(general_exact_feasible(behavior, actual_join, 2))
        self.assertFalse(general_exact_feasible(behavior, overapprox_join, 2))

    def test_incidence_access_realization_preserves_hyperedges(self):
        source_edges = [{"x", "y"}, {"y", "z", "w"}, {"x", "w"}]
        behavior, indist, access = incidence_access_instance(source_edges)
        self.assertTrue(is_refinement(indist, behavior))
        self.assertTrue(all(p in access[p] for p in access))
        quotient_edges = access_hypergraph(behavior, indist, access)
        index_to_vertex = {
            i: next(iter(block))[1]
            for i, block in enumerate(indist)
        }
        realized = {frozenset(index_to_vertex[i] for i in edge) for edge in quotient_edges}
        self.assertEqual(realized, {frozenset(edge) for edge in source_edges})


    def test_relabeling_invariance(self):
        behavior = normalize_partition([{"a0", "a1"}, {"b0", "b1"}, {"c0", "c1"}])
        indist = normalize_partition([{"a0", "c1"}, {"a1", "b0"}, {"b1", "c0"}])
        renaming = {x: f"renamed::{i}" for i, x in enumerate(sorted({y for b in behavior for y in b}))}
        relabeled_behavior = normalize_partition([{renaming[x] for x in b} for b in behavior])
        relabeled_indist = normalize_partition([{renaming[x] for x in b} for b in indist])
        for messages in (1, 2, 3):
            self.assertEqual(
                general_exact_feasible(behavior, indist, messages),
                general_exact_feasible(relabeled_behavior, relabeled_indist, messages),
            )

    def test_duplicate_representatives_do_not_change_general_feasibility(self):
        behavior = normalize_partition([{"a0", "a1"}, {"b0", "b1"}, {"c0", "c1"}])
        indist = normalize_partition([{"a0", "c1"}, {"a1", "b0"}, {"b1", "c0"}])
        duplicate = {x: f"{x}::copy" for block in behavior for x in block}
        doubled_behavior = normalize_partition([
            set(block) | {duplicate[x] for x in block} for block in behavior
        ])
        doubled_indist = normalize_partition([
            set(block) | {duplicate[x] for x in block} for block in indist
        ])
        for messages in (1, 2, 3):
            self.assertEqual(
                general_exact_feasible(behavior, indist, messages),
                general_exact_feasible(doubled_behavior, doubled_indist, messages),
            )

    def test_disjoint_union_feasibility_is_componentwise(self):
        feasible_behavior = normalize_partition([{"d0", "d1"}, {"e0", "e1"}])
        feasible_indist = normalize_partition([{"d0", "e1"}, {"d1", "e0"}])
        impossible_behavior = normalize_partition([{"a0", "a1"}, {"b0", "b1"}, {"c0", "c1"}])
        impossible_indist = normalize_partition([{"a0", "c1"}, {"a1", "b0"}, {"b1", "c0"}])
        union_behavior = normalize_partition(list(feasible_behavior) + list(impossible_behavior))
        union_indist = normalize_partition(list(feasible_indist) + list(impossible_indist))
        for messages in (1, 2, 3):
            expected = (
                general_exact_feasible(feasible_behavior, feasible_indist, messages)
                and general_exact_feasible(impossible_behavior, impossible_indist, messages)
            )
            self.assertEqual(expected, general_exact_feasible(union_behavior, union_indist, messages))

    def test_held_out_random_instances_agree_with_program_level_oracles(self):
        rng = random.Random(0x574F43)
        for _trial in range(40):
            items = tuple(range(5))
            behavior_labels = [rng.randrange(1, 4) for _ in items]
            indist_labels = [rng.randrange(1, 5) for _ in items]
            behavior = normalize_partition([
                {item for item, label in zip(items, behavior_labels) if label == value}
                for value in sorted(set(behavior_labels))
            ])
            indist = normalize_partition([
                {item for item, label in zip(items, indist_labels) if label == value}
                for value in sorted(set(indist_labels))
            ])
            b_index = {x: i for i, block in enumerate(behavior) for x in block}
            access = {}
            for p0 in items:
                candidates = {p0}
                for q0 in items:
                    if b_index[p0] == b_index[q0] and rng.random() < 0.45:
                        candidates.add(q0)
                access[p0] = candidates
            for messages in (1, 2, 3):
                self.assertEqual(
                    direct_general_exact_feasible(behavior, indist, messages),
                    general_exact_feasible(behavior, indist, messages),
                )
                self.assertEqual(
                    direct_access_exact_feasible(behavior, indist, access, messages),
                    access_exact_feasible(behavior, indist, access, messages),
                )


    def test_semantic_product_corresponds_to_hypergraph_product(self):
        first_behavior = normalize_partition([{"a0", "a1"}, {"b0", "b1"}, {"c0", "c1"}])
        first_indist = normalize_partition([{"a0", "c1"}, {"a1", "b0"}, {"b1", "c0"}])
        second_behavior = normalize_partition([{0, 1, 2, 3}])
        second_indist = normalize_partition([{0, 1}, {2}, {3}])

        product_behavior = product_partition(first_behavior, second_behavior)
        product_indist = product_partition(first_indist, second_indist)
        realized = quotient_hypergraph(product_behavior, product_indist)
        expected = coordinate_product_edges(
            quotient_hypergraph(first_behavior, first_indist),
            len(first_indist),
            quotient_hypergraph(second_behavior, second_indist),
            len(second_indist),
        )
        self.assertEqual({frozenset(edge) for edge in realized}, {frozenset(edge) for edge in expected})

    def test_joint_capacity_lower_bound_on_small_hypergraphs(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        two_colorable = ((0, 1), (2, 3))
        examples = [(triangle, 3), (two_colorable, 4)]
        for first_edges, first_vertices in examples:
            for second_edges, second_vertices in examples:
                product_edges = coordinate_product_edges(
                    first_edges, first_vertices, second_edges, second_vertices
                )
                self.assertGreaterEqual(
                    polychromatic_number(product_edges, first_vertices * second_vertices),
                    polychromatic_number(first_edges, first_vertices)
                    * polychromatic_number(second_edges, second_vertices),
                )

    def test_refinement_product_capacity_is_exactly_multiplicative(self):
        first_behavior = normalize_partition([{0, 1, 2, 3}])
        first_indist = normalize_partition([{0, 1}, {2, 3}])
        second_behavior = normalize_partition([{"a", "b", "c", "d", "e", "f"}])
        second_indist = normalize_partition([{"a", "b"}, {"c", "d"}, {"e", "f"}])
        product_behavior = product_partition(first_behavior, second_behavior)
        product_indist = product_partition(first_indist, second_indist)
        self.assertEqual(exact_message_capacity(first_behavior, first_indist), 2)
        self.assertEqual(exact_message_capacity(second_behavior, second_indist), 3)
        self.assertEqual(exact_message_capacity(product_behavior, product_indist), 6)

    def test_triangle_square_has_exact_capacity_three(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        square = coordinate_product_edges(triangle, 3, triangle, 3)
        self.assertEqual(len(square), 9)
        self.assertEqual(polychromatic_number(square, 9), 3)
        self.assertEqual(transversal_number(square, 9), 3)

    def test_triangle_fourth_power_has_nine_label_witness(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        square = coordinate_product_edges(triangle, 3, triangle, 3)
        fourth = coordinate_product_edges(square, 9, square, 9)
        self.assertEqual(len(fourth), 81)
        self.assertEqual(9 * 9, 81)

        def label(vertex: int) -> int:
            left, right = divmod(vertex, 9)
            i0, i1 = divmod(left, 3)
            i2, i3 = divmod(right, 3)
            return 3 * ((i0 + i1) % 3) + ((i2 + i3) % 3)

        target = set(range(9))
        self.assertTrue(all({label(vertex) for vertex in edge} == target for edge in fourth))

    def test_disjoint_alternative_capacity_is_component_minimum(self):
        two_colorable = ((0, 1), (2, 3))
        triangle = ((0, 1), (1, 2), (0, 2))
        union = disjoint_union_edges(two_colorable, 4, triangle, 3)
        self.assertEqual(polychromatic_number(two_colorable, 4), 2)
        self.assertEqual(polychromatic_number(triangle, 3), 1)
        self.assertEqual(polychromatic_number(union, 7), 1)


    def test_average_unit_list_triangle_value_is_five_sixths(self):
        edges = ((0, 1), (1, 2), (0, 2))
        weights = tuple((Fraction(1, 6), Fraction(1, 6)) for _ in edges)
        value, witness = max_average_list_cover(edges, 3, 2, (1, 1, 1), weights)
        self.assertEqual(value, Fraction(5, 6))
        self.assertEqual(len(witness), 3)

    def test_heterogeneous_local_list_budget_bound_is_tight(self):
        edges = ((0, 1, 2),)
        prior = ((Fraction(2, 5), Fraction(3, 10), Fraction(1, 5), Fraction(1, 10)),)
        value, witness = max_average_list_cover(edges, 3, 4, (1, 0, 1), prior)
        self.assertEqual(value, Fraction(7, 10))
        self.assertEqual(sum(len(cell_list) for cell_list in witness), 2)

    def test_correlated_list_law_agrees_with_program_level_oracle(self):
        behavior = normalize_partition([{0, 1, 2}])
        indist = normalize_partition([{0}, {1}, {2}])
        access = {0: {0, 1}, 1: {1, 2}, 2: {0, 2}}
        matrix = (
            (Fraction(4, 18), Fraction(1, 18), Fraction(1, 18)),
            (Fraction(1, 18), Fraction(4, 18), Fraction(1, 18)),
            (Fraction(1, 18), Fraction(1, 18), Fraction(4, 18)),
        )
        edges = access_hypergraph(behavior, indist, access)
        hyper_value, _ = max_average_list_cover(edges, 3, 3, (1, 1, 1), matrix)
        items = tuple(sorted({0, 1, 2}))
        weights = {
            (source, message): matrix[source][message]
            for source in items
            for message in range(3)
        }
        direct_value, _ = direct_average_list_cover(
            behavior, indist, access, 3, (1, 1, 1), weights
        )
        self.assertEqual(hyper_value, direct_value)
        self.assertLess(hyper_value, 1)

    def test_one_source_list_bound_covers_most_likely_messages(self):
        value, witness = max_average_list_cover(
            ((0, 1),),
            2,
            4,
            (1, 1),
            ((Fraction(1, 2), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8)),),
        )
        self.assertEqual(value, Fraction(3, 4))
        covered = witness[0] | witness[1]
        self.assertEqual(covered, frozenset({0, 1}))

    def test_unit_list_perfect_recovery_matches_polychromatic_feasibility(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        square = ((0, 1), (1, 2), (2, 3), (3, 0))
        triangle_weights = tuple((Fraction(1, 6), Fraction(1, 6)) for _ in triangle)
        square_weights = tuple((Fraction(1, 8), Fraction(1, 8)) for _ in square)
        triangle_value, _ = max_average_list_cover(
            triangle, 3, 2, (1, 1, 1), triangle_weights
        )
        square_value, _ = max_average_list_cover(
            square, 4, 2, (1, 1, 1, 1), square_weights
        )
        self.assertLess(triangle_value, 1)
        self.assertEqual(square_value, 1)
        self.assertFalse(find_polychromatic_coloring(triangle, 3, 2))
        self.assertIsNotNone(find_polychromatic_coloring(square, 4, 2))

    def test_program_level_list_oracle_filters_outputs_by_behavior(self):
        behavior = normalize_partition([{"a", "b"}, {"c", "d"}])
        indist = normalize_partition([{"a", "c"}, {"b"}, {"d"}])
        access = {
            "a": {"a", "b", "c"},
            "b": {"a", "b", "d"},
            "c": {"a", "c", "d"},
            "d": {"b", "c", "d"},
        }
        items = tuple(sorted({"a", "b", "c", "d"}))
        weights = {
            (source, message): Fraction(1, 8)
            for source in items
            for message in range(2)
        }
        edges = access_hypergraph(behavior, indist, access)
        matrix = tuple(tuple(weights[(source, message)] for message in range(2)) for source in items)
        hyper_value, _ = max_average_list_cover(edges, len(indist), 2, (1, 1, 1), matrix)
        direct_value, _ = direct_average_list_cover(
            behavior, indist, access, 2, (1, 1, 1), weights
        )
        self.assertEqual(hyper_value, direct_value)

    def test_held_out_correlated_list_instances_agree_with_direct_oracle(self):
        rng = random.Random(0x4C495354)
        for _trial in range(12):
            items = tuple(range(4))
            behavior_labels = [rng.randrange(1, 3) for _ in items]
            indist_labels = [rng.randrange(1, 4) for _ in items]
            behavior = normalize_partition([
                {item for item, label in zip(items, behavior_labels) if label == value}
                for value in sorted(set(behavior_labels))
            ])
            indist = normalize_partition([
                {item for item, label in zip(items, indist_labels) if label == value}
                for value in sorted(set(indist_labels))
            ])
            b_index = {x: i for i, block in enumerate(behavior) for x in block}
            access = {}
            for source in items:
                row = {source}
                for output in items:
                    if b_index[source] == b_index[output] and rng.random() < 0.55:
                        row.add(output)
                access[source] = row
            messages = rng.choice((2, 3))
            budgets = tuple(rng.randrange(0, min(2, messages) + 1) for _ in indist)
            raw = {
                (source, message): rng.randrange(1, 8)
                for source in items
                for message in range(messages)
            }
            total = sum(raw.values())
            weights = {key: Fraction(value, total) for key, value in raw.items()}
            edges = access_hypergraph(behavior, indist, access)
            matrix = tuple(
                tuple(weights[(source, message)] for message in range(messages))
                for source in items
            )
            hyper_value, _ = max_average_list_cover(
                edges, len(indist), messages, budgets, matrix
            )
            direct_value, _ = direct_average_list_cover(
                behavior, indist, access, messages, budgets, weights
            )
            self.assertEqual(hyper_value, direct_value)


    def test_directed_preservation_compiler_example_matches_direct_oracle(self):
        sources = ("s_ab", "s_a")
        targets = normalize_partition([{"t_a"}, {"t_b"}])
        preservation = {
            "s_ab": {"t_a", "t_b"},
            "s_a": {"t_a"},
        }
        access = {
            "s_ab": {"t_a", "t_b"},
            "s_a": {"t_a"},
        }
        edges = directed_access_hypergraph(sources, targets, preservation, access)
        self.assertEqual(edges, ((0,), (0, 1)))
        self.assertFalse(
            directed_access_exact_feasible(sources, targets, preservation, access, 2)
        )
        self.assertEqual(
            directed_access_exact_feasible(sources, targets, preservation, access, 2),
            direct_directed_access_exact_feasible(
                sources, targets, preservation, access, 2
            ),
        )

        supported = ("s_ab",)
        self.assertTrue(
            directed_access_exact_feasible(supported, targets, preservation, access, 2)
        )
        self.assertEqual(
            directed_access_exact_feasible(supported, targets, preservation, access, 2),
            direct_directed_access_exact_feasible(
                supported, targets, preservation, access, 2
            ),
        )

    def test_dual_role_rewrite_never_increases_small_capacity(self):
        items = (0, 1, 2)
        behavior = normalize_partition([items])
        operational_partitions = tuple(set_partitions(items))
        off_diagonal = tuple((p, q) for p in items for q in items if p != q)

        for operational in operational_partitions:
            for mask in range(1 << len(off_diagonal)):
                access = {p: {p} for p in items}
                for bit, (p, q) in enumerate(off_diagonal):
                    if mask & (1 << bit):
                        access[p].add(q)
                for source, target in off_diagonal:
                    rewrite_partition = normalize_partition(
                        [{source, target}] + [{x} for x in items if x not in {source, target}]
                    )
                    coarser = join_partitions(operational, rewrite_partition)
                    expanded = {p: set(row) for p, row in access.items()}
                    expanded[source].add(target)
                    for messages in (1, 2, 3):
                        new_feasible = access_exact_feasible(
                            behavior, coarser, expanded, messages
                        )
                        old_feasible = access_exact_feasible(
                            behavior, operational, access, messages
                        )
                        self.assertFalse(new_feasible and not old_feasible)

    def test_deterministic_worst_source_triangle_value(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        value, _ = deterministic_worst_source_value(
            triangle, 3, (Fraction(1, 2), Fraction(1, 2))
        )
        self.assertEqual(value, Fraction(1, 2))

    def test_private_triangle_witness_has_value_three_quarters(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        q = (
            (Fraction(1), Fraction(0)),
            (Fraction(1, 2), Fraction(1, 2)),
            (Fraction(0), Fraction(1)),
        )
        value = private_recovery_value(
            triangle, (Fraction(1, 2), Fraction(1, 2)), q
        )
        self.assertEqual(value, Fraction(3, 4))

    def test_shared_triangle_primal_witness_has_value_five_sixths(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        nonconstant = [
            coloring
            for coloring in product((0, 1), repeat=3)
            if coloring not in {(0, 0, 0), (1, 1, 1)}
        ]
        distribution = {coloring: Fraction(1, 6) for coloring in nonconstant}
        value = shared_recovery_value(
            triangle, (Fraction(1, 2), Fraction(1, 2)), distribution
        )
        self.assertEqual(value, Fraction(5, 6))

    def test_shared_triangle_dual_certificate_matches_primal(self):
        triangle = ((0, 1), (1, 2), (0, 2))
        bound = shared_recovery_dual_bound(
            triangle,
            (Fraction(1, 2), Fraction(1, 2)),
            (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)),
            3,
        )
        self.assertEqual(bound, Fraction(5, 6))

    def test_prior_aware_refinement_closed_form(self):
        edges = ((0, 1), (2, 3, 4))
        prior = (Fraction(1, 2), Fraction(1, 3), Fraction(1, 6))
        value, _ = deterministic_worst_source_value(edges, 5, prior)
        self.assertEqual(value, Fraction(5, 6))

    def test_small_exhaustive_refinement_check(self):
        result = exhaustive_refinement_check(4)
        self.assertGreater(result.message_instances, 0)
        self.assertGreater(result.constructive_passes, 0)
        self.assertGreater(result.impossibility_checks, 0)

    def test_small_exhaustive_general_check(self):
        result = exhaustive_general_check(4)
        self.assertGreater(result.partition_pairs, 0)
        self.assertGreater(result.feasible_instances, 0)
        self.assertGreater(result.infeasible_instances, 0)
        self.assertEqual(result.agreement_checks, result.message_instances)
        self.assertGreater(result.operational_refinement_pairs, 0)
        self.assertGreater(result.operational_monotonicity_checks, 0)
        self.assertGreater(result.behavior_refinement_pairs, 0)
        self.assertGreater(result.behavior_monotonicity_checks, 0)

    def test_small_exhaustive_access_check(self):
        result = exhaustive_access_check(3)
        self.assertGreater(result.access_relation_instances, 0)
        self.assertGreater(result.feasible_instances, 0)
        self.assertGreater(result.infeasible_instances, 0)
        self.assertEqual(result.agreement_checks, result.message_instances)
        self.assertGreater(result.access_inclusion_pairs, 0)
        self.assertEqual(result.access_inclusion_pairs, result.access_monotonicity_checks)


if __name__ == "__main__":
    unittest.main()
