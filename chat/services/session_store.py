import json
import os
from typing import Any

import redis


def _redis_client() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://redis:6379/1")
    return redis.Redis.from_url(url, decode_responses=True)


def session_key(*, organization_id, user_id, session_id: str) -> str:
    return f"rag_chat:{organization_id}:{user_id}:{session_id}"


def load_messages(*, organization_id, user_id, session_id: str) -> list[dict[str, Any]]:
    r = _redis_client()
    raw = r.get(session_key(organization_id=organization_id, user_id=user_id, session_id=session_id))
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def save_messages(
    *,
    organization_id,
    user_id,
    session_id: str,
    messages: list[dict[str, Any]],
    ttl_seconds: int,
) -> None:
    r = _redis_client()
    key = session_key(organization_id=organization_id, user_id=user_id, session_id=session_id)
    r.set(key, json.dumps(messages))
    r.expire(key, ttl_seconds)


def delete_session(*, organization_id, user_id, session_id: str) -> None:
    r = _redis_client()
    r.delete(session_key(organization_id=organization_id, user_id=user_id, session_id=session_id))
