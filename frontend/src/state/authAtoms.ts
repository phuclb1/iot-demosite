/**
 * Authentication state management using Jotai atoms.
 *
 * Manages user authentication, JWT tokens, permissions, and auth-related state
 * for the IoT dashboard application.
 */

import { atom } from 'jotai';
import { atomWithQuery } from 'jotai-tanstack-query';

// Types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'operator' | 'viewer';
  organization_permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

export interface UserPermissions {
  user_id: string;
  role: string;
  organization_permissions: string[];
  capabilities: {
    can_view: boolean;
    can_operate: boolean;
    can_admin: boolean;
  };
}

// Token management
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user_data';

// Base atoms
export const isAuthenticatedAtom = atom<boolean>(false);
export const authLoadingAtom = atom<boolean>(false);
export const authErrorAtom = atom<string | null>(null);
export const currentUserAtom = atom<User | null>(null);

// Token atoms
export const accessTokenAtom = atom<string | null>(
  () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(ACCESS_TOKEN_KEY);
    }
    return null;
  },
  (get, set, token: string | null) => {
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
      } else {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
      }
    }
  }
);

export const refreshTokenAtom = atom<string | null>(
  () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(REFRESH_TOKEN_KEY);
    }
    return null;
  },
  (get, set, token: string | null) => {
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, token);
      } else {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
      }
    }
  }
);

