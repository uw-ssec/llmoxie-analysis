"""session_recovery.py — recover session grouping when ``end_user`` has no session id.

Every gateway request resends the whole conversation so far, so the *first user
turn* is a natural conversation fingerprint: all requests belonging to one
session carry a byte-identical copy of it. This module turns that observation
into a candidate session key and provides the machinery to score it against the
requests whose ``end_user`` *did* parse, which are the only ground truth
available.

Nothing here retains prompt text. Message bodies are reduced to salted-free
SHA-256 digests at extraction time, so the resulting frame is safe to cache and
to aggregate over — see ``knowledge/datasets/pii-handling.md``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Sequence
from itertools import pairwise
from pathlib import Path
from typing import Any

import jsonlines
import pandas as pd
from tqdm import tqdm

from ..data.reader import _parse_end_user

#: Characters of the first user turn used for the prefix digest. A client that
#: re-renders volatile context (timestamps, token budgets) at the *end* of its
#: opening turn still produces a stable prefix.
PREFIX_CHARS = 2000

#: Columns that identify a request's conversation independently of ``end_user``.
#: ``first_user_sha`` is the fingerprint; the rest narrow collisions between
#: distinct conversations that happen to open with identical text.
KEY_COMPONENTS = ("first_user_sha", "alias_sha", "call_type", "model")


def sha(value: str) -> str:
    """Return a short stable digest of ``value`` (empty string maps to "")."""
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:16]


def _text_of(content: Any) -> str:
    """Flatten a message ``content`` field to plain text.

    Content is either a plain string (Chat Completions) or a list of typed
    blocks (Anthropic Messages). Only ``text`` blocks contribute; a turn made
    entirely of tool results flattens to the empty string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in parts if p)
    return ""


def first_user_text(messages: Sequence[dict[str, Any]]) -> str:
    """Return the text of the first ``user`` turn, or "" when there is none.

    The first *message* is not usable directly: 1,620 requests in the Jan-Mar
    2026 extract open with a ``system`` turn, and a system prompt is shared by
    every session of a given agent, so keying on it would merge them all.
    """
    for message in messages:
        if message.get("role") == "user":
            return _text_of(message.get("content"))
    return ""


def request_features(record: dict[str, Any]) -> dict[str, Any]:
    """Reduce one raw spend-log record to the fields session recovery needs.

    Returns digests and counts only — never prompt text.
    """
    psr = record.get("proxy_server_request") or {}
    messages = psr.get("messages") or []
    metadata = record.get("metadata") or {}
    eu = _parse_end_user(record.get("end_user"))

    opening = first_user_text(messages)
    system = psr.get("system")
    tools = psr.get("tools")

    return {
        "request_id": record.get("request_id") or "",
        "native_session_id": record.get("session_id") or "",
        "eu_session_id": eu["session_id"],
        "eu_device_id": eu["device_id"],
        "eu_account_uuid": eu["account_uuid"],
        "alias_sha": sha(str(metadata.get("user_api_key_alias") or "")),
        "call_type": record.get("call_type") or "",
        "model": record.get("model") or "",
        "status": record.get("status") or "",
        "start_time": record.get("startTime") or "",
        "end_time": record.get("endTime") or "",
        "n_messages": len(messages),
        "spend": record.get("spend") or 0.0,
        "total_tokens": record.get("total_tokens") or 0,
        "first_user_sha": sha(opening),
        "first_user_prefix_sha": sha(opening[:PREFIX_CHARS]),
        "first_user_len": len(opening),
        "system_sha": sha(_text_of(system) if system is not None else ""),
        "tools_sha": sha(json.dumps(tools, sort_keys=True) if tools else ""),
        "message_shas": [sha(_text_of(m.get("content"))) for m in messages],
    }


def iter_features(path: Path) -> Iterator[dict[str, Any]]:
    """Yield :func:`request_features` for every record in a JSONL extract."""
    with jsonlines.open(path) as reader:
        for record in reader:
            if isinstance(record, dict):
                yield request_features(record)


def build_features(path: Path, *, progress: bool = True) -> pd.DataFrame:
    """Stream a JSONL extract into a per-request feature frame.

    Streaming matters: the extracts are ~1 GB because every record repeats the
    whole conversation, while the feature frame is a few MB.
    """
    rows = iter_features(path)
    if progress:
        rows = tqdm(rows, unit="rec", desc="extracting features")
    frame = pd.DataFrame(list(rows))
    frame["start_dt"] = pd.to_datetime(frame["start_time"], format="ISO8601", utc=True)
    return frame.sort_values("start_dt").reset_index(drop=True)


