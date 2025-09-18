/**
 * Server-Sent Events (SSE) client hook for real-time data streaming.
 *
 * Provides robust SSE connection management with automatic reconnection,
 * error handling, and connection state tracking for real-time telemetry updates.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useAtom } from 'jotai';

import { accessTokenAtom } from '@/state/authAtoms';

export interface SSEMessage {
  id?: string;
  event?: string;
  data: any;
  timestamp: Date;
}

export interface SSEConnectionState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  lastMessageTime: Date | null;
  connectionAttempts: number;
  totalMessages: number;
}

export interface SSEOptions {
  url: string;
  withCredentials?: boolean;
  headers?: Record<string, string>;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  timeout?: number;
  eventTypes?: string[];
}

export interface SSEHookReturn {
  connectionState: SSEConnectionState;
  lastMessage: SSEMessage | null;
  connect: () => void;
  disconnect: () => void;
  send: (data: any) => void; // For future WebSocket upgrade
}

const DEFAULT_OPTIONS: Required<Omit<SSEOptions, 'url'>> = {
  withCredentials: true,
  headers: {},
  autoReconnect: true,
  maxReconnectAttempts: 10,
  reconnectDelay: 1000,
  heartbeatInterval: 30000,
  timeout: 30000,
  eventTypes: ['message', 'telemetry', 'status', 'alert', 'heartbeat'],
};

export function useSSEConnection(
  options: SSEOptions,
  onMessage?: (message: SSEMessage) => void,
  onError?: (error: Event | string) => void,
  onOpen?: () => void,
  onClose?: () => void
): SSEHookReturn {
  // Auth token for authenticated connections
  const [accessToken] = useAtom(accessTokenAtom);

  // Connection state
  const [connectionState, setConnectionState] = useState<SSEConnectionState>({
    connected: false,
    connecting: false,
    error: null,
    lastMessageTime: null,
    connectionAttempts: 0,
    totalMessages: 0,
  });

  const [lastMessage, setLastMessage] = useState<SSEMessage | null>(null);

  // Refs for managing connection lifecycle
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const optionsRef = useRef<Required<SSEOptions>>();

  // Merge options with defaults
  useEffect(() => {
    optionsRef.current = {
      ...DEFAULT_OPTIONS,
      ...options,
      headers: {
        ...DEFAULT_OPTIONS.headers,
        ...options.headers,
      },
    };
  }, [options]);

  // Clear timeouts on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
      }
    };
  }, []);

  const updateConnectionState = useCallback((updates: Partial<SSEConnectionState>) => {
    setConnectionState(prev => ({ ...prev, ...updates }));
  }, []);

  const setupHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }

    const interval = optionsRef.current?.heartbeatInterval ?? DEFAULT_OPTIONS.heartbeatInterval;

    heartbeatTimeoutRef.current = setTimeout(() => {
      const now = new Date();
      const lastMessage = connectionState.lastMessageTime;

      if (lastMessage && (now.getTime() - lastMessage.getTime()) > interval * 2) {
        console.warn('SSE heartbeat timeout, attempting reconnection');
        disconnect();
        if (optionsRef.current?.autoReconnect) {
          scheduleReconnect();
        }
      } else {
        setupHeartbeat(); // Schedule next heartbeat check
      }
    }, interval);
  }, [connectionState.lastMessageTime]);

  const scheduleReconnect = useCallback(() => {
    const maxAttempts = optionsRef.current?.maxReconnectAttempts ?? DEFAULT_OPTIONS.maxReconnectAttempts;

    if (connectionState.connectionAttempts >= maxAttempts) {
      updateConnectionState({
        connecting: false,
        error: `Max reconnection attempts (${maxAttempts}) exceeded`,
      });
      return;
    }

    const delay = Math.min(
      (optionsRef.current?.reconnectDelay ?? DEFAULT_OPTIONS.reconnectDelay) *
      Math.pow(2, connectionState.connectionAttempts), // Exponential backoff
      30000 // Max 30 seconds
    );

    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);

    updateConnectionState({
      connectionAttempts: connectionState.connectionAttempts + 1,
    });
  }, [connectionState.connectionAttempts]);

  const parseSSEMessage = useCallback((event: MessageEvent): SSEMessage => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      data = event.data;
    }

    return {
      id: event.lastEventId || undefined,
      event: event.type,
      data,
      timestamp: new Date(),
    };
  }, []);

  const connect = useCallback(() => {
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      console.warn('SSE connection already open');
      return;
    }

    if (!optionsRef.current) {
      console.error('SSE options not initialized');
      return;
    }

    updateConnectionState({
      connecting: true,
      error: null,
    });

    try {
      // Prepare URL with auth token if available
      const url = new URL(optionsRef.current.url);
      if (accessToken) {
        url.searchParams.set('token', accessToken);
      }

      // Create EventSource
      eventSourceRef.current = new EventSource(url.toString(), {
        withCredentials: optionsRef.current.withCredentials,
      });

      // Setup event listeners
      eventSourceRef.current.onopen = () => {
        console.log('SSE connection opened');
        updateConnectionState({
          connected: true,
          connecting: false,
          error: null,
          connectionAttempts: 0,
        });

        setupHeartbeat();
        onOpen?.();
      };

      eventSourceRef.current.onerror = (error) => {
        console.error('SSE connection error:', error);

        updateConnectionState({
          connected: false,
          connecting: false,
          error: 'Connection error occurred',
        });

        onError?.(error);

        // Auto-reconnect if enabled
        if (optionsRef.current?.autoReconnect &&
            connectionState.connectionAttempts < (optionsRef.current?.maxReconnectAttempts ?? DEFAULT_OPTIONS.maxReconnectAttempts)) {
          scheduleReconnect();
        }
      };

      eventSourceRef.current.onmessage = (event) => {
        const message = parseSSEMessage(event);

        updateConnectionState({
          lastMessageTime: message.timestamp,
          totalMessages: connectionState.totalMessages + 1,
        });

        setLastMessage(message);
        onMessage?.(message);
      };

      // Setup listeners for specific event types
      optionsRef.current.eventTypes.forEach(eventType => {
        if (eventSourceRef.current && eventType !== 'message') {
          eventSourceRef.current.addEventListener(eventType, (event) => {
            const message = parseSSEMessage(event as MessageEvent);

            updateConnectionState({
              lastMessageTime: message.timestamp,
              totalMessages: connectionState.totalMessages + 1,
            });

            setLastMessage(message);
            onMessage?.(message);
          });
        }
      });

    } catch (error) {
      console.error('Failed to create SSE connection:', error);
      updateConnectionState({
        connecting: false,
        error: error instanceof Error ? error.message : 'Unknown connection error',
      });
      onError?.(error instanceof Error ? error.message : 'Unknown connection error');
    }
  }, [
    accessToken,
    connectionState.connectionAttempts,
    connectionState.totalMessages,
    onMessage,
    onError,
    onOpen,
    parseSSEMessage,
    scheduleReconnect,
    setupHeartbeat,
    updateConnectionState,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    updateConnectionState({
      connected: false,
      connecting: false,
      connectionAttempts: 0,
    });

    onClose?.();
  }, [onClose, updateConnectionState]);

  // Placeholder for future WebSocket upgrade
  const send = useCallback((data: any) => {
    console.warn('Send not implemented for SSE connections. Use WebSocket for bidirectional communication.');
    // This would be implemented when upgrading to WebSocket
  }, []);

  // Auto-connect on mount if URL is provided
  useEffect(() => {
    if (options.url && optionsRef.current?.autoReconnect !== false) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [options.url]); // Only reconnect when URL changes

  // Reconnect when auth token changes
  useEffect(() => {
    if (connectionState.connected && accessToken) {
      // Reconnect with new token
      disconnect();
      setTimeout(connect, 100);
    }
  }, [accessToken]);

  return {
    connectionState,
    lastMessage,
    connect,
    disconnect,
    send,
  };
}

// Specialized hook for telemetry data streaming
export function useTelemetrySSE(
  deviceId?: string,
  onTelemetryMessage?: (data: any) => void
) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
  const url = deviceId
    ? `${baseUrl}/api/v1/sse/telemetry/${deviceId}`
    : `${baseUrl}/api/v1/sse/telemetry`;

  return useSSEConnection(
    {
      url,
      eventTypes: ['telemetry', 'status', 'alert'],
      autoReconnect: true,
      maxReconnectAttempts: 10,
      reconnectDelay: 2000,
    },
    (message) => {
      if (message.event === 'telemetry' && onTelemetryMessage) {
        onTelemetryMessage(message.data);
      }
    }
  );
}

// Specialized hook for device status updates
export function useDeviceStatusSSE(
  organizationId?: string,
  onStatusUpdate?: (data: any) => void
) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
  const url = organizationId
    ? `${baseUrl}/api/v1/sse/status/${organizationId}`
    : `${baseUrl}/api/v1/sse/status`;

  return useSSEConnection(
    {
      url,
      eventTypes: ['status', 'alert', 'heartbeat'],
      autoReconnect: true,
      maxReconnectAttempts: 5,
      reconnectDelay: 3000,
    },
    (message) => {
      if (['status', 'alert'].includes(message.event || '') && onStatusUpdate) {
        onStatusUpdate(message.data);
      }
    }
  );
}

// Hook for general real-time notifications
export function useNotificationSSE(
  onNotification?: (data: any) => void
) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
  const url = `${baseUrl}/api/v1/sse/notifications`;

  return useSSEConnection(
    {
      url,
      eventTypes: ['notification', 'alert', 'system'],
      autoReconnect: true,
      maxReconnectAttempts: 3,
      reconnectDelay: 5000,
    },
    (message) => {
      if (onNotification) {
        onNotification(message.data);
      }
    }
  );
}