"""Fetch the three generations of Weibo rulebooks from the Wayback Machine.

The verdicts in the dump cite three rulebook URLs (counts in the full dump):

    http://weibo.com/z/guize/guiding.html             6,339x  gen1 2012-13
    http://service.account.weibo.com/roles/guiding   23,174x  gen2 2014-16 (content changed over time!)
    http://service.account.weibo.com/roles/xize       1,439x  gen3 2017-18

For each (url, target-date) pair this script asks the Wayback CDX API for the
closest snapshot, downloads it, strips HTML, and writes text + provenance.

Run this OUTSIDE restricted environments (needs access to web.archive.org):
    pip install requests beautifulsoup4
    python scripts/fetch_rules.py --out data/rules
"""

import argparse
import json
import os
import re

import requests

TARGETS = [
    # (label, original URL, snapshot target date YYYYMMDD)
    ('gen1_sina_guiding_2013', 'http://weibo.com/z/guize/guiding.html', '20130601'),
    ('gen2_guiding_trial_2015', 'http://service.account.weibo.com/roles/guiding', '20150301'),
    ('gen2_guiding_2016', 'http://service.account.weibo.com/roles/guiding', '20160601'),
    ('gen3_xize_2018', 'http://service.account.weibo.com/roles/xize', '20180601'),
    ('banfa_2018', 'http://service.account.weibo.com/roles/banfa', '20180601'),
]

CDX = 'https://web.archive.org/cdx/search/cdx'


def closest_snapshot(session, url, target):
    params = {'url': url, 'output': 'json', 'filter': 'statuscode:200',
              'collapse': 'timestamp:8', 'limit': '200'}
    rows = session.get(CDX, params=params, timeout=60).json()
    if len(rows) < 2:
        return None
    timestamps = [r[1] for r in rows[1:]]
    return min(timestamps, key=lambda t: abs(int(t[:8]) - int(target)))


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='data/rules')
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    session = requests.Session()
    session.headers['User-Agent'] = 'weibo-complaint-crawler-research/1.0'
    for label, url, target in TARGETS:
        try:
            ts = closest_snapshot(session, url, target)
            if not ts:
                print(f'[{label}] no snapshot found for {url}')
                continue
            snap_url = f'https://web.archive.org/web/{ts}/{url}'
            html = session.get(snap_url, timeout=120).text
            text = html_to_text(html)
            base = os.path.join(args.out, label)
            with open(base + '.txt', 'w', encoding='utf-8') as f:
                f.write(text)
            with open(base + '.meta.json', 'w', encoding='utf-8') as f:
                json.dump({'original_url': url, 'snapshot': snap_url,
                           'snapshot_timestamp': ts, 'target_date': target}, f,
                          ensure_ascii=False, indent=2)
            n_articles = len(re.findall(r'第[0-9一二三四五六七八九十百]+条', text))
            print(f'[{label}] {snap_url} -> {base}.txt ({len(text)} chars, '
                  f'{n_articles} 条 markers)')
        except Exception as e:
            print(f'[{label}] FAILED: {e}')


if __name__ == '__main__':
    main()
