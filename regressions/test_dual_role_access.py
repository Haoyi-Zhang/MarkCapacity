"""Three-program counterexample to closing a single-step access theorem.

These are exact finite proof witnesses, not independently sampled software or
a performance experiment. Historical test/campaign counts remain unchanged.
"""
from itertools import product
import csv
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from woc import access_message_capacity

PROGRAMS = ('a', 'b', 'c')
BEHAVIOR = (frozenset(PROGRAMS),)
OLD_CELLS = tuple(frozenset((p,)) for p in PROGRAMS)
NEW_CELLS = (frozenset(('a', 'b')), frozenset(('c',)))
OLD_ACCESS = {'a': frozenset('a'), 'b': frozenset('bc'), 'c': frozenset('bc')}
REWRITE = {'a': frozenset('b'), 'b': frozenset(), 'c': frozenset()}


def closure(rows):
    """Plain graph reachability, independent of quotient/coloring helpers."""
    answer = {}
    for source in PROGRAMS:
        seen, todo = {source}, [source]
        while todo:
            for target in rows[todo.pop()]:
                if target not in seen:
                    seen.add(target)
                    todo.append(target)
        answer[source] = frozenset(seen)
    return answer


def direct_capacity(cells, rows):
    """Enumerate all 1/2/3-message program decoders without quotient search."""
    best = 0
    for count in (1, 2, 3):
        alphabet = set(range(count))
        for values in product(range(count), repeat=3):
            decoder = dict(zip(PROGRAMS, values))
            if any(len({decoder[p] for p in block}) != 1 for block in cells):
                continue
            if all({decoder[q] for q in rows[p]} == alphabet for p in PROGRAMS):
                best = count
                break
    return best


class DualRoleAccessTests(unittest.TestCase):
    def test_reflexive_transitive_old_access_does_not_prevent_counterexample(self):
        ledger = Path(__file__).resolve().parents[1] / 'claim_evidence_ledger.csv'
        with ledger.open(encoding='utf-8', newline='') as stream:
            row = next(row for row in csv.DictReader(stream) if row['claim_id'] == 'C34')
        for field in ('claim_text', 'claim_scope'):
            self.assertIn('R_T=R union T', row[field])
            self.assertIn('J_T=EqCl(J union T)', row[field])
            self.assertRegex(row[field].lower(), r'reflexive old (?:access )?r\b')
        self.assertIn('not alternating closure', row['claim_scope'])
        self.assertIn('1/1/2', row['limitations'])
        self.assertIn('regressions/test_dual_role_access.py', row['source_or_test'])
        self.assertEqual(closure(OLD_ACCESS), OLD_ACCESS)
        union = {p: OLD_ACCESS[p] | REWRITE[p] for p in PROGRAMS}
        composed = closure(union)
        self.assertEqual(union['a'], frozenset('ab'))
        self.assertEqual(composed['a'], frozenset('abc'))
        for cells, rows, expected in ((OLD_CELLS, OLD_ACCESS, 1),
                                      (NEW_CELLS, union, 1),
                                      (NEW_CELLS, composed, 2)):
            with self.subTest(cells=cells, rows=rows):
                self.assertEqual(direct_capacity(cells, rows), expected)
                self.assertEqual(access_message_capacity(BEHAVIOR, cells, rows), expected)

    def test_actual_two_message_decoder_and_source_targets(self):
        union = {p: OLD_ACCESS[p] | REWRITE[p] for p in PROGRAMS}
        composed = closure(union)
        decoder = {'a': 0, 'b': 0, 'c': 1}
        self.assertEqual({decoder[p] for p in NEW_CELLS[0]}, {0})
        self.assertEqual({decoder[q] for q in union['a']}, {0})
        for source in PROGRAMS:
            self.assertEqual({decoder[q] for q in composed[source]}, {0, 1})
        self.assertNotIn('c', union['a'])
        self.assertIn('b', REWRITE['a'])
        self.assertIn('c', OLD_ACCESS['b'])

    def test_postcomposition_alone_does_not_supply_the_missing_color(self):
        tail = closure(REWRITE)
        post = {p: frozenset(z for q in OLD_ACCESS[p] for z in tail[q])
                for p in PROGRAMS}
        self.assertEqual(post['a'], frozenset('ab'))
        self.assertEqual(direct_capacity(NEW_CELLS, post), 1)
        self.assertEqual(access_message_capacity(BEHAVIOR, NEW_CELLS, post), 1)


if __name__ == '__main__':
    unittest.main()
