"""group_sessions.py — turn raw LiteLLM spend-log requests into per-session conversations.

Each raw record is a single request/response pair, and re-sends the full
conversation history seen so far. This script groups those requests by
``session_id`` and reconstructs, for each session, the single full ordered
conversation (using the last/most-complete request in that session) plus
session-level stats (request count, spend, tokens, time span).

Usage
-----
    pixi run group-sessions path/to/jan-feb-march-2026.zip -o sessions.jsonl
    pixi run group-sessions path/to/adls/logs/ --format parquet

``path`` may be a single ``.jsonl`` file (the ``litellm_spend_logs_*.jsonl``
format produced by ``llmaven infra extract`` in the ``uw-ssec/llmoxie``
repo), a single ``.json`` file (one request
per file, the ADLS format from ``adl_logger.py``), a directory containing
either (searched recursively, so nested ``<yyyy>/<mm>/<dd>/`` layouts work),
or a ``.zip`` of them. The container does not change the result.

Every input streams through :func:`stream_sessions`: one pass to collect
per-session stats and spill block rows to an intermediate Parquet, a second to
rebuild each session from its chosen request. The intermediate lives in a
temporary directory unless ``--parquet-cache PATH`` asks to keep it, in which
case a later run over the same input reuses it instead of rescanning.

Thinking blocks are included; pass ``--no-thinking`` to drop them. Pass ``-v``
to keep the reader's per-record warnings rather than only an aggregate count.

Output defaults to JSONL, one JSON object per line, one line per session.
Pass ``--format parquet`` for a flat table instead (one row per message
block, session fields repeated per row):

    {
      "session_id": "...",
      "device_id": "...",
      "account_uuid": "...",
      "user_api_key_alias": "...",
      "models": ["claude-sonnet-4.6"],
      "n_requests": 4,
      "total_spend": 0.0192,
      "total_tokens": 1320,
      "start_time": "2026-03-28T02:46:57.632000Z",
      "end_time": "2026-03-28T02:51:10.221000Z",
      "messages": [
        {"role": "user", "content": [{"type": "text", "text": "..."}]},
        {"role": "assistant", "content": [{"type": "tool_use", "name": "...", "id": "...", "input": {...}}]},
        ...
      ]
    }
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import tempfile
import zipfile
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO, Any

import jsonlines
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

from .reader import _block_columns, _parse_end_user, _rows_from_record
from .sources import from_adls

logger = logging.getLogger(__name__)


def _iter_raw_records(input_path: Path) -> Iterator[dict[str, Any]]:
    """Yield raw record dicts from a file, directory, or zip.

    Supports ``.jsonl`` (the ``litellm_spend_logs_*.jsonl`` format from
    ``llmaven infra extract``) and individual ``.json`` files (one request
    per file, the ADLS format written by ``adl_logger.py``, e.g.
    ``logs/<yyyy>/<mm>/<dd>/<request_id>.json``). A directory is searched
    recursively so that nested date folders are picked up. Zip members are
    read directly from the archive without extracting to disk.
    """
    if input_path.is_dir():
        for p in sorted(input_path.rglob("*")):
            if p.suffix in (".jsonl", ".json"):
                yield from _iter_raw_records(p)
    elif input_path.suffix == ".zip":
        with zipfile.ZipFile(input_path) as zf:
            for name in sorted(zf.namelist()):
                if name.endswith(".jsonl"):
                    with (
                        zf.open(name) as fh,
                        jsonlines.Reader(io.TextIOWrapper(fh, encoding="utf-8")) as reader,
                    ):
                        yield from reader
                elif name.endswith(".json"):
                    yield from _load_adls_json(zf.open(name), name)
    elif input_path.suffix == ".jsonl":
        # An empty .jsonl file just yields no records below; no special-casing needed.
        with jsonlines.open(input_path) as reader:
            yield from reader
    elif input_path.suffix == ".json":
        with input_path.open("rb") as f:
            yield from _load_adls_json(f, str(input_path))
    else:
        logger.warning("Skipping file with unrecognized extension: %s", input_path)


def _load_adls_json(fh: IO[bytes], name: str) -> Iterator[dict[str, Any]]:
    """Parse one ADLS .json file, skipping (with a warning) if it's empty or corrupt.

    Unlike an empty .jsonl file, json.load() raises on an empty/corrupt file
    rather than quietly yielding nothing, so this needs an explicit guard.
    """
    try:
        record = json.load(fh)
    except json.JSONDecodeError as exc:
        logger.warning("Skipping unparsable ADLS json file %s: %s", name, exc)
        return
    yield from_adls(record, Path(name).stem)


def _block_to_content(row: pd.Series) -> dict[str, Any]:
    """Convert one flattened block row back into an Anthropic-style content block."""
    if row["type"] == "text":
        return {"type": "text", "text": row["text"]}
    if row["type"] == "thinking":
        return {"type": "thinking", "thinking": row["thinking"]}
    if row["type"] == "tool_use":
        try:
            tool_input = json.loads(row["tool_input"]) if row["tool_input"] else None
        except (json.JSONDecodeError, TypeError):
            tool_input = row["tool_input"]
        return {
            "type": "tool_use",
            "id": row["tool_use_id"],
            "name": row["tool_name"],
            "input": tool_input,
        }
    # Fallback for any other block type (e.g. tool_result), row["text"] holds
    # the JSON-serialised block from reader.py's fallback path.
    if row["text"] is not None:
        try:
            block: dict[str, Any] = json.loads(row["text"])
        except (json.JSONDecodeError, TypeError):
            pass
        else:
            return block
    return {"type": row["type"]}


def _blocks_to_message(block_rows: pd.DataFrame) -> dict[str, Any]:
    """Merge a group of same-message block rows into one {role, content} message."""
    role = block_rows["role"].iloc[0]
    content = [_block_to_content(row) for _, row in block_rows.iterrows()]
    return {"role": role, "content": content}


def _reconstruct_conversation(last_request_rows: pd.DataFrame) -> list[dict[str, Any]]:
    """Reconstruct one session's ordered message list from its last request.

    The last (most complete) request already resent the full input history,
    so its input blocks in msg_idx order are the conversation so far; its
    output blocks are the final assistant turn.
    """
    messages: list[dict[str, Any]] = []
    input_rows = last_request_rows[last_request_rows["direction"] == "input"].sort_values(["msg_idx", "block_idx"])
    for _, block_rows in input_rows.groupby("msg_idx", sort=True):
        messages.append(_blocks_to_message(block_rows))

    output_rows = last_request_rows[last_request_rows["direction"] == "output"].sort_values("block_idx")
    if not output_rows.empty:
        messages.append(_blocks_to_message(output_rows))

    return messages


def _sessions_to_flat_rows(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Explode session records into one flat row per message content block.

    One row = one block, same value columns as the block-level rows
    :func:`~.reader._rows_from_record` produces, but built from the
    reconstructed session messages rather than raw request rows, with
    session-level fields (spend, tokens, time span, ...) repeated onto every
    row. Meant as an alternative, non-nested output format for tools that work
    better with flat tables (e.g. loading into a DataFrame or parquet) than
    with nested JSON.
    """
    rows: list[dict[str, Any]] = []
    for session in sessions:
        session_meta = {k: v for k, v in session.items() if k != "messages"}
        if isinstance(session_meta.get("models"), list):
            session_meta["models"] = ", ".join(session_meta["models"])

        for msg_idx, message in enumerate(session["messages"]):
            for block_idx, block in enumerate(message["content"]):
                rows.append(
                    {
                        **session_meta,
                        "msg_idx": msg_idx,
                        "role": message["role"],
                        "block_idx": block_idx,
                        "type": block.get("type"),
                        **_block_columns(block),
                    }
                )
    return rows


