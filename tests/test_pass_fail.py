import copy
import unittest
from test_server import initial_state,valid_state

class TestPassFail(unittest.TestCase):
 def test_public_assessment_mode_is_optional_and_strict(self):
  for mode in ['numeric','pass-fail',None]:
   s=initial_state();c=dict(id='pf',title='Seminar',number='TEST',ects=4,role='specialisation',subtype='seminar',semester=s['actualPlan']['semesters'][0],status='planned',events=[])
   if mode is not None:c['gradingMode']=mode
   s['actualPlan']['courses']=[c];self.assertTrue(valid_state(s))
   c['gradingMode']='unrecognised';self.assertFalse(valid_state(s))
 def test_no_numeric_grade_can_leak_with_assessment_metadata(self):
  s=initial_state();s['actualPlan']['courses']=[dict(id='pf',title='Seminar',ects=4,role='specialisation',semester=s['actualPlan']['semesters'][0],status='planned',events=[],gradingMode='pass-fail',grade=6)];self.assertFalse(valid_state(s))
