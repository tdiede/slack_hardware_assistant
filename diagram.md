                          Users & Channels
                         (messages, threads)
                                 │
                                 │
                                 ▼
                   ┌───────────────────────────────┐
                   │       Slack Workspaces        │
                   │  (multiple hardware teams)    │
                   │  ┌─────────────────────────┐  │
                   │  |   Slack App / Bot       │  │
                   │  │  - Events (webhooks)    │  │
                   │  │  - Web API (chat.*)     │  │
                   │  └─────────────────────────┘  │
                   └─────────────┬─────────────────┘
                                 │ HTTPS (events, OAuth, Web API)
                                 ▼
                         ┌─────────────────┐
                         │     Internet    │
                         └───────┬─────────┘
                                 │ HTTPS
                                 ▼
                        ┌───────────────────┐
                        │   ngrok Tunnel    │
                        │ https://xyz.ngrok │
                        │    ▼              │
                        │ http://host:8000  │
                        └────────┬──────────┘
                                 │ HTTP
                                 ▼
                          Docker Host (dev/prod)
    ┌──────────────────────────────────────────────────────────────────────┐
    |                                                                      │
    │  ┌───────────────────────────────┐       ┌─────────────────────────┐ │
    │  │  fastapi-app container        |       │   postgres-db container │ │
    │  │  (Python + FastAPI backend)   │       │  (PostgreSQL + schema)  │ │
    │  │  ┌─────────────────────────┐  │       │  - workspaces           │ │
    │  │  | Slack Integration Layer │  │       │  - users                │ │
    │  │  │  - /slack/events        │◀─┼──────▶│  - channels             │ │
    │  │  │  - verifies signatures  │  │  SQL  │  - messages             │ │
    │  │  │  - rate-limit handling  │  │       │  - auth sessions        │ │
    │  │  └─────────────────────────┘  │       └─────────────────────────┘ │
    │  │  ┌─────────────────────────┐  │                                   │
    │  │  │ REST API      │  │                                   │
    │  │  │  - /api/chat/query      │  │                                   │
    │  │  │  - /api/messages        │  │                                   │
    │  │  │  - /auth/login          │  │                                   │
    │  │  └─────────────────────────┘  │                                   │
    │  │  ┌─────────────────────────┐  │                                   │
    │  │  │ Business Logic Layer    │  │                                   │
    │  │  │  - fetch Slack data     │  │                                   │
    │  │  │  - query DB             │  │                                   │
    │  │  │  - semantic search (*)  │  │                                   │
    │  │  │  - caching layer (*)    │  │                                   │
    │  │  └─────────────────────────┘  │                                   │
    │  │                               │                                   │
    │  └───────────────────────────────┘                                   │
    │                                                                      │
    └──────────────────────────────────────────────────────────────────────┘
                                         ▲
                                         │ HTTP/HTTPS (REST/GraphQL)
                                         │
                           ┌────────────────────────────────┐
                           │    Browser (React Frontend)    │
                           │  - Chat UI                     │
                           │  - Login / auth                │
                           │  - Displays search results     │
                           └────────────────────────────────┘


(*) Optional / extensible components for the take-home:
    - Semantic search: embeddings + vector search (pgvector or separate service)
    - Caching: Redis or in-memory cache sitting next to FastAPI

Horizontal scaling (conceptual):
    - Multiple fastapi-app containers behind a load balancer
    - Shared Postgres (and shared cache) across instances
    - Slack points at load balancer URL instead of single ngrok/dev URL
