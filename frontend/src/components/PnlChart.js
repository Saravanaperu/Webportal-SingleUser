import React from 'react';

const PnlChart = ({ trades }) => {
  return (
    <section id="pnl-chart-section">
      <h2>Daily P&L Chart</h2>
      <div id="pnl-chart">
        <p>P&L Chart will be displayed here (lightweight-charts integration pending)</p>
      </div>
    </section>
  );
};

export default PnlChart;