def assign_keys(
    frame: pd.DataFrame,
    components: Sequence[str] = KEY_COMPONENTS,
    *,
    gap_minutes: float | None = None,
) -> pd.Series:
    """Label each request with a candidate session id built from ``components``.

    Requests sharing every component get the same label. With ``gap_minutes``
    set, a group is additionally cut wherever consecutive requests are further
    apart in time than the threshold — this is standard sessionization, and it
    separates the case where one person re-runs an identical opening prompt on
    a later day into two conversations rather than one.

    Requests with an empty ``first_user_sha`` (no user turn at all) get a label
    unique to themselves: they carry no fingerprint, so they cannot be joined
    to anything without fabricating a link.
    """
    parts = [frame[c].astype(str) for c in components]
    key = parts[0].str.cat(parts[1:], sep="|") if len(parts) > 1 else parts[0]

    unkeyable = frame["first_user_sha"].eq("")
    key = key.mask(unkeyable, "singleton|" + frame["request_id"].astype(str))

    if gap_minutes is None:
        return key

    order = frame.sort_values("start_dt").index
    ordered_key = key.loc[order]
    gap = frame.loc[order, "start_dt"].groupby(ordered_key, sort=False).diff()
    new_run = (gap > pd.Timedelta(minutes=gap_minutes)).fillna(value=False)
    suffix = new_run.groupby(ordered_key, sort=False).cumsum()
    return (ordered_key + "#" + suffix.astype(str)).reindex(frame.index)


def _pair_count(sizes: pd.Series) -> int:
    """Count unordered within-group pairs, summed over groups."""
    return int((sizes * (sizes - 1) // 2).sum())


def partition_metrics(truth: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """Score a predicted grouping against known session ids.

    Two complementary views, because the failure modes have different costs:

    **Pairwise precision / recall** treats every pair of requests as a question
    ("same conversation?"). Precision is the share of pairs the key put
    together that truly belong together — low precision means distinct
    conversations were *merged*, which silently concatenates two people's work.
    Recall is the share of truly-together pairs the key found — low recall
    means a conversation was *split*, which inflates session counts the same
    way the native-``session_id`` fallback does. F1 is their harmonic mean.
    Pair counting is size-aware: getting one 300-request session right counts
    for far more than getting a 2-request session right.

    **Exact session rate** is the stricter, more legible number: the share of
    true sessions recovered with every request present and nothing extra.
    """
    table = pd.crosstab(truth, predicted)
    tp = _pair_count(pd.Series(table.to_numpy().ravel()))
    same_true = _pair_count(table.sum(axis=1))
    same_pred = _pair_count(table.sum(axis=0))

    precision = tp / same_pred if same_pred else 1.0
    recall = tp / same_true if same_true else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    true_sizes = table.sum(axis=1)
    pred_sizes = table.sum(axis=0)
    # A true session is recovered exactly when all of its requests sit in one
    # predicted cluster and that cluster holds nothing else.
    exact = 0
    for session, row in table.iterrows():
        hit = row[row > 0]
        if len(hit) == 1 and pred_sizes[hit.index[0]] == true_sizes[session]:
            exact += 1

    n_true = int((true_sizes > 0).sum())
    return {
        "n_requests": int(table.to_numpy().sum()),
        "n_true_sessions": n_true,
        "n_pred_clusters": int((pred_sizes > 0).sum()),
        "pair_precision": precision,
        "pair_recall": recall,
        "pair_f1": f1,
        "exact_session_rate": exact / n_true if n_true else 0.0,
        "n_split": int(((table > 0).sum(axis=1) > 1).sum()),
        "n_merged": int(((table > 0).sum(axis=0) > 1).sum()),
    }


def _common_prefix_len(left: Sequence[str], right: Sequence[str]) -> int:
    """Count leading elements two sequences share."""
    n = 0
    for a, b in zip(left, right, strict=False):
        if a != b:
            break
        n += 1
    return n


def consecutive_overlap(frame: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Measure how much conversation history consecutive requests share.

    For each adjacent pair of requests within a group (ordered by time),
    reports the length of their common leading run of messages as a fraction
    of the shorter history.

    This is the test of whether a group really is *one* conversation. Because
    every request resends the whole history so far, two requests from the same
    thread must share a long prefix; a fraction near zero means the later
    request started a different conversation under the same label.
    """
    rows: list[dict[str, Any]] = []
    for label, part in frame.sort_values("start_dt").groupby(group_col, sort=False):
        histories = list(part["message_shas"])
        for earlier, later in pairwise(histories):
            shorter = min(len(earlier), len(later))
            if not shorter:
                continue
            shared = _common_prefix_len(earlier, later)
            rows.append(
                {
                    group_col: label,
                    "shared_messages": shared,
                    "shared_fraction": shared / shorter,
                    "is_continuation": bool(len(earlier) <= len(later) and shared == len(earlier)),
                }
            )
    return pd.DataFrame(rows)
