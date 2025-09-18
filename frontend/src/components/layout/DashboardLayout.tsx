/**
 * Dashboard layout component using React, Shadcn UI, and Jotai state management.
 *
 * Provides consistent layout structure with navigation, header, sidebar,
 * and user management features for the IoT dashboard application.
 */

'use client';

import React, { useState } from 'react';
import { useAtom } from 'jotai';
import { useRouter } from 'next/navigation';
import {
  BarChart3,
  Bell,
  Home,
  LogOut,
  Menu,
  Settings,
  User,
  X,
  Activity,
  Building,
  Database,
  Wifi
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

// State
import { userAtom, logoutAtom, hasAdminRoleAtom, hasOperatorRoleAtom } from '@/state/authAtoms';
import {
  selectedOrganizationAtom,
  selectedSiteAtom,
  selectedAreaAtom,
  selectedDeviceAtom
} from '@/state/hierarchyAtoms';
import { isRealTimeEnabledAtom, streamingConnectionAtom } from '@/state/telemetryAtoms';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // State atoms
  const [user] = useAtom(userAtom);
  const [, logout] = useAtom(logoutAtom);
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);
  const [selectedOrg] = useAtom(selectedOrganizationAtom);
  const [selectedSite] = useAtom(selectedSiteAtom);
  const [selectedArea] = useAtom(selectedAreaAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);
  const [isRealTimeEnabled] = useAtom(isRealTimeEnabledAtom);
  const [streamingConnection] = useAtom(streamingConnectionAtom);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const handleNavigate = (path: string) => {
    router.push(path);
    setIsSidebarOpen(false);
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(part => part.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Navigation items
  const navigationItems = [
    {
      name: 'Dashboard',
      icon: Home,
      href: '/dashboard',
      current: true
    },
    {
      name: 'Analytics',
      icon: BarChart3,
      href: '/analytics',
      current: false,
      disabled: true
    },
    {
      name: 'Device Management',
      icon: Settings,
      href: '/devices',
      current: false,
      disabled: !hasOperatorRole
    },
    {
      name: 'System Settings',
      icon: Database,
      href: '/settings',
      current: false,
      disabled: !hasAdminRole
    }
  ];

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo/Brand */}
      <div className="flex items-center space-x-2 p-6 border-b">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Activity className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-lg">IoT Dashboard</h1>
          <p className="text-xs text-muted-foreground">Telemetry Monitor</p>
        </div>
      </div>

      {/* Current Selection Summary */}
      {(selectedOrg || selectedSite || selectedArea || selectedDevice) && (
        <div className="p-4 border-b bg-muted/30">
          <p className="text-xs font-medium text-muted-foreground mb-2">CURRENT SELECTION</p>
          <div className="space-y-1 text-sm">
            {selectedOrg && (
              <div className="flex items-center space-x-2">
                <Building className="h-3 w-3" />
                <span className="truncate">{selectedOrg.name}</span>
              </div>
            )}
            {selectedSite && (
              <div className="flex items-center space-x-2 ml-2">
                <span className="text-muted-foreground">→</span>
                <span className="truncate">{selectedSite.name}</span>
              </div>
            )}
            {selectedArea && (
              <div className="flex items-center space-x-2 ml-4">
                <span className="text-muted-foreground">→</span>
                <span className="truncate">{selectedArea.name}</span>
              </div>
            )}
            {selectedDevice && (
              <div className="flex items-center space-x-2 ml-6">
                <span className="text-muted-foreground">→</span>
                <span className="truncate font-medium text-blue-600">{selectedDevice.name}</span>
                <Badge
                  variant={
                    selectedDevice.status === 'online' ? 'default' :
                    selectedDevice.status === 'offline' ? 'destructive' : 'secondary'
                  }
                  className="text-xs"
                >
                  {selectedDevice.status}
                </Badge>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Real-time Status */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Wifi className={`h-4 w-4 ${
              streamingConnection.connected ? 'text-green-500' : 'text-red-500'
            }`} />
            <span className="text-sm font-medium">
              {isRealTimeEnabled ? 'Live Mode' : 'Historical Mode'}
            </span>
          </div>
          <Badge
            variant={isRealTimeEnabled && streamingConnection.connected ? 'default' : 'secondary'}
            className="text-xs"
          >
            {isRealTimeEnabled && streamingConnection.connected ? 'Connected' : 'Offline'}
          </Badge>
        </div>
        {streamingConnection.error && (
          <p className="text-xs text-red-600 mt-1">{streamingConnection.error}</p>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <p className="text-xs font-medium text-muted-foreground mb-3">NAVIGATION</p>
        {navigationItems.map((item) => {
          const Icon = item.icon;
          return (
            <Button
              key={item.name}
              variant={item.current ? "default" : "ghost"}
              className={`w-full justify-start ${item.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              onClick={() => !item.disabled && handleNavigate(item.href)}
              disabled={item.disabled}
            >
              <Icon className="h-4 w-4 mr-3" />
              {item.name}
            </Button>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t">
        {user && (
          <div className="flex items-center space-x-3">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs">
                {getInitials(user.name)}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col">
        <Card className="flex flex-col h-full rounded-none border-r">
          <SidebarContent />
        </Card>
      </div>

      {/* Mobile Sidebar */}
      <Sheet open={isSidebarOpen} onOpenChange={setIsSidebarOpen}>
        <SheetContent side="left" className="p-0 w-64">
          <SidebarContent />
        </SheetContent>
      </Sheet>

      {/* Main Content */}
      <div className="md:pl-64">
        {/* Top Header */}
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
          {/* Mobile Menu Button */}
          <div className="flex items-center space-x-4">
            <Sheet>
              <SheetTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="md:hidden"
                  onClick={() => setIsSidebarOpen(true)}
                >
                  <Menu className="h-4 w-4" />
                </Button>
              </SheetTrigger>
            </Sheet>

            {/* Page Title - Hidden on mobile */}
            <div className="hidden md:block">
              <h2 className="text-lg font-semibold">Dashboard</h2>
            </div>
          </div>

          {/* Right Side Actions */}
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <Button variant="outline" size="sm" disabled>
              <Bell className="h-4 w-4" />
              <Badge variant="secondary" className="ml-2 text-xs">
                0
              </Badge>
            </Button>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <User className="h-4 w-4 mr-2" />
                  {user?.name || 'User'}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium">{user?.name}</p>
                  <p className="text-xs text-muted-foreground">{user?.email}</p>
                  <p className="text-xs text-muted-foreground capitalize">Role: {user?.role}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem disabled>
                  <Settings className="h-4 w-4 mr-2" />
                  Profile Settings
                </DropdownMenuItem>
                <DropdownMenuItem disabled>
                  <Bell className="h-4 w-4 mr-2" />
                  Notifications
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="h-4 w-4 mr-2" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="min-h-[calc(100vh-4rem)]">
          {children}
        </main>
      </div>
    </div>
  );
}