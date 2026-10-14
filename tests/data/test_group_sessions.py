"""Unit and integration tests for llmoxie_analysis.data.group_sessions."""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from llmoxie_analysis.data.group_sessions import (
    _iter_raw_records,
    _sessions_to_flat_rows,
    main,
    stream_sessions,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── Record builders ──────────────────────────────────────────────
# The streaming path reads raw records, so tests build records rather than
# DataFrames. These helpers keep each test to the one field it is about.


def _text(role: str, text: str) -> dict[str, Any]:
    return {"role": role, "content": [{"type": "text", "text": text}]}


def _record(
    request_id: str,
    session_id: str | None,
    *,
    messages: list[dict[str, Any]] | None = None,
    reply: list[dict[str, Any]] | None = None,
    start: str = "2026-03-01T00:00:00.000000Z",
    spend: float = 0.01,
    total_tokens: int = 100,
) -> dict[str, Any]:
    """One spend-log record. ``session_id=None`` omits end_user entirely."""
    record: dict[str, Any] = {
        "request_id": request_id,
        "startTime": start,
        "endTime": start,
        "model": "claude-sonnet-4.6",
        "spend": spend,
        "total_tokens": total_tokens,
        "metadata": {"user_api_key_alias": "alias"},
        "proxy_server_request": {"messages": messages or []},
        "response": (
            {"choices": [{"message": {"role": "assistant", "content": reply}}]}
            if reply is not None
            else {}
        ),
    }
    if session_id is not None:
        record["end_user"] = json.dumps(
            {"device_id": "d1", "account_uuid": "a1", "session_id": session_id}
        )
    return record


def _conversation(session_id: str, n_turns: int) -> list[dict[str, Any]]:
    """``n_turns`` records for one session, each resending the history so far.

    Reproduces the shape the whole module exists to undo: request *i* carries
    every message through turn *i*, so only the last one is a full transcript.
    """
    records = []
    history: list[dict[str, Any]] = []
    for i in range(n_turns):
        history = [*history, _text("user", f"q{i}")]
        records.append(
            _record(
                f"{session_id}-r{i}",
                session_id,
                messages=list(history),
                reply=[{"type": "text", "text": f"a{i}"}],
                start=f"2026-03-01T00:0{i}:00.000000Z",
            )
        )
        history = [*history, _text("assistant", f"a{i}")]
    return records


def _to_adls(record: dict[str, Any]) -> dict[str, Any]:
    """Re-shape a spend-log record into the ADLS blob shape sources.from_adls reads."""

    def _epoch(iso: str) -> float:
        return (
            datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%fZ")
            .replace(tzinfo=UTC)
            .timestamp()
        )

    return {
        "kwargs": {
            "standard_logging_object": {
                "id": record["request_id"],
                "startTime": _epoch(record["startTime"]),
                "endTime": _epoch(record["endTime"]),
                "end_user": record.get("end_user"),
                "model": record["model"],
                "response_cost": record["spend"],
                "total_tokens": record["total_tokens"],
                "metadata": {"user_api_key_alias": "alias"},
                "messages": record["proxy_server_request"]["messages"],
                "response": record["response"],
            }
        }
    }


# ── Input writers ────────────────────────────────────────────────


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return path


def _write_json_dir(path: Path, records: list[dict[str, Any]]) -> Path:
    """Write records as the ADLS logs/<yyyy>/<mm>/<dd>/<request_id>.json layout."""
    day = path / "logs" / "2026" / "03" / "01"
    day.mkdir(parents=True)
    for record in records:
        (day / f"{record['request_id']}.json").write_text(json.dumps(_to_adls(record)))
    return path


def _write_zip(path: Path, records: list[dict[str, Any]]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "litellm_spend_logs_2026-03-01.jsonl",
            "".join(json.dumps(r) + "\n" for r in records),
        )
    return path


def _sessions_by_id(
    input_path: Path, tmp_path: Path, **kwargs: Any
) -> dict[str, dict[str, Any]]:
    """Run the streaming pipeline and key the result by session_id."""
    parquet = tmp_path / f"{input_path.name}.blocks.parquet"
    sessions, _ = stream_sessions(input_path, parquet_path=parquet, **kwargs)
    return {s["session_id"]: s for s in sessions}


def _transcript(session: dict[str, Any]) -> list[tuple[str, str]]:
    """Flatten a session's messages to (role, type) pairs for terse comparison."""
    return [
        (m["role"], block.get("type", ""))
        for m in session["messages"]
        for block in m["content"]
    ]


class TestIterRawRecords:
    def test_single_jsonl_file(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        p.write_text(json.dumps({"request_id": "r1"}) + "\n")
        records = list(_iter_raw_records(p))
        assert [r["request_id"] for r in records] == ["r1"]

    def test_empty_jsonl_file_yields_nothing(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert list(_iter_raw_records(p)) == []

    def test_empty_json_file_warns_and_skips_instead_of_crashing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Unlike an empty .jsonl file, json.load() raises on an empty file,
        # so this needs to be handled explicitly rather than left to "naturally
        # yield nothing".
        p = tmp_path / "empty.json"
        p.write_text("")
        with caplog.at_level(logging.WARNING):
            records = list(_iter_raw_records(p))
        assert records == []
        assert "Skipping unparsable" in caplog.text

    def test_single_adls_json_file_uses_filename_as_request_id(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "req-abc.json"
        p.write_text(json.dumps({"kwargs": {"standard_logging_object": {}}}))
        records = list(_iter_raw_records(p))
        assert len(records) == 1
        assert records[0]["request_id"] == "req-abc"

    def test_directory_recurses_nested_date_folders(self, tmp_path: Path) -> None:
        nested = tmp_path / "logs" / "2026" / "03" / "28"
        nested.mkdir(parents=True)
        (nested / "req-1.json").write_text(json.dumps({"kwargs": {}}))
        (tmp_path / "top.jsonl").write_text(json.dumps({"request_id": "r-top"}) + "\n")

        records = list(_iter_raw_records(tmp_path))
        request_ids = {r["request_id"] for r in records}
        assert "req-1" in request_ids
        assert "r-top" in request_ids

    def test_zip_reads_in_memory_without_leftover_files(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "data.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "litellm_spend_logs_2026-01-01.jsonl",
                json.dumps({"request_id": "r1"}) + "\n",
            )
            zf.writestr("logs/2026/01/01/req-2.json", json.dumps({"kwargs": {}}))

        before = set(tmp_path.iterdir())
        records = list(_iter_raw_records(zip_path))
        after = set(tmp_path.iterdir())

        assert {r["request_id"] for r in records} == {"r1", "req-2"}
        assert before == after  # nothing extracted to disk


class TestSessionsToFlatRows:
    def test_explodes_messages_to_one_row_per_block(self) -> None:
        sessions = [
            {
                "session_id": "s1",
                "n_requests": 2,
                "total_spend": 0.1,
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "hi"}]},
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "sure"},
                            {
                                "type": "tool_use",
                                "id": "t1",
                                "name": "Bash",
                                "input": {"command": "ls"},
                            },
                        ],
                    },
                ],
            }
        ]
        rows = _sessions_to_flat_rows(sessions)
        assert len(rows) == 3
        assert rows[0]["msg_idx"] == 0
        assert rows[0]["role"] == "user"
        assert rows[0]["text"] == "hi"
        assert rows[2]["type"] == "tool_use"
        assert rows[2]["tool_name"] == "Bash"
        assert json.loads(rows[2]["tool_input"]) == {"command": "ls"}
        # session-level fields repeated onto every row
        assert all(r["session_id"] == "s1" and r["n_requests"] == 2 for r in rows)


