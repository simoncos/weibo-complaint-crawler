"""Fetch and validate historical Weibo policy snapshots from Wayback.

Any missing snapshot, HTTP error, empty body, article mismatch or write failure
causes a non-zero exit. Retrieved text is accompanied by content hashes and
snapshot provenance, but still requires human version verification.
"""

import argparse
import hashlib
import json
import os
import re
from datetime import datetime

import requests


TARGETS = [
    ('gen1_sina_guiding_2013', 'http://weibo.com/z/guize/guiding.html',
     '20130601', 22),
    ('gen2_guiding_trial_2015',
     'http://service.account.weibo.com/roles/guiding', '20150301', 22),
    ('gen2_guiding_2016',
     'http://service.account.weibo.com/roles/guiding', '20160601', 23),
    ('gen3_xize_2018', 'http://service.account.weibo.com/roles/xize',
     '20180601', 19),
    ('banfa_2018', 'http://service.account.weibo.com/roles/banfa',
     '20180601', None),
]

CDX = 'https://web.archive.org/cdx/search/cdx'
CN_ARTICLES = {19: '十九', 22: '二十二', 23: '二十三'}


def _date(timestamp):
    return datetime.strptime(timestamp[:8], '%Y%m%d').date()


def closest_snapshot(session, url, target):
    target_date = _date(target)
    params = {
        'url': url,
        'output': 'json',
        'fl': 'timestamp,original,statuscode,digest',
        'filter': 'statuscode:200',
        'collapse': 'timestamp:8',
        'from': str(target_date.year - 1),
        'to': str(target_date.year + 1),
        'limit': '1000',
    }
    response = session.get(CDX, params=params, timeout=60)
    response.raise_for_status()
    rows = response.json()
    if len(rows) < 2:
        return None
    timestamps = [row[0] for row in rows[1:] if row and row[0].isdigit()]
    return min(
        timestamps,
        key=lambda timestamp: (abs(_date(timestamp) - target_date), timestamp))


def html_to_text(html):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style']):
            tag.decompose()
        text = soup.get_text('\n')
    except ImportError:
        text = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
        text = re.sub(r'<[^>]+>', '\n', text)
    return re.sub(r'\n{3,}', '\n\n', re.sub(r'[ \t]+', ' ', text)).strip()


def validate_rule_text(text, expected_article):
    if len(text) < 500:
        raise ValueError(f'rule text unexpectedly short: {len(text)} characters')
    if expected_article is None:
        return
    chinese = CN_ARTICLES[expected_article]
    pattern = re.compile(rf'第\s*(?:{expected_article}|{chinese})\s*条')
    if not pattern.search(text):
        raise ValueError(f'expected article {expected_article} not found')


def fetch_target(session, out_dir, label, url, target, expected_article):
    timestamp = closest_snapshot(session, url, target)
    if not timestamp:
        raise ValueError(f'no snapshot found for {url}')
    snapshot_url = f'https://web.archive.org/web/{timestamp}id_/{url}'
    response = session.get(snapshot_url, timeout=120)
    response.raise_for_status()
    text = html_to_text(response.text)
    validate_rule_text(text, expected_article)
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    base = os.path.join(out_dir, label)
    with open(base + '.txt', 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    metadata = {
        'label': label,
        'original_url': url,
        'snapshot_url': snapshot_url,
        'snapshot_timestamp': timestamp,
        'target_date': target,
        'expected_article': expected_article,
        'text_sha256': digest,
        'text_characters': len(text),
        'human_version_verified': False,
    }
    with open(base + '.meta.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='data/rules')
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    session = requests.Session()
    session.headers['User-Agent'] = 'weibo-complaint-crawler-research/2.0'
    failures = []
    for target in TARGETS:
        label = target[0]
        try:
            metadata = fetch_target(session, args.out, *target)
            print(f"[{label}] {metadata['snapshot_url']} -> "
                  f"sha256={metadata['text_sha256']}")
        except Exception as error:
            failures.append((label, error))
            print(f'[{label}] FAILED: {type(error).__name__}: {error}')
    if failures:
        raise SystemExit(f'{len(failures)} rule retrieval target(s) failed')


if __name__ == '__main__':
    main()
