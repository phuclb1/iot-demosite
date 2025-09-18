/**
 * LineChart Component
 *
 * High-performance line chart implementation using VisActor/VChart
 * with support for real-time data updates and interactive features.
 */

import React, { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { VChart } from '@visactor/vchart';
import type { ILineChartSpec } from '@visactor/vchart';
import { useThrottledUpdate } from '@/hooks/useThrottledUpdate';
import type {
  TelemetryDataPoint,
  ChartConfiguration,
  ChartUpdateOptions,
  ChartEvent
} from '../types';

interface LineChartProps {
  data: TelemetryDataPoint[];
  config: ChartConfiguration;
  updateOptions?: ChartUpdateOptions;
  onEvent?: (event: ChartEvent) => void;
  onInit?: (chart: VChart) => void;
  className?: string;
}

export interface LineChartRef {
  getChart: () => VChart | null;
  updateData: (data: TelemetryDataPoint[]) => void;
  resize: () => void;
  exportChart: (format: string) => Promise<string>;
}

export const LineChart = forwardRef<LineChartRef, LineChartProps>(({
  data,
  config,
  updateOptions = {},
  onEvent,
  onInit,
  className
}, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<VChart | null>(null);

  // Throttled data updates for performance
  const [throttledData, updateThrottledData] = useThrottledUpdate(data, {
    delay: config.realtime?.updateInterval || 200,
    leading: true,
    trailing: true
  });

  // Transform telemetry data to VChart format
  const transformData = (telemetryData: TelemetryDataPoint[]) => {
    const dataByField = new Map<string, any[]>();

    telemetryData.forEach(point => {
      if (!dataByField.has(point.field)) {
        dataByField.set(point.field, []);
      }

      dataByField.get(point.field)!.push({
        x: new Date(point.timestamp).getTime(),
        y: point.value,
        field: point.field,
        deviceId: point.deviceId,
        unit: point.unit,
        quality: point.quality,
        timestamp: point.timestamp
      });
    });

    return Array.from(dataByField.entries()).map(([field, values]) => ({
      name: field,
      values: values.sort((a, b) => a.x - b.x)
    }));
  };

  // Create chart specification
  const createChartSpec = (chartData: any[]): ILineChartSpec => {
    const fields = chartData.map(d => d.name);
    const allValues = chartData.flatMap(d => d.values);

    return {
      type: 'line',
      data: chartData,
      xField: 'x',
      yField: 'y',
      seriesField: 'field',

      // Axes configuration
      axes: [
        {
          orient: 'bottom',
          type: 'time',
          label: {
            formatMethod: (value: number) => {
              const date = new Date(value);
              if (config.axes?.x?.format) {
                return config.axes.x.format; // Custom format would need implementation
              }
              return date.toLocaleTimeString();
            }
          },
          grid: config.axes?.x?.grid !== false,
          title: {
            visible: !!config.axes?.x?.label,
            text: config.axes?.x?.label || ''
          }
        },
        {
          orient: 'left',
          type: 'linear',
          label: {
            formatMethod: (value: number) => {
              if (config.axes?.y?.format) {
                return config.axes.y.format; // Custom format would need implementation
              }
              return value.toLocaleString();
            }
          },
          grid: config.axes?.y?.grid !== false,
          title: {
            visible: !!config.axes?.y?.label,
            text: config.axes?.y?.label || ''
          },
          min: config.axes?.y?.min,
          max: config.axes?.y?.max
        }
      ],

      // Series styling
      line: {
        style: {
          lineWidth: 2,
          lineDash: [0]
        }
      },

      // Point styling
      point: {
        visible: config.realtime?.enabled ? false : true, // Hide points in real-time mode for performance
        style: {
          size: 4,
          stroke: '#fff',
          strokeWidth: 1
        }
      },

      // Color scheme
      color: config.theme?.colors?.primary || [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
      ],

      // Legend
      legends: config.legend?.show !== false ? [{
        visible: true,
        position: config.legend?.position || 'top',
        orient: 'horizontal',
        interactive: config.legend?.interactive !== false
      }] : [],

      // Tooltip
      tooltip: config.tooltip?.show !== false ? {
        visible: true,
        mark: {
          title: {
            key: 'field',
            value: 'field'
          },
          content: [
            {
              key: 'timestamp',
              value: (datum: any) => new Date(datum.x).toLocaleString()
            },
            {
              key: 'value',
              value: (datum: any) => `${datum.y} ${datum.unit || ''}`
            },
            {
              key: 'device',
              value: 'deviceId'
            },
            {
              key: 'quality',
              value: 'quality'
            }
          ]
        }
      } : undefined,

      // Animation
      animation: config.animation !== false ? {
        appear: {
          duration: 1000,
          easing: 'cubicOut'
        },
        update: {
          duration: updateOptions.duration || 300,
          easing: updateOptions.easing || 'linear'
        }
      } : false,

      // Zoom and pan
      brush: config.zoom?.enabled ? {
        brushType: config.zoom.type === 'x' ? 'x' : config.zoom.type === 'y' ? 'y' : 'xy',
        inBrush: {
          colorAlpha: 1
        },
        outOfBrush: {
          colorAlpha: 0.2
        }
      } : undefined,

      // Theme
      theme: config.theme?.name || 'light',

      // Performance optimizations
      morphConfig: {
        morph: config.realtime?.enabled ? false : true // Disable morphing for real-time
      },

      // Background
      background: config.theme?.colors?.background || 'transparent'
    };
  };

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    const chartData = transformData(throttledData);
    const spec = createChartSpec(chartData);

    try {
      const chart = new VChart(spec, {
        dom: containerRef.current,
        mode: 'desktop-browser',
        logLevel: 0 // Suppress logs in production
      });

      chartRef.current = chart;

      // Setup event handlers
      chart.on('click', (params: any) => {
        onEvent?.({
          type: 'click',
          data: params.datum,
          chart,
          originalEvent: params.event
        });
      });

      chart.on('mouseover', (params: any) => {
        onEvent?.({
          type: 'hover',
          data: params.datum,
          chart,
          originalEvent: params.event
        });
      });

      // Render chart
      chart.renderAsync().then(() => {
        onInit?.(chart);
        onEvent?.({
          type: 'init',
          chart
        });
      }).catch((error: any) => {
        onEvent?.({
          type: 'error',
          data: { message: 'Chart initialization failed', error },
          chart
        });
      });

      return () => {
        try {
          chart.release();
        } catch (error) {
          console.warn('Error releasing chart:', error);
        }
      };
    } catch (error) {
      onEvent?.({
        type: 'error',
        data: { message: 'Chart creation failed', error }
      });
    }
  }, [throttledData, config, onEvent, onInit, updateOptions]);

  // Update data when it changes
  useEffect(() => {
    updateThrottledData(data);
  }, [data, updateThrottledData]);

  // Update chart data
  const updateChart = (newData: TelemetryDataPoint[]) => {
    if (!chartRef.current) return;

    try {
      const chartData = transformData(newData);

      if (config.realtime?.enabled && updateOptions.updateMode === 'append') {
        // For real-time mode, we might want to append data efficiently
        // This would require more sophisticated data management
        chartRef.current.updateData('data', chartData);
      } else {
        // Replace all data
        chartRef.current.updateData('data', chartData);
      }

      onEvent?.({
        type: 'dataUpdate',
        data: newData,
        chart: chartRef.current
      });
    } catch (error) {
      onEvent?.({
        type: 'error',
        data: { message: 'Chart data update failed', error },
        chart: chartRef.current
      });
    }
  };

  // Resize chart
  const resizeChart = () => {
    if (chartRef.current && containerRef.current) {
      try {
        const { width, height } = containerRef.current.getBoundingClientRect();
        chartRef.current.resize(width, height);
      } catch (error) {
        console.warn('Chart resize failed:', error);
      }
    }
  };

  // Export chart
  const exportChart = async (format: string): Promise<string> => {
    if (!chartRef.current) {
      throw new Error('Chart not initialized');
    }

    try {
      if (format === 'png' || format === 'svg') {
        return await chartRef.current.exportImg(format);
      } else {
        throw new Error(`Export format ${format} not supported`);
      }
    } catch (error) {
      throw new Error(`Chart export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Expose methods through ref
  useImperativeHandle(ref, () => ({
    getChart: () => chartRef.current,
    updateData: updateChart,
    resize: resizeChart,
    exportChart
  }), []);

  return (
    <div
      ref={containerRef}
      className={`line-chart ${className || ''}`}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '200px'
      }}
    />
  );
});

LineChart.displayName = 'LineChart';

export default LineChart;