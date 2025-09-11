import React from 'react';

const IndicesDisplay = ({ indices }) => {
  // Fallback data when broker is not available
  const fallbackData = {
    NIFTY: { price: 19847.25, change: -23.45, changePercent: -0.12 },
    BANKNIFTY: { price: 45234.80, change: 156.30, changePercent: 0.35 },
    FINNIFTY: { price: 18965.15, change: 42.85, changePercent: 0.23 }
  };
  
  // Check if we have valid data or errors
  const hasError = indices && indices.error;
  const hasValidData = indices && Object.values(indices).some(item => item.price > 0);
  const hasData = hasValidData || hasError;
  
  // Use provided data, fallback data, or loading state
  let displayData;
  if (hasValidData) {
    displayData = indices;
  } else if (hasError) {
    displayData = fallbackData;
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
        Indices {hasData ? (marketClosed ? '📊' : '🟢') : '🔄'}
        {marketClosed && hasData && <span style={{ fontSize: '0.8rem', color: '#666' }}> (Last Traded Prices)</span>}
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
        background: hasValidData ? (marketClosed ? '#e2e3e5' : '#d4edda') : hasError ? '#f8d7da' : '#fff3cd', 
        borderRadius: '4px', 
        fontSize: '0.9rem', 
        color: hasValidData ? (marketClosed ? '#383d41' : '#155724') : hasError ? '#721c24' : '#856404' 
      }}>
        {hasValidData ? (
          marketClosed ? 
          '📊 Market Closed - Showing Last Traded Prices' : 
          '✅ Live Market Data'
        ) : hasError ? (
          '⚠️ Broker Unavailable - Showing Demo Data'
        ) : (
          '🔄 Connecting to broker for live data...'
        )}
      </div>
    </div>
  );
};

export default IndicesDisplay;