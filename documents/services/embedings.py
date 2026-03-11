# services/embedings.py

from google import genai

client = genai.Client()  # Assumes GEMINI_API_KEY is set in environment variables


def generate_embedding(text: str, is_query: bool = False):
    task_type = "retrieval_query" if is_query else "retrieval_document"
    
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config={
            "task_type": task_type,
            "output_dimensionality": 768
        }
    )
    return response.embeddings[0].values

