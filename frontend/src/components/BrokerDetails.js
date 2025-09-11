import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BrokerDetails = () => {
  const [brokerInfo, setBrokerInfo] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const fetchBrokerInfo = async () => {
      try {
        const response = await axios.get('/api/broker/details');
        setBrokerInfo(response.data);
      } catch (error) {
        setBrokerInfo({ error: error.message });
      }
    };

    fetchBrokerInfo();
    const interval = setInterval(fetchBrokerInfo, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'CONNECTED': return '#28a745';
      case 'DISCONNECTED': return '#dc3545';
      case 'CONNECTING': return '#ffc107';
      default: return '#6c757d';
    }
  };

  return (
    <div style={{ 
      border: '1px solid #ccc', 
      padding: '15px', 
      borderRadius: '8px', 
      backgroundColor: '#f8f9fa',
      marginBottom: '20px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
        <h3>Broker Connection Details</h3>
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ 
            padding: '5px 10px',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          {isExpanded ? 'Hide' : 'Show'} Details
        </button>
      </div>
      
      <div style={{ display: 'grid', gap: '8px', fontSize: '14px' }}>
        <div>
          <strong>Status:</strong> 
          <span style={{ 
            color: getStatusColor(brokerInfo?.status), 
            fontWeight: 'bold',
            marginLeft: '10px'
          }}>
            {brokerInfo?.status || 'CHECKING...'}
          </span>
        </div>
        
        {isExpanded && brokerInfo && (
          <>
            <div><strong>Broker:</strong> {brokerInfo.broker_name || 'Angel One'}</div>
            <div><strong>API Version:</strong> {brokerInfo.api_version || 'N/A'}</div>
            <div><strong>Session Token:</strong> {brokerInfo.session_token ? '✓ Active' : '✗ Missing'}</div>
            <div><strong>Feed Token:</strong> {brokerInfo.feed_token ? '✓ Active' : '✗ Missing'}</div>
            <div><strong>Client ID:</strong> {brokerInfo.client_id || 'N/A'}</div>
            <div><strong>Last Heartbeat:</strong> {brokerInfo.last_heartbeat || 'N/A'}</div>
            <div><strong>Connection Time:</strong> {brokerInfo.connection_time || 'N/A'}</div>
            <div><strong>Market Data Feed:</strong> 
              <span style={{ 
                color: brokerInfo.market_feed_active ? '#28a745' : '#dc3545',
                marginLeft: '10px'
              }}>
                {brokerInfo.market_feed_active ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </div>
            <div><strong>WebSocket Status:</strong> 
              <span style={{ 
                color: brokerInfo.websocket_connected ? '#28a745' : '#dc3545',
                marginLeft: '10px'
              }}>
                {brokerInfo.websocket_connected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
            {brokerInfo.error && (
              <div style={{ color: '#dc3545', marginTop: '10px' }}>
                <strong>Error:</strong> {brokerInfo.error}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default BrokerDetails;