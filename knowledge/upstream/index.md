# Upstream
* [Model Name Normalization](model-name-normalization.md) - The ordered rewrite rules that collapse provider-prefixed model identifiers into a single canonical family-and-version label for grouping.
* [reader.py — Flattening Requests to Message Blocks](reader-flattening.md) - The upstream module that explodes each gateway request into one row per content block, including the end_user parsing that session identity depends on.
* [group_sessions.py — Reconstructing Conversations](session-reconstruction.md) - The upstream prototype that groups flat request rows into per-session conversations, its DataFrame and streaming code paths, and the specific behaviors this project must preserve or repair.
