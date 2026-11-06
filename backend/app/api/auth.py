"""
ResearchMind AI – Auth API Router
====================================
User registration, login, logout, and profile endpoints.

Endpoints:
  POST /api/auth/register   – Register a new user account
  POST /api/auth/login      – Login and get access token
  POST /api/auth/logout     – Logout (client-side token invalidation)
  GET  /api/auth/me         – Get current user profile
  PUT  /api/auth/me/password – Change password
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.database.models import User
from app.database.session import get_db
from app.schemas.auth import (
    PasswordChangeRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a New Account",
    description="Create a new user account. Returns an access token on success.",
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account."""
    # Check email uniqueness
    existing_email = await db.execute(select(User).where(User.email == request.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Check username uniqueness
    existing_username = await db.execute(select(User).where(User.username == request.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken. Please choose another.",
        )

    # Create user with hashed password
    hashed = hash_password(request.password)
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed,
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()  # Get the generated ID

    logger.info("user_registered", user_id=user.id, username=user.username)

    # Generate access token
    token = create_access_token(user_id=user.id, email=user.email)
    expires_in = settings.access_token_expire_minutes * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password. Returns a JWT access token.",
)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return JWT token."""
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    # Use same error message for both "user not found" and "wrong password"
    # to prevent user enumeration attacks
    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        logger.warning("login_user_not_found", email=request.email)
        raise invalid_credentials_error

    if not verify_password(request.password, user.hashed_password):
        logger.warning("login_wrong_password", user_id=user.id)
        raise invalid_credentials_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated.",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    logger.info("user_logged_in", user_id=user.id, username=user.username)

    token = create_access_token(user_id=user.id, email=user.email)
    expires_in = settings.access_token_expire_minutes * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    summary="Logout",
    description=(
        "Logout the current user. "
        "JWT tokens are stateless — this endpoint instructs the client to discard the token. "
        "For token blacklisting, integrate Redis (future feature)."
    ),
)
async def logout(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Logout the current user."""
    logger.info("user_logged_out", user_id=current_user.id)
    return {"message": "Logged out successfully. Please discard your access token."}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Return the profile of the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me/password",
    summary="Change Password",
    description="Change the current user's password.",
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the user's password."""
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    # Update with new hash
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    user.hashed_password = hash_password(request.new_password)

    logger.info("user_password_changed", user_id=current_user.id)
    return {"message": "Password changed successfully."}
