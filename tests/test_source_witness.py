from itertools import combinations, product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import source_language as source
import source_witness as adapter


class SourceWitnessTests(unittest.TestCase):
    def test_all_small_source_requests_and_actual_returns(self):
        witnessed = 0
        with patch.object(source.language, 'embed', side_effect=AssertionError('symbolic encoder forbidden')):
            for n in range(4):
                for b, t in product(range(1 << n), repeat=2):
                    text = source.render(source.language.make_procedure(n, b, t))
                    for width in range(n+1):
                        for sites in combinations(range(n), width):
                            messages = 1 << ((n-width+1).bit_length()-1)
                            for message in range(messages):
                                out, receipt = adapter.encode_with_receipt(text, message, sites)
                                self.assertTrue(adapter.verify_receipt(text, out, receipt, sites))
                                native = source.compile_source(out)
                                for args in product((0, 1), repeat=n):
                                    self.assertEqual(native(args), tuple(x+1 for x in args))
                                witnessed += 1
        self.assertEqual(witnessed, 1213)

    def test_decodable_but_unreachable_and_extra_edits_are_refused(self):
        text = source.render(source.language.make_procedure(3))
        out, receipt = adapter.encode_with_receipt(text, 3)
        # Two swaps recover message 3 just like column 3, but exceed the budget.
        two = source.commute(source.commute(text, 0), 1)
        self.assertEqual(source.decode(two), 3)
        for bad in (two, source.rename_form(out, 0)):
            forged = dict(receipt, output_sha256=adapter.digest(bad))
            with self.assertRaisesRegex(ValueError, 'not exactly'):
                adapter.verify_receipt(text, bad, forged)

    def test_identity_binding_normalization_and_message_premises(self):
        text = source.render(source.language.make_procedure(2))
        out, receipt = adapter.encode_with_receipt(text, 1, (1,))
        for changed in (dict(receipt, source_sha256='0'*64),
                        dict(receipt, normalized_sites=[0]), dict(receipt, message=True),
                        dict(receipt, commutations=2)):
            with self.assertRaises(ValueError):
                adapter.verify_receipt(text, out, changed, (1,))
        # An internally consistent receipt cannot choose a weaker verifier
        # policy that drops an externally required normalization obligation.
        with self.assertRaisesRegex(ValueError, 'verifier policy'):
            adapter.verify_receipt(text, out, receipt, (0,))
        identity, same = adapter.encode_with_receipt(text, 0)
        self.assertEqual(identity, text)
        with self.assertRaises(ValueError):
            adapter.verify_receipt(text, text+'\n', dict(same, output_sha256=adapter.digest(text+'\n')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
