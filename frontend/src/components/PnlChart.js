import React from 'react';

const PnlChart = React.memo(({ trades }) => {
  const totalPnl = trades?.reduce((sum, trade) => sum + (trade.pnl || 0), 0) || 0;
  const winTrades = trades?.filter(trade => (trade.pnl || 0) > 0).length || 0;
  const totalTrades = trades?.length || 0;
  const winRate = totalTrades > 0 ? (winTrades / totalTrades * 100).toFixed(1) : 0;
  
  return (
    <div className="card">
      <h3>📈 Daily P&L Chart</h3>
      <div className="chart-container">
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '1rem', color: totalPnl >= 0 ? '#38a169' : '#e53e3e' }}>
            ₹{totalPnl.toFixed(2)}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: '600' }}>{totalTrades}</div>
              <div style={{ fontSize: '0.9rem', color: '#718096' }}>Total Trades</div>
            </div>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#4299e1' }}>{winRate}%</div>
              <div style={{ fontSize: '0.9rem', color: '#718096' }}>Win Rate</div>
            </div>
          </div>
          <div style={{ fontSize: '0.9rem', color: '#718096' }}>Interactive chart coming soon</div>
        </div>
      </div>
    </div>
  );
});

export default PnlChart;