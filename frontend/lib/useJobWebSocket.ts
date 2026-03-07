import { useState, useEffect, useRef, useCallback } from 'react';
import { API_URL } from './config';

export interface JobStatusUpdate {
  type: 'status_update' | 'error' | 'pong';
  job_id?: string;
  status?: string;
  report_payload?: unknown;
  charts_payload?: unknown;
  retirement_payload?: unknown;
  error_message?: string;
  message?: string;
}

interface UseJobWebSocketOptions {
  onStatusChange?: (update: JobStatusUpdate) => void;
  onCompleted?: (update: JobStatusUpdate) => void;
  onFailed?: (update: JobStatusUpdate) => void;
  onError?: (error: Event) => void;
}

/**
 * Hook for real-time job status updates via WebSocket.
 * Replaces the polling approach with a persistent WebSocket connection.
 */
export function useJobWebSocket(
  jobId: string | null,
  options: UseJobWebSocketOptions = {}
) {
  const [status, setStatus] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const cleanup = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (!jobId) {
      cleanup();
      return;
    }

    // Build WebSocket URL from API_URL
    let wsUrl: string;
    if (API_URL === '' || API_URL === undefined) {
      // Production: derive from current page location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/ws/jobs/${jobId}`;
    } else {
      // Local development: replace http with ws
      const base = API_URL.replace(/^http/, 'ws');
      wsUrl = `${base}/ws/jobs/${jobId}`;
    }

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        // Send periodic pings to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const update: JobStatusUpdate = JSON.parse(event.data);

          if (update.type === 'pong') return;

          if (update.type === 'status_update' && update.status) {
            setStatus(update.status);
            optionsRef.current.onStatusChange?.(update);

            if (update.status === 'completed') {
              optionsRef.current.onCompleted?.(update);
              // Server closes after sending completed, cleanup our side
              cleanup();
            } else if (update.status === 'failed') {
              optionsRef.current.onFailed?.(update);
              cleanup();
            }
          }

          if (update.type === 'error') {
            console.error('WebSocket job error:', update.message);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        optionsRef.current.onError?.(error);
      };

      ws.onclose = () => {
        setConnected(false);
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        // Reconnect if the job hasn't completed/failed and we still want to watch
        if (wsRef.current === ws && status !== 'completed' && status !== 'failed') {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    };

    connect();

    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return { status, connected, cleanup };
}