// User query atom
export const userQueryAtom = atomWithQuery((get) => {
  const accessToken = get(accessTokenAtom);
  const isAuthenticated = get(isAuthenticatedAtom);

  return {
    queryKey: ['current-user'],
    queryFn: async (): Promise<User> => {
      const response = await fetch('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch user profile: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: isAuthenticated && !!accessToken,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,
    retry: 1, // Don't retry auth failures too many times
  };
});

// User permissions query atom
export const userPermissionsQueryAtom = atomWithQuery((get) => {
  const accessToken = get(accessTokenAtom);
  const isAuthenticated = get(isAuthenticatedAtom);

  return {
    queryKey: ['user-permissions'],
    queryFn: async (): Promise<UserPermissions> => {
      const response = await fetch('/api/v1/auth/permissions', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch user permissions: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: isAuthenticated && !!accessToken,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  };
});

// Computed atoms
export const userAtom = atom((get) => {
  const query = get(userQueryAtom);
  return query.data || null;
});

export const userPermissionsAtom = atom((get) => {
  const query = get(userPermissionsQueryAtom);
  return query.data || null;
});

// Initialize authentication state from stored tokens
export const initializeAuthAtom = atom(
  null,
  (get, set) => {
    const accessToken = get(accessTokenAtom);
    const refreshToken = get(refreshTokenAtom);

    if (accessToken && refreshToken) {
      // Check if token is expired (basic check)
      try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        const currentTime = Math.floor(Date.now() / 1000);

        if (payload.exp > currentTime) {
          set(isAuthenticatedAtom, true);
          set(currentUserAtom, get(userAtom));
        } else {
          // Token expired, try to refresh
          set(refreshAccessTokenAtom);
        }
      } catch (error) {
        // Invalid token, clear auth state
        set(logoutAtom);
      }
    }
  }
);

// Login action atom
export const loginAtom = atom(
  null,
  async (get, set, credentials: LoginCredentials) => {
    try {
      set(authLoadingAtom, true);
      set(authErrorAtom, null);

      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Login failed: ${response.statusText}`);
      }

      const authData = await response.json();

      // Store tokens
      set(accessTokenAtom, authData.access_token);
      set(refreshTokenAtom, authData.refresh_token);

      // Set user data
      set(currentUserAtom, authData.user);
      set(isAuthenticatedAtom, true);

      // Fetch user profile and permissions
      const userQuery = get(userQueryAtom);
      const permissionsQuery = get(userPermissionsQueryAtom);
      userQuery.refetch?.();
      permissionsQuery.refetch?.();

      return authData;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed';
      set(authErrorAtom, errorMessage);
      throw error;
    } finally {
      set(authLoadingAtom, false);
    }
  }
);

// Logout action atom
export const logoutAtom = atom(
  null,
  async (get, set) => {
    try {
      const accessToken = get(accessTokenAtom);

      // Call logout endpoint if we have a token
      if (accessToken) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        }).catch(() => {
          // Ignore logout endpoint errors
        });
      }
    } finally {
      // Clear all auth state regardless of logout endpoint success
      set(accessTokenAtom, null);
      set(refreshTokenAtom, null);
      set(currentUserAtom, null);
      set(isAuthenticatedAtom, false);
      set(authErrorAtom, null);

      // Clear user cache
      if (typeof window !== 'undefined') {
        localStorage.removeItem(USER_KEY);
      }
    }
  }
);

// Refresh token action atom
export const refreshAccessTokenAtom = atom(
  null,
  async (get, set) => {
    try {
      const refreshToken = get(refreshTokenAtom);

      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const tokenData = await response.json();

      // Update access token
      set(accessTokenAtom, tokenData.access_token);
      set(isAuthenticatedAtom, true);

      return tokenData.access_token;
    } catch (error) {
      // Refresh failed, logout user
      set(logoutAtom);
      throw error;
    }
  }
);

// Change password action atom
export const changePasswordAtom = atom(
  null,
  async (get, set, passwordData: ChangePasswordData) => {
    try {
      set(authLoadingAtom, true);
      set(authErrorAtom, null);

      const accessToken = get(accessTokenAtom);

      const response = await fetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(passwordData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Password change failed');
      }

      return await response.json();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Password change failed';
      set(authErrorAtom, errorMessage);
      throw error;
    } finally {
      set(authLoadingAtom, false);
    }
  }
);

// Verify token action atom
export const verifyTokenAtom = atom(
  null,
  async (get, set) => {
    try {
      const accessToken = get(accessTokenAtom);

      if (!accessToken) {
        return false;
      }

      const response = await fetch('/api/v1/auth/verify-token', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (response.ok) {
        set(isAuthenticatedAtom, true);
        return true;
      } else {
        // Token invalid, try to refresh
        await set(refreshAccessTokenAtom);
        return true;
      }
    } catch (error) {
      // Verification and refresh failed
      set(logoutAtom);
      return false;
    }
  }
);

// Permission check atoms
export const hasAdminRoleAtom = atom((get) => {
  const user = get(userAtom);
  return user?.role === 'admin';
});

export const hasOperatorRoleAtom = atom((get) => {
  const user = get(userAtom);
  return user?.role === 'operator' || user?.role === 'admin';
});

export const hasViewerRoleAtom = atom((get) => {
  const user = get(userAtom);
  return !!user; // All authenticated users are at least viewers
});

export const canAccessOrganizationAtom = atom((get) => (organizationId: string) => {
  const user = get(userAtom);

  if (!user) return false;
  if (user.role === 'admin') return true; // Admins can access all organizations

  return user.organization_permissions.includes(organizationId);
});

// Auth state loading
export const authStateLoadingAtom = atom((get) => {
  const authLoading = get(authLoadingAtom);
  const userQuery = get(userQueryAtom);
  const permissionsQuery = get(userPermissionsQueryAtom);

  return authLoading || userQuery.isLoading || permissionsQuery.isLoading;
});

// Auth error state
export const authStateErrorAtom = atom((get) => {
  const authError = get(authErrorAtom);
  const userQuery = get(userQueryAtom);
  const permissionsQuery = get(userPermissionsQueryAtom);

  return authError || userQuery.error?.message || permissionsQuery.error?.message || null;
});

// Auto-refresh token setup
export const setupTokenRefreshAtom = atom(
  null,
  (get, set) => {
    const accessToken = get(accessTokenAtom);

    if (!accessToken) return;

    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const expirationTime = payload.exp * 1000; // Convert to milliseconds
      const currentTime = Date.now();
      const timeUntilExpiry = expirationTime - currentTime;

      // Refresh token 5 minutes before expiry
      const refreshTime = Math.max(timeUntilExpiry - 5 * 60 * 1000, 0);

      if (refreshTime > 0) {
        setTimeout(() => {
          set(refreshAccessTokenAtom);
        }, refreshTime);
      }
    } catch (error) {
      console.warn('Failed to parse access token for auto-refresh setup');
    }
  }
);

// Clear auth error
export const clearAuthErrorAtom = atom(
  null,
  (get, set) => {
    set(authErrorAtom, null);
  }
);