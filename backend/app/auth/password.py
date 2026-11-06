"""
ResearchMind AI – Password Hashing
======================================
Secure password hashing using bcrypt via passlib.

Never store plaintext passwords. Always hash on registration
and verify on login using this module.
"""

from __future__ import annotations

try:
    from passlib.context import CryptContext  # type: ignore[import]
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _passlib_available = True
except ImportError:
    _passlib_available = False
    _pwd_context = None  # type: ignore[assignment]


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        plain_password: The user's plaintext password.

    Returns:
        A bcrypt hashed password string safe to store in the database.

    Raises:
        ImportError: If passlib is not installed.
    """
    if not _passlib_available or _pwd_context is None:
        raise ImportError(
            "passlib is not installed. Run: pip install passlib[bcrypt]"
        )
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: The password the user entered.
        hashed_password: The hashed password from the database.

    Returns:
        True if the password matches, False otherwise.
    """
    if not _passlib_available or _pwd_context is None:
        raise ImportError(
            "passlib is not installed. Run: pip install passlib[bcrypt]"
        )
    return _pwd_context.verify(plain_password, hashed_password)
