from celery import shared_task
from django.db import transaction

from .models import Document, DocumentChunk
from .services.document_processor import extract_text_from_file, create_chunks
from .services.embedings import generate_embedding


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id):

    document = None

    try:
        document = Document.objects.get(id=document_id)

        # mark processing
        document.status = "processing"
        document.save(update_fields=["status"])

        file_path = document.file.path

        # 1️⃣ extract text
        text = extract_text_from_file(file_path)

        if not text:
            raise ValueError("No text extracted from document")

        # 2️⃣ create chunks
        chunks = create_chunks(text)

        chunk_objects = []

        # 3️⃣ generate embeddings for each chunk
        for index, chunk in enumerate(chunks):

            embedding = generate_embedding(chunk)
            if embedding is None:
                continue

            chunk_objects.append(
                DocumentChunk(
                    document=document,
                    organization=document.organization,
                    content=chunk,
                    embedding=embedding,
                    index=index
                )
            )

        # 4️⃣ bulk insert chunks
        with transaction.atomic():
            DocumentChunk.objects.bulk_create(chunk_objects)

        # 5️⃣ mark document processed
        document.status = "processed"
        document.save(update_fields=["status"])

        return f"{len(chunks)} chunks created with embeddings"

    except Exception as exc:

        if document:
            document.status = "error"
            document.save(update_fields=["status"])

        raise self.retry(exc=exc, countdown=10)
    