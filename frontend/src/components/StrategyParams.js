import React, { useState, useEffect } from 'react';
import axios from 'axios';

const StrategyParams = ({ params }) => {
  const [showModal, setShowModal] = useState(false);
  const [formParams, setFormParams] = useState({
    ema_short: '',
    ema_long: '',
    atr_period: '',
    supertrend_period: '',
    supertrend_multiplier: ''
  });
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (params) {
      setFormParams(params);
    }
  }, [params]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormParams(prevParams => ({
      ...prevParams,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('Saving...');
    try {
      const payload = {
        ...formParams,
        ema_short: parseInt(formParams.ema_short),
        ema_long: parseInt(formParams.ema_long),
        atr_period: parseInt(formParams.atr_period),
        supertrend_period: parseInt(formParams.supertrend_period),
        supertrend_multiplier: parseFloat(formParams.supertrend_multiplier)
      };
      await axios.post('/api/strategy/parameters', payload);
      setStatus('Parameters saved!');
      setTimeout(() => setShowModal(false), 1000);
    } catch (err) {
      console.error('Failed to save parameters:', err);
      setStatus(`Error: ${err.message}`);
    } finally {
      setTimeout(() => setStatus(''), 3000);
    }
  };

  return (
    <>
      <button 
        onClick={() => setShowModal(true)}
        style={{ 
          padding: '10px 15px',
          backgroundColor: '#6c757d',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px'
        }}
        title="Configure Strategy Parameters"
      >
        ⚙️ Settings
      </button>
      
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '8px',
            minWidth: '400px',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3>Strategy Parameters</h3>
              <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>×</button>
            </div>
            
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gap: '15px' }}>
                <div>
                  <label>EMA Short</label>
                  <input type="number" name="ema_short" value={formParams.ema_short} onChange={handleChange} style={{ width: '100%', padding: '8px', marginTop: '5px' }} />
                </div>
                <div>
                  <label>EMA Long</label>
                  <input type="number" name="ema_long" value={formParams.ema_long} onChange={handleChange} style={{ width: '100%', padding: '8px', marginTop: '5px' }} />
                </div>
                <div>
                  <label>ATR Period</label>
                  <input type="number" name="atr_period" value={formParams.atr_period} onChange={handleChange} style={{ width: '100%', padding: '8px', marginTop: '5px' }} />
                </div>
                <div>
                  <label>SuperTrend Period</label>
                  <input type="number" name="supertrend_period" value={formParams.supertrend_period} onChange={handleChange} style={{ width: '100%', padding: '8px', marginTop: '5px' }} />
                </div>
                <div>
                  <label>SuperTrend Multiplier</label>
                  <input type="number" step="0.1" name="supertrend_multiplier" value={formParams.supertrend_multiplier} onChange={handleChange} style={{ width: '100%', padding: '8px', marginTop: '5px' }} />
                </div>
              </div>
              <div style={{ marginTop: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                <button type="submit" style={{ padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Save Parameters</button>
                <span>{status}</span>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default StrategyParams;