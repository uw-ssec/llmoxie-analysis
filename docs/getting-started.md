# Getting Started

Set up a development environment for llmoxie-analysis and run the project's
checks.

## Prerequisites

This project uses [Pixi](https://pixi.sh) for dependency management and task
execution. It is the only package manager used here. Install it by following the
[installation instructions](https://pixi.sh/latest/#installation).

## Install

Clone the repository, then create the environment and run the one-time setup:

```bash
git clone https://github.com/uw-ssec/llmoxie-analysis.git
cd llmoxie-analysis
pixi install
pixi run setup
```

`pixi run setup` installs the pre-commit git hooks and initializes the read-only
`reference/` submodules.

Confirm the package imports:

```bash
pixi run python -c "import llmoxie_analysis; print(llmoxie_analysis.__version__)"
```

## Common tasks

| Task                  | Command               |
| --------------------- | --------------------- |
| Run the test suite    | `pixi run test`       |
| Lint and check format | `pixi run lint`       |
| Type-check            | `pixi run typecheck`  |
| Build wheel and sdist | `pixi run build`      |
| Run the quality gate  | `pixi run verify`     |
| Preview these docs    | `pixi run docs-serve` |
| Build these docs      | `pixi run docs-build` |

Run `pixi run verify` before committing or opening a pull request. It must exit
with status 0.

## Preview the docs

```bash
pixi run docs-serve    # live reload at http://127.0.0.1:8000
pixi run docs-build    # build into site/, failing on any warning
```
