"""Candidate: preserve explicit quantity schedules at structural transitions.

V15 already protects this page type, but its spelling matcher misses doubled н.
Apply at the terminal stage so the experiment cannot alter upstream model queries.
This policy is unpromoted and does not run in the typed-context GPU probe.
"""
import re

QUANTITIES=re.compile(r'количествен{1,2}а\s+сметка|bill\s+of\s+quantities|quantity\s+schedule',re.I)
PROTECTED=('fact_recovery','plot_rule','thermal_rule','anchor_rule','filing_unit_rule',
           'identity_rule','sequence_rule','artifact_rule')

def apply(decisions):
 result={page:dict(d) for page,d in decisions.items()};changes=[]
 for page,d in decisions.items():
  if (d.get('structural_rule')!='internal_structural_calculation'
      or d.get('new_document') is not False or d.get('model_new_document') is not True
      or d.get('model_relationship')!='independent'
      or min(d.get('confidence',0),d.get('page_type_confidence',0))<90
      or any(d.get(k) for k in PROTECTED)
      or not any(QUANTITIES.search(d.get(side+'_heading','')) for side in ('left','right'))):continue
  result[page].update(new_document=True,relationship='independent',
                      terminal_quantity_guard='literal_quantity_schedule_not_structural_body')
  changes.append(dict(page=page,before=False,after=True,reason='quantity_schedule_type_guard'))
 return result,changes
