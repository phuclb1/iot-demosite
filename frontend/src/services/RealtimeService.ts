/**
 * Real-time data synchronization service.
 *
 * Coordinates real-time data updates between SSE connections and application state,
 * managing data flow, caching, and synchronization for optimal performance.
 */

import { useAtom } from 'jotai';
import { useCallback, useEffect, useRef } from 'react';

import { useSSEConnection, useTelemetrySSE, useDeviceStatusSSE } from '@/hooks/useSSEConnection';
import {
  addRealTimeDataAtom,
  isRealTimeEnabledAtom,
  selectedFieldsAtom,
  updateStreamingConnectionAtom,
  refreshTelemetryAtom,
  currentTelemetryAtom,
} from '@/state/telemetryAtoms';
import {
  selectedDeviceIdAtom,
  selectedOrganizationIdAtom,
  refreshDevicesAtom,
  deviceStatsAtom,
} from '@/state/hierarchyAtoms';

export interface TelemetryUpdate {
  device_id: string;
  timestamp: string;
  readings: Record<string, {
    value: number;
    unit: string;
    timestamp: string;
  }>;
}

export interface DeviceStatusUpdate {
  device_id: string;
  status: 'online' | 'offline' | 'maintenance' | 'error';
  timestamp: string;
  battery_level?: number;
  signal_strength?: number;
  last_seen?: string;
}

export interface AlertUpdate {
  device_id: string;
  alert_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  description: string;
  timestamp: string;
  acknowledgment_required?: boolean;
}

export interface RealtimeServiceState {
  isConnected: boolean;
  lastUpdateTime: Date | null;
  updateCount: number;
  errorCount: number;
  averageLatency: number;
  connectionQuality: 'excellent' | 'good' | 'poor' | 'disconnected';
}

interface DataBuffer<T> {
  data: T[];
  maxSize: number;
  lastFlush: Date;
}

interface LatencyMeasurement {
  timestamp: Date;
  latency: number;
}

class RealtimeDataService {
  private telemetryBuffer: DataBuffer<TelemetryUpdate>;
  private statusBuffer: DataBuffer<DeviceStatusUpdate>;
  private alertBuffer: DataBuffer<AlertUpdate>;
  private latencyMeasurements: LatencyMeasurement[];
  private state: RealtimeServiceState;
  private listeners: Set<(state: RealtimeServiceState) => void>;

  constructor() {
    this.telemetryBuffer = {
      data: [],
      maxSize: 1000,
      lastFlush: new Date(),
    };

    this.statusBuffer = {
      data: [],
      maxSize: 500,
      lastFlush: new Date(),
    };

    this.alertBuffer = {
      data: [],
      maxSize: 100,
      lastFlush: new Date(),
    };

    this.latencyMeasurements = [];
    this.state = {
      isConnected: false,
      lastUpdateTime: null,
      updateCount: 0,
      errorCount: 0,
      averageLatency: 0,
      connectionQuality: 'disconnected',
    };

    this.listeners = new Set();
  }

  // Buffer management
  addToBuffer<T>(buffer: DataBuffer<T>, item: T): void {
    buffer.data.push(item);
    if (buffer.data.length > buffer.maxSize) {
      buffer.data = buffer.data.slice(-buffer.maxSize);
    }
  }

  flushBuffer<T>(buffer: DataBuffer<T>): T[] {
    const data = buffer.data.slice();
    buffer.data = [];
    buffer.lastFlush = new Date();
    return data;
  }

  // Latency tracking
  recordLatency(serverTimestamp: string): void {
    const serverTime = new Date(serverTimestamp);
    const clientTime = new Date();
    const latency = clientTime.getTime() - serverTime.getTime();

    if (latency >= 0 && latency < 30000) { // Ignore negative or excessive latencies
      this.latencyMeasurements.push({
        timestamp: clientTime,
        latency,
      });

      // Keep only last 100 measurements
      if (this.latencyMeasurements.length > 100) {
        this.latencyMeasurements = this.latencyMeasurements.slice(-100);
      }

      // Update average latency
      const totalLatency = this.latencyMeasurements.reduce((sum, m) => sum + m.latency, 0);
      this.state.averageLatency = totalLatency / this.latencyMeasurements.length;

      // Update connection quality
      this.updateConnectionQuality();
    }
  }

  updateConnectionQuality(): void {
    const { averageLatency } = this.state;

    if (!this.state.isConnected) {
      this.state.connectionQuality = 'disconnected';
    } else if (averageLatency < 100) {
      this.state.connectionQuality = 'excellent';
    } else if (averageLatency < 500) {
      this.state.connectionQuality = 'good';
    } else {
      this.state.connectionQuality = 'poor';
    }
  }

