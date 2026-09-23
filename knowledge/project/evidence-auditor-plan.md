---
type: Process
title: "Adversarial review agents: the design settled in brainstorming and what is left to build"
description: "Two adversarial agents split on tool permissions rather than topic, with evidence-auditor first: it audits the commit and PR artifacts instead of the session, advises without blocking, and its enforcement lives in the eval-covered skill layer."
tags: [agents, adversarial-review, evals, design, planning]
generated: { by: "claude-code:claude-opus-5", at: "2026-09-23T16:28:32Z" }
status: draft
governance: context
code_refs: [".agents/agents/**", ".agents/skills/create-pr/**", evals/inspect/skill_eval.py, "evals/harbor/tasks/**", tests/test_skill_evals.py]
sources:
  - resource: "brainstorming session 2026-09-23, design approved in conversation"
  - resource: llmoxie-analysis evals/inspect/skill_eval.py and evals/harbor/tasks/create-pr as read on 2026-09-23
---

Design settled in conversation on 2026-09-23. No spec written, nothing built.
Recorded so the reasoning survives; see the Status section for the resume point.

## How many agents, and the rule that decided it

**Split on tool permissions and trigger moment; merge on judgment type.**
Two checks needing the same access at the same point are one agent even when
they sound different; two needing different access stay separate even when
they sound alike.

Four candidate targets were on the table: claims made in session, the diff
before a PR, the knowledge bundle, and the analysis conclusions. Running them
through the rule gives:

- `evidence-auditor` — claims plus diff. Same tools, same window, same
  question ("asserted or shown?"). Build this one first.
- `analysis-auditor` — data conclusions only. Separate because it is the one
  that needs the 1.0 GB extract, which is a real permission escalation and
  where `datasets/pii-handling` binds. Deferred until the first agent has
  earned its keep on real PRs.
- The knowledge bundle is **not** an agent. Most of it is mechanical and
  `okf validate --strict --drift` already covers part; the rest belongs in the
  validator. Its judgment half folds into `evidence-auditor` when a diff
  touches `knowledge/`.

Rejected: **one agent with four modes** — subagent dispatch matches on
`description`, and a description spanning all four is vague enough to fire at
the wrong times, while one model setting must serve both a near-deterministic
check and a deep one. Rejected: **four agents** — four uncalibrated prompts,
and miscalibration in any one teaches the maintainer to ignore all four.

## Why it audits artifacts, not the session

A subagent defined under `.claude/agents/` starts with a fresh context window
and cannot see what the main session ran or asserted. An audit fed by "here
are the claims I made" is therefore self-reported, and an agent that omits a
claim evades it entirely — weakest exactly where it matters most.

So the claim surface is the durable artifacts: commit message bodies, the PR
description, and the diff, reconstructed by the agent from
`git log main..HEAD --format=%B`, `git diff main...HEAD`, and
`gh pr view --json body`. For each falsifiable assertion it **re-runs the
check itself**; its evidence is its own command output, never the session's
word. Cost is roughly one verify run, so it belongs at PR time and nowhere
near per-edit.

## Advisory with teeth

It cannot block a PR. Any `unsupported` or `overstated` finding must be
transcribed **verbatim** — claim, command, output — into the
"Less certain about" field that `.github/pull_request_template.md` already
provides. The PR still opens; the waiver becomes visible to a reviewer rather
than silent.

This puts each half where it can be trusted: the judgment nobody has
calibrated stays advisory inside the agent, while the transcription rule lives
in the `/create-pr` skill, which the eval suite can assert on.

## Output contract

Four verdicts on a grounding axis, not the installed `severity-framework`,
which is built for code defects:

- `unsupported` — check re-run, output contradicts the claim.
- `overstated` — check passes but the claim is broader than what it proves.
- `unverifiable` — no command could falsify it from the artifacts.
- `grounded` — checked, holds.

Every finding carries four fields or it is not a finding: the claim quoted
verbatim with its location, the command run, the actual output, the verdict.
A mandatory calibration line comes first and carries the denominator
(`12 claims extracted, 9 machine-checkable, 8 grounded, 1 overstated`), so a
sharp pass is distinguishable from a lazy one. A clean run returns that line
and nothing else, and that is a success.

