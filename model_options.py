"""Model selection shared by production and evaluation; no inference imports.

The default Hugging Face path preserves the measured Qwen2.5 implementation.
Qwen3.8 uses a separately pinned local server and an explicit deployment record.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

DEFAULT_MODEL = 'Qwen/Qwen2.5-VL-32B-Instruct'
DEFAULT_DEPLOYMENT = Path(__file__).parent / 'data' / 'qwen38_deployment.json'
RESPONSE_VALIDATION_RETRIES = 1
RESPONSE_FORMAT = 'json_schema_v1'
RESPONSE_RECOVERY_POLICY = 'format_or_bounded_off_length_once_v3'
BOUNDED_RETRY_HEADING_CHARS = 160
BOUNDED_RETRY_STRING_CHARS = 256


class ResponseValidationError(RuntimeError):
    """A completed model answer does not satisfy the requested JSON format."""


def add_model_arguments(parser):
    group = parser.add_argument_group('model and inference')
    group.add_argument('--backend', choices=('hf', 'qwen38'), default='hf',
                       help='hf: existing Qwen2.5 CUDA loader; qwen38: pinned local inference server')
    group.add_argument('--model', help=f'HF model path (default {DEFAULT_MODEL}); Qwen3.8 defaults to deployment model')
    group.add_argument('--revision', help='Pin weights/processor; Qwen3.8 defaults to the deployment revision')
    group.add_argument('--endpoint', help='Qwen3.8 OpenAI-compatible base URL, default http://127.0.0.1:8000/v1')
    group.add_argument('--deployment', type=Path, help='Pinned Qwen3.8 server deployment JSON')
    group.add_argument('--thinking', choices=('off', 'low', 'medium', 'xhigh'),
                       help='Qwen3.8 reasoning mode (default off)')
    group.add_argument('--max-completion-tokens', type=int,
                       help='Qwen3.8 total reasoning + answer cap per call (default 4096)')
    group.add_argument('--request-timeout', type=float,
                       help='Qwen3.8 HTTP timeout in seconds (default 180)')


def validate_deployment(deployment):
    if (not isinstance(deployment, dict) or deployment.get('version') != 1
            or deployment.get('model_family') != 'qwen3.8'):
        raise ValueError('Expected a version 1 Qwen3.8 deployment manifest')
    for key in ('id', 'served_model', 'checkpoint', 'base_model', 'quantization'):
        if not isinstance(deployment.get(key), str) or not deployment[key].strip():
            raise ValueError(f'Deployment needs a nonempty {key}')
    if not re.fullmatch(r'[0-9a-f]{40}', str(deployment.get('revision', ''))):
        raise ValueError('Deployment must pin an exact checkpoint revision')
    runtime = deployment.get('runtime', {})
    if (not isinstance(runtime, dict) or runtime.get('engine') not in ('sglang', 'vllm')
            or not re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', str(runtime.get('image', '')))
            or not re.fullmatch(r'[0-9a-f]{40}', str(runtime.get('commit', '')))
            or not isinstance(runtime.get('cuda'), str) or not runtime['cuda']):
        raise ValueError('Deployment must pin its server image digest, engine commit and CUDA version')
    for key in ('context_length', 'max_running_requests'):
        if type(deployment.get(key)) is not int or deployment[key] <= 0:
            raise ValueError(f'Deployment {key} must be a positive integer')
    # Retain launch details too: they affect cache validity, not just documentation.
    return copy.deepcopy(deployment)


def resolve_model_arguments(args):
    if args.backend == 'hf':
        if any(getattr(args, key) is not None for key in
               ('endpoint', 'deployment', 'thinking', 'max_completion_tokens', 'request_timeout')):
            raise ValueError('Server/thinking options require --backend qwen38')
        model = args.model or DEFAULT_MODEL
        if 'qwen3.8' in model.lower():
            raise ValueError('Qwen3.8 requires --backend qwen38 and a running vision-enabled server')
        return model, args.revision, {'backend': 'hf'}
    deployment_path = args.deployment or DEFAULT_DEPLOYMENT
    deployment = validate_deployment(json.loads(deployment_path.read_text(encoding='utf-8')))
    if args.model is not None and args.model not in (
            deployment['served_model'], deployment['checkpoint'], deployment['base_model']):
        raise ValueError('--model does not match the pinned Qwen3.8 deployment')
    if args.revision is not None and args.revision != deployment['revision']:
        raise ValueError('--revision does not match the pinned Qwen3.8 deployment')
    endpoint = args.endpoint or 'http://127.0.0.1:8000/v1'
    parts = urlsplit(endpoint)
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError('Invalid Qwen3.8 endpoint port') from exc
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username is not None or parts.password is not None or parts.query or parts.fragment
            or any(char.isspace() for char in endpoint)):
        raise ValueError('Endpoint must be an HTTP(S) base URL without credentials, query or fragment')
    cap = args.max_completion_tokens if args.max_completion_tokens is not None else 4096
    timeout = args.request_timeout if args.request_timeout is not None else 180.0
    if type(cap) is not int or not 0 < cap < deployment['context_length']:
        raise ValueError('Completion token cap must be positive and smaller than the server context')
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Request timeout must be finite and positive')
    options = {'backend': 'qwen38', 'endpoint': endpoint.rstrip('/'), 'deployment': deployment,
               'thinking': args.thinking or 'off', 'max_completion_tokens': cap,
               'timeout_seconds': timeout, 'response_validation_retries': RESPONSE_VALIDATION_RETRIES,
               'response_format': RESPONSE_FORMAT, 'response_recovery': RESPONSE_RECOVERY_POLICY}
    return deployment['served_model'], deployment['revision'], options


def load_kwargs(settings):
    """Keep legacy callers' load signature unchanged unless the server is selected."""
    kwargs = {'revision': settings['model_revision']} if settings.get('model_revision') else {}
    if settings.get('inference', {}).get('backend', 'hf') == 'qwen38':
        kwargs['inference'] = settings['inference']
    return kwargs


