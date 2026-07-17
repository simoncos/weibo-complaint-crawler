"""Load complaint records from a MongoDB dump.

Supports JSON Lines (mongoexport default), a single JSON array file, and
mongo-shell-style pretty exports (ObjectId(...) / NumberInt(...) constructs,
one pretty-printed document after another). Extended-JSON wrappers like
{"$oid": ...} / {"$numberInt": ...} are unwrapped.
"""

import json
import re

_RE_SHELL_CONSTRUCT = re.compile(
    r'ObjectId\("([0-9a-fA-F]+)"\)'
    r'|NumberInt\((-?\d+)\)'
    r'|NumberLong\("?(-?\d+)"?\)'
    r'|ISODate\("([^"]*)"\)')


def _replace_shell_construct(m):
    oid, number_int, number_long, isodate = m.groups()
    if oid is not None:
        return json.dumps(oid)
    if number_int is not None:
        return number_int
    if number_long is not None:
        return number_long
    return json.dumps(isodate)


def _iter_mongo_shell(f):
    """Yield dicts from a mongo-shell pretty export (documents end with '}'
    at the start of a line)."""
    buffer = []
    for line in f:
        buffer.append(line)
        if line.rstrip() == '}':
            text = _RE_SHELL_CONSTRUCT.sub(_replace_shell_construct, ''.join(buffer))
            buffer = []
            yield json.loads(text.rstrip().rstrip(','))
    if any(line.strip() for line in buffer):
        raise ValueError('trailing partial document in mongo shell dump')


def _unwrap_extended_json(value):
    if isinstance(value, dict):
        if len(value) == 1:
            key = next(iter(value))
            if key in ('$oid', '$date', '$numberLong', '$numberInt', '$numberDouble'):
                inner = value[key]
                if key in ('$numberLong', '$numberInt'):
                    return int(inner)
                if key == '$numberDouble':
                    return float(inner)
                return _unwrap_extended_json(inner)
        return {k: _unwrap_extended_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_unwrap_extended_json(v) for v in value]
    return value


def iter_complaints(path):
    """Yield complaint dicts from a .jsonl / .json dump file."""
    with open(path, encoding='utf-8') as f:
        head = f.read(4096)
        f.seek(0)
        if head.lstrip().startswith('['):
            for record in json.load(f):
                yield _unwrap_extended_json(record)
        elif 'ObjectId(' in head or 'NumberInt(' in head:
            for record in _iter_mongo_shell(f):
                yield _unwrap_extended_json(record)
        else:
            for line in f:
                line = line.strip()
                if line:
                    yield _unwrap_extended_json(json.loads(line))
