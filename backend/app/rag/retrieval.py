"""
ResearchMind AI – RAG Retrieval
==================================
Semantic retrieval from Qdrant vector store.

Retrieves the most relevant document chunks for a query,
filtered by user and optional document IDs.
"""

from __future__ import annotations

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TOP_K = 5
MAX_TOP_K = 20


class RetrievedChunk:
    """A document chunk retrieved from Qdrant."""

    def __init__(self, payload: dict, score: float):
        self.chunk_id: str = payload.get("id", "")
        self.document_id: str = payload.get("document_id", "")
        self.filename: str = payload.get("filename", "")
        self.page_number: int = payload.get("page_number", 1)
        self.chunk_index: int = payload.get("chunk_index", 0)
        self.text: str = payload.get("text", "")
        self.score: float = score

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "score": self.score,
        }


def _get_qdrant_client():
    """Get Qdrant client."""
    if not settings.is_qdrant_configured:
        raise RuntimeError("Qdrant is not configured. Set QDRANT_URL in .env.")
    try:
        from qdrant_client import QdrantClient  # type: ignore[import]
    except ImportError:
        raise ImportError("qdrant-client not installed. Run: pip install qdrant-client")

    kwargs = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key
    return QdrantClient(**kwargs)


async def retrieve(
    query: str,
    user_id: str,
    document_ids: list[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = 0.4,
) -> list[RetrievedChunk]:
    """
    Retrieve the most relevant document chunks for a query.

    Args:
        query: The search query text.
        user_id: Filter to only this user's documents.
        document_ids: Optional list of specific document IDs to search within.
        top_k: Number of top results to return.
        score_threshold: Minimum similarity score (0–1).

    Returns:
        List of RetrievedChunk sorted by relevance (highest score first).
    """
    from app.rag.embeddings import embed_query
    from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny  # type: ignore[import]

    top_k = min(top_k, MAX_TOP_K)

    logger.debug("rag_retrieving", query=query[:80], user_id=user_id, top_k=top_k)

    # Build filter
    must_conditions = [
        FieldCondition(key="user_id", match=MatchValue(value=user_id))
    ]
    if document_ids:
        must_conditions.append(
            FieldCondition(key="document_id", match=MatchAny(any=document_ids))
        )

    query_filter = Filter(must=must_conditions)

    # Embed query
    query_vector = embed_query(query)

    # Search Qdrant
    client = _get_qdrant_client()
    collection = settings.qdrant_collection

    results = client.search(
        collection_name=collection,
        query_vector=query_vector.tolist(),
        query_filter=query_filter,
        limit=top_k,
        score_threshold=score_threshold,
    )

    chunks = [
        RetrievedChunk(payload=hit.payload or {}, score=hit.score)
        for hit in results
    ]

    logger.debug("rag_retrieved", result_count=len(chunks))
    return chunks


async def retrieve_for_research(
    research_questions: list[str],
    user_id: str,
    document_ids: list[str] | None = None,
    top_k_per_question: int = 3,
) -> list[dict]:
    """
    Retrieve relevant chunks for a list of research questions.

    Args:
        research_questions: List of research question strings.
        user_id: User ID for ownership filtering.
        document_ids: Optional specific document IDs.
        top_k_per_question: Results per question.

    Returns:
        List of chunk dicts with deduplicated results.
    """
    seen_chunk_ids: set[str] = set()
    all_chunks: list[dict] = []

    for question in research_questions:
        chunks = await retrieve(
            query=question,
            user_id=user_id,
            document_ids=document_ids,
            top_k=top_k_per_question,
        )
        for chunk in chunks:
            chunk_key = f"{chunk.document_id}:{chunk.page_number}:{chunk.chunk_index}"
            if chunk_key not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_key)
                all_chunks.append(chunk.to_dict())

    logger.info("rag_research_retrieval_complete", chunk_count=len(all_chunks))
    return all_chunks
