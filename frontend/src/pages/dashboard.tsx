/**
 * Main dashboard page using Next.js, React, and Jotai state management.
 *
 * Provides comprehensive IoT telemetry dashboard with device hierarchy navigation,
 * real-time charts, and responsive layout design.
 */

'use client';

import React from 'react';
import { useAtom } from 'jotai';
import Head from 'next/head';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

// Layout
import DashboardLayout from '@/components/layout/DashboardLayout';

// Hierarchy components
import OrganizationSelector from '@/components/hierarchy/OrganizationSelector';
import SiteSelector from '@/components/hierarchy/SiteSelector';
import AreaSelector from '@/components/hierarchy/AreaSelector';
import DeviceList from '@/components/hierarchy/DeviceList';

// Chart components
import TemperatureChart from '@/components/charts/TemperatureChart';
import VibrationChart from '@/components/charts/VibrationChart';
import PowerChart from '@/components/charts/PowerChart';
import ElectricityChart from '@/components/charts/ElectricityChart';
import TimeRangePicker from '@/components/charts/TimeRangePicker';

// Auth component
import { RequireAuth } from '@/components/auth/LoginForm';

// State
import { selectedOrganizationAtom } from '@/state/organizationAtoms';
import { selectedSiteAtom, selectedAreaAtom, selectedDeviceAtom } from '@/state/hierarchyAtoms';
import { currentTelemetryAtom, selectedTimeRangeAtom, TIME_RANGES } from '@/state/telemetryAtoms';
import { userAtom } from '@/state/authAtoms';

