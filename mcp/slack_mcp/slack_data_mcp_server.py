import os
import time
import logging
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] slack-data-mcp: %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Slack Web API wrapper with retry / pagination
# ------------------------------------------------------------

class SlackDataClient:
    """
    A thin wrapper around slack_sdk.WebClient that:
      - centralizes rate-limit handling (HTTP 429)
      - provides helpers for pagination
    """

    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("SLACK_BOT_TOKEN is required")
        self.client = WebClient(token=bot_token)

    def _call_with_retry(self, method_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a Slack Web API method with basic rate-limit handling.
        'method_name' is the WebClient method name, e.g. 'conversations_list'.
        """
        while True:
            try:
                method = getattr(self.client, method_name)
                resp = method(**kwargs)
                return resp.data
            except SlackApiError as e:
                if e.response is not None and e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", "1"))
                    logger.warning(
                        "Rate limited on %s. Retrying after %s seconds...",
                        method_name,
                        retry_after,
                    )
                    time.sleep(retry_after)
                    continue

                logger.error(
                    "Slack API error on %s: %s",
                    method_name,
                    getattr(e.response, "data", e),
                )
                raise

    # ------------- Channels -------------

    def list_channels(
        self,
        types: str = "public_channel,private_channel",
        limit: int = 200,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a single page of channels, plus next_cursor if more pages exist.
        This mirrors Slack's conversations.list.
        """
        resp = self._call_with_retry(
            "conversations_list",
            types=types,
            limit=limit,
            cursor=cursor,
        )

        channels = resp.get("channels", [])
        next_cursor = resp.get("response_metadata", {}).get("next_cursor", "")

        return {"channels": channels, "next_cursor": next_cursor}

    def fetch_channel_history(
        self,
        channel: str,
        oldest: Optional[float] = None,
        latest: Optional[float] = None,
        limit: int = 200,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a single page of messages for a channel, plus next_cursor.
        This mirrors conversations.history.
        """
        kwargs: Dict[str, Any] = {
            "channel": channel,
            "limit": limit,
        }
        if cursor:
            kwargs["cursor"] = cursor
        if oldest is not None:
            kwargs["oldest"] = str(oldest)
        if latest is not None:
            kwargs["latest"] = str(latest)

        resp = self._call_with_retry("conversations_history", **kwargs)

        messages = resp.get("messages", [])
        next_cursor = resp.get("response_metadata", {}).get("next_cursor", "")

        return {"messages": messages, "next_cursor": next_cursor}

    def fetch_thread(
        self,
        channel: str,
        thread_ts: str,
        limit: int = 200,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a single page of messages for a thread, plus next_cursor.
        This mirrors conversations.replies.
        """
        kwargs: Dict[str, Any] = {
            "channel": channel,
            "ts": thread_ts,
            "limit": limit,
        }
        if cursor:
            kwargs["cursor"] = cursor

        resp = self._call_with_retry("conversations_replies", **kwargs)

        messages = resp.get("messages", [])
        next_cursor = resp.get("response_metadata", {}).get("next_cursor", "")

        return {"messages": messages, "next_cursor": next_cursor}

    # ------------- Users -------------

    def list_users(
        self,
        limit: int = 200,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a single page of users, plus next_cursor.
        This mirrors users.list.
        """
        kwargs: Dict[str, Any] = {
            "limit": limit,
        }
        if cursor:
            kwargs["cursor"] = cursor

        resp = self._call_with_retry("users_list", **kwargs)

        members = resp.get("members", [])
        next_cursor = resp.get("response_metadata", {}).get("next_cursor", "")

        return {"users": members, "next_cursor": next_cursor}


load_dotenv() # take environment variables from .env.

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
slack_client = SlackDataClient(bot_token=SLACK_BOT_TOKEN)


# ------------------------------------------------------------
# Pydantic models for the FastAPI layer
# (MCP-style "tools")
# ------------------------------------------------------------

class ChannelListResponse(BaseModel):
    channels: List[Dict[str, Any]]
    next_cursor: str


class MessagePageResponse(BaseModel):
    messages: List[Dict[str, Any]]
    next_cursor: str


class UserListResponse(BaseModel):
    users: List[Dict[str, Any]]
    next_cursor: str


# ------------------------------------------------------------
# FastAPI app exposing Slack data as MCP tools
# ------------------------------------------------------------


app = FastAPI(
    title="Slack Data MCP Server",
    description=(
        "MCP-style server that wraps Slack Web API for conversations & users. "
        "Exposes tools for list_channels, fetch_channel_history, fetch_thread, list_users. "
        "Use this as a standalone microservice or as a tool provider for an MCP client."
    ),
    version="0.1.0",
)

# ------------- MCP Tools Endpoints -------------

# - GET /tools/list_channels
# - GET /tools/fetch_channel_history
# - GET /tools/fetch_thread
# - GET /tools/list_users

# ------------------------------------------------------------

@app.get("/tools/list_channels", response_model=ChannelListResponse)
def tool_list_channels(
    types: str = Query(
        "public_channel,private_channel",
        description="Comma-separated channel types: public_channel,private_channel,im,mpim",
    ),
    limit: int = Query(200, ge=1, le=1000),
    cursor: Optional[str] = Query(
        None,
        description="Slack cursor for pagination. If omitted, starts at first page.",
    ),
):
    """
    MCP Tool: list_channels

    Returns a single page of channels from Slack's conversations.list, with an optional
    next_cursor if more pages are available.
    """
    try:
        result = slack_client.list_channels(types=types, limit=limit, cursor=cursor)
        return ChannelListResponse(**result)
    except Exception as e:
        logger.exception("Error in list_channels")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/fetch_channel_history", response_model=MessagePageResponse)
def tool_fetch_channel_history(
    channel: str = Query(..., description="Slack channel ID (e.g. C0123456789)"),
    oldest: Optional[float] = Query(
        None,
        description="Oldest timestamp to include (as Unix epoch float). Optional.",
    ),
    latest: Optional[float] = Query(
        None,
        description="Latest timestamp to include (as Unix epoch float). Optional.",
    ),
    limit: int = Query(200, ge=1, le=1000),
    cursor: Optional[str] = Query(
        None, description="Slack cursor for pagination. If omitted, starts at first page."
    ),
):
    """
    MCP Tool: fetch_channel_history

    Returns a single page of channel messages from Slack's conversations.history.
    """
    try:
        result = slack_client.fetch_channel_history(
            channel=channel,
            oldest=oldest,
            latest=latest,
            limit=limit,
            cursor=cursor,
        )
        return MessagePageResponse(**result)
    except Exception as e:
        logger.exception("Error in fetch_channel_history")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/fetch_thread", response_model=MessagePageResponse)
def tool_fetch_thread(
    channel: str = Query(..., description="Slack channel ID containing the thread."),
    thread_ts: str = Query(..., description="Parent message ts of the thread."),
    limit: int = Query(200, ge=1, le=1000),
    cursor: Optional[str] = Query(
        None, description="Slack cursor for pagination. If omitted, starts at first page."
    ),
):
    """
    MCP Tool: fetch_thread

    Returns a single page of messages for a thread using conversations.replies.
    """
    try:
        result = slack_client.fetch_thread(
            channel=channel,
            thread_ts=thread_ts,
            limit=limit,
            cursor=cursor,
        )
        return MessagePageResponse(**result)
    except Exception as e:
        logger.exception("Error in fetch_thread")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/list_users", response_model=UserListResponse)
def tool_list_users(
    limit: int = Query(200, ge=1, le=1000),
    cursor: Optional[str] = Query(
        None, description="Slack cursor for pagination. If omitted, starts at first page."
    ),
):
    """
    MCP Tool: list_users

    Returns a single page of users from Slack's users.list.
    """
    try:
        result = slack_client.list_users(limit=limit, cursor=cursor)
        return UserListResponse(**result)
    except Exception as e:
        logger.exception("Error in list_users")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------
# Local dev entrypoint
# ------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "slack_data_mcp_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "3030")),
        reload=True,
    )
