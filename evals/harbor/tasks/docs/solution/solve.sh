#!/bin/bash
set -euo pipefail
cd /app
git log --oneline -20
git log --oneline --since="8 hours ago"
cat docs/index.md mkdocs.yml
mkdir -p docs/architecture
cat > docs/architecture/sessions.md <<'EOF'
# Sessions table

One row per conversation, built from raw request logs and partitioned by date.

## Why date partitions

ADLS listings are per-day, so a daily partition maps one listing to one write.

```mermaid
graph TD
    A[Raw request logs] -->|per-day listing| B[build_sessions]
    B -->|Parquet partition| C[sessions/date=YYYY-MM-DD]
```

## API

| Function              | Returns                        |
| ---------------------- | ------------------------------- |
| `build_sessions(day)` | row count written for that day |
EOF
printf '  - Architecture:\n      - Sessions table: architecture/sessions.md\n' >> mkdocs.yml
printf -- '- [Sessions table](architecture/sessions.md): how the sessions table is built and partitioned.\n' >> docs/index.md
pixi run docs-build
echo "Created docs/architecture/sessions.md; nav entry added; build passed."
