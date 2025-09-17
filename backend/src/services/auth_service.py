"""
JWT authentication service.

Provides JWT token generation, validation, and user authentication
for the IoT telemetry dashboard API.
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.user import UserResponse, UserRole
from ..services.user_service import get_user_service, UserService


logger = logging.getLogger(__name__)


class AuthService:
    """Service class for JWT authentication operations."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        user_service: Optional[UserService] = None
    ):
        """
        Initialize authentication service.

        Args:
            secret_key: JWT signing secret key
            algorithm: JWT signing algorithm
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_days: Refresh token expiration in days
            user_service: User service for authentication
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.user_service = user_service

        # Token revocation store (in production, use Redis or database)
        self._revoked_tokens: set = set()

    async def authenticate_user(self, email: str, password: str) -> Optional[UserResponse]:
        """
        Authenticate user with email and password.

        Args:
            email: User email address
            password: Plain text password

        Returns:
            User if authentication successful, None otherwise

        Raises:
            HTTPException: If authentication service fails
        """
        try:
            if not self.user_service:
                raise HTTPException(
                    status_code=500,
                    detail="User service not available"
                )

            # Get user by email
            user = await self.user_service.get_user_by_email(email)
            if not user:
                return None

            # Verify password
            password_valid = await self.user_service.verify_password(user.id, password)
            if not password_valid:
                return None

            logger.info(f"User authenticated: {email}")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error for {email}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Authentication service error"
            )

    def create_access_token(
        self,
        user: UserResponse,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token for user.

        Args:
            user: User to create token for
            expires_delta: Optional custom expiration time

        Returns:
            JWT access token string

        Raises:
            HTTPException: If token creation fails
        """
        try:
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

            # Create token payload
            payload = {
                "sub": str(user.id),  # Subject (user ID)
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "organization_permissions": [str(org_id) for org_id in user.organization_permissions],
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access"
            }

            # Create and return token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created access token for user {user.email}")
            return token

        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create access token"
            )

    def create_refresh_token(
        self,
        user: UserResponse,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token for user.

        Args:
            user: User to create token for
            expires_delta: Optional custom expiration time

        Returns:
            JWT refresh token string

        Raises:
            HTTPException: If token creation fails
        """
        try:
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

            # Create token payload (minimal for refresh tokens)
            payload = {
                "sub": str(user.id),
                "email": user.email,
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh"
            }

            # Create and return token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created refresh token for user {user.email}")
            return token

        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create refresh token"
            )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Check if token is revoked
            if token in self._revoked_tokens:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )

            # Decode and verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Validate token type
            token_type = payload.get("type")
            if not token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )

    async def get_current_user(self, token: str) -> UserResponse:
        """
        Get current user from JWT token.

        Args:
            token: JWT access token

        Returns:
            Current user information

        Raises:
            HTTPException: If token is invalid or user not found
        """
        try:
            # Verify token
            payload = self.verify_token(token)

            # Validate token type
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            # Get user ID from token
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )

            # Get user from database
            if not self.user_service:
                raise HTTPException(
                    status_code=500,
                    detail="User service not available"
                )

            user = await self.user_service.get_user(UUID(user_id_str))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get current user error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get current user"
            )

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token

        Raises:
            HTTPException: If refresh token is invalid
        """
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token)

            # Validate token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            # Get user from token
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )

            # Get current user data
            if not self.user_service:
                raise HTTPException(
                    status_code=500,
                    detail="User service not available"
                )

            user = await self.user_service.get_user(UUID(user_id_str))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            # Create new access token
            access_token = self.create_access_token(user)
            logger.info(f"Refreshed access token for user {user.email}")
            return access_token

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh token"
            )

    def revoke_token(self, token: str) -> None:
        """
        Revoke JWT token.

        Args:
            token: JWT token to revoke
        """
        try:
            # Add token to revocation list
            self._revoked_tokens.add(token)
            logger.debug("Token revoked")

        except Exception as e:
            logger.error(f"Token revocation error: {e}")

    def check_permission(
        self,
        user: UserResponse,
        required_role: Optional[UserRole] = None,
        required_organization: Optional[UUID] = None
    ) -> bool:
        """
        Check if user has required permissions.

        Args:
            user: User to check permissions for
            required_role: Optional minimum required role
            required_organization: Optional required organization access

        Returns:
            True if user has permission, False otherwise
        """
        # Check role permission
        if required_role:
            role_hierarchy = {
                UserRole.VIEWER: 1,
                UserRole.OPERATOR: 2,
                UserRole.ADMIN: 3
            }

            user_level = role_hierarchy.get(user.role, 0)
            required_level = role_hierarchy.get(required_role, 999)

            if user_level < required_level:
                return False

        # Check organization permission
        if required_organization:
            # Admins have access to all organizations
            if user.role == UserRole.ADMIN:
                return True

            # Check if user has explicit permission for organization
            if required_organization not in user.organization_permissions:
                return False

        return True

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Complete login process with token generation.

        Args:
            email: User email
            password: User password

        Returns:
            Dictionary with tokens and user info

        Raises:
            HTTPException: If login fails
        """
        try:
            # Authenticate user
            user = await self.authenticate_user(email, password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Create tokens
            access_token = self.create_access_token(user)
            refresh_token = self.create_refresh_token(user)

            # Return login response
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value,
                    "organization_permissions": [str(org_id) for org_id in user.organization_permissions]
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Login service error"
            )


# Global service instance
auth_service: Optional[AuthService] = None

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_auth_service(
    user_service: UserService = Depends(get_user_service)
) -> AuthService:
    """
    Dependency function to get authentication service instance.

    Args:
        user_service: User service

    Returns:
        Authentication service instance

    Raises:
        HTTPException: If service not initialized
    """
    global auth_service

    if auth_service is None:
        raise HTTPException(
            status_code=500,
            detail="Authentication service not initialized"
        )

    # Inject user service
    auth_service.user_service = user_service
    return auth_service


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Dependency to get current authenticated user.

    Args:
        credentials: HTTP authorization credentials
        auth_service: Authentication service

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return await auth_service.get_current_user(credentials.credentials)


async def get_current_admin_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency to get current user with admin role requirement.

    Args:
        current_user: Current authenticated user

    Returns:
        Current admin user

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


def initialize_auth_service(
    secret_key: str,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7
) -> AuthService:
    """
    Initialize global authentication service instance.

    Args:
        secret_key: JWT signing secret key
        algorithm: JWT signing algorithm
        access_token_expire_minutes: Access token expiration in minutes
        refresh_token_expire_days: Refresh token expiration in days

    Returns:
        Initialized authentication service
    """
    global auth_service

    auth_service = AuthService(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days
    )

    return auth_service