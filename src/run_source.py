"""Fixed owned source-execution campaign; separate from the historical census."""
import argparse
import builtins
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import sys

import arithmetic_language as language
import source_language as source

PROTOCOL={'small_sites':[0,1,2,3],'small_order_naming':'all 4^n procedures',
          'normalization':'all subsets at the small bound',
          'larger_sites':7,'larger_naming':[0,127],
          'larger_orders':'all 128','larger_messages':'all eight',
          'inputs':'every Boolean integer tuple at each bound',
          'external_targets':0,'grammar':'owned pure integer addition/tuple return',
          'interpretation':'executable correspondence, not new coding or production robustness'}

def main(out):
    out.mkdir(parents=True,exist_ok=False)
    programs=out/'programs'
    programs.mkdir()
    counts={'small_contract_rows':0,'small_witnesses':0,'larger_witnesses':0,
            'native_function_calls':0,'native_function_compilations':0,
            'native_rewrite_rows':0,'generated_attack_checks':0,
            'mismatched_returns':0,'mismatched_recovery':0}
    def compile(text):
        counts['native_function_compilations']+=1
        return source.compile_source(text)
    def call(fn,args):
        value=fn(args)
        counts['native_function_calls']+=1
        return value
    def save_program(text):
        digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
        path=programs/(digest+'.py')
        if not path.exists():
            path.write_text(text,encoding='utf-8',newline='\n')
        return digest
    with (out/'rows.jsonl').open('w',encoding='utf-8',newline='\n') as rows:
        for n in PROTOCOL['small_sites']:
            inputs=tuple(product((0,1),repeat=n))
            for b,t in product(range(1<<n),repeat=2):
                p=language.make_procedure(n,b,t)
                text=source.render(p)
                text_id=save_program(text)
                actual_access={source.parse_source(s) for s in source.source_reachable(text)}
                if actual_access!=language.reachable(p):
                    raise AssertionError('AST and model edit-budget images differ')
                counts['native_rewrite_rows']+=1
                baseline=compile(text)
                baseline_outputs=[call(baseline,x) for x in inputs]
                expected=[language.evaluate(p,x) for x in inputs]
                if baseline_outputs!=expected:
                    raise AssertionError('native source behavior differs')
                for mask in range(1<<n):
                    sites=tuple(i for i in range(n) if mask&(1<<i))
                    messages=1<<((n-len(sites)+1).bit_length()-1)
                    witnesses=[]
                    for m in range(messages):
                        marked=source.encode(text,m,sites)
                        marked_id=save_program(marked)
                        native=compile(marked)
                        outputs=[call(native,x) for x in inputs]
                        if outputs!=expected or source.decode(marked,sites)!=m:
                            raise AssertionError('native witness behavior/recovery differs')
                        pb,pt=language.shape(p)
                        qb,qt=language.shape(source.parse_source(marked))
                        if qt!=pt or sum(a!=b for a,b in zip(pb,qb,strict=True))>1:
                            raise AssertionError('source selector exceeded edit budget')
                        attacks=[]
                        for target in source.attack_sources(marked,sites):
                            label=source.decode(target,sites)
                            attacked_native=compile(target)
                            attack_outputs=[call(attacked_native,x) for x in inputs]
                            if label!=m or attack_outputs!=expected:
                                raise AssertionError('declared native attack breaks contract')
                            attacks.append({'program':save_program(target),'decoded':label,
                                            'native_returns':attack_outputs})
                            counts['generated_attack_checks']+=1
                        witnesses.append({'message':m,'program':marked_id,'decoded':m,
                                          'native_returns':outputs,'attacks':attacks})
                        counts['small_witnesses']+=1
                    row={'n':n,'order':b,'naming':t,'normalized_sites':sites,
                         'source':text_id,'inputs':inputs,'reference_returns':expected,
                         'source_native_returns':baseline_outputs,'witnesses':witnesses}
                    rows.write(json.dumps(row,separators=(',',':'))+'\n')
                    counts['small_contract_rows']+=1
        n=PROTOCOL['larger_sites']
        inputs=tuple(product((0,1),repeat=n))
        for b,t in product(range(128),PROTOCOL['larger_naming']):
            p=language.make_procedure(n,b,t)
            text=source.render(p)
            expected=[language.evaluate(p,x) for x in inputs]
            witnesses=[]
            for m in range(8):
                marked=source.encode(text,m)
                native=compile(marked)
                outputs=[call(native,x) for x in inputs]
                if outputs!=expected or source.decode(marked)!=m:
                    raise AssertionError('seven-site native correspondence failure')
                witnesses.append({'message':m,'program':save_program(marked),
                                  'decoded':m,'native_returns':outputs})
                counts['larger_witnesses']+=1
            rows.write(json.dumps({'n':n,'order':b,'naming':t,'normalized_sites':[],
                                  'source':save_program(text),'inputs':inputs,
                                  'reference_returns':expected,'witnesses':witnesses},
                                 separators=(',',':'))+'\n')
    # Two fixed benign negatives; neither is a production watermark attack.
    naive='def carrier(x0, x1):\n    t = x0 + 1\n    t = x1 + 1\n    return (t, t)\n'
    namespace={'__builtins__':{}}
    exec(builtins.compile(naive,'<owned-binding-counterexample>','exec'),namespace)
    actual=namespace['carrier'](0,1)
    counts['native_function_calls']+=1
    counts['native_function_compilations']+=1
    try:
        source.parse_source(naive)
    except ValueError as error:
        admission_error=str(error)
    else:
        raise AssertionError('aliased temporary admitted')
    original=source.render(language.make_procedure(1))
    marked=source.encode(original,1)
    excluded=source.commute(marked,0)
    excluded_native=compile(excluded)
    negative=[{'case':'function-local-reuse-is-not-component-local',
               'source_text':naive,'input':[0,1],'reference_return':[1,2],
               'native_return':actual,'admission_error':admission_error},
              {'case':'undeclared-operand-normalization',
               'marked':save_program(marked),'normalized':save_program(excluded),
               'requested':1,'decoded_after_normalization':source.decode(excluded),
               'inputs':[[0],[1]],'native_returns':[call(excluded_native,x) for x in ((0,),(1,))]}]
    assert counts['small_contract_rows']==585 and counts['small_witnesses']==1213
    assert counts['native_rewrite_rows']==85 and counts['larger_witnesses']==2048
    bindings={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (Path(__file__).parent/name for name in
                        ('run_source.py','source_language.py','arithmetic_language.py','woc.py'))}
    summary={'protocol':PROTOCOL,'counts':counts,'source_sha256':bindings,
             'program_files':len(list(programs.glob('*.py'))),
             'rows_sha256':hashlib.sha256((out/'rows.jsonl').read_bytes()).hexdigest(),
             'reference_capacity_small':[1,2,2,4],
             'capacity_or_novelty_established_by_native_counts':False,
             'environment':{'python':sys.version,'platform':platform.platform(),
                            'implementation':platform.python_implementation()},
             'unexecuted_scope':'all other seven-site naming patterns; general Python; production compilers; effects'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    (out/'negative.json').write_text(json.dumps(negative,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    main(parser.parse_args().out.resolve())
