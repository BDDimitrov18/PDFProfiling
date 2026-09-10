import unittest
from receipt_consistency import apply

TITLE='ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ'
def row(left=TITLE,right=TITLE,new=False,confidence=100):
 return dict(left_heading=left,right_heading=right,new_document=new,page_type_confidence=confidence,left_kind='other',right_kind='other',relationship='independent' if new else 'form_series')
class ReceiptConsistencyTests(unittest.TestCase):
 def test_repairs_same_page_reading_disagreement_inside_batch(self):
  typo='ИЗВЕСТИЕ ЗА ПОСТАВЯНЕ';ds={9:row(),10:row(typo,typo,True),11:row()};out=apply(ds)
  self.assertFalse(out[10]['new_document']);self.assertTrue(ds[10]['new_document']);self.assertEqual(out[10]['left_heading'],typo);self.assertEqual(apply(out),out)
 def test_does_not_coerce_unrelated_title_or_known_typed_instrument(self):
  ds={9:row(),10:row('УДОСТОВЕРЕНИЕ','ПРОТОКОЛ',True),11:row()};self.assertEqual(apply(ds),ds)
  ds[10]=row(TITLE,TITLE,True);ds[10]['right_kind']='coordinate_table';self.assertEqual(apply(ds),ds)
 def test_requires_complete_high_confidence_neighbour_evidence(self):
  ds={9:row(),10:row('ИЗВЕСТИЕ ЗА ПОСТАВЯНЕ','ИЗВЕСТИЕ ЗА ПОСТАВЯНЕ',True),11:row()}
  for p in ds:
   altered={k:dict(v) for k,v in ds.items()};altered[p]['page_type_confidence']=89;self.assertEqual(apply(altered),altered)
  for p in (9,11):
   altered={k:v for k,v in ds.items() if k!=p};self.assertEqual(apply(altered),altered)
 def test_preserves_batch_start_and_single_supporting_receipt(self):
  ds={9:row('СЪОБЩЕНИЕ',TITLE,True),10:row(),11:row(TITLE,'УДОСТОВЕРЕНИЕ',True)};self.assertEqual(apply(ds),ds)
if __name__=='__main__':unittest.main()
