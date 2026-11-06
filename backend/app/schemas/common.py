"""
ResearchMind AI – Common Pydantic Schemas
=========================================
Shared response models and base types used across multiple API endpoints.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """
    Generic API success response wrapper.

    Every successful API response follows this envelope so the frontend
    can handle responses uniformly.

    Example:
        {
            "success": true,
            "data": { ... },
            "message": "Research plan created successfully."
        }
    """

    success: bool = True
    data: T
    message: str = "OK"


class ErrorResponse(BaseModel):
    """
    Standard API error response body.

    Returned by exception handlers for all application errors.
    """

    success: bool = False
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response wrapper.

    Used for endpoints that return lists of items (e.g., research history).
    """

    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
            has_prev=page > 1,
        )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str
    services: dict[str, str] = Field(default_factory=dict)
