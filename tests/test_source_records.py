"""Benign in-memory regressions for retained source-record semantics."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import check_source
import retained_sources

OUT=Path(__file__).resolve().parents[1]/'results/source-execution'

class SourceRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[json.loads(line) for line in (OUT/'rows.jsonl').read_text(encoding='utf-8').splitlines()]
        cls.raw=(OUT/'rows.jsonl').read_bytes()
        cls.summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
        cls.negative=json.loads((OUT/'negative.json').read_text(encoding='utf-8'))

    def check_rows(self,rows,summary=None,negative=None):
        raw=(self.raw if rows is self.rows else
             ('\n'.join(json.dumps(row,separators=(',',':')) for row in rows)+'\n').encode())
        summary=copy.deepcopy(self.summary if summary is None else summary)
        summary['rows_sha256']=hashlib.sha256(raw).hexdigest()
        read_text,read_bytes=Path.read_text,Path.read_bytes
        def text(path,*args,**kwargs):
            if path==OUT/'rows.jsonl':return raw.decode()
            if path==OUT/'summary.json':return json.dumps(summary)
            if path==OUT/'negative.json' and negative is not None:return json.dumps(negative)
            return read_text(path,*args,**kwargs)
        def data(path):
            return raw if path==OUT/'rows.jsonl' else read_bytes(path)
        with patch.object(Path,'read_text',text),patch.object(Path,'read_bytes',data):
            return check_source.check(OUT)

    def test_retained_records_pass_without_native_reexecution(self):
        result=self.check_rows(self.rows)
        self.assertEqual(result['rows'],841)
        self.assertFalse(result['semantic_or_native_rerun'])
        self.assertEqual(result['native_calls_recorded'],290997)
        self.assertEqual(result['native_compilations_recorded'],5820)
        self.assertEqual(result['validation_mode'],'data_only_derivation_no_native_replay')
        self.assertEqual(result['source_binding_resolution']['basis'],'fixed_historical_producer_preimages')
        self.assertFalse(result['source_binding_resolution']['native_replay'])

    def test_source_parameters_are_typed_and_match_the_record(self):
        for field,value in [('n',False),('order',1),('naming',1),('normalized_sites',[False])]:
            rows=copy.deepcopy(self.rows);rows[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.check_rows(rows)
        rows=copy.deepcopy(self.rows)
        target=next(row for row in rows if row['n']==1 and row['order']==0 and row['naming']==0)
        target['source']=next(row['source'] for row in rows if row['n']==1 and row['order']==1 and row['naming']==0)
        with self.assertRaisesRegex(ValueError,'source parameters'):self.check_rows(rows)
        bindings=self.summary['source_sha256']
        mutants=[{},None,[],dict(bindings,unexpected='0'*64)]
        for key in bindings:
            missing=dict(bindings);missing.pop(key);mutants.append(missing)
            for bad in ('0'*64,'not-a-digest',True):
                mutants.append(dict(bindings,**{key:bad}))
        for mutant in mutants:
            with self.subTest(bindings=mutant),self.assertRaises(ValueError):
                self.check_rows(self.rows,summary=dict(self.summary,source_sha256=mutant))
        # A fixed historical map is useful only with every actual old byte file.
        original_bytes=Path.read_bytes
        original_is_file=Path.is_file
        for name in bindings:
            target=retained_sources.ROOT/'source-preimages/source-execution'/name
            def changed(path):
                return b'changed owned preimage' if path==target else original_bytes(path)
            with patch.object(Path,'read_bytes',changed),self.assertRaisesRegex(ValueError,'binding differs'):
                self.check_rows(self.rows)
            def missing(path):
                return False if path==target else original_is_file(path)
            with patch.object(Path,'is_file',missing),self.assertRaisesRegex(ValueError,'missing or nonregular'):
                self.check_rows(self.rows)
        with tempfile.TemporaryDirectory() as directory,patch.object(retained_sources,'ROOT',Path(directory)):
            with self.assertRaisesRegex(ValueError,'missing or nonregular'):
                retained_sources.resolve_source_execution(bindings)
        current={name:hashlib.sha256((retained_sources.ROOT/'src'/name).read_bytes()).hexdigest()
                 for name in bindings}
        with self.assertRaisesRegex(ValueError,'unknown retained'):
            self.check_rows(self.rows,summary=dict(self.summary,source_sha256=current))

    def test_generated_attack_membership_and_recorded_labels(self):
        for mode in ('identity','missing','decoded'):
            rows=copy.deepcopy(self.rows)
            row=next(row for row in rows if row['n']==1 and row['order']==0 and row['naming']==1)
            witness=row['witnesses'][0]
            if mode=='identity':witness['attacks'][0]['program']=witness['program']
            elif mode=='missing':witness['attacks']=[]
            else:witness['attacks'][0]['decoded']=1-witness['message']
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.check_rows(rows)
        def changed(case,field,value):
            negative=copy.deepcopy(self.negative);negative[case][field]=value;return negative
        mutations=[[],self.negative[:1],self.negative+[{'case':'unexpected'}],
                   changed(0,'source_text','not Python; no evidence'),
                   changed(0,'input',[0,0]),changed(0,'reference_return',[True,2]),
                   changed(0,'native_return',[False,2]),changed(0,'admission_error','different error'),
                   changed(0,'case','wrong case'),changed(1,'native_returns',[[999],[999]]),
                   changed(1,'native_returns',[[True],[2]]),changed(1,'inputs',[[False],[1]]),
                   changed(1,'marked','0'*64),changed(1,'normalized','../foreign'),
                   changed(1,'requested',True),changed(1,'decoded_after_normalization',False)]
        missing=copy.deepcopy(self.negative);missing[0].pop('source_text');mutations.append(missing)
        extra=copy.deepcopy(self.negative);extra[1]['extra']=1;mutations.append(extra)
        # Standalone negative validator uses the same byte-bound owned models,
        # not a native compiler or the original producer.
        def model(identifier):
            data=(OUT/'programs'/(identifier+'.py')).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),identifier)
            return check_source.source.parse_source(data.decode('utf-8'))
        self.assertEqual(check_source.check_negatives(self.negative,model),(3,2))
        for negative in mutations:
            with self.subTest(negative=negative),self.assertRaises(ValueError):
                self.check_rows(self.rows,negative=negative)

    def test_protocol_completeness_and_message_coverage(self):
        rows=copy.deepcopy(self.rows);rows[-1]=copy.deepcopy(rows[-2])
        with self.assertRaisesRegex(ValueError,'duplicate'):self.check_rows(rows)
        rows=copy.deepcopy(self.rows);rows[-1]['witnesses'][1]['message']=0
        with self.assertRaisesRegex(ValueError,'witness messages'):self.check_rows(rows)
        rows=copy.deepcopy(self.rows)
        row=next(row for row in rows if row['n']==1)
        row['witnesses'][0]['native_returns'][0][0]=True
        with self.assertRaisesRegex(ValueError,'native return'):self.check_rows(rows)
        for key,value in self.summary['counts'].items():
            for bad in (value+1,True):
                summary=copy.deepcopy(self.summary);summary['counts'][key]=bad
                with self.subTest(count=key,value=bad),self.assertRaises(ValueError):
                    self.check_rows(self.rows,summary=summary)
        for key,bad in [('counts',{}),('protocol',{}),('program_files',True),
                        ('reference_capacity_small',[True,2,2,4]),
                        ('capacity_or_novelty_established_by_native_counts',0),
                        ('unexecuted_scope','all naming patterns executed')]:
            with self.subTest(summary=key),self.assertRaises(ValueError):
                self.check_rows(self.rows,summary=dict(self.summary,**{key:bad}))
        summary=copy.deepcopy(self.summary);summary['counts']['small_witnesses']=0
        with self.assertRaises(ValueError):self.check_rows(self.rows,summary=summary)
        with self.assertRaisesRegex(ValueError,'duplicate JSON'):
            check_source.read_json('{"n":0,"n":0}')

if __name__=='__main__':unittest.main()
