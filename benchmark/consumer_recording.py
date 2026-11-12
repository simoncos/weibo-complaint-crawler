"""Copyable, stdlib-only records of final consumer bodies or SDK arguments.

Pass the object after all consumer transformations. This does not serialize an
SDK request, send it, log prompts, read credentials, or resolve model settings.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

DIGEST_ALGORITHM = "sorted-json-utf8-v1"
SCALAR_PARAMETERS = {
    "model", "max_tokens", "max_completion_tokens", "temperature", "top_p",
    "top_k", "stream", "seed", "presence_penalty", "frequency_penalty", "n",
    "reasoning_effort",
}
SOURCE_FIELDS = {
    "schema_version", "catalog_key", "catalog_id", "emitter_revision",
    "library_version", "requested_level", "mechanism", "sampling_inert",
}
SENSITIVE_KEYS = {"authorization", "apikey", "access_token", "api_key", "headers"}


def request_digest(body: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _reject_credentials(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("request keys must be strings")
            if key.lower().replace("-", "_") in SENSITIVE_KEYS:
                raise ValueError("pass request content without credentials or headers")
            if key == "extra_body":
                _reject_credentials(item)


def _configuration(body: Mapping[str, Any]) -> dict[str, Any]:
    # Only known configuration is projected. Unknown structures (including
    # prompt-bearing tools and JSON-schema descriptions) remain covered by the
    # whole-object digest without appearing as plaintext in the record.
    result = {key: deepcopy(body[key]) for key in SCALAR_PARAMETERS if key in body
              and isinstance(body[key], (str, int, float, bool))}
    for key, allowed in {
        "thinking": {"type", "budget_tokens"},
        "reasoning": {"effort", "exclude", "max_tokens", "enabled"},
    }.items():
        if isinstance(body.get(key), dict):
            result[key] = {name: deepcopy(item) for name, item in body[key].items()
                           if name in allowed and isinstance(item, (str, int, float, bool))}
    if isinstance(body.get("response_format"), dict):
        raw = body["response_format"]
        result["response_format"] = {"configuration_sha256": request_digest(raw)}
        if raw.get("type") in {"text", "json_object", "json_schema"}:
            result["response_format"]["type"] = raw["type"]
    for key in ("tools", "tool_choice", "stop", "system"):
        if key in body:
            result[key + "_sha256"] = request_digest({key: body[key]})
    if isinstance(body.get("extra_body"), dict):
        result["extra_body"] = _configuration(body["extra_body"])
    return result


def record_final_request(
    body: Mapping[str, Any], *, api_flavor: str,
    representation: str = "request_body",
    decision_record: Mapping[str, Any] | None = None,
    digest_request: Callable[[dict[str, Any]], str] | None = None,
    digest_algorithm: str | None = None,
) -> dict[str, Any]:
    """Capture supplied final content, without claiming SDK wire-byte evidence.

    Use representation='sdk_arguments' when recording kwargs after a wrapper,
    and 'request_body' for a consumer-assembled JSON body. A custom digest must
    carry a consumer-owned algorithm label, so historical hashes stay distinct.
    """
    if api_flavor not in {"openai-compatible", "anthropic-messages"}:
        raise ValueError("unsupported api_flavor")
    if representation not in {"request_body", "sdk_arguments"}:
        raise ValueError("invalid representation")
    if digest_request is None:
        if digest_algorithm not in {None, DIGEST_ALGORITHM}:
            raise ValueError("a custom algorithm needs its digest function")
        algorithm = DIGEST_ALGORITHM
    else:
        if not digest_algorithm or digest_algorithm == DIGEST_ALGORITHM:
            raise ValueError("custom digest requires a distinct algorithm label")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", digest_algorithm):
            raise ValueError("invalid digest algorithm label")
        algorithm = digest_algorithm
    final = deepcopy(dict(body))
    _reject_credentials(final)
    # Validate JSON and finite numbers even with a custom digest callback.
    content_digest = request_digest(final)
    callback_input = deepcopy(final)
    digest = (digest_request(callback_input) if digest_request else content_digest)
    if request_digest(callback_input) != content_digest:
        raise ValueError("digest callback must not mutate the request")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("digest must be a lowercase SHA-256 hex string")
    source = None if decision_record is None else {
        key: deepcopy(value) for key, value in decision_record.items() if key in SOURCE_FIELDS
    }
    if source is not None:
        _reject_credentials(source)
        request_digest(source)
    return {
        "record_schema_version": 1,
        "observation": "consumer_supplied_final_content",
        "representation": representation,
        "api_flavor": api_flavor,
        "digest_algorithm": algorithm,
        "request_body_sha256": digest,
        "final_content_sha256": content_digest,
        "final_content_digest_algorithm": DIGEST_ALGORITHM,
        "sent_parameters": _configuration(final),
        "model_decision_source": source,
    }


def validate_request_record(
    body: Mapping[str, Any], record: Mapping[str, Any], *,
    digest_request: Callable[[dict[str, Any]], str] | None = None,
) -> bool:
    """Check that content and projected parameters still match this record."""
    current = record_final_request(
        body, api_flavor=record["api_flavor"], representation=record["representation"],
        digest_request=digest_request, digest_algorithm=record["digest_algorithm"],
        decision_record=record.get("model_decision_source"),
    )
    return current == dict(record)
