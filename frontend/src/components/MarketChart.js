import React, { useEffect, useRef } from 'react';

const MarketChart = ({ data }) => {
  const canvasRef = useRef();

  useEffect(() => {
    if (!canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw sample candlestick chart
    const sampleData = [
      { open: 100, high: 110, low: 95, close: 105 },
      { open: 105, high: 115, low: 100, close: 108 },
      { open: 108, high: 120, low: 105, close: 112 },
      { open: 112, high: 118, low: 108, close: 115 },
      { open: 115, high: 125, low: 110, close: 120 }
    ];
    
    const width = canvas.width;
    const height = canvas.height;
    const candleWidth = width / sampleData.length * 0.8;
    const maxPrice = Math.max(...sampleData.map(d => d.high));
    const minPrice = Math.min(...sampleData.map(d => d.low));
    const priceRange = maxPrice - minPrice;
    
    sampleData.forEach((candle, i) => {
      const x = (i + 0.5) * (width / sampleData.length);
      const openY = height - ((candle.open - minPrice) / priceRange) * height;
      const closeY = height - ((candle.close - minPrice) / priceRange) * height;
      const highY = height - ((candle.high - minPrice) / priceRange) * height;
      const lowY = height - ((candle.low - minPrice) / priceRange) * height;
      
      // Draw wick
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, highY);
      ctx.lineTo(x, lowY);
      ctx.stroke();
      
      // Draw body
      const bodyHeight = Math.abs(closeY - openY);
      const bodyY = Math.min(openY, closeY);
      
      ctx.fillStyle = candle.close > candle.open ? '#26a69a' : '#ef5350';
      ctx.fillRect(x - candleWidth/2, bodyY, candleWidth, bodyHeight);
    });
    
  }, [data]);

  return (
    <section id="chart-section">
      <h2>Market Chart</h2>
      <div style={{ width: '100%', height: '300px', border: '1px solid #ccc', position: 'relative' }}>
        <canvas 
          ref={canvasRef} 
          width={600} 
          height={300} 
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </section>
  );
};

export default MarketChart;