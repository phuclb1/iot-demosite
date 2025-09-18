/**
 * Real-time temperature chart component using VisActor and Jotai state management.
 *
 * Displays temperature telemetry data with real-time updates,
 * time range selection, and interactive visualization features.
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { useAtom } from 'jotai';
import { LineChart, Thermometer } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

import {
  temperatureChartDataAtom,
  selectedTimeRangeAtom,
  isRealTimeEnabledAtom,
  telemetryIsLoadingAtom,
  telemetryHasErrorAtom,
  currentTelemetryAtom,
  TELEMETRY_FIELDS,
  TIME_RANGES,
} from '@/state/telemetryAtoms';

import { selectedDeviceAtom } from '@/state/hierarchyAtoms';

// VisActor chart instance type
interface VChart {
  updateData: (id: string, data: any[]) => void;
  renderAsync: () => Promise<void>;
  release: () => void;
  resize: () => void;
}

declare global {
  interface Window {
    VChart: any;
  }
}

interface TemperatureChartProps {
  className?: string;
  height?: number;
  showLegend?: boolean;
  showTooltip?: boolean;
  showCurrentValue?: boolean;
  showThresholds?: boolean;
}

export default function TemperatureChart({
  className = '',
  height = 300,
  showLegend = true,
  showTooltip = true,
  showCurrentValue = true,
  showThresholds = true
}: TemperatureChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<VChart | null>(null);

  // State atoms
  const [chartData] = useAtom(temperatureChartDataAtom);
  const [timeRange] = useAtom(selectedTimeRangeAtom);
  const [isRealTimeEnabled] = useAtom(isRealTimeEnabledAtom);
  const [isLoading] = useAtom(telemetryIsLoadingAtom);
  const [hasError] = useAtom(telemetryHasErrorAtom);
  const [currentTelemetry] = useAtom(currentTelemetryAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);

  // Get current temperature value
  const currentTemperature = currentTelemetry?.readings?.temperature;
  const temperatureField = TELEMETRY_FIELDS.temperature;

  // Temperature thresholds (configurable based on device type)
  const temperatureThresholds = {
    critical: 80, // °C
    warning: 70,  // °C
    normal: 50    // °C
  };

  // Get temperature status based on current value
  const getTemperatureStatus = (value: number) => {
    if (value >= temperatureThresholds.critical) return { status: 'critical', color: '#ef4444' };
    if (value >= temperatureThresholds.warning) return { status: 'warning', color: '#f59e0b' };
    return { status: 'normal', color: '#10b981' };
  };

  const currentStatus = currentTemperature ? getTemperatureStatus(currentTemperature.value) : null;

  // Initialize chart
  useEffect(() => {
    if (!chartRef.current || !window.VChart) return;

    const spec = {
      type: 'line',
      data: {
        id: 'temperature',
        values: chartData.map(point => ({
          timestamp: new Date(point.timestamp).getTime(),
          value: point.value
        }))
      },
      xField: 'timestamp',
      yField: 'value',
      seriesField: 'type',
      axes: [
        {
          orient: 'bottom',
          type: 'time',
          label: {
            formatMethod: (val: number) => {
              const date = new Date(val);
              const timeRange = TIME_RANGES[timeRange as keyof typeof TIME_RANGES];
              if (timeRange.hours <= 24) {
                return date.toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit'
                });
              }
              return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric'
              });
            }
          }
        },
        {
          orient: 'left',
          type: 'linear',
          label: {
            formatMethod: (val: number) => `${val}${temperatureField.unit}`
          }
        }
      ],
      line: {
        style: {
          stroke: temperatureField.color,
          lineWidth: 2
        }
      },
      point: {
        style: {
          fill: temperatureField.color,
          stroke: temperatureField.color,
          size: 3
        }
      },
      area: {
        style: {
          fill: temperatureField.color,
          fillOpacity: 0.1
        }
      },
      markLine: showThresholds ? [
        {
          y: temperatureThresholds.critical,
          line: {
            style: {
              stroke: '#ef4444',
              lineWidth: 2,
              lineDash: [5, 5]
            }
          },
          label: {
            text: `Critical: ${temperatureThresholds.critical}°C`,
            position: 'end',
            style: {
              fill: '#ef4444',
              fontSize: 12
            }
          }
        },
        {
          y: temperatureThresholds.warning,
          line: {
            style: {
              stroke: '#f59e0b',
              lineWidth: 2,
              lineDash: [5, 5]
            }
          },
          label: {
            text: `Warning: ${temperatureThresholds.warning}°C`,
            position: 'end',
            style: {
              fill: '#f59e0b',
              fontSize: 12
            }
          }
        }
      ] : [],
      tooltip: showTooltip ? {
        dimension: {
          title: {
            value: 'Time'
          },
          content: {
            key: 'timestamp',
            value: (datum: any) => new Date(datum.timestamp).toLocaleString()
          }
        },
        measure: {
          title: {
            value: temperatureField.label
          },
          content: {
            key: 'value',
            value: (datum: any) => {
              const status = getTemperatureStatus(datum.value);
              return `${datum.value} ${temperatureField.unit} (${status.status})`;
            }
          }
        }
      } : false,
      legends: showLegend ? [
        {
          visible: true,
          position: 'bottom',
          item: {
            label: {
              style: {
                fill: '#666'
              }
            }
          }
        }
      ] : false,
      animation: {
        appear: {
          duration: 1000,
          easing: 'easeOutCubic'
        },
        update: {
          duration: 300,
          easing: 'easeOutCubic'
        }
      },
      theme: 'light'
    };

    chartInstanceRef.current = new window.VChart(spec, {
      dom: chartRef.current,
      animation: true
    });

    chartInstanceRef.current.renderAsync();

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.release();
        chartInstanceRef.current = null;
      }
    };
  }, [showLegend, showTooltip, showThresholds, timeRange, temperatureField]);

  // Update chart data
  useEffect(() => {
    if (!chartInstanceRef.current || !chartData) return;

    const formattedData = chartData.map(point => ({
      timestamp: new Date(point.timestamp).getTime(),
      value: point.value,
      type: 'temperature'
    }));

    chartInstanceRef.current.updateData('temperature', formattedData);
  }, [chartData]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.resize();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Load VisActor library
  useEffect(() => {
    if (window.VChart) return;

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/@visactor/vchart/build/index.min.js';
    script.async = true;
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, []);

  if (!selectedDevice) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Please select a device to view temperature data</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Thermometer className="h-5 w-5" style={{ color: temperatureField.color }} />
            <CardTitle>{temperatureField.label}</CardTitle>
            {isRealTimeEnabled && (
              <Badge variant="secondary" className="text-xs">
                Live
              </Badge>
            )}
            {currentStatus && (
              <Badge
                variant={
                  currentStatus.status === 'critical' ? 'destructive' :
                  currentStatus.status === 'warning' ? 'secondary' : 'default'
                }
                className="text-xs"
              >
                {currentStatus.status}
              </Badge>
            )}
          </div>
          {showCurrentValue && currentTemperature && (
            <div className="text-right">
              <p
                className="text-2xl font-bold"
                style={{ color: currentStatus?.color || temperatureField.color }}
              >
                {currentTemperature.value}
              </p>
              <p className="text-sm text-muted-foreground">{temperatureField.unit}</p>
            </div>
          )}
        </div>
        <CardDescription>
          Device: {selectedDevice.name} • Range: {TIME_RANGES[timeRange as keyof typeof TIME_RANGES].label}
          {showThresholds && (
            <>
              {' • '}Warning: {temperatureThresholds.warning}°C • Critical: {temperatureThresholds.critical}°C
            </>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {hasError && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>
              Failed to load temperature data. Please try refreshing.
            </AlertDescription>
          </Alert>
        )}

        {currentStatus?.status === 'critical' && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>
              Critical temperature detected! Current temperature ({currentTemperature?.value}°C) exceeds safe limits.
            </AlertDescription>
          </Alert>
        )}

        {currentStatus?.status === 'warning' && (
          <Alert className="mb-4">
            <AlertDescription>
              Temperature warning: Current temperature ({currentTemperature?.value}°C) is above normal operating range.
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <div className="animate-pulse space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <p className="text-muted-foreground">No temperature data available</p>
          </div>
        ) : (
          <div ref={chartRef} style={{ height, width: '100%' }} />
        )}

        {showCurrentValue && currentTemperature && (
          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <span>Last reading: {new Date(currentTemperature.timestamp).toLocaleString()}</span>
            <span className="flex items-center">
              <div
                className="w-2 h-2 rounded-full mr-2"
                style={{ backgroundColor: currentStatus?.color || temperatureField.color }}
              />
              Current: {currentTemperature.value} {temperatureField.unit}
            </span>
          </div>
        )}

        {showThresholds && (
          <div className="mt-4 pt-4 border-t">
            <p className="text-sm font-medium mb-2">Temperature Thresholds:</p>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                <span>Normal: &lt; {temperatureThresholds.warning}°C</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></div>
                <span>Warning: {temperatureThresholds.warning}-{temperatureThresholds.critical - 1}°C</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
                <span>Critical: ≥ {temperatureThresholds.critical}°C</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}