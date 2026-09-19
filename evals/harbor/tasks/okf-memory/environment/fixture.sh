. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
commit_file knowledge/decisions/parquet-partitioning.md '---
id: decisions/parquet-partitioning
title: Partition the sessions Parquet by date
type: Decision
description: The sessions table is written as date-partitioned Parquet
governance: constraint
code_refs:
  - src/llmoxie_analysis/sessions.py
generated: true
---

Sessions are partitioned by date.' "feat(knowledge): record the partitioning decision" 3
mkdir -p /fixture/okf
printf 'decisions/parquet-partitioning  Decision  The sessions table is written as date-partitioned Parquet  (governance: constraint)\n' > /fixture/okf/search.txt
finish_fixture
