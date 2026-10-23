"""Independent syntax/rotation and bounded native controls for the worked channel."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from associativity_example import colorings, detect, instance, rotations, source, study


class AssociativityTests(unittest.TestCase):
    def test_derived_cycle_and_global_obstruction(self):
        shapes, edges = instance()
        self.assertEqual(len(set(shapes)), 5)
        self.assertTrue(all(len(e) == 3 and i in e for i, e in enumerate(edges)))
        self.assertEqual(sum(len(rotations(t)) for t in shapes), 10)
        self.assertTrue(colorings(edges, 2))
        self.assertEqual(colorings(edges, 3), ())

    def test_independent_parsed_detector_and_renaming(self):
        for tree in instance()[0]:
            for names in (('a', 'b', 'c', 'd'), ('v0', 'v1', 'v2', 'v3')):
                self.assertEqual(detect(source(tree, names)), tree)

    def test_outside_the_declared_language_is_not_silently_accepted(self):
        for text in ('def carrier(a,b,c,d):\n return a-b+c+d\n',
                     'def carrier(a,b,c,d):\n return a+b+d+c\n',
                     'def carrier(a,b,c,d):\n return a+b+c+c\n'):
            with self.assertRaises(ValueError):
                detect(text)

    def test_native_witnesses_are_executed_not_only_counted(self):
        result, sources = study(range(-1, 2))
        self.assertEqual((result['compiled_functions'], len(sources)), (10, 10))
        self.assertEqual(result['actual_native_calls'], 1620)
        self.assertEqual(result['native_mismatches'], 0)
        self.assertEqual(len(result['source_message_witnesses']), 10)
        self.assertEqual(result['two_rotation_reachable_cells'], [5]*5)
        self.assertEqual(result['two_rotation_capacity'], 5)


if __name__ == '__main__':
    unittest.main()
