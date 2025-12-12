import os
import time
import logging
import uuid
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from vector_db import init_weaviate
from weaviate.exceptions import WeaviateBaseError


WEAVIATE_CLASS_NAME = "Message"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] semantic-mcp: %(message)s",
)
logger = logging.getLogger(__name__)



# ------------------------------------------------------------
# Pydantic models
# ------------------------------------------------------------

class MessageInput(BaseModel):
    """
    Representation of a message we want to embed & store.
    You can adapt fields to match your schema.
    """
    message_id: str = Field(..., description="Stable ID from your system, e.g. Slack ts or DB UUID")
    workspace_id: str
    channel_id: str
    user_id: str
    text: str
    ts: float = Field(..., description="Unix timestamp (seconds)")
    topics: Optional[List[str]] = Field(default=None, description="Optional topic tags (e.g. ['pcb', 'firmware'])")


class EmbedAndUpsertRequest(BaseModel):
    messages: List[MessageInput]


class EmbedAndUpsertResponse(BaseModel):
    upserted_count: int


class SearchRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="User for personalization (optional).")
    # workspace_id: str
    query: Optional[str] = Field(
        None,
        description="Free-text query. If omitted, topics are used as concepts.",
    )
    topics: Optional[List[str]] = Field(
        default=None,
        description="Optional list of canonical topics (e.g. ['pcb', 'mechanical']).",
    )
    timeframe_days: int = Field(
        60,
        description="How far back to search (in days).",
        ge=1,
        le=365,
    )
    top_k: int = Field(
        20,
        description="Number of results to return after re-ranking.",
        ge=1,
        le=100,
    )
    min_score: float = Field(
        0.0,
        description="Minimum semantic score (certainty) required.",
        ge=0.0,
        le=1.0,
    )
    recency_weight: float = Field(
        0.3,
        description="How much to weight recency vs semantic similarity (0-1).",
        ge=0.0,
        le=1.0,
    )


class SearchResultItem(BaseModel):
    message_id: str
    workspace_id: str
    channel_id: str
    user_id: str
    text: str
    ts: float
    topics: Optional[List[str]] = None
    semantic_score: float
    recency_score: float
    final_score: float


class SearchResponse(BaseModel):
    results: List[SearchResultItem]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _upsert_message(msg: MessageInput) -> None:
    """Create or update a Weaviate object for this message."""
    slack_key = f"{msg.channel_id}:{msg.ts}"  # "C67890:1711000000.001"
    weaviate_id = str(uuid.uuid5(uuid.NAMESPACE_URL, slack_key))

    data: Dict[str, Any] = {
        "message_id": msg.message_id,
        "workspace_id": msg.workspace_id,
        "channel_id": msg.channel_id,
        "user_id": msg.user_id,
        "text": msg.text,
        "ts": msg.ts,
        "topics": msg.topics or [],
    }

    try:
        collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
    except WeaviateBaseError as e:
        logger.error("Error getting Weaviate collection %s: %s", WEAVIATE_CLASS_NAME, e, exc_info=True)
        raise

    try:
        # Try updating first
        collection.data.update(
            uuid=weaviate_id,
            properties=data,
        )
        logger.info("Updated existing Weaviate object %s", weaviate_id)

    except WeaviateBaseError as e:
        # If the error indicates "not found", fall back to insert.
        # You can inspect attributes like e.status_code or e.message depending on the exception class.
        msg_text = str(e)
        if "404" in msg_text or "not found" in msg_text.lower():
            logger.info("Object %s not found, inserting instead", weaviate_id)
            try:
                collection.data.insert(
                    uuid=weaviate_id,
                    properties=data,
                )
                logger.info("Inserted new Weaviate object %s", weaviate_id)
            except WeaviateBaseError as inner:
                logger.error("Error inserting object into Weaviate: %s", inner, exc_info=True)
                raise
        else:
            logger.error("Error updating object in Weaviate: %s", e, exc_info=True)
            raise


def _build_where_filter(workspace_id: str, min_ts: float) -> Dict[str, Any]:
    """
    Build a Weaviate 'where' filter combining workspace_id and time window.
    """
    filters: List[Dict[str, Any]] = [
        {
            "path": ["workspace_id"],
            "operator": "Equal",
            "valueString": workspace_id,
        },
        {
            "path": ["ts"],
            "operator": "GreaterThanEqual",
            "valueNumber": min_ts,
        },
    ]

    return {
        "operator": "And",
        "operands": filters,
    }


def _compute_recency_score(ts: float, min_ts: float, now_ts: float) -> float:
    """
    Normalize recency between 0 and 1 based on [min_ts, now_ts].
    """
    if ts <= min_ts:
        return 0.0
    if ts >= now_ts:
        return 1.0
    return (ts - min_ts) / (now_ts - min_ts + 1e-9)


