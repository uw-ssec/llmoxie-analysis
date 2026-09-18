# Caveats
* [Caveat: Cost and Token Double-Counting](cost-token-double-counting.md) - Agentic clients resend the whole conversation on every turn, so summing per-request spend across a session counts the same content many times over.
* [Caveat: last_request_per_session vs deduplicate_messages](dedup-vs-last-request.md) - Two reduction functions that look interchangeable are not, and applying them in the wrong order silently destroys most of a conversation.
* [Caveat: end_user Parsing Fragility](end-user-parsing.md) - Session identity is recovered by parsing a free-form client-supplied string, and roughly a quarter of early-2026 requests cannot be parsed at all.
* [Caveat: The Responses API Output Gap](responses-api-gap.md) - Requests made through the OpenAI Responses API return output under a different key, which the reader does not parse — so those replies are silently missing from sessions.
