import React, { useState, useEffect } from 'react';
import axios from 'axios';

const PaperTradingToggle = React.memo(() => {
  const [paperStatus, setPaperStatus] = useState({
    is_paper_mode: false,
    stats: { current_balance: 100000, total_pnl: 0, total_trades: 0 }
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPaperStatus();
    const interval = setInterval(fetchPaperStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchPaperStatus = async () => {
    try {
      const response = await axios.get('/api/paper-trading/status');
      setPaperStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch paper trading status:', error);
    }
  };

  const togglePaperMode = async () => {
    setLoading(true);
    try {
      const action = paperStatus.is_paper_mode ? 'disable' : 'enable';
      await axios.post('/api/paper-trading/toggle', { action });
      await fetchPaperStatus();
    } catch (error) {
      console.error('Failed to toggle paper mode:', error);
    } finally {
      setLoading(false);
    }
  };

  const resetPaperAccount = async () => {
    if (window.confirm('Reset paper trading account to ₹1,00,000?')) {
      setLoading(true);
      try {
        await axios.post('/api/paper-trading/toggle', { action: 'reset' });
        await fetchPaperStatus();
      } catch (error) {
        console.error('Failed to reset paper account:', error);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.5rem 1rem',
      background: paperStatus.is_paper_mode 
        ? 'rgba(255, 193, 7, 0.2)' 
        : 'rgba(255, 255, 255, 0.1)',
      borderRadius: '8px',
      border: paperStatus.is_paper_mode 
        ? '1px solid #ffc107' 
        : '1px solid rgba(255, 255, 255, 0.2)',
      fontSize: '0.8rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
        <span style={{ 
          width: '8px', 
          height: '8px', 
          borderRadius: '50%', 
          background: paperStatus.is_paper_mode ? '#ffc107' : '#6c757d' 
        }}></span>
        <span style={{ fontWeight: '600', fontSize: '0.75rem' }}>
          {paperStatus.is_paper_mode ? 'Paper' : 'Live'}
        </span>
      </div>
      
      {paperStatus.is_paper_mode && (
        <div style={{ fontSize: '0.7rem', color: '#ffc107' }}>
          ₹{paperStatus.stats.current_balance?.toLocaleString('en-IN')} 
          ({paperStatus.stats.total_pnl >= 0 ? '+' : ''}₹{paperStatus.stats.total_pnl?.toFixed(0)})
        </div>
      )}
      
      <button
        onClick={togglePaperMode}
        disabled={loading}
        style={{
          padding: '0.25rem 0.5rem',
          fontSize: '0.7rem',
          border: 'none',
          borderRadius: '4px',
          background: paperStatus.is_paper_mode ? '#dc3545' : '#28a745',
          color: 'white',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontWeight: '600'
        }}
      >
        {loading ? '...' : (paperStatus.is_paper_mode ? 'Live' : 'Paper')}
      </button>
      
      {paperStatus.is_paper_mode && (
        <button
          onClick={resetPaperAccount}
          disabled={loading}
          style={{
            padding: '0.25rem 0.5rem',
            fontSize: '0.7rem',
            border: 'none',
            borderRadius: '4px',
            background: '#6c757d',
            color: 'white',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: '600'
          }}
        >
          Reset
        </button>
      )}
    </div>
  );
});

export default PaperTradingToggle;