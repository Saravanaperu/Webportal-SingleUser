import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BrokerStatus = () => {
  const [brokerStatus, setBrokerStatus] = useState(null);

  useEffect(() => {
    const fetchBrokerStatus = async () => {
      try {
        const response = await axios.get('/api/broker/status');
        setBrokerStatus(response.data);
      } catch (error) {
        setBrokerStatus({ connected: false, error: error.message });
      }
    };

    fetchBrokerStatus();
    const interval = setInterval(fetchBrokerStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (connected) => connected ? '#28a745' : '#dc3545';
  const getStatusText = (connected) => connected ? 'CONNECTED' : 'DISCONNECTED';

  return (
    <div style={{ 
      border: '1px solid #ccc', 
      padding: '15px', 
      borderRadius: '8px', 
      backgroundColor: '#f8f9fa',
      marginBottom: '20px'
    }}>
      <h3>Broker Connection Status</h3>
      <div style={{ display: 'grid', gap: '10px', fontSize: '14px' }}>
        <div>
          <strong>API Connection:</strong> 
          <span style={{ 
            color: getStatusColor(brokerStatus?.connected), 
            fontWeight: 'bold',
            marginLeft: '10px'
          }}>
            {brokerStatus ? getStatusText(brokerStatus.connected) : 'CHECKING...'}
          </span>
        </div>
        
        {brokerStatus?.connected && (
          <>
            <div><strong>Session ID:</strong> {brokerStatus.session_id || 'N/A'}</div>
            <div><strong>User ID:</strong> {brokerStatus.user_id || 'N/A'}</div>
            <div><strong>Last Update:</strong> {brokerStatus.last_update || 'N/A'}</div>
            <div><strong>Market Data:</strong> 
              <span style={{ 
                color: getStatusColor(brokerStatus.market_data_active),
                marginLeft: '10px'
              }}>
                {getStatusText(brokerStatus.market_data_active)}
              </span>
            </div>
          </>
        )}
        
        {brokerStatus?.error && (
          <div style={{ color: '#dc3545' }}>
            <strong>Error:</strong> {brokerStatus.error}
          </div>
        )}
      </div>
    </div>
  );
};

export default BrokerStatus;