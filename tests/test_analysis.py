"""Unit tests for the adjudication parser and reporter features.

Run with:  python -m tests.test_analysis   (or pytest)
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.load import iter_complaints
from analysis.official_parser import (
    parse_cited_articles, parse_cited_documents, parse_debunkers,
    parse_effect_delay_minutes, parse_official, parse_penalties, parse_verdict)
from analysis.reporter_features import (
    classify_reporter_type, extract_report_features, strip_reporter_prefix)
from analysis.stats import collect_stats, render_report
from benchmark.build_benchmark import build_instance

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_complaints.jsonl')

OFFICIAL_UPHELD = (
    '经查，此微博称“……”不实。@德州运河公安分局 已辟谣：…… 。'
    '被举报人言论构成“发布不实信息”。现根据《微博举报投诉操作细则》'
    '（http://service.account.weibo.com/roles/xize ）第19条，对被举报人处理如下：'
    '扣除信用积分2分。上述处理在公布后60分钟内生效。')

OFFICIAL_MUTE = (
    '被举报人言论构成“发布不实信息”。根据《微博举报投诉操作细则》第二十一条，'
    '对被举报人处理如下：扣除信用积分5分，禁言7天，禁被关注30天，删除该微博。'
    '上述处理在公布后30分钟内生效。')

OFFICIAL_REJECTED = '经查，被举报人言论不构成“发布不实信息”，本次举报不成立。'

OFFICIAL_UNDETERMINED = '经查，现有证据暂无法判定被举报内容真实性，暂不处理。'


def test_parse_verdict():
    assert parse_verdict(OFFICIAL_UPHELD) == 'upheld'
    assert parse_verdict(OFFICIAL_REJECTED) == 'rejected'
    assert parse_verdict(OFFICIAL_UNDETERMINED) == 'undetermined'
    assert parse_verdict('') is None
    assert parse_verdict(None) is None


def test_parse_cited_articles():
    assert parse_cited_articles(OFFICIAL_UPHELD) == [19]
    assert parse_cited_articles(OFFICIAL_MUTE) == [21]
    assert parse_cited_articles('依据第3条、第十二条与第19条') == [3, 12, 19]
    assert parse_cited_articles('无引用') == []


def test_parse_cited_documents():
    assert parse_cited_documents(OFFICIAL_UPHELD) == ['微博举报投诉操作细则']


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
    assert parse_debunkers(OFFICIAL_UPHELD) == ['德州运河公安分局']

    full = parse_official(OFFICIAL_MUTE)
    assert full['verdict'] == 'upheld'
    assert full['cited_articles'] == [21]
    assert len(full['penalties']) == 4


def test_reporter_features():
    assert classify_reporter_type('漳州普法官方微博') == 'government'
    assert classify_reporter_type('XX日报官方账号') in ('government', 'media')
    assert classify_reporter_type('专业辟谣账号') == 'debunker'
    assert classify_reporter_type('执业律师') == 'legal'
    assert classify_reporter_type('爱吃可丽饼') == 'ordinary'
    assert classify_reporter_type(None) == 'ordinary'

    assert strip_reporter_prefix('漳州普法', '漳州普法：#微博辟谣# 已辟谣') == '#微博辟谣# 已辟谣'
    assert strip_reporter_prefix('A', None) == ''

    feats = extract_report_features({
        'reporter_name': '漳州普法',
        'reporter_description': '漳州普法官方微博',
        'reporter_gender': 'male',
        'report_time': '2018-08-30 12:47',
        'report_text': '漳州普法：#微博辟谣# 详情 https://weibo.com/xxx',
    })
    assert feats['reporter_type'] == 'government'
    assert feats['uses_debunk_hashtag']
    assert feats['has_evidence_url']


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
    assert instance['input']['reported_user']['alias'].startswith('user_')
    assert '每日上海 ：' not in instance['input']['reported_post']

    # unusable record -> None
    assert build_instance({'rumor': {}, 'official': {}}) is None


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
