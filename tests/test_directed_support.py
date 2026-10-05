"""Declared-source boundaries for the two directed decision paths."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from woc import (directed_access_hypergraph, directed_access_exact_feasible,
                 direct_directed_access_exact_feasible, normalize_partition)


class DirectedSupportTests(unittest.TestCase):
    def test_empty_declared_support_rejected(self):
        targets = normalize_partition([{'t'}])
        for make_sources in (lambda: [], lambda: iter(())):
            with self.assertRaises(ValueError):
                directed_access_hypergraph(make_sources(), targets, {}, {})
            for decide in (directed_access_exact_feasible,
                           direct_directed_access_exact_feasible):
                with self.subTest(decide=decide.__name__, sources=make_sources):
                    with self.assertRaises(ValueError):
                        decide(make_sources(), targets, {}, {}, 2)

    def test_empty_admissible_row_is_valid_but_infeasible(self):
        targets = normalize_partition([{'t'}])
        self.assertEqual(directed_access_hypergraph(['s'], targets,
                                                 {'s': {'t'}}, {'s': set()}), ((),))
        for decide in (directed_access_exact_feasible,
                       direct_directed_access_exact_feasible):
            self.assertFalse(decide(['s'], targets, {'s': {'t'}}, {'s': set()}, 1))

    def test_singleton_identity_one_message(self):
        targets = normalize_partition([{'t'}])
        for decide in (directed_access_exact_feasible,
                       direct_directed_access_exact_feasible):
            self.assertTrue(decide(['t'], targets, {'t': {'t'}}, {'t': {'t'}}, 1))


if __name__ == '__main__':
    unittest.main()
