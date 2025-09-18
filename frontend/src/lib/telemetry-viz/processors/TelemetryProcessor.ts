/**
 * TelemetryProcessor
 *
 * Core data processing engine for telemetry data with support for
 * aggregation, filtering, transformation, and caching.
 */

import type {
  TelemetryDataPoint,
  TelemetryField,
  AggregationType,
  FilterOptions,
  AggregationOptions,
  GroupingOptions
} from '../types';

interface ProcessingOptions {
  aggregation?: AggregationOptions;
  filtering?: FilterOptions;
  grouping?: GroupingOptions;
  sorting?: {
    field: 'timestamp' | 'value' | 'field' | 'deviceId';
    direction: 'asc' | 'desc';
  };
  limit?: number;
  caching?: boolean;
}

interface ProcessorConfig {
  enableCaching?: boolean;
  cacheSize?: number;
  enableValidation?: boolean;
  enablePerformanceTracking?: boolean;
}

interface ProcessingStats {
  lastProcessingTime: number;
  totalProcessed: number;
  cacheHits: number;
  cacheMisses: number;
  errorCount: number;
}

export class TelemetryProcessor {
  private cache = new Map<string, any>();
  private stats: ProcessingStats = {
    lastProcessingTime: 0,
    totalProcessed: 0,
    cacheHits: 0,
    cacheMisses: 0,
    errorCount: 0
  };

  constructor(private config: ProcessorConfig = {}) {
    this.config = {
      enableCaching: true,
      cacheSize: 1000,
      enableValidation: true,
      enablePerformanceTracking: true,
      ...config
    };
  }

  /**
   * Process telemetry data with specified options
   */
  processData(data: TelemetryDataPoint[], options: ProcessingOptions = {}): TelemetryDataPoint[] {
    const startTime = performance.now();

    try {
      // Generate cache key
      const cacheKey = this.generateCacheKey(data, options);

      // Check cache
      if (this.config.enableCaching && this.cache.has(cacheKey)) {
        this.stats.cacheHits++;
        return this.cache.get(cacheKey);
      }

      this.stats.cacheMisses++;

      // Validate input data
      if (this.config.enableValidation) {
        this.validateData(data);
      }

      let processedData = [...data];

      // Apply filtering
      if (options.filtering) {
        processedData = this.applyFilters(processedData, options.filtering);
      }

      // Apply grouping
      if (options.grouping) {
        processedData = this.applyGrouping(processedData, options.grouping);
      }

      // Apply aggregation
      if (options.aggregation && options.aggregation.method !== 'none') {
        processedData = this.applyAggregation(processedData, options.aggregation);
      }

      // Apply sorting
      if (options.sorting) {
        processedData = this.applySorting(processedData, options.sorting);
      }

      // Apply limit
      if (options.limit && options.limit > 0) {
        processedData = processedData.slice(0, options.limit);
      }

      // Cache result
      if (this.config.enableCaching) {
        this.cacheResult(cacheKey, processedData);
      }

      // Update stats
      this.stats.totalProcessed++;
      if (this.config.enablePerformanceTracking) {
        this.stats.lastProcessingTime = performance.now() - startTime;
      }

      return processedData;

    } catch (error) {
      this.stats.errorCount++;
      console.error('Data processing failed:', error);
      return data; // Return original data on error
    }
  }

  /**
   * Apply filters to telemetry data
   */
  private applyFilters(data: TelemetryDataPoint[], filters: FilterOptions): TelemetryDataPoint[] {
    return data.filter(point => {
      // Field filter
      if (filters.fields && !filters.fields.includes(point.field)) {
        return false;
      }

      // Device filter
      if (filters.devices && !filters.devices.includes(point.deviceId)) {
        return false;
      }

      // Value range filter
      if (filters.valueRange) {
        if (filters.valueRange.min !== undefined && point.value < filters.valueRange.min) {
          return false;
        }
        if (filters.valueRange.max !== undefined && point.value > filters.valueRange.max) {
          return false;
        }
      }

      // Quality filter
      if (filters.quality && point.quality && !filters.quality.includes(point.quality)) {
        return false;
      }

      // Custom filters
      if (filters.customFilters) {
        for (const customFilter of filters.customFilters) {
          if (!this.applyCustomFilter(point, customFilter)) {
            return false;
          }
        }
      }

      return true;
    });
  }