# Explicit schema prevents PyArrow from inferring `null` type for columns whose
# first batch happens to contain only None values (e.g. thinking, tool_name).
_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("request_id", pa.string()),
        pa.field("session_id", pa.string()),
        pa.field("direction", pa.string()),
        pa.field("msg_idx", pa.int64()),
        pa.field("block_idx", pa.int64()),
        pa.field("role", pa.string()),
        pa.field("type", pa.string()),
        pa.field("text", pa.string()),
        pa.field("thinking", pa.string()),
        pa.field("tool_name", pa.string()),
        pa.field("tool_input", pa.string()),
        pa.field("tool_use_id", pa.string()),
    ]
)

_PARQUET_COLS = tuple(_PARQUET_SCHEMA.names)

_PARQUET_BATCH_SIZE = 10_000

# Bumped whenever a change alters what pass 1 records in the sidecar. The cache
# fingerprint carries it, so a stale cache is rejected rather than reused.
# 2: dropped the native-session_id fallback, so caches built under 1 hold
# fabricated singleton sessions; added SkipStats in place of a bare count.
_GROUPING_SCHEMA = 2


@dataclass
class SkipStats:
    """Records pass 1 dropped because ``end_user`` carried no session_id.

    Session totals are computed over the records that survived, so they do not
    reconcile with request-level totals taken from the same input. The
    difference is exactly ``spend``/``total_tokens`` here, which is why the
    dropped volume is accumulated rather than only counted.

    ``n_with_native_session_id`` is the subset LiteLLM stamped with a
    per-request trace id. Grouping once used that id as a fallback key, which
    turned each of these into a singleton "session"; the field now measures how
    much that fallback was inflating the output.

    ``n_with_account_uuid`` is the subset whose ``end_user`` parsed far enough
    to name an account but not a session — ungroupable, yet still attributable.
    """

    n_records: int = 0
    spend: float = 0.0
    total_tokens: int = 0
    n_with_native_session_id: int = 0
    n_with_account_uuid: int = 0

    def record(self, record: dict[str, Any], end_user: dict[str, str]) -> None:
        """Count one dropped record and the volume it takes with it."""
        self.n_records += 1
        self.spend += record.get("spend") or 0.0
        self.total_tokens += record.get("total_tokens") or 0
        if record.get("session_id"):
            self.n_with_native_session_id += 1
        if end_user["account_uuid"]:
            self.n_with_account_uuid += 1


