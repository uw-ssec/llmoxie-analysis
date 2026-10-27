from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from llmoxie_analysis.analysis.session_recovery import (
    assign_keys,
    consecutive_overlap,
    first_user_text,
    partition_metrics,
    request_features,
    sha,
)


def _frame(rows: list[tuple[str, str, int]]) -> pd.DataFrame:
    """Build a minimal feature frame from (fingerprint, request_id, minute) triples."""
    frame = pd.DataFrame(
        [{"first_user_sha": f, "request_id": r, "alias_sha": "a", "call_type": "c", "model": "m"} for f, r, _ in rows]
    )
    frame["start_dt"] = pd.to_datetime([f"2026-01-01T00:{m:02d}:00Z" for _, _, m in rows], utc=True)
    return frame


def test_first_user_text_skips_system_and_flattens_blocks() -> None:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "ignored"},
        {
            "role": "user",
            "content": [{"type": "text", "text": "a"}, {"type": "tool_result"}, {"type": "text", "text": "b"}],
        },
        {"role": "user", "content": "later"},
    ]
    assert first_user_text(messages) == "a\nb"
    assert first_user_text([{"role": "assistant", "content": "x"}]) == ""


def test_request_features_digests_without_retaining_text() -> None:
    record = {
        "request_id": "r1",
        "end_user": '{"device_id": "d", "account_uuid": "u", "session_id": "s"}',
        "proxy_server_request": {"messages": [{"role": "user", "content": "secret prompt"}]},
    }
    features = request_features(record)
    assert features["eu_session_id"] == "s"
    assert features["first_user_sha"] == sha("secret prompt")
    assert "secret prompt" not in str(features)


def test_assign_keys_groups_matching_fingerprints_and_isolates_unkeyable() -> None:
    frame = _frame([("x", "r1", 0), ("x", "r2", 1), ("y", "r3", 2), ("", "r4", 3), ("", "r5", 4)])
    keys = assign_keys(frame)
    assert keys.iloc[0] == keys.iloc[1]
    assert keys.iloc[2] != keys.iloc[0]
    # No fingerprint means no evidence of a link, so each stands alone.
    assert keys.iloc[3] != keys.iloc[4]


def test_assign_keys_splits_on_time_gap() -> None:
    frame = _frame([("x", "r1", 0), ("x", "r2", 5), ("x", "r3", 50)])
    keys = assign_keys(frame, gap_minutes=30.0)
    assert keys.iloc[0] == keys.iloc[1]
    assert keys.iloc[2] != keys.iloc[0]


@pytest.mark.parametrize(
    ("predicted", "precision", "recall", "exact"),
    [
        (["a", "a", "b", "b"], 1.0, 1.0, 1.0),  # perfect
        (["a", "a", "a", "a"], 1 / 3, 1.0, 0.0),  # merged: 2 right pairs out of the 6 the cluster claims
        (["a", "b", "c", "d"], 1.0, 0.0, 0.0),  # split: every request alone
    ],
)
def test_partition_metrics(predicted: list[str], precision: float, recall: float, exact: float) -> None:
    truth = pd.Series(["s1", "s1", "s2", "s2"])
    metrics = partition_metrics(truth, pd.Series(predicted))
    assert metrics["pair_precision"] == pytest.approx(precision)
    assert metrics["pair_recall"] == pytest.approx(recall)
    assert metrics["exact_session_rate"] == pytest.approx(exact)


def test_consecutive_overlap_detects_continuation_and_restart() -> None:
    frame = pd.DataFrame(
        {
            "sid": ["s", "s", "s"],
            "message_shas": [["m1"], ["m1", "m2"], ["z1"]],
            "start_dt": pd.to_datetime(
                ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", "2026-01-01T00:02:00Z"], utc=True
            ),
        }
    )
    overlap = consecutive_overlap(frame, "sid")
    assert list(overlap.is_continuation) == [True, False]
    assert list(overlap.shared_fraction) == [1.0, 0.0]
