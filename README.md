# Slack Hardware Assistant

A Slack integration tool for hardware teams that enables intelligent knowledge sharing via AI-generated daily digests.

## Vision

Hardware teams often juggle specifications, lab data, issue trackers, release plans, and manufacturing status across many tools. This project aims to surface coordination issues before they become a critical manufaturing problem or delay important steps in the production process.

## Initial Scope

MCP server architecture

Daily Digest worker acts as the MCP client, issuing structured “tools”/calls to:

- Slack Data MCP server for:
   - backfilling & refreshing messages/users/channels
   - fetching message bodies + metadata

- Semantic Search MCP server for:
   - embedding new content
   - performing vector search for digests or interactive queries


### Semantic Search

#### Tools:
- embed_and_upsert(messages, workspace_id)
- search_similar(user_id, timeframe, knobs) → returns ranked messages/topics.

Embeddings are computed either inside this server or via a configured embedding provider (e.g., OpenAI) and stored as vectors in Weaviate.

Postgres stores “ground truth” and metadata; Weaviate stores the vector space and semantic relationships.

####  Knobs to turn:

- top_k (how many results to retrieve per user per topic)
- minimum relevance score / cosine similarity threshold
- recency decay factor (how much to penalize older messages)
- per-topic quota in the digest (e.g., limit “firmware” items)
- diversity vs similarity (avoid too many near-duplicate hits)
- per-user interest weight (boost topics the user interacts with)

Global knob values can be stored in tuning_params table & used by MCP server; other knobs are submitted by MCP client tool on a per-user basis.
