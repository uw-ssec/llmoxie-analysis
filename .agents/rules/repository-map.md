# Repository Map

**Load when:** you need to know what this repository is, where a file lives, or
what CI runs against it.

## Repository Overview

**llmoxie-analysis** is the data analysis package for the
[LLMoxie](https://github.com/uw-ssec/llmoxie) project at UW SSEC (Scientific
Software Engineering Center). It turns raw LLMoxie gateway request logs into a
queryable Parquet warehouse of sessions, messages, and tool calls. The package
is still early scaffolding; the pipeline design is recorded in `knowledge/` and
the working prototypes live in the `reference/` submodules.

**Repository Stats:**

- **Type:** Installable Python package (src layout, Hatchling build backend)
- **Languages:** Python (>=3.11), plus configuration (TOML, YAML, Markdown)
- **Build System:** Pixi (pinned to v0.81.0 in CI and the devcontainer)
- **Platforms:** osx-arm64, linux-64, linux-aarch64
- **License:** BSD 3-Clause

## Project Structure & Key Files

```
.
├── .agents/
│   ├── rules/                   # On-demand rules referenced by AGENTS.md
│   └── skills/                  # User-invocable skills (/commit, /create-pr, ...)
├── .claude/
│   └── skills -> ../.agents/skills  # Symlink so Claude Code discovers the skills
├── .devcontainer/               # Dev container / Codespaces image (pins PIXI_VERSION)
├── .github/
│   ├── copilot-instructions.md -> ../AGENTS.md
│   ├── dependabot.yml           # Dependabot config for GitHub Actions
│   ├── pull_request_template.md # PR template (requires pre-commit checks)
│   ├── release.yml              # Release notes configuration
│   ├── workflows/               # GitHub Actions (zizmor workflow linting, Copilot agent setup)
│   └── ISSUE_TEMPLATE/          # Issue templates (bug, feature, docs, onboard, etc.)
├── docs/                        # Documentation site source: hand-written Markdown pages
├── evals/                       # Skill evals: Inspect harness and samples, Harbor base image and task directories; see evals/README.md
├── knowledge/                   # Project memory (OKF bundle); read and write via the okf-memory skill
├── reference/                   # Read-only git submodules: llmoxie, ceil-dlp (upstream prototypes)
├── src/llmoxie_analysis/        # The package; __version__ lives in __init__.py
├── tests/                       # pytest suite
├── .pre-commit-config.yaml      # Pre-commit hook configuration
├── mkdocs.yml                   # Docs site config; every page must be listed under nav:
├── pixi.toml                    # **PRIMARY CONFIG**: Dependencies, tasks, features
├── pixi.lock                    # Lock file (auto-generated, don't manually edit)
├── pyproject.toml               # Package metadata, plus ruff, mypy, and pytest settings
├── .gitignore                   # Ignores .pixi/, build artifacts, tool caches, site/
├── .gitmodules                  # Declares the reference/ submodules
├── AGENTS.md                    # Entry point for AI assistants
├── CLAUDE.md                    # Points Claude Code at AGENTS.md (@AGENTS.md)
├── .cursorrules -> AGENTS.md    # Symlink so Cursor reads the same entry point
├── AI_POLICY.md                 # How AI assistance is disclosed and credited
├── CODE_OF_CONDUCT.md           # Contributor Covenant v2.0
├── CONTRIBUTING.md              # Contribution guidelines (references Conventional Commits)
├── LICENSE                      # BSD 3-Clause License
├── README.md                    # Project documentation
└── onboarded.md                 # Empty file (excluded from pre-commit)
```

The documentation site (`docs/` + `mkdocs.yml`) and project memory
(`knowledge/`) are separate: nothing in `knowledge/` is rendered into the site.
Build the site with `pixi run docs-build` and preview it with
`pixi run docs-serve`. Build output goes to `site/`, which is gitignored.

## Continuous Integration & Validation

**GitHub Actions:** `.github/workflows/zizmor.yml` runs
[zizmor](https://github.com/zizmorcore/zizmor) static analysis to lint workflow
files for security issues. Changes to anything under `.github/workflows/` must
keep this check passing.

**Skill evals:** `.github/workflows/skill-evals.yml` runs the Inspect and Harbor
skill evals (see `evals/README.md`).

**Copilot cloud agent:** `.github/workflows/copilot-setup-steps.yml` prepares
the GitHub Copilot coding agent's environment (pixi install from `pixi.lock`,
pre-commit hook environments). Copilot reads `AGENTS.md` and `.agents/skills/`
on its own; keep the pinned `pixi-version` in sync with
`.devcontainer/Dockerfile`.

**Pre-commit.ci Integration:** The `.pre-commit-config.yaml` includes a `ci:`
section, suggesting integration with https://pre-commit.ci for automated PR
checks. Verify if enabled on the repository.

**Dependabot:** Configured to update GitHub Actions weekly (groups all action
updates together).

## Further Reading

For more information on SSEC best practices, see:
https://rse-guidelines.readthedocs.io/en/latest/llms-full.txt