export default function DashboardPage() {
  // State atoms
  const [user] = useAtom(userAtom);
  const [selectedOrg] = useAtom(selectedOrganizationAtom);
  const [selectedSite] = useAtom(selectedSiteAtom);
  const [selectedArea] = useAtom(selectedAreaAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);
  const [currentTelemetry] = useAtom(currentTelemetryAtom);
  const [timeRange] = useAtom(selectedTimeRangeAtom);

  const hasSelectedDevice = !!selectedDevice;
  const hasCurrentTelemetry = !!currentTelemetry;

  return (
    <RequireAuth>
      <Head>
        <title>IoT Telemetry Dashboard</title>
        <meta name="description" content="Real-time IoT device telemetry monitoring dashboard" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <DashboardLayout>
        <div className="min-h-screen bg-gray-50">
          <div className="container mx-auto px-4 py-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  IoT Telemetry Dashboard
                </h1>
                <p className="text-gray-600 mt-1">
                  Real-time monitoring and analytics for connected devices
                </p>
              </div>
              <div className="flex items-center space-x-4">
                {user && (
                  <div className="text-right">
                    <p className="text-sm font-medium">{user.name}</p>
                    <p className="text-xs text-gray-500 capitalize">{user.role}</p>
                  </div>
                )}
                {hasSelectedDevice && (
                  <Badge variant="secondary">
                    Device Selected
                  </Badge>
                )}
              </div>
            </div>

            {/* Breadcrumb Navigation */}
            {(selectedOrg || selectedSite || selectedArea || selectedDevice) && (
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                {selectedOrg && (
                  <>
                    <span className="font-medium">{selectedOrg.name}</span>
                    {selectedSite && <span>→</span>}
                  </>
                )}
                {selectedSite && (
                  <>
                    <span className="font-medium">{selectedSite.name}</span>
                    {selectedArea && <span>→</span>}
                  </>
                )}
                {selectedArea && (
                  <>
                    <span className="font-medium">{selectedArea.name}</span>
                    {selectedDevice && <span>→</span>}
                  </>
                )}
                {selectedDevice && (
                  <span className="font-medium text-blue-600">{selectedDevice.name}</span>
                )}
              </div>
            )}

            {/* Time Range Controls */}
            {hasSelectedDevice && (
              <Card>
                <CardContent className="pt-6">
                  <TimeRangePicker
                    variant="default"
                    showRealTimeToggle={true}
                    showRefreshButton={true}
                    showFieldSelector={true}
                  />
                </CardContent>
              </Card>
            )}

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Left Sidebar - Device Hierarchy */}
              <div className="lg:col-span-1 space-y-4">
                <OrganizationSelector
                  variant="card"
                  showStats={true}
                  showManagement={true}
                />

                {selectedOrg && (
                  <SiteSelector
                    variant="card"
                    showStats={true}
                    showManagement={true}
                  />
                )}

                {selectedSite && (
                  <AreaSelector
                    variant="card"
                    showStats={true}
                    showManagement={true}
                  />
                )}

                {selectedArea && (
                  <DeviceList
                    variant="compact"
                    showStats={false}
                    showSearch={true}
                    showFilters={true}
                    showManagement={true}
                  />
                )}
              </div>

              {/* Main Content Area */}
              <div className="lg:col-span-3">
                {!hasSelectedDevice ? (
                  // Welcome/Getting Started
                  <Card className="h-96">
                    <CardContent className="flex flex-col items-center justify-center h-full space-y-4">
                      <div className="text-center">
                        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                          Welcome to IoT Dashboard
                        </h2>
                        <p className="text-gray-600 max-w-md">
                          Select an organization, site, area, and device from the sidebar to begin monitoring telemetry data.
                        </p>
                      </div>
                      <div className="text-sm text-gray-500 space-y-1">
                        <p>📊 Real-time data visualization</p>
                        <p>🌡️ Temperature monitoring</p>
                        <p>⚡ Power consumption tracking</p>
                        <p>📈 Historical analytics</p>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  // Dashboard Content
                  <div className="space-y-6">
                    {/* Device Status Overview */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center justify-between">
                          <span>Device Status</span>
                          <Badge
                            variant={
                              selectedDevice.status === 'online' ? 'default' :
                              selectedDevice.status === 'offline' ? 'destructive' : 'secondary'
                            }
                          >
                            {selectedDevice.status}
                          </Badge>
                        </CardTitle>
                        <CardDescription>
                          {selectedDevice.model} • Last seen: {
                            selectedDevice.last_seen
                              ? new Date(selectedDevice.last_seen).toLocaleString()
                              : 'Never'
                          }
                        </CardDescription>
                      </CardHeader>
                      {hasCurrentTelemetry && (
                        <CardContent>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {currentTelemetry.readings.temperature && (
                              <div className="text-center">
                                <p className="text-2xl font-bold text-red-500">
                                  {currentTelemetry.readings.temperature.value}°C
                                </p>
                                <p className="text-sm text-gray-600">Temperature</p>
                              </div>
                            )}
                            {currentTelemetry.readings.vibration && (
                              <div className="text-center">
                                <p className="text-2xl font-bold text-blue-500">
                                  {currentTelemetry.readings.vibration.value}
                                </p>
                                <p className="text-sm text-gray-600">Vibration (mm/s)</p>
                              </div>
                            )}
                            {currentTelemetry.readings.power && (
                              <div className="text-center">
                                <p className="text-2xl font-bold text-green-500">
                                  {currentTelemetry.readings.power.value}W
                                </p>
                                <p className="text-sm text-gray-600">Power</p>
                              </div>
                            )}
                            {currentTelemetry.readings.electricity && (
                              <div className="text-center">
                                <p className="text-2xl font-bold text-yellow-500">
                                  {currentTelemetry.readings.electricity.value}
                                </p>
                                <p className="text-sm text-gray-600">Electricity (kWh)</p>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      )}
                    </Card>

                    {/* Telemetry Charts Grid */}
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                      <TemperatureChart
                        height={300}
                        showCurrentValue={true}
                        showThresholds={true}
                      />

                      <VibrationChart
                        height={300}
                        showCurrentValue={true}
                      />

                      <PowerChart
                        height={300}
                        showCurrentValue={true}
                        showEfficiencyMetrics={true}
                      />

                      <ElectricityChart
                        height={300}
                        showCurrentValue={true}
                        showCostEstimation={true}
                        electricityRate={0.12}
                      />
                    </div>

                    {/* Additional Info */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Data Information</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                          <div>
                            <p className="font-medium text-gray-900">Time Range</p>
                            <p className="text-gray-600">
                              {TIME_RANGES[timeRange].label}
                            </p>
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">Update Interval</p>
                            <p className="text-gray-600">
                              {TIME_RANGES[timeRange].interval}
                            </p>
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">Last Update</p>
                            <p className="text-gray-600">
                              {hasCurrentTelemetry
                                ? new Date(currentTelemetry.timestamp).toLocaleString()
                                : 'No data'
                              }
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <Separator />
            <div className="text-center text-sm text-gray-500">
              IoT Telemetry Dashboard • Built with Next.js, TypeScript, and VisActor
            </div>
          </div>
        </div>
      </DashboardLayout>
    </RequireAuth>
  );
}