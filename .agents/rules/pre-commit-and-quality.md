# Pre-commit & Quality Standards

**Load when:** you are about to commit, open a PR, or claim that checks pass.

## Pre-commit Checks (MANDATORY BEFORE PRs)

**Always run pre-commit checks before creating a pull request.** The PR template
requires this, and PRs will fail if checks don't pass.

```bash
# Install pre-commit hooks (run once per clone)
pixi run pre-commit-install
# ✓ Installs .git/hooks/pre-commit
# ✓ Hooks will automatically run on every commit

# Run pre-commit on staged files only
pixi run pre-commit
# ✓ Fast, only checks staged changes
# ✓ Will auto-fix many issues (trailing whitespace, end-of-file, formatting)
# ⚠️ If fixes are made, files are modified; you must re-stage them

# Run pre-commit on ALL files (required before PR submission)
pixi run pre-commit-all
# ✓ Takes 1-3 minutes on first run (installs hook environments)
# ✓ Subsequent runs are fast (environments are cached)
# ✓ Auto-fixes issues where possible
```

To check a specific file, pass it through the task:
`pixi run pre-commit --files <path>`.

**The full gate is `pixi run verify`:** it runs `pre-commit-all`, then mypy
(`typecheck`), pytest (`test`), and a wheel/sdist build (`build`), stopping at
the first failure. Pre-commit alone covers formatting and hygiene only.

**Pre-commit Hooks Configured:**

- ruff-check (with `--fix`) and ruff-format (Python lint and formatting)
- check-added-large-files, check-case-conflict, check-merge-conflict
- check-yaml, check-symlinks
- fix-end-of-files, trim-trailing-whitespace, mixed-line-ending
- prettier (formats YAML, Markdown, HTML, CSS, JavaScript, JSON)
- codespell (spell checking)
- Disallow improper capitalization (e.g., incorrect → correct)
- Validate Dependabot config and GitHub workflows

**Files Excluded from Pre-commit:** `pixi.lock`, `onboarded.md`

## Making Changes: Validated Workflow

1. **Setup (first time):**

   ```bash
   pixi install
   pixi run pre-commit-install
   ```

2. **Make your changes** to files — surgically, per
   [working-agreement.md](working-agreement.md).

3. **Test changes:**

   ```bash
   # Stage your changes
   git add <files>

   # Run pre-commit checks
   pixi run pre-commit

   # If checks fail and auto-fix issues, re-add the fixed files
   git add <files>
   ```

4. **Before creating a PR:**

   ```bash
   # Run the full gate: pre-commit on all files, mypy, pytest, build
   pixi run verify

   # Verify every step passes (exit 0; pre-commit shows "Passed" or "Skipped")
   ```

5. **Create PR:** work through the checklist in
   [contribution-discipline.md](contribution-discipline.md) before submitting.
   - PR template requires confirming `pre-commit run --all-files` was run
   - Follow Conventional Commits for PR titles
   - Link related issues using "Resolves #<issue-number>"

## Documentation Standards

- Follow Conventional Commits for commit messages and PR titles
- Use Markdown with proper formatting (enforced by prettier)
- Spell check enabled (codespell)
- No trailing whitespace
- Files must end with newline
- Consistent line endings
