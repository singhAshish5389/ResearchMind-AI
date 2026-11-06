"""
ResearchMind AI – Auth Pydantic Schemas
=========================================
Request and response models for user authentication endpoints.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr = Field(..., description="User's email address.")
    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username (3–50 chars)."
    )
    password: str = Field(
        ..., min_length=8, max_length=100, description="Password (minimum 8 characters)."
    )

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Allow letters, numbers, underscores, hyphens only."""
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens."
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Require at least one letter and one digit."""
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not has_letter or not has_digit:
            raise ValueError("Password must contain at least one letter and one digit.")
        return v


class UserLoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(..., description="Account password.")


class UserResponse(BaseModel):
    """Public user data returned by the API (never includes password)."""

    id: str
    email: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response returned on successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class PasswordChangeRequest(BaseModel):
    """Request body for changing a password."""

    current_password: str = Field(..., description="The user's current password.")
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not has_letter or not has_digit:
            raise ValueError("Password must contain at least one letter and one digit.")
        return v
