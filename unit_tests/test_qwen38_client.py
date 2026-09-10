import base64
import copy
import io
import json
import logging
import os
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from PIL import Image

from qwen38_client import Qwen38Client, Qwen38Error


MODEL = 'qwen3.8-27b-009632fe'
DEPLOYMENT = {'version': 1, 'served_model': MODEL, 'revision': 'a' * 40,
              'runtime': {'engine': 'sglang', 'image': 'example@sha256:' + 'b' * 64}}
LOG = logging.getLogger('test-qwen38-client')
LOG.addHandler(logging.NullHandler())


def completion(content='{"starts_new_document": false}', finish='stop', **message_fields):
    return {'model': MODEL, 'choices': [{'finish_reason': finish,
            'message': {'role': 'assistant', 'content': content, **message_fields}}],
            'usage': {'prompt_tokens': 50, 'completion_tokens': 30,
                      'completion_tokens_details': {'reasoning_tokens': 20}}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append(('GET', self.path, None, dict(self.headers)))
        self.reply(self.server.get_status, self.server.models)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append(('POST', self.path, payload, dict(self.headers)))
        status, body = self.server.responses.pop(0) if self.server.responses else (200, completion())
        self.reply(status, body)

    def reply(self, status, body):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        if status == 302:
            self.send_header('Location', self.server.redirect)
        self.end_headers()
        self.wfile.write(raw)


class ClientTests(unittest.TestCase):
    def test_required_schema_is_sent_in_both_reasoning_modes(self):
        for thinking in ('off', 'medium'):
            client = Qwen38Client(self.url, MODEL, DEPLOYMENT, thinking=thinking)
            self.infer(client, response_schema={'end': bool, 'signal_on_page': int,
                       'confidence': 'confidence', 'optional_evidence': (str, type(None))})
            payload = self.server.requests[-1][2]
            response_format = payload['response_format']
            self.assertEqual(response_format['type'], 'json_schema')
            schema = response_format['json_schema']['schema']
            self.assertTrue(response_format['json_schema']['strict'])
            self.assertEqual(set(schema['required']), set(schema['properties']))
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(schema['properties']['optional_evidence'], {'type': ['string', 'null']})
            self.assertEqual(schema['properties']['confidence'],
                             {'type': 'number', 'minimum': 0, 'maximum': 100})
            self.assertEqual(payload['chat_template_kwargs']['enable_thinking'], thinking != 'off')
            self.assertEqual(payload['messages'][0]['content'][-1]['text'], 'unchanged prompt')

    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.requests = []
        self.server.responses = []
        self.server.models = {'data': [{'id': MODEL}]}
        self.server.get_status = 200
        self.server.redirect = 'http://127.0.0.1:1/credential-must-not-be-forwarded'
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.url = f'http://127.0.0.1:{self.server.server_port}/v1'
        self.page = Image.new('RGB', (3, 4), 'red')
        self.client = Qwen38Client(self.url, MODEL, DEPLOYMENT)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def infer(self, client=None, prompt='unchanged prompt', images=None, **kwargs):
        return (client or self.client).infer(prompt, images or [self.page], LOG, **kwargs)

    def test_constructor_does_not_connect_and_verification_requires_exact_model(self):
        self.assertEqual(self.server.requests, [])
        details = self.client.verify()
        self.assertEqual(details['verification'], 'declared_manifest_and_advertised_model_id')
        self.assertEqual(self.server.requests[0][:2], ('GET', '/v1/models'))
        self.assertEqual(self.client.snapshot()['model_calls'], 0)
        self.server.models = {'data': [{'id': MODEL + '-other'}]}
        with self.assertRaisesRegex(Qwen38Error, 'not advertised'):
            self.client.verify()
        self.assertEqual(self.client.model_details()['verification'], 'unverified')
        with self.assertRaisesRegex(Qwen38Error, 'not advertised'):
            self.infer()
        self.assertFalse(any(r[0] == 'POST' for r in self.server.requests))

    def test_images_are_lossless_ordered_and_prompt_and_queries_are_independent(self):
        second = Image.new('RGB', (7, 2), (4, 18, 222))
        prompt = '  Прочети тези две страници.\nReturn JSON unchanged.  '
        with patch.dict(os.environ, {'QWEN38_API_KEY': 'test-secret-key'}):
            self.infer(prompt=prompt, images=[self.page, second], max_tokens=8)
            self.infer(prompt='second independent prompt')
        requests = [r for r in self.server.requests if r[0] == 'POST']
        self.assertEqual(len(requests), 2)
        first = requests[0][2]
        self.assertEqual(requests[0][1], '/v1/chat/completions')
        self.assertEqual(requests[0][3]['Authorization'], 'Bearer test-secret-key')
        self.assertEqual(first['model'], MODEL)
        self.assertFalse(first['stream'])
        self.assertEqual(first['max_tokens'], 4096)
        self.assertEqual(first['chat_template_kwargs'], {'enable_thinking': False, 'preserve_thinking': False})
        self.assertEqual(first['seed'], 0)
        self.assertNotIn('reasoning_effort', first)
        self.assertEqual((first['temperature'], first['top_p'], first['top_k'],
                          first['presence_penalty']), (.7, .8, 20, 1.5))
        self.assertEqual(len(first['messages']), 1)
        self.assertEqual(first['messages'][0]['role'], 'user')
        content = first['messages'][0]['content']
        self.assertEqual(content[-1], {'type': 'text', 'text': prompt})
        for encoded, original in zip(content[:-1], [self.page, second]):
            uri = encoded['image_url']['url']
            self.assertTrue(uri.startswith('data:image/png;base64,'))
            decoded = Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1])))
            self.assertEqual(decoded.format, 'PNG')
            self.assertEqual(decoded.size, original.size)
            self.assertEqual(decoded.tobytes(), original.tobytes())
        self.assertEqual(len(requests[1][2]['messages']), 1)
        self.assertEqual(requests[1][2]['messages'][0]['content'][-1]['text'], 'second independent prompt')
        self.assertNotIn(prompt, json.dumps(requests[1][2]))
        self.assertNotIn('test-secret-key', json.dumps(self.client.model_details()))
        self.assertNotIn('test-secret-key', json.dumps(self.client.snapshot()))

    def test_reasoning_modes_have_explicit_budget_and_never_return_reasoning_content(self):
        for effort in ['low', 'medium', 'xhigh']:
            with self.subTest(effort=effort):
                client = Qwen38Client(self.url, MODEL, DEPLOYMENT, thinking=effort,
                                      max_completion_tokens=8192)
                self.server.responses.append((200, completion('  {"answer":false}\n',
                    reasoning_content='Internal guess: {"answer":true}')))
                self.assertEqual(self.infer(client), '  {"answer":false}\n')
                payload = self.server.requests[-1][2]
                self.assertEqual(payload['reasoning_effort'], effort)
                self.assertEqual(payload['chat_template_kwargs'], {'enable_thinking': True, 'preserve_thinking': False})
                self.assertEqual(payload['seed'], 0)
                self.assertEqual(payload['max_tokens'], 8192)
                self.assertEqual((payload['temperature'], payload['top_p'],
                    payload['top_k'], payload['presence_penalty']), (1, .95, 20, 0))

    def test_inline_reasoning_is_removed_only_as_complete_leading_block(self):
        self.server.responses.append((200, completion('<think>{"wrong":true}</think>\n {"right":true} ')))
        self.assertEqual(self.infer(), '\n {"right":true} ')
        invalid = [
            completion('<think>{"wrong":true}'),
            completion('<think>{"wrong":true}</think>'),
            completion('{"answer":true}</think>'),
            completion('<think>nested <think>wrong</think></think>{"answer":true}'),
            completion('<think>wrong</think><think>more</think>{"answer":true}'),
            completion('<think>wrong</think>{"answer":true}', reasoning_content='separate'),
            completion(None, reasoning_content='{"looks_like_final":true}'),
            completion('   ', reasoning_content='{"looks_like_final":true}'),
        ]
        for response in invalid:
            with self.subTest(response=response):
                self.server.responses.append((200, response))
                with self.assertRaises(Qwen38Error):
                    self.infer()

    def test_failed_and_truncated_responses_are_not_negative_boundary_predictions(self):
        wrong_model = completion()
        wrong_model['model'] = MODEL + '-other'
        malformed_usage = completion()
        malformed_usage['usage']['prompt_tokens'] = -3
        cases = [completion(finish='length'), completion(finish='error'),
                 completion(finish=None), wrong_model, malformed_usage,
                 {'choices': []}, {'choices': [{'finish_reason': 'stop', 'message': {}}]},
                 completion('answer', refusal='No'), completion('answer', tool_calls=[{}]),
                 completion('answer', reasoning_content={'invalid': 'type'}),
                 {'error': {'message': 'private error details'}}, b'not valid JSON',
                 b'{"choices":NaN}', []]
        for response in cases:
            with self.subTest(response=response):
                self.server.responses.append((200, response))
                with self.assertRaises(Qwen38Error):
                    self.infer()
        stats = self.client.snapshot()
        self.assertEqual(stats['successful_calls'], 0)
        self.assertEqual(stats['failed_calls'], len(cases))
        self.assertEqual(stats['model_calls'], len(cases))
        self.assertEqual(stats['successful_seconds'], 0)

    def test_usage_is_counted_for_failed_length_and_missing_usage_is_unavailable(self):
        self.assertIsNone(self.client.last_final_text)
        self.infer()
        self.assertEqual(self.client.last_final_text, '{"starts_new_document": false}')
        self.server.responses.append((200, completion(finish='length')))
        with self.assertRaises(Qwen38Error):
            self.infer()
        self.assertIsNone(self.client.last_final_text)
        snapshot = self.client.snapshot()
        self.assertEqual((snapshot['input_tokens'], snapshot['output_tokens'],
                          snapshot['reasoning_tokens']), (100, 60, 40))
        self.assertEqual((snapshot['successful_calls'], snapshot['failed_calls']), (1, 1))
        self.assertGreater(snapshot['successful_seconds'], 0)
        no_details = completion()
        no_details['usage'].pop('completion_tokens_details')
        self.server.responses.append((200, no_details))
        self.infer()
        stats = self.client.snapshot()
        self.assertEqual(stats['input_tokens'], 150)
        self.assertIsNone(stats['reasoning_tokens'])
        self.assertEqual(stats['known_reasoning_tokens'], 40)
        missing = completion()
        missing.pop('usage')
        self.server.responses.append((200, missing))
        self.infer()
        stats = self.client.snapshot()
        for field in ['input_tokens', 'output_tokens', 'reasoning_tokens']:
            self.assertIsNone(stats[field])
        self.assertEqual(stats['known_input_tokens'], 150)
        self.assertEqual(snapshot['input_tokens'], 100)

    def test_http_and_transport_failures_do_not_leak_credentials_or_server_text(self):
        self.client.verify()
        secret = 'do-not-leak-this-secret'
        with patch.dict(os.environ, {'QWEN38_API_KEY': secret}):
            self.server.responses.append((401, {'error': f'Rejected credential {secret}'}))
            with self.assertRaisesRegex(Qwen38Error, 'HTTP 401') as caught:
                self.infer()
            self.assertNotIn(secret, str(caught.exception))
            with patch.object(self.client._opener, 'open', side_effect=urllib.error.URLError(secret)):
                with self.assertRaisesRegex(Qwen38Error, 'Could not complete') as caught:
                    self.infer()
                self.assertNotIn(secret, str(caught.exception))
        with patch.dict(os.environ, {'QWEN38_API_KEY': secret + '\nwrong'}):
            with self.assertRaisesRegex(Qwen38Error, 'invalid header') as caught:
                self.infer()
            self.assertNotIn(secret, str(caught.exception))
        self.assertEqual(self.client.snapshot()['failed_calls'], 3)
        self.assertIsNone(self.client.snapshot()['input_tokens'])

    def test_sglang_reasoning_usage_supported_and_conflicting_accounting_rejected(self):
        response = completion()
        response['usage'].pop('completion_tokens_details')
        response['usage']['reasoning_tokens'] = 12
        self.server.responses.append((200, response))
        self.infer()
        self.assertEqual(self.client.snapshot()['reasoning_tokens'], 12)
        response['usage']['completion_tokens_details'] = {'reasoning_tokens': 13}
        self.server.responses.append((200, response))
        with self.assertRaisesRegex(Qwen38Error, 'conflicting reasoning'):
            self.infer()

    def test_redirects_are_not_followed_and_model_listing_schema_is_checked(self):
        self.server.get_status = 302
        with self.assertRaisesRegex(Qwen38Error, 'HTTP 302'):
            self.client.verify()
        self.server.get_status = 200
        for listing in [{}, {'data': []}, {'data': [MODEL]}, {'data': [{'id': MODEL}, None]},
                        {'data': [{'id': ''}]}]:
            with self.subTest(listing=listing):
                self.server.models = listing
                with self.assertRaisesRegex(Qwen38Error, 'malformed model listing'):
                    self.client.verify()

    def test_validation_rejects_unsafe_identity_and_secret_metadata_before_network(self):
        bad_urls = ['ftp://host/v1', 'http://user:password@host/v1', 'http://host/v1?q=secret',
                    'http://host/v1#fragment', 'http://host/v1?', 'http://host/v1#',
                    'http://host:bad/v1', 'http://host:0/v1', 'http://[invalid',
                    '/v1', ' http://host/v1', 'http://host/\npath']
        for url in bad_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                Qwen38Client(url, MODEL, DEPLOYMENT)
        bad_args = [{'model': 'wrong'}, {'thinking': 'high'}, {'max_completion_tokens': True},
                    {'max_completion_tokens': 0}, {'timeout_seconds': float('nan')},
                    {'timeout_seconds': 0}, {'api_key_env': 'actual-key-value!'},
                    {'deployment': {}}, {'deployment': {**DEPLOYMENT, 'api_key': 'secret'}}]
        for changes in bad_args:
            args = {'base_url': self.url, 'model': MODEL, 'deployment': DEPLOYMENT, **changes}
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Qwen38Client(**args)
        deployment = copy.deepcopy(DEPLOYMENT)
        client = Qwen38Client(self.url, MODEL, deployment)
        deployment['revision'] = 'mutated'
        details = client.model_details()
        self.assertEqual(details['deployment']['revision'], 'a' * 40)
        details['deployment']['revision'] = 'also mutated'
        self.assertEqual(client.model_details()['deployment']['revision'], 'a' * 40)
        self.assertEqual(self.server.requests, [])


if __name__ == '__main__':
    unittest.main()
