import React, { useEffect, useRef } from 'react';

const PnlChart = ({ trades }) => {
  const canvasRef = useRef();

  useEffect(() => {
    if (!canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Sample P&L data
    const samplePnL = [0, 150, -50, 200, 100, 350, 250, 400, 300, 500];
    
    if (samplePnL.length < 2) return;
    
    const width = canvas.width;
    const height = canvas.height;
    const maxPnL = Math.max(...samplePnL);
    const minPnL = Math.min(...samplePnL);
    const pnlRange = maxPnL - minPnL || 1;
    
    // Draw grid lines
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = (i / 5) * height;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    
    // Draw zero line
    const zeroY = height - ((-minPnL) / pnlRange) * height;
    ctx.strokeStyle = '#666';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(width, zeroY);
    ctx.stroke();
    
    // Draw P&L area
    ctx.beginPath();
    ctx.moveTo(0, height - ((samplePnL[0] - minPnL) / pnlRange) * height);
    
    samplePnL.forEach((pnl, i) => {
      const x = (i / (samplePnL.length - 1)) * width;
      const y = height - ((pnl - minPnL) / pnlRange) * height;
      ctx.lineTo(x, y);
    });
    
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    
    // Fill area
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(46, 204, 113, 0.3)');
    gradient.addColorStop(1, 'rgba(46, 204, 113, 0.1)');
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // Draw line
    ctx.beginPath();
    ctx.moveTo(0, height - ((samplePnL[0] - minPnL) / pnlRange) * height);
    
    samplePnL.forEach((pnl, i) => {
      const x = (i / (samplePnL.length - 1)) * width;
      const y = height - ((pnl - minPnL) / pnlRange) * height;
      ctx.lineTo(x, y);
    });
    
    ctx.strokeStyle = '#2ecc71';
    ctx.lineWidth = 2;
    ctx.stroke();
    
  }, [trades]);

  return (
    <section id="pnl-chart-section">
      <h2>Daily P&L Chart</h2>
      <div style={{ width: '100%', height: '250px', border: '1px solid #ccc', position: 'relative' }}>
        <canvas 
          ref={canvasRef} 
          width={600} 
          height={250} 
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </section>
  );
};

export default PnlChart;