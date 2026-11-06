"""
ResearchMind AI – Document Ingestion Pipeline
===============================================
Handles PDF/text upload, text extraction, chunking, embedding,
and storage in Qdrant vector database.

Pipeline:
    Document Upload → Text Extraction → Chunking → Embedding → Qdrant Storage
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import BinaryIO

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_CHUNK_SIZE = 512        # characters per chunk
DEFAULT_CHUNK_OVERLAP = 64      # character overlap between chunks
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def _extract_text_from_pdf(file_bytes: bytes) -> list[tuple[int, str]]:
    """
    Extract text from a PDF file, page by page.

    Returns:
        List of (page_number, text) tuples (1-indexed).
    """
    try:
        import fitz  # PyMuPDF  # type: ignore[import]
    except ImportError:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")

    pages = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        if text.strip():
            pages.append((page_num + 1, text.strip()))
    doc.close()
    return pages


def _extract_text_from_txt(file_bytes: bytes) -> list[tuple[int, str]]:
    """Extract text from plain text or markdown files."""
    text = file_bytes.decode("utf-8", errors="replace")
    return [(1, text)]


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: The text to split.
        chunk_size: Target character count per chunk.
        chunk_overlap: Characters to overlap between adjacent chunks.

    Returns:
        List of text chunks.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start = end - chunk_overlap

    return chunks


def _get_qdrant_client():
    """Get Qdrant client, raising if not configured."""
    if not settings.is_qdrant_configured:
        raise RuntimeError(
            "Qdrant is not configured. Set QDRANT_URL in your .env file."
        )
    try:
        from qdrant_client import QdrantClient  # type: ignore[import]
        from qdrant_client.http.models import Distance, VectorParams  # type: ignore[import]
    except ImportError:
        raise ImportError("qdrant-client not installed. Run: pip install qdrant-client")

    kwargs = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key

    client = QdrantClient(**kwargs)
    return client


def ensure_collection_exists(collection_name: str, vector_size: int) -> None:
    """
    Create the Qdrant collection if it doesn't exist.

    Args:
        collection_name: Qdrant collection name.
        vector_size: Embedding dimensionality.
    """
    from qdrant_client import QdrantClient  # type: ignore[import]
    from qdrant_client.http.models import Distance, VectorParams  # type: ignore[import]

    client = _get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]

    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("qdrant_collection_created", collection=collection_name, vector_size=vector_size)


async def ingest_document(
    file_bytes: bytes,
    filename: str,
    document_id: str,
    user_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> dict:
    """
    Ingest a document into the Qdrant vector store.

    Args:
        file_bytes: Raw file bytes.
        filename: Original filename (used to determine file type).
        document_id: Unique ID for this document.
        user_id: ID of the user who uploaded the document.
        chunk_size: Characters per chunk.
        chunk_overlap: Overlap between chunks.

    Returns:
        Dict with ingestion summary: chunk_count, document_id.

    Raises:
        ValueError: If file type is unsupported.
        RuntimeError: If Qdrant is not configured.
    """
    from app.rag.embeddings import embed_texts, get_embedding_dimension

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    logger.info("document_ingestion_start", document_id=document_id, filename=filename)

    # 1. Extract text
    if suffix == ".pdf":
        pages = _extract_text_from_pdf(file_bytes)
    else:
        pages = _extract_text_from_txt(file_bytes)

    if not pages:
        raise ValueError(f"Could not extract any text from {filename}.")

    # 2. Chunk text per page
    all_chunks: list[dict] = []
    chunk_index = 0

    for page_num, page_text in pages:
        chunks = chunk_text(page_text, chunk_size, chunk_overlap)
        for chunk_text_content in chunks:
            all_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "user_id": user_id,
                "filename": filename,
                "page_number": page_num,
                "chunk_index": chunk_index,
                "text": chunk_text_content,
            })
            chunk_index += 1

    if not all_chunks:
        raise ValueError(f"No text chunks produced from {filename}.")

    logger.info("document_chunked", document_id=document_id, chunk_count=len(all_chunks))

    # 3. Generate embeddings
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)
    vector_dim = embeddings.shape[1] if len(embeddings.shape) > 1 else embeddings.shape[0]

    # 4. Ensure Qdrant collection exists
    collection = settings.qdrant_collection
    ensure_collection_exists(collection, vector_dim)

    # 5. Store in Qdrant
    from qdrant_client.models import PointStruct  # type: ignore[import]

    client = _get_qdrant_client()
    points = [
        PointStruct(
            id=chunk["chunk_id"],
            vector=embeddings[i].tolist(),
            payload={
                "document_id": chunk["document_id"],
                "user_id": chunk["user_id"],
                "filename": chunk["filename"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
            },
        )
        for i, chunk in enumerate(all_chunks)
    ]

    client.upsert(collection_name=collection, points=points)

    logger.info(
        "document_ingestion_complete",
        document_id=document_id,
        chunk_count=len(all_chunks),
    )

    return {
        "document_id": document_id,
        "chunk_count": len(all_chunks),
        "page_count": len(pages),
    }


async def delete_document(document_id: str, user_id: str) -> None:
    """
    Remove all Qdrant vectors for a document owned by user_id.

    Args:
        document_id: The document to delete.
        user_id: Must match the user who uploaded (ownership check).
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore[import]

    client = _get_qdrant_client()
    collection = settings.qdrant_collection

    client.delete(
        collection_name=collection,
        points_selector=Filter(
            must=[
                FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            ]
        ),
    )
    logger.info("document_deleted_from_qdrant", document_id=document_id)