@dataclass(frozen=True)
class ScanResult:
    """What pass 1 learned: everything about a session except its messages."""

    session_stats: dict[str, dict[str, Any]]
    skipped: SkipStats

    @property
    def last_request_ids(self) -> set[str]:
        """The request_id chosen as each session's full transcript."""
        return {s["_best_request_id"] for s in self.session_stats.values()}


def _scan_and_write_blocks(
    input_path: Path,
    parquet_path: Path,
    *,
    include_thinking: bool,
    verbose: bool,
) -> ScanResult:
    """Stream all records from input_path into a compact Parquet file.

    Accumulates per-session stats in memory (O(n_sessions)) without building a
    full block-level DataFrame.  Writes only the 12 columns needed for session
    reconstruction to the Parquet — all other columns go into the returned
    session_stats dict.

    Stats are accumulated from the raw record *before* it is flattened, so a
    record that yields no content blocks (an empty message list, or a
    Responses-API reply the reader cannot parse) still counts toward its
    session's n_requests, spend and tokens.
    """
    session_stats: dict[str, dict[str, Any]] = {}
    skipped = SkipStats()
    n_no_content = 0

    writer = pq.ParquetWriter(parquet_path, _PARQUET_SCHEMA, compression="snappy")
    batch: list[dict[str, Any]] = []

    def _flush() -> None:
        nonlocal batch
        if not batch:
            return
        writer.write_table(pa.Table.from_pylist(batch, schema=_PARQUET_SCHEMA))
        batch = []

    # Suppress per-record reader warnings during streaming; count and report in
    # aggregate.  -v/--verbose keeps them, for working out why a particular
    # request produced nothing.  Use __module__ rather than a hard-coded name so
    # it works regardless of how the package was imported.
    _reader_logger = logging.getLogger(_rows_from_record.__module__)
    _saved_level = _reader_logger.level
    if not verbose:
        _reader_logger.setLevel(logging.ERROR)
    try:
        for record in tqdm(_iter_raw_records(input_path), unit="rec", desc="Pass 1: scanning"):
            eu = _parse_end_user(record.get("end_user"))
            session_id = eu["session_id"]

            if not session_id:
                skipped.record(record, eu)
                continue

            request_id = record.get("request_id") or ""
            start_time = record.get("startTime") or ""
            end_time = record.get("endTime") or ""
            spend = record.get("spend") or 0.0
            total_tokens = record.get("total_tokens") or 0
            model = record.get("model")
            metadata = record.get("metadata") or {}
            alias = metadata.get("user_api_key_alias")
            n_messages = len((record.get("proxy_server_request") or {}).get("messages") or [])

            # Seed a neutral record, then run the same accumulation for every
            # record including the first.  The seed is neutral for the summed
            # and min/max fields, but takes this record's values for the
            # first-wins identity fields and for `_best_*` — a neutral
            # `_best_n_messages` would have to be -1, since a first request
            # with zero messages cannot beat 0 and would leave the session
            # with no chosen request at all.
            s = session_stats.get(session_id)
            if s is None:
                s = {
                    "device_id": eu["device_id"],
                    "account_uuid": eu["account_uuid"],
                    "user_api_key_alias": alias,
                    "n_requests": 0,
                    "total_spend": 0.0,
                    "total_tokens": 0,
                    "start_time": start_time,
                    "end_time": end_time,
                    "models": set(),
                    "_best_request_id": request_id,
                    "_best_n_messages": n_messages,
                    "_best_start_time": start_time,
                }
                session_stats[session_id] = s

            s["n_requests"] += 1
            s["total_spend"] += spend
            s["total_tokens"] += total_tokens
            if start_time and (not s["start_time"] or start_time < s["start_time"]):
                s["start_time"] = start_time
            if end_time and end_time > s["end_time"]:
                s["end_time"] = end_time
            if model:
                s["models"].add(model)
            if n_messages > s["_best_n_messages"] or (
                n_messages == s["_best_n_messages"] and start_time > s["_best_start_time"]
            ):
                s["_best_request_id"] = request_id
                s["_best_n_messages"] = n_messages
                s["_best_start_time"] = start_time

            block_rows = _rows_from_record(record, include_thinking=include_thinking, include_tool_use=True)
            if not block_rows:
                n_no_content += 1
            for row in block_rows:
                batch.append({col: row.get(col) for col in _PARQUET_COLS})
                if len(batch) >= _PARQUET_BATCH_SIZE:
                    _flush()

    finally:
        _reader_logger.setLevel(_saved_level)

    _flush()
    writer.close()

    if n_no_content:
        logger.info(
            "%d records yielded no content blocks (empty messages or Responses-API format)",
            n_no_content,
        )

    return ScanResult(session_stats=session_stats, skipped=skipped)


