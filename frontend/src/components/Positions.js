import React from 'react';

const Positions = ({ data }) => {
  return (
    <section>
      <h2>Open Positions</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Entry Price</th>
            <th>Live Price</th>
            <th>P&L</th>
          </tr>
        </thead>
        <tbody>
          {data?.length > 0 ? (
            data.map((pos, index) => (
              <tr key={index}>
                <td>{pos.symbol}</td>
                <td className={pos.side.toLowerCase()}>{pos.side}</td>
                <td>{pos.qty}</td>
                <td>{pos.entry_price}</td>
                <td>{pos.live_price}</td>
                <td className={pos.pnl >= 0 ? 'positive' : 'negative'}>{pos.pnl}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan="6">No open positions.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
};

export default Positions;
