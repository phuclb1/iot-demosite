/**
 * Chart data update throttling hook (200ms).
 *
 * Optimizes chart performance by throttling rapid data updates to maintain
 * smooth 60fps rendering while handling high-frequency real-time data streams.
 */

import { useCallback, useRef, useEffect, useState } from 'react';

export interface ThrottleOptions {
  delay: number;
  leading?: boolean;
  trailing?: boolean;
  maxWait?: number;
}

export interface ThrottledUpdateState<T> {
  value: T;
  isThrottling: boolean;
  pendingUpdate: boolean;
  updateCount: number;
  droppedCount: number;
  lastUpdateTime: number | null;
  averageInterval: number;
}

const DEFAULT_THROTTLE_OPTIONS: Required<ThrottleOptions> = {
  delay: 200,
  leading: true,
  trailing: true,
  maxWait: 1000,
};

/**
 * Generic throttling hook for any value updates.
 */
export function useThrottledUpdate<T>(
  initialValue: T,
  options: Partial<ThrottleOptions> = {}
): [ThrottledUpdateState<T>, (newValue: T) => void, () => void] {
  const opts = { ...DEFAULT_THROTTLE_OPTIONS, ...options };

  const [state, setState] = useState<ThrottledUpdateState<T>>({
    value: initialValue,
    isThrottling: false,
    pendingUpdate: false,
    updateCount: 0,
    droppedCount: 0,
    lastUpdateTime: null,
    averageInterval: 0,
  });

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastCallTimeRef = useRef<number>(0);
  const lastInvokeTimeRef = useRef<number>(0);
  const pendingValueRef = useRef<T>(initialValue);
  const intervalsRef = useRef<number[]>([]);

  const updateValue = useCallback((newValue: T, fromTimeout = false) => {
    const now = Date.now();

    setState(prev => {
      const intervals = intervalsRef.current;

      // Calculate average interval
      if (prev.lastUpdateTime) {
        const interval = now - prev.lastUpdateTime;
        intervals.push(interval);

        // Keep only last 20 intervals for rolling average
        if (intervals.length > 20) {
          intervals.shift();
        }
      }

      const averageInterval = intervals.length > 0
        ? intervals.reduce((sum, i) => sum + i, 0) / intervals.length
        : 0;

      return {
        ...prev,
        value: newValue,
        isThrottling: false,
        pendingUpdate: false,
        updateCount: prev.updateCount + 1,
        lastUpdateTime: now,
        averageInterval,
      };
    });

    lastInvokeTimeRef.current = now;
  }, []);

  const throttledUpdate = useCallback((newValue: T) => {
    const now = Date.now();
    const timeSinceLastCall = now - lastCallTimeRef.current;
    const timeSinceLastInvoke = now - lastInvokeTimeRef.current;

    lastCallTimeRef.current = now;
    pendingValueRef.current = newValue;

    // Leading edge
    if (timeSinceLastInvoke >= opts.delay) {
      if (opts.leading) {
        updateValue(newValue);
        return;
      }
    }

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    // Set throttling state
    setState(prev => ({
      ...prev,
      isThrottling: true,
      pendingUpdate: true,
      droppedCount: prev.droppedCount + (prev.pendingUpdate ? 1 : 0),
    }));

    // Calculate delay for next execution
    const remainingWait = opts.delay - timeSinceLastInvoke;
    const delay = Math.max(remainingWait, 0);

    // Check if we should invoke due to maxWait
    const shouldInvokeNow = opts.maxWait && timeSinceLastInvoke >= opts.maxWait;

    if (shouldInvokeNow) {
      updateValue(newValue);
    } else if (opts.trailing) {
      timeoutRef.current = setTimeout(() => {
        updateValue(pendingValueRef.current, true);
        timeoutRef.current = null;
      }, delay);
    }
  }, [opts.delay, opts.leading, opts.trailing, opts.maxWait, updateValue]);

  const flush = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
      updateValue(pendingValueRef.current);
    }
  }, [updateValue]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return [state, throttledUpdate, flush];
}

/**
 * Specialized hook for chart data updates with performance monitoring.
 */
