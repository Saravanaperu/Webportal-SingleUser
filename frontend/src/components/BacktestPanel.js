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
        
        <div className="form-row">
          <label>Strategy:</label>
          <select 
            value={backtestParams.strategy} 
            onChange={(e) => setBacktestParams({...backtestParams, strategy: e.target.value})}
          >
            <option value="options_scalping">High Win Rate (Conservative)</option>
            <option value="aggressive_scalping">Aggressive Scalping (Daily Profits)</option>
          </select>
        </div>
        
        <div className="form-row">
          <label>Timeframe:</label>
          <select 
            value={backtestParams.timeframe || 'ONE_MINUTE'} 
            onChange={(e) => setBacktestParams({...backtestParams, timeframe: e.target.value})}
          >
            <option value="ONE_MINUTE">1 Minute</option>
            <option value="THREE_MINUTE">3 Minutes</option>
            <option value="FIVE_MINUTE">5 Minutes</option>
            <option value="TEN_MINUTE">10 Minutes</option>
            <option value="FIFTEEN_MINUTE">15 Minutes</option>
          </select>
        </div>
        
        <button onClick={runBacktest} disabled={loading} className="btn-primary">
          {loading ? 'Testing All Timeframes...' : 'Find Best Timeframe'}
        </button>
      </div>

      {results && (
        <div className="backtest-results">
          {results.error ? (
            <div className="error">{results.error}</div>
          ) : (
            <>
              <h4 style={{marginBottom: '1rem', textAlign: 'center'}}>
                {backtestParams.strategy === 'aggressive_scalping' ? 
                  '⚡ Aggressive Scalping Results' : 
                  '🎯 High Win Rate Results'
                }
              </h4>
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
              
              {results.timeframe_comparison && (
                <div className="timeframe-comparison">
                  <h4 style={{marginTop: '1.5rem', marginBottom: '1rem'}}>⏱️ Timeframe Analysis (Best: {results.best_timeframe})</h4>
                  <div className="timeframe-grid">
                    {Object.entries(results.timeframe_comparison).map(([tf, stats]) => (
                      <div key={tf} className={`timeframe-item ${tf === results.best_timeframe ? 'best' : ''}`}>
                        <strong>{tf.replace('_', ' ')}</strong><br/>
                        <span>{stats}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {results.daily_breakdown && (
                <div className="daily-breakdown">
                  <h4 style={{marginTop: '1.5rem', marginBottom: '1rem'}}>📅 Daily Performance</h4>
                  <div className="daily-table">
                    <table>
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Trades</th>
                          <th>Win Rate</th>
                          <th>P&L</th>
                          <th>Return %</th>
                          <th>Capital</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.daily_breakdown.map((day, index) => (
                          <tr key={index}>
                            <td>{day.date}</td>
                            <td>{day.trades}</td>
                            <td>{day.win_rate?.toFixed(1)}%</td>
                            <td className={day.pnl >= 0 ? 'positive' : 'negative'}>
                              ₹{day.pnl?.toFixed(0)}
                            </td>
                            <td className={day.return_pct >= 0 ? 'positive' : 'negative'}>
                              {day.return_pct?.toFixed(2)}%
                            </td>
                            <td>₹{day.end_capital?.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default BacktestPanel;