"""Unit tests for the adjudication parser and reporter features.

Run with:  python -m tests.test_analysis   (or pytest)
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.load import iter_complaints
from analysis.official_parser import (
    parse_cited_articles, parse_cited_documents, parse_debunkers,
    parse_effect_delay_minutes, parse_official, parse_penalties, parse_verdict)
from analysis.reporter_features import (
    classify_reporter_type, extract_report_features, reporter_identity,
    strip_reporter_prefix)
from analysis.concentration import collect as collect_concentration, render as render_concentration
from analysis.reporter_profiles import median
from analysis.validation import (
    build_validation_records, score_validation_records)
from analysis.stats import collect_stats, render_report
from benchmark.build_benchmark import build_case, build_instance
from benchmark.score import (
    normalize_prediction_record, score_records)
from benchmark.sample import sample_records
from benchmark.run_eval import (
    BASE_SYSTEM_PROMPT, _load_existing_case_ids, assert_model_facing_record,
    load_data_processing_approval, load_rules_manifest, parse_model_json,
    rule_for_record, sha256_file, sha256_text, system_prompt_for)
from datetime import date
from scripts.fetch_rules import closest_snapshot, validate_rule_text
from scripts.build_data_manifest import build_manifest

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_complaints.jsonl')

OFFICIAL_UPHELD = (
    '经查，此微博称“……”不实。@合成核验机构 已辟谣：…… 。'
    '被举报人言论构成“发布不实信息”。现根据《微博举报投诉操作细则》'
    '（http://service.account.weibo.com/roles/xize ）第19条，对被举报人处理如下：'
    '扣除信用积分2分。上述处理在公布后60分钟内生效。')

OFFICIAL_MUTE = (
    '被举报人言论构成“发布不实信息”。根据《微博举报投诉操作细则》第二十一条，'
    '对被举报人处理如下：扣除信用积分5分，禁言7天，禁被关注30天，删除该微博。'
    '上述处理在公布后30分钟内生效。')

OFFICIAL_REJECTED = '经查，被举报人言论不构成“发布不实信息”，本次举报不成立。'

OFFICIAL_UNDETERMINED = '经查，现有证据暂无法判定被举报内容真实性，暂不处理。'

OFFICIAL_INFORMAL = (
    '经查，此微博称“合成人物甲被聘为合成机构顾问”不实。'
    '@合成辟谣账号 已对此事件辟谣：这是一条谣言')

OFFICIAL_HARMFUL = (
    '经查，被举报人通过微博平台发布所谓地震预报信息，其行为违反《中华人民共和国防震减灾法》相关规定，'
    '微博内容构成“有害信息”。现根据《微博举报投诉操作细则》第20条，对被举报人处理如下：禁言15天。')

# Evidence citation (IAAF rules 第168条) must not be counted as a platform article.
OFFICIAL_EVIDENCE_ARTICLE = (
    '经查，栏架高度为1.067米，规定于国际田联（IAAF）《2012-2013最新竞赛规则》（IAAF COMPETITION RULES）'
    '第168条。被举报人言论构成“发布不实信息”。现根据《新浪微博社区管理规定(试行)》'
    '（http://weibo.com/z/guize/guiding.html）第22条，对被举报人处理如下：扣除信用积分2分。')


def test_parse_verdict():
    assert parse_verdict(OFFICIAL_UPHELD) == 'upheld'
    assert parse_verdict(OFFICIAL_REJECTED) == 'rejected'
    assert parse_verdict(OFFICIAL_UNDETERMINED) == 'undetermined'
    assert parse_verdict(OFFICIAL_INFORMAL) == 'upheld_informal'
    assert parse_verdict(OFFICIAL_HARMFUL) == 'upheld_harmful'
    assert parse_verdict('') is None
    assert parse_verdict(None) is None


def test_parse_cited_articles():
    assert parse_cited_articles(OFFICIAL_UPHELD) == [19]
    assert parse_cited_articles(OFFICIAL_MUTE) == [21]
    # evidence citations (IAAF 第168条, laws) are excluded
    assert parse_cited_articles(OFFICIAL_EVIDENCE_ARTICLE) == [22]
    assert parse_cited_articles(OFFICIAL_HARMFUL) == [20]
    # fallback when no platform rulebook is cited at all
    assert parse_cited_articles('依据第3条、第十二条与第19条') == [3, 12, 19]
    assert parse_cited_articles('无引用') == []


def test_parse_cited_documents():
    assert parse_cited_documents(OFFICIAL_UPHELD) == ['微博举报投诉操作细则']
    assert parse_cited_documents(OFFICIAL_EVIDENCE_ARTICLE) == ['新浪微博社区管理规定(试行)']


def test_parse_penalties():
    p = parse_penalties(OFFICIAL_UPHELD)
    assert p == [{'type': 'credit_deduction', 'magnitude': 2}]

    p = parse_penalties(OFFICIAL_MUTE)
    types = {(x['type'], x['magnitude']) for x in p}
    assert ('credit_deduction', 5) in types
    assert ('mute', 7) in types
    assert ('follow_ban', 30) in types
    assert ('delete_post', None) in types

    p = parse_penalties('对被举报人永久禁言，账号予以关闭。')
    types = {(x['type'], x['magnitude']) for x in p}
    assert ('mute', None) in types
    assert ('account_closure', None) in types


def test_parse_misc():
    assert parse_effect_delay_minutes(OFFICIAL_UPHELD) == 60
    assert parse_effect_delay_minutes(OFFICIAL_REJECTED) is None
    assert parse_debunkers(OFFICIAL_UPHELD) == ['合成核验机构']

    full = parse_official(OFFICIAL_MUTE)
    assert full['verdict'] == 'upheld'
    assert full['cited_articles'] == [21]
    assert len(full['penalties']) == 4


def test_reporter_features():
    assert classify_reporter_type('合成政务账号，仅用于测试') == 'government'
    assert classify_reporter_type('XX日报官方账号') in ('government', 'media')
    assert classify_reporter_type('专业辟谣账号') == 'debunker'
    assert classify_reporter_type('执业律师') == 'legal'
    assert classify_reporter_type('爱吃可丽饼') == 'ordinary'
    assert classify_reporter_type(None) == 'ordinary'

    assert strip_reporter_prefix(
        '合成举报者', '合成举报者：#微博辟谣# 已辟谣') == '#微博辟谣# 已辟谣'
    assert strip_reporter_prefix('A', None) == ''

    feats = extract_report_features({
        'reporter_name': '合成政务举报者',
        'reporter_description': '合成政务账号，仅用于测试',
        'reporter_gender': 'unspecified',
        'report_time': '2018-08-30 12:47',
        'report_text': '合成政务举报者：#微博辟谣# 详情 https://example.invalid/evidence',
    })
    assert feats['reporter_type'] == 'government'
    assert feats['uses_debunk_hashtag']
    assert feats['has_evidence_url']

    assert reporter_identity({
        'reporter_url': 'https://weibo.com/u/0000000000',
        'reporter_name': 'renameable',
    }) == ('uid:0000000000', 'uid')
    assert reporter_identity({
        'reporter_url': '', 'reporter_name': 'fallback',
    }) == ('name-fallback:fallback', 'name_fallback')


def test_load_and_stats_on_sample():
    complaints = list(iter_complaints(SAMPLE_PATH))
    assert len(complaints) == 1
    assert complaints[0]['actual_reporter_count'] == 3

    stats = collect_stats(complaints)
    assert stats['n_complaints'] == 1
    assert stats['verdicts']['upheld'] == 1
    assert stats['cited_articles'][19] == 1
    assert stats['penalty_types']['credit_deduction'] == 1
    assert stats['reporter_types']['government'] == 1
    assert stats['n_reports'] == 3
    assert '## Verdicts' in render_report(stats)


def test_build_instance():
    complaint = next(iter_complaints(SAMPLE_PATH))
    instance = build_instance(complaint)
    assert instance['gold']['verdict'] == 'upheld'
    assert instance['gold']['cited_articles'] == [19]
    assert instance['gold']['penalties'] == [{'type': 'credit_deduction', 'magnitude': 2}]
    assert len(instance['input']['reports']) == 3
    # PII reduced: aliases replace names, no raw name appears in input reports
    assert all(r['reporter_alias'].startswith('reporter_') for r in instance['input']['reports'])
    assert instance['input']['reported_user']['alias'] == 'reported_user'
    assert '合成发布者：' not in instance['input']['reported_post']
    assert 'official_text' not in instance

    input_record, gold_record, linkage = build_case(
        complaint, 'case-000001')
    assert input_record['case_id'] == gold_record['case_id']
    assert 'source_url' not in input_record
    assert input_record['input']['reported_user'] == {'alias': 'reported_user'}
    assert 'official_text' not in gold_record
    assert linkage['source_url'] == complaint['url']

    # unusable record -> None
    assert build_instance({'rumor': {}, 'official': {}}) is None


def test_build_data_manifest():
    manifest = build_manifest(
        Path(SAMPLE_PATH),
        'synthetic-fixture', 'synthetic', '2018-08-30', 'test-v1',
        Path(__file__).resolve().parents[1])
    assert manifest['record_count'] == 1
    assert len(manifest['sha256']) == 64
    assert manifest['classification'] == 'restricted-research-data'
    assert not manifest['release_approved']
    assert isinstance(manifest['code_dirty'], bool)


def test_concentration_uses_case_denominators_and_visibility():
    complaint = {
        'actual_reporter_count': 2,
        'rumor': {'rumor_time': '2018-01-01 00:00:00'},
        'reports': [
            {
                'reporter_url': 'https://weibo.com/u/0000000000',
                'reporter_name': 'A',
                'reporter_description': '',
                'report_time': '2018-01-01 01:00',
                'report_text': 'A：文字证据，无链接',
            },
            {
                'reporter_url': 'https://weibo.com/u/0000000001',
                'reporter_name': 'B',
                'reporter_description': '',
                'report_time': None,
                'report_text': None,
            },
        ],
        'official': {'official_text': (
            '被举报人言论构成“发布不实信息”。根据《微博举报投诉操作细则》'
            '第19条，扣除信用积分2分，禁言7天。')},
    }
    data = collect_concentration([complaint])
    assert data['case_visibility']['complete'] == 1
    assert data['case_years']['2018'] == 1
    assert data['penalty_year']['2018']['credit_deduction'] == 1
    assert data['penalty_year']['2018']['mute'] == 1
    assert data['evidence_year']['2018']['statements'] == 1
    assert data['evidence_year']['2018']['missing_statement'] == 1
    report = render_concentration(data)
    assert '1 (100.0%)' in report
    assert 'all cases' in report


def test_concentration_reports_truncation_and_deduplicates_uid():
    complaint = {
        'actual_reporter_count': 25,
        'rumor': {'rumor_time': '2017-01-01 00:00:00'},
        'reports': [
            {'reporter_url': 'https://weibo.com/u/0000000000',
             'reporter_name': 'old name', 'reporter_description': ''},
            {'reporter_url': 'https://weibo.com/u/0000000000',
             'reporter_name': 'new name', 'reporter_description': ''},
        ],
        'official': {'official_text': ''},
    }
    data = collect_concentration([complaint])
    assert data['case_visibility']['truncated'] == 1
    assert data['hidden_reporters_lower_bound'] == 23
    assert data['reporter_cases']['uid:0000000000'] == 1
    assert not data['complete_reporter_cases']
    stats = collect_stats([complaint])
    assert stats['serial_reporters']['uid:0000000000'] == 1


def test_median_handles_even_samples():
    assert median([1, 3]) == 2
    assert median([1, 2, 9]) == 2


def test_validation_requires_two_labels_or_adjudication():
    complaint = next(iter_complaints(SAMPLE_PATH))
    records = build_validation_records([complaint], per_stratum=10, seed=7)
    assert any(record['task'] == 'official_parser' for record in records)
    official = next(record for record in records
                    if record['task'] == 'official_parser')
    official['annotator_a'] = official['machine_label']
    summary = score_validation_records(records)
    assert summary['resolved'] == 0
    official['annotator_b'] = official['machine_label']
    summary = score_validation_records(records)
    assert summary['resolved'] == 1
    assert summary['official_verdict_exact'] == 1


def test_run_eval_wrapper_is_accepted_by_strict_scorer():
    complaint = next(iter_complaints(SAMPLE_PATH))
    instance = build_instance(complaint)
    wrapped = {
        'case_id': instance['case_id'],
        'pred': {
            'verdict': instance['gold']['verdict'],
            'cited_articles': instance['gold']['cited_articles'],
            'penalties': instance['gold']['penalties'],
            'reasoning_summary': 'synthetic test',
        },
        'score': {},
    }
    case_id, normalized = normalize_prediction_record(wrapped)
    assert case_id == instance['case_id']
    assert normalized['verdict'] == 'upheld'
    summary = score_records([instance], [wrapped])
    assert summary['scored'] == 1
    assert summary['totals']['verdict_match'] == 1
    assert summary['totals']['penalties_exact'] == 1


def test_scorer_keeps_failures_in_primary_denominator():
    instance = build_instance(next(iter_complaints(SAMPLE_PATH)))
    failure = {'case_id': instance['case_id'], 'status': 'refusal', 'pred': None}
    summary = score_records([instance], [failure])
    assert summary['attempted'] == 1
    assert summary['scored'] == 0
    assert summary['failures']['refusal'] == 1
    assert summary['all_expected_rates']['verdict_match'] == 0
    assert summary['unscored'] == [instance['case_id']]


def test_scorer_rejects_unknown_duplicate_and_missing_ids():
    instance = build_instance(next(iter_complaints(SAMPLE_PATH)))
    prediction = {
        'case_id': instance['case_id'],
        'verdict': 'upheld',
        'cited_articles': [19],
        'penalties': [{'type': 'credit_deduction', 'magnitude': 2}],
    }
    try:
        score_records([instance], [])
        assert False, 'missing predictions must fail'
    except ValueError as error:
        assert 'missing' in str(error)
    try:
        score_records([instance], [prediction, prediction])
        assert False, 'duplicate predictions must fail'
    except ValueError as error:
        assert 'duplicate' in str(error)
    try:
        score_records([], [])
        assert False, 'empty benchmark must fail'
    except ValueError as error:
        assert 'no instances' in str(error)


def test_sampling_uses_observed_era_not_gold():
    records = [
        {'case_id': 'a', 'era': 'era_2012_2013', 'input': {}},
        {'case_id': 'b', 'era': 'era_2014_2016', 'input': {}},
        {'case_id': 'c', 'era': 'era_2017_2018', 'input': {}},
        {'case_id': 'd', 'era': 'unknown', 'input': {}},
    ]
    selected, counts = sample_records(records, per_stratum=1, seed=42)
    assert {record['case_id'] for record in selected} == {'a', 'b', 'c'}
    assert set(counts) == {
        'era_2012_2013', 'era_2014_2016', 'era_2017_2018'}


def test_eval_conditions_are_isolated_and_rules_are_date_selected():
    record = {
        'case_id': 'case-1', 'era': 'era_2014_2016',
        'policy_date': '2015-03-01', 'input': {
            'reported_post': 'synthetic', 'post_year': '2015',
            'reports': [], 'visible_reporter_count': 0,
            'actual_reporter_count': 0,
        },
    }
    zero_prompt, _ = system_prompt_for(record, 'zero_shot')
    assert zero_prompt == BASE_SYSTEM_PROMPT
    assert 'no-penalty' not in zero_prompt
    era_prompt, _ = system_prompt_for(record, 'era_hint')
    assert '2014-2016 study period' in era_prompt
    rules = [{
        'id': 'trial', 'effective_from': date(2014, 1, 1),
        'effective_to': date(2015, 6, 30), 'text': 'verified policy',
        'sha256': 'a' * 64, 'source': 'synthetic',
    }]
    assert rule_for_record(record, rules)['id'] == 'trial'
    policy_prompt, metadata = system_prompt_for(
        record, 'policy_prompt', rules)
    assert 'verified policy' in policy_prompt
    assert metadata['policy_period_id'] == 'trial'


def test_model_json_parser_accepts_wrapped_json():
    prediction = parse_model_json(
        '```json\n{"verdict":"upheld","cited_articles":[19],'
        '"penalties":[],"reasoning_summary":"synthetic"}\n```',
        'case-1')
    assert prediction['verdict'] == 'upheld'
    assert prediction['reasoning_summary'] == 'synthetic'


def test_model_runner_rejects_gold_and_source_fields():
    clean = {'case_id': 'case-clean', 'input': {'reported_post': 'synthetic'}}
    assert_model_facing_record(clean)
    for forbidden in ('gold', 'official_text', 'source_url', 'reporter_name'):
        leaked = json.loads(json.dumps(clean))
        leaked['input'][forbidden] = 'must-not-reach-model'
        try:
            assert_model_facing_record(leaked)
            assert False, f'{forbidden} must be rejected'
        except ValueError as error:
            assert forbidden in str(error)


def test_resume_rejects_mixed_experiment_configuration():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'results.jsonl'
        path.write_text(json.dumps({
            'case_id': 'case-1',
            'run': {
                'run_id': 'run-a', 'condition': 'zero_shot',
                'model': 'model-a', 'max_tokens': 2048,
                'model_input_sha256': 'a' * 64,
                'data_processing_approval_id': None,
            },
        }) + '\n', encoding='utf-8')
        expected = {
            'run_id': 'run-a', 'condition': 'zero_shot',
            'model': 'model-a', 'max_tokens': 2048,
            'model_input_sha256': 'a' * 64,
            'data_processing_approval_id': None,
        }
        assert _load_existing_case_ids(path, expected) == {'case-1'}
        expected['model'] = 'model-b'
        try:
            _load_existing_case_ids(path, expected)
            assert False, 'resume with a different model must fail'
        except ValueError as error:
            assert 'configuration mismatch' in str(error)


def test_build_requires_valid_policy_date_for_paired_conditions():
    complaint = next(iter_complaints(SAMPLE_PATH))
    complaint = json.loads(json.dumps(complaint))
    complaint['rumor']['rumor_time'] = '2018 only'
    assert build_case(complaint, 'case-invalid-date') is None


def test_data_processing_approval_is_bound_to_input_and_model():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        inputs = root / 'inputs.jsonl'
        inputs.write_text('{"case_id":"synthetic"}\n', encoding='utf-8')
        digest = sha256_file(inputs)
        approval = {
            'approved': True,
            'approval_id': 'synthetic-approval-001',
            'purpose': 'historical-adjudication-benchmark',
            'provider': 'anthropic',
            'allowed_models': ['model-a'],
            'approved_input_sha256': digest,
            'expires_on': '2999-12-31',
        }
        path = root / 'approval.json'
        path.write_text(json.dumps(approval), encoding='utf-8')
        loaded = load_data_processing_approval(path, 'model-a', digest)
        assert loaded['approval_id'] == 'synthetic-approval-001'
        try:
            load_data_processing_approval(path, 'model-b', digest)
            assert False, 'unapproved model must fail'
        except ValueError as error:
            assert 'not covered' in str(error)


def test_rule_snapshot_distance_uses_calendar_days():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                ['timestamp', 'original', 'statuscode', 'digest'],
                ['20150228000000', 'url', '200', 'a'],
                ['20150302000000', 'url', '200', 'b'],
            ]

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    assert closest_snapshot(Session(), 'http://example.invalid', '20150301') \
        == '20150228000000'
    validate_rule_text('正文' * 300 + ' 第二十二条 ', 22)


def test_rules_manifest_requires_human_verification_and_no_overlap():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        text = '合成规则正文。' * 100
        (root / 'rule-a.txt').write_text(text, encoding='utf-8')
        (root / 'rule-b.txt').write_text(text, encoding='utf-8')
        manifest = {
            'human_version_verified': True,
            'periods': [
                {
                    'id': 'a', 'effective_from': '2014-01-01',
                    'effective_to': '2014-12-31', 'file': 'rule-a.txt',
                    'sha256': sha256_text(text), 'source': 'synthetic-review-a',
                },
                {
                    'id': 'b', 'effective_from': '2015-01-01',
                    'effective_to': '2015-12-31', 'file': 'rule-b.txt',
                    'sha256': sha256_text(text), 'source': 'synthetic-review-b',
                },
            ],
        }
        path = root / 'manifest.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        assert [entry['id'] for entry in load_rules_manifest(path)] == ['a', 'b']
        manifest['periods'][1]['effective_from'] = '2014-12-31'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        try:
            load_rules_manifest(path)
            assert False, 'overlapping policy periods must fail'
        except ValueError as error:
            assert 'overlapping' in str(error)


def main():
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print(f'PASS {name}')
            except AssertionError:
                failures += 1
                import traceback
                print(f'FAIL {name}')
                traceback.print_exc()
    if failures:
        sys.exit(f'{failures} test(s) failed')
    print('All tests passed.')


if __name__ == '__main__':
    main()