  /**
   * Apply custom filter to a data point
   */
  private applyCustomFilter(point: TelemetryDataPoint, filter: FilterOptions['customFilters'][0]): boolean {
    const fieldValue = this.getFieldValue(point, filter.field);

    switch (filter.operator) {
      case 'eq':
        return fieldValue === filter.value;
      case 'ne':
        return fieldValue !== filter.value;
      case 'gt':
        return fieldValue > filter.value;
      case 'gte':
        return fieldValue >= filter.value;
      case 'lt':
        return fieldValue < filter.value;
      case 'lte':
        return fieldValue <= filter.value;
      case 'in':
        return Array.isArray(filter.value) && filter.value.includes(fieldValue);
      case 'nin':
        return Array.isArray(filter.value) && !filter.value.includes(fieldValue);
      case 'regex':
        return new RegExp(filter.value).test(String(fieldValue));
      default:
        return true;
    }
  }

  /**
   * Apply grouping to telemetry data
   */
  private applyGrouping(data: TelemetryDataPoint[], grouping: GroupingOptions): TelemetryDataPoint[] {
    if (!grouping.by) return data;

    const groups = new Map<string, TelemetryDataPoint[]>();

    data.forEach(point => {
      let groupKey: string;

      switch (grouping.by) {
        case 'field':
          groupKey = point.field;
          break;
        case 'device':
          groupKey = point.deviceId;
          break;
        case 'time':
          // Group by time intervals
          const timestamp = new Date(point.timestamp);
          const interval = grouping.interval || 60000; // Default 1 minute
          const roundedTime = Math.floor(timestamp.getTime() / interval) * interval;
          groupKey = new Date(roundedTime).toISOString();
          break;
        default:
          groupKey = this.getFieldValue(point, grouping.by) || 'unknown';
          break;
      }

      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)!.push(point);
    });

    // Flatten groups back to array
    let result: TelemetryDataPoint[] = [];
    groups.forEach(group => {
      result = result.concat(group);
    });

    // Apply limit if specified
    if (grouping.limit) {
      result = result.slice(0, grouping.limit);
    }

