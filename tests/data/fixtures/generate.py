"""Generate the synthetic spend-log fixture the integration tests read.

The upstream prototype tested against two real sessions lifted from the
Jan-Mar 2026 dump. Real gateway logs are prompt bodies and identifiers, and
`datasets/pii-handling` in the knowledge bundle forbids committing them, so
this script fabricates records with the same *shape* instead:

- every request re-sends the whole conversation so far, which is what
  `last_request_per_session` exists to undo
- one session carries the JSON-object `end_user` format, the other the
  `user_..._account_..._session_...` string format, so both parse paths run
- the second session pairs each assistant `tool_use` block with a
  `tool_result` block in the following user message

Regenerate with::

    pixi run python tests/data/fixtures/generate.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

OUT = Path(__file__).parent / "sessions.jsonl"

SESSION_A = "11111111-1111-1111-1111-111111111111"
SESSION_B = "22222222-2222-2222-2222-222222222222"
START = datetime(2026, 3, 19, 18, 23, 2, 530000, tzinfo=UTC)


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _text(role: str, text: str) -> dict[str, Any]:
    return {"role": role, "content": [{"type": "text", "text": text}]}


def _record(
    *,
    request_id: str,
    end_user: str,
    alias: str,
    model: str,
    offset_minutes: int,
    history: list[dict[str, Any]],
    reply: list[dict[str, Any]],
) -> dict[str, Any]:
    """One request: the conversation so far as input, one assistant turn out."""
    start = START + timedelta(minutes=offset_minutes)
    return {
        "request_id": request_id,
        "startTime": _iso(start),
        "endTime": _iso(start + timedelta(seconds=4)),
        "end_user": end_user,
        "model": model,
        "spend": 0.0123,
        "total_tokens": 1320,
        "api_key": "sk-hash-placeholder",
        "metadata": {"user_api_key_alias": alias},
        "proxy_server_request": {"messages": history},
        "response": {"choices": [{"message": {"role": "assistant", "content": reply}}]},
    }


def _session_a() -> list[dict[str, Any]]:
    """Five plain text turns, `end_user` as a JSON object."""
    end_user = json.dumps(
        {"device_id": "a1b2c3d4", "account_uuid": "account-a", "session_id": SESSION_A}
    )
    records = []
    history: list[dict[str, Any]] = []
    for turn in range(5):
        history = [*history, _text("user", f"question {turn}")]
        reply = [{"type": "text", "text": f"answer {turn}"}]
        records.append(
            _record(
                request_id=f"req-a-{turn}",
                end_user=end_user,
                alias="alias-one",
                model="claude-sonnet-4-6-20250929",
                offset_minutes=turn,
                history=history,
                reply=reply,
            )
        )
        history = [*history, {"role": "assistant", "content": reply}]
    return records


def _session_b() -> list[dict[str, Any]]:
    """Six turns alternating tool_use and tool_result, string `end_user`."""
    end_user = f"user_beef1234_account_account-b_session_{SESSION_B}"
    records = []
    history: list[dict[str, Any]] = []
    for turn in range(6):
        if turn == 0:
            history = [*history, _text("user", "start the task")]
        else:
            # answer the previous turn's tool_use
            history = [
                *history,
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": f"tool-{turn - 1}",
                            "content": f"result {turn - 1}",
                        }
                    ],
                },
            ]

        if turn < 5:
            reply: list[dict[str, Any]] = [
                {
                    "type": "tool_use",
                    "id": f"tool-{turn}",
                    "name": "Bash",
                    "input": {"command": f"echo {turn}"},
                }
            ]
        else:
            reply = [{"type": "text", "text": "done"}]

        records.append(
            _record(
                request_id=f"req-b-{turn}",
                end_user=end_user,
                alias="alias-two",
                model="bedrock/anthropic.claude-4-6-sonnet-20250929-v1:0",
                offset_minutes=10 + turn,
                history=history,
                reply=reply,
            )
        )
        history = [*history, {"role": "assistant", "content": reply}]
    return records


def main() -> None:
    """Write both sessions' requests, interleaved, to the fixture file."""
    records = _session_a() + _session_b()
    with OUT.open("w") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
