"""Serialization and output isolation, with a reduced finite census."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import run_all


class ReproductionTests(unittest.TestCase):
    def test_separate_output_is_canonical_and_preserves_retained_records(self):
        root = Path(__file__).resolve().parents[1]
        retained = {str(p.relative_to(root)): p.read_bytes()
                    for directory in ('raw', 'generated')
                    for p in (root / directory).glob('*') if p.is_file()}
        output = Path(tempfile.mkdtemp(prefix='woc-serialization-',
                                      dir=os.environ.get('WOC_CHECK_OUTPUT')))
        refinement = run_all.exhaustive_refinement_check
        general = run_all.exhaustive_general_check
        access = run_all.exhaustive_access_check
        # Only this I/O regression reduces the census; the whole driver still
        # executes the full declared scientific grids during reproduction.
        with patch.object(run_all, 'exhaustive_refinement_check', lambda **_: refinement(2)), \
             patch.object(run_all, 'exhaustive_general_check', lambda **_: general(2)), \
             patch.object(run_all, 'exhaustive_access_check', lambda **_: access(2)), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_all.main(output), 0)
        for relative in ('raw/results.json', 'raw/run_manifest.json',
                         'raw/run_stdout.txt', 'raw/SHA256SUMS'):
            data = (output / relative).read_bytes()
            self.assertNotIn(b'\r', data, relative)
            self.assertTrue(data.endswith(b'\n'), relative)
        for relative, data in retained.items():
            self.assertEqual((root / relative).read_bytes(), data, relative)


if __name__ == '__main__':
    unittest.main()
