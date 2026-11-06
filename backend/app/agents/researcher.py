"""
ResearchMind AI – Researcher Agent
====================================
The Researcher Agent searches the internet using Tavily for each
research question and collects real, verifiable sources.

Responsibilities:
  1. Use Tavily Search API to search per research question.
  2. Collect title, URL, domain, excerpt, published date, retrieved date.
  3. Remove duplicate sources by URL.
  4. Handle search failures and rate limits gracefully.
  5. Return a list of validated ResearchSource objects.

Design notes:
  - Never invent sources or URLs.
  - Sources with duplicate URLs are marked as duplicates and excluded.
  - Each source is linked to its research question via question_id.
  - Raises ResearcherError on unrecoverable failures.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.schemas.research import ResearchPlan, ResearchSource
from app.utils.exceptions import ConfigurationError, ResearcherError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Results per query based on depth
DEPTH_RESULTS_MAP = {
    "quick": 3,
    "standard": 5,
    "comprehensive": 8,
}


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def _url_fingerprint(url: str) -> str:
    """Create a normalized fingerprint for deduplication."""
    # Normalize: lowercase, strip trailing slash
    normalized = url.lower().rstrip("/")
    # Remove common tracking params by hashing the normalized URL
    return hashlib.md5(normalized.encode()).hexdigest()


def _parse_tavily_result(result: dict, question_id: str) -> ResearchSource | None:
    """
    Convert a single Tavily result dict into a ResearchSource.

    Returns None if the result is missing a URL (invalid).
    """
    url = result.get("url", "").strip()
    if not url:
        return None

    title = result.get("title", "No title").strip()
    content = result.get("content", "").strip()
    # Tavily returns 'published_date' in some results
    published_date = result.get("published_date") or result.get("publishedDate")

    return ResearchSource(
        question_id=question_id,
        title=title or url,
        url=url,
        domain=_extract_domain(url),
        excerpt=content[:1500] if content else "",  # Limit excerpt length
        published_date=str(published_date) if published_date else None,
        retrieved_at=datetime.now(timezone.utc),
        relevance_score=result.get("score"),
    )


class ResearcherAgent:
    """
    Researcher Agent – searches the internet for each research question.

    Uses Tavily Search API to retrieve real, verifiable sources.
    Deduplicates results across questions.

    Usage:
        agent = ResearcherAgent()
        sources = await agent.research(plan)
    """

    def __init__(self) -> None:
        if not settings.is_tavily_configured:
            raise ConfigurationError(
                "TAVILY_API_KEY is not configured. "
                "Please add your Tavily API key to the .env file. "
                "Get it free at: https://tavily.com"
            )

        try:
            from tavily import TavilyClient  # type: ignore[import]
            self._client = TavilyClient(api_key=settings.tavily_api_key)
        except ImportError as e:
            raise ConfigurationError(
                f"tavily-python package is not installed: {e}. "
                "Run: pip install tavily-python"
            )

        logger.info("researcher_agent_initialized")

    @retry(
        retry=retry_if_exception_type(ResearcherError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    def _search_query(self, query: str, max_results: int) -> list[dict]:
        """
        Execute a single Tavily search query.

        Returns list of raw result dicts. Retries on transient errors.
        """
        try:
            response = self._client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_raw_content=False,
            )
            return response.get("results", [])
        except Exception as e:
            error_msg = str(e)
            logger.warning("tavily_search_error", query=query[:80], error=error_msg)

            if "rate" in error_msg.lower() or "429" in error_msg:
                raise ResearcherError(
                    "Tavily rate limit reached. Please wait a moment.",
                    details={"query": query},
                )
            if "api key" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                raise ResearcherError(
                    "Tavily API key is invalid or expired.",
                    details={"query": query},
                )
            # Non-retryable errors: log and return empty
            logger.error("tavily_search_failed", query=query[:80], error=error_msg)
            return []

    async def research(
        self,
        plan: ResearchPlan,
        max_results_per_query: int | None = None,
    ) -> list[ResearchSource]:
        """
        Run searches for all research questions in the plan.

        Args:
            plan: The approved ResearchPlan.
            max_results_per_query: Override number of results per query.

        Returns:
            List of deduplicated ResearchSource objects.
        """
        # Determine results per query
        results_per_query = max_results_per_query or DEPTH_RESULTS_MAP.get(
            plan.depth.value, 5
        )

        all_sources: list[ResearchSource] = []
        seen_fingerprints: set[str] = set()
        total_duplicates = 0

        logger.info(
            "researcher_starting",
            question_count=len(plan.research_questions),
            results_per_query=results_per_query,
        )

        for question in plan.research_questions:
            question_sources: list[ResearchSource] = []

            for query in question.search_queries:
                logger.debug(
                    "searching_query",
                    question_id=question.id,
                    query=query[:80],
                )

                raw_results = self._search_query(query, results_per_query)

                for raw in raw_results:
                    source = _parse_tavily_result(raw, question.id)
                    if source is None:
                        continue

                    fingerprint = _url_fingerprint(source.url)
                    if fingerprint in seen_fingerprints:
                        source.is_duplicate = True
                        total_duplicates += 1
                        logger.debug("duplicate_source_skipped", url=source.url[:80])
                        continue

                    seen_fingerprints.add(fingerprint)
                    question_sources.append(source)

            logger.info(
                "question_researched",
                question_id=question.id,
                sources_found=len(question_sources),
            )
            all_sources.extend(question_sources)

        logger.info(
            "researcher_complete",
            total_sources=len(all_sources),
            total_duplicates=total_duplicates,
        )

        return all_sources
