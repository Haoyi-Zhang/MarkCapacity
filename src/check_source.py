"""Read-only scientific-row/source/count checks; no source functions executed."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from itertools import product

import source_language as source
import arithmetic_language as language

def same_returns(record, expected):
    return (type(record) is list and len(record)==len(expected)
            and all(type(row) is list and len(row)==len(want)
                    and all(type(value) is int for value in row)
                    and tuple(row)==want for row,want in zip(record,expected,strict=True)))

def check(out):
    summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
    for name,digest in summary['source_sha256'].items():
        if Path(name).name!=name or hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('executed source binding differs')
    if hashlib.sha256((out/'rows.jsonl').read_bytes()).hexdigest()!=summary['rows_sha256']:
        raise ValueError('row binding differs')
    program_cache={}
    def model(identifier):
        if not re.fullmatch('[0-9a-f]{64}',identifier):raise ValueError('invalid source identifier')
        if identifier not in program_cache:
            data=(out/'programs'/(identifier+'.py')).read_bytes()
            if hashlib.sha256(data).hexdigest()!=identifier:raise ValueError('program byte binding differs')
            program_cache[identifier]=source.parse_source(data.decode('utf-8'))
        return program_cache[identifier]
    rows=small=witnesses=large=attacks=calls=compilations=0
    baseline_seen=set()
    seen_rows=set()
    expected_rows={(n,b,t,tuple(i for i in range(n) if mask&(1<<i)))
                   for n in range(4) for b,t in product(range(1<<n),repeat=2)
                   for mask in range(1<<n)}
    expected_rows.update((7,b,t,()) for b in range(128) for t in (0,127))
    for line in (out/'rows.jsonl').read_text(encoding='utf-8').splitlines():
        row=json.loads(line)
        n=row['n']
        if type(n) is not int or n not in (0,1,2,3,7):raise ValueError('unexpected site bound')
        if any(type(row[name]) is not int or not 0<=row[name]<(1<<n)
               for name in ('order','naming')):raise ValueError('source mask outside protocol')
        sites=row['normalized_sites']
        if (type(sites) is not list or any(type(site) is not int or not 0<=site<n for site in sites)
                or sites!=sorted(set(sites))):raise ValueError('invalid normalization sites')
        key=(n,row['order'],row['naming'],tuple(sites))
        if key not in expected_rows or key in seen_rows:raise ValueError('duplicate or unexpected protocol row')
        seen_rows.add(key)
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
    negative=json.loads((out/'negative.json').read_text(encoding='utf-8'))
    if (negative[0]['native_return']!=[2,2] or negative[0]['reference_return']!=[1,2]
            or negative[1]['decoded_after_normalization']!=0):raise ValueError('negative evidence changed')
    calls+=3;compilations+=2  # One recorded binding call and two normalization calls.
    counts=summary['counts']
    if (rows,small,witnesses,large,attacks,calls,compilations)!=(841,585,1213,2048,2472,290997,5820):
        raise ValueError('recorded execution count mismatch')
    if calls!=counts['native_function_calls'] or compilations!=counts['native_function_compilations']:
        raise ValueError('summary execution count mismatch')
    if len(list((out/'programs').glob('*.py')))!=summary['program_files']:raise ValueError('program inventory mismatch')
    return {'rows':rows,'native_calls_recorded':calls,'native_compilations_recorded':compilations,
            'source_bindings_match':True,'semantic_or_native_rerun':False,'status':'scientific records consistent'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    print(json.dumps(check(p.parse_args().out),indent=2))
