"""Benign in-memory regressions for retained source-record semantics."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import check_source

OUT=Path(__file__).resolve().parents[1]/'results/source-execution'

class SourceRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[json.loads(line) for line in (OUT/'rows.jsonl').read_text(encoding='utf-8').splitlines()]
        cls.summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))

    def check_rows(self,rows):
        raw=('\n'.join(json.dumps(row,separators=(',',':')) for row in rows)+'\n').encode()
        summary=copy.deepcopy(self.summary)
        summary['rows_sha256']=hashlib.sha256(raw).hexdigest()
        read_text,read_bytes=Path.read_text,Path.read_bytes
        def text(path,*args,**kwargs):
            if path==OUT/'rows.jsonl':return raw.decode()
            if path==OUT/'summary.json':return json.dumps(summary)
            return read_text(path,*args,**kwargs)
        def data(path):
            return raw if path==OUT/'rows.jsonl' else read_bytes(path)
        with patch.object(Path,'read_text',text),patch.object(Path,'read_bytes',data):
            return check_source.check(OUT)

    def test_retained_records_pass_without_native_reexecution(self):
        result=self.check_rows(self.rows)
        self.assertEqual(result['rows'],841)
        self.assertFalse(result['semantic_or_native_rerun'])

    def test_source_parameters_are_typed_and_match_the_record(self):
        for field,value in [('n',False),('order',1),('naming',1),('normalized_sites',[False])]:
            rows=copy.deepcopy(self.rows);rows[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.check_rows(rows)
        rows=copy.deepcopy(self.rows)
        target=next(row for row in rows if row['n']==1 and row['order']==0 and row['naming']==0)
        target['source']=next(row['source'] for row in rows if row['n']==1 and row['order']==1 and row['naming']==0)
        with self.assertRaisesRegex(ValueError,'source parameters'):self.check_rows(rows)

    def test_generated_attack_membership_and_recorded_labels(self):
        for mode in ('identity','missing','decoded'):
            rows=copy.deepcopy(self.rows)
            row=next(row for row in rows if row['n']==1 and row['order']==0 and row['naming']==1)
            witness=row['witnesses'][0]
            if mode=='identity':witness['attacks'][0]['program']=witness['program']
            elif mode=='missing':witness['attacks']=[]
            else:witness['attacks'][0]['decoded']=1-witness['message']
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.check_rows(rows)

    def test_protocol_completeness_and_message_coverage(self):
        rows=copy.deepcopy(self.rows);rows[-1]=copy.deepcopy(rows[-2])
        with self.assertRaisesRegex(ValueError,'duplicate'):self.check_rows(rows)
        rows=copy.deepcopy(self.rows);rows[-1]['witnesses'][1]['message']=0
        with self.assertRaisesRegex(ValueError,'witness messages'):self.check_rows(rows)
        rows=copy.deepcopy(self.rows)
        row=next(row for row in rows if row['n']==1)
        row['witnesses'][0]['native_returns'][0][0]=True
        with self.assertRaisesRegex(ValueError,'native return'):self.check_rows(rows)

if __name__=='__main__':unittest.main()
