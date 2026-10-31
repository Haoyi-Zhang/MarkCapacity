"""Concrete single-AST-step adapter for the admitted owned arithmetic grammar.

No symbolic model embedder constructs the output. A verifier replays the actual
AST swap and checks the source-specific edit budget, not just the decoded label.
This is neither a general Python transformer nor an external compiler adapter.
"""
from __future__ import annotations
import ast
import hashlib
import source_language as source


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def label_and_columns(text, normalized):
    model, _, _ = source.inspect_source(text)
    orders, _ = source.language.shape(model)
    normalized = source.language.normalized_sites(len(orders), normalized)
    free = tuple(i for i in range(len(orders)) if i not in normalized)
    messages = 1 << ((len(free) + 1).bit_length() - 1)
    columns = {i: column for column, i in enumerate(free[:messages-1], 1)}
    label = 0
    for i, column in columns.items():
        if orders[i]:
            label ^= column
    return label, columns, messages, normalized


def encode_with_receipt(text, message, normalized=()):
    label, columns, messages, normalized = label_and_columns(text, normalized)
    if type(message) is not int or not 0 <= message < messages:
        raise ValueError('message outside the syndrome alphabet')
    difference = label ^ message
    site = next((i for i, column in columns.items() if column == difference), None)
    output = text if site is None else source.commute(text, site)
    return output, dict(source_sha256=digest(text), output_sha256=digest(output),
                        message=message, normalized_sites=sorted(normalized),
                        commute_site=site, commutations=0 if site is None else 1)


def verify_receipt(text, output, receipt, normalized=()):
    """Verify an actual source step without invoking the producer/model embedder.

    Admission implies pure return-value preservation. AST replay additionally
    excludes changes to naming, signature, other sites, or the spent budget.
    Content hashes bind evidence but do not themselves prove reachability.
    """
    required = {'source_sha256', 'output_sha256', 'message', 'normalized_sites',
                'commute_site', 'commutations'}
    if type(receipt) is not dict or set(receipt) != required:
        raise ValueError('complete encoding receipt required')
    if receipt['source_sha256'] != digest(text) or receipt['output_sha256'] != digest(output):
        raise ValueError('receipt source/output identity mismatch')
    model, tree, nodes = source.inspect_source(text)
    _, target, _ = source.inspect_source(output)
    n = len(model.components)
    sites = receipt['normalized_sites']
    if type(sites) is not list or any(type(i) is not int for i in sites) or len(set(sites)) != len(sites):
        raise ValueError('unique declared normalization sites required')
    declared = source.language.normalized_sites(n, sites)
    normalized = source.language.normalized_sites(n, normalized)
    if declared != normalized:
        raise ValueError('receipt normalization contract differs from verifier policy')
    site, spent = receipt['commute_site'], receipt['commutations']
    if type(spent) is not int or spent not in (0, 1):
        raise ValueError('one-commutation budget required')
    if site is None:
        if spent != 0 or text != output:
            raise ValueError('identity receipt must preserve the source text')
    else:
        if type(site) is not int or not 0 <= site < n or site in normalized or spent != 1:
            raise ValueError('one surviving source site must justify the edit')
        node = nodes[site]
        node.left, node.right = node.right, node.left
        if ast.dump(tree, include_attributes=False) != ast.dump(target, include_attributes=False):
            raise ValueError('output is not exactly the declared source AST swap')
    # Recompute decoding via the separately retained source decoder, not the
    # adapter's label/column calculation or the producer's requested output.
    message = receipt['message']
    free_count = n - len(normalized)
    messages = 1 << ((free_count + 1).bit_length() - 1)
    if type(message) is not int or not 0 <= message < messages or source.decode(output, normalized) != message:
        raise ValueError('requested label is not recovered')
    return True