class TestStreamSessionsIntegration:
    """Uses tests/data/fixtures/sessions.jsonl, two synthetic sessions built by
    fixtures/generate.py to reproduce the shapes that matter: resent history,
    both end_user formats, and tool_use/tool_result pairing.

    These assertions predate the consolidation onto the streaming path, so they
    are the guard that it preserved behavior."""

    @pytest.fixture
    def sessions(self, tmp_path: Path) -> dict[str, dict[str, Any]]:
        parquet = tmp_path / "blocks.parquet"
        sessions, n_skipped = stream_sessions(
            FIXTURES / "sessions.jsonl", parquet_path=parquet
        )
        assert n_skipped == 0  # every record in this fixture has a session_id
        return {s["session_id"]: s for s in sessions}

    def test_two_sessions_found(self, sessions: dict[str, dict[str, Any]]) -> None:
        assert set(sessions) == {
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        }

    def test_text_session_reconstructed_in_order(
        self, sessions: dict[str, dict[str, Any]]
    ) -> None:
        # Five requests, each resending the history, rebuild as ten messages:
        # the five user turns interleaved with the five replies.
        s = sessions["11111111-1111-1111-1111-111111111111"]
        assert s["n_requests"] == 5
        roles = [m["role"] for m in s["messages"]]
        assert roles == ["user", "assistant"] * 5
        # conversation starts with the user's actual request, not a stray reply
        assert s["messages"][0]["content"][0]["type"] == "text"
        # ends with the assistant's final reply
        assert s["messages"][-1]["role"] == "assistant"

    def test_tool_session_tool_use_tool_result_pairing(
        self, sessions: dict[str, dict[str, Any]]
    ) -> None:
        s = sessions["22222222-2222-2222-2222-222222222222"]
        assert s["n_requests"] == 6
        assert len(s["messages"]) == 12
        # every tool_use in an assistant message is answered by a tool_result
        # in the very next (user) message
        pairs_checked = 0
        for i, m in enumerate(s["messages"][:-1]):
            tool_use_ids = [
                c["id"] for c in m["content"] if c.get("type") == "tool_use"
            ]
            if not tool_use_ids:
                continue
            next_msg = s["messages"][i + 1]
            result_ids = [c.get("tool_use_id") for c in next_msg["content"]]
            assert set(tool_use_ids) <= set(result_ids)
            pairs_checked += 1
        assert pairs_checked == 5

    def test_session_stats_are_positive(
        self, sessions: dict[str, dict[str, Any]]
    ) -> None:
        for s in sessions.values():
            assert s["total_spend"] > 0
            assert s["total_tokens"] > 0
            assert s["start_time"] < s["end_time"]