def _build_sessions_from_parquet(
    parquet_path: Path,
    session_stats: dict[str, dict[str, Any]],
    last_request_ids: set[str],
) -> list[dict[str, Any]]:
    """Read the block Parquet, reconstruct one session record per session_id.

    The request_id filter is pushed down into PyArrow rather than applied to a
    fully-loaded frame, so only the chosen requests' rows are materialised.
    Row-group *pruning* does not help here (request ids are UUIDs, so per-group
    min/max statistics span everything), but the predicate is still evaluated a
    row group at a time, which keeps peak memory at roughly the output size
    instead of every block row of every resent request.
    """
    df = pd.read_parquet(
        parquet_path,
        filters=[("request_id", "in", list(last_request_ids))],
    )

    sessions: list[dict[str, Any]] = []
    grouped = df.groupby("session_id")
    for session_id, s in tqdm(
        session_stats.items(),
        total=len(session_stats),
        unit="session",
        desc="Pass 2: building sessions",
    ):
        group = grouped.get_group(session_id) if session_id in grouped.groups else df.iloc[:0]
        sessions.append(
            {
                "session_id": session_id,
                "device_id": s["device_id"],
                "account_uuid": s["account_uuid"],
                "user_api_key_alias": s["user_api_key_alias"],
                "models": sorted(m for m in s["models"] if m),
                "n_requests": s["n_requests"],
                "total_spend": float(s["total_spend"]) if s["total_spend"] else None,
                "total_tokens": int(s["total_tokens"]) if s["total_tokens"] else None,
                "start_time": s["start_time"],
                "end_time": s["end_time"],
                "messages": _reconstruct_conversation(group),
            }
        )

    sessions.sort(key=lambda s: s["start_time"] or "")
    return sessions


