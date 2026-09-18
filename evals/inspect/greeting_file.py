"""Inspect eval for whether a model follows the `greeting-file` skill in context.

This is the model-level half of skill evaluation. Harbor covers the agent-level
half (does an agent harness actually *use* the skill inside a sandbox). Here we
just inject SKILL.md as the system prompt and check the model's reply.

Run against the mock provider (no API key, deterministic):

    pixi run -e evals inspect-smoke

Run against a real model:

    pixi run -e evals inspect eval evals/inspect/greeting_file.py \
        --model anthropic/claude-haiku-4-5
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import exact
from inspect_ai.solver import generate, system_message

# Skills under test live in one place and are shared with the harbor task.
SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

EXPECTED = "Hello from the greeting-file skill"


def load_skill(name: str) -> str:
    """Return the body of a SKILL.md with its YAML frontmatter stripped."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text()
    if text.startswith("---"):
        # frontmatter is delimited by the first two '---' lines
        _, _, body = text.split("---", 2)
        return body.strip()
    return text.strip()


@task
def greeting_file(smoke: bool = False) -> Task:
    """Skill-following check for `greeting-file`.

    Args:
        smoke: when true, pin the task to the mock model with a canned correct
            answer so the pipeline can be exercised without any API key.
            Pass via `-T smoke=true`.
    """
    dataset = [
        Sample(
            input="Please give me the greeting file content.",
            target=EXPECTED,
        ),
        Sample(
            input="I need a greeting file. What should it contain?",
            target=EXPECTED,
        ),
    ]

    model = None
    if smoke:
        # mockllm replays these outputs in order; they must be ModelOutput objects.
        canned = [
            ModelOutput.from_content(model="mockllm/model", content=EXPECTED)
            for _ in dataset
        ]
        model = get_model("mockllm/model", custom_outputs=canned)

    return Task(
        dataset=dataset,
        solver=[system_message(load_skill("greeting-file")), generate()],
        # exact() strips whitespace and punctuation before comparing, which is
        # what we want for a one-line canonical answer.
        scorer=exact(),
        model=model,
    )
