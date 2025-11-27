import os 

from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt import App

from slack_sdk import WebClient


SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

client = WebClient(token=SLACK_BOT_TOKEN)

bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = SlackRequestHandler(bolt_app)


# SLACK INTEGRATION EVENT SUBSCRIPTIONS ###

@bolt_app.event("message")
def handle_message(body, say):
    event = body.get("event", {})
    for block in event.get("blocks", []):
        for element in block.get("elements", []):
            for e in element.get("elements", []):
                if e.get("type") == "user":
                    return  # Ignore app mentions, which are handled separately
    text = event.get("text")
    user = event.get("user")
    channel = event.get("channel")
    say(f"Message {text} sent by user {user} in channel {channel}")

@bolt_app.event("app_mention")
def handle_app_mention(body, say):
    say(f"👋 Hi! I received your message.")