def _extract_semantic_score(additional: Dict[str, Any]) -> float:
    """
    Weaviate _additional can contain 'certainty' or 'distance'. We prefer certainty (0-1).
    If only distance exists, convert it to a pseudo-score.
    """
    if "certainty" in additional:
        return float(additional["certainty"])

    # If distance is cosine distance, we can approximate: score = 1 - distance
    if "distance" in additional:
        try:
            dist = float(additional["distance"])
            return max(0.0, min(1.0, 1.0 - dist))
        except (TypeError, ValueError):
            pass

    # Fallback
    return 0.0


# ------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------

app = FastAPI(
    title="Semantic Search MCP Server",
    description=(
        "MCP-style server wrapping a Weaviate vector DB. "
        "Tools:\n"
        "- embed_and_upsert: upsert messages into Weaviate (vectorization handled by Weaviate)\n"
        "- search_similar: semantic search with recency-aware ranking and tuning knobs"
    ),
    version="0.1.0",
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/tools/sample_messages", response_model=List)
def tool_sample_messages():
    """
    MCP Tool: sample_messages

    Returns a few sample messages for testing.
    """
    # samples = [
    #     MessageInput(
    #         message_id="msg-001",
    #         workspace_id="W12345",
    #         channel_id="C67890",
    #         user_id="U12345",
    #         text="Hello, this is a test message from user U12345 in channel C67890.",
    #         ts=1711000000.001,
    #         topics=["test", "example"],
    #     ),
    #     MessageInput(
    #         message_id="msg-002",
    #         workspace_id="W12345",
    #         channel_id="C67890",
    #         user_id="U67890",
    #         text="Another example message discussing PCB design and firmware development.",
    #         ts=1712000000.002,
    #         topics=["pcb", "firmware"],
    #     ),
    # ]

    query_vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]  # same dimension as your embeddings

    collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
    results = collection.query.fetch_objects(
        limit=20  # adjust as needed
    )

    for obj in results.objects:
        print(obj.uuid, obj.properties)

    # results = collection.query.near_vector(
    #     near_vector=query_vector,
    #     limit=5,
    #     return_properties=["text", "user_id", "channel_id", "slack_ts"]
    # )

    # for o in results.objects:
    #     print(o.uuid, o.properties, o.distance)
    return results.objects


@app.post("/tools/embed_and_upsert", response_model=EmbedAndUpsertResponse)
def tool_embed_and_upsert(req: EmbedAndUpsertRequest):
    """
    MCP Tool: embed_and_upsert

    Upserts the given messages into Weaviate. We assume Weaviate is configured with a
    text2vec module to compute embeddings automatically based on 'text'.
    """
    if not req.messages:
        return EmbedAndUpsertResponse(upserted_count=0)

    count = 0
    start = time.time()

    try:
        for msg in req.messages:
            _upsert_message(msg)
            count += 1
    except Exception as e:
        logger.exception("Error during embed_and_upsert")
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = time.time() - start
    logger.info("Upserted %d messages into Weaviate in %.2fs", count, elapsed)
    return EmbedAndUpsertResponse(upserted_count=count)


@app.post("/tools/fetch_relevant_messages", response_model=SearchResponse)
def tool_fetch_relevant_messages(req: SearchRequest):
    """
    MCP Tool: fetch_relevant_messages

    Perform a semantic search in Weaviate for messages relevant to the user,
    restricted to a workspace and timeframe, and re-ranked by recency.

    The final_score is:
        (1 - recency_weight) * semantic_score + recency_weight * recency_score
    where semantic_score and recency_score are both in [0, 1].
    """
    return SearchResponse(results=[])
    if not req.query and not req.topics:
        raise HTTPException(
            status_code=400,
            detail="Either 'query' or 'topics' must be provided.",
        )

    now_ts = time.time()
    min_ts = now_ts - req.timeframe_days * 86400

    where_filter = _build_where_filter(req.workspace_id, min_ts)

    # Concepts for nearText
    concepts: List[str] = []
    if req.query:
        concepts.append(req.query)
    if req.topics:
        concepts.extend(req.topics)

    near_text: Dict[str, Any] = {
        "concepts": concepts,
    }

    # We fetch somewhat more results than top_k, then apply additional filtering
    # and re-ranking in Python.
    raw_limit = min(req.top_k * 3, 200)

    try:
        gql_response = (
            weaviate_client.query
            .get(
                WEAVIATE_CLASS_NAME,
                [
                    "message_id",
                    "workspace_id",
                    "channel_id",
                    "user_id",
                    "text",
                    "ts",
                    "topics",
                ],
            )
            .with_where(where_filter)
            .with_near_text(near_text)
            .with_limit(raw_limit)
            .with_additional(["id", "certainty", "distance"])
            .do()
        )
    except WeaviateBaseError as e:
        logger.error("Weaviate query error: %s", e)
        raise HTTPException(status_code=500, detail=f"Weaviate query error: {e}")

    hits = (
        gql_response
        .get("data", {})
        .get("Get", {})
        .get(WEAVIATE_CLASS_NAME, [])
    )

    logger.info("Weaviate returned %d raw hits", len(hits))

    scored_results: List[SearchResultItem] = []

    for hit in hits:
        additional = hit.get("_additional", {})
        semantic_score = _extract_semantic_score(additional)
        if semantic_score < req.min_score:
            continue

        ts_val = float(hit.get("ts", 0.0))
        recency_score = _compute_recency_score(ts_val, min_ts, now_ts)

        final_score = (
            (1.0 - req.recency_weight) * semantic_score
            + req.recency_weight * recency_score
        )

        scored_results.append(
            SearchResultItem(
                message_id=hit.get("message_id"),
                workspace_id=hit.get("workspace_id"),
                channel_id=hit.get("channel_id"),
                user_id=hit.get("user_id"),
                text=hit.get("text"),
                ts=ts_val,
                topics=hit.get("topics", []),
                semantic_score=semantic_score,
                recency_score=recency_score,
                final_score=final_score,
            )
        )

    # Sort by final_score descending and truncate to top_k
    scored_results.sort(key=lambda r: r.final_score, reverse=True)
    top_results = scored_results[: req.top_k]

    logger.info("Returning %d ranked results", len(top_results))
    return SearchResponse(results=top_results)


