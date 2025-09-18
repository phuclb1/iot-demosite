/**
 * Telemetry Visualization Library
 *
 * A comprehensive library for visualizing IoT telemetry data with support for
 * real-time updates, multiple chart types, and performance optimization.
 */

// Core components
export { TelemetryChart } from './components/TelemetryChart';
export { TelemetryDashboard } from './components/TelemetryDashboard';
export { TelemetryMetrics } from './components/TelemetryMetrics';
export { TelemetryControls } from './components/TelemetryControls';

// Chart types
export { LineChart } from './charts/LineChart';
export { AreaChart } from './charts/AreaChart';
export { BarChart } from './charts/BarChart';
export { ScatterChart } from './charts/ScatterChart';
export { HeatmapChart } from './charts/HeatmapChart';
export { GaugeChart } from './charts/GaugeChart';

// Data processing
export { TelemetryProcessor } from './processors/TelemetryProcessor';
export { DataAggregator } from './processors/DataAggregator';
export { DataFilter } from './processors/DataFilter';
export { DataTransformer } from './processors/DataTransformer';

// Configuration and themes
export { ChartTheme, createChartTheme } from './themes/ChartTheme';
export { ChartConfig } from './config/ChartConfig';

// Utilities
export { TelemetryUtils } from './utils/TelemetryUtils';
export { PerformanceMonitor } from './utils/PerformanceMonitor';
export { ExportUtils } from './utils/ExportUtils';

// Hooks
export { useTelemetryChart } from './hooks/useTelemetryChart';
export { useTelemetryData } from './hooks/useTelemetryData';
export { useChartPerformance } from './hooks/useChartPerformance';

// Types
export type {
  TelemetryDataPoint,
  TelemetryField,
  ChartConfiguration,
  VisualizationOptions,
  TelemetryQueryParams,
  ChartUpdateOptions,
  ExportOptions
} from './types';

// CLI (for library management)
export { cli } from './cli';

// Constants
export const LIBRARY_VERSION = '1.0.0';
export const SUPPORTED_CHART_TYPES = [
  'line',
  'area',
  'bar',
  'scatter',
  'heatmap',
  'gauge'
] as const;