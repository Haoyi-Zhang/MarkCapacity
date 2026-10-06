"""Reject malformed finite indices before arithmetic, lookup, or search."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from woc import (private_recovery_value, shared_recovery_value,
                 coordinate_product_edges, disjoint_union_edges, transversal_number,
                 max_average_list_cover, deterministic_worst_source_value,
                 shared_recovery_dual_bound, polychromatic_number,
                 find_polychromatic_coloring)


class IndexBoundaryTests(unittest.TestCase):
    def test_indices_are_checked_before_deduplication_and_lookup(self):
        for vertex in (True, False, 0.5, '0', -1, 2):
            with self.subTest(vertex=vertex):
                with self.assertRaises(ValueError):
                    private_recovery_value(((vertex,),), (1,), ((1,), (1,)))
                with self.assertRaises(ValueError):
                    shared_recovery_value(((vertex,),), (1,), {(0, 0): 1})
        self.assertEqual(private_recovery_value(((0,),), (1,), ((1,),)), 1)
        self.assertEqual(shared_recovery_value(((0,),), (1,), {(0,): 1}), 1)
        evaluators = (
            lambda e: max_average_list_cover((e,), 2, 1, (1, 1), ((1,),)),
            lambda e: deterministic_worst_source_value((e,), 2, (1,)),
            lambda e: private_recovery_value((e,), (1,), ((1,), (1,))),
            lambda e: shared_recovery_value((e,), (1,), {(0, 0): 1}),
            lambda e: shared_recovery_dual_bound((e,), (1,), (1,), 2),
            lambda e: polychromatic_number((e,), 2),
            lambda e: transversal_number((e,), 2),
            lambda e: find_polychromatic_coloring((e,), 2, 1),
        )
        for edge in ((0, False), (1, True), (0, 0.0), (1, 1.0)):
            for evaluator_index, evaluate in enumerate(evaluators):
                with self.subTest(edge=edge, evaluator=evaluator_index):
                    with self.assertRaises(ValueError):
                        evaluate(edge)
        self.assertEqual(find_polychromatic_coloring(((0, 0, 1, 1),), 2, 2), (0, 1))

    def test_shared_labels_are_nonboolean_integers(self):
        for label in (True, False, 0.5, '0', -1, 1):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    shared_recovery_value(((0,),), (1,), {(label,): 1})
        self.assertEqual(shared_recovery_value(((0,),), (1,), {(0,): 1}), 1)

    def test_product_counts_are_nonboolean_integers(self):
        for make in (coordinate_product_edges, disjoint_union_edges):
            for count in (True, False, 1.5, '1', -1):
                for args in ((((0,),), count, ((0,),), 1),
                             (((0,),), 1, ((0,),), count)):
                    with self.subTest(make=make.__name__, args=args):
                        with self.assertRaises(ValueError):
                            make(*args)

            for edge in ((0, False), (1, True), (0, 0.0), (1, 1.0)):
                for args in (((edge,), 2, ((0,),), 1),
                             (((0,),), 1, (edge,), 2)):
                    with self.subTest(make=make.__name__, args=args):
                        with self.assertRaises(ValueError):
                            make(*args)
        self.assertEqual(coordinate_product_edges(((0,),), 1, ((0,),), 1), ((0,),))
        self.assertEqual(disjoint_union_edges(((0,),), 1, ((0,),), 1), ((0,), (1,)))

    def test_product_vertices_are_checked_before_offsetting(self):
        for make in (coordinate_product_edges, disjoint_union_edges):
            for vertex in (True, False, 0.5, '0', -1, 2):
                for args in ((((vertex,),), 2, ((0,),), 1),
                             (((0,),), 1, ((vertex,),), 2)):
                    with self.subTest(make=make.__name__, args=args):
                        with self.assertRaises(ValueError):
                            make(*args)

    def test_transversal_inputs_are_validated_before_enumeration(self):
        for count in (True, False, 1.5, '1', -1):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    transversal_number(((0,),), count)
        for vertex in (True, False, 0.5, '0', -1, 2):
            with self.subTest(vertex=vertex):
                with self.assertRaises(ValueError):
                    transversal_number(((vertex,),), 2)
        self.assertEqual(transversal_number(((0, 1),), 2), 1)


if __name__ == '__main__':
    unittest.main()
