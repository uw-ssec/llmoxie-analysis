---
type: Project
title: "Cross-VISS Demo and the Repository's Two Purposes"
description: "The repository serves internal trace analysis for the long term and a Cross-VISS Convening demo in the near term, and the demo runs on a fork so its scaffolding must not shape this repository."
tags: [demo, cross-viss, priorities, workflow, project]
stale_after: 2026-12-31
sources:
  - resource: Project owner direction, 2026-09-18, on the demo venue and its relationship to this repository
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:22:49Z" }
---

This repository has two audiences, and they pull in different directions.

**The lasting purpose** is internal: analyzing the SSEC's own LLM gateway
traces. That is the work `pipeline/` specifies and the reason the caveats in
this bundle matter — they are properties of data the center will be making
decisions from.

**The near-term purpose** is a demonstration at the Cross-VISS Convening in
Atlanta in 2026, the annual internal meeting of the four VISS centers. The demo
is a worked example of agent-assisted research software engineering: knowledge
moved out of a person's head into artifacts an agent can use, with the
judgment gates left in human hands.

## The demo runs on a fork

This is the constraint worth remembering. The demo lives on a **fork** of this
repository, not on `main` here. Demo scaffolding — a branch per segment, reset
scripts, recorded prompts, deliberately broken starting states — belongs on the
fork. Do not add it here, and do not shape this repository's layout around a
presentation.

What the demo does legitimately influence is *priority*. It explains why the
skills in `.claude/skills/`, the verify gate, the AI policy, and this knowledge
bundle have had attention disproportionate to the analysis code itself: they
are the subject matter, not overhead. See
[[project/current-state]] for how lopsided that is right now.

## The through-line

The run of show is a working draft and its structure will move, so it is not
recorded here segment by segment. What is stable is the thesis and the arc:

1. Run a task with no skills, no memory, and no gates, and score the result
   against a checklist it visibly fails. That is the problem statement.
2. Add each layer — executable skills, then durable memory, then the full
   issue-to-PR loop — and rerun, showing what each one fixes.
3. Close on evaluation: the same task with and without each skill, measured
   rather than asserted. See [[project/skill-evals]].

The audience is internal and technical, so the demo can assume familiarity with
research software engineering practice and spend its time on the workflow
rather than on motivation.

## Related Concepts

- [What Exists and What Is Only Designed](current-state.md): Why the
  scaffolding is further along than the analysis package.
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The measurement
  half of the argument the demo makes.
- [LLMoxie Analysis](llmoxie-analysis.md): The actual software, whose value
  outlasts the presentation.
