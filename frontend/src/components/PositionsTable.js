import React from 'react';

const PositionsTable = ({ positions }) => {
  return (
    <div id="positions">
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
        <tbody id="positions-table-body">
          {positions && positions.length > 0 ? (
            positions.map((pos, index) => {
              const pnlClass = pos.pnl >= 0 ? 'positive' : 'negative';
              return (
                <tr key={index}>
                  <td>{pos.symbol}</td>
                  <td className={pos.side.toLowerCase()}>{pos.side}</td>
                  <td>{pos.qty}</td>
                  <td>{Number(pos.entry_price).toFixed(2)}</td>
                  <td>{Number(pos.live_price).toFixed(2)}</td>
                  <td className={pnlClass}>{pos.pnl.toFixed(2)}</td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan="6">No open positions.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default PositionsTable;
