/**
 * Device list component using React, Shadcn UI, and Jotai state management.
 *
 * Provides device listing interface with search, filtering by status,
 * and device management capabilities within an area.
 */

'use client';

import React, { useState } from 'react';
import { useAtom } from 'jotai';
import { Cpu, Search, Plus, Settings, Wifi, WifiOff, Wrench, Eye, Activity, Clock } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import {
  selectedAreaIdAtom,
  selectedAreaAtom,
  devicesListAtom,
  selectedDeviceIdAtom,
  selectedDeviceAtom,
  selectDeviceAtom,
  hierarchyIsLoadingAtom,
  hierarchyHasErrorAtom,
  refreshDevicesAtom,
  deviceStatusFilterAtom,
  deviceSearchAtom,
  filteredDevicesAtom,
  deviceStatsAtom,
} from '@/state/hierarchyAtoms';

import { hasAdminRoleAtom, hasOperatorRoleAtom, userAtom } from '@/state/authAtoms';

interface DeviceListProps {
  className?: string;
  showStats?: boolean;
  showSearch?: boolean;
  showFilters?: boolean;
  showManagement?: boolean;
  variant?: 'default' | 'grid' | 'compact';
}

export default function DeviceList({
  className = '',
  showStats = true,
  showSearch = true,
  showFilters = true,
  showManagement = false,
  variant = 'default'
}: DeviceListProps) {
  // State atoms
  const [selectedAreaId] = useAtom(selectedAreaIdAtom);
  const [selectedArea] = useAtom(selectedAreaAtom);
  const [devices] = useAtom(devicesListAtom);
  const [filteredDevices] = useAtom(filteredDevicesAtom);
  const [deviceStats] = useAtom(deviceStatsAtom);
  const [selectedDeviceId] = useAtom(selectedDeviceIdAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);
  const [, selectDevice] = useAtom(selectDeviceAtom);
  const [isLoading] = useAtom(hierarchyIsLoadingAtom);
  const [hasError] = useAtom(hierarchyHasErrorAtom);
  const [, refreshDevices] = useAtom(refreshDevicesAtom);

  // Filter atoms
  const [statusFilter, setStatusFilter] = useAtom(deviceStatusFilterAtom);
  const [searchQuery, setSearchQuery] = useAtom(deviceSearchAtom);

  // Permission atoms
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);
  const [user] = useAtom(userAtom);

  const handleSelect = (deviceId: string) => {
    selectDevice(deviceId === selectedDeviceId ? null : deviceId);
  };

  const handleRefresh = () => {
    refreshDevices();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <Wifi className="h-4 w-4 text-green-500" />;
      case 'offline':
        return <WifiOff className="h-4 w-4 text-red-500" />;
      case 'maintenance':
        return <Wrench className="h-4 w-4 text-yellow-500" />;
      default:
        return <Cpu className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      online: 'default',
      offline: 'destructive',
      maintenance: 'secondary'
    } as const;

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status}
      </Badge>
    );
  };

  // Don't render if no area is selected
  if (!selectedAreaId || !selectedArea) {
    return (
      <div className={`text-center py-8 text-muted-foreground ${className}`}>
        Please select an area first to view devices.
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={`space-y-2 ${className}`}>
        {filteredDevices.map((device) => (
          <Card
            key={device.id}
            className={`cursor-pointer transition-colors ${
              selectedDeviceId === device.id ? 'ring-2 ring-primary bg-primary/5' : 'hover:bg-muted/50'
            }`}
            onClick={() => handleSelect(device.id)}
          >
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(device.status)}
                  <span className="font-medium">{device.name}</span>
                </div>
                {getStatusBadge(device.status)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Cpu className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Devices</h3>
          {devices.length > 0 && (
            <Badge variant="secondary">{devices.length}</Badge>
          )}
        </div>

        {showManagement && (hasAdminRole || hasOperatorRole) && (
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isLoading}
            >
              Refresh
            </Button>
            {hasAdminRole && (
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Device
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Area context */}
      <div className="text-sm text-muted-foreground">
        Area: <span className="font-medium">{selectedArea.name}</span>
      </div>

      {/* Device statistics */}
      {showStats && deviceStats.total > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
                  <Cpu className="h-4 w-4" />
                  <span>Total</span>
                </div>
                <p className="text-2xl font-bold">{deviceStats.total}</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
                  <Wifi className="h-4 w-4 text-green-500" />
                  <span>Online</span>
                </div>
                <p className="text-2xl font-bold text-green-600">{deviceStats.online}</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
                  <WifiOff className="h-4 w-4 text-red-500" />
                  <span>Offline</span>
                </div>
                <p className="text-2xl font-bold text-red-600">{deviceStats.offline}</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
                  <Wrench className="h-4 w-4 text-yellow-500" />
                  <span>Maintenance</span>
                </div>
                <p className="text-2xl font-bold text-yellow-600">{deviceStats.maintenance}</p>
              </div>
            </div>
            {deviceStats.total > 0 && (
              <div className="mt-4">
                <div className="flex justify-between text-sm mb-2">
                  <span>Online Status</span>
                  <span>{deviceStats.onlinePercentage}% Online</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${deviceStats.onlinePercentage}%` }}
                  ></div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      {showFilters && (
        <div className="flex items-center space-x-4">
          {/* Search */}
          {showSearch && (
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search devices..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
          )}

          {/* Status filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Devices</SelectItem>
              <SelectItem value="online">Online Only</SelectItem>
              <SelectItem value="offline">Offline Only</SelectItem>
              <SelectItem value="maintenance">Maintenance Only</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Error state */}
      {hasError && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load devices. Please try refreshing.
          </AlertDescription>
        </Alert>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse space-y-2">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      )}

      {/* Device list */}
      {!isLoading && !hasError && (
        <div className={`${variant === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-2'}`}>
          {filteredDevices.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground col-span-full">
              {searchQuery || statusFilter !== 'all'
                ? 'No devices found matching your criteria.'
                : 'No devices available in this area.'}
            </div>
          ) : (
            filteredDevices.map((device) => (
              <DeviceCard
                key={device.id}
                device={device}
                isSelected={selectedDeviceId === device.id}
                onSelect={handleSelect}
                showManagement={showManagement}
                variant={variant}
              />
            ))
          )}
        </div>
      )}

      {/* Selected device details */}
      {selectedDevice && showStats && (
        <SelectedDeviceDetails />
      )}
    </div>
  );
}

interface DeviceCardProps {
  device: any;
  isSelected: boolean;
  onSelect: (deviceId: string) => void;
  showManagement: boolean;
  variant: string;
}

function DeviceCard({
  device,
  isSelected,
  onSelect,
  showManagement,
  variant
}: DeviceCardProps) {
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <Wifi className="h-4 w-4 text-green-500" />;
      case 'offline':
        return <WifiOff className="h-4 w-4 text-red-500" />;
      case 'maintenance':
        return <Wrench className="h-4 w-4 text-yellow-500" />;
      default:
        return <Cpu className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      online: 'default',
      offline: 'destructive',
      maintenance: 'secondary'
    } as const;

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status}
      </Badge>
    );
  };

  return (
    <Card
      className={`cursor-pointer transition-colors ${
        isSelected ? 'ring-2 ring-primary bg-primary/5' : 'hover:bg-muted/50'
      }`}
      onClick={() => onSelect(device.id)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              {getStatusIcon(device.status)}
              <h4 className="font-medium">{device.name}</h4>
              {isSelected && (
                <Badge variant="outline" className="text-xs">
                  Selected
                </Badge>
              )}
            </div>

            <div className="space-y-1 text-sm text-muted-foreground">
              <p>Model: {device.model}</p>
              {device.firmware_version && (
                <p>Firmware: {device.firmware_version}</p>
              )}
              {device.mac_address && (
                <p className="font-mono text-xs">MAC: {device.mac_address}</p>
              )}
              {device.last_seen && (
                <p className="flex items-center">
                  <Clock className="h-3 w-3 mr-1" />
                  Last seen: {new Date(device.last_seen).toLocaleString()}
                </p>
              )}
            </div>

            <div className="mt-2">
              {getStatusBadge(device.status)}
            </div>
          </div>

          {showManagement && (hasAdminRole || hasOperatorRole) && (
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle view telemetry
                }}
              >
                <Activity className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle device settings
                }}
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SelectedDeviceDetails() {
  const [selectedDevice] = useAtom(selectedDeviceAtom);

  if (!selectedDevice) return null;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <Wifi className="h-5 w-5 text-green-500" />;
      case 'offline':
        return <WifiOff className="h-5 w-5 text-red-500" />;
      case 'maintenance':
        return <Wrench className="h-5 w-5 text-yellow-500" />;
      default:
        return <Cpu className="h-5 w-5 text-gray-500" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          {getStatusIcon(selectedDevice.status)}
          <span>{selectedDevice.name}</span>
        </CardTitle>
        <CardDescription>
          Model: {selectedDevice.model}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Status</Label>
            <p className="capitalize">{selectedDevice.status}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Area ID</Label>
            <p className="font-mono text-xs">{selectedDevice.area_id}</p>
          </div>
        </div>

        {(selectedDevice.firmware_version || selectedDevice.mac_address) && (
          <>
            <Separator />
            <div className="grid grid-cols-2 gap-4 text-sm">
              {selectedDevice.firmware_version && (
                <div>
                  <Label className="text-muted-foreground">Firmware</Label>
                  <p>{selectedDevice.firmware_version}</p>
                </div>
              )}
              {selectedDevice.mac_address && (
                <div>
                  <Label className="text-muted-foreground">MAC Address</Label>
                  <p className="font-mono text-xs">{selectedDevice.mac_address}</p>
                </div>
              )}
            </div>
          </>
        )}

        <Separator />

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Created</Label>
            <p>{new Date(selectedDevice.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Updated</Label>
            <p>{new Date(selectedDevice.updated_at).toLocaleDateString()}</p>
          </div>
        </div>

        {selectedDevice.last_seen && (
          <>
            <Separator />
            <div className="text-sm">
              <Label className="text-muted-foreground">Last Seen</Label>
              <p className="flex items-center mt-1">
                <Clock className="h-4 w-4 mr-1" />
                {new Date(selectedDevice.last_seen).toLocaleString()}
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}