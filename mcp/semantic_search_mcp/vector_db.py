# import logging
# import weaviate
# from dotenv import load_dotenv
# from weaviate.classes.config import Configure

# logger = logging.getLogger(__name__)
# WEAVIATE_CLASS_NAME = "Message"

# def init_weaviate():
#     # Create a long-lived client (no context manager here)
#     client = weaviate.connect_to_local(port=8080, host="weaviate")
#     print("Connected to Weaviate")

#     # Ensure the collection exists (create if missing)
#     existing = client.collections.list_all().keys()
#     if WEAVIATE_CLASS_NAME not in existing:
#         client.collections.create(
#             name=WEAVIATE_CLASS_NAME,
#             vector_config=Configure.Vectors.self_provided(),  # you already had this
#         )
#         print(f"Created collection {WEAVIATE_CLASS_NAME}")

#     # Example import of one object
#     data_objects = [
#         {
#             "properties": {
#                 "message_id": "msg-001",
#                 "user_id": "U12345",
#                 "channel_id": "C67890",
#                 "text": "Hello, this is a test message from user U12345 in channel C67890.",
#             },
#             "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
#         },
#     ]

#     messages = client.collections.get(WEAVIATE_CLASS_NAME)

#     with messages.batch.fixed_size(batch_size=200) as batch:
#         for obj in data_objects:
#             batch.add_object(
#                 properties=obj["properties"],
#                 vector=obj["vector"],
#             )

#     print(f"Imported {len(data_objects)} objects with vectors into the {WEAVIATE_CLASS_NAME} collection")

#     return client


# # ---- Startup code ----

# load_dotenv()

# try:
#     weaviate_client = init_weaviate()

#     # v4-style "test access" instead of data_object.get_class(...)
#     test_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
#     logger.info("Weaviate client initialized successfully, collection: %s", test_collection.name)

# except Exception as e:
#     logger.error("Failed to create Weaviate client: %s", e)
#     raise


# vector_db.py
import time
import logging
import weaviate
from weaviate.exceptions import WeaviateConnectionError

logger = logging.getLogger(__name__)

_WEAVIATE_CLIENT = None

WEAVIATE_CLASS_NAME = "Message"

def init_weaviate(max_retries: int = 20, delay: float = 2.0):
    """Connect to Weaviate with retries, returns a live client."""
    url = "http://weaviate:8080"
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Connecting to Weaviate at %s (attempt %d/%d)", url, attempt, max_retries)
            client = weaviate.connect_to_local(host="weaviate", port=8080)
            # Simple ping to confirm it’s really up
            client.collections.list_all()
            logger.info("Connected to Weaviate successfully.")
            return client
        except WeaviateConnectionError as e:
            logger.warning("Weaviate not ready yet: %s", e)
        except Exception as e:
            logger.warning("Unexpected error connecting to Weaviate: %s", e)

        if attempt == max_retries:
            logger.error("Failed to connect to Weaviate after %d attempts", max_retries)
            raise
        time.sleep(delay)

def get_weaviate_client():
    """Lazy global singleton."""
    global _WEAVIATE_CLIENT
    if _WEAVIATE_CLIENT is None:
        _WEAVIATE_CLIENT = init_weaviate()
    return _WEAVIATE_CLIENT
