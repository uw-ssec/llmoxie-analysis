"""sources.py — normalize each logging path's records into one common shape.

LLMoxie logs every gateway request down two paths with different record
shapes: ADLS (one JSON blob per request, message content never truncated) and
the LiteLLM PostgreSQL spend logs (exported as JSONL, long messages may be
truncated). This module is the boundary that keeps the rest of the pipeline
from knowing which path a record came from.

The spend-log row shape *is* the common format, because that is what
:mod:`reader` already consumes, so :func:`from_litellm` is a pass-through and
:func:`from_adls` does the reshaping. Both must produce identical
common-format output for equivalent input.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _epoch_to_iso(ts: float | None) -> str | None:
    """Convert a Unix epoch timestamp to an ISO-8601 string.

    Matches the format used by the litellm_spend_logs JSONL export, e.g.
    ``"2026-01-02T23:41:18.414000Z"``.
    """
    if ts is None:
        return None
    return datetime.fromtimestamp(float(ts), tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def from_adls(record: dict[str, Any], fallback_request_id: str = "") -> dict[str, Any]:
    """Adapt one ADLS per-request JSON record into the common record shape.

    Sourced from ``kwargs["standard_logging_object"]``, litellm's own
    normalized per-request log object — verified against a real sample from
    the ``litellm-logs`` container (a GitHub Copilot / gpt-5.3-codex request
    via the Responses API), which has the same field names
    (``end_user``, ``messages``, ``model``, ``total_tokens``, ...) as the
    litellm_spend_logs JSONL export, just with epoch-float timestamps
    instead of ISO strings.

    Known gap: ``standard_logging_object["response"]`` keeps the raw
    provider-shaped response. For Chat Completions calls that's the
    ``{"choices": [...]}`` shape reader.py already parses. For Responses-API
    calls (``call_type == "responses"``, seen from Copilot/gpt-5.3-codex
    traffic) the reply is shaped as ``{"output": [...]}`` instead, which
    reader.py does not yet parse — reader.py logs a warning and the
    session's messages simply won't include that request's final reply.
    Follow-up work if Responses-API output needs to be included.

    Parameters
    ----------
    record:
        One parsed ADLS blob, as written by the gateway's ``AdlLogger``.
    fallback_request_id:
        Used when the record carries no id of its own. Callers reading from
        ``logs/<yyyy>/<mm>/<dd>/<request_id>.json`` pass the filename stem.

    Returns
    -------
    dict[str, Any]
        A record in the common (spend-log) shape.
    """
    kw = record.get("kwargs") or {}
    slo = kw.get("standard_logging_object") or {}
    metadata = slo.get("metadata") or {}

    return {
        "request_id": slo.get("id") or fallback_request_id,
        "startTime": _epoch_to_iso(slo.get("startTime")),
        "endTime": _epoch_to_iso(slo.get("endTime")),
        "end_user": slo.get("end_user"),
        "model": slo.get("model"),
        "spend": slo.get("response_cost"),
        "total_tokens": slo.get("total_tokens"),
        "api_key": metadata.get("user_api_key_hash"),
        "metadata": {"user_api_key_alias": metadata.get("user_api_key_alias")},
        "proxy_server_request": {"messages": slo.get("messages") or []},
        "response": slo.get("response") or {},
    }


def from_litellm(record: dict[str, Any]) -> dict[str, Any]:
    """Adapt one LiteLLM spend-log record into the common record shape.

    A pass-through: the spend-log shape is the common format. It exists so
    callers have one symmetric entry point per source rather than special-casing
    the path that happens to need no work.
    """
    return record