class TestMainRefusesToOverwriteOutput:
    def test_exits_if_output_already_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        existing_output = tmp_path / "sessions.jsonl"
        existing_output.write_text("not touching this\n")

        monkeypatch.setattr(
            "sys.argv",
            [
                "group_sessions.py",
                str(FIXTURES / "sessions.jsonl"),
                "-o",
                str(existing_output),
            ],
        )

        with pytest.raises(SystemExit, match="already exists"):
            main()

        # the pre-existing file must be untouched
        assert existing_output.read_text() == "not touching this\n"


class TestInputTypeParity:
    """The reason the two code paths were consolidated: which container the
    records arrive in must not change the result."""

    def test_jsonl_zip_and_directory_agree(self, tmp_path: Path) -> None:
        records = _conversation("s1", 3)
        as_jsonl = _write_jsonl(tmp_path / "logs.jsonl", records)
        as_zip = _write_zip(tmp_path / "logs.zip", records)
        as_dir = tmp_path / "dir"
        as_dir.mkdir()
        _write_jsonl(as_dir / "logs.jsonl", records)

        results = [
            _sessions_by_id(path, tmp_path) for path in (as_jsonl, as_zip, as_dir)
        ]
        assert results[0] == results[1] == results[2]

    def test_adls_json_directory_rebuilds_the_same_conversation(
        self, tmp_path: Path
    ) -> None:
        records = _conversation("s1", 3)
        from_jsonl = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", records), tmp_path
        )
        from_adls = _sessions_by_id(
            _write_json_dir(tmp_path / "adls", records), tmp_path
        )

        assert set(from_adls) == {"s1"}
        assert from_adls["s1"]["messages"] == from_jsonl["s1"]["messages"]
        assert from_adls["s1"]["n_requests"] == 3


