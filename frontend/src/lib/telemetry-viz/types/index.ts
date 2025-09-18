/**
 * Type definitions for telemetry visualization library
 */

// Core data types
export interface TelemetryDataPoint {
  timestamp: string | Date;
  value: number;
  field: string;
  deviceId: string;
  unit?: string;
  quality?: 'good' | 'fair' | 'poor';
  metadata?: Record<string, any>;
}

export interface TelemetryField {
  name: string;
  displayName: string;
  unit: string;
  type: 'numeric' | 'boolean' | 'string';
  color?: string;
  visible: boolean;
  aggregation?: AggregationType;
  thresholds?: FieldThreshold[];
}

export interface FieldThreshold {
  value: number;
  color: string;
  label: string;
  operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq';
}

// Chart configuration
export interface ChartConfiguration {
  type: ChartType;
  title?: string;
  width?: number | string;
  height?: number | string;
  responsive?: boolean;
  animation?: boolean;
  theme?: ChartThemeOptions;
  axes?: AxisConfiguration;
  legend?: LegendConfiguration;
  tooltip?: TooltipConfiguration;
  zoom?: ZoomConfiguration;
  realtime?: RealtimeConfiguration;
}

export type ChartType =
  | 'line'
  | 'area'
  | 'bar'
  | 'scatter'
  | 'heatmap'
  | 'gauge'
  | 'histogram'
  | 'box'
  | 'candlestick';

export interface AxisConfiguration {
  x?: {
    type?: 'time' | 'numeric' | 'category';
    label?: string;
    min?: number | Date;
    max?: number | Date;
    format?: string;
    grid?: boolean;
    tick?: TickConfiguration;
  };
  y?: {
    type?: 'numeric' | 'log';
    label?: string;
    min?: number;
    max?: number;
    format?: string;
    grid?: boolean;
    tick?: TickConfiguration;
    dual?: boolean;
  };
}

export interface TickConfiguration {
  count?: number;
  interval?: number;
  rotation?: number;
  format?: string;
}

export interface LegendConfiguration {
  show?: boolean;
  position?: 'top' | 'bottom' | 'left' | 'right';
  align?: 'start' | 'center' | 'end';
  interactive?: boolean;
}

export interface TooltipConfiguration {
  show?: boolean;
  format?: string;
  position?: 'follow' | 'fixed';
  template?: string;
}

export interface ZoomConfiguration {
  enabled?: boolean;
  type?: 'x' | 'y' | 'xy';
  resetButton?: boolean;
  wheel?: boolean;
  drag?: boolean;
}

export interface RealtimeConfiguration {
  enabled?: boolean;
  updateInterval?: number;
  maxDataPoints?: number;
  scrolling?: boolean;
  bufferSize?: number;
}

// Theme configuration
export interface ChartThemeOptions {
  name?: string;
  colors?: {
    primary?: string[];
    background?: string;
    text?: string;
    grid?: string;
    axis?: string;
  };
  fonts?: {
    family?: string;
    size?: number;
    weight?: string;
  };
  spacing?: {
    margin?: number | [number, number, number, number];
    padding?: number | [number, number, number, number];
  };
}

// Visualization options
export interface VisualizationOptions {
  timeRange?: TimeRange;
  aggregation?: AggregationOptions;
  filtering?: FilterOptions;
  grouping?: GroupingOptions;
  display?: DisplayOptions;
}

export interface TimeRange {
  start: Date | string;
  end: Date | string;
  relative?: RelativeTimeRange;
}

export interface RelativeTimeRange {
  value: number;
  unit: 'minutes' | 'hours' | 'days' | 'weeks' | 'months';
}

export interface AggregationOptions {
  method: AggregationType;
  interval?: number;
  intervalUnit?: 'seconds' | 'minutes' | 'hours' | 'days';
}

export type AggregationType =
  | 'none'
  | 'avg'
  | 'sum'
  | 'min'
  | 'max'
  | 'count'
  | 'first'
  | 'last'
  | 'median'
  | 'percentile'
  | 'stddev'
  | 'rate';

export interface FilterOptions {
  fields?: string[];
  devices?: string[];
  valueRange?: {
    min?: number;
    max?: number;
  };
  quality?: ('good' | 'fair' | 'poor')[];
  customFilters?: CustomFilter[];
}

