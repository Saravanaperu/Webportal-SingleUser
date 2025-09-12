import React from 'react';

const IndicesDisplay = ({ indices }) => {
  // Check if we have valid data from broker API
  const hasValidData = indices && Object.values(indices).some(item => item.price > 0);
  const hasError = indices && indices.error;
  
  // Only use live broker data - no fallback/mock data
  let displayData;
  if (hasValidData) {
    displayData = indices;
  } else {
    displayData = {
      NIFTY: { price: 0, change: 0, changePercent: 0 },
      BANKNIFTY: { price: 0, change: 0, changePercent: 0 },
      FINNIFTY: { price: 0, change: 0, changePercent: 0 }
    };
  }

  // Check if market is likely closed (static prices)
  const isMarketClosed = () => {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentTime = hours * 100 + minutes;
    return currentTime < 915 || currentTime > 1530; // Before 9:15 AM or after 3:30 PM
  };

  const marketClosed = isMarketClosed();

  return (
    <div className="card">
      <h3>
        Indices {hasValidData ? (marketClosed ? '📊' : '🟢') : '🔄'}
        {marketClosed && hasValidData && <span style={{ fontSize: '0.8rem', color: '#666' }}> (Live Prices)</span>}
      </h3>
      <div style={{ display: 'grid', gap: '1rem' }}>
        {Object.entries(displayData).map(([name, data]) => (
          <div key={name} className="index-card" style={{
            background: data.change >= 0 
              ? 'linear-gradient(135deg, #28a745 0%, #20c997 100%)'
              : 'linear-gradient(135deg, #dc3545 0%, #e74c3c 100%)'
          }}>
            <div style={{ fontSize: '1.2rem', fontWeight: '600' }}>{name}</div>
            <div className="index-price">
              {data.price > 0 ? data.price.toFixed(2) : 'Loading...'}
            </div>
            <div className="index-change">
              {data.price > 0 ? (
                <>
                  {data.change >= 0 ? '+' : ''}{data.change.toFixed(2)} 
                  ({data.changePercent >= 0 ? '+' : ''}{data.changePercent.toFixed(2)}%)
                </>
              ) : (
                'Fetching data...'
              )}
            </div>
          </div>
        ))}
      </div>
      <div style={{ 
        marginTop: '1rem', 
        padding: '0.5rem', 
        background: hasValidData ? (marketClosed ? '#e2e3e5' : '#d4edda') : '#fff3cd', 
        borderRadius: '4px', 
        fontSize: '0.9rem', 
        color: hasValidData ? (marketClosed ? '#383d41' : '#155724') : '#856404' 
      }}>
        {hasValidData ? (
          marketClosed ? 
          '📊 Market Closed - Live Prices from Broker' : 
          '✅ Live Market Data from Broker'
        ) : hasError ? (
          '⚠️ Broker Connection Error - Retrying...'
        ) : (
          '🔄 Fetching live data from broker...'
        )}
      </div>
    </div>
  );
};

export default IndicesDisplay;