export function useChartDataThrottling<T>(
  initialData: T,
  updateInterval: number = 200
): {
  data: T;
  updateData: (newData: T) => void;
  stats: {
    updateRate: number;
    droppedRate: number;
    averageInterval: number;
    isPerformant: boolean;
  };
  flush: () => void;
} {
  const [throttledState, updateThrottled, flush] = useThrottledUpdate(initialData, {
    delay: updateInterval,
    leading: true,
    trailing: true,
    maxWait: updateInterval * 2,
  });

  const stats = {
    updateRate: throttledState.averageInterval > 0 ? 1000 / throttledState.averageInterval : 0,
    droppedRate: throttledState.updateCount > 0 ? throttledState.droppedCount / throttledState.updateCount : 0,
    averageInterval: throttledState.averageInterval,
    isPerformant: throttledState.averageInterval >= updateInterval * 0.8, // Within 80% of target
  };

  return {
    data: throttledState.value,
    updateData: updateThrottled,
    stats,
    flush,
  };
}

/**
 * Hook for throttling array data updates (like time series).
 */
export function useTimeSeriesThrottling<T>(
  initialSeries: T[],
  maxPoints: number = 1000,
  updateInterval: number = 200
): {
  series: T[];
  appendData: (newPoint: T) => void;
  updateSeries: (newSeries: T[]) => void;
  stats: {
    pointCount: number;
    updateRate: number;
    memoryUsage: string;
  };
  flush: () => void;
} {
  const [throttledState, updateThrottled, flush] = useThrottledUpdate(initialSeries, {
    delay: updateInterval,
    leading: true,
    trailing: true,
  });

  const appendData = useCallback((newPoint: T) => {
    const newSeries = [...throttledState.value, newPoint];

    // Trim to max points to prevent memory issues
    const trimmedSeries = newSeries.length > maxPoints
      ? newSeries.slice(-maxPoints)
      : newSeries;

    updateThrottled(trimmedSeries);
  }, [throttledState.value, maxPoints, updateThrottled]);

  const updateSeries = useCallback((newSeries: T[]) => {
    const trimmedSeries = newSeries.length > maxPoints
      ? newSeries.slice(-maxPoints)
      : newSeries;

    updateThrottled(trimmedSeries);
  }, [maxPoints, updateThrottled]);

  const stats = {
    pointCount: throttledState.value.length,
    updateRate: throttledState.averageInterval > 0 ? 1000 / throttledState.averageInterval : 0,
    memoryUsage: `${(JSON.stringify(throttledState.value).length / 1024).toFixed(1)}KB`,
  };

  return {
    series: throttledState.value,
    appendData,
    updateSeries,
    stats,
    flush,
  };
}

/**
 * Hook for batch updating multiple values with throttling.
 */
export function useBatchThrottling<T extends Record<string, any>>(
  initialValues: T,
  updateInterval: number = 200
): {
  values: T;
  updateValue: <K extends keyof T>(key: K, value: T[K]) => void;
  updateValues: (updates: Partial<T>) => void;
  batchStats: {
    batchSize: number;
    updateRate: number;
    efficiency: number;
  };
  flush: () => void;
} {
  const [throttledState, updateThrottled, flush] = useThrottledUpdate(initialValues, {
    delay: updateInterval,
    leading: false, // For batching, we want trailing behavior
    trailing: true,
  });

  const pendingUpdatesRef = useRef<Partial<T>>({});
  const batchSizeRef = useRef<number[]>([]);

  const updateValue = useCallback(<K extends keyof T>(key: K, value: T[K]) => {
    pendingUpdatesRef.current[key] = value;

    const newValues = { ...throttledState.value, ...pendingUpdatesRef.current };

    // Track batch size
    const batchSize = Object.keys(pendingUpdatesRef.current).length;
    batchSizeRef.current.push(batchSize);
    if (batchSizeRef.current.length > 20) {
      batchSizeRef.current.shift();
    }

    updateThrottled(newValues);
    pendingUpdatesRef.current = {};
  }, [throttledState.value, updateThrottled]);

  const updateValues = useCallback((updates: Partial<T>) => {
    Object.assign(pendingUpdatesRef.current, updates);

    const newValues = { ...throttledState.value, ...pendingUpdatesRef.current };

    // Track batch size
    const batchSize = Object.keys(pendingUpdatesRef.current).length;
    batchSizeRef.current.push(batchSize);
    if (batchSizeRef.current.length > 20) {
      batchSizeRef.current.shift();
    }

    updateThrottled(newValues);
    pendingUpdatesRef.current = {};
  }, [throttledState.value, updateThrottled]);

  const batchStats = {
    batchSize: batchSizeRef.current.length > 0
      ? batchSizeRef.current.reduce((sum, size) => sum + size, 0) / batchSizeRef.current.length
      : 1,
    updateRate: throttledState.averageInterval > 0 ? 1000 / throttledState.averageInterval : 0,
    efficiency: throttledState.updateCount > 0
      ? (throttledState.updateCount / (throttledState.updateCount + throttledState.droppedCount)) * 100
      : 100,
  };

  return {
    values: throttledState.value,
    updateValue,
    updateValues,
    batchStats,
    flush,
  };
}

