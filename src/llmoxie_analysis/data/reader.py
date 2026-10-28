"""reader.py — flatten LiteLLM spend-log JSONL files into a tidy DataFrame.

Each row in the output corresponds to one content block within a message
(or the entire message content when it is a plain string).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import jsonlines
import pandas as pd

logger = logging.getLogger(__name__)


def _parse_end_user(raw: Any) -> dict[str, str]:
    """Return device_id/account_uuid/session_id from the end_user field.

    The field is usually a JSON-encoded string but may already be a dict
    or missing entirely.
    """
    if isinstance(raw, str):
        parsed = None
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            try:
                # row_to_json() writes JSONB TEXT fields with literal backslash+quote
                # pairs: {\"key\":\"val\"}.  json.loads fails on the raw string but
                # succeeds after replacing \" with ".
                parsed = json.loads(raw.replace('\\"', '"'))
            except (json.JSONDecodeError, TypeError):
                m = re.fullmatch(
                    r"user_(?P<device_id>[0-9a-f]*)_account_(?P<account_uuid>.*?)_session_(?P<session_id>[0-9a-f-]+)",
                    raw,
                )
                if m:
                    return m.groupdict()
        if parsed is not None:
            raw = parsed
    if isinstance(raw, dict):
        return {
            "device_id": raw.get("device_id", ""),
            "account_uuid": raw.get("account_uuid", ""),
            "session_id": raw.get("session_id", ""),
        }
    return {"device_id": "", "account_uuid": "", "session_id": ""}


def _base_row(record: dict[str, Any]) -> dict[str, Any]:
    """Extract record-level metadata shared by every block row."""
    eu = _parse_end_user(record.get("end_user"))
    metadata = record.get("metadata") or {}
    return {
        "request_id": record.get("request_id"),
        "start_time": record.get("startTime"),
        "end_time": record.get("endTime"),
        "device_id": eu["device_id"],
        "account_uuid": eu["account_uuid"],
        # end_user is the only source of session identity. The top-level
        # session_id is a per-request trace id LiteLLM mints fresh every
        # call, so falling back to it does not recover a session — it
        # invents a singleton one per record. "" marks it ungroupable.
        "session_id": eu["session_id"],
        "model": record.get("model"),
        "spend": record.get("spend"),
        "total_tokens": record.get("total_tokens"),
        "user_api_key": record.get("api_key"),
        "user_api_key_alias": metadata.get("user_api_key_alias"),
    }


_BLOCK_COLUMNS = ("text", "thinking", "tool_name", "tool_input", "tool_use_id")


def _block_columns(block: dict[str, Any]) -> dict[str, Any]:
    """Map one content block onto the flat per-block value columns.

    Every block row carries the same columns; which one is populated depends
    on ``block["type"]``. Unknown types are JSON-serialised into ``text`` so
    no data is lost.
    """
    columns: dict[str, Any] = dict.fromkeys(_BLOCK_COLUMNS)
    btype = block.get("type")

    if btype == "text":
        columns["text"] = block.get("text")
    elif btype == "thinking":
        columns["thinking"] = block.get("thinking")
    elif btype == "tool_use":
        columns["tool_name"] = block.get("name")
        columns["tool_use_id"] = block.get("id")
        input_val = block.get("input")
        columns["tool_input"] = json.dumps(input_val) if input_val is not None else None
    else:
        columns["text"] = json.dumps(block)

    return columns


def _row_from_block(
    base: dict[str, Any],
    direction: str,
    msg_idx: int | None,
    role: str,
    block_idx: int,
    block: dict[str, Any] | str,
    *,
    include_thinking: bool,
    include_tool_use: bool,
) -> dict[str, Any] | None:
    """Convert one content block into a row dict, or None if it is filtered out."""
    if isinstance(block, str):
        block = {"type": "text", "text": block}

    btype = block.get("type", "unknown")
    if btype == "thinking" and not include_thinking:
        return None
    if btype == "tool_use" and not include_tool_use:
        return None

    cache = block.get("cache_control")

    return {
        **base,
        "direction": direction,
        "msg_idx": msg_idx,
        "block_idx": block_idx,
        "role": role,
        "type": btype,
        **_block_columns(block),
        "cache_control": cache.get("type") if isinstance(cache, dict) else None,
    }


def _iter_blocks(content: Any) -> Iterator[dict[str, Any] | str]:
    """Yield a message's content blocks, whether it is a string or a list."""
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        yield from content


