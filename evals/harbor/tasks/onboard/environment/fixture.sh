. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
commit_file knowledge/project/current-state.md '---
id: project/current-state
title: What exists and what is only designed
type: Fact
description: The analysis package is still empty scaffolding; pipeline/ records decisions for code that has not been written
generated: true
---

Most of pipeline/ is a specification. The working prototypes live in the
read-only reference/ submodules.' "feat(knowledge): record the current state" 4
commit_file knowledge/project/llmoxie-analysis.md '---
id: project/llmoxie-analysis
title: llmoxie-analysis
type: Project
description: Turns raw LLMoxie gateway request logs into a queryable Parquet warehouse
generated: true
---

Raw gateway logs in, a Parquet warehouse of sessions, messages, and tool calls
out.' "feat(knowledge): record what this project is" 4
commit_file knowledge/caveats/cost-token-double-counting.md '---
id: caveats/cost-token-double-counting
title: Caveat: Cost and Token Double-Counting
type: Fact
description: Agentic clients resend the whole conversation on every turn, so summing per-request spend across a session counts the same content many times over
governance: constraint
generated: true
---

Summing per-request spend across a session double-counts resent content.' "feat(knowledge): record the double-counting caveat" 4
mkdir -p /fixture/okf
printf 'caveats/cost-token-double-counting  Fact  Agentic clients resend the whole conversation on every turn  (governance: constraint)\ncaveats/end-user-parsing  Fact  Session identity is parsed from a free-form client string\n' > /fixture/okf/search.txt
finish_fixture
