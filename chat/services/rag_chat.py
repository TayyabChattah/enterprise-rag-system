import logging
import os
from typing import Any

from google import genai

from documents.services.vector_search import search_similar_chunks

logger = logging.getLogger(__name__)


def _genai_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()


_client = _genai_client()


def _normalize_model_name(name: str) -> str:
    name = (name or "").strip()
    if name.startswith("models/"):
        return name[len("models/") :]
    return name


def list_generate_content_models() -> list[dict[str, Any]]:
    """List models that support generateContent (best-effort)."""

    models_api = getattr(_client, "models", None)
    if not models_api:
        return []

    list_fn = getattr(models_api, "list", None)
    if not callable(list_fn):
        list_fn = getattr(models_api, "list_models", None)

    if not callable(list_fn):
        return []

    out: list[dict[str, Any]] = []

    try:
        for m in list_fn():
            name = getattr(m, "name", None) or getattr(m, "model", None) or str(m)
            supported = getattr(m, "supported_generation_methods", None)
            if supported is None:
                supported = getattr(m, "supported_methods", None)
            supported_list = list(supported) if supported else []

            if any(str(x).lower() == "generatecontent" for x in supported_list):
                out.append({"name": name, "supported_generation_methods": supported_list})
    except Exception:
        logger.exception("GenAI list models failed")
        return []

    return out


def _build_context(chunks, max_chars_per_chunk: int = 1200) -> tuple[str, list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    context_parts: list[str] = []

    for chunk in chunks:
        content = (chunk.content or "")[:max_chars_per_chunk]
        sources.append(
            {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "index": int(getattr(chunk, "index", 0)),
                "preview": content[:200],
            }
        )
        context_parts.append(
            "\n".join(
                [
                    f"[Source doc={chunk.document_id} chunk_index={getattr(chunk, 'index', 0)}]",
                    content,
                ]
            )
        )

    return "\n\n".join(context_parts).strip(), sources


def _build_history(history: list[dict[str, Any]] | None, max_messages: int = 20) -> str:
    if not history or max_messages <= 0:
        return ""

    trimmed = history[-max_messages:]
    lines: list[str] = []
    for msg in trimmed:
        role = (msg.get("role", "") or "").strip()
        content = (msg.get("content", "") or "").strip()
        if not role or not content:
            continue
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines).strip()


def _try_generate(model_name: str, prompt: str) -> str:
    model_name = _normalize_model_name(model_name)
    resp = _client.models.generate_content(model=model_name, contents=prompt)
    text = getattr(resp, "text", None)
    return (text or str(resp)).strip()


def generate_rag_answer(
    *,
    query: str,
    organization_id,
    top_k: int = 5,
    history: list[dict[str, Any]] | None = None,
    history_max_messages: int = 20,
) -> tuple[str, list[dict[str, Any]]]:
    chunks = list(search_similar_chunks(query, organization_id=organization_id, limit=top_k))
    context, sources = _build_context(chunks)

    if not context:
        return "I couldn't find anything relevant in your knowledge base for that question.", []

    system_instructions = (
        "You are a helpful assistant for an enterprise knowledge base. "
        "Answer using ONLY the provided sources. "
        "If the sources do not contain the answer, say you don't know. "
        "Cite sources inline like [doc:<id>#<chunk_index>]."
    )

    chat_history = _build_history(history, max_messages=history_max_messages)

    prompt = (
        f"{system_instructions}\n\n"
        + (f"CHAT HISTORY:\n{chat_history}\n\n" if chat_history else "")
        + f"SOURCES:\n{context}\n\n"
        + f"QUESTION: {query}\n\n"
        + "ANSWER:"
    )

    preferred = _normalize_model_name(os.getenv("GENAI_CHAT_MODEL", ""))
    candidates: list[str] = [c for c in [preferred] if c]

    last_exc: Exception | None = None

    for model_name in candidates:
        try:
            return _try_generate(model_name, prompt), sources
        except Exception as exc:
            last_exc = exc
            logger.exception("GenAI generate_content failed (model=%s)", model_name)

    if os.getenv("DEBUG") == "1" and last_exc is not None:
        hint = " Use /api/chat/sessions/models/ to pick GENAI_CHAT_MODEL."
        return f"LLM generation failed: {last_exc.__class__.__name__}: {last_exc}.{hint}", sources

    fallback = (
        "I found relevant sources, but the chat model isn't configured/available right now. "
        "Here are the sources that match your question."
    )
    return fallback, sources