def _rows_from_record(
    record: dict[str, Any], *, include_thinking: bool, include_tool_use: bool
) -> list[dict[str, Any]]:
    """Convert one raw LiteLLM spend-log record into its flattened block rows."""
    kwargs = {
        "include_thinking": include_thinking,
        "include_tool_use": include_tool_use,
    }
    rows: list[dict[str, Any]] = []
    base = _base_row(record)

    def _add(direction: str, msg_idx: int | None, role: str, content: Any) -> None:
        """Append every surviving block row of one message's content."""
        for block_idx, block in enumerate(_iter_blocks(content)):
            row = _row_from_block(base, direction, msg_idx, role, block_idx, block, **kwargs)
            if row is not None:
                rows.append(row)

    # ── Input messages ────────────────────────────────────────────
    messages = record.get("proxy_server_request", {}).get("messages", [])
    for msg_idx, message in enumerate(messages):
        _add("input", msg_idx, message.get("role", ""), message.get("content", ""))

    # ── Output message ────────────────────────────────────────────
    out_msg = None
    response = record.get("response")
    if response:
        try:
            out_msg = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "request_id=%s: could not read response.choices[0].message: %s",
                base["request_id"],
                exc,
            )

    if out_msg:
        _add(
            "output",
            None,
            out_msg.get("role", "assistant"),
            out_msg.get("content", ""),
        )
    elif not messages:
        logger.warning(
            "request_id=%s: record yielded neither input nor output messages",
            base["request_id"],
        )

    return rows


def load_messages_from_records(
    records: Iterable[dict[str, Any]],
    *,
    include_thinking: bool = False,
    include_tool_use: bool = True,
) -> pd.DataFrame:
    """Flatten an iterable of already-parsed LiteLLM spend-log records into a tidy DataFrame.

    Same output as :func:`load_messages`, but takes record dicts directly
    instead of reading them from a ``.jsonl`` file on disk — useful for
    records read from a zip member in memory, or adapted from another
    source format.
    """
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.extend(
            _rows_from_record(
                record,
                include_thinking=include_thinking,
                include_tool_use=include_tool_use,
            )
        )
    return pd.DataFrame(rows)


def load_messages(
    path: str | Path,
    *,
    include_thinking: bool = False,
    include_tool_use: bool = True,
) -> pd.DataFrame:
    """Read a LiteLLM spend log JSONL file and return a tidy DataFrame.

    Each row corresponds to one content block within a message.  Both the
    input conversation (``proxy_server_request.messages``) and the model
    output (``response.choices[0].message``) are included, distinguished by
    the ``direction`` column (``"input"`` / ``"output"``).

    Parameters
    ----------
    path:
        Path to the ``.jsonl`` file.
    include_thinking:
        If *False* (default), blocks with ``type="thinking"`` are dropped.
    include_tool_use:
        If *False*, blocks with ``type="tool_use"`` are dropped.

    Returns
    -------
    pd.DataFrame
        Columns: request_id, start_time, device_id, account_uuid, session_id,
        model, spend, total_tokens, user_api_key, user_api_key_alias,
        direction, msg_idx, block_idx, role, type, text, thinking, tool_name,
        tool_input, tool_use_id, cache_control.
    """
    with jsonlines.open(Path(path)) as reader:
        return load_messages_from_records(reader, include_thinking=include_thinking, include_tool_use=include_tool_use)


