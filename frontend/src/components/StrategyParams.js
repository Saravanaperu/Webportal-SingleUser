import React, { useState, useEffect } from 'react';
import axios from 'axios';

const StrategyParams = ({ params }) => {
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
    } catch (err) {
      console.error('Failed to save parameters:', err);
      setStatus(`Error: ${err.message}`);
    } finally {
      setTimeout(() => setStatus(''), 3000);
    }
  };

  return (
    <section id="strategy-params">
      <h2>Strategy Parameters</h2>
      <form id="params-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div>
            <label htmlFor="param-ema-short">EMA Short</label>
            <input type="number" id="param-ema-short" name="ema_short" value={formParams.ema_short} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="param-ema-long">EMA Long</label>
            <input type="number" id="param-ema-long" name="ema_long" value={formParams.ema_long} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="param-atr-period">ATR Period</label>
            <input type="number" id="param-atr-period" name="atr_period" value={formParams.atr_period} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="param-st-period">SuperTrend Period</label>
            <input type="number" id="param-st-period" name="supertrend_period" value={formParams.supertrend_period} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="param-st-multiplier">SuperTrend Multiplier</label>
            <input type="number" step="0.1" id="param-st-multiplier" name="supertrend_multiplier" value={formParams.supertrend_multiplier} onChange={handleChange} />
          </div>
        </div>
        <div className="form-actions">
          <button type="submit">Save Parameters</button>
          <span id="params-status">{status}</span>
        </div>
      </form>
    </section>
  );
};

export default StrategyParams;
