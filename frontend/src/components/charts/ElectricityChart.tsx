/**
 * Real-time electricity chart component using VisActor and Jotai state management.
 *
 * Displays electricity consumption telemetry data with real-time updates,
 * cumulative consumption tracking, and cost estimation features.
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { useAtom } from 'jotai';
import { LineChart, Bolt, DollarSign, Calculator } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

import {
  electricityChartDataAtom,
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

interface ElectricityChartProps {
  className?: string;
  height?: number;
  showLegend?: boolean;
  showTooltip?: boolean;
  showCurrentValue?: boolean;
  showCostEstimation?: boolean;
  electricityRate?: number; // Cost per kWh in local currency
}

export default function ElectricityChart({
  className = '',
  height = 300,
  showLegend = true,
  showTooltip = true,
  showCurrentValue = true,
  showCostEstimation = true,
  electricityRate = 0.12 // Default rate: $0.12 per kWh
}: ElectricityChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<VChart | null>(null);

  // State atoms
  const [chartData] = useAtom(electricityChartDataAtom);
  const [timeRange] = useAtom(selectedTimeRangeAtom);
  const [isRealTimeEnabled] = useAtom(isRealTimeEnabledAtom);
  const [isLoading] = useAtom(telemetryIsLoadingAtom);
  const [hasError] = useAtom(telemetryHasErrorAtom);
  const [currentTelemetry] = useAtom(currentTelemetryAtom);
  const [telemetrySummary] = useAtom(telemetrySummaryAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);

  // Get current electricity value
  const currentElectricity = currentTelemetry?.readings?.electricity;
  const electricityField = TELEMETRY_FIELDS.electricity;
  const electricitySummary = telemetrySummary?.field_summaries?.electricity;

  // Calculate electricity statistics and cost estimates
  const electricityStats = React.useMemo(() => {
    if (!electricitySummary || !chartData.length) return null;

    const currentValue = currentElectricity?.value || 0;
    const totalConsumption = electricitySummary.max || 0; // Assuming cumulative reading
    const avgConsumptionRate = electricitySummary.mean || 0;

    // Calculate consumption for the current time period
    const timeRangeInfo = TIME_RANGES[timeRange as keyof typeof TIME_RANGES];
    const periodConsumption = totalConsumption; // This would be delta in real implementation

    // Calculate costs
    const periodCost = periodConsumption * electricityRate;
    const dailyCost = avgConsumptionRate * 24 * electricityRate; // Estimated daily cost
    const monthlyCost = dailyCost * 30; // Estimated monthly cost

    // Calculate consumption trend
    const sortedData = [...chartData].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    let trend = 'stable';
    if (sortedData.length >= 2) {
      const recent = sortedData.slice(-3).reduce((sum, point) => sum + point.value, 0) / 3;
      const earlier = sortedData.slice(0, 3).reduce((sum, point) => sum + point.value, 0) / 3;
      if (recent > earlier * 1.1) trend = 'increasing';
      else if (recent < earlier * 0.9) trend = 'decreasing';
    }

    return {
      current: currentValue,
      total: totalConsumption,
      average: avgConsumptionRate,
      periodConsumption: periodConsumption,
      periodCost: periodCost,
      dailyCost: dailyCost,
      monthlyCost: monthlyCost,
      trend,
      efficiency: avgConsumptionRate > 0 ? Math.min(100, (1 / avgConsumptionRate) * 10) : 100
    };
  }, [electricitySummary, chartData, currentElectricity, timeRange, electricityRate]);

  // Initialize chart
  useEffect(() => {
    if (!chartRef.current || !window.VChart) return;

    const spec = {
      type: 'line',
      data: {
        id: 'electricity',
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
            formatMethod: (val: number) => `${val}${electricityField.unit}`
          }
        }
      ],
      line: {
        style: {
          stroke: electricityField.color,
          lineWidth: 2
        }
      },
      point: {
        style: {
          fill: electricityField.color,
          stroke: electricityField.color,
          size: 3
        }
      },
      area: {
        style: {
          fill: electricityField.color,
          fillOpacity: 0.15
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
            value: electricityField.label
          },
          content: {
            key: 'value',
            value: (datum: any) => {
              const cost = datum.value * electricityRate;
              return `${datum.value} ${electricityField.unit} (≈$${cost.toFixed(3)})`;
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
  }, [showLegend, showTooltip, timeRange, electricityField, electricityRate]);

  // Update chart data
  useEffect(() => {
    if (!chartInstanceRef.current || !chartData) return;

    const formattedData = chartData.map(point => ({
      timestamp: new Date(point.timestamp).getTime(),
      value: point.value,
      type: 'electricity'
    }));

    chartInstanceRef.current.updateData('electricity', formattedData);
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
          <p className="text-muted-foreground">Please select a device to view electricity data</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Bolt className="h-5 w-5" style={{ color: electricityField.color }} />
            <CardTitle>{electricityField.label}</CardTitle>
            {isRealTimeEnabled && (
              <Badge variant="secondary" className="text-xs">
                Live
              </Badge>
            )}
            {electricityStats && (
              <Badge
                variant={
                  electricityStats.trend === 'increasing' ? 'destructive' :
                  electricityStats.trend === 'decreasing' ? 'default' : 'secondary'
                }
                className="text-xs"
              >
                {electricityStats.trend}
              </Badge>
            )}
          </div>
          {showCurrentValue && currentElectricity && (
            <div className="text-right">
              <p className="text-2xl font-bold" style={{ color: electricityField.color }}>
                {currentElectricity.value}
              </p>
              <p className="text-sm text-muted-foreground">{electricityField.unit}</p>
            </div>
          )}
        </div>
        <CardDescription>
          Device: {selectedDevice.name} • Range: {TIME_RANGES[timeRange as keyof typeof TIME_RANGES].label}
          {showCostEstimation && ` • Rate: $${electricityRate}/kWh`}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {hasError && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>
              Failed to load electricity data. Please try refreshing.
            </AlertDescription>
          </Alert>
        )}

        {/* Cost and consumption metrics */}
        {showCostEstimation && electricityStats && (
          <div className="mb-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Period</div>
              <div className="text-lg font-semibold" style={{ color: electricityField.color }}>
                {electricityStats.periodConsumption.toFixed(2)} kWh
              </div>
              <div className="text-xs text-muted-foreground">
                ${electricityStats.periodCost.toFixed(2)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Daily Est.</div>
              <div className="text-lg font-semibold text-blue-600">
                ${electricityStats.dailyCost.toFixed(2)}
              </div>
              <div className="text-xs text-muted-foreground">
                ~{(electricityStats.dailyCost / electricityRate).toFixed(1)} kWh
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Monthly Est.</div>
              <div className="text-lg font-semibold text-purple-600">
                ${electricityStats.monthlyCost.toFixed(0)}
              </div>
              <div className="text-xs text-muted-foreground">
                ~{(electricityStats.monthlyCost / electricityRate).toFixed(0)} kWh
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-muted-foreground">Avg Rate</div>
              <div className="text-lg font-semibold text-gray-600">
                {electricityStats.average.toFixed(3)} kWh
              </div>
              <div className="text-xs text-muted-foreground">
                per interval
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
            <p className="text-muted-foreground">No electricity data available</p>
          </div>
        ) : (
          <div ref={chartRef} style={{ height, width: '100%' }} />
        )}

        {showCurrentValue && currentElectricity && (
          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <span>Last reading: {new Date(currentElectricity.timestamp).toLocaleString()}</span>
            <span className="flex items-center">
              <div
                className="w-2 h-2 rounded-full mr-2"
                style={{ backgroundColor: electricityField.color }}
              />
              Current: {currentElectricity.value} {electricityField.unit}
              {showCostEstimation && (
                <span className="ml-2">
                  (${(currentElectricity.value * electricityRate).toFixed(3)})
                </span>
              )}
            </span>
          </div>
        )}

        {showCostEstimation && electricityStats && (
          <div className="mt-4 pt-4 border-t space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-medium flex items-center">
                <DollarSign className="h-4 w-4 mr-1" />
                Cost Analysis
              </span>
              <span className="text-sm text-muted-foreground">
                Rate: ${electricityRate}/kWh
              </span>
            </div>

            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center p-2 bg-blue-50 rounded">
                <div className="font-medium text-blue-700">Today</div>
                <div className="text-lg font-bold text-blue-800">
                  ${electricityStats.dailyCost.toFixed(2)}
                </div>
              </div>
              <div className="text-center p-2 bg-purple-50 rounded">
                <div className="font-medium text-purple-700">This Month</div>
                <div className="text-lg font-bold text-purple-800">
                  ${electricityStats.monthlyCost.toFixed(0)}
                </div>
              </div>
              <div className="text-center p-2 bg-green-50 rounded">
                <div className="font-medium text-green-700">Efficiency</div>
                <div className={`text-lg font-bold ${
                  electricityStats.efficiency >= 80 ? 'text-green-800' :
                  electricityStats.efficiency >= 60 ? 'text-yellow-700' : 'text-red-700'
                }`}>
                  {electricityStats.efficiency.toFixed(0)}%
                </div>
              </div>
            </div>

            <div className="text-xs text-muted-foreground">
              * Estimates based on current consumption patterns and electricity rate of ${electricityRate}/kWh
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}