"""Portable finite references for exact coloring order and current bindings."""
import hashlib
import json
from itertools import product
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import woc


def complete_coloring_reference(edges, vertices, messages):
    """Enumerate complete assignments, with no incremental viability pruning.

    Degree order is part of the producer's first-witness contract. The oracle
    uses that order only to enumerate full candidates; it checks every edge.
    Fixtures supplied here already have valid integer indices/cardinalities.
    """
    edges = tuple(tuple(dict.fromkeys(edge)) for edge in edges)
    degree = [sum(v in edge for edge in edges) for v in range(vertices)]
    order = sorted(range(vertices), key=lambda v: (-degree[v], v))
    required = set(range(messages))
    for labels in product(range(messages), repeat=vertices):
        coloring = [None] * vertices
        for v, label in zip(order, labels):
            coloring[v] = label
        if all({coloring[v] for v in edge} == required for edge in edges):
            return tuple(coloring)
    return None


def program_reference(behavior, operational, access, messages):
    """Existence by program-label enumeration, not quotient reconstruction."""
    items = sorted({p for block in behavior for p in block}, key=repr)
    behavior_of = {p: i for i, block in enumerate(behavior) for p in block}
    for labels in product(range(messages), repeat=len(items)):
        decoder = dict(zip(items, labels))
        if any(len({decoder[p] for p in block}) != 1 for block in operational):
            continue
        if all(any(behavior_of[q] == behavior_of[p] and decoder[q] == m
                   for q in access[p]) for p in items for m in range(messages)):
            return True
    return False


class IncidentPruningTests(unittest.TestCase):
    def test_all_small_hypergraph_families_exact_first_coloring(self):
        for vertices in range(4):
            possible = [tuple(v for v in range(vertices) if mask & (1 << v))
                        for mask in range(1 << vertices)]
            for family in range(1 << len(possible)):
                edges = tuple(edge for i, edge in enumerate(possible)
                              if family & (1 << i))
                for messages in (1, 2, 3):
                    with self.subTest(vertices=vertices, family=family, messages=messages):
                        self.assertEqual(woc.find_polychromatic_coloring(edges, vertices, messages),
                                         complete_coloring_reference(edges, vertices, messages))

    def test_sparse_components_isolates_and_backtracking(self):
        families = (
            (((0, 1), (1, 2), (2, 0), (3, 4)), 6),
            (((0, 1), (1, 2), (2, 3), (3, 0), (4, 5)), 6),
            (((0, 1, 2), (1, 3, 4), (0, 4), (2, 3)), 6),
            (((0, 2), (0, 3), (1, 2), (1, 4), (3, 4)), 6),
        )
        for edges, vertices in families:
            for messages in (1, 2, 3):
                self.assertEqual(woc.find_polychromatic_coloring(edges, vertices, messages),
                                 complete_coloring_reference(edges, vertices, messages))

    def test_duplicate_vertices_edges_and_single_use_iterators(self):
        edges = ((2, 0, 2, 1), (1, 3), (2, 0, 2, 1), (4, 3))
        for messages in (1, 2, 3):
            expected = complete_coloring_reference(edges, 6, messages)
            self.assertEqual(woc.find_polychromatic_coloring(edges, 6, messages), expected)
            once = (iter(edge) for edge in edges)
            self.assertEqual(woc.find_polychromatic_coloring(once, 6, messages), expected)

    def test_validation_precedes_empty_or_small_edge_shortcuts(self):
        for bad in (True, False, 0.5, '0', -1, 2):
            with self.assertRaises(ValueError):
                woc.find_polychromatic_coloring(((), (0, bad)), 2, 3)
        for vertices, messages in ((True, 1), (-1, 1), (1.5, 1),
                                   (2, True), (2, 0), (2, 1.5)):
            with self.assertRaises(ValueError):
                woc.find_polychromatic_coloring((), vertices, messages)
        self.assertEqual(woc.find_polychromatic_coloring((), 0, 3), ())
        self.assertEqual(woc.find_polychromatic_coloring((), 2, 3), (0, 0))
        self.assertIsNone(woc.find_polychromatic_coloring(((),), 2, 1))

    def test_source_witnesses_against_program_label_reference(self):
        items = (None, 'x')
        partitions = ((frozenset(items),), (frozenset({None}), frozenset({'x'})))
        for behavior, operational, mask, messages in product(partitions, partitions,
                                                              range(16), (1, 2)):
            access = {p: {q for j, q in enumerate(items) if mask & (1 << (2 * i + j))}
                      for i, p in enumerate(items)}
            expected = program_reference(behavior, operational, access, messages)
            self.assertEqual(woc.access_exact_feasible(behavior, operational, access, messages), expected)
            if not expected:
                with self.assertRaises(ValueError):
                    woc.construct_access_scheme(behavior, operational, access, messages)
                continue
            decoder, embedder = woc.construct_access_scheme(behavior, operational, access, messages)
            behavior_of = {p: i for i, block in enumerate(behavior) for p in block}
            self.assertTrue(all(len({decoder[p] for p in block}) == 1 for block in operational))
            for p, m in product(items, range(messages)):
                q = embedder[p, m]
                self.assertIn(q, access[p])
                self.assertEqual(behavior_of[q], behavior_of[p])
                self.assertEqual(decoder[q], m)
            self.assertEqual(woc.validate_access_scheme(behavior, operational, access,
                                                      messages, decoder, embedder), (True, []))

    def test_current_manifest_and_archived_output_bindings(self):
        archived = json.loads((ROOT / 'raw/run_manifest.json').read_text(encoding='utf-8'))
        current = json.loads((ROOT / 'current-source-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(set(current), set(archived))
        for field in ('command', 'determinism_contract', 'outputs'):
            self.assertEqual(current[field], archived[field])
        self.assertEqual(set(current['inputs']), set(archived['inputs']))
        self.assertEqual(set(current['inputs']), {'src/woc.py', 'src/run_all.py', 'src/witness_checks.py'})
        for rel, digest in current['inputs'].items():
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest, rel)
        for rel, digest in archived['outputs'].items():
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest, rel)
        for line in (ROOT / 'raw/SHA256SUMS').read_text(encoding='utf-8').splitlines():
            digest, rel = line.split('  ', 1)
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest, rel)


if __name__ == '__main__':
    unittest.main()
