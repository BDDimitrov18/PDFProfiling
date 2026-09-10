import json
import unittest
from unittest.mock import patch
from model_options import DEFAULT_DEPLOYMENT
from qwen38_client import Qwen38Client
from labeled_qwen38 import LabeledQwen38Client


class LabeledClientTests(unittest.TestCase):
    def test_annotations_preserve_image_order_and_record_sampling(self):
        d=json.loads(DEFAULT_DEPLOYMENT.read_text())
        c=LabeledQwen38Client('http://127.0.0.1:8000/v1',d['served_model'],d,greedy=True)
        original={'messages':[{'content':[{'type':'image_url','image_url':{'url':'first'}},
                                          {'type':'image_url','image_url':{'url':'second'}},
                                          {'type':'text','text':'Question'}]}], 'temperature':0.7}
        frozen=json.dumps(original)
        with patch.object(Qwen38Client,'_request_json',autospec=True,return_value={}) as request:
            c._request_json('/chat/completions',original)
            payload=request.call_args.args[2]
        content=payload['messages'][0]['content']
        self.assertEqual([i['image_url']['url'] for i in content if i['type']=='image_url'],['first','second'])
        self.assertIn('IMAGE 1',content[0]['text']);self.assertIn('IMAGE 2',content[3]['text'])
        self.assertEqual(json.dumps(original),frozen)
        self.assertEqual(payload['temperature'],0.0)
        self.assertEqual(c.model_details()['generation']['presence_penalty'],0.0)


if __name__=='__main__':unittest.main()
