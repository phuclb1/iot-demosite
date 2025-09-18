/**
 * Real-time vibration chart component using VisActor and Jotai state management.
 *
 * Displays vibration telemetry data with real-time updates,
 * time range selection, and interactive visualization features.
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { useAtom } from 'jotai';
import { LineChart, Activity } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

import {
  vibrationChartDataAtom,
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

interface VibrationChartProps {
  className?: string;
  height?: number;
  showLegend?: boolean;
  showTooltip?: boolean;
  showCurrentValue?: boolean;
}

export default function VibrationChart({
  className = '',
  height = 300,
  showLegend = true,
  showTooltip = true,
  showCurrentValue = true
}: VibrationChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<VChart | null>(null);

  // State atoms
  const [chartData] = useAtom(vibrationChartDataAtom);
  const [timeRange] = useAtom(selectedTimeRangeAtom);
  const [isRealTimeEnabled] = useAtom(isRealTimeEnabledAtom);
  const [isLoading] = useAtom(telemetryIsLoadingAtom);
  const [hasError] = useAtom(telemetryHasErrorAtom);
  const [currentTelemetry] = useAtom(currentTelemetryAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);

  // Get current vibration value
  const currentVibration = currentTelemetry?.readings?.vibration;
  const vibrationField = TELEMETRY_FIELDS.vibration;

  // Initialize chart
  useEffect(() => {
    if (!chartRef.current || !window.VChart) return;

    const spec = {
      type: 'line',
      data: {
        id: 'vibration',
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
            formatMethod: (val: number) => `${val}${vibrationField.unit}`
          }
        }
      ],
      line: {
        style: {
          stroke: vibrationField.color,
          lineWidth: 2
        }
      },
      point: {
        style: {
          fill: vibrationField.color,
          stroke: vibrationField.color,
          size: 3
        }
      },
      area: {
        style: {
          fill: vibrationField.color,
          fillOpacity: 0.1
        }
      },
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
            value: vibrationField.label
          },
          content: {
            key: 'value',
            value: (datum: any) => `${datum.value} ${vibrationField.unit}`
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
  }, [showLegend, showTooltip, timeRange, vibrationField]);

  // Update chart data
  useEffect(() => {
    if (!chartInstanceRef.current || !chartData) return;

    const formattedData = chartData.map(point => ({
      timestamp: new Date(point.timestamp).getTime(),
      value: point.value,
      type: 'vibration'
    }));

    chartInstanceRef.current.updateData('vibration', formattedData);
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
          <p className="text-muted-foreground">Please select a device to view vibration data</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5" style={{ color: vibrationField.color }} />
            <CardTitle>{vibrationField.label}</CardTitle>
            {isRealTimeEnabled && (
              <Badge variant="secondary" className="text-xs">
                Live
              </Badge>
            )}
          </div>
          {showCurrentValue && currentVibration && (
            <div className="text-right">
              <p className="text-2xl font-bold" style={{ color: vibrationField.color }}>
                {currentVibration.value}
              </p>
              <p className="text-sm text-muted-foreground">{vibrationField.unit}</p>
            </div>
          )}
        </div>
        <CardDescription>
          Device: {selectedDevice.name} • Range: {TIME_RANGES[timeRange as keyof typeof TIME_RANGES].label}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {hasError && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>
              Failed to load vibration data. Please try refreshing.
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
            <p className="text-muted-foreground">No vibration data available</p>
          </div>
        ) : (
          <div ref={chartRef} style={{ height, width: '100%' }} />
        )}

        {showCurrentValue && currentVibration && (
          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <span>Last reading: {new Date(currentVibration.timestamp).toLocaleString()}</span>
            <span className="flex items-center">
              <div
                className="w-2 h-2 rounded-full mr-2"
                style={{ backgroundColor: vibrationField.color }}
              />
              Current: {currentVibration.value} {vibrationField.unit}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}