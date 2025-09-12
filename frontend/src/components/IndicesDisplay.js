import React from 'react';

const IndicesDisplay = React.memo(({ indices }) => {
  const hasValidData = indices && Object.values(indices).some(item => item.price > 0);
  
  const displayData = hasValidData ? indices : {
    NIFTY: { price: 0, change: 0, changePercent: 0 },
    BANKNIFTY: { price: 0, change: 0, changePercent: 0 },
    FINNIFTY: { price: 0, change: 0, changePercent: 0 }
  };

  return (
    <div className="card">
      <h3>📊 Market Indices</h3>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        {Object.entries(displayData).map(([name, data]) => (
          <div key={name} style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.75rem',
            background: 'linear-gradient(135deg, #f8f9fa, #e9ecef)',
            borderRadius: '8px',
            borderLeft: `4px solid ${data.change >= 0 ? '#38a169' : '#e53e3e'}`
          }}>
            <div>
              <div style={{ fontWeight: '700', fontSize: '0.9rem', color: '#2d3748' }}>{name}</div>
              <div style={{ fontSize: '0.8rem', color: '#718096' }}>Index</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#2d3748' }}>
                {data.price > 0 ? data.price.toLocaleString('en-IN', {minimumFractionDigits: 2}) : '--'}
              </div>
              <div style={{ 
                fontSize: '0.8rem', 
                fontWeight: '600',
                color: data.change >= 0 ? '#38a169' : '#e53e3e'
              }}>
                {data.price > 0 ? (
                  `${data.change >= 0 ? '+' : ''}${data.change.toFixed(2)} (${data.changePercent >= 0 ? '+' : ''}${data.changePercent.toFixed(2)}%)`
                ) : 'Loading...'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

export default IndicesDisplay;