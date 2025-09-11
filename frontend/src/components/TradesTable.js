import React from 'react';

const TradesTable = ({ trades }) => {
  return (
    <div id="trades">
      <h2>Historical Trades</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>P&L</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody id="trades-table-body">
          {trades && trades.length > 0 ? (
            trades.map((trade, index) => {
              const pnlClass = trade.pnl >= 0 ? 'positive' : 'negative';
              const entryTime = new Date(trade.entry_time).toLocaleTimeString();
              return (
                <tr key={index}>
                  <td>{trade.symbol}</td>
                  <td className={trade.side.toLowerCase()}>{trade.side}</td>
                  <td>{trade.qty}</td>
                  <td>₹{Number(trade.entry_price).toFixed(2)}</td>
                  <td>₹{Number(trade.exit_price).toFixed(2)}</td>
                  <td className={pnlClass}>₹{trade.pnl.toFixed(2)}</td>
                  <td>{entryTime}</td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan="7">No trades yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default TradesTable;
