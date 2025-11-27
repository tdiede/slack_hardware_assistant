# Slack Hardware Assistant

A Slack integration tool for hardware teams that enables intelligent data retrieval through a conversational chat interface.

## Vision

Hardware teams often juggle specifications, lab data, issue trackers, release plans, and manufacturing status across many tools. This project aims to provide a single conversational surface inside Slack where engineers and program managers can:
- Ask questions about hardware designs, test results, and manufacturing status
- Retrieve relevant documents, tickets, and dashboards
- Log issues and decisions from Slack into source systems

## Initial Scope

The first iteration of this project will focus on:
- A Slack app that can be installed into a workspace and added to specific channels
- A bot event subscription for when @hardware_assistant is mentioned with a question
- A bot event subscription for messages (in channels where hardware_assistant has been added)
- A backend service that can route natural-language questions to the appropriate data source adapters
- Backend storage to save data for historical analysis and aggregation

## MVP Feature List (Deliverable-Ready)

### A. Slack Integration

#### Inbound

✔️ Bot receives:
- app_mention events
- message.channels events (only for channels it is in)

#### Outbound

✔️ Fetch using Slack Web API:
- channels (conversations.list)
- messages (conversations.history)
- thread replies (conversations.replies)
- users (users.list)

### B. Backend Features (Python/FastAPI)

#### 1. REST endpoints

- GET /api/workspaces/{id}/channels
- GET /api/channels/{id}/messages?days=60&query=<keyword>
- GET /api/messages/{ts}/thread
- GET /api/users
- GET /api/aggregates/topics?days=60
- GET /api/aggregates/top_users?days=60
- GET /api/aggregates/activity?days=60

#### 2. Aggregation logic

✔️ Compute:
- Most-discussed topics (keyword frequency)
- Most active users (message count)
- Thread depth statistics
- Channel activity (messages per day)
- Engineering-topic clusters (PCB, mechanical, firmware, electrical, etc.)

#### 3. Scheduled ingestion

Fetch new Slack messages every 1 hour or daily.

#### 4. Postgres Storage

✔️ Tables:
- workspaces(id, slack_workspace_id, token)
- channels(id, slack_channel_id, workspace_id, name)
- users(id, slack_user_id, workspace_id, real_name, title)
- messages(ts, channel_id, user_id, text, parent_ts, created_at)
- aggregate_topic_stats(date, channel_id, keyword, count)
- aggregate_user_stats(date, channel_id, user_id, messages)

### C. Frontend Features (React or simple HTML) *not implemented here

✔️ Channel browser page
- List available channels
- Click to view messages / aggregates

✔️ Aggregates dashboard
- Top topics (keyword list or bar chart)
- Top users
- Most active days/weeks
- Threads with the most activity

✔️ Search/Query UI
- Search bar: “PCB”, “mechanical”, “battery”, etc.
- Dropdown for timeframe (7 days, 30 days, 60 days)

## Future Ideas

- Support for common hardware tools (issue trackers, PLM, lab/ATE data, manufacturing dashboards)
- Proactive alerts posted into Slack based on rules or anomalies


## Project Layout

app/
  __init__.py
  main.py          # FastAPI app, routes
  db.py            # DB engine + session + get_db dependency + init_db
  models.py        # SQLAlchemy ORM models (User, etc.)
  schemas.py       # Pydantic models (request/response)
  crud.py          # Database operations (create/read users)



  


## Intended high-level architecture (from README)

The `README.md` describes the intended first iteration and future direction. The architecture is expected to revolve around these major components:

- **Slack app**: Installed into a workspace and specific channels, providing the conversational surface (slash commands, message shortcuts, and possibly event handlers).
- **Backend service**: A service (to be defined) that receives natural-language questions and routing metadata from the Slack app.
- **Data source adapters**: A set of adapters behind the backend that connect to external systems (e.g., issue trackers, PLM, lab/ATE data, manufacturing dashboards) and translate between domain-specific queries/objects and the assistant’s internal representations.
- **Conversation and routing layer**: Logic (likely in the backend) that interprets user questions, selects appropriate data source adapters, and composes responses (including summaries of test runs, regressions, or manufacturing status).

These components are not yet implemented in this repository. When adding code, organize it so that the Slack app, backend routing, and data source adapters remain clearly separated, and then expand this section with concrete module/package names and key entrypoints.

## How to keep this file useful

As the project matures and real code is added, update this file to include:

- The actual stack in use (languages, frameworks, key services).
- Concrete commands for local development, testing, and deployment.
- Pointers to the main entrypoints (e.g., bot startup script, backend service main, adapter registries).

Avoid duplicating obvious file listings; focus on information that requires reading multiple files to piece together (overall architecture, data flows, and non-obvious conventions specific to this project).
