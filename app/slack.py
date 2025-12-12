import os 
import logging
from dotenv import load_dotenv

from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt import App

logger = logging.getLogger(__name__)

load_dotenv() # take environment variables from .env.

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

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
    _, user, text = parse_body(body)
    # call LLM or other text analysis tool here with `text` to extract intent/entities
    # return structured query for database
    query = f"SELECT user_id, channel_id, text FROM messages WHERE user_id = '%{user}%'"
    say(f"👋 Hi <@{user}>! I received your message: {text}")

def parse_body(body) -> list[str]:
    event = body.get("event", {})
    user = event.get("user")
    text = event.get("text")
    logger.info(f"App mentioned by user {user} with text: {text}")
    return [event, user, text]