@app.post("/tools/search_similar", response_model=SearchResponse)
def tool_search_similar(req: SearchRequest):
    """
    MCP Tool: search_similar

    Perform a semantic search in Weaviate for messages relevant to the query/topics,
    restricted to a workspace and timeframe, and re-ranked by recency.

    The final_score is:
        (1 - recency_weight) * semantic_score + recency_weight * recency_score
    where semantic_score and recency_score are both in [0, 1].
    """
    if not req.query and not req.topics:
        raise HTTPException(
            status_code=400,
            detail="Either 'query' or 'topics' must be provided.",
        )

    now_ts = time.time()
    min_ts = now_ts - req.timeframe_days * 86400

    where_filter = _build_where_filter(req.workspace_id, min_ts)

    # Concepts for nearText
    concepts: List[str] = []
    if req.query:
        concepts.append(req.query)
    if req.topics:
        concepts.extend(req.topics)

    near_text: Dict[str, Any] = {
        "concepts": concepts,
    }

    # We fetch somewhat more results than top_k, then apply additional filtering
    # and re-ranking in Python.
    raw_limit = min(req.top_k * 3, 200)

    try:
        gql_response = (
            weaviate_client.query
            .get(
                WEAVIATE_CLASS_NAME,
                [
                    "message_id",
                    "workspace_id",
                    "channel_id",
                    "user_id",
                    "text",
                    "ts",
                    "topics",
                ],
            )
            .with_where(where_filter)
            .with_near_text(near_text)
            .with_limit(raw_limit)
            .with_additional(["id", "certainty", "distance"])
            .do()
        )
    except WeaviateBaseError as e:
        logger.error("Weaviate query error: %s", e)
        raise HTTPException(status_code=500, detail=f"Weaviate query error: {e}")

    hits = (
        gql_response
        .get("data", {})
        .get("Get", {})
        .get(WEAVIATE_CLASS_NAME, [])
    )

    logger.info("Weaviate returned %d raw hits", len(hits))

    scored_results: List[SearchResultItem] = []

    for hit in hits:
        additional = hit.get("_additional", {})
        semantic_score = _extract_semantic_score(additional)
        if semantic_score < req.min_score:
            continue

        ts_val = float(hit.get("ts", 0.0))
        recency_score = _compute_recency_score(ts_val, min_ts, now_ts)

        final_score = (
            (1.0 - req.recency_weight) * semantic_score
            + req.recency_weight * recency_score
        )

        scored_results.append(
            SearchResultItem(
                message_id=hit.get("message_id"),
                workspace_id=hit.get("workspace_id"),
                channel_id=hit.get("channel_id"),
                user_id=hit.get("user_id"),
                text=hit.get("text"),
                ts=ts_val,
                topics=hit.get("topics", []),
                semantic_score=semantic_score,
                recency_score=recency_score,
                final_score=final_score,
            )
        )

    # Sort by final_score descending and truncate to top_k
    scored_results.sort(key=lambda r: r.final_score, reverse=True)
    top_results = scored_results[: req.top_k]

    logger.info("Returning %d ranked results", len(top_results))
    return SearchResponse(results=top_results)


# ------------------------------------------------------------
# Dev entrypoint
# ------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    from vector_db import get_weaviate_client

    client = get_weaviate_client()
    collection = client.collections.get(WEAVIATE_CLASS_NAME)

    uvicorn.run(
        "semantic_search_mcp_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "6060")),
        reload=True,
    )
