"""Independent syntax/rotation and bounded native controls for the worked channel."""
import sys
from pathlib import Path
import unittest
import io
import json
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from associativity_example import colorings, detect, instance, rotations, source, study, main


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

    def test_cli_outputs_have_canonical_lf_bytes_on_every_host(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'owned-output'
            with patch.object(sys, 'argv', ['owned-example', '--out', str(out)]), redirect_stdout(io.StringIO()):
                main()
            files = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob('*') if p.is_file()}
            self.assertEqual(len(files), 12)
            for name, data in files.items():
                self.assertNotIn(b'\r', data, name)
                self.assertTrue(data.endswith(b'\n'), name)
            self.assertEqual(files['summary.json'],
                             (json.dumps(study()[0], indent=2) + '\n').encode('utf-8'))


if __name__ == '__main__':
    unittest.main()