  // State management
  updateState(updates: Partial<RealtimeServiceState>): void {
    this.state = { ...this.state, ...updates };
    this.notifyListeners();
  }

  setState(newState: RealtimeServiceState): void {
    this.state = newState;
    this.notifyListeners();
  }

  getState(): RealtimeServiceState {
    return { ...this.state };
  }

  subscribe(listener: (state: RealtimeServiceState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.state));
  }

  // Data processing
  processTelemetryUpdate(data: TelemetryUpdate): void {
    this.addToBuffer(this.telemetryBuffer, data);
    this.recordLatency(data.timestamp);
    this.updateState({
      lastUpdateTime: new Date(),
      updateCount: this.state.updateCount + 1,
    });
  }

  processStatusUpdate(data: DeviceStatusUpdate): void {
    this.addToBuffer(this.statusBuffer, data);
    this.recordLatency(data.timestamp);
    this.updateState({
      lastUpdateTime: new Date(),
      updateCount: this.state.updateCount + 1,
    });
  }

  processAlertUpdate(data: AlertUpdate): void {
    this.addToBuffer(this.alertBuffer, data);
    this.recordLatency(data.timestamp);
    this.updateState({
      lastUpdateTime: new Date(),
      updateCount: this.state.updateCount + 1,
    });
  }

  // Data retrieval
  getTelemetryUpdates(): TelemetryUpdate[] {
    return this.flushBuffer(this.telemetryBuffer);
  }

  getStatusUpdates(): DeviceStatusUpdate[] {
    return this.flushBuffer(this.statusBuffer);
  }

  getAlertUpdates(): AlertUpdate[] {
    return this.flushBuffer(this.alertBuffer);
  }

  // Connection management
  setConnected(connected: boolean): void {
    this.updateState({ isConnected: connected });
    if (!connected) {
      this.updateState({ connectionQuality: 'disconnected' });
    }
  }

  recordError(): void {
    this.updateState({ errorCount: this.state.errorCount + 1 });
  }

  // Statistics
  getStatistics() {
    return {
      ...this.state,
      bufferSizes: {
        telemetry: this.telemetryBuffer.data.length,
        status: this.statusBuffer.data.length,
        alerts: this.alertBuffer.data.length,
      },
      latencyStats: {
        measurements: this.latencyMeasurements.length,
        min: Math.min(...this.latencyMeasurements.map(m => m.latency)) || 0,
        max: Math.max(...this.latencyMeasurements.map(m => m.latency)) || 0,
        average: this.state.averageLatency,
      },
    };
  }
}

// Global service instance
const realtimeService = new RealtimeDataService();

