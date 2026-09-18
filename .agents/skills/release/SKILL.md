---
name: release
description:
  Use when a new version needs cutting — a semver bump, changelog entry, git
  tag, GitHub release, and built wheel/sdist assets.
---

# Release

Create a versioned release with changelog, citation metadata, tag, GitHub
release, and built wheel/sdist assets.

## Arguments

Optional: version bump type — `patch`, `minor`, or `major`. Defaults to
analyzing changes.

## Instructions

1. Determine the version bump:

   - If `patch`, `minor`, or `major` was passed, use that
   - If not specified, analyze commits since the last tag to determine:
     - `major`: breaking changes (commits with `!` or `BREAKING CHANGE`)
     - `minor`: new features (`feat:` commits)
     - `patch`: fixes, refactors, docs, chores only

2. Get the current version:

   - Check `git tag --sort=-v:refname | head -1` for the latest tag
   - If no tags exist, start at `v0.1.0`

3. Calculate the new version following semver.

4. Verify readiness:

   - `git status` — must be on `main` with no uncommitted changes
   - `git pull origin main` — must be up to date
   - Warn and stop if not on `main` or if there are uncommitted changes

5. Read `CHANGELOG.md` and check that the `[Unreleased]` section has content.

6. Update `CHANGELOG.md`:

   - Rename `[Unreleased]` to `[X.Y.Z] -- YYYY-MM-DD` (today's date)
   - Add a new empty `[Unreleased]` section above it

7. Bump the package version in `src/llmoxie_analysis/__init__.py`
   (`__version__`, read by Hatchling) and `pixi.toml` (`version`). If
   `CITATION.cff` exists, set its `version` and `date-released` too.

8. Run `pixi run verify`; it must exit 0.

9. Commit the release preparation:

   ```bash
   git add CHANGELOG.md pixi.toml src/llmoxie_analysis/__init__.py  # and CITATION.cff if present
   git commit -m "chore(release): prepare vX.Y.Z" -m "Assisted-by: <harness>:<model>"
   ```

   The trailer follows the `commit` skill's AI Attribution section. Omit it
   entirely if the release was cut without AI assistance.

10. Create the git tag:

    ```bash
    git tag -a vX.Y.Z -m "vX.Y.Z"
    ```

11. Push the commit and tag:

    ```bash
    git push origin main --follow-tags
    ```

12. Build the distribution from the tagged commit:

    ```bash
    rm -rf dist && pixi run build
    ```

    This writes `dist/llmoxie_analysis-X.Y.Z-py3-none-any.whl` and
    `dist/llmoxie_analysis-X.Y.Z.tar.gz`. Confirm the version in the file names
    matches the tag.

13. Create a GitHub release with the built artifacts:

    ```bash
    gh release create vX.Y.Z --title "vX.Y.Z" \
      --notes "$(cat <<'EOF'
    ## What's Changed

    <extract the relevant section from CHANGELOG.md>

    **Full Changelog**: <repo compare URL>/compare/vPREVIOUS...vX.Y.Z
    EOF
    )" \
      dist/*.whl dist/*.tar.gz
    ```

    If the repository is linked to Zenodo, the release triggers a DOI
    automatically; add the DOI to `CITATION.cff` in a follow-up commit.

14. Confirm: "Released vX.Y.Z — <release URL>"

## Version Guidelines

| Bump            | When                               | Example             |
| --------------- | ---------------------------------- | ------------------- |
| `patch` (0.1.X) | Bug fixes, docs, chores, refactors | `v0.1.1` → `v0.1.2` |
| `minor` (0.X.0) | New features, non-breaking changes | `v0.1.2` → `v0.2.0` |
| `major` (X.0.0) | Breaking changes, major rewrites   | `v0.2.0` → `v1.0.0` |

## Rules

- Must be on `main` branch with no uncommitted changes
- Must have content in `[Unreleased]` section of CHANGELOG.md
- Never create a release from a feature branch
- Tag format is always `vX.Y.Z` (with `v` prefix)
- Ask for confirmation before pushing the tag and creating the release
- If CHANGELOG.md doesn't exist or has no `[Unreleased]` section, warn and ask
  how to proceed
- Never commit `dist/` — build artifacts are upload-only (gitignored)
- NEVER add "Generated with" or similar marketing lines to the release notes
- NEVER include sensitive information in the release notes or changelog
