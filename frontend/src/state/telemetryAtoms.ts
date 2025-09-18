/**
 * Telemetry data state management using Jotai atoms.
 *
 * Manages real-time and historical telemetry data, streaming connections,
 * and chart data for the IoT dashboard visualization.
 */

import { atom } from 'jotai';
import { atomWithQuery } from 'jotai-tanstack-query';
import { selectedDeviceIdAtom } from './hierarchyAtoms';

// Types
export interface TelemetryReading {
  timestamp: string;
  readings: {
    [fieldName: string]: {
      value: number;
      unit: string;
      timestamp: string;
    };
  };
}

export interface TelemetryField {
  name: string;
  unit: string;
  label: string;
  color: string;
}

export interface HistoricalTelemetryData {
  device_id: string;
  start_time: string;
  end_time: string;
  interval?: string;
  data_points: number;
  time_series: Array<{
    timestamp: string;
    readings: {
      [fieldName: string]: {
        value: number;
        unit: string;
      };
    };
  }>;
}

export interface TelemetrySummary {
  device_id: string;
  summary_period_hours: number;
  start_time: string;
  end_time: string;
  field_summaries: {
    [fieldName: string]: {
      unit: string;
      min?: number;
      max?: number;
      mean?: number;
      count?: number;
    };
  };
}

export interface StreamingConnection {
  connected: boolean;
  lastMessage?: string;
  error?: string;
  retryCount: number;
}

// Telemetry field definitions
export const TELEMETRY_FIELDS: Record<string, TelemetryField> = {
  temperature: {
    name: 'temperature',
    unit: '°C',
    label: 'Temperature',
    color: '#ef4444', // red
  },
  vibration: {
    name: 'vibration',
    unit: 'mm/s',
    label: 'Vibration',
    color: '#3b82f6', // blue
  },
  power: {
    name: 'power',
    unit: 'W',
    label: 'Power',
    color: '#10b981', // green
  },
  electricity: {
    name: 'electricity',
    unit: 'kWh',
    label: 'Electricity',
    color: '#f59e0b', // amber
  },
};

// Time range options
export const TIME_RANGES = {
  '1h': { label: '1 Hour', hours: 1, interval: '1m' },
  '6h': { label: '6 Hours', hours: 6, interval: '5m' },
  '24h': { label: '24 Hours', hours: 24, interval: '15m' },
  '7d': { label: '7 Days', hours: 168, interval: '1h' },
  '30d': { label: '30 Days', hours: 720, interval: '4h' },
} as const;

export type TimeRangeKey = keyof typeof TIME_RANGES;

// Base atoms
export const selectedTimeRangeAtom = atom<TimeRangeKey>('24h');
export const selectedFieldsAtom = atom<string[]>(Object.keys(TELEMETRY_FIELDS));
export const isRealTimeEnabledAtom = atom<boolean>(true);
export const telemetryErrorAtom = atom<string | null>(null);

// Streaming connection state
export const streamingConnectionAtom = atom<StreamingConnection>({
  connected: false,
  retryCount: 0,
});

