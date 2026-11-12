"""Synthetic SDK/transport regression; no Anthropic package or API required.

Run: python -B -m tests.test_run_eval_offline
"""

import io
import json
import socket
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout, redirect_stderr
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from benchmark import run_eval
from benchmark.consumer_recording import validate_request_record
from benchmark.score import score_records


MODEL = 'synthetic-model'
PRIVATE_TEXT = 'SYNTHETIC_PRIVATE_REQUEST_MARKER'
PRIVATE_ERROR = 'SYNTHETIC_PRIVATE_EXCEPTION_MARKER'
GOLD = {'verdict': 'upheld', 'cited_articles': [19], 'penalties': []}


def case(case_id='synthetic-1'):
    return {
        'case_id': case_id,
        'era': 'era_2014_2016',
        'policy_date': '2015-06-01',
        'input': {
            'reported_post': PRIVATE_TEXT,
            'post_year': 2015,
            'reports': [],
            'visible_reporter_count': 0,
            'actual_reporter_count': 0,
        },
    }


def response(text=None, stop_reason='end_turn', usage=None):
    if text is None:
        text = json.dumps({**GOLD, 'reasoning_summary': 'synthetic outcome'})
    return SimpleNamespace(
        content=[SimpleNamespace(type='text', text=text)],
        stop_reason=stop_reason, usage=usage)


class MockSDK:
    """Observe kwargs and mock physical calls, including simulated SDK retry.

    The default deliberately retries twice: removing max_retries=0 from the
    real constructor makes the physical-call bound regression fail.
    """

    def __init__(self, events, boundary_observer=None):
        self.events = list(events)
        self.constructor_kwargs = []
        self.sdk_calls = []
        self.physical_calls = []
        self.boundary_observer = boundary_observer
        self.module = ModuleType('anthropic')
        self.module.Anthropic = self.construct

    def construct(self, **kwargs):
        self.constructor_kwargs.append(deepcopy(kwargs))
        sdk_retries = kwargs.get('max_retries', 2)

        def create(**arguments):
            self.sdk_calls.append(deepcopy(arguments))
            if self.boundary_observer:
                self.boundary_observer(arguments)
            for retry in range(sdk_retries + 1):
                self.physical_calls.append(deepcopy(arguments))
                if not self.events:
                    raise AssertionError('unexpected mock physical call')
                event = self.events.pop(0)
                if isinstance(event, Exception):
                    if (isinstance(event, (ConnectionError, TimeoutError))
                            and retry < sdk_retries):
                        continue
                    raise event
                return event

        return SimpleNamespace(messages=SimpleNamespace(create=create),
                               max_retries=sdk_retries)


class OfflineEvalTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # Fail closed if future edits accidentally enter a real transport.
        self.stack.enter_context(patch.object(
            socket, 'create_connection', side_effect=AssertionError('network forbidden')))
        self.stack.enter_context(patch.object(
            socket.socket, 'connect', side_effect=AssertionError('network forbidden')))
        self.sleep = self.stack.enter_context(patch.object(run_eval.time, 'sleep'))
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.inputs = self.root / 'inputs.jsonl'
        self.out = self.root / 'results.jsonl'
        self.approval = self.root / 'approval.json'
        self.write_inputs([case()])

    def write_inputs(self, cases):
        self.inputs.write_text(''.join(json.dumps(item) + '\n' for item in cases))
        self.approval.write_text(json.dumps({
            'approved': True, 'approval_id': 'synthetic-offline-only',
            'provider': 'anthropic', 'purpose': 'historical-adjudication-benchmark',
            'allowed_models': [MODEL], 'expires_on': '2999-12-31',
            'approved_input_sha256': run_eval.sha256_file(self.inputs),
        }))

    def argv(self, *extra):
        return [str(self.inputs), '--out', str(self.out), '--model', MODEL,
                '--run-id', 'synthetic-run', '--condition', 'zero_shot',
                '--data-processing-approval', str(self.approval), *extra]

    def invoke(self, sdk, *extra):
        with patch.dict(sys.modules, {'anthropic': sdk.module}), \
                patch.object(run_eval.importlib.metadata, 'version',
                             return_value='mock-sdk-offline'), \
                redirect_stdout(io.StringIO()):
            run_eval.main(self.argv(*extra))

    def rows(self):
        return [json.loads(line) for line in self.out.read_text().splitlines()]

    def run_case(self, events, max_attempts=3, system=PRIVATE_TEXT):
        records = []

        def observe(arguments):
            self.assertEqual(len(records), len(sdk.sdk_calls))
            self.assertIsNone(records[-1]['outcome'])
            self.assertTrue(validate_request_record(arguments, records[-1]['request_record']))

        sdk = MockSDK(events, observe)
        result = run_eval.run_case(
            sdk.construct(max_retries=0), case(), MODEL, system, 2048,
            max_attempts, records)
        self.assertEqual(result[2], len(sdk.sdk_calls))
        self.assertEqual(len(records), len(sdk.physical_calls))
        for arguments, record in zip(sdk.sdk_calls, records):
            self.assertTrue(validate_request_record(arguments, record['request_record']))
        self.assertNotIn(PRIVATE_TEXT, json.dumps(records))
        self.assertNotIn(PRIVATE_ERROR, json.dumps(records))
        return result, records, sdk

    def test_success_records_exact_sdk_arguments_before_invocation(self):
        usage = SimpleNamespace(input_tokens=11, output_tokens=7,
                                cache_read_input_tokens=0)
        result, records, sdk = self.run_case([response(usage=usage)])
        self.assertEqual(result[:3], ('success', {**GOLD, 'reasoning_summary':
                                                'synthetic outcome'}, 1))
        record = records[0]
        self.assertEqual(record['outcome'], 'success')
        self.assertEqual(record['provider_usage'], {
            'input_tokens': 11, 'output_tokens': 7,
            'cache_read_input_tokens': 0, 'cache_creation_input_tokens': None})
        self.assertIsNone(record['cost_usd'])
        self.assertEqual(record['request_record']['representation'], 'sdk_arguments')
        self.assertEqual(record['request_record']['api_flavor'], 'anthropic-messages')
        self.assertEqual(sdk.sdk_calls[0]['temperature'], 0)
        self.sleep.assert_not_called()

    def test_refusal_is_terminal_and_preserves_reported_usage(self):
        result, records, _ = self.run_case([
            response(stop_reason='refusal', usage={'input_tokens': 13})])
        self.assertEqual(result, ('refusal', None, 1, None))
        self.assertEqual(records[0]['provider_usage']['input_tokens'], 13)
        self.assertEqual(records[0]['outcome'], 'refusal')
        self.sleep.assert_not_called()

    def test_parse_repair_reuses_original_condition_without_http_retry(self):
        result, records, sdk = self.run_case([
            response('not-json', usage={'input_tokens': 5, 'output_tokens': 2}),
            response(usage={'input_tokens': 6, 'output_tokens': 3})])
        self.assertEqual(result[0], 'success')
        self.assertEqual([item['outcome'] for item in records], ['parse_failure', 'success'])
        self.assertEqual([item['trigger'] for item in records], ['initial', 'parse_repair'])
        self.assertEqual(sdk.sdk_calls[0], sdk.sdk_calls[1])
        self.assertEqual([item['provider_usage']['input_tokens'] for item in records], [5, 6])
        self.assertEqual(sdk.constructor_kwargs, [{'max_retries': 0}])

    def test_parse_exhaustion_is_one_error_case_with_safe_error_class(self):
        invalid = json.dumps({**GOLD, 'verdict': PRIVATE_ERROR})
        result, records, _ = self.run_case([response(invalid)] * 3)
        self.assertEqual(result, ('error', None, 3, 'parse_failure: ValueError'))
        self.assertEqual([item['outcome'] for item in records], ['parse_failure'] * 3)
        self.assertNotIn(PRIVATE_ERROR, json.dumps(result))
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 2])

    def test_network_failure_respects_physical_mock_bound_for_each_limit(self):
        for limit in (1, 2, 4):
            with self.subTest(limit=limit):
                self.out.unlink(missing_ok=True)
                sdk = MockSDK([ConnectionError(PRIVATE_ERROR)] * (limit + 2))
                self.invoke(sdk, '--max-attempts', str(limit))
                row = self.rows()[0]
                self.assertEqual(row['status'], 'error')
                self.assertEqual(row['run']['attempts'], limit)
                self.assertEqual(row['run']['sdk_call_attempts'], limit)
                self.assertEqual(len(sdk.physical_calls), limit)
                self.assertEqual(sdk.constructor_kwargs, [{'max_retries': 0}])
                self.assertEqual(row['run']['retry_executor'], 'application')
                self.assertNotIn(PRIVATE_ERROR, self.out.read_text())
                self.assertTrue(all(value is None for item in row['run']['attempt_records']
                                    for value in item['provider_usage'].values()))

    def test_network_then_parse_then_success_records_distinct_retry_triggers(self):
        result, records, _ = self.run_case([
            TimeoutError(PRIVATE_ERROR), response('not-json'), response()])
        self.assertEqual(result[0], 'success')
        self.assertEqual([item['trigger'] for item in records],
                         ['initial', 'sdk_error_retry', 'parse_repair'])
        self.assertEqual([item['outcome'] for item in records],
                         ['sdk_error', 'parse_failure', 'success'])

    def test_unknown_usage_is_not_zero_and_invalid_counts_are_unknown(self):
        result, records, _ = self.run_case([response(usage={
            'input_tokens': True, 'output_tokens': -1,
            'cache_read_input_tokens': '9', 'cache_creation_input_tokens': 0})])
        self.assertEqual(result[0], 'success')
        self.assertEqual(records[0]['provider_usage'], {
            'input_tokens': None, 'output_tokens': None,
            'cache_read_input_tokens': None, 'cache_creation_input_tokens': 0})
        _, missing, _ = self.run_case([response()])
        self.assertTrue(all(value is None for value in missing[0]['provider_usage'].values()))

    def test_digest_changes_with_every_final_request_component(self):
        arguments = run_eval.sdk_arguments_for(case(), MODEL, PRIVATE_TEXT, 2048)
        record = run_eval.safe_request_record(arguments)
        for key, value in (
                ('model', 'other-model'), ('max_tokens', 1024),
                ('temperature', 1), ('system', 'changed system'),
                ('messages', [{'role': 'user', 'content': 'changed content'}])):
            with self.subTest(key=key):
                changed = deepcopy(arguments)
                changed[key] = value
                self.assertFalse(validate_request_record(changed, record))

    def test_record_projection_does_not_leak_tool_schema_or_system_text(self):
        arguments = run_eval.sdk_arguments_for(case(), MODEL, PRIVATE_TEXT, 2048)
        arguments['tools'] = [{'name': 'synthetic-tool', 'description': PRIVATE_ERROR,
                               'input_schema': {'description': PRIVATE_TEXT}}]
        record = run_eval.safe_request_record(arguments)
        self.assertNotIn(PRIVATE_TEXT, json.dumps(record))
        self.assertNotIn(PRIVATE_ERROR, json.dumps(record))
        self.assertIn('tools_sha256', record['sent_parameters'])
        with self.assertRaisesRegex(ValueError, 'credentials'):
            run_eval.safe_request_record({**arguments, 'headers': {'authorization': 'synthetic'}})

    def test_main_persists_all_statuses_and_scorer_keeps_failure_denominators(self):
        cases = [case(f'synthetic-{index}') for index in range(4)]
        self.write_inputs(cases)
        sdk = MockSDK([response(), response(stop_reason='refusal')]
                      + [response('invalid')] * 3 + [ConnectionError(PRIVATE_ERROR)] * 3)
        self.invoke(sdk)
        rows = self.rows()
        self.assertEqual([row['status'] for row in rows], ['success', 'refusal', 'error', 'error'])
        self.assertEqual(len(sdk.physical_calls), 8)
        summary = score_records([{**item, 'gold': GOLD} for item in cases], rows)
        self.assertEqual(summary['attempted'], 4)
        self.assertEqual(summary['scored'], 1)
        self.assertEqual(summary['failures'], {'refusal': 1, 'error': 2})
        self.assertEqual(summary['all_expected_rates']['verdict_match'], 0.25)
        call_index = 0
        for row, item in zip(rows, cases):
            run = row['run']
            system, _ = run_eval.system_prompt_for(item, 'zero_shot')
            self.assertEqual(run['prompt_sha256'], run_eval.sha256_text(
                system + '\n---USER---\n' + run_eval.render_case(item)))
            self.assertNotIn(PRIVATE_TEXT, json.dumps(run))
            self.assertNotIn(PRIVATE_ERROR, json.dumps(row))
            self.assertEqual(run['request_record_stage'], 'before_sdk_call')
            self.assertEqual(run['sdk_call_attempts'], run['attempts'])
            for attempt in run['attempt_records']:
                self.assertTrue(validate_request_record(sdk.sdk_calls[call_index],
                                                       attempt['request_record']))
                call_index += 1

    def test_resume_appends_only_unfinished_cases_and_preserves_prior_bytes(self):
        self.write_inputs([case('synthetic-1'), case('synthetic-2')])
        sdk = MockSDK([response(), response()])
        self.invoke(sdk, '--limit', '1')
        first = self.out.read_bytes()
        self.invoke(sdk, '--resume')
        self.assertEqual(len(sdk.physical_calls), 2)
        self.assertEqual(len(self.rows()), 2)
        self.assertTrue(self.out.read_bytes().startswith(first))
        complete = self.out.read_bytes()
        self.invoke(sdk, '--resume')
        self.assertEqual(len(sdk.physical_calls), 2)
        self.assertEqual(self.out.read_bytes(), complete)

    def test_resume_rejects_changed_retry_config_and_legacy_unknown_retry(self):
        sdk = MockSDK([response()])
        self.invoke(sdk)
        before = self.out.read_bytes()
        with self.assertRaisesRegex(ValueError, 'max_attempts'):
            self.invoke(sdk, '--resume', '--max-attempts', '4')
        self.assertEqual(self.out.read_bytes(), before)
        legacy = self.rows()[0]
        for key in ('max_attempts', 'dry_run', 'retry_executor', 'sdk_max_retries'):
            legacy['run'].pop(key)
        self.out.write_text(json.dumps(legacy) + '\n')
        before = self.out.read_bytes()
        with self.assertRaisesRegex(ValueError, 'configuration mismatch'):
            self.invoke(sdk, '--resume')
        self.assertEqual(self.out.read_bytes(), before)
        self.assertEqual(len(sdk.constructor_kwargs), 1)

    def test_dry_run_and_resume_never_import_or_call_sdk(self):
        with patch.dict(sys.modules, {'anthropic': None}), redirect_stdout(io.StringIO()):
            run_eval.main(self.argv('--dry-run'))
            first = self.out.read_bytes()
            run_eval.main(self.argv('--dry-run', '--resume'))
        row = self.rows()[0]
        self.assertEqual(row['status'], 'dry_run')
        self.assertEqual(row['run']['attempts'], 0)
        self.assertEqual(row['run']['sdk_call_attempts'], 0)
        self.assertEqual(row['run']['attempt_records'], [])
        self.assertIsNone(row['run']['anthropic_sdk'])
        self.assertEqual(row['run']['request_record_stage'], 'planned_sdk_arguments')
        self.assertEqual(self.out.read_bytes(), first)
        sdk = MockSDK([response()])
        with self.assertRaisesRegex(ValueError, 'dry_run'):
            self.invoke(sdk, '--resume')
        self.assertEqual(sdk.constructor_kwargs, [])
        self.assertEqual(self.out.read_bytes(), first)

    def test_dry_run_does_not_require_processing_approval(self):
        argv = self.argv('--dry-run')
        start = argv.index('--data-processing-approval')
        del argv[start:start + 2]
        with patch.dict(sys.modules, {'anthropic': None}), redirect_stdout(io.StringIO()):
            run_eval.main(argv)
        self.assertIsNone(self.rows()[0]['run']['data_processing_approval_id'])

    def test_missing_or_invalid_approval_blocks_before_sdk_construction(self):
        sdk = MockSDK([response()])
        argv = self.argv()
        start = argv.index('--data-processing-approval')
        del argv[start:start + 2]
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            run_eval.main(argv)
        self.assertEqual(error.exception.code, 2)
        baseline = json.loads(self.approval.read_text())
        for key, value in (('approved', False), ('provider', 'other'),
                           ('purpose', 'other'), ('allowed_models', ['other']),
                           ('approved_input_sha256', '0' * 64),
                           ('expires_on', '2000-01-01')):
            with self.subTest(key=key):
                self.approval.write_text(json.dumps({**baseline, key: value}))
                with self.assertRaises(ValueError):
                    self.invoke(sdk)
                self.assertFalse(self.out.exists())
                self.assertEqual(sdk.constructor_kwargs, [])

    def test_mock_calls_preserve_conditions_and_exact_date_selected_rule(self):
        text = 'Synthetic verified policy material. ' * 20
        (self.root / 'rule.txt').write_text(text)
        manifest = self.root / 'rules.json'
        manifest.write_text(json.dumps({
            'human_version_verified': True, 'periods': [{
                'id': 'synthetic-policy', 'effective_from': '2015-01-01',
                'effective_to': '2015-12-31', 'file': 'rule.txt',
                'sha256': run_eval.sha256_text(text), 'source': 'synthetic-review',
            }],
        }))
        observed = {}
        for condition in ('zero_shot', 'era_hint', 'policy_prompt'):
            with self.subTest(condition=condition):
                self.out.unlink(missing_ok=True)
                sdk = MockSDK([response()])
                extra = ['--condition', condition]
                if condition == 'policy_prompt':
                    extra += ['--rules-manifest', str(manifest)]
                self.invoke(sdk, *extra)
                observed[condition] = sdk.sdk_calls[0]['system']
                run = self.rows()[0]['run']
                self.assertTrue(validate_request_record(sdk.sdk_calls[0], run['request_record']))
                self.assertEqual(run['rules_sha256'],
                                 run_eval.sha256_text(text) if condition == 'policy_prompt' else None)
        self.assertEqual(observed['zero_shot'], run_eval.BASE_SYSTEM_PROMPT)
        self.assertIn('2014-2016 study period', observed['era_hint'])
        self.assertNotIn(text, observed['era_hint'])
        self.assertIn(text, observed['policy_prompt'])
        # A date outside the verified interval still fails before any call.
        outside = case()
        outside['policy_date'] = '2016-01-01'
        self.write_inputs([outside])
        self.out.unlink()
        sdk = MockSDK([response()])
        with self.assertRaisesRegex(ValueError, 'expected one policy period'):
            self.invoke(sdk, '--condition', 'policy_prompt', '--rules-manifest', str(manifest))
        self.assertEqual(sdk.physical_calls, [])

    def test_existing_outputs_are_never_overwritten(self):
        self.out.write_text('synthetic sentinel')
        sdk = MockSDK([response()])
        with self.assertRaises(FileExistsError):
            self.invoke(sdk)
        self.assertEqual(self.out.read_text(), 'synthetic sentinel')
        self.assertEqual(sdk.constructor_kwargs, [])

    def test_forbidden_model_fields_never_reach_sdk(self):
        forbidden = case()
        forbidden['input']['gold'] = GOLD
        self.write_inputs([forbidden])
        sdk = MockSDK([response()])
        with self.assertRaisesRegex(ValueError, 'forbidden model-input'):
            self.invoke(sdk)
        self.assertEqual(sdk.physical_calls, [])
        self.assertEqual(self.out.read_text(), '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
