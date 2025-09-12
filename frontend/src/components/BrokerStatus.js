import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BrokerStatus = React.memo(() => {
  const [brokerInfo, setBrokerInfo] = useState(null);

  useEffect(() => {
    const fetchBrokerInfo = async () => {
      try {
        const response = await axios.get('/api/broker/details');
        setBrokerInfo(prevInfo => ({ ...prevInfo, ...response.data }));
      } catch (error) {
        setBrokerInfo(prevInfo => ({ ...prevInfo, error: error.message }));
      }
    };

    fetchBrokerInfo();
    const interval = setInterval(fetchBrokerInfo, 15000);
    return () => clearInterval(interval);
  }, []);

  const isConnected = brokerInfo?.status === 'CONNECTED';
  const isMarketFeedActive = brokerInfo?.market_feed_active || false;
  const isWebSocketConnected = brokerInfo?.websocket_connected || false;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.5rem 1rem',
      background: 'rgba(255, 255, 255, 0.15)',
      borderRadius: '8px',
      fontSize: '0.8rem',
      border: '1px solid rgba(255, 255, 255, 0.2)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
        <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
        <span style={{ fontWeight: '600', fontSize: '0.75rem' }}>
          Broker
        </span>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
        <span className={`status-indicator ${isMarketFeedActive ? 'connected' : 'disconnected'}`}></span>
        <span style={{ fontWeight: '600', fontSize: '0.75rem' }}>
          Market
        </span>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
        <span className={`status-indicator ${isWebSocketConnected ? 'connected' : 'disconnected'}`}></span>
        <span style={{ fontWeight: '600', fontSize: '0.75rem' }}>
          Data
        </span>
      </div>
    </div>
  );
});

export default BrokerStatus;