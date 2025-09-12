import { useState, useEffect, useRef } from 'react';

const useWebSocket = (url) => {
  const [data, setData] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = () => {
    try {
      wsRef.current = new WebSocket(url);
      
      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'realtime_update') {
            setData(message.data);
          }
        } catch (error) {
          console.error('WebSocket message parse error:', error);
        }
      };
      
      wsRef.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected, attempting reconnect...');
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  };

  useEffect(() => {
    connect();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  return { data, isConnected };
};

export default useWebSocket;