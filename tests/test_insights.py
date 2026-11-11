"""Persistent public notes/advisory assessments must not weaken state validation."""
import copy
import tempfile
import unittest
from test_server import Store,initial_state,valid_state

class TestModuleInsights(unittest.TestCase):
    def fixture(self):
        s=initial_state();p=dict(semester='2026W',assessment='Review calculus',confidence='medium',prerequisites=['Calculus'],gaps=[],recommendations=['Revise differentiation'],source={'document':'Synthetic context'})
        s['moduleInsights']={'number:TEST':{'notes':'Personal course note','preparation':p,'preparations':{'2026W':p}}};return s

    def test_roundtrip_keeps_notes_and_assessments_separate(self):
        s=self.fixture();self.assertTrue(valid_state(s))
        with tempfile.TemporaryDirectory() as d:
            store=Store(d);store.save(s);self.assertEqual(Store(d).get()['moduleInsights'],s['moduleInsights'])

    def test_rejects_malformed_notes_and_assessments(self):
        for value in [None,[],{'x':None},{'x':{'notes':5}},{'x':{'notes':'x'*20001}},{'x':{'preparation':{}}},{'x':{'preparations':[]}}]:
            with self.subTest(value=str(value)[:60]):
                s=initial_state();s['moduleInsights']=value;self.assertFalse(valid_state(s))
        for key,value in [('semester',{'bad':True}),('confidence','certain'),('prerequisites','Calculus'),('assessment',None),('recommendations',['x'*2001])]:
            s=self.fixture();s['moduleInsights']['number:TEST']['preparation'][key]=value;self.assertFalse(valid_state(s))

    def test_private_grade_fields_still_rejected_inside_notes_payload(self):
        s=self.fixture();s['moduleInsights']['number:TEST']['grade']=5
        self.assertFalse(valid_state(s))
