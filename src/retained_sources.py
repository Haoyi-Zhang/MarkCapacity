"""Byte-only resolution of explicitly retained producer identities; never replay.

Snapshots are evidence, not importable implementations. Historical source maps
remain unchanged; a whole known map resolves only to its fixed, verified files.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ABSTRACT_COMMAND = 'python3 src/run_all.py --out FRESH_OUTPUT_DIRECTORY'
SOURCE_EXECUTION = {
    'arithmetic_language.py': 'e4253ca53fe1f631a4ac50fe1c2d4c67eff22d8efe74a5bb62b13e963135773d',
    'run_source.py': '5f3bcd9c3dcff44a7aa247aeab8d6156bbbf5a5a1380611a7cb13714c85e7b7a',
    'source_language.py': '02c44224d353abec348678501f5ab37d61c954d3a7c663f82271541d6fa58dc7',
    'woc.py': '3f4fb66dff30b1f69d7fe66243f596b660ad9025ff95372aa2ca0e8ace456148',
}
ABSTRACT = {
    'src/run_all.py': 'a9f31556e6596655f7f125944ea4d14417dafb70c9ea5b9e634de78633a90ee2',
    'src/witness_checks.py': '923dda01c36711f608c9321a24ea5e5cdf65cc610d26db0c133df1221bda947d',
    'src/woc.py': SOURCE_EXECUTION['woc.py'],
}


def digest_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('source preimage missing or nonregular: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding_map(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError('complete exact source binding keyset required')
    if any(type(d) is not str or re.fullmatch('[0-9a-f]{64}', d) is None
           for d in value.values()):
        raise ValueError('source bindings require SHA-256 values')


def resolve_source_execution(bindings):
    binding_map(bindings, SOURCE_EXECUTION)
    if bindings != SOURCE_EXECUTION:
        raise ValueError('unknown retained source-execution identity map')
    paths = {name: ROOT/'source-preimages/source-execution'/name for name in bindings}
    for name, path in paths.items():
        if digest_file(path) != bindings[name]:
            raise ValueError('executed source binding differs: ' + name)
    return {'basis': 'fixed_historical_producer_preimages', 'native_replay': False,
            'files': {name: path.relative_to(ROOT).as_posix() for name, path in paths.items()}}


def check_abstract_manifests(retained, fresh=None):
    """Check the saved source era and, optionally, a separately generated map."""
    binding_map(retained.get('inputs'), ABSTRACT)
    if retained['inputs'] != ABSTRACT:
        raise ValueError('unknown retained abstract source identity map')
    historical = {
        'src/run_all.py': ROOT/'source-preimages/abstract/run_all.py',
        'src/woc.py': ROOT/'source-preimages/source-execution/woc.py',
        'src/witness_checks.py': ROOT/'src/witness_checks.py',
    }
    for name, path in historical.items():
        if digest_file(path) != ABSTRACT[name]:
            raise ValueError('retained abstract source preimage differs: ' + name)
    outputs = retained.get('outputs')
    binding_map(outputs, ('raw/results.json', 'generated/capacity_table.csv'))
    for name, expected in outputs.items():
        if digest_file(ROOT/name) != expected:
            raise ValueError('retained abstract output differs: ' + name)
    if fresh is not None:
        if set(fresh) != set(retained):
            raise ValueError('fresh abstract manifest schema differs')
        if fresh.get('command') != ABSTRACT_COMMAND:
            raise ValueError('fresh abstract command template differs')
        for field in ('outputs', 'determinism_contract'):
            if fresh[field] != retained[field]:
                raise ValueError('fresh abstract manifest differs: ' + field)
        binding_map(fresh['inputs'], ABSTRACT)
        for name, expected in fresh['inputs'].items():
            if digest_file(ROOT/name) != expected:
                raise ValueError('fresh abstract source differs: ' + name)
    return {'historical_source_preimages_verified': True, 'native_replay': False,
            'fresh_manifest_checked': fresh is not None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--abstract-fresh', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check_abstract_manifests(
        json.loads((ROOT/'current-source-manifest.json').read_text(encoding='utf-8')),
        json.loads(args.abstract_fresh.read_text(encoding='utf-8')))))
