from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".agents" / "skills"
SAMPLES_DIR = ROOT / "evals" / "inspect" / "samples"

SKILL_NAMES: list[str] = sorted(
    p.name for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file()
)


def test_skills_were_found() -> None:
    assert len(SKILL_NAMES) >= 12


def test_every_skill_has_inspect_samples() -> None:
    missing = [
        name for name in SKILL_NAMES if not (SAMPLES_DIR / f"{name}.yaml").is_file()
    ]
    assert missing == []


SHIMS_TEST = ROOT / "evals" / "harbor" / "base" / "shims" / "test_shims.sh"


def test_shims_self_test() -> None:
    result = subprocess.run(
        ["bash", str(SHIMS_TEST)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


HARBOR_TASKS_DIR = ROOT / "evals" / "harbor" / "tasks"
HARBOR_TASK_FILES = (
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/test.sh",
)


def test_every_skill_has_harbor_task() -> None:
    missing = [name for name in SKILL_NAMES if not (HARBOR_TASKS_DIR / name).is_dir()]
    assert missing == []


def test_every_harbor_task_is_complete() -> None:
    incomplete = [
        f"{task.name}/{rel}"
        for task in sorted(HARBOR_TASKS_DIR.iterdir())
        if task.is_dir()
        for rel in HARBOR_TASK_FILES
        if not (task / rel).is_file()
    ]
    assert incomplete == []
