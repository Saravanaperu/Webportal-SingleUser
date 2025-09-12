import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BrokerDetails = React.memo(() => {
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
    const interval = setInterval(fetchBrokerInfo, 15000); // Reduced frequency
    return () => clearInterval(interval);
  }, []);

  const isConnected = brokerInfo?.status === 'CONNECTED';

  return (
    <div className="card">
      <h3>
        <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
        🔗 Broker Connection
      </h3>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Status:</span>
          <span className={isConnected ? 'status-positive' : 'status-negative'} style={{ fontWeight: '600' }}>
            {brokerInfo?.status || 'CHECKING...'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Broker:</span>
          <span style={{ fontWeight: '600' }}>{brokerInfo?.broker_name || 'Angel One'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>API Version:</span>
          <span style={{ fontWeight: '600' }}>{brokerInfo?.api_version || 'N/A'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Market Feed:</span>
          <span className={brokerInfo?.market_feed_active ? 'status-positive' : 'status-negative'} style={{ fontWeight: '600' }}>
            {brokerInfo?.market_feed_active ? 'ACTIVE' : 'INACTIVE'}
          </span>
        </div>
        {brokerInfo?.error && (
          <div style={{ color: '#e53e3e', fontSize: '0.9rem', marginTop: '0.5rem' }}>
            Error: {brokerInfo.error}
          </div>
        )}
      </div>
    </div>
  );
});

export default BrokerDetails;