**Hard boundary: human attestations are out of scope.** The template's
"I personally verified:" is the maintainer's word and the agent has no
standing to call it unsupported. Only machine-checkable claims are in scope;
absent a falsifying command the verdict is `unverifiable`, never
`unsupported`. This is what keeps an adversarial agent from drifting into
accusing its maintainer, which is the fastest route to it being switched off.

Scope for the first build is narrow: process claims, plus `knowledge/`
frontmatter (`code_refs`, `status`, `generated:`) because those are
mechanically checkable and drift silently today. Substantive assertions inside
a diff are deferred — more valuable, much harder to calibrate, and they start
overlapping `analysis-auditor`.

## Tools, and a limitation not to paper over

`tools: Read, Grep, Glob, Bash` with `model: opus`. Bash is unavoidable: the
premise is re-running checks. Opus because constructing a falsifying command
and reading output skeptically is the hard part; a cheaper model sees the word
"passed" and returns `grounded`.

**A Bash-enabled agent cannot be made read-only through configuration.**
Omitting Edit and Write does nothing when `>`, `tee` and `sed -i` are in
Bash, and `permissions.deny` entries match on command prefix, so a wrapper
walks past them. They are worth adding against casual drift; they are not a
sandbox.

Worktree isolation was considered and rejected for this repo: a fresh worktree
has no `.pixi/`, so `pixi run verify` needs a full install before it can check
anything, turning a one-minute audit into a multi-minute one. Instead the
agent runs in the same working tree and `/create-pr` records
`git rev-parse HEAD` and `git status --porcelain` before dispatch and after,
failing loudly if either moved — proof rather than trust, and assertable in
the skill layer.

Note that `.claude/hooks/okf-for-path.sh` matches `Edit|Write|MultiEdit` and
so never fires for this agent. Correct, but it means the memory check is not
in its path.

## Eval plan

Inspect extends nearly for free: `skill_body()` in
`evals/inspect/skill_eval.py` strips YAML frontmatter from a markdown file, so
adding `.agents/agents` to `SKILL_ROOTS` is close to a one-line change and the
sample format needs nothing. But samples get `TEXT_ONLY_NOTE` appended, so
Inspect covers the **protocol** — quoting the claim, naming the command,
emitting the calibration line, choosing `unverifiable` over `unsupported`,
refusing to flag an attestation — and not the judgment.

Harbor covers the judgment, following the shim-log pattern in
`evals/harbor/tasks/create-pr/tests/test.sh`:

- `evidence-auditor` — a seeded false claim with the `pixi` shim reporting
  failure; assert `unsupported` and that the shim output is quoted.
- `evidence-auditor-clean` — every claim true; assert the calibration line and
  **zero** findings. The most valuable test in the set, because
  finding-inflation is the failure mode nothing else catches.
- `evidence-auditor-guard` — copying `commit-guard` / `push-guard`: no
  `git commit` or `git push` in the shim log, HEAD unchanged.

Extend the existing `create-pr` verifier, which already inspects
`gh pr create` body arguments, to assert verbatim transcription. Extend
`test_every_skill_has_inspect_samples` and `test_every_skill_has_harbor_task`
in `tests/test_skill_evals.py` to cover `.agents/agents`, making coverage
structural.

**What scripted evals cannot give:** the false-positive rate on real work.
Both layers test scripted scenarios against fake shims. The number that
decides whether the agent is worth running — flagged N things across M real
PRs, K were noise — needs a backtest over this repository's merged PRs, where
ground truth is already known. Treat that as a separate calibration step
before trusting it.

## Status

Design approved in conversation; the spec at
`docs/superpowers/specs/2026-09-23-evidence-auditor-design.md` is **not
written** and no agent, rule, or eval exists. Resume by writing that spec,
then the shared standard at `.agents/rules/adversarial-review.md`, then
`evidence-auditor` and its three Harbor tasks. `analysis-auditor` stays
deferred until the first has run on real PRs.

# Related Concepts
- [Harness wiring: where agent definitions live and which harness reads them](harness-agent-wiring.md): Where an agent definition must live and why the standard cannot live only in it.
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The two-level suite this plan extends to cover agents as well as skills.