class TestThinkingBlocks:
    @pytest.fixture
    def records(self) -> list[dict[str, Any]]:
        return [
            _record(
                "r1",
                "s1",
                messages=[_text("user", "q")],
                reply=[
                    {"type": "thinking", "thinking": "hmm"},
                    {"type": "text", "text": "a"},
                ],
            )
        ]

    def test_included_by_default(
        self, tmp_path: Path, records: list[dict[str, Any]]
    ) -> None:
        sessions = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", records), tmp_path
        )
        assert _transcript(sessions["s1"]) == [
            ("user", "text"),
            ("assistant", "thinking"),
            ("assistant", "text"),
        ]

    def test_dropped_when_disabled(
        self, tmp_path: Path, records: list[dict[str, Any]]
    ) -> None:
        sessions = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", records),
            tmp_path,
            include_thinking=False,
        )
        assert _transcript(sessions["s1"]) == [("user", "text"), ("assistant", "text")]


class TestSkippedAndEmptyRecords:
    def test_record_without_any_session_id_is_skipped(self, tmp_path: Path) -> None:
        # end_user missing entirely, so the parse yields "" and the native
        # session_id fallback yields None — neither is a usable session key.
        records = [
            *_conversation("s1", 1),
            _record("orphan", None, messages=[_text("user", "q")]),
        ]
        parquet = tmp_path / "blocks.parquet"
        sessions, n_skipped = stream_sessions(
            _write_jsonl(tmp_path / "logs.jsonl", records), parquet_path=parquet
        )

        assert n_skipped == 1
        assert [s["session_id"] for s in sessions] == ["s1"]

    def test_record_with_no_content_blocks_still_counts_toward_stats(
        self, tmp_path: Path
    ) -> None:
        # An empty or Responses-API-shaped record yields no block rows, but it
        # was still a billed request and must not vanish from the totals.
        records = [
            *_conversation("s1", 1),
            _record("empty", "s1", spend=0.5, total_tokens=50),
        ]
        sessions = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", records), tmp_path
        )

        assert sessions["s1"]["n_requests"] == 2
        assert sessions["s1"]["total_spend"] == pytest.approx(0.51)
        assert sessions["s1"]["total_tokens"] == 150


class TestLastRequestSelection:
    def test_only_the_longest_request_is_reconstructed(self, tmp_path: Path) -> None:
        # Three requests resending growing history: the transcript must be the
        # last one's, not a concatenation of all three.
        sessions = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", _conversation("s1", 3)), tmp_path
        )

        assert sessions["s1"]["n_requests"] == 3
        assert _transcript(sessions["s1"]) == [
            ("user", "text"),
            ("assistant", "text"),
            ("user", "text"),
            ("assistant", "text"),
            ("user", "text"),
            ("assistant", "text"),
        ]
        texts = [b["text"] for m in sessions["s1"]["messages"] for b in m["content"]]
        assert texts == ["q0", "a0", "q1", "a1", "q2", "a2"]


