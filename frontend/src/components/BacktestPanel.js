import React, { useState } from 'react';
import axios from 'axios';

const BacktestPanel = () => {
  const [backtestParams, setBacktestParams] = useState({
    symbol: 'BANKNIFTY',
    startDate: '',
    endDate: '',
    capital: 100000,
    strategy: 'options_scalping'
  });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/backtest/run', backtestParams);
      setResults(response.data);
    } catch (error) {
      console.error('Backtest failed:', error);
      setResults({ error: 'Backtest failed' });
    }
    setLoading(false);
  };

  return (
    <div className="card backtest-panel">
      <h3>📊 Backtest Strategy</h3>
      
      <div className="backtest-form">
        <div className="form-row">
          <label>Symbol:</label>
          <select 
            value={backtestParams.symbol} 
            onChange={(e) => setBacktestParams({...backtestParams, symbol: e.target.value})}
          >
            <option value="BANKNIFTY">BANKNIFTY</option>
            <option value="NIFTY">NIFTY</option>
            <option value="FINNIFTY">FINNIFTY</option>
          </select>
        </div>
        
        <div className="form-row">
          <label>Start Date:</label>
          <input 
            type="date" 
            value={backtestParams.startDate}
            onChange={(e) => setBacktestParams({...backtestParams, startDate: e.target.value})}
          />
        </div>
        
        <div className="form-row">
          <label>End Date:</label>
          <input 
            type="date" 
            value={backtestParams.endDate}
            onChange={(e) => setBacktestParams({...backtestParams, endDate: e.target.value})}
          />
        </div>
        
        <div className="form-row">
          <label>Capital (₹):</label>
          <input 
            type="number" 
            value={backtestParams.capital}
            onChange={(e) => setBacktestParams({...backtestParams, capital: parseInt(e.target.value)})}
          />
        </div>
        
        <button onClick={runBacktest} disabled={loading} className="btn-primary">
          {loading ? 'Running...' : 'Run Backtest'}
        </button>
      </div>

      {results && (
        <div className="backtest-results">
          {results.error ? (
            <div className="error">{results.error}</div>
          ) : (
            <div className="results-grid">
              <div className="result-item">
                <span>Total Return:</span>
                <span className={results.total_return >= 0 ? 'positive' : 'negative'}>
                  {results.total_return?.toFixed(2)}%
                </span>
              </div>
              <div className="result-item">
                <span>Win Rate:</span>
                <span>{results.win_rate?.toFixed(1)}%</span>
              </div>
              <div className="result-item">
                <span>Total Trades:</span>
                <span>{results.total_trades}</span>
              </div>
              <div className="result-item">
                <span>Max Drawdown:</span>
                <span className="negative">{results.max_drawdown?.toFixed(2)}%</span>
              </div>
              <div className="result-item">
                <span>Sharpe Ratio:</span>
                <span>{results.sharpe_ratio?.toFixed(2)}</span>
              </div>
              <div className="result-item">
                <span>Final Capital:</span>
                <span>₹{results.final_capital?.toLocaleString()}</span>
              </div>
              <div className="result-item">
                <span>Avg Win:</span>
                <span className="positive">₹{results.avg_win?.toFixed(0)}</span>
              </div>
              <div className="result-item">
                <span>Avg Loss:</span>
                <span className="negative">₹{results.avg_loss?.toFixed(0)}</span>
              </div>
              <div className="result-item">
                <span>Avg Hold Time:</span>
                <span>{results.avg_hold_time?.toFixed(1)} min</span>
              </div>
              <div className="result-item">
                <span>Profit Factor:</span>
                <span className={results.profit_factor >= 2 ? 'positive' : 'negative'}>
                  {results.profit_factor === Infinity ? '∞' : results.profit_factor?.toFixed(2)}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BacktestPanel;