def usage_snapshot(model):
    from qwen38_client import Qwen38Client
    return model.snapshot() if isinstance(model, Qwen38Client) else None


def usage_delta(before, after):
    """Unknown token usage stays unknown; failed queries are never counted as free."""
    if before is None or after is None:
        return None
    return {key: (after[key] - before[key] if after[key] is not None and before.get(key) is not None else None)
            for key in after}


def summarize_usage(rows):
    rows = list(rows)
    if not rows or any(row is None for row in rows):
        return None
    return {key: (sum(row[key] for row in rows) if all(row.get(key) is not None for row in rows) else None)
            for key in rows[0]}


def validate_final_json(raw, schema=None):
    """All live splitter prompts request an object; don't turn bad JSON into no-cut."""
    if not isinstance(raw, str):
        raise ResponseValidationError('Qwen3.8 final JSON must be text')
    text = raw.strip()
    fenced = re.fullmatch(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fenced:
        text = fenced.group(1)
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    try:
        data = json.loads(text, object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite value')))
    except (ValueError, RecursionError):
        raise ResponseValidationError('Qwen3.8 returned malformed final JSON') from None
    if not isinstance(data, dict) or not data:
        raise ResponseValidationError('Qwen3.8 must return a nonempty final JSON object')
    if schema is not None:
        validate_query_fields(data, schema)
    return raw


def validate_query_fields(data, schema):
    if not isinstance(data, dict):
        raise ResponseValidationError('Qwen3.8 must return a final JSON object')
    for key, kind in schema.items():
        value = data.get(key)
        if kind == 'confidence':
            valid = type(value) in (int, float) and 0 <= value <= 100 and math.isfinite(value)
        else:
            kinds = kind if isinstance(kind, tuple) else (kind,)
            valid = type(value) in kinds
        if key not in data or not valid:
            raise ResponseValidationError(f'Qwen3.8 final JSON has an invalid {key} field')


def response_format_reminder(schema):
    """Describe required output types without supplying a decision or prior answer."""
    reminder = ('\n\nResponse format requirement: Return one nonempty JSON object only. '
                'Include every requested field, even when a decision is false. '
                'For boolean and numeric fields, use native JSON values rather than quoted strings.')
    if schema:
        names = {bool: 'boolean', int: 'integer', str: 'string', type(None): 'null'}
        fields = []
        for key, kind in schema.items():
            if kind == 'confidence':
                label = 'number from 0 to 100'
            else:
                kinds = kind if isinstance(kind, tuple) else (kind,)
                label = ' or '.join(names[item] for item in kinds)
            fields.append(f'{json.dumps(key)}: {label}')
        reminder += '\nRequired fields: ' + '; '.join(fields) + '.'
    return reminder


def query_json_schema(schema, *, bounded_response=False):
    """Translate query field types into the server's constrained decoding schema.

    All fields are required, including those on negative decisions. Recovery also
    caps text lengths and uses whole-percent confidence to prevent unbounded
    strings/numeric formatting; the model still chooses the semantic values.
    """
    if not isinstance(schema, dict) or not schema:
        raise ValueError('A nonempty query field schema is required')
    names = {bool: 'boolean', int: 'integer', str: 'string', type(None): 'null'}
    properties = {}
    for key, kind in schema.items():
        if not isinstance(key, str) or not key:
            raise ValueError('Query field names must be nonempty strings')
        if kind == 'confidence':
            properties[key] = ({'type': 'integer', 'enum': list(range(101))} if bounded_response
                               else {'type': 'number', 'minimum': 0, 'maximum': 100})
        else:
            kinds = kind if isinstance(kind, tuple) else (kind,)
            if not kinds or any(item not in names for item in kinds):
                raise ValueError(f'Unsupported query field type: {key}')
            types = [names[item] for item in kinds]
            properties[key] = {'type': types[0] if len(types) == 1 else types}
            if bounded_response and str in kinds:
                properties[key]['maxLength'] = (BOUNDED_RETRY_HEADING_CHARS if 'heading' in key
                                                else BOUNDED_RETRY_STRING_CHARS)
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}
