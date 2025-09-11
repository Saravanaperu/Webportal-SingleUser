import React, { useState, useEffect } from 'react';
import { getStrategyParams, setStrategyParams } from '../api';

const StrategyParameters = () => {
  const [params, setParams] = useState({});
  const [status, setStatus] = useState('');

  useEffect(() => {
    getStrategyParams()
      .then(response => setParams(response.data))
      .catch(err => console.error(err));
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setParams(prevParams => ({
      ...prevParams,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setStatus('Saving...');
    setStrategyParams(params)
      .then(() => setStatus('Saved!'))
      .catch(() => setStatus('Error!'))
      .finally(() => setTimeout(() => setStatus(''), 3000));
  };

  return (
    <section>
      <h2>Strategy Parameters</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          {Object.keys(params).map(key => (
            <div key={key}>
              <label htmlFor={key}>{key}</label>
              <input
                type="number"
                id={key}
                name={key}
                value={params[key] || ''}
                onChange={handleChange}
              />
            </div>
          ))}
        </div>
        <button type="submit">Save Parameters</button>
        <span>{status}</span>
      </form>
    </section>
  );
};

export default StrategyParameters;
