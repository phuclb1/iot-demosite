/**
 * TelemetryChart Component
 *
 * A comprehensive chart component for displaying telemetry data with support for
 * multiple chart types, real-time updates, and performance optimization.
 */

import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { LineChart } from '../charts/LineChart';
import { AreaChart } from '../charts/AreaChart';
import { BarChart } from '../charts/BarChart';
import { ScatterChart } from '../charts/ScatterChart';
import { HeatmapChart } from '../charts/HeatmapChart';
import { GaugeChart } from '../charts/GaugeChart';
import { useChartPerformance } from '../hooks/useChartPerformance';
import { TelemetryProcessor } from '../processors/TelemetryProcessor';
import { PerformanceMonitor } from '../utils/PerformanceMonitor';
import type {
  TelemetryDataPoint,
  ChartConfiguration,
  ChartUpdateOptions,
  ChartEvent,
  ChartInteraction,
  ChartError
} from '../types';

interface TelemetryChartProps {
  data: TelemetryDataPoint[];
  config: ChartConfiguration;
  className?: string;
  style?: React.CSSProperties;
  onUpdate?: (data: TelemetryDataPoint[]) => void;
  onError?: (error: ChartError) => void;
  onInteraction?: (event: ChartEvent) => void;
  interactions?: ChartInteraction[];
  updateOptions?: ChartUpdateOptions;
  autoResize?: boolean;
  debug?: boolean;
}

export const TelemetryChart: React.FC<TelemetryChartProps> = ({
  data,
  config,
  className,
  style,
  onUpdate,
  onError,
  onInteraction,
  interactions = [],
  updateOptions = {},
  autoResize = true,
  debug = false
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const processorRef = useRef<TelemetryProcessor>();
  const performanceMonitorRef = useRef<PerformanceMonitor>();

  // State
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ChartError | null>(null);
  const [chartInstance, setChartInstance] = useState<any>(null);

  // Performance monitoring
  const { metrics, recordMetric } = useChartPerformance({
    enabled: debug,
    onPerformanceIssue: (issue) => {
      console.warn('Chart performance issue:', issue);
    }
  });

  // Initialize processor and performance monitor
  useEffect(() => {
    processorRef.current = new TelemetryProcessor({
      enableCaching: true,
      cacheSize: 1000,
      enableValidation: true
    });

    if (debug) {
      performanceMonitorRef.current = new PerformanceMonitor();
    }

    return () => {
      processorRef.current?.cleanup();
      performanceMonitorRef.current?.stop();
    };
  }, [debug]);

  // Process data
  const processedData = useMemo(() => {
    if (!processorRef.current) return data;

    const startTime = performance.now();

    try {
      const processed = processorRef.current.processData(data, {
        aggregation: config.realtime?.enabled ? undefined : {
          method: 'none',
          interval: 1,
          intervalUnit: 'minutes'
        },
        filtering: {
          quality: ['good', 'fair'] // Filter out poor quality data
        },
        sorting: {
          field: 'timestamp',
          direction: 'asc'
        }
      });

      const processingTime = performance.now() - startTime;
      recordMetric('dataProcessing', processingTime);

      return processed;

    } catch (error) {
      const chartError: ChartError = {
        type: 'data',
        message: `Data processing failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        details: error,
        timestamp: new Date()
      };

      setError(chartError);
      onError?.(chartError);
      return data; // Fallback to original data
    }
  }, [data, config.realtime?.enabled, recordMetric, onError]);

  // Chart component selection
  const ChartComponent = useMemo(() => {
    switch (config.type) {
      case 'line':
        return LineChart;
      case 'area':
        return AreaChart;
      case 'bar':
        return BarChart;
      case 'scatter':
        return ScatterChart;
      case 'heatmap':
        return HeatmapChart;
      case 'gauge':
        return GaugeChart;
      default:
        return LineChart; // Default fallback
    }
  }, [config.type]);

  // Handle chart events
  const handleChartEvent = useCallback((event: ChartEvent) => {
    onInteraction?.(event);

    // Handle specific event types
    switch (event.type) {
      case 'dataUpdate':
        onUpdate?.(event.data);
        break;
      case 'error':
        const chartError: ChartError = {
          type: 'render',
          message: event.data?.message || 'Chart rendering error',
          details: event.data,
          timestamp: new Date()
        };
        setError(chartError);
        onError?.(chartError);
        break;
      default:
        break;
    }
  }, [onInteraction, onUpdate, onError]);

  // Handle resize
  const handleResize = useCallback(() => {
    if (chartInstance && autoResize) {
      try {
        chartInstance.resize();
      } catch (error) {
        console.warn('Chart resize failed:', error);
      }
    }
  }, [chartInstance, autoResize]);

  // Setup resize observer
  useEffect(() => {
    if (!autoResize || !containerRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [handleResize, autoResize]);

  // Setup interactions
  useEffect(() => {
    if (!chartInstance) return;

    const cleanup: (() => void)[] = [];

    interactions.forEach(interaction => {
      try {
        const handler = (event: ChartEvent) => {
          handleChartEvent(event);
          interaction.handler(event);
        };

        // Register interaction with chart
        if (chartInstance.on) {
          chartInstance.on(interaction.type, handler);
          cleanup.push(() => chartInstance.off(interaction.type, handler));
        }
      } catch (error) {
        console.warn(`Failed to register interaction ${interaction.type}:`, error);
      }
    });

    return () => {
      cleanup.forEach(fn => fn());
    };
  }, [chartInstance, interactions, handleChartEvent]);

  // Handle loading state
  useEffect(() => {
    if (processedData.length === 0) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const timer = setTimeout(() => setIsLoading(false), 100);

    return () => clearTimeout(timer);
  }, [processedData]);

  // Clear error when data changes
  useEffect(() => {
    setError(null);
  }, [data]);

  // Chart style with responsive sizing
  const chartStyle: React.CSSProperties = {
    width: config.width || '100%',
    height: config.height || '400px',
    ...style
  };

  return (
    <div
      ref={containerRef}
      className={`telemetry-chart ${className || ''}`}
      style={chartStyle}
      data-chart-type={config.type}
      data-loading={isLoading}
      data-error={!!error}
    >
      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/50 z-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Error display */}
      {error && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-red-50 z-10">
          <div className="text-center p-4">
            <div className="text-red-600 font-medium mb-2">Chart Error</div>
            <div className="text-red-500 text-sm">{error.message}</div>
            <button
              onClick={() => setError(null)}
              className="mt-2 px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Chart component */}
      {!error && (
        <ChartComponent
          ref={chartRef}
          data={processedData}
          config={config}
          updateOptions={updateOptions}
          onEvent={handleChartEvent}
          onInit={setChartInstance}
          className="w-full h-full"
        />
      )}

      {/* Debug panel */}
      {debug && metrics && (
        <div className="absolute top-2 right-2 bg-black/80 text-white text-xs p-2 rounded z-20">
          <div>FPS: {metrics.fps}</div>
          <div>Render: {metrics.renderTime.toFixed(1)}ms</div>
          <div>Points: {processedData.length}</div>
          <div>Memory: {(metrics.memoryUsage / 1024 / 1024).toFixed(1)}MB</div>
        </div>
      )}

      {/* Chart title */}
      {config.title && (
        <div className="absolute top-2 left-2 text-lg font-medium text-gray-800 z-10">
          {config.title}
        </div>
      )}
    </div>
  );
};

export default TelemetryChart;