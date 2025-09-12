import React from 'react';

const MarketChart = React.memo(({ data }) => {
  return (
    <div className="card">
      <h3>📉 Market Chart</h3>
      <div className="chart-container">
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: '#4299e1' }}>
            BANKNIFTY
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#38a169' }}>54,809.30</div>
              <div style={{ fontSize: '0.9rem', color: '#718096' }}>Current Price</div>
            </div>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#38a169' }}>+139.70</div>
              <div style={{ fontSize: '0.9rem', color: '#718096' }}>Change</div>
            </div>
          </div>
          <div style={{ fontSize: '0.9rem', color: '#718096' }}>TradingView integration coming soon</div>
        </div>
      </div>
    </div>
  );
});

export default MarketChart;