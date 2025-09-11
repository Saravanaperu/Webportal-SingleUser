import React from 'react';

const Trades = ({ data }) => {
  return (
    <section>
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
        <tbody>
          {data?.length > 0 ? (
            data.map((trade, index) => (
              <tr key={index}>
                <td>{trade.symbol}</td>
                <td className={trade.side.toLowerCase()}>{trade.side}</td>
                <td>{trade.qty}</td>
                <td>{trade.entry_price}</td>
                <td>{trade.exit_price}</td>
                <td className={trade.pnl >= 0 ? 'positive' : 'negative'}>{trade.pnl}</td>
                <td>{new Date(trade.exit_time).toLocaleTimeString()}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan="7">No trades yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
};

export default Trades;
