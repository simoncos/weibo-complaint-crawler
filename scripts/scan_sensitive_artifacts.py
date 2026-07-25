"""Fail when release-facing data artifacts contain obvious identifiers.

This is a narrow guardrail, not an anonymization certificate. By default it
scans release-facing documentation, tracked data fixtures and common generated
JSONL names in the repository.
"""

import argparse
import re
import sys
from pathlib import Path


PATTERNS = {
    'weibo_user_url': re.compile(r'https?://(?:www\.)?weibo\.com/(?:u/)?\d+', re.I),
    'weibo_avatar_url': re.compile(r'https?://[^\s"\']*sinaimg\.cn/', re.I),
    'qq_contact': re.compile(r'(?i)(?:qq|企鹅)[\s:：号]*[1-9]\d{4,11}'),
    'phone_number': re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)'),
    'at_handle': re.compile(r'@[\w\-\u3400-\u9fff]{2,}'),
}

DEFAULT_GLOBS = (
    'README.md',
    'docs/**/*.md',
    'data/**/*.json',
    'data/**/*.jsonl',
    'data/**/*.ndjson',
    'instances*.jsonl',
    'samples*.jsonl',
    'predictions*.jsonl',
    'eval_results*.jsonl',
)


def iter_paths(root, supplied):
    if supplied:
        for raw in supplied:
            path = Path(raw)
            yield path if path.is_absolute() else root / path
        return
    seen = set()
    for pattern in DEFAULT_GLOBS:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def scan(path, root):
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    text = path.read_text(encoding='utf-8', errors='replace')
    findings = []
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count('\n', 0, match.start()) + 1
            findings.append((relative, line, name, match.group(0)[:80]))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', help='optional files to scan')
    parser.add_argument('--root', default='.', help='repository root')
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    findings = []
    for path in iter_paths(root, args.paths):
        if path.exists():
            findings.extend(scan(path.resolve(), root))
    for path, line, kind, excerpt in findings:
        print(f'{path}:{line}: {kind}: {excerpt}')
    if findings:
        raise SystemExit(f'{len(findings)} potential sensitive value(s) found')
    print('Sensitive-artifact scan passed (automated checks only).')


if __name__ == '__main__':
    main()