def last_request_per_session(df: pd.DataFrame) -> pd.DataFrame:
    """Filter a messages DataFrame to only the longest request per session.

    Each request in a session re-sends the full conversation history, so
    the request with the most input messages is the final (and most complete)
    one. Ties are broken by ``start_time`` (latest wins).

    Parameters
    ----------
    df:
        DataFrame produced by :func:`load_messages`.

    Returns
    -------
    pd.DataFrame
        Subset of *df* containing only rows from the longest request per
        ``session_id``.
    """
    longest = (
        df[(df["direction"] == "input") & (df["session_id"].notna() & df["session_id"].ne(""))]
        .groupby(["session_id", "request_id", "start_time"], dropna=False)["msg_idx"]
        .max()
        .reset_index()
        .sort_values(["msg_idx", "start_time"], ascending=[False, False])
        .groupby("session_id", as_index=False)
        .first()
    )[["request_id"]]

    return df.merge(longest, on="request_id")


def deduplicate_messages(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate a messages DataFrame to one row per unique content block.

    Since each request re-sends the full conversation history, input blocks
    appear once per request. This keeps only the earliest occurrence of each
    ``(session_id, msg_idx, block_idx)``, so ``start_time`` reflects when
    that message was actually introduced rather than the last request's time.

    Output blocks (``direction="output"``) are unique per request and are
    kept as-is.

    Parameters
    ----------
    df:
        DataFrame produced by :func:`load_messages`.

    Returns
    -------
    pd.DataFrame
        Deduplicated DataFrame with one row per unique content block.
    """
    input_rows = df[df["direction"] == "input"]
    has_session = input_rows["session_id"].notna() & input_rows["session_id"].ne("")
    input_deduped = pd.concat(
        [
            input_rows[has_session]
            .sort_values(["start_time", "msg_idx", "block_idx"])
            .drop_duplicates(subset=["session_id", "msg_idx", "block_idx"]),
            input_rows[~has_session],
        ]
    ).sort_values(["start_time", "msg_idx", "block_idx"])
    return pd.concat(
        [input_deduped, df[df["direction"] == "output"]],
        ignore_index=True,
    )


def normalize_model_name(model: str | None) -> str | None:
    """Clean up a raw model string into one consistent short form.

    Model names show up in inconsistent formats depending on provider
    routing, e.g. ``bedrock/anthropic.claude-4-6-sonnet-20250929-v1:0`` or
    ``us.anthropic.claude-3-5-haiku-20241022-v1:0``. This strips provider
    prefixes, date/version suffixes, and reorders to
    ``claude-<family>-<major>.<minor>`` (e.g. ``claude-sonnet-4.6``).
    """
    if not model:
        return model
    # Handle '--model X' CLI-style entries
    m = re.match(r"^--model\s+(.+)", model)
    if m:
        model = "claude-" + m.group(1)
    # Strip provider prefixes
    for pattern in [
        r"^bedrock/us\.anthropic\.",
        r"^bedrock/anthropic\.",
        r"^us\.anthropic\.",
        r"^anthropic/",
        r"^perplexity/",
        r"^bedrock/",
        r"^bedrock-",
    ]:
        sub = re.sub(pattern, "", model)
        if sub != model:
            model = sub
            break
    # Reorder 'claude-{major}-{minor}-{family}' → 'claude-{family}-{major}.{minor}'
    model = re.sub(r"^(claude)-(\d+)-(\d+)-(haiku|sonnet|opus)", r"\1-\4-\2.\3", model)
    # Strip date suffixes like -20250929
    model = re.sub(r"-20\d{6}", "", model)
    # Strip version suffixes like -v1:0 or -v1
    model = re.sub(r"-v\d+(?::\d+)?$", "", model)
    # Convert trailing hyphenated version numbers to dot notation: -4-6 → -4.6
    return re.sub(r"-(\d+)-(\d+)$", r"-\1.\2", model)
