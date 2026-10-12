"""Concrete semantic translation and known syndrome-selector checks."""
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import arithmetic_language as language
import woc


class ArithmeticLanguageTests(unittest.TestCase):
    def test_interpreter_all_boolean_inputs_through_three_sites(self):
        count = 0
        for n in range(4):
            for order, naming in product(range(1 << n), repeat=2):
                p = language.make_procedure(n, order, naming)
                for inputs in product((0, 1), repeat=n):
                    self.assertEqual(language.evaluate(p, inputs), tuple(x + 1 for x in inputs))
                    count += 1
        self.assertEqual(count, 585)

    def test_generated_access_matches_budget_not_transitive_order_closure(self):
        count = 0
        for n in range(4):
            for order, naming in product(range(1 << n), repeat=2):
                p = language.make_procedure(n, order, naming)
                actual = language.reachable(p)
                expected = {language.make_procedure(n, b, t)
                            for b, t in product(range(1 << n), repeat=2)
                            if (b ^ order).bit_count() <= 1}
                self.assertEqual(actual, expected)
                count += 1
        self.assertEqual(count, 85)
        self.assertNotIn(language.make_procedure(2, 3), language.reachable(language.make_procedure(2)))

    def test_semantic_cells_and_access_edges_for_all_small_attack_subsets(self):
        instances = rows = 0
        for n in range(4):
            for mask in range(1 << n):
                sites = tuple(i for i in range(n) if mask & (1 << i))
                free = tuple(i for i in range(n) if i not in sites)
                behavior, operational, access = language.finite_instance(n, sites)
                self.assertEqual(len(behavior), 1)
                cell_of = woc.block_index(operational)
                key_of = {p: tuple(language.shape(p)[0][i] for i in free) for p in access}
                self.assertEqual(len(operational), 1 << len(free))
                for p, q in product(access, repeat=2):
                    self.assertEqual(cell_of[p] == cell_of[q], key_of[p] == key_of[q])
                edges = woc.access_hypergraph(behavior, operational, access)
                actual_edges = {frozenset(key_of[next(iter(operational[v]))] for v in edge)
                                for edge in edges}
                expected_edges = {frozenset(t for t in product((0, 1), repeat=len(free))
                                            if sum(x != y for x, y in zip(s, t)) <= 1)
                                  for s in product((0, 1), repeat=len(free))}
                self.assertEqual(actual_edges, expected_edges)
                instances += 1
                rows += len(access)
        self.assertEqual((instances, rows), (15, 585))

    def test_exact_small_capacities_against_complete_label_enumeration(self):
        # No incremental search in this second route; label each cube vertex.
        for n, expected in enumerate((1, 2, 2, 4)):
            behavior, operational, access = language.finite_instance(n)
            edges = tuple(set(e) for e in woc.access_hypergraph(behavior, operational, access))
            direct = 0
            for messages in range(1, n + 2):
                required = set(range(messages))
                if any(all({labels[v] for v in edge} == required for edge in edges)
                       for labels in product(range(messages), repeat=len(operational))):
                    direct = messages
            self.assertEqual(direct, expected)
            self.assertEqual(woc.access_message_capacity(behavior, operational, access), direct)

    def test_concrete_encoder_and_validator_on_small_semantic_instances(self):
        pairs = 0
        for n in range(4):
            for mask in range(1 << n):
                sites = tuple(i for i in range(n) if mask & (1 << i))
                b, j, access = language.finite_instance(n, sites)
                messages = 1 << ((n - len(sites) + 1).bit_length() - 1)
                decoder = {p: language.syndrome(p, sites) for p in access}
                embedder = {(p, m): language.embed(p, m, sites)
                            for p in access for m in range(messages)}
                self.assertEqual(woc.validate_access_scheme(b, j, access, messages, decoder, embedder),
                                 (True, []))
                pairs += len(embedder)
        self.assertEqual(pairs, 1213)

    def test_seven_site_syndrome_covers_every_source_and_message(self):
        pairs = 0
        # All 128 order vectors, both all-direct and all-named AST forms.
        # Full naming combinations are checked at the smaller semantic bound.
        for order, naming in product(range(128), (0, 127)):
            p = language.make_procedure(7, order, naming)
            for message in range(8):
                q = language.embed(p, message)
                qb, qt = language.shape(q)
                pb, pt = language.shape(p)
                self.assertLessEqual(sum(x != y for x, y in zip(pb, qb)), 1)
                self.assertEqual(qt, pt)
                self.assertEqual(language.syndrome(q), message)
                for target in language.attack_targets(q, ()):
                    self.assertEqual(language.syndrome(target), message)
                for inputs in product((0, 1), repeat=7):
                    self.assertEqual(language.evaluate(p, inputs), language.evaluate(q, inputs))
                pairs += 1
        self.assertEqual(pairs, 2048)

    def test_partial_and_complete_normalization_preserve_claimed_labels(self):
        for n in range(4):
            for mask in range(1 << n):
                sites = tuple(i for i in range(n) if mask & (1 << i))
                for order, naming in product(range(1 << n), repeat=2):
                    p = language.make_procedure(n, order, naming)
                    label = language.syndrome(p, sites)
                    for q in language.attack_targets(p, sites):
                        self.assertEqual(language.syndrome(q, sites), label)
        b, j, access = language.finite_instance(3, (0,))
        self.assertEqual(woc.access_message_capacity(b, j, access), 2)
        b, j, access = language.finite_instance(3, (0, 1, 2))
        self.assertEqual(woc.access_message_capacity(b, j, access), 1)

    def test_input_boundaries_and_excluded_normalization_attack(self):
        for n in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                language.make_procedure(n)
        for order in (-1, True, 1.5, 2):
            with self.assertRaises(ValueError):
                language.make_procedure(1, order)
        p = language.make_procedure(1)
        for site in (-1, True, 1.5, 1):
            with self.assertRaises(ValueError):
                language.syndrome(p, (site,))
        for message in (-1, True, 1.5, 2):
            with self.assertRaises(ValueError):
                language.embed(p, message)
        with self.assertRaises(ValueError):
            language.evaluate(p, (True,))
        with self.assertRaises(ValueError):
            language.shape(language.Procedure((language.Return(language.Var('x0')),)))
        with self.assertRaises(ValueError):
            language.shape(language.Procedure((language.Return(language.Add(language.Var('x0'),
                                                                           language.Lit(True))),)))
        # Positive labels are not robust against a normalization omitted from K.
        marked = language.embed(p, 1)
        self.assertEqual(language.syndrome(marked), 1)
        normalized = language.attack_targets(marked, (0,))[0]
        self.assertEqual(language.syndrome(normalized), 0)


if __name__ == '__main__':
    unittest.main()
