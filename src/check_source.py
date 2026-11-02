"""Read-only scientific-row/source/count checks; no source functions executed."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
from itertools import product

import source_language as source
import arithmetic_language as language
from retained_sources import resolve_source_execution

PROTOCOL = {
    'small_sites': [0, 1, 2, 3], 'small_order_naming': 'all 4^n procedures',
    'normalization': 'all subsets at the small bound', 'larger_sites': 7,
    'larger_naming': [0, 127], 'larger_orders': 'all 128', 'larger_messages': 'all eight',
    'inputs': 'every Boolean integer tuple at each bound', 'external_targets': 0,
    'grammar': 'owned pure integer addition/tuple return',
    'interpretation': 'executable correspondence, not new coding or production robustness',
}
COUNTS = {'small_contract_rows': 585, 'small_witnesses': 1213, 'larger_witnesses': 2048,
          'native_function_calls': 290997, 'native_function_compilations': 5820,
          'native_rewrite_rows': 85, 'generated_attack_checks': 2472,
          'mismatched_returns': 0, 'mismatched_recovery': 0}
UNEXECUTED = 'all other seven-site naming patterns; general Python; production compilers; effects'
NAIVE = 'def carrier(x0, x1):\n    t = x0 + 1\n    t = x1 + 1\n    return (t, t)\n'


def object_fields(value, fields, name):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError('invalid ' + name + ' fields')


def exact(value, expected, name):
    # JSON equality must not identify true with 1, including nested fields.
    if json.dumps(value, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True):
        raise ValueError(name + ' differs from the fixed protocol')


def read_json(text):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('duplicate JSON field: ' + key)
            out[key] = value
        return out
    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON value')))


def check_summary(summary):
    object_fields(summary, ('source_sha256', 'rows_sha256', 'counts', 'program_files',
                  'protocol', 'environment', 'reference_capacity_small',
                  'capacity_or_novelty_established_by_native_counts', 'unexecuted_scope'), 'summary')
    binding = resolve_source_execution(summary['source_sha256'])
    if type(summary['rows_sha256']) is not str or re.fullmatch('[0-9a-f]{64}', summary['rows_sha256']) is None:
        raise ValueError('row binding requires SHA-256')
    exact(summary['protocol'], PROTOCOL, 'summary protocol')
    exact(summary['counts'], COUNTS, 'summary counts')
    exact(summary['reference_capacity_small'], [1, 2, 2, 4], 'reference capacity')
    exact(summary['program_files'], 341, 'program count')
    exact(summary['capacity_or_novelty_established_by_native_counts'], False, 'capacity claim')
    exact(summary['unexecuted_scope'], UNEXECUTED, 'unexecuted scope')
    object_fields(summary['environment'], ('python', 'platform', 'implementation'), 'recorded environment')
    if any(type(s) is not str or not s.strip() for s in summary['environment'].values()):
        raise ValueError('recorded environment must contain nonempty strings')
    return binding


def check_negatives(negative, model):
    """Bind the two owned legacy cases, then derive their values as data only."""
    if type(negative) is not list or len(negative) != 2:
        raise ValueError('exactly two negative cases required')
    first, second = negative
    object_fields(first, ('case', 'source_text', 'input', 'native_return',
                         'reference_return', 'admission_error'), 'binding negative')
    exact(first['case'], 'function-local-reuse-is-not-component-local', 'negative case')
    exact(first['source_text'], NAIVE, 'negative source identity')
    exact(first['input'], [0, 1], 'negative context')
    # Parse only after binding the exact fixed text. No compile/exec/eval or
    # imported historical implementation is used to replay the claimed run.
    function = ast.parse(first['source_text']).body[0]
    values = dict(zip(('x0', 'x1'), first['input']))
    for statement in function.body[:-1]:
        expression = statement.value
        values[statement.targets[0].id] = values[expression.left.id] + expression.right.value
    derived = [values[node.id] for node in function.body[-1].value.elts]
    exact(first['native_return'], derived, 'negative native return')
    exact(first['reference_return'], [x + 1 for x in first['input']], 'negative reference return')
    try:
        source.parse_source(first['source_text'])
    except ValueError as error:
        exact(first['admission_error'], str(error), 'negative admission error')
    else:
        raise ValueError('binding negative was admitted')
    object_fields(second, ('case', 'marked', 'normalized', 'requested',
                          'decoded_after_normalization', 'inputs', 'native_returns'), 'normalization negative')
    exact(second['case'], 'undeclared-operand-normalization', 'negative case')
    exact(second['requested'], 1, 'negative request')
    exact(second['inputs'], [[0], [1]], 'negative contexts')
    for name, order in (('marked', 1), ('normalized', 0)):
        expected = language.make_procedure(1, order, 0)
        identifier = hashlib.sha256(source.render(expected).encode('utf-8')).hexdigest()
        exact(second[name], identifier, 'negative program identity')
        if model(second[name]) != expected:
            raise ValueError('negative parsed program differs')
    normalized = model(second['normalized'])
    exact(second['decoded_after_normalization'], language.syndrome(normalized), 'negative decoded label')
    expected = [language.evaluate(normalized, tuple(x)) for x in second['inputs']]
    if not same_returns(second['native_returns'], expected):
        raise ValueError('negative native returns differ')
    return 1 + len(second['inputs']), 2

def same_returns(record, expected):
    return (type(record) is list and len(record)==len(expected)
            and all(type(row) is list and len(row)==len(want)
                    and all(type(value) is int for value in row)
                    and tuple(row)==want for row,want in zip(record,expected,strict=True)))

def _check(out):
    summary=read_json((out/'summary.json').read_text(encoding='utf-8'))
    binding=check_summary(summary)
    if hashlib.sha256((out/'rows.jsonl').read_bytes()).hexdigest()!=summary['rows_sha256']:
        raise ValueError('row binding differs')
    program_cache={}
    def model(identifier):
        if type(identifier) is not str or not re.fullmatch('[0-9a-f]{64}',identifier):raise ValueError('invalid source identifier')
        if identifier not in program_cache:
            path=out/'programs'/(identifier+'.py')
            if path.is_symlink() or not path.is_file():raise ValueError('program must be a regular owned file')
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest()!=identifier:raise ValueError('program byte binding differs')
            program_cache[identifier]=source.parse_source(data.decode('utf-8'))
        return program_cache[identifier]
    negative_calls,negative_compilations=check_negatives(
        read_json((out/'negative.json').read_text(encoding='utf-8')), model)
    rows=small=witnesses=large=attacks=calls=compilations=0
    baseline_seen=set()
    seen_rows=set()
    expected_rows={(n,b,t,tuple(i for i in range(n) if mask&(1<<i)))
                   for n in range(4) for b,t in product(range(1<<n),repeat=2)
                   for mask in range(1<<n)}
    expected_rows.update((7,b,t,()) for b in range(128) for t in (0,127))
    for line in (out/'rows.jsonl').read_text(encoding='utf-8').splitlines():
        row=read_json(line)
        if type(row) is not dict:raise ValueError('protocol row must be an object')
        n=row['n']
        if type(n) is not int or n not in (0,1,2,3,7):raise ValueError('unexpected site bound')
        fields={'n','order','naming','normalized_sites','source','inputs','reference_returns','witnesses'}
        object_fields(row,fields|({'source_native_returns'} if n<=3 else set()),'protocol row')
        if any(type(row[name]) is not int or not 0<=row[name]<(1<<n)
               for name in ('order','naming')):raise ValueError('source mask outside protocol')
        sites=row['normalized_sites']
        if (type(sites) is not list or any(type(site) is not int or not 0<=site<n for site in sites)
                or sites!=sorted(set(sites))):raise ValueError('invalid normalization sites')
        key=(n,row['order'],row['naming'],tuple(sites))
        if key not in expected_rows or key in seen_rows:raise ValueError('duplicate or unexpected protocol row')
        seen_rows.add(key)
        if type(row['inputs']) is not list or any(type(x) is not list for x in row['inputs']):
            raise ValueError('Boolean context vectors required')
        inputs=[tuple(x) for x in row['inputs']]
        expected=[tuple(x+1 for x in args) for args in inputs]
        if len(inputs)!=(1<<n) or any(len(x)!=n or any(type(v) is not int or v not in (0,1) for v in x) for x in inputs):
            raise ValueError('incomplete Boolean context set')
        if len(set(inputs))!=len(inputs) or not same_returns(row['reference_returns'],expected):
            raise ValueError('context/reference mismatch')
        p=model(row['source'])
        if p!=language.make_procedure(n,row['order'],row['naming']):
            raise ValueError('source parameters disagree with parsed program')
        pb,pt=language.shape(p)
        if n<=3:
            small+=1
            if not same_returns(row['source_native_returns'],expected):raise ValueError('source return mismatch')
            if row['source'] not in baseline_seen:
                baseline_seen.add(row['source']);calls+=len(inputs);compilations+=1
        messages=1<<((n-len(sites)+1).bit_length()-1)
        if type(row['witnesses']) is not list:raise ValueError('witness list required')
        for witness in row['witnesses']:
            fields={'message','program','decoded','native_returns'}
            object_fields(witness,fields|({'attacks'} if n<=3 else set()),'witness')
        if (type(row['witnesses']) is not list or
                [w['message'] for w in row['witnesses']]!=list(range(messages)) or
                any(type(w['message']) is not int for w in row['witnesses'])):
            raise ValueError('incomplete or repeated witness messages')
        for w in row['witnesses']:
            q=model(w['program']);qb,qt=language.shape(q)
            if qt!=pt or sum(a!=b for a,b in zip(pb,qb,strict=True))>1:raise ValueError('witness edit-budget mismatch')
            if language.syndrome(q,row['normalized_sites'])!=w['message']:raise ValueError('recovery mismatch')
            if type(w['decoded']) is not int or w['decoded']!=w['message']:
                raise ValueError('recorded witness label mismatch')
            if not same_returns(w['native_returns'],expected):raise ValueError('native return mismatch')
            calls+=len(inputs);compilations+=1
            if n<=3:witnesses+=1
            else:large+=1
            recorded_attacks=w.get('attacks',[])
            if type(recorded_attacks) is not list:raise ValueError('attack list required')
            for attack in recorded_attacks:
                object_fields(attack,('program','decoded','native_returns'),'attack')
            expected_attacks=language.attack_targets(q,sites) if n<=3 else ()
            observed_attacks=[model(a['program']) for a in recorded_attacks]
            if (len(observed_attacks)!=len(set(observed_attacks)) or
                    set(observed_attacks)!=set(expected_attacks)):
                raise ValueError('recorded attacks differ from generated attack set')
            for a,q2 in zip(recorded_attacks,observed_attacks,strict=True):
                if language.syndrome(q2,row['normalized_sites'])!=w['message']:raise ValueError('attack label mismatch')
                if type(a['decoded']) is not int or a['decoded']!=w['message']:
                    raise ValueError('recorded attack label mismatch')
                if not same_returns(a['native_returns'],expected):raise ValueError('attack native return mismatch')
                calls+=len(inputs);compilations+=1;attacks+=1
        rows+=1
    if seen_rows!=expected_rows:raise ValueError('incomplete protocol row set')
    calls+=negative_calls;compilations+=negative_compilations
    derived={'small_contract_rows':small,'small_witnesses':witnesses,'larger_witnesses':large,
             'native_function_calls':calls,'native_function_compilations':compilations,
             'native_rewrite_rows':len(baseline_seen),'generated_attack_checks':attacks,
             'mismatched_returns':0,'mismatched_recovery':0}
    exact(derived,summary['counts'],'derived summary counts')
    if rows!=841:raise ValueError('recorded row count mismatch')
    inventory=list((out/'programs').iterdir())
    if (len(inventory)!=summary['program_files'] or
            {p.name for p in inventory}!={identifier+'.py' for identifier in program_cache} or
            any(p.is_symlink() or not p.is_file() for p in inventory)):
        raise ValueError('program inventory mismatch')
    return {'rows':rows,'native_calls_recorded':calls,'native_compilations_recorded':compilations,
            'source_bindings_match':True,'source_binding_resolution':binding,
            'semantic_or_native_rerun':False,'validation_mode':'data_only_derivation_no_native_replay',
            'status':'scientific records consistent'}


def check(out):
    try:
        return _check(Path(out))
    except (KeyError, TypeError, AttributeError, IndexError, OSError, UnicodeError) as error:
        raise ValueError('malformed or missing source record: ' + str(error)) from error

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    print(json.dumps(check(p.parse_args().out),indent=2))
