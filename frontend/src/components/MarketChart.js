import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const MarketChart = ({ data }) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const seriesRef = useRef();

  useEffect(() => {
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 300,
        layout: { backgroundColor: '#ffffff', textColor: '#333' },
        grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
        timeScale: { timeVisible: true, secondsVisible: true }
      });
      seriesRef.current = chartRef.current.addCandlestickSeries();
    }
  }, []);

  useEffect(() => {
    if (data && data.length > 0 && seriesRef.current) {
        // This assumes the data is in the format: {time, open, high, low, close}
      seriesRef.current.setData(data);
    }
  }, [data]);

  return (
    <section id="chart-section">
      <h2>Market Chart</h2>
      <div id="trading-chart" ref={chartContainerRef}></div>
    </section>
  );
};

export default MarketChart;
