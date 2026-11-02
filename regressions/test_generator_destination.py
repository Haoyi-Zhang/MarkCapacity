"""Output-path dispatch fixtures only: no scientific helper may execute."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import run_all


class GeneratorDestinationTests(unittest.TestCase):
    def test_rejects_omitted_existing_and_overlapping_paths_before_science(self):
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory);project=work/'project';root=project/'artifact'
            root.mkdir(parents=True);(project/'paper').mkdir()
            sentinel=root/'sentinel';sentinel.write_bytes(b'original retained bytes')
            occupied=work/'occupied';occupied.mkdir();(occupied/'keep').write_bytes(b'keep')
            with patch.object(run_all,'ROOT',root),patch.object(run_all,'exhaustive_refinement_check',
                    side_effect=AssertionError('scientific helper forbidden in fixture')) as science:
                with self.assertRaises(ValueError):run_all.main()
                for out in (root,project,work,root/'fresh',project/'paper/fresh',occupied,sentinel):
                    with self.subTest(out=out),self.assertRaises(ValueError):run_all.main(out)
                science.assert_not_called()
            self.assertEqual(sentinel.read_bytes(),b'original retained bytes')
            self.assertEqual((occupied/'keep').read_bytes(),b'keep')
            self.assertFalse((root/'fresh').exists())
            self.assertFalse((project/'paper/fresh').exists())

    def test_accepts_and_reserves_only_an_explicit_absent_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'fresh'
            # Reaching this deliberate sentinel proves the validated path was
            # forwarded before the first helper; that helper does no research.
            with patch.object(run_all,'exhaustive_refinement_check',side_effect=RuntimeError('owned stop')) as science:
                with self.assertRaisesRegex(RuntimeError,'owned stop'):run_all.main(out)
                science.assert_called_once_with(max_universe_size=5)
                with self.assertRaises(ValueError):run_all.main(out)
                self.assertEqual(science.call_count,1)
            self.assertTrue((out/'raw').is_dir());self.assertTrue((out/'generated').is_dir())
            self.assertEqual(list((out/'raw').iterdir()),[])

    def test_cli_requires_out_and_preserves_error_or_dispatch(self):
        with patch.object(run_all,'main') as main,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:run_all.cli([])
            self.assertEqual(error.exception.code,2);main.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'fresh'
            with patch.object(run_all,'main',return_value=0) as main:
                self.assertEqual(run_all.cli(['--out',str(out)]),0)
                main.assert_called_once_with(out.resolve())
            with contextlib.redirect_stderr(io.StringIO()),patch.object(run_all,'exhaustive_refinement_check',
                    side_effect=AssertionError('scientific helper forbidden in fixture')) as science:
                with self.assertRaises(SystemExit) as error:run_all.cli(['--out',directory])
                self.assertEqual(error.exception.code,2);science.assert_not_called()


if __name__=='__main__':unittest.main()
