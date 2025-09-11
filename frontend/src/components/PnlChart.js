import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const PnlChart = ({ trades }) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const seriesRef = useRef();

  useEffect(() => {
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 250,
        layout: { backgroundColor: '#ffffff', textColor: '#333' },
        grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
        timeScale: { timeVisible: true, secondsVisible: false }
      });
      seriesRef.current = chartRef.current.addAreaSeries({
        topColor: 'rgba(46, 204, 113, 0.56)',
        bottomColor: 'rgba(46, 204, 113, 0.04)',
        lineColor: 'rgba(46, 204, 113, 1)',
        lineWidth: 2
      });
    }
  }, []);

  useEffect(() => {
    if (trades && trades.length > 0 && seriesRef.current) {
      let cumulativePnl = 0;
      const pnlData = trades.reduce((acc, trade) => {
        cumulativePnl += trade.pnl;
        acc.push({
          time: new Date(trade.exit_time).getTime() / 1000,
          value: cumulativePnl
        });
        return acc;
      }, []);
      seriesRef.current.setData(pnlData);
    }
  }, [trades]);

  return (
    <section id="pnl-chart-section">
      <h2>Daily P&L Chart</h2>
      <div id="pnl-chart" ref={chartContainerRef}></div>
    </section>
  );
};

export default PnlChart;
