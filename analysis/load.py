"""Load complaint records from a mongoexport dump.

Supports JSON Lines (mongoexport default) and a single JSON array file.
Extended-JSON wrappers like {"$oid": ...} / {"$numberInt": ...} are unwrapped.
"""

import json


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
        first = f.read(1)
        f.seek(0)
        if first == '[':
            for record in json.load(f):
                yield _unwrap_extended_json(record)
        else:
            for line in f:
                line = line.strip()
                if line:
                    yield _unwrap_extended_json(json.loads(line))