/**
 * Performance monitoring hook for throttled updates.
 */
export function useThrottlePerformanceMonitor() {
  const [performanceData, setPerformanceData] = useState({
    frameRate: 60,
    memoryUsage: 0,
    updateLatency: 0,
    isOptimal: true,
  });

  const frameCountRef = useRef(0);
  const lastFrameTimeRef = useRef(performance.now());
  const latencyMeasurementsRef = useRef<number[]>([]);

  useEffect(() => {
    let animationId: number;

    const measureFrame = () => {
      const now = performance.now();
      const deltaTime = now - lastFrameTimeRef.current;

      frameCountRef.current++;

      // Calculate frame rate every second
      if (deltaTime >= 1000) {
        const fps = (frameCountRef.current * 1000) / deltaTime;

        setPerformanceData(prev => ({
          ...prev,
          frameRate: Math.round(fps),
          isOptimal: fps >= 55, // Consider 55+ FPS as optimal
        }));

        frameCountRef.current = 0;
        lastFrameTimeRef.current = now;
      }

      animationId = requestAnimationFrame(measureFrame);
    };

    measureFrame();

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, []);

  const recordUpdateLatency = useCallback((latency: number) => {
    latencyMeasurementsRef.current.push(latency);

    if (latencyMeasurementsRef.current.length > 50) {
      latencyMeasurementsRef.current.shift();
    }

    const averageLatency = latencyMeasurementsRef.current.reduce((sum, l) => sum + l, 0) /
                          latencyMeasurementsRef.current.length;

    setPerformanceData(prev => ({
      ...prev,
      updateLatency: Math.round(averageLatency),
    }));
  }, []);

  return {
    performanceData,
    recordUpdateLatency,
  };
}

/**
 * High-level hook that combines chart throttling with performance monitoring.
 */
export function useOptimizedChartUpdates<T>(
  initialData: T,
  targetFPS: number = 60
) {
  const updateInterval = Math.max(1000 / targetFPS, 16); // Minimum 16ms (60 FPS)

  const chartThrottling = useChartDataThrottling(initialData, updateInterval);
  const performanceMonitor = useThrottlePerformanceMonitor();

  const optimizedUpdate = useCallback((newData: T) => {
    const startTime = performance.now();

    chartThrottling.updateData(newData);

    const endTime = performance.now();
    performanceMonitor.recordUpdateLatency(endTime - startTime);
  }, [chartThrottling, performanceMonitor]);

  return {
    data: chartThrottling.data,
    updateData: optimizedUpdate,
    flush: chartThrottling.flush,
    stats: {
      ...chartThrottling.stats,
      ...performanceMonitor.performanceData,
      targetInterval: updateInterval,
      actualInterval: chartThrottling.stats.averageInterval,
      efficiency: chartThrottling.stats.averageInterval > 0
        ? (updateInterval / chartThrottling.stats.averageInterval) * 100
        : 100,
    },
  };
}