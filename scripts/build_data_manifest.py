"""Build a reproducibility manifest for a local complaint dump.

The manifest records the content hash and record count without copying the
restricted dataset into the repository or exposing its absolute local path.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.load import iter_complaints


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root):
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'], cwd=root, check=False,
        capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def git_dirty(root):
    result = subprocess.run(
        ['git', 'status', '--porcelain'], cwd=root, check=False,
        capture_output=True, text=True)
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def detect_format(path):
    with path.open('r', encoding='utf-8') as f:
        head = f.read(4096).lstrip()
    if head.startswith('['):
        return 'json-array'
    if 'ObjectId(' in head or 'NumberInt(' in head:
        return 'mongo-shell-export'
    return 'json-lines'


def build_manifest(path, dataset_id, source, collected_through,
                   schema_version, repo_root):
    before = path.stat()
    record_count = 0
    top_level_fields = set()
    for record in iter_complaints(path):
        record_count += 1
        top_level_fields.update(record)
    digest = sha256_file(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('dump changed while the manifest was being generated')
    return {
        'manifest_version': 1,
        'dataset_id': dataset_id,
        'classification': 'restricted-research-data',
        'file_name': path.name,
        'format': detect_format(path),
        'bytes': after.st_size,
        'sha256': digest,
        'record_count': record_count,
        'top_level_fields': sorted(top_level_fields),
        'schema_version': schema_version,
        'collection': {
            'source': source,
            'collected_through': collected_through,
        },
        'code_commit': git_head(repo_root),
        'code_dirty': git_dirty(repo_root),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'release_approved': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump')
    parser.add_argument('--out', required=True)
    parser.add_argument('--dataset-id', default='weibo-cmc-complaints-2012-2018')
    parser.add_argument('--source', default='Weibo Community Management Center')
    parser.add_argument('--collected-through', default='2018-08-30')
    parser.add_argument('--schema-version', default='legacy-v1')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)

    dump = Path(args.dump).resolve()
    repo_root = REPO_ROOT
    manifest = build_manifest(
        dump, args.dataset_id, args.source, args.collected_through,
        args.schema_version, repo_root)
    out = Path(args.out)
    if out.exists() and not args.overwrite:
        parser.error(f'output already exists (use --overwrite intentionally): {out}')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                   encoding='utf-8')
    print(f"manifest: {out} ({manifest['record_count']} records, "
          f"sha256={manifest['sha256']})")


if __name__ == '__main__':
    main()
