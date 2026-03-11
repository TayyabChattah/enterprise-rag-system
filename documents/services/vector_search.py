from pgvector.django import CosineDistance

from documents.models import DocumentChunk
from .embedings import generate_embedding


def search_similar_chunks(query: str, organization_id, limit=5):
    query_embedding = generate_embedding(query, is_query=True)

    if query_embedding is None:
        return []

    return (
        DocumentChunk.objects.filter(
            organization_id=organization_id,
            is_active=True,
            embedding__isnull=False,
        )
        .order_by(CosineDistance("embedding", query_embedding))[:limit]
    )
