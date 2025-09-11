import React from 'react';

const DailyStats = ({ stats, dataFeedConnected, isStrategyRunning }) => {
  const getPnlClass = (pnl) => (pnl >= 0 ? 'positive' : 'negative');

  return (
    <div>
      <h2>Daily Stats</h2>
      <div id="daily-stats" className="stats-grid">
        <p>Realized P&L: <span id="realized-pnl" className={stats ? getPnlClass(stats.realized_pnl) : ''}>{stats ? `₹${stats.realized_pnl?.toFixed(2)}` : '--'}</span></p>
        <p>Total Trades: <span id="total-trades">{stats ? stats.total_trades : '--'}</span></p>
        <p>Win Rate: <span id="win-rate">{stats ? `${stats.win_rate?.toFixed(1)}%` : '--'}</span></p>
        <p>Avg. Win: <span id="avg-win">{stats ? `₹${stats.avg_win?.toFixed(2)}` : '--'}</span></p>
        <p>Avg. Loss: <span id="avg-loss">{stats ? `₹${stats.avg_loss?.toFixed(2)}` : '--'}</span></p>
        <p>Trading Status: <span id="trading-status" className={isStrategyRunning ? 'positive' : 'negative'}>{isStrategyRunning ? 'RUNNING' : 'STOPPED'}</span></p>
        <p>Data Feed: <span id="data-feed-status" className={dataFeedConnected ? 'positive' : 'negative'}>{dataFeedConnected ? 'CONNECTED' : 'DISCONNECTED'}</span></p>
      </div>
    </div>
  );
};

export default DailyStats;
