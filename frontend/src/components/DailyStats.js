import React from 'react';

const DailyStats = ({ data }) => {
  const pnlClass = data?.realized_pnl >= 0 ? 'positive' : 'negative';
  const tradingStatusClass = data?.is_strategy_running ? 'positive' : 'negative';
  const dataFeedStatusClass = data?.data_feed_connected ? 'positive' : 'negative';

  return (
    <section>
      <h2>Daily Stats</h2>
      <div className="stats-grid">
        <p>Realized P&L: <span className={pnlClass}>{data?.realized_pnl ?? '--'}</span></p>
        <p>Total Trades: <span>{data?.total_trades ?? '--'}</span></p>
        <p>Win Rate: <span>{data?.win_rate ?? '--'}%</span></p>
        <p>Avg. Win: <span>{data?.avg_win ?? '--'}</span></p>
        <p>Avg. Loss: <span>{data?.avg_loss ?? '--'}</span></p>
        <p>Trading Status: <span className={tradingStatusClass}>{data?.is_strategy_running ? 'RUNNING' : 'STOPPED'}</span></p>
        <p>Data Feed: <span className={dataFeedStatusClass}>{data?.data_feed_connected ? 'CONNECTED' : 'DISCONNECTED'}</span></p>
      </div>
    </section>
  );
};

export default DailyStats;
