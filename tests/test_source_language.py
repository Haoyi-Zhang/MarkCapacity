"""Owned ordinary CPython execution, binding, edit-budget and admission checks."""
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import arithmetic_language as language
import source_language as source

class SourceLanguageTests(unittest.TestCase):
    def test_roundtrip_and_actual_execution_of_every_small_procedure(self):
        calls=0
        for n in range(4):
            for b,t in product(range(1<<n),repeat=2):
                p=language.make_procedure(n,b,t)
                text=source.render(p)
                self.assertEqual(source.parse_source(text),p)
                native=source.compile_source(text)
                for x in product((0,1),repeat=n):
                    self.assertEqual(native(x),language.evaluate(p,x))
                    calls+=1
        self.assertEqual(calls,585)

    def test_function_scope_requires_fresh_temporaries(self):
        # Fixed benign counterexample, not input to the admitted compiler.
        naive='def carrier(x0, x1):\n    t = x0 + 1\n    t = x1 + 1\n    return (t, t)\n'
        namespace={'__builtins__':{}}
        exec(compile(naive,'<owned-binding-counterexample>','exec'),namespace)
        self.assertEqual(namespace['carrier'](0,1),(2,2))
        self.assertEqual(language.evaluate(language.make_procedure(2,0,3),(0,1)),(1,2))
        with self.assertRaisesRegex(ValueError,'fresh and unique'):
            source.parse_source(naive)
        hygienic=source.render(language.make_procedure(2,0,3))
        self.assertEqual(source.compile_source(hygienic)((0,1)),(1,2))

    def test_independent_ast_access_matches_model_without_budget_reset(self):
        for n in range(3):
            for b,t in product(range(1<<n),repeat=2):
                p=language.make_procedure(n,b,t)
                actual={source.parse_source(s) for s in source.source_reachable(source.render(p))}
                self.assertEqual(actual,language.reachable(p))
        self.assertNotIn(source.render(language.make_procedure(2,3)),
                         source.source_reachable(source.render(language.make_procedure(2))))

    def test_source_encoder_attack_and_excluded_normalization(self):
        for b,t in product(range(8),repeat=2):
            text=source.render(language.make_procedure(3,b,t))
            for sites in ((),(0,),(0,1,2)):
                messages=1<<((3-len(sites)+1).bit_length()-1)
                for m in range(messages):
                    marked=source.encode(text,m,sites)
                    self.assertEqual(source.decode(marked,sites),m)
                    for attacked in source.attack_sources(marked,sites):
                        self.assertEqual(source.decode(attacked,sites),m)
        marked=source.encode(source.render(language.make_procedure(1)),1)
        self.assertEqual(source.decode(source.commute(marked,0)),0)

    def test_strict_admission_preserves_pure_integer_and_binding_premises(self):
        bad=(
            'def carrier(x0):\n    return (x0 + True,)\n',
            'def carrier(x0):\n    return (x0 + 1.0,)\n',
            'def carrier(x0):\n    x0 = x0 + 1\n    return (x0 + 1,)\n',
            'def carrier(x0, x1):\n    v0 = x1 + 1\n    return (v0, x1 + 1)\n',
            'def carrier(x0):\n    v0 = x0 + 1\n    return (x0 + 1,)\n',
            'def carrier(x0=0):\n    return (x0 + 1,)\n',
        )
        for text in bad:
            with self.subTest(source=text):
                with self.assertRaises(ValueError):
                    source.compile_source(text)
        native=source.compile_source(source.render(language.make_procedure(1)))
        for args in ((True,),[0],(0.0,),(),(2,)):
            with self.assertRaises(ValueError):
                native(args)

if __name__=='__main__':
    unittest.main(verbosity=2)
