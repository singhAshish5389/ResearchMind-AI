"""
ResearchMind AI – JWT Token Utilities
========================================
Creates and validates JWT access tokens for user authentication.

Tokens contain:
  - sub: user ID
  - email: user email
  - exp: expiration timestamp
  - type: "access"
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.utils.exceptions import AuthenticationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _get_jose():
    """Import python-jose, raising clearly if not installed."""
    try:
        from jose import jwt, JWTError  # type: ignore[import]
        return jwt, JWTError
    except ImportError:
        raise ImportError(
            "python-jose is not installed. Run: pip install python-jose[cryptography]"
        )


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token for the given user.

    Args:
        user_id: The user's database ID.
        email: The user's email address.
        expires_delta: Custom expiry. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        A signed JWT token string.
    """
    jwt, _ = _get_jose()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_refresh_token(user_id: str, email: str) -> str:
    """Create a longer-lived refresh token."""
    return create_access_token(
        user_id=user_id,
        email=email,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        The decoded payload dict.

    Raises:
        AuthenticationError: If token is invalid, expired, or malformed.
    """
    jwt, JWTError = _get_jose()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload

    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        raise AuthenticationError(
            "Invalid or expired token. Please log in again.",
            details={"jwt_error": str(e)},
        )


def get_user_id_from_token(token: str) -> str:
    """
    Extract the user ID from a valid JWT token.

    Args:
        token: JWT token string.

    Returns:
        The user ID string.

    Raises:
        AuthenticationError: If token is invalid or missing sub claim.
    """
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token missing user ID claim.")
    return str(user_id)
