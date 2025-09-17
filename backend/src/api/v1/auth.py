"""
Authentication API endpoints.

Provides REST API endpoints for user authentication including
login, token refresh, logout, and user profile management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from ...models.user import UserResponse
from ...services.auth_service import get_auth_service, AuthService, security
from ...middleware.auth_middleware import require_viewer_role


logger = logging.getLogger(__name__)

# Create router for authentication
router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response model."""
    access_token: str
    token_type: str
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    current_password: str
    new_password: str


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user with email and password, returns JWT tokens."
)
async def login(
    login_request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """
    Authenticate user and return JWT tokens.

    Returns access token for API authentication and refresh token for token renewal.
    """
    try:
        login_result = await auth_service.login(
            email=login_request.email,
            password=login_request.password
        )

        logger.info(f"User logged in: {login_request.email}")
        return LoginResponse(**login_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {login_request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service error"
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token."
)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> RefreshTokenResponse:
    """
    Get new access token using refresh token.

    Use this endpoint to get a new access token when the current one expires.
    """
    try:
        new_access_token = await auth_service.refresh_access_token(
            refresh_request.refresh_token
        )

        logger.info("Access token refreshed")
        return RefreshTokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=auth_service.access_token_expire_minutes * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error"
        )


@router.post(
    "/logout",
    summary="User logout",
    description="Logout user and revoke current access token."
)
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user and revoke access token.

    Adds the current access token to the revocation list.
    """
    try:
        if credentials:
            # Revoke the current token
            auth_service.revoke_token(credentials.credentials)

        logger.info("User logged out")
        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service error"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get current authenticated user's profile information."
)
async def get_current_user_profile(
    current_user: UserResponse = Depends(require_viewer_role)
) -> UserResponse:
    """
    Get current user's profile information.

    Returns the authenticated user's profile data.
    """
    try:
        logger.info(f"Retrieved profile for user {current_user.email}")
        return current_user

    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.post(
    "/change-password",
    summary="Change password",
    description="Change current user's password."
)
async def change_password(
    password_request: ChangePasswordRequest,
    current_user: UserResponse = Depends(require_viewer_role),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change current user's password.

    Requires current password for verification and new password.
    """
    try:
        # Verify current password
        if not auth_service.user_service:
            raise HTTPException(
                status_code=500,
                detail="User service not available"
            )

        password_valid = await auth_service.user_service.verify_password(
            current_user.id, password_request.current_password
        )

        if not password_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Validate new password
        if len(password_request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )

        if password_request.current_password == password_request.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )

        # Change password
        success = await auth_service.user_service.change_password(
            current_user.id, password_request.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )

        logger.info(f"Password changed for user {current_user.email}")
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change service error"
        )


@router.post(
    "/verify-token",
    summary="Verify token",
    description="Verify if current access token is valid."
)
async def verify_token(
    current_user: UserResponse = Depends(require_viewer_role)
):
    """
    Verify if current access token is valid.

    Returns user information if token is valid.
    """
    try:
        logger.info(f"Token verified for user {current_user.email}")
        return {
            "valid": True,
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "name": current_user.name,
                "role": current_user.role.value
            }
        }

    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification service error"
        )


@router.get(
    "/permissions",
    summary="Get user permissions",
    description="Get current user's role and organization permissions."
)
async def get_user_permissions(
    current_user: UserResponse = Depends(require_viewer_role)
):
    """
    Get current user's permissions.

    Returns role-based permissions and organization access list.
    """
    try:
        permissions = {
            "user_id": str(current_user.id),
            "role": current_user.role.value,
            "organization_permissions": [str(org_id) for org_id in current_user.organization_permissions],
            "capabilities": {
                "can_view": True,
                "can_operate": current_user.role.value in ["operator", "admin"],
                "can_admin": current_user.role.value == "admin"
            }
        }

        logger.info(f"Retrieved permissions for user {current_user.email}")
        return permissions

    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user permissions"
        )