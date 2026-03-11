import logging
import os

from google import genai

logger = logging.getLogger(__name__)


def _genai_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()


_client = _genai_client()


def generate_embedding(text: str, is_query: bool = False):
    task_type = "retrieval_query" if is_query else "retrieval_document"

    try:
        response = _client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={
                "task_type": task_type,
                "output_dimensionality": 768,
            },
        )
        return response.embeddings[0].values
    except Exception:
        logger.exception("GenAI embed_content failed")
        raise
