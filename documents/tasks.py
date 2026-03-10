from celery import shared_task
from django.db import transaction

from .models import Document, DocumentChunk
from .services.document_processor import extract_text_from_file, create_chunks


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id):

    try:
        document = Document.objects.get(id=document_id)

        # update status
        document.status = "processing"
        document.save(update_fields=["status"])

        file_path = document.file.path

        # extract raw text
        text = extract_text_from_file(file_path)

        if not text:
            raise ValueError("No text extracted")

        # create chunks
        chunks = create_chunks(text)

        chunk_objects = []

        for chunk in chunks:
            chunk_objects.append(
                DocumentChunk(
                    document=document,
                    content=chunk,
                    organization=document.organization,
                    index=chunks.index(chunk)
                )
            )

        # bulk insert for performance
        with transaction.atomic():
            DocumentChunk.objects.bulk_create(chunk_objects)

        # mark document as processed
        document.status = "processed"
        document.save(update_fields=["status"])

        return f"{len(chunks)} chunks created"

    except Exception as exc:

        document = Document.objects.filter(id=document_id).first()

        if document:
            document.status = "error"
            document.save(update_fields=["status"])

        raise self.retry(exc=exc, countdown=10)
    
