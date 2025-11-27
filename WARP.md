# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository overview

The repository includes a minimal Python backend (`app/`) exposed via a FastAPI app served by `uvicorn`, plus Docker configuration for running the backend alongside a PostgreSQL database.

## Development commands

### Local (without Docker)

- Create and activate a virtualenv (example):
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Install dependencies:
  - `pip install -r requirements.txt`
- Run the backend with auto-reload:
  - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Run ngrok to expose local dev with public request url (for Slack event subscriptions):
  - `ngrok http 8000`
- Add ngrok forwarding https url to Slack app:
  - `https://api.slack.com/apps/A0A06HZG9B7/event-subscriptions`

For local Postgres, either run it yourself and set `DATABASE_URL`, or rely on Docker as described below.

### Docker (docker compose w/ backend + Postgres)

- Build the backend image from Dockerfile:
  - `make build`
- Start the containers in background:
  - `make up`
- Tear them down:
  - `make down`

## Helpful Commands

- Hit the health check:
  - `curl http://localhost:8000/health`
