"""Read-only scientific-row/source/count checks; no source functions executed."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import source_language as source
import arithmetic_language as language

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
    for line in (out/'rows.jsonl').read_text(encoding='utf-8').splitlines():
        row=json.loads(line)
        n=row['n']
        if n not in (0,1,2,3,7):raise ValueError('unexpected site bound')
        inputs=[tuple(x) for x in row['inputs']]
        expected=[tuple(x+1 for x in args) for args in inputs]
        if len(inputs)!=(1<<n) or any(len(x)!=n or any(type(v) is not int or v not in (0,1) for v in x) for x in inputs):
            raise ValueError('incomplete Boolean context set')
        if len(set(inputs))!=len(inputs) or [tuple(x) for x in row['reference_returns']]!=expected:
            raise ValueError('context/reference mismatch')
        p=model(row['source'])
        pb,pt=language.shape(p)
        if n<=3:
            small+=1
            if [tuple(x) for x in row['source_native_returns']]!=expected:raise ValueError('source return mismatch')
            if row['source'] not in baseline_seen:
                baseline_seen.add(row['source']);calls+=len(inputs);compilations+=1
        for w in row['witnesses']:
            q=model(w['program']);qb,qt=language.shape(q)
            if qt!=pt or sum(a!=b for a,b in zip(pb,qb,strict=True))>1:raise ValueError('witness edit-budget mismatch')
            if language.syndrome(q,row['normalized_sites'])!=w['message']:raise ValueError('recovery mismatch')
            if [tuple(x) for x in w['native_returns']]!=expected:raise ValueError('native return mismatch')
            calls+=len(inputs);compilations+=1
            if n<=3:witnesses+=1
            else:large+=1
            for a in w.get('attacks',[]):
                q2=model(a['program'])
                if language.syndrome(q2,row['normalized_sites'])!=w['message']:raise ValueError('attack label mismatch')
                if [tuple(x) for x in a['native_returns']]!=expected:raise ValueError('attack native return mismatch')
                calls+=len(inputs);compilations+=1;attacks+=1
        rows+=1
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
