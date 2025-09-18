/**
 * Login page using Next.js, React, and Jotai state management.
 *
 * Provides user authentication interface with demo credentials
 * and responsive design for the IoT dashboard application.
 */

'use client';

import React from 'react';
import { useAtom } from 'jotai';
import Head from 'next/head';
import { useRouter } from 'next/navigation';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';

// Auth components
import LoginForm, { DemoCredentials } from '@/components/auth/LoginForm';

// State
import { isAuthenticatedAtom } from '@/state/authAtoms';

export default function LoginPage() {
  const router = useRouter();
  const [isAuthenticated] = useAtom(isAuthenticatedAtom);

  // Redirect if already authenticated
  React.useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  return (
    <>
      <Head>
        <title>Sign In - IoT Telemetry Dashboard</title>
        <meta name="description" content="Sign in to access the IoT telemetry monitoring dashboard" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <div className="text-center">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                IoT Dashboard
              </h1>
              <p className="text-gray-600">
                Real-time telemetry monitoring platform
              </p>
            </div>
          </div>

          {/* Login Form */}
          <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
            <LoginForm />

            {/* Demo Credentials */}
            <div className="mt-6">
              <DemoCredentials />
            </div>

            {/* Additional Information */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="text-lg">Platform Features</CardTitle>
                <CardDescription>
                  What you can do with IoT Dashboard
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-1 gap-3 text-sm">
                  <div className="flex items-start space-x-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                    <div>
                      <p className="font-medium">Real-time Monitoring</p>
                      <p className="text-gray-600">Live telemetry data from connected IoT devices</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                    <div>
                      <p className="font-medium">Historical Analytics</p>
                      <p className="text-gray-600">Analyze trends with flexible time range selection</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></div>
                    <div>
                      <p className="font-medium">Multi-tenant Support</p>
                      <p className="text-gray-600">Organize devices by organization, site, and area</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-2">
                    <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                    <div>
                      <p className="font-medium">Interactive Charts</p>
                      <p className="text-gray-600">Temperature, vibration, power, and electricity monitoring</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Role Information */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="text-lg">User Roles</CardTitle>
                <CardDescription>
                  Different access levels available
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center p-2 bg-blue-50 rounded">
                    <div>
                      <p className="font-medium text-blue-700">Admin</p>
                      <p className="text-blue-600">Full access to all features and management</p>
                    </div>
                    <div className="text-blue-500 text-xs">👑</div>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-green-50 rounded">
                    <div>
                      <p className="font-medium text-green-700">Operator</p>
                      <p className="text-green-600">Can monitor and manage assigned devices</p>
                    </div>
                    <div className="text-green-500 text-xs">⚙️</div>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                    <div>
                      <p className="font-medium text-gray-700">Viewer</p>
                      <p className="text-gray-600">Read-only access to telemetry data</p>
                    </div>
                    <div className="text-gray-500 text-xs">👀</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Technical Information */}
            <Alert className="mt-6">
              <AlertDescription>
                <strong>Development Environment:</strong> This is a demo IoT dashboard built with Next.js, TypeScript, FastAPI, and VisActor for data visualization. Use the demo credentials above to explore different user roles and features.
              </AlertDescription>
            </Alert>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <Separator className="my-6 max-w-md mx-auto" />
            <p className="text-sm text-gray-500">
              IoT Telemetry Dashboard • Built with Next.js & FastAPI
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Demo environment for showcasing real-time IoT monitoring capabilities
            </p>
          </div>
        </div>
      </div>
    </>
  );
}