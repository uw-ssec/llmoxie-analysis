---
name: run-tests
description:
  Use when running the test suite, a single test, or a failing test — after
  changing anything under src/ or tests/, before claiming code works, or when
  reading pytest output.
---

# Run Tests

Run pytest through pixi and read the result, not the exit code alone.

## Commands

| Goal                  | Command                                                   |
| --------------------- | --------------------------------------------------------- |
| Full suite            | `pixi run test`                                           |
| One file              | `pixi run pytest tests/test_version.py -vv`               |
| One test              | `pixi run pytest tests/test_version.py::test_version -vv` |
| Only last failures    | `pixi run pytest --lf -x`                                 |
| Stop at first failure | `pixi run pytest -x`                                      |

`testpaths = ["tests"]` in `pyproject.toml` keeps collection out of the
`reference/` submodules, which carry their own suites. Do not run pytest from
inside `reference/`.

## Reading the output

- The last line is the verdict: `N passed in Xs`, or `M failed, N passed`.
- `ERROR` during collection is an import or syntax problem in a test module; fix
  it before reading any assertion failures.
- A failing assertion prints the values on both sides. Fix the code or the
  expectation deliberately; never widen a tolerance or delete an assertion to
  make it pass.

## Writing tests

- `tests/` mirrors `src/llmoxie_analysis/`; one `test_<module>.py` per module.
- Data fixtures are files under `tests/fixtures/`, not records generated in the
  test module, so a human can inspect what is asserted against.
- Assert exact expected values a human has checked, not "does not crash".
- Test functions carry return type `-> None`; mypy checks `tests/` in strict
  mode.

## Flaky tests

None recorded. If a test passes and fails without a code change, file an issue
with the `create-issue` skill and say so in the PR. Do not mark it `skip` or
`xfail` silently.

## Done

Exit 0 and the summary line pasted into your report. One failure means not done.
