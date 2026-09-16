# Repository Map

**Load when:** you need to know what this repository is, where a file lives, or
what CI runs against it.

## Repository Overview

This is a **blank project template** repository for UW SSEC (Scientific Software
Engineering Center) projects. It provides standardized community health files,
pre-commit configurations, and onboarding tools. The repository itself contains
no application code — it serves as a starting point for new projects.

**Repository Stats:**

- **Type:** Template repository / Boilerplate
- **Size:** Small (~20 files)
- **Languages:** Configuration files (TOML, YAML, Markdown)
- **Build System:** Pixi (v0.49.0+)
- **Platform:** macOS (osx-arm64), easily extensible to other platforms
- **License:** BSD 3-Clause

## Project Structure & Key Files

```
.
├── .agents/
│   ├── rules/                   # On-demand rules referenced by AGENTS.md
│   └── skills/                  # User-invocable skills (/commit, /create-pr, ...)
├── .claude/
│   └── skills -> ../.agents/skills  # Symlink so Claude Code discovers the skills
├── .github/
│   ├── dependabot.yml           # Dependabot config for GitHub Actions
│   ├── pull_request_template.md # PR template (requires pre-commit checks)
│   ├── release.yml              # Release notes configuration
│   ├── workflows/               # GitHub Actions (zizmor workflow linting)
│   └── ISSUE_TEMPLATE/          # Issue templates (bug, feature, docs, onboard, etc.)
├── .pre-commit-config.yaml      # Pre-commit hook configuration
├── pixi.toml                    # **PRIMARY CONFIG**: Dependencies, tasks, features
├── pixi.lock                    # Lock file (auto-generated, don't manually edit)
├── .gitignore                   # Ignores .pixi/ and .DS_Store
├── AGENTS.md                    # Entry point for AI assistants
├── CLAUDE.md                    # Points Claude Code at AGENTS.md (@AGENTS.md)
├── CODE_OF_CONDUCT.md           # Contributor Covenant v2.0
├── CONTRIBUTING.md              # Contribution guidelines (references Conventional Commits)
├── LICENSE                      # BSD 3-Clause License
├── README.md                    # Project documentation
└── onboarded.md                 # Empty file (excluded from pre-commit)
```

## Continuous Integration & Validation

**GitHub Actions:** `.github/workflows/zizmor.yml` runs
[zizmor](https://github.com/zizmorcore/zizmor) static analysis to lint workflow
files for security issues. Changes to anything under `.github/workflows/` must
keep this check passing.

**Pre-commit.ci Integration:** The `.pre-commit-config.yaml` includes a `ci:`
section, suggesting integration with https://pre-commit.ci for automated PR
checks. Verify if enabled on the repository.

**Dependabot:** Configured to update GitHub Actions weekly (groups all action
updates together).

## Further Reading

For more information on SSEC best practices, see:
https://rse-guidelines.readthedocs.io/en/latest/llms-full.txt
