import React from 'react';

const DailyStats = React.memo(({ stats, dataFeedConnected, isStrategyRunning }) => {
  const getPnlClass = (pnl) => (pnl >= 0 ? 'status-positive' : 'status-negative');

  return (
    <div className="card">
      <h3>Daily Performance</h3>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Realized P&L:</span>
          <span className={stats ? getPnlClass(stats.realized_pnl) : ''} style={{ fontWeight: '700', fontSize: '1.2rem' }}>
            {stats ? `₹${stats.realized_pnl?.toFixed(2)}` : '--'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Total Trades:</span>
          <span style={{ fontWeight: '600' }}>{stats ? stats.total_trades : '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Win Rate:</span>
          <span style={{ fontWeight: '600', color: '#17a2b8' }}>{stats ? `${stats.win_rate?.toFixed(1)}%` : '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Avg. Win:</span>
          <span className="status-positive" style={{ fontWeight: '600' }}>{stats ? `₹${stats.avg_win?.toFixed(2)}` : '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Avg. Loss:</span>
          <span className="status-negative" style={{ fontWeight: '600' }}>{stats ? `₹${stats.avg_loss?.toFixed(2)}` : '--'}</span>
        </div>
        <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid #e9ecef' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Strategy:</span>
          <span className={isStrategyRunning ? 'status-positive' : 'status-negative'} style={{ fontWeight: '600' }}>
            {isStrategyRunning ? 'RUNNING' : 'STOPPED'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Data Feed:</span>
          <span className={dataFeedConnected ? 'status-positive' : 'status-negative'} style={{ fontWeight: '600' }}>
            {dataFeedConnected ? 'CONNECTED' : 'DISCONNECTED'}
          </span>
        </div>
      </div>
    </div>
  );
});

export default DailyStats;