def _cache_fingerprint(input_path: Path, *, include_thinking: bool) -> dict[str, Any]:
    """Identify the input a cached Parquet was built from.

    Nothing else ties a cache to its input, and because the tool refuses to
    overwrite its output, the natural way to re-run is to delete the output and
    reuse the same paths — which would otherwise silently reuse a stale cache.

    ``include_thinking`` is part of the fingerprint because it changes the
    Parquet's *contents*, not just the run: reusing a no-thinking cache for a
    thinking run would quietly produce a transcript missing its thinking blocks.
    """
    if input_path.is_dir():
        files = [p for p in input_path.rglob("*") if p.suffix in (".jsonl", ".json") and p.is_file()]
        size = len(files)
        mtime_ns = max((p.stat().st_mtime_ns for p in files), default=0)
    else:
        stat = input_path.stat()
        size = stat.st_size
        mtime_ns = stat.st_mtime_ns
    return {
        "path": str(input_path.resolve()),
        "size": size,
        "mtime_ns": mtime_ns,
        "include_thinking": include_thinking,
        "grouping_schema": _GROUPING_SCHEMA,
    }


def stream_sessions(
    input_path: Path,
    *,
    parquet_path: Path,
    include_thinking: bool = True,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], SkipStats]:
    """Group every raw record under input_path into per-session conversations.

    Two passes. Pass 1 scans the records once, accumulating per-session stats in
    memory (O(n_sessions)) and spilling block rows to ``parquet_path``. Pass 2
    reads back only the rows of each session's chosen request and rebuilds its
    conversation. Memory never holds a block-level frame of the whole input,
    which matters because every request resends the conversation so far.

    ``input_path`` may be a ``.jsonl``, a ``.json``, a directory of either, or a
    ``.zip`` — the container is handled by :func:`_iter_raw_records` and does
    not change the result.

    If ``parquet_path`` already exists it is reused, provided its sidecar says
    it was built from this same input with the same ``include_thinking``.

    Returns
    -------
    (sessions, skipped)
        ``skipped`` describes the records whose ``end_user`` carried no
        session_id, so they could not be grouped — see :class:`SkipStats`.
    """
    if input_path.is_dir() and parquet_path.resolve().is_relative_to(input_path.resolve()):
        msg = "Place the Parquet cache outside the input directory so its sidecar is not read as input"
        raise SystemExit(msg)
    stats_path = parquet_path.with_suffix(parquet_path.suffix + ".stats.json")
    fingerprint = _cache_fingerprint(input_path, include_thinking=include_thinking)

    if parquet_path.exists():
        if not stats_path.exists():
            msg = f"Parquet cache found at {parquet_path} but sidecar {stats_path} is missing"
            raise SystemExit(msg)
        with stats_path.open() as f:
            raw_stats = json.load(f)
        cached = raw_stats.get("fingerprint")
        if cached != fingerprint:
            differing = sorted(k for k in fingerprint if not cached or cached.get(k) != fingerprint[k])
            msg = (
                f"Parquet cache at {parquet_path} does not match this input "
                f"(differs on: {', '.join(differing)}). Delete it to rebuild."
            )
            raise SystemExit(msg)
        logger.info("Reusing cached Parquet at %s", parquet_path)
        scan = ScanResult(
            session_stats={sid: {**s, "models": set(s["models"])} for sid, s in raw_stats["sessions"].items()},
            skipped=SkipStats(**raw_stats["skipped"]),
        )
    else:
        scan = _scan_and_write_blocks(
            input_path,
            parquet_path,
            include_thinking=include_thinking,
            verbose=verbose,
        )
        with stats_path.open("w") as f:
            json.dump(
                {
                    "fingerprint": fingerprint,
                    "skipped": asdict(scan.skipped),
                    "sessions": {sid: {**s, "models": sorted(s["models"])} for sid, s in scan.session_stats.items()},
                },
                f,
            )
        logger.info("Saved Parquet at %s", parquet_path)

    logger.info("Scanning complete: %d sessions found", len(scan.session_stats))
    if not scan.session_stats:
        msg = (
            "No sessions found — all records had an unparsable or missing "
            f"end_user field. ({scan.skipped.n_records} records skipped)"
        )
        raise SystemExit(msg)

    sessions = _build_sessions_from_parquet(parquet_path, scan.session_stats, scan.last_request_ids)
    return sessions, scan.skipped


