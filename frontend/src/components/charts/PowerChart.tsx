/**
 * Real-time power chart component using VisActor and Jotai state management.
 *
 * Displays power consumption telemetry data with real-time updates,
 * time range selection, and energy efficiency indicators.
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { useAtom } from 'jotai';
import { LineChart, Zap, TrendingUp, TrendingDown } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

import {
  powerChartDataAtom,
  selectedTimeRangeAtom,
  isRealTimeEnabledAtom,
  telemetryIsLoadingAtom,
  telemetryHasErrorAtom,
  currentTelemetryAtom,
  telemetrySummaryAtom,
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

interface PowerChartProps {
  className?: string;
  height?: number;
  showLegend?: boolean;
  showTooltip?: boolean;
  showCurrentValue?: boolean;
  showEfficiencyMetrics?: boolean;
}

export default function PowerChart({
  className = '',
  height = 300,
  showLegend = true,
  showTooltip = true,
  showCurrentValue = true,
  showEfficiencyMetrics = true
}: PowerChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<VChart | null>(null);

  // State atoms
  const [chartData] = useAtom(powerChartDataAtom);
  const [timeRange] = useAtom(selectedTimeRangeAtom);
  const [isRealTimeEnabled] = useAtom(isRealTimeEnabledAtom);
  const [isLoading] = useAtom(telemetryIsLoadingAtom);
  const [hasError] = useAtom(telemetryHasErrorAtom);
  const [currentTelemetry] = useAtom(currentTelemetryAtom);
  const [telemetrySummary] = useAtom(telemetrySummaryAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);

  // Get current power value
  const currentPower = currentTelemetry?.readings?.power;
  const powerField = TELEMETRY_FIELDS.power;
  const powerSummary = telemetrySummary?.field_summaries?.power;

  // Calculate power statistics
  const powerStats = React.useMemo(() => {
    if (!powerSummary || !chartData.length) return null;

    const currentValue = currentPower?.value || 0;
    const avgValue = powerSummary.mean || 0;
    const maxValue = powerSummary.max || 0;
    const minValue = powerSummary.min || 0;

    // Calculate trend (comparing current with average)
    const trend = currentValue > avgValue ? 'up' : currentValue < avgValue ? 'down' : 'stable';
    const trendPercentage = avgValue > 0 ? Math.abs(((currentValue - avgValue) / avgValue) * 100) : 0;

    // Calculate efficiency score (lower power consumption = higher efficiency)
    const efficiencyScore = maxValue > 0 ? Math.max(0, 100 - ((currentValue / maxValue) * 100)) : 100;

    return {
      current: currentValue,
      average: avgValue,
      max: maxValue,
      min: minValue,
      trend,
      trendPercentage: Math.round(trendPercentage),
      efficiencyScore: Math.round(efficiencyScore)
    };
  }, [powerSummary, chartData, currentPower]);

  // Initialize chart
  useEffect(() => {
    if (!chartRef.current || !window.VChart) return;

    const avgValue = powerStats?.average || 0;

    const spec = {
      type: 'line',
      data: {
        id: 'power',
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
            formatMethod: (val: number) => `${val}${powerField.unit}`
          }
        }
      ],
      line: {
        style: {
          stroke: powerField.color,
          lineWidth: 2
        }
      },
      point: {
        style: {
          fill: powerField.color,
          stroke: powerField.color,
          size: 3
        }
      },
      area: {
        style: {
          fill: powerField.color,
          fillOpacity: 0.1
        }
      },
      markLine: avgValue > 0 ? [
        {
          y: avgValue,
          line: {
            style: {
              stroke: '#64748b',
              lineWidth: 1,
              lineDash: [3, 3]
            }
          },
          label: {
            text: `Avg: ${avgValue.toFixed(1)}W`,
            position: 'end',
            style: {
              fill: '#64748b',
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
            value: powerField.label
          },
          content: {
            key: 'value',
            value: (datum: any) => `${datum.value} ${powerField.unit}`
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
  }, [showLegend, showTooltip, timeRange, powerField, powerStats]);

  // Update chart data
  useEffect(() => {
    if (!chartInstanceRef.current || !chartData) return;

    const formattedData = chartData.map(point => ({
      timestamp: new Date(point.timestamp).getTime(),
      value: point.value,
      type: 'power'
    }));

    chartInstanceRef.current.updateData('power', formattedData);
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
          <p className="text-muted-foreground">Please select a device to view power data</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Zap className="h-5 w-5" style={{ color: powerField.color }} />
            <CardTitle>{powerField.label}</CardTitle>
            {isRealTimeEnabled && (
              <Badge variant="secondary" className="text-xs">
                Live
              </Badge>
            )}
            {powerStats && (
              <Badge
                variant={
                  powerStats.trend === 'up' ? 'destructive' :
                  powerStats.trend === 'down' ? 'default' : 'secondary'
                }
                className="text-xs"
              >
                {powerStats.trend === 'up' && <TrendingUp className="h-3 w-3 mr-1" />}
                {powerStats.trend === 'down' && <TrendingDown className="h-3 w-3 mr-1" />}
                {powerStats.trendPercentage}%
              </Badge>
            )}
          </div>
          {showCurrentValue && currentPower && (
            <div className="text-right">
              <p className="text-2xl font-bold" style={{ color: powerField.color }}>
                {currentPower.value}
              </p>
              <p className="text-sm text-muted-foreground">{powerField.unit}</p>
            </div>
          )}
        </div>
        <CardDescription>
          Device: {selectedDevice.name} • Range: {TIME_RANGES[timeRange as keyof typeof TIME_RANGES].label}
          {powerStats && ` • Avg: ${powerStats.average.toFixed(1)}W`}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {hasError && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>
              Failed to load power data. Please try refreshing.
            </AlertDescription>
          </Alert>
        )}

        {/* Efficiency metrics */}
        {showEfficiencyMetrics && powerStats && (
          <div className="mb-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Current</div>
              <div className="text-lg font-semibold" style={{ color: powerField.color }}>
                {powerStats.current.toFixed(1)}W
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Average</div>
              <div className="text-lg font-semibold text-gray-600">
                {powerStats.average.toFixed(1)}W
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Peak</div>
              <div className="text-lg font-semibold text-red-600">
                {powerStats.max.toFixed(1)}W
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Efficiency</div>
              <div className={`text-lg font-semibold ${
                powerStats.efficiencyScore >= 80 ? 'text-green-600' :
                powerStats.efficiencyScore >= 60 ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {powerStats.efficiencyScore}%
              </div>
            </div>
          </div>
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
            <p className="text-muted-foreground">No power data available</p>
          </div>
        ) : (
          <div ref={chartRef} style={{ height, width: '100%' }} />
        )}

        {showCurrentValue && currentPower && (
          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <span>Last reading: {new Date(currentPower.timestamp).toLocaleString()}</span>
            <span className="flex items-center">
              <div
                className="w-2 h-2 rounded-full mr-2"
                style={{ backgroundColor: powerField.color }}
              />
              Current: {currentPower.value} {powerField.unit}
            </span>
          </div>
        )}

        {showEfficiencyMetrics && powerStats && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Power Efficiency</span>
              <span className={`flex items-center ${
                powerStats.efficiencyScore >= 80 ? 'text-green-600' :
                powerStats.efficiencyScore >= 60 ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {powerStats.efficiencyScore >= 80 && '🟢'}
                {powerStats.efficiencyScore >= 60 && powerStats.efficiencyScore < 80 && '🟡'}
                {powerStats.efficiencyScore < 60 && '🔴'}
                <span className="ml-1">{powerStats.efficiencyScore}% Efficient</span>
              </span>
            </div>
            <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  powerStats.efficiencyScore >= 80 ? 'bg-green-500' :
                  powerStats.efficiencyScore >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${powerStats.efficiencyScore}%` }}
              ></div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              Efficiency calculated based on current vs. peak power consumption
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}