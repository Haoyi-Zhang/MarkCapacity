"""Derive an interacting rewrite channel from four pure-integer operands.

Only generated addition trees are compiled. No input source, external program,
network, or third-party payload is executed. The bound is five tree shapes,
two parameter-name patterns and 625 input tuples.
"""
from __future__ import annotations

import argparse
import ast
import itertools
import json
from pathlib import Path


def trees(start=0, stop=4):
    if stop - start == 1:
        return (start,)
    return tuple((a, b) for cut in range(start + 1, stop)
                 for a in trees(start, cut) for b in trees(cut, stop))


def rotations(tree):
    """One local associativity rewrite at any position, in either direction."""
    if isinstance(tree, int):
        return frozenset()
    left, right = tree
    out = {(other, right) for other in rotations(left)}
    out.update((left, other) for other in rotations(right))
    if isinstance(left, tuple):
        a, b = left
        out.add((a, (b, right)))
    if isinstance(right, tuple):
        b, c = right
        out.add(((left, b), c))
    return frozenset(out)


def expression(tree, names):
    if isinstance(tree, int):
        return names[tree]
    return '(' + expression(tree[0], names) + ' + ' + expression(tree[1], names) + ')'


def source(tree, names):
    return 'def carrier(' + ', '.join(names) + '):\n    return ' + expression(tree, names) + '\n'


def detect(text):
    """Read parenthesization from parsed syntax, normalizing bound identifiers."""
    module = ast.parse(text)
    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef):
        raise ValueError('one generated function required')
    function = module.body[0]
    args = function.args
    if (function.name != 'carrier' or len(args.args) != 4 or args.posonlyargs
            or args.kwonlyargs or args.vararg or args.kwarg or args.defaults
            or function.decorator_list or len(function.body) != 1
            or not isinstance(function.body[0], ast.Return)):
        raise ValueError('four-operand generated syntax required')
    names = [a.arg for a in args.args]
    if len(set(names)) != 4:
        raise ValueError('distinct parameter bindings required')

    def visit(node):
        if isinstance(node, ast.Name) and node.id in names:
            return names.index(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return (visit(node.left), visit(node.right))
        raise ValueError('only parameter references and addition are admitted')

    tree = visit(function.body[0].value)
    if tree not in trees():
        raise ValueError('each ordered operand must occur exactly once')
    return tree


def instance():
    shapes = trees()
    identity = {tree: i for i, tree in enumerate(shapes)}
    edges = tuple(tuple(sorted({i} | {identity[q] for q in rotations(p)}))
                  for i, p in enumerate(shapes))
    return shapes, edges


def colorings(edges, colors):
    required = set(range(colors))
    return tuple(labels for labels in itertools.product(range(colors), repeat=5)
                 if all({labels[i] for i in edge} == required for edge in edges))


def study(values=range(-2, 3)):
    shapes, edges = instance()
    if len(shapes) != 5 or not all(len(e) == 3 for e in edges):
        raise AssertionError('derived five-shape incidence changed')
    binary = colorings(edges, 2)
    ternary = colorings(edges, 3)
    if not binary or ternary:
        raise AssertionError('derived capacity is not exactly two')
    two_step = [sorted({j for neighbor in edge for j in edges[neighbor]}) for edge in edges]
    if any(edge != list(range(5)) for edge in two_step):
        raise AssertionError('two-rotation access must cover all five cells')
    labeling = binary[0]
    namesets = (('x0', 'x1', 'x2', 'x3'), ('arg0', 'arg1', 'arg2', 'arg3'))
    samples = tuple(itertools.product(values, repeat=4))
    functions = {}
    sources = {}
    calls = 0
    for i, tree in enumerate(shapes):
        for pattern, names in enumerate(namesets):
            text = source(tree, names)
            if detect(text) != tree:
                raise AssertionError('printed/parsed syntax mismatch')
            namespace = {'__builtins__': {}}
            exec(compile(text, '<owned-associativity-carrier>', 'exec'), namespace)
            function = namespace['carrier']
            functions[i, pattern] = function
            sources[f'cell-{i}-names-{pattern}.py'] = text
            for args in samples:
                if function(*args) != sum(args):
                    raise AssertionError('native pure-addition mismatch')
                calls += 1
    witnesses = []
    for i, edge in enumerate(edges):
        for message in range(2):
            output = next(j for j in edge if labeling[j] == message)
            if output != i and shapes[output] not in rotations(shapes[i]):
                raise AssertionError('selected witness is not a one-step output')
            if labeling[shapes.index(detect(sources[f'cell-{output}-names-1.py']))] != message:
                raise AssertionError('renamed witness does not decode to its message')
            for args in samples:
                if functions[output, 1](*args) != sum(args):
                    raise AssertionError('native selected-witness mismatch')
                calls += 1
            witnesses.append({'source': i, 'message': message, 'output': output})
    summary = {'tree_shapes': 5, 'parameter_name_patterns': 2,
               'local_reachable_cells': [len(e) for e in edges],
               'source_edges': [list(e) for e in edges], 'capacity': 2,
               'two_rotation_reachable_cells': [len(e) for e in two_step],
               'two_rotation_capacity': 5,
               'binary_colorings': len(binary), 'ternary_colorings': len(ternary),
               'color_assignments_checked': 2**5 + 3**5,
               'labeling': list(labeling), 'source_message_witnesses': witnesses,
               'compiled_functions': len(functions), 'input_tuples_per_function': len(samples),
               'actual_native_calls': calls, 'native_mismatches': 0,
               'scope': 'Four ordered pure integer operands; at most one local associativity rewrite; bound-identifier renaming only; no compiler-wide or cryptographic claim.'}
    return summary, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    root = Path(__file__).resolve().parents[1]
    if out.exists() or out == root or root in out.parents or out in root.parents:
        parser.error('use an absent directory outside the artifact')
    summary, sources = study()
    (out / 'sources').mkdir(parents=True)
    for name, text in sources.items():
        (out / 'sources' / name).write_text(text, encoding='utf-8', newline='\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    rows = [r'\begin{tabular}{lrrr}', r'\toprule',
            r'Carrier & Local cells & Exact messages & Native calls \\', r'\midrule',
            r'Four-operand reassociation & 3 & 2 & ' + f"{summary['actual_native_calls']:,}" + r' \\',
            r'\bottomrule', r'\end{tabular}']
    (out / 'table.tex').write_text('\n'.join(rows) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
