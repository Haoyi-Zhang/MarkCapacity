"""Independent input-domain and source-output witness regressions."""
from fractions import Fraction
from itertools import product
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from witness_checks import run_larger_stress_checks
from woc import (normalize_partition, validate_scheme, construct_decoder, construct_embedder,
                 construct_access_scheme, validate_access_scheme,
                 find_polychromatic_coloring, access_exact_feasible,
                 direct_access_exact_feasible, general_exact_feasible,
                 direct_general_exact_feasible, directed_access_exact_feasible,
                 direct_directed_access_exact_feasible, max_average_list_cover,
                 direct_average_list_cover, deterministic_worst_source_value,
                 shared_recovery_dual_bound, set_partitions)


class WitnessBoundaryTests(unittest.TestCase):
    def test_none_is_a_legal_program(self):
        p = normalize_partition([{None}])
        self.assertEqual(validate_scheme(p, p, 1, {None: 0}, {(None, 0): None}), (True, []))

    def test_invalid_message_cardinality_is_not_a_scheme(self):
        p = normalize_partition([{0}])
        for messages in (0, -1, True, 1.5):
            with self.subTest(messages=messages):
                self.assertFalse(validate_scheme(p, p, messages, {0: 0}, {})[0])
                with self.assertRaises(ValueError):
                    construct_decoder(p, p, messages)
                with self.assertRaises(ValueError):
                    construct_embedder(p, p, messages)


    def test_direct_oracles_reject_noninteger_cardinalities(self):
        p = normalize_partition([{0}])
        directed_sources = ('s',)
        preservation = {'s': {0}}
        access = {'s': {0}}
        for messages in (0, -1, True, 1.5):
            with self.subTest(messages=messages):
                with self.assertRaises(ValueError):
                    direct_general_exact_feasible(p, p, messages)
                with self.assertRaises(ValueError):
                    direct_access_exact_feasible(p, p, {0: {0}}, messages)
                with self.assertRaises(ValueError):
                    direct_directed_access_exact_feasible(
                        directed_sources, p, preservation, access, messages
                    )

    def test_list_and_recovery_inputs_are_type_checked(self):
        p = normalize_partition([{0}])
        weights = ((Fraction(1),),)
        for messages in (0, -1, True, 1.5):
            with self.subTest(messages=messages):
                with self.assertRaises(ValueError):
                    max_average_list_cover(((0,),), 1, messages, (1,), weights)
                with self.assertRaises(ValueError):
                    direct_average_list_cover(p, p, {0: {0}}, messages, (1,), {(0, 0): 1})
        for budget in (-1, True, 1.5):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    max_average_list_cover(((0,),), 1, 1, (budget,), weights)
                with self.assertRaises(ValueError):
                    direct_average_list_cover(p, p, {0: {0}}, 1, (budget,), {(0, 0): 1})
        for vertices in (-1, True, 1.5):
            with self.subTest(vertices=vertices):
                with self.assertRaises(ValueError):
                    deterministic_worst_source_value(((0,),), vertices, (Fraction(1),))

    def test_larger_random_instances_match_independent_oracles(self):
        self.assertEqual(
            run_larger_stress_checks(),
            {
                'instances': 240,
                'general_oracle_agreements': 240,
                'access_oracle_agreements': 240,
                'positive_access_instances': 13,
                'negative_access_instances': 227,
                'validated_positive_witnesses': 13,
            },
        )

    def test_bad_witnesses_return_diagnostics(self):
        p = normalize_partition([{0}])
        cases = [({}, {(0, 0): 0}), ({0: 0}, {}), ({0: 0}, {(0, 0): 17}),
                 ({0: 0}, {(0, 0): []}), ({0: 2}, {(0, 0): 0}),
                 ({0: 0}, {(0, 0): 0, (9, 0): 0})]
        for decoder, embedder in cases:
            with self.subTest(decoder=decoder, embedder=embedder):
                ok, reasons = validate_scheme(p, p, 1, decoder, embedder)
                self.assertFalse(ok)
                self.assertTrue(reasons)

    def test_empty_supplied_decoder_is_not_replaced(self):
        p = normalize_partition([{0}])
        with self.assertRaises(ValueError):
            construct_embedder(p, p, 1, {})
        behavior = normalize_partition([{0, 1}])
        with self.assertRaises(ValueError):
            construct_embedder(behavior, behavior, 2, {0: 0, 1: 1})

    def test_invalid_hypergraph_precedes_cardinality_shortcut(self):
        for edges, vertices, messages in [(((9,),), 1, 2), (((-1,),), 1, 2),
                                           (((0.5,),), 1, 2), (((0,),), -1, 2),
                                           (((0,),), 1, 0)]:
            with self.subTest(edges=edges, vertices=vertices, messages=messages):
                with self.assertRaises(ValueError):
                    find_polychromatic_coloring(edges, vertices, messages)
        self.assertIsNone(find_polychromatic_coloring(((),), 1, 1))
        self.assertEqual(find_polychromatic_coloring((), 0, 1), ())

    def test_dual_certificate_rejects_illegal_vertex_indices(self):
        for edges in (((-1,),), ((2,),), ((0.5,),), ((),)):
            with self.subTest(edges=edges):
                with self.assertRaises(ValueError):
                    shared_recovery_dual_bound(edges, (Fraction(1, 2), Fraction(1, 2)), (1,), 2)

    def test_access_certificate_checks_each_source_not_pooled_outputs(self):
        b = normalize_partition([{None, 'x'}]); j = normalize_partition([{None}, {'x'}])
        access = {None: {None}, 'x': {'x'}}
        decoder = {None: 0, 'x': 1}
        embedder = {(p, m): (None if m == 0 else 'x') for p in (None, 'x') for m in (0, 1)}
        self.assertTrue(validate_scheme(b, j, 2, decoder, embedder)[0])
        self.assertFalse(validate_access_scheme(b, j, access, 2, decoder, embedder)[0])

    def test_extracted_witnesses_match_direct_oracle_exhaustively(self):
        items = (None, 'x')
        partitions = list(set_partitions(items))
        count = 0
        for b, j, mask, messages in product(partitions, partitions, range(16), (1, 2)):
            access = {p: {q for k, q in enumerate(items) if mask & (1 << (i*2+k))} for i, p in enumerate(items)}
            feasible = direct_access_exact_feasible(b, j, access, messages)
            if feasible:
                decoder, embedder = construct_access_scheme(b, j, access, messages)
                self.assertEqual(validate_access_scheme(b, j, access, messages, decoder, embedder), (True, []))
            else:
                with self.assertRaises(ValueError):
                    construct_access_scheme(b, j, access, messages)
            count += 1
        self.assertEqual(count, 128)

    def test_unfiltered_generated_witness_cases(self):
        rng = random.Random(0x5749544E)
        items = (None, 'x', ('tag', 2))
        partitions = list(set_partitions(items))
        for _ in range(192):
            b, j = rng.choice(partitions), rng.choice(partitions)
            access = {p: {q for q in items if rng.getrandbits(1)} for p in items}
            messages = rng.choice((1, 2, 3))
            feasible = direct_access_exact_feasible(b, j, access, messages)
            if feasible:
                d, e = construct_access_scheme(b, j, access, messages)
                self.assertTrue(validate_access_scheme(b, j, access, messages, d, e)[0])
            else:
                with self.assertRaises(ValueError):
                    construct_access_scheme(b, j, access, messages)

    def test_single_use_access_iterators_are_supported(self):
        b = normalize_partition([{None, 'x'}]); j = normalize_partition([{None}, {'x'}])
        access = {None: iter((None, 'x')), 'x': iter((None, 'x'))}
        d, e = construct_access_scheme(b, j, access, 2)
        self.assertTrue(validate_access_scheme(b, j, {p: {None, 'x'} for p in (None, 'x')}, 2, d, e)[0])

if __name__ == '__main__':
    unittest.main()
