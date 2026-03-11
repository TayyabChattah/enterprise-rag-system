from pgvector.django import CosineDistance # You must add this import
from documents.models import DocumentChunk
from .embedings import generate_embedding

def search_similar_chunks(query: str, organization_id, limit=5):
    query_embedding = generate_embedding(query)

    if query_embedding is None:
        return []

    # Use CosineDistance to wrap the embedding list
    results = (
        DocumentChunk.objects
        .filter(organization_id=organization_id)
        .order_by(CosineDistance("embedding", query_embedding))[:limit]
    )

    return results