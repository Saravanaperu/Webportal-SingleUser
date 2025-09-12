import React, { createContext, useContext, useEffect, useState } from 'react';
import useWebSocket from '../hooks/useWebSocket';
import useDashboardData from '../hooks/useDashboardData';

const TradingContext = createContext();

export const useTradingContext = () => {
  const context = useContext(TradingContext);
  if (!context) {
    throw new Error('useTradingContext must be used within TradingProvider');
  }
  return context;
};

export const TradingProvider = ({ children }) => {
  const wsUrl = `ws://${window.location.host}/api/ws/realtime`;
  const { data: wsData, isConnected } = useWebSocket(wsUrl);
  const { data: fallbackData, loading, error } = useDashboardData();
  
  // Use WebSocket data when available, fallback to polling data
  const [currentData, setCurrentData] = useState({
    account: null,
    positions: [],
    indices: {},
    stats: null
  });

  useEffect(() => {
    if (isConnected && wsData && Object.keys(wsData).length > 0) {
      setCurrentData(prevData => ({
        ...prevData,
        ...wsData
      }));
    } else if (!loading && fallbackData) {
      setCurrentData(prevData => ({
        ...prevData,
        ...fallbackData
      }));
    }
  }, [wsData, fallbackData, isConnected, loading]);

  const value = {
    ...currentData,
    isConnected,
    loading,
    error
  };

  return (
    <TradingContext.Provider value={value}>
      {children}
    </TradingContext.Provider>
  );
};

export default TradingContext;