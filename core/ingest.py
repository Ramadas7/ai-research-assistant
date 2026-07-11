import os
from core.document_loader import extract_pdf_content
from core.chunker import chunk_document
from core import vector_store
from database.models import create_document


def ingest_pdf(filepath: str, filename: str) -> dict:
    """
    Full pipeline for one uploaded PDF:
      extract (text/table/image) -> chunk -> embed + store -> record in SQLite
    Returns the document record that gets shown in the UI.
    """
    extracted = extract_pdf_content(filepath)
    chunks = chunk_document(extracted["chunks"])

    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)

    doc_id = create_document(
        filename=filename,
        filepath=filepath,
        size_mb=size_mb,
        num_pages=extracted["num_pages"],
        num_chunks=len(chunks),
        has_tables=extracted["has_tables"],
        has_images=extracted["has_images"],
    )

    vector_store.add_chunks(doc_id, filename, chunks)

    return {
        "id": doc_id,
        "filename": filename,
        "size_mb": size_mb,
        "num_pages": extracted["num_pages"],
        "num_chunks": len(chunks),
        "has_tables": extracted["has_tables"],
        "has_images": extracted["has_images"],
    }