def _log_skipped(skipped: SkipStats) -> None:
    """Report the dropped records, so the gap is visible rather than inferred."""
    if not skipped.n_records:
        return
    logger.warning(
        "Skipped %d records with no end_user session_id (not grouped): "
        "$%.2f spend and %d tokens are therefore absent from session totals",
        skipped.n_records,
        skipped.spend,
        skipped.total_tokens,
    )
    logger.info(
        "  of those, %d carried a per-request LiteLLM session_id (never a "
        "session key) and %d parsed to an account but no session",
        skipped.n_with_native_session_id,
        skipped.n_with_account_uuid,
    )


def main() -> None:
    """CLI entry point: parse args, load the input, build sessions, write the output."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "input",
        type=Path,
        help=("Raw data: a .jsonl file, a .json file, a directory of either (searched recursively), or a .zip of them"),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: sessions.jsonl or sessions.parquet, depending on --format)",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "parquet"],
        default="jsonl",
        help="Output format: jsonl (one nested session per line) or parquet (flat, one row per message block)",
    )
    parser.add_argument(
        "--parquet-cache",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Keep the intermediate block Parquet at PATH instead of in a "
            "temporary directory.  If the file already exists and was built "
            "from this same input, pass 1 is skipped and it is reused."
        ),
    )
    parser.add_argument(
        "--no-thinking",
        action="store_false",
        dest="include_thinking",
        help="Drop thinking blocks from the reconstructed conversations",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Keep the reader's per-record warnings instead of only an aggregate count",
    )
    args = parser.parse_args()
    output = args.output or Path(f"sessions.{args.format}")
    if output.exists():
        msg = f"{output} already exists, pass a different -o/--output to avoid overwriting it"
        raise SystemExit(msg)

    with tempfile.TemporaryDirectory() as tmp:
        sessions, skipped = stream_sessions(
            args.input,
            parquet_path=args.parquet_cache or Path(tmp) / "blocks.parquet",
            include_thinking=args.include_thinking,
            verbose=args.verbose,
        )

    if args.format == "jsonl":
        with jsonlines.open(output, mode="w") as writer:
            for record in sessions:
                writer.write(record)
    else:
        pd.DataFrame(_sessions_to_flat_rows(sessions)).to_parquet(output, index=False)

    logger.info("Wrote %d sessions to %s", len(sessions), output)
    _log_skipped(skipped)


if __name__ == "__main__":
    main()