class TestSessionStatsSeeding:
    """Pass 1 seeds a session's stats on first sight, then accumulates.

    The seed is neutral for the summed fields but takes the first record's
    values for identity and for the chosen-request tie-break, which is what
    these guard.
    """

    def test_session_with_no_messages_still_picks_a_request(
        self, tmp_path: Path
    ) -> None:
        # Every request has an empty input and no timestamp, but a parseable
        # reply — so the session has block rows, yet neither half of the
        # tie-break can ever beat a neutral seed. Seeding `_best_*` from the
        # first record is what keeps the session from being dropped in pass 2
        # for want of a chosen request_id.
        records = [
            _record("r1", "s1", start="", reply=[{"type": "text", "text": "a"}]),
            _record("r2", "s1", start="", reply=[{"type": "text", "text": "b"}]),
        ]
        sessions = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", records), tmp_path
        )

        assert sessions["s1"]["n_requests"] == 2
        assert _transcript(sessions["s1"]) == [("assistant", "text")]

    def test_first_record_wins_for_identity_fields(self, tmp_path: Path) -> None:
        later = _record("r2", "s1", messages=[_text("user", "q")])
        later["end_user"] = json.dumps(
            {"device_id": "d2", "account_uuid": "a2", "session_id": "s1"}
        )
        later["metadata"] = {"user_api_key_alias": "alias2"}
        sessions = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", [_record("r1", "s1"), later]),
            tmp_path,
        )

        assert sessions["s1"]["device_id"] == "d1"
        assert sessions["s1"]["account_uuid"] == "a1"
        assert sessions["s1"]["user_api_key_alias"] == "alias"

    def test_totals_and_span_accumulate_across_records(self, tmp_path: Path) -> None:
        reply = [{"type": "text", "text": "a"}]
        records = [
            _record("r1", "s1", start="2026-03-01T00:00:05.000000Z", reply=reply),
            # Arrives out of order, so start_time is a min and not just the
            # first record's value.
            _record("r2", "s1", start="2026-03-01T00:00:01.000000Z", reply=reply),
        ]
        sessions = _sessions_by_id(
            _write_jsonl(tmp_path / "logs.jsonl", records), tmp_path
        )

        assert sessions["s1"]["total_spend"] == pytest.approx(0.02)
        assert sessions["s1"]["total_tokens"] == 200
        assert sessions["s1"]["start_time"] == "2026-03-01T00:00:01.000000Z"
        assert sessions["s1"]["end_time"] == "2026-03-01T00:00:05.000000Z"


class TestParquetCache:
    def _argv(self, tmp_path: Path, *extra: str) -> list[str]:
        return [
            "group_sessions.py",
            str(tmp_path / "logs.jsonl"),
            "-o",
            str(tmp_path / "out.jsonl"),
            *extra,
        ]

    def test_no_intermediate_files_left_behind_without_the_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_jsonl(tmp_path / "logs.jsonl", _conversation("s1", 2))
        monkeypatch.setattr("sys.argv", self._argv(tmp_path))
        main()

        leftovers = [
            p.name
            for p in tmp_path.iterdir()
            if p.suffix == ".parquet" or p.name.endswith(".stats.json")
        ]
        assert leftovers == []
        assert (tmp_path / "out.jsonl").exists()

    def test_second_run_reuses_the_cache(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _write_jsonl(tmp_path / "logs.jsonl", _conversation("s1", 2))
        cache = tmp_path / "blocks.parquet"
        monkeypatch.setattr(
            "sys.argv", self._argv(tmp_path, "--parquet-cache", str(cache))
        )
        main()
        assert cache.exists()

        (tmp_path / "out.jsonl").unlink()
        with caplog.at_level(logging.INFO):
            main()
        assert "Reusing cached Parquet" in caplog.text

    def test_cache_is_rejected_when_the_input_changed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_jsonl(tmp_path / "logs.jsonl", _conversation("s1", 2))
        cache = tmp_path / "blocks.parquet"
        monkeypatch.setattr(
            "sys.argv", self._argv(tmp_path, "--parquet-cache", str(cache))
        )
        main()

        (tmp_path / "out.jsonl").unlink()
        _write_jsonl(tmp_path / "logs.jsonl", _conversation("s1", 4))
        with pytest.raises(SystemExit, match="does not match"):
            main()

    def test_cache_is_rejected_when_thinking_setting_changed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The cached Parquet's *contents* depend on include_thinking, so
        # reusing one built the other way would silently produce wrong output.
        _write_jsonl(tmp_path / "logs.jsonl", _conversation("s1", 2))
        cache = tmp_path / "blocks.parquet"
        monkeypatch.setattr(
            "sys.argv", self._argv(tmp_path, "--parquet-cache", str(cache))
        )
        main()

        (tmp_path / "out.jsonl").unlink()
        monkeypatch.setattr(
            "sys.argv",
            self._argv(tmp_path, "--parquet-cache", str(cache), "--no-thinking"),
        )
        with pytest.raises(SystemExit, match="does not match"):
            main()
