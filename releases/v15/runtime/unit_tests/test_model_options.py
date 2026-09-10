import argparse
import contextlib
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
from pypdf import PdfWriter

import eval_boundaries
import model_options
from production_state import file_hash, state_key
from qwen38_client import Qwen38Client, Qwen38Error, Qwen38TruncatedError
from run_production import runtime_settings
import split


LOG = logging.getLogger("unit-model-options")
LOG.addHandler(logging.NullHandler())


def resolve(*arguments):
    parser = argparse.ArgumentParser()
    model_options.add_model_arguments(parser)
    return model_options.resolve_model_arguments(parser.parse_args(arguments))


@contextlib.contextmanager
def boundary_server(served_model, first_response=None):
    """Small loopback server for the evaluator integration, not protocol unit tests."""
    calls = {"models": 0, "completions": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def send_json(self, body, status=200):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            calls["models"] += 1
            self.send_json({"data": [{"id": served_model}]})

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls["completions"].append(payload)
            if first_response is not None and len(calls['completions']) == 1:
                status, response = first_response
                self.send_json(response, status)
                return
            prompt = payload["messages"][0]["content"][-1]["text"]
            if prompt.startswith("Compare these two scanned"):
                answer = {"style_match": True, "letterhead_match": True,
                          "layout_type_prev": "text", "layout_type_curr": "text",
                          "strongest_difference": None, "confidence": 95}
            elif "Does page 1 END" in prompt:
                answer = {"end": False, "signal": "none", "signal_on_page": 1, "confidence": 95,
                          "reason": "continuation page"}
            elif "Does page 2 END" in prompt:
                answer = {"end": True, "signal": "fresh_letterhead", "signal_on_page": 3, "confidence": 95,
                          "reason": "different issuer on page three"}
            elif "Decide: does page 2 BEGIN" in prompt:
                answer = {"starts_new": False, "confidence": 95, "reason": "same document"}
            else:
                self.send_error(500, "Unexpected detector query")
                return
            self.send_json({"model": served_model,
                            "choices": [{"finish_reason": "stop", "message": {
                                "role": "assistant", "content": json.dumps(answer)}}],
                            "usage": {"prompt_tokens": 20, "completion_tokens": 10,
                                      "completion_tokens_details": {"reasoning_tokens": 0}}})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class ModelOptionsTests(unittest.TestCase):
    def test_default_hf_selection_preserves_loader_signature_and_never_contacts_server(self):
        with patch.object(Qwen38Client, "verify", side_effect=AssertionError("unexpected server contact")):
            model, revision, options = resolve()
            self.assertEqual((model, revision, options), (model_options.DEFAULT_MODEL, None, {"backend": "hf"}))
            settings = runtime_settings(model, 150, False, revision, options)
            self.assertEqual(model_options.load_kwargs(settings), {})
            settings["model_revision"] = "a" * 40
            self.assertEqual(model_options.load_kwargs(settings), {"revision": "a" * 40})

    def test_hf_model_and_processor_keep_existing_nf4_load_arguments(self):
        model, processor, quantization = MagicMock(), MagicMock(), object()
        model_class = SimpleNamespace(from_pretrained=MagicMock(return_value=model))
        processor_class = SimpleNamespace(from_pretrained=MagicMock(return_value=processor))
        quantization_class = MagicMock(return_value=quantization)
        dtype = object()
        torch = SimpleNamespace(bfloat16=dtype)
        transformers = SimpleNamespace(Qwen2_5_VLForConditionalGeneration=model_class,
                                       AutoProcessor=processor_class, BitsAndBytesConfig=quantization_class)
        with patch.dict(sys.modules, {"torch": torch, "transformers": transformers}), \
                patch.object(Qwen38Client, "verify", side_effect=AssertionError("unexpected server contact")):
            result = split.load_model(model_options.DEFAULT_MODEL, LOG)
        self.assertEqual(result, (model, processor, None))
        quantization_class.assert_called_once_with(load_in_4bit=True, bnb_4bit_compute_dtype=dtype,
                                                   bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4")
        model_class.from_pretrained.assert_called_once_with(model_options.DEFAULT_MODEL,
                                                            quantization_config=quantization, device_map="auto")
        processor_class.from_pretrained.assert_called_once_with(model_options.DEFAULT_MODEL)
        model.eval.assert_called_once_with()

    def test_qwen38_cannot_enter_the_hf_loader(self):
        for name in ("Qwen/Qwen3.8-27B", "RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "requires"):
                resolve("--model", name)
            with self.subTest(name=name), patch.dict(sys.modules, {"torch": None}), \
                    self.assertRaisesRegex(ValueError, "requires"):
                split.load_model(name, LOG)
        for arguments in (("--thinking", "low"), ("--endpoint", "http://127.0.0.1:8000/v1")):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(ValueError, "require --backend"):
                resolve(*arguments)

    def test_qwen38_selection_uses_actual_pinned_deployment(self):
        deployment = json.loads(model_options.DEFAULT_DEPLOYMENT.read_text())
        model, revision, options = resolve("--backend", "qwen38")
        self.assertEqual(model, deployment["served_model"])
        self.assertEqual(revision, deployment["revision"])
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertRegex(options["deployment"]["runtime"]["image"], r"@sha256:[0-9a-f]{64}$")
        self.assertEqual(options["deployment"], deployment)
        self.assertEqual(options["thinking"], "off")
        self.assertEqual(options["max_completion_tokens"], 4096)
        self.assertEqual(options['response_validation_retries'], 1)
        self.assertEqual(options['response_format'], 'json_schema_v1')
        self.assertEqual(options["endpoint"], "http://127.0.0.1:8000/v1")
        self.assertEqual(model_options.load_kwargs({"model_revision": revision, "inference": options}),
                         {"revision": revision, "inference": options})
        for alias in (deployment["checkpoint"], deployment["base_model"], deployment["served_model"]):
            self.assertEqual(resolve("--backend", "qwen38", "--model", alias)[0], model)

    def test_endpoint_secrets_bad_budgets_and_pin_mismatches_are_rejected(self):
        invalid = [
            ("--endpoint", "http://user:secret@127.0.0.1:8000/v1"),
            ("--endpoint", "http://127.0.0.1:8000/v1?api_key=secret"),
            ("--endpoint", "http://127.0.0.1:8000/v1#secret"),
            ("--endpoint", "http://127.0.0.1:99999/v1"),
            ("--endpoint", "file:///tmp/socket"),
            ("--max-completion-tokens", "0"), ("--max-completion-tokens", "-1"),
            ("--max-completion-tokens", "32768"),
            ("--request-timeout", "0"), ("--request-timeout", "nan"), ("--request-timeout", "inf"),
            ("--model", "different-model"), ("--revision", "0" * 40),
        ]
        for flags in invalid:
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                resolve("--backend", "qwen38", *flags)

    def test_generation_and_deployment_changes_invalidate_runtime_identity(self):
        model, revision, options = resolve("--backend", "qwen38")
        baseline = runtime_settings(model, 150, False, revision, copy.deepcopy(options))
        variations = []
        for key, value in (("thinking", "low"), ("max_completion_tokens", 2048),
                           ('response_validation_retries', 0), ('response_format', 'prompt_only')):
            changed = copy.deepcopy(options)
            changed[key] = value
            variations.append(changed)
        for key, value in (("context_length", 16384), ("max_running_requests", 2)):
            changed = copy.deepcopy(options)
            changed["deployment"][key] = value
            variations.append(changed)
        changed = copy.deepcopy(options)
        changed["deployment"]["runtime"]["image"] = "registry/engine@sha256:" + "f" * 64
        variations.append(changed)
        for changed in variations:
            with self.subTest(options=changed):
                self.assertNotEqual(runtime_settings(model, 150, False, revision, changed), baseline)

    def test_server_loader_constructs_real_client_and_verifies_before_returning(self):
        model, revision, options = resolve("--backend", "qwen38")
        with patch.dict(sys.modules, {"torch": None}), patch.object(Qwen38Client, "verify", autospec=True) as verify:
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
        self.assertIsInstance(client, Qwen38Client)
        self.assertIsNone(processor)
        self.assertEqual(config, {"backend": "qwen38"})
        verify.assert_called_once_with(client)
        with patch.object(Qwen38Client, "verify", side_effect=Qwen38Error("ID not advertised")), \
                self.assertRaisesRegex(Qwen38Error, "ID not advertised"):
            split.load_model(model, LOG, revision=revision, inference=options)
        with self.assertRaisesRegex(ValueError, 'exactly one response-format retry'):
            split.load_model(model, LOG, revision=revision,
                             inference={**options, 'response_validation_retries': 0})

    def test_server_inference_routes_final_json_without_importing_torch(self):
        model, revision, options = resolve("--backend", "qwen38")
        with patch.object(Qwen38Client, "verify"):
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
        images = [Image.new("RGB", (8, 8))]
        answer = '{"end": false, "confidence": 90}'
        with patch.dict(sys.modules, {"torch": None}), patch.object(client, "infer", return_value=answer) as infer:
            self.assertEqual(split._infer("Read this page", images, client, processor, config, LOG, max_tokens=60), answer)
        infer.assert_called_once_with("Read this page", images, LOG, max_tokens=60)

    def test_server_malformed_answer_cannot_turn_into_a_default_boundary_decision(self):
        model, revision, options = resolve("--backend", "qwen38")
        with patch.object(Qwen38Client, "verify"):
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
        for answer in ("", "not JSON", "[true]", "null", "{broken}",
                       '{"end":true,"end":false}', '{"confidence":NaN}'):
            with self.subTest(answer=answer), patch.object(client, "infer", return_value=answer) as infer, \
                    self.assertRaises((RuntimeError, ValueError)):
                split._infer("Read this page", [Image.new("RGB", (8, 8))], client, processor, config, LOG)
            self.assertEqual(infer.call_count, 2)

    def test_missing_page_on_a_negative_decision_gets_one_format_only_retry(self):
        model, revision, options = resolve('--backend', 'qwen38')
        with patch.object(Qwen38Client, 'verify'):
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
        missing_page = {'end': False, 'signal': 'none', 'confidence': 55, 'reason': 'UNIQUE_PRIOR_ANSWER'}
        valid = {**missing_page, 'signal_on_page': 1, 'reason': 'same document'}
        images = [Image.new('RGB', (10, 10)), Image.new('RGB', (10, 20))]
        with patch.object(client, 'infer', side_effect=[json.dumps(missing_page), json.dumps(valid)]) as infer:
            result = split._query_document_end(images, [1, 2], 1, client, processor, config, LOG)
        self.assertEqual(result, (False, .55, 'none', 1))
        self.assertEqual(infer.call_count, 2)
        first, second = infer.call_args_list
        original_prompt = first.args[0]
        self.assertTrue(second.args[0].startswith(original_prompt + '\n\nResponse format requirement:'))
        self.assertIn('"signal_on_page": integer', second.args[0])
        self.assertIn('"end": boolean', second.args[0])
        self.assertNotIn('UNIQUE_PRIOR_ANSWER', second.args[0])
        self.assertIs(first.args[1], images)
        self.assertIs(second.args[1], images)
        self.assertEqual(first.kwargs, second.kwargs)
        self.assertEqual(first.kwargs, {'max_tokens': 150, 'response_schema': {
            'end': bool, 'signal': str, 'signal_on_page': int,
            'confidence': 'confidence', 'reason': str}})
        # A fully valid negative decision is used immediately, without a retry.
        with patch.object(client, 'infer', return_value=json.dumps(valid)) as infer:
            self.assertEqual(split._query_document_end(images, [1, 2], 1, client, processor, config, LOG), result)
        infer.assert_called_once()

    def test_invalid_field_types_retry_once_then_fail_instead_of_defaulting(self):
        model, revision, options = resolve('--backend', 'qwen38')
        with patch.object(Qwen38Client, 'verify'):
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
        valid = {'end': False, 'signal': 'none', 'signal_on_page': 1,
                 'confidence': 55, 'reason': 'same document'}
        for bad in [{**valid, 'end': 'false'}, {**valid, 'signal_on_page': '1'},
                    {**valid, 'confidence': True}, {**valid, 'confidence': 101}]:
            with self.subTest(bad=bad), patch.object(client, 'infer', return_value=json.dumps(bad)) as infer:
                with self.assertRaises(model_options.ResponseValidationError):
                    split._query_document_end([Image.new('RGB', (10, 10))], [1], 1,
                                              client, processor, config, LOG)
                self.assertEqual(infer.call_count, 2)

    def test_format_repair_http_calls_and_tokens_are_included_in_usage(self):
        model, revision, _ = resolve('--backend', 'qwen38')
        first_answer = {'end': False, 'signal': 'none', 'confidence': 55, 'reason': 'same document'}
        first_response = {'model': model, 'choices': [{'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': json.dumps(first_answer)}}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 10, 'reasoning_tokens': 0}}
        with boundary_server(model, first_response=(200, first_response)) as (endpoint, calls):
            model, revision, options = resolve('--backend', 'qwen38', '--endpoint', endpoint)
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
            result = split._query_document_end([Image.new('RGB', (10, 10))], [1], 1,
                                              client, processor, config, LOG)
            self.assertEqual(result, (False, .95, 'none', 1))
            self.assertEqual(len(calls['completions']), 2)
            stats = client.snapshot()
            self.assertEqual((stats['model_calls'], stats['input_tokens'], stats['output_tokens']), (2, 40, 20))
            first, second = calls['completions']
            schema = first['response_format']['json_schema']
            self.assertTrue(schema['strict'])
            self.assertIn('signal_on_page', schema['schema']['required'])
            self.assertEqual(schema['schema']['properties']['signal_on_page'], {'type': 'integer'})
            self.assertEqual(first['response_format'], second['response_format'])
            self.assertEqual(first['max_tokens'], second['max_tokens'])
            self.assertEqual(first['seed'], second['seed'])
            self.assertEqual(first['temperature'], second['temperature'])
            self.assertEqual(first['messages'][0]['content'][:-1], second['messages'][0]['content'][:-1])

    def test_http_failures_are_not_format_retried(self):
        model, revision, _ = resolve('--backend', 'qwen38')
        with boundary_server(model, first_response=(503, {'error': 'unavailable'})) as (endpoint, calls):
            model, revision, options = resolve('--backend', 'qwen38', '--endpoint', endpoint)
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
            with self.assertRaises(Qwen38Error):
                split._query_document_end([Image.new('RGB', (10, 10))], [1], 1,
                                          client, processor, config, LOG)
            self.assertEqual(len(calls['completions']), 1)
            self.assertEqual(client.snapshot()['failed_calls'], 1)

    def test_off_length_recovery_bounds_fields_preserves_prompt_and_counts_failed_tokens(self):
        model, revision, _ = resolve('--backend', 'qwen38')
        truncated = {'model': model, 'choices': [{'finish_reason': 'length',
                     'message': {'role': 'assistant', 'content': '{"end":false'}}],
                     'usage': {'prompt_tokens': 20, 'completion_tokens': 4096, 'reasoning_tokens': 0}}
        with boundary_server(model, first_response=(200, truncated)) as (endpoint, calls):
            model, revision, options = resolve('--backend', 'qwen38', '--endpoint', endpoint)
            client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
            result = split._query_document_end([Image.new('RGB', (10, 10))], [1], 1,
                                              client, processor, config, LOG)
            self.assertEqual(result, (False, .95, 'none', 1))
            self.assertEqual(len(calls['completions']), 2)
            first, second = calls['completions']
            self.assertEqual({k:v for k,v in first.items() if k!='response_format'},
                             {k:v for k,v in second.items() if k!='response_format'})
            properties = second['response_format']['json_schema']['schema']['properties']
            self.assertEqual(properties['reason']['maxLength'], 256)
            self.assertEqual(properties['confidence']['enum'], list(range(101)))
            self.assertNotIn('maxLength', first['response_format']['json_schema']['schema']['properties']['reason'])
            usage = client.snapshot()
            self.assertEqual((usage['model_calls'], usage['failed_calls'], usage['output_tokens']),
                             (2, 1, 4106))

    def test_repeated_length_failures_remain_errors_and_medium_is_not_retried(self):
        for thinking, expected in [('off', 2), ('medium', 1)]:
            model, revision, options = resolve('--backend', 'qwen38', '--thinking', thinking)
            with patch.object(Qwen38Client, 'verify'):
                client, processor, config = split.load_model(model, LOG, revision=revision, inference=options)
            with patch.object(client, 'infer', side_effect=Qwen38TruncatedError('length')) as infer:
                with self.assertRaises(Qwen38TruncatedError):
                    split._query_document_end([Image.new('RGB', (10, 10))], [1], 1,
                                              client, processor, config, LOG)
                self.assertEqual(infer.call_count, expected)

    def test_hf_inference_preserves_generation_settings_and_does_not_format_retry(self):
        torch = SimpleNamespace(no_grad=contextlib.nullcontext)
        processor = MagicMock()
        class Inputs(dict):
            @property
            def input_ids(self):
                return self['input_ids']
        inputs = Inputs(input_ids=[[1, 2, 3]])
        processor.return_value.to.return_value = inputs
        processor.batch_decode.return_value = ['not JSON']
        model = MagicMock()
        model.generate.return_value = [[1, 2, 3, 9]]
        process_images = MagicMock(return_value=(['processed image'], None))
        image = Image.new('RGB', (10, 10))
        with patch.dict(sys.modules, {'torch': torch, 'qwen_vl_utils': SimpleNamespace(process_vision_info=process_images)}):
            result = split._infer('original prompt', [image], model, processor, None, LOG,
                                  max_tokens=150, response_schema={'end': bool})
        self.assertEqual(result, 'not JSON')
        model.generate.assert_called_once_with(**inputs, max_new_tokens=150, do_sample=False)
        processor.apply_chat_template.assert_called_once_with(
            [{'role': 'user', 'content': [{'type': 'image', 'image': image},
                                        {'type': 'text', 'text': 'original prompt'}]}],
            tokenize=False, add_generation_prompt=True)

    def test_server_query_rejects_string_booleans_and_missing_fields_without_changing_hf(self):
        valid = {"end": False, "signal": "none", "signal_on_page": 1,
                 "confidence": 90, "reason": "continuation"}
        invalid = [{**valid, "end": "false"}, {**valid, "confidence": True},
                   {**valid, "signal_on_page": "1"}, {**valid, "confidence": 101},
                   {key: value for key, value in valid.items() if key != "end"}]
        for answer in invalid:
            with self.subTest(answer=answer), patch.object(split, "_infer", return_value=json.dumps(answer)), \
                    self.assertRaisesRegex(RuntimeError, "invalid .* field"):
                split._query_document_end([object(), object()], [1, 2], 1, None, None,
                                          {"backend": "qwen38"}, LOG)
        with patch.object(split, "_infer", return_value="{}"):
            legacy = split._query_document_end([object(), object()], [1, 2], 1, None, None, None, LOG)
        self.assertEqual(legacy, (False, 0.5, "none", 1))

    def test_three_page_http_evaluation_preserves_predictions_and_resumes_without_server_calls(self):
        model, revision, _ = resolve("--backend", "qwen38")
        with tempfile.TemporaryDirectory() as temporary, boundary_server(model) as (endpoint, calls):
            folder, run_dir = Path(temporary), Path(temporary) / "run"
            pdf = folder / "source.pdf"
            writer = PdfWriter()
            for _ in range(3):
                writer.add_blank_page(width=72, height=72)
            with pdf.open("wb") as handle:
                writer.write(handle)
            gt = {pdf.name: [1, 3]}
            (folder / "ground_truth.json").write_text(json.dumps(gt))
            model, revision, options = resolve("--backend", "qwen38", "--endpoint", endpoint)
            settings = runtime_settings(model, 150, False, revision, options)
            settings["code"]["eval_boundaries.py"] = file_hash(Path(eval_boundaries.__file__))
            with patch.object(eval_boundaries, "preflight"), \
                    patch.object(split, "_load_page", side_effect=lambda _pdf, page, _dpi: Image.new("RGB", (page * 10, 20))), \
                    patch.object(split, "_query_rotation", side_effect=lambda _img, page, *_args: 90 if page == 2 else 0):
                predictions, totals = eval_boundaries.run_predictions(folder, gt, run_dir, settings, split, LOG)
            self.assertEqual(predictions, {pdf.name: {3}})
            self.assertEqual(totals, {pdf.name: 3})
            self.assertEqual(calls["models"], 1)
            self.assertEqual(len(calls["completions"]), 5)
            cached = json.loads((run_dir / "predictions" / (state_key(pdf) + ".json")).read_text())
            self.assertEqual(cached["starts"], [1, 3])
            self.assertEqual(cached["rotations_ccw_for_inference"], {"2": 90})
            self.assertEqual(cached["model_usage"]["model_calls"], 5)
            self.assertEqual(cached["model_usage"]["input_tokens"], 100)
            self.assertEqual(cached["model_usage"]["output_tokens"], 50)
            with patch.object(split, "load_model", side_effect=AssertionError("cache must not reload a model")):
                resumed = eval_boundaries.run_predictions(folder, gt, run_dir, settings, split, LOG)
            self.assertEqual(resumed, (predictions, totals))
            self.assertEqual(len(calls["completions"]), 5)
            changed = copy.deepcopy(settings)
            changed["inference"]["thinking"] = "low"
            with self.assertRaisesRegex(ValueError, "different inputs/code/settings"):
                eval_boundaries.run_predictions(folder, gt, run_dir, changed, split, LOG)
            self.assertEqual(len(calls["completions"]), 5)


if __name__ == "__main__":
    unittest.main()
