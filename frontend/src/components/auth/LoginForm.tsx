/**
 * Login form component using React, Shadcn UI, and Jotai state management.
 *
 * Provides user authentication interface with form validation,
 * error handling, and responsive design.
 */

'use client';

import React, { useState } from 'react';
import { useAtom } from 'jotai';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

import {
  loginAtom,
  authLoadingAtom,
  authErrorAtom,
  clearAuthErrorAtom,
  isAuthenticatedAtom
} from '@/state/authAtoms';

interface LoginFormData {
  email: string;
  password: string;
}

interface LoginFormErrors {
  email?: string;
  password?: string;
  general?: string;
}

export default function LoginForm() {
  const router = useRouter();

  // State atoms
  const [, login] = useAtom(loginAtom);
  const [isLoading] = useAtom(authLoadingAtom);
  const [authError] = useAtom(authErrorAtom);
  const [, clearError] = useAtom(clearAuthErrorAtom);
  const [isAuthenticated] = useAtom(isAuthenticatedAtom);

  // Local state
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState<LoginFormErrors>({});
  const [showPassword, setShowPassword] = useState(false);

  // Redirect if already authenticated
  React.useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  // Clear auth error when component mounts or form data changes
  React.useEffect(() => {
    if (authError) {
      clearError();
    }
  }, [formData, clearError]);

  const validateForm = (): boolean => {
    const newErrors: LoginFormErrors = {};

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters long';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: keyof LoginFormData) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = e.target.value;
    setFormData(prev => ({ ...prev, [field]: value }));

    // Clear field error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      await login({
        email: formData.email.trim(),
        password: formData.password,
      });

      // Login successful, redirect will happen via useEffect
    } catch (error) {
      // Error handling is managed by the auth atom
      console.error('Login failed:', error);
    }
  };

  const togglePasswordVisibility = () => {
    setShowPassword(prev => !prev);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Sign in to IoT Dashboard
          </CardTitle>
          <CardDescription className="text-center">
            Enter your credentials to access the telemetry dashboard
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* General error message */}
            {authError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{authError}</AlertDescription>
              </Alert>
            )}

            {/* Email field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="Enter your email"
                value={formData.email}
                onChange={handleInputChange('email')}
                className={errors.email ? 'border-red-500' : ''}
                disabled={isLoading}
                autoComplete="email"
                autoFocus
              />
              {errors.email && (
                <p className="text-sm text-red-600">{errors.email}</p>
              )}
            </div>

            {/* Password field */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleInputChange('password')}
                  className={errors.password ? 'border-red-500 pr-10' : 'pr-10'}
                  disabled={isLoading}
                  autoComplete="current-password"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={togglePasswordVisibility}
                  disabled={isLoading}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4 text-gray-500" />
                  ) : (
                    <Eye className="h-4 w-4 text-gray-500" />
                  )}
                </Button>
              </div>
              {errors.password && (
                <p className="text-sm text-red-600">{errors.password}</p>
              )}
            </div>

            {/* Submit button */}
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </Button>
          </form>

          {/* Additional options */}
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">
                  Need help?
                </span>
              </div>
            </div>

            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Contact your administrator for account access
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Demo credentials component (remove in production)
export function DemoCredentials() {
  return (
    <Card className="w-full max-w-md mt-4">
      <CardHeader>
        <CardTitle className="text-lg">Demo Credentials</CardTitle>
        <CardDescription>
          Use these credentials for testing (development only)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="font-medium">Admin</p>
            <p className="text-gray-600">admin@example.com</p>
            <p className="text-gray-600">password123</p>
          </div>
          <div>
            <p className="font-medium">Operator</p>
            <p className="text-gray-600">operator@example.com</p>
            <p className="text-gray-600">password123</p>
          </div>
          <div>
            <p className="font-medium">Viewer</p>
            <p className="text-gray-600">viewer@example.com</p>
            <p className="text-gray-600">password123</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Auth guard component
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const [isAuthenticated] = useAtom(isAuthenticatedAtom);
  const [isLoading] = useAtom(authLoadingAtom);
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect to login
  }

  return <>{children}</>;
}

// Role-based access component
interface RequireRoleProps {
  children: React.ReactNode;
  roles: ('admin' | 'operator' | 'viewer')[];
  fallback?: React.ReactNode;
}

export function RequireRole({ children, roles, fallback }: RequireRoleProps) {
  const [user] = useAtom(userAtom);

  if (!user || !roles.includes(user.role)) {
    return fallback || (
      <div className="text-center py-8">
        <p className="text-gray-600">
          You don't have permission to access this content.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}