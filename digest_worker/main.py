import os
import requests
from datetime import date


MCP_SLACK_URL = os.getenv("MCP_SLACK_URL", "http://localhost:3030")
MCP_SEMANTIC_URL = os.getenv("MCP_SEMANTIC_URL", "http://localhost:6060")

def fetch_all_users():
    """Call Slack MCP server to get user list."""
    resp = requests.get(f"{MCP_SLACK_URL}/tools/list_users")
    resp.raise_for_status()
    return resp.json()["users"]


def fetch_relevant_messages(user_id):
    """Call Semantic Search MCP server."""
    payload = {
        "user_id": user_id,
        "top_k": 10,
        "timeframe_days": 1,
        "recency_weight": 0.5
    }
    resp = requests.post(f"{MCP_SEMANTIC_URL}/tools/fetch_relevant_messages", json=payload)
    resp.raise_for_status()
    return resp.json()["results"]


def format_digest(relevant_messages):
    """Turn vector search results into a readable digest."""
    if not relevant_messages:
        return "No updates today."

    lines = ["Here’s your daily digest:\n"]
    for msg in relevant_messages:
        lines.append(f"• {msg['score']:.2f} — {msg['text']}")
    return "\n".join(lines)


def deliver_digest(user_id, digest_text):
    """Send digest via Slack MCP server."""
    payload = {"user_id": user_id, "text": digest_text}
    resp = requests.post(f"{MCP_SLACK_URL}/send_message", json=payload)
    resp.raise_for_status()


def main():
    print(f"[{date.today()}] Running daily digest job…")

    users = fetch_all_users()

    for user in users:
        uid = user["id"]
        print(f"Generating digest for {uid}...")
        messages = fetch_relevant_messages(uid)
        digest = format_digest(messages)
        deliver_digest(uid, digest)

    print("Daily digest job complete.")


if __name__ == "__main__":
    main()