// Hook for using the realtime service
export function useRealtimeService() {
  const [isRealTimeEnabled] = useAtom(isRealTimeEnabledAtom);
  const [selectedDeviceId] = useAtom(selectedDeviceIdAtom);
  const [selectedOrgId] = useAtom(selectedOrganizationIdAtom);
  const [selectedFields] = useAtom(selectedFieldsAtom);
  const [, addRealTimeData] = useAtom(addRealTimeDataAtom);
  const [, updateStreamingConnection] = useAtom(updateStreamingConnectionAtom);
  const [, refreshTelemetry] = useAtom(refreshTelemetryAtom);
  const [, refreshDevices] = useAtom(refreshDevicesAtom);
  const [currentTelemetry] = useAtom(currentTelemetryAtom);

  const processingQueueRef = useRef<NodeJS.Timeout | null>(null);

  // Telemetry message handler
  const handleTelemetryMessage = useCallback((data: TelemetryUpdate) => {
    if (!isRealTimeEnabled || !selectedDeviceId || data.device_id !== selectedDeviceId) {
      return;
    }

    realtimeService.processTelemetryUpdate(data);

    // Add data to chart atoms for each selected field
    Object.entries(data.readings).forEach(([fieldName, reading]) => {
      if (selectedFields.includes(fieldName)) {
        addRealTimeData({
          fieldName,
          timestamp: reading.timestamp,
          value: reading.value,
        });
      }
    });

    // Update connection status
    updateStreamingConnection({
      connected: true,
      lastMessage: new Date().toISOString(),
      error: undefined,
    });
  }, [isRealTimeEnabled, selectedDeviceId, selectedFields, addRealTimeData, updateStreamingConnection]);

  // Status update handler
  const handleStatusUpdate = useCallback((data: DeviceStatusUpdate) => {
    realtimeService.processStatusUpdate(data);

    // Refresh device list if status changed
    refreshDevices();

    // Update streaming connection state
    updateStreamingConnection({
      connected: true,
      lastMessage: new Date().toISOString(),
      error: undefined,
    });
  }, [refreshDevices, updateStreamingConnection]);

  // Alert handler
  const handleAlert = useCallback((data: AlertUpdate) => {
    realtimeService.processAlertUpdate(data);

    // Show notification or update alert state
    console.warn(`Alert for device ${data.device_id}:`, data);

    // Update connection status
    updateStreamingConnection({
      connected: true,
      lastMessage: new Date().toISOString(),
      error: undefined,
    });
  }, [updateStreamingConnection]);

  // Connection error handler
  const handleConnectionError = useCallback((error: any) => {
    realtimeService.recordError();
    realtimeService.setConnected(false);

    updateStreamingConnection({
      connected: false,
      error: error instanceof Error ? error.message : String(error),
    });

    console.error('Realtime connection error:', error);
  }, [updateStreamingConnection]);

  // Connection open handler
  const handleConnectionOpen = useCallback(() => {
    realtimeService.setConnected(true);

    updateStreamingConnection({
      connected: true,
      error: undefined,
    });

    console.log('Realtime connection established');
  }, [updateStreamingConnection]);

  // Connection close handler
  const handleConnectionClose = useCallback(() => {
    realtimeService.setConnected(false);

    updateStreamingConnection({
      connected: false,
    });

    console.log('Realtime connection closed');
  }, [updateStreamingConnection]);

  // Setup SSE connections
  const telemetrySSE = useTelemetrySSE(
    selectedDeviceId || undefined,
    handleTelemetryMessage
  );

  const statusSSE = useDeviceStatusSSE(
    selectedOrgId || undefined,
    handleStatusUpdate
  );

  // Update connection state based on SSE status
  useEffect(() => {
    const isConnected = telemetrySSE.connectionState.connected && statusSSE.connectionState.connected;
    const hasError = telemetrySSE.connectionState.error || statusSSE.connectionState.error;

    realtimeService.setConnected(isConnected);

    updateStreamingConnection({
      connected: isConnected,
      error: hasError || undefined,
      retryCount: Math.max(
        telemetrySSE.connectionState.connectionAttempts,
        statusSSE.connectionState.connectionAttempts
      ),
    });
  }, [
    telemetrySSE.connectionState,
    statusSSE.connectionState,
    updateStreamingConnection,
  ]);

  // Process queued updates periodically
  useEffect(() => {
    if (!isRealTimeEnabled) {
      return;
    }

    processingQueueRef.current = setInterval(() => {
      // Process any buffered updates
      const telemetryUpdates = realtimeService.getTelemetryUpdates();
      const statusUpdates = realtimeService.getStatusUpdates();
      const alertUpdates = realtimeService.getAlertUpdates();

      // Additional processing could be done here
      // For example, batch operations or data aggregation
    }, 1000); // Process every second

    return () => {
      if (processingQueueRef.current) {
        clearInterval(processingQueueRef.current);
      }
    };
  }, [isRealTimeEnabled]);

  return {
    service: realtimeService,
    connectionState: {
      telemetry: telemetrySSE.connectionState,
      status: statusSSE.connectionState,
    },
    statistics: realtimeService.getStatistics(),
    connect: () => {
      telemetrySSE.connect();
      statusSSE.connect();
    },
    disconnect: () => {
      telemetrySSE.disconnect();
      statusSSE.disconnect();
    },
  };
}

// Hook for monitoring realtime service state
export function useRealtimeServiceState() {
  const [state, setState] = React.useState(realtimeService.getState());

  useEffect(() => {
    const unsubscribe = realtimeService.subscribe(setState);
    return unsubscribe;
  }, []);

  return state;
}

// Hook for realtime statistics
export function useRealtimeStatistics() {
  const [stats, setStats] = React.useState(realtimeService.getStatistics());

  useEffect(() => {
    const updateStats = () => setStats(realtimeService.getStatistics());
    const interval = setInterval(updateStats, 1000);

    return () => clearInterval(interval);
  }, []);

  return stats;
}

// Utility function to format connection quality
export function getConnectionQualityColor(quality: RealtimeServiceState['connectionQuality']): string {
  switch (quality) {
    case 'excellent':
      return 'text-green-600';
    case 'good':
      return 'text-blue-600';
    case 'poor':
      return 'text-yellow-600';
    case 'disconnected':
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
}

// Utility function to get connection quality icon
export function getConnectionQualityIcon(quality: RealtimeServiceState['connectionQuality']): string {
  switch (quality) {
    case 'excellent':
      return '🟢';
    case 'good':
      return '🔵';
    case 'poor':
      return '🟡';
    case 'disconnected':
      return '🔴';
    default:
      return '⚪';
  }
}

// Export the service instance for direct access
export { realtimeService };