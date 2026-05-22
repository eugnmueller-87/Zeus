import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8081/ws';

export default function useWebSocket() {
  const [events, setEvents]       = useState([]);
  const [status, setStatus]       = useState(null);
  const [agents, setAgents]       = useState([]);
  const [connected, setConnected] = useState(false);
  const ws = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      setConnected(true);
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    socket.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        if (event.type === 'status_update') {
          setStatus(event);
        } else if (event.type === 'agent_health') {
          setAgents(event.agents || []);
        } else {
          setEvents(prev => [event, ...prev].slice(0, 200));
        }
      } catch (_) {}
    };

    socket.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    socket.onerror = () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) ws.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  const send = useCallback((action) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ action }));
    }
  }, []);

  return { events, status, agents, connected, send };
}