    return result;
  }

  /**
   * Apply aggregation to telemetry data
   */
  private applyAggregation(data: TelemetryDataPoint[], aggregation: AggregationOptions): TelemetryDataPoint[] {
    if (!aggregation.interval || !aggregation.intervalUnit) {
      // Aggregate all data into single points per field
      return this.aggregateByField(data, aggregation.method);
    }

    // Time-based aggregation
    return this.aggregateByTime(data, aggregation);
  }

  /**
   * Aggregate data by field
   */
  private aggregateByField(data: TelemetryDataPoint[], method: AggregationType): TelemetryDataPoint[] {
    const fieldGroups = new Map<string, TelemetryDataPoint[]>();

    // Group by field
    data.forEach(point => {
      if (!fieldGroups.has(point.field)) {
        fieldGroups.set(point.field, []);
      }
      fieldGroups.get(point.field)!.push(point);
    });

    // Aggregate each field group
    const result: TelemetryDataPoint[] = [];
    fieldGroups.forEach((points, field) => {
      const aggregatedPoint = this.aggregatePoints(points, method);
      if (aggregatedPoint) {
        result.push(aggregatedPoint);
      }
    });

    return result;
  }

  /**
   * Aggregate data by time intervals
   */
  private aggregateByTime(data: TelemetryDataPoint[], aggregation: AggregationOptions): TelemetryDataPoint[] {
    const intervalMs = this.getIntervalInMs(aggregation.interval!, aggregation.intervalUnit!);
    const timeGroups = new Map<string, Map<string, TelemetryDataPoint[]>>();

    // Group by time intervals and field
    data.forEach(point => {
      const timestamp = new Date(point.timestamp);
      const intervalStart = Math.floor(timestamp.getTime() / intervalMs) * intervalMs;
      const intervalKey = new Date(intervalStart).toISOString();

      if (!timeGroups.has(intervalKey)) {
        timeGroups.set(intervalKey, new Map());
      }

      const fieldGroups = timeGroups.get(intervalKey)!;
      if (!fieldGroups.has(point.field)) {
        fieldGroups.set(point.field, []);
      }

      fieldGroups.get(point.field)!.push(point);
    });

    // Aggregate each group
    const result: TelemetryDataPoint[] = [];
    timeGroups.forEach((fieldGroups, timeKey) => {
      fieldGroups.forEach((points, field) => {
        const aggregatedPoint = this.aggregatePoints(points, aggregation.method);
        if (aggregatedPoint) {
          aggregatedPoint.timestamp = timeKey;
          result.push(aggregatedPoint);
        }
      });
    });

    return result;
  }

  /**
   * Aggregate a group of points using specified method
   */
  private aggregatePoints(points: TelemetryDataPoint[], method: AggregationType): TelemetryDataPoint | null {
    if (points.length === 0) return null;

    const values = points.map(p => p.value).filter(v => !isNaN(v));
    if (values.length === 0) return null;

    let aggregatedValue: number;

    switch (method) {
      case 'avg':
        aggregatedValue = values.reduce((sum, v) => sum + v, 0) / values.length;
        break;
      case 'sum':
        aggregatedValue = values.reduce((sum, v) => sum + v, 0);
        break;
      case 'min':
        aggregatedValue = Math.min(...values);
        break;
      case 'max':
        aggregatedValue = Math.max(...values);
        break;
      case 'count':
        aggregatedValue = values.length;
        break;
      case 'first':
        aggregatedValue = points[0].value;
        break;
      case 'last':
        aggregatedValue = points[points.length - 1].value;
        break;
      case 'median':
        const sorted = values.sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        aggregatedValue = sorted.length % 2 === 0
          ? (sorted[mid - 1] + sorted[mid]) / 2
          : sorted[mid];
        break;
      case 'stddev':
        const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
        const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
        aggregatedValue = Math.sqrt(variance);
        break;
      default:
        aggregatedValue = values[0];
        break;
    }

    // Return aggregated point based on first point in group
    const basePoint = points[0];
    return {
      ...basePoint,
      value: aggregatedValue,
      metadata: {
        ...basePoint.metadata,
        aggregation: {
          method,
          pointCount: points.length,
          originalValues: values
        }
      }
    };
  }

  /**
   * Apply sorting to telemetry data
   */
  private applySorting(data: TelemetryDataPoint[], sorting: ProcessingOptions['sorting']): TelemetryDataPoint[] {
    if (!sorting) return data;

    return [...data].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sorting.field) {
        case 'timestamp':
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
          break;
        case 'value':
          aValue = a.value;
          bValue = b.value;
          break;
        case 'field':
          aValue = a.field;
          bValue = b.field;
          break;
        case 'deviceId':
          aValue = a.deviceId;
          bValue = b.deviceId;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sorting.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sorting.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }

  /**
   * Validate telemetry data
   */
  private validateData(data: TelemetryDataPoint[]): void {
    if (!Array.isArray(data)) {
      throw new Error('Data must be an array');
    }

    data.forEach((point, index) => {
      if (!point.timestamp) {
        throw new Error(`Data point ${index} missing timestamp`);
      }
      if (typeof point.value !== 'number' || isNaN(point.value)) {
        throw new Error(`Data point ${index} has invalid value`);
      }
      if (!point.field) {
        throw new Error(`Data point ${index} missing field`);
      }
      if (!point.deviceId) {
        throw new Error(`Data point ${index} missing deviceId`);
      }
    });
  }

  /**
   * Generate cache key for processed data
   */
  private generateCacheKey(data: TelemetryDataPoint[], options: ProcessingOptions): string {
    const dataHash = this.hashData(data);
    const optionsHash = this.hashObject(options);
    return `${dataHash}_${optionsHash}`;
  }

  /**
   * Cache processed result
   */
  private cacheResult(key: string, result: TelemetryDataPoint[]): void {
    if (this.cache.size >= (this.config.cacheSize || 1000)) {
      // Remove oldest entry
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, result);
  }

  /**
   * Get field value from data point
   */
  private getFieldValue(point: TelemetryDataPoint, fieldPath: string): any {
    const keys = fieldPath.split('.');
    let value: any = point;

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return undefined;
      }
    }

    return value;
  }

  /**
   * Convert interval to milliseconds
   */
  private getIntervalInMs(interval: number, unit: string): number {
    const multipliers = {
      seconds: 1000,
      minutes: 60 * 1000,
      hours: 60 * 60 * 1000,
      days: 24 * 60 * 60 * 1000
    };

    return interval * (multipliers[unit as keyof typeof multipliers] || 1000);
  }

  /**
   * Simple hash function for data
   */
  private hashData(data: TelemetryDataPoint[]): string {
    if (data.length === 0) return '0';

    const sample = data.length > 100 ?
      [data[0], data[Math.floor(data.length / 2)], data[data.length - 1]] :
      data;

    return sample.map(p => `${p.timestamp}_${p.value}_${p.field}_${p.deviceId}`).join('|');
  }

  /**
   * Simple hash function for objects
   */
  private hashObject(obj: any): string {
    return JSON.stringify(obj);
  }

  /**
   * Get processing statistics
   */
  getStats(): ProcessingStats {
    return { ...this.stats };
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
    this.stats.cacheHits = 0;
    this.stats.cacheMisses = 0;
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.clearCache();
  }
}