// Current telemetry query atom
export const currentTelemetryQueryAtom = atomWithQuery((get) => {
  const deviceId = get(selectedDeviceIdAtom);
  const selectedFields = get(selectedFieldsAtom);

  return {
    queryKey: ['current-telemetry', deviceId, selectedFields],
    queryFn: async (): Promise<TelemetryReading | null> => {
      if (!deviceId) return null;

      const params = new URLSearchParams();
      selectedFields.forEach(field => params.append('fields', field));

      const response = await fetch(
        `/api/v1/telemetry/current/${deviceId}?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch current telemetry: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!deviceId,
    refetchInterval: 5000, // Refetch every 5 seconds
    staleTime: 1000, // Consider stale after 1 second
    gcTime: 30000, // Keep in cache for 30 seconds
  };
});

// Historical telemetry query atom
export const historicalTelemetryQueryAtom = atomWithQuery((get) => {
  const deviceId = get(selectedDeviceIdAtom);
  const timeRange = get(selectedTimeRangeAtom);
  const selectedFields = get(selectedFieldsAtom);

  return {
    queryKey: ['historical-telemetry', deviceId, timeRange, selectedFields],
    queryFn: async (): Promise<HistoricalTelemetryData | null> => {
      if (!deviceId) return null;

      const range = TIME_RANGES[timeRange];
      const endTime = new Date();
      const startTime = new Date(endTime.getTime() - range.hours * 60 * 60 * 1000);

      const params = new URLSearchParams({
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        interval: range.interval,
      });

      selectedFields.forEach(field => params.append('fields', field));

      const response = await fetch(
        `/api/v1/telemetry/historical/${deviceId}?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch historical telemetry: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!deviceId,
    staleTime: 30000, // Historical data is less volatile
    gcTime: 5 * 60 * 1000, // Keep for 5 minutes
  };
});

// Telemetry summary query atom
export const telemetrySummaryQueryAtom = atomWithQuery((get) => {
  const deviceId = get(selectedDeviceIdAtom);
  const timeRange = get(selectedTimeRangeAtom);

  return {
    queryKey: ['telemetry-summary', deviceId, timeRange],
    queryFn: async (): Promise<TelemetrySummary | null> => {
      if (!deviceId) return null;

      const range = TIME_RANGES[timeRange];
      const params = new URLSearchParams({
        hours: range.hours.toString(),
      });

      const response = await fetch(
        `/api/v1/telemetry/summary/${deviceId}?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch telemetry summary: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!deviceId,
    staleTime: 60000, // Summary is less volatile
    gcTime: 5 * 60 * 1000,
  };
});

// Computed atoms
export const currentTelemetryAtom = atom((get) => {
  const query = get(currentTelemetryQueryAtom);
  return query.data || null;
});

export const historicalTelemetryAtom = atom((get) => {
  const query = get(historicalTelemetryQueryAtom);
  return query.data || null;
});

export const telemetrySummaryAtom = atom((get) => {
  const query = get(telemetrySummaryQueryAtom);
  return query.data || null;
});

// Loading states
export const telemetryIsLoadingAtom = atom((get) => {
  const currentQuery = get(currentTelemetryQueryAtom);
  const historicalQuery = get(historicalTelemetryQueryAtom);
  const summaryQuery = get(telemetrySummaryQueryAtom);

  return currentQuery.isLoading || historicalQuery.isLoading || summaryQuery.isLoading;
});

export const telemetryHasErrorAtom = atom((get) => {
  const currentQuery = get(currentTelemetryQueryAtom);
  const historicalQuery = get(historicalTelemetryQueryAtom);
  const summaryQuery = get(telemetrySummaryQueryAtom);

  return !!(currentQuery.error || historicalQuery.error || summaryQuery.error);
});

// Chart data atoms
export const chartDataAtom = atom((get) => {
  const historical = get(historicalTelemetryAtom);
  const selectedFields = get(selectedFieldsAtom);

  if (!historical || !historical.time_series) return {};

  // Transform data for chart libraries
  const chartData: Record<string, Array<{ timestamp: string; value: number }>> = {};

  selectedFields.forEach(fieldName => {
    chartData[fieldName] = [];
  });

  historical.time_series.forEach(dataPoint => {
    selectedFields.forEach(fieldName => {
      if (dataPoint.readings[fieldName]) {
        chartData[fieldName].push({
          timestamp: dataPoint.timestamp,
          value: dataPoint.readings[fieldName].value,
        });
      }
    });
  });

  return chartData;
});

// Real-time data buffer atom (for streaming updates)
export const realTimeBufferAtom = atom<Record<string, Array<{ timestamp: string; value: number }>>>({});

// Combined chart data atom (historical + real-time)
export const combinedChartDataAtom = atom((get) => {
  const chartData = get(chartDataAtom);
  const realtimeBuffer = get(realTimeBufferAtom);
  const isRealTimeEnabled = get(isRealTimeEnabledAtom);

  if (!isRealTimeEnabled) return chartData;

  // Merge historical and real-time data
  const combined: Record<string, Array<{ timestamp: string; value: number }>> = {};

  Object.keys(chartData).forEach(fieldName => {
    combined[fieldName] = [...(chartData[fieldName] || [])];

    // Add real-time data if available
    if (realtimeBuffer[fieldName]) {
      combined[fieldName] = [...combined[fieldName], ...realtimeBuffer[fieldName]];
    }

    // Sort by timestamp and limit to reasonable size
    combined[fieldName] = combined[fieldName]
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .slice(-1000); // Keep last 1000 points
  });

  return combined;
});

// Field-specific chart data atoms
export const temperatureChartDataAtom = atom((get) => {
  const chartData = get(combinedChartDataAtom);
  return chartData.temperature || [];
});

export const vibrationChartDataAtom = atom((get) => {
  const chartData = get(combinedChartDataAtom);
  return chartData.vibration || [];
});

export const powerChartDataAtom = atom((get) => {
  const chartData = get(combinedChartDataAtom);
  return chartData.power || [];
});

export const electricityChartDataAtom = atom((get) => {
  const chartData = get(combinedChartDataAtom);
  return chartData.electricity || [];
});

// Action atoms
export const setTimeRangeAtom = atom(
  null,
  (get, set, timeRange: TimeRangeKey) => {
    set(selectedTimeRangeAtom, timeRange);
  }
);

export const toggleFieldAtom = atom(
  null,
  (get, set, fieldName: string) => {
    const currentFields = get(selectedFieldsAtom);
    const newFields = currentFields.includes(fieldName)
      ? currentFields.filter(f => f !== fieldName)
      : [...currentFields, fieldName];
    set(selectedFieldsAtom, newFields);
  }
);

export const setSelectedFieldsAtom = atom(
  null,
  (get, set, fields: string[]) => {
    set(selectedFieldsAtom, fields);
  }
);

export const toggleRealTimeAtom = atom(
  null,
  (get, set) => {
    const current = get(isRealTimeEnabledAtom);
    set(isRealTimeEnabledAtom, !current);
  }
);

// Real-time update atom
export const addRealTimeDataAtom = atom(
  null,
  (get, set, data: { fieldName: string; timestamp: string; value: number }) => {
    const currentBuffer = get(realTimeBufferAtom);
    const newBuffer = { ...currentBuffer };

    if (!newBuffer[data.fieldName]) {
      newBuffer[data.fieldName] = [];
    }

    newBuffer[data.fieldName].push({
      timestamp: data.timestamp,
      value: data.value,
    });

    // Keep only last 100 real-time points per field
    newBuffer[data.fieldName] = newBuffer[data.fieldName].slice(-100);

    set(realTimeBufferAtom, newBuffer);
  }
);

// Clear real-time buffer
export const clearRealTimeBufferAtom = atom(
  null,
  (get, set) => {
    set(realTimeBufferAtom, {});
  }
);

// Refresh telemetry data
export const refreshTelemetryAtom = atom(
  null,
  (get, set) => {
    const currentQuery = get(currentTelemetryQueryAtom);
    const historicalQuery = get(historicalTelemetryQueryAtom);
    const summaryQuery = get(telemetrySummaryQueryAtom);

    currentQuery.refetch?.();
    historicalQuery.refetch?.();
    summaryQuery.refetch?.();
  }
);

// Streaming connection management
export const updateStreamingConnectionAtom = atom(
  null,
  (get, set, update: Partial<StreamingConnection>) => {
    const current = get(streamingConnectionAtom);
    set(streamingConnectionAtom, { ...current, ...update });
  }
);

// Export telemetry data atom
export const exportTelemetryDataAtom = atom(
  null,
  async (get, set, format: 'csv' | 'json' = 'csv') => {
    const historical = get(historicalTelemetryAtom);

    if (!historical) {
      throw new Error('No telemetry data available for export');
    }

    if (format === 'csv') {
      // Convert to CSV format
      const headers = ['timestamp', ...Object.keys(TELEMETRY_FIELDS).map(f => `${f}_value`), ...Object.keys(TELEMETRY_FIELDS).map(f => `${f}_unit`)];
      const csvRows = [headers.join(',')];

      historical.time_series.forEach(dataPoint => {
        const row = [dataPoint.timestamp];

        // Add values
        Object.keys(TELEMETRY_FIELDS).forEach(fieldName => {
          const reading = dataPoint.readings[fieldName];
          row.push(reading ? reading.value.toString() : '');
        });

        // Add units
        Object.keys(TELEMETRY_FIELDS).forEach(fieldName => {
          const reading = dataPoint.readings[fieldName];
          row.push(reading ? reading.unit : '');
        });

        csvRows.push(row.join(','));
      });

      return csvRows.join('\n');
    } else {
      // Return JSON format
      return JSON.stringify(historical, null, 2);
    }
  }
);