export interface CustomFilter {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'nin' | 'regex';
  value: any;
}

export interface GroupingOptions {
  by?: 'field' | 'device' | 'time' | string;
  interval?: number;
  limit?: number;
}

export interface DisplayOptions {
  showPoints?: boolean;
  showLines?: boolean;
  showAreas?: boolean;
  lineWidth?: number;
  pointSize?: number;
  opacity?: number;
  interpolation?: 'linear' | 'step' | 'smooth';
}

// Query and data processing
export interface TelemetryQueryParams {
  deviceIds?: string[];
  fields?: string[];
  timeRange: TimeRange;
  aggregation?: AggregationOptions;
  limit?: number;
  offset?: number;
  orderBy?: 'timestamp' | 'value';
  orderDirection?: 'asc' | 'desc';
}

export interface TelemetryQueryResult {
  data: TelemetryDataPoint[];
  totalCount: number;
  hasMore: boolean;
  queryTime: number;
  cacheHit: boolean;
}

// Chart update and performance
export interface ChartUpdateOptions {
  animation?: boolean;
  duration?: number;
  easing?: string;
  updateMode?: 'replace' | 'append' | 'prepend';
  throttle?: boolean;
  debounce?: number;
}

export interface ChartPerformanceMetrics {
  renderTime: number;
  dataPoints: number;
  fps: number;
  memoryUsage: number;
  updateCount: number;
  lastUpdate: Date;
}

// Export and sharing
export interface ExportOptions {
  format: 'png' | 'svg' | 'pdf' | 'csv' | 'json' | 'excel';
  filename?: string;
  width?: number;
  height?: number;
  quality?: number;
  includeData?: boolean;
  includeMetadata?: boolean;
}

export interface ShareOptions {
  url?: boolean;
  embed?: boolean;
  format?: 'iframe' | 'script' | 'image';
  interactive?: boolean;
  theme?: string;
}

// Dashboard and layout
export interface DashboardLayout {
  columns: number;
  rows: number;
  gap?: number;
  responsive?: boolean;
  widgets: DashboardWidget[];
}

export interface DashboardWidget {
  id: string;
  type: 'chart' | 'metric' | 'text' | 'image';
  title?: string;
  position: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  config: ChartConfiguration | MetricConfiguration | TextConfiguration;
  dataSource?: DataSourceConfiguration;
}

export interface MetricConfiguration {
  field: string;
  aggregation: AggregationType;
  format?: string;
  unit?: string;
  thresholds?: FieldThreshold[];
  trend?: boolean;
  comparison?: ComparisonConfiguration;
}

export interface ComparisonConfiguration {
  type: 'previous' | 'target' | 'baseline';
  value?: number;
  period?: RelativeTimeRange;
}

export interface TextConfiguration {
  content: string;
  style?: {
    fontSize?: number;
    fontWeight?: string;
    color?: string;
    align?: 'left' | 'center' | 'right';
  };
}

export interface DataSourceConfiguration {
  type: 'api' | 'websocket' | 'static';
  url?: string;
  params?: Record<string, any>;
  refreshInterval?: number;
  transformFunction?: string;
}

// Event and interaction types
export interface ChartEvent {
  type: string;
  data?: any;
  chart?: any;
  originalEvent?: Event;
}

export interface ChartInteraction {
  type: 'click' | 'hover' | 'select' | 'zoom' | 'pan';
  handler: (event: ChartEvent) => void;
  options?: any;
}

// Error and validation types
export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ChartError {
  type: 'data' | 'config' | 'render' | 'performance';
  message: string;
  details?: any;
  timestamp: Date;
}

// Plugin and extension types
export interface ChartPlugin {
  name: string;
  version: string;
  init: (chart: any, options?: any) => void;
  destroy?: (chart: any) => void;
  update?: (chart: any, data: any) => void;
}

export interface ChartExtension {
  name: string;
  type: 'renderer' | 'interaction' | 'data' | 'export';
  handler: (...args: any[]) => any;
  options?: any;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredKeys<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;

export type ChartEventHandler<T = any> = (event: ChartEvent & { data: T }) => void;

export type DataProcessor<TInput = any, TOutput = any> = (data: TInput) => TOutput;

export type ColorScale = string[] | ((value: number) => string);

export type TimeFormatter = (date: Date) => string;

export type ValueFormatter = (value: number, unit?: string) => string;