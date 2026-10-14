"""Unit tests for llmoxie_analysis.data.sources."""

from __future__ import annotations

from typing import Any

from llmoxie_analysis.data.reader import load_messages_from_records
from llmoxie_analysis.data.sources import _epoch_to_iso, from_adls, from_litellm


def _adls_record() -> dict[str, Any]:
    """One ADLS blob covering every field the adapter maps."""
    return {
        "kwargs": {
            "standard_logging_object": {
                "id": "req-123",
                "startTime": 1767397278.414,
                "endTime": 1767397280.0,
                "end_user": "user_dev1_account_acc1_session_sess1",
                "model": "gpt-5.3-codex",
                "response_cost": 0.05,
                "total_tokens": 500,
                "metadata": {
                    "user_api_key_alias": "carlos-api",
                    "user_api_key_hash": "hash1",
                },
                "messages": [{"role": "user", "content": "hi"}],
                "response": {
                    "choices": [{"message": {"role": "assistant", "content": "hello"}}]
                },
            }
        }
    }


def _litellm_record() -> dict[str, Any]:
    """The same request as _adls_record, in spend-log (common) shape."""
    return {
        "request_id": "req-123",
        "startTime": "2026-01-02T23:41:18.414000Z",
        "endTime": "2026-01-02T23:41:20.000000Z",
        "end_user": "user_dev1_account_acc1_session_sess1",
        "model": "gpt-5.3-codex",
        "spend": 0.05,
        "total_tokens": 500,
        "api_key": "hash1",
        "metadata": {"user_api_key_alias": "carlos-api"},
        "proxy_server_request": {"messages": [{"role": "user", "content": "hi"}]},
        "response": {
            "choices": [{"message": {"role": "assistant", "content": "hello"}}]
        },
    }


class TestEpochToIso:
    def test_converts_to_matching_format(self) -> None:
        # 2026-01-02T23:41:18.414000Z, matching the litellm_spend_logs JSONL format
        assert _epoch_to_iso(1767397278.414) == "2026-01-02T23:41:18.414000Z"

    def test_none_passthrough(self) -> None:
        assert _epoch_to_iso(None) is None


class TestFromAdls:
    def test_maps_standard_logging_object_fields(self) -> None:
        adapted = from_adls(_adls_record(), fallback_request_id="fallback")

        assert adapted["request_id"] == "req-123"
        assert adapted["startTime"] == "2026-01-02T23:41:18.414000Z"
        assert adapted["end_user"] == "user_dev1_account_acc1_session_sess1"
        assert adapted["model"] == "gpt-5.3-codex"
        assert adapted["spend"] == 0.05
        assert adapted["total_tokens"] == 500
        assert adapted["metadata"]["user_api_key_alias"] == "carlos-api"
        assert adapted["proxy_server_request"]["messages"] == [
            {"role": "user", "content": "hi"}
        ]
        assert adapted["response"]["choices"][0]["message"]["content"] == "hello"

    def test_falls_back_to_filename_request_id_when_missing(self) -> None:
        record: dict[str, Any] = {"kwargs": {"standard_logging_object": {}}}
        adapted = from_adls(record, fallback_request_id="from-filename")
        assert adapted["request_id"] == "from-filename"

    def test_responses_api_shape_does_not_crash(self) -> None:
        # Real shape seen from a GitHub Copilot / gpt-5.3-codex request: reply is
        # under "output", not "choices" -- reader.py should warn, not crash.
        record: dict[str, Any] = {
            "kwargs": {
                "standard_logging_object": {
                    "id": "req-1",
                    "end_user": "",
                    "messages": [{"role": "user", "content": "hi"}],
                    "response": {"output": [{"type": "message"}]},
                }
            }
        }
        adapted = from_adls(record, fallback_request_id="fallback")
        df = load_messages_from_records([adapted])
        assert len(df[df["direction"] == "input"]) == 1
        assert len(df[df["direction"] == "output"]) == 0


class TestFromLitellm:
    def test_is_a_pass_through(self) -> None:
        record = _litellm_record()
        assert from_litellm(record) == record


class TestAdapterParity:
    """Issue #3's acceptance criterion: both adapters must produce identical
    common-format output for the same underlying request, so that data_source
    stays a descriptive tag rather than a branch condition downstream."""

    def test_both_sources_produce_the_same_common_record(self) -> None:
        assert from_adls(_adls_record()) == from_litellm(_litellm_record())

    def test_and_therefore_the_same_flattened_rows(self) -> None:
        from_adls_df = load_messages_from_records([from_adls(_adls_record())])
        from_litellm_df = load_messages_from_records([from_litellm(_litellm_record())])
        assert from_adls_df.equals(from_litellm_df)
