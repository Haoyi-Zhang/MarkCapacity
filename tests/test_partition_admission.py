"""Malformed equivalences are input errors, not capacity obstructions."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import woc

class PartitionAdmissionTests(unittest.TestCase):
    def test_common_universe_does_not_make_overlapping_blocks_a_partition(self):
        valid=(frozenset({0}),frozenset({1}))
        bad=(frozenset({0}),frozenset({0,1}))
        access={0:{0,1},1:{0,1}}
        operations=(
            lambda:woc.general_exact_feasible(bad,valid,2),
            lambda:woc.direct_general_exact_feasible(bad,valid,2),
            lambda:woc.access_exact_feasible(bad,valid,access,2),
            lambda:woc.direct_access_exact_feasible(bad,valid,access,2),
            lambda:woc.construct_access_scheme(bad,valid,access,1),
            lambda:woc.exact_message_capacity((frozenset({0,1}),),bad),
        )
        for i,operation in enumerate(operations):
            with self.subTest(operation=i):
                with self.assertRaisesRegex(ValueError,'overlap'):
                    operation()

    def test_empty_and_duplicate_blocks_reject_in_both_directed_routes(self):
        for bad in ((frozenset(),frozenset({0})),
                    (frozenset({0}),frozenset({0}))):
            for decide in (woc.directed_access_exact_feasible,
                           woc.direct_directed_access_exact_feasible):
                with self.subTest(partition=bad,decide=decide.__name__):
                    with self.assertRaises(ValueError):
                        decide(('source',),bad,{'source':{0}},{'source':{0}},1)

    def test_invalid_product_operand_rejects_before_empty_shortcut(self):
        bad=(frozenset(),)
        for first,second in (((),bad),(bad,())):
            with self.subTest(first=first):
                with self.assertRaises(ValueError):
                    woc.product_partition(first,second)
        self.assertEqual(woc.product_partition((),(frozenset({0}),)),())

    def test_valid_supplied_block_order_and_negative_results_are_preserved(self):
        b=(frozenset({0,1}),)
        j=(frozenset({1}),frozenset({0}))
        self.assertEqual(woc.block_index(j),{1:0,0:1})
        self.assertEqual(woc.access_hypergraph(b,j,{0:{0},1:{1}}),((1,),(0,)))
        self.assertFalse(woc.access_exact_feasible(b,j,{0:{0},1:{1}},2))
        self.assertEqual(woc.access_message_capacity(b,j,{0:set(),1:{1}}),0)
        ok,reasons=woc.validate_scheme((frozenset({0}),frozenset({0})),
                                      (frozenset({0}),),1,{0:0},{(0,0):0})
        self.assertFalse(ok)
        self.assertTrue(reasons)

if __name__=='__main__':
    unittest.main(verbosity=2)
