import React, { useState } from 'react';
import axios from 'axios';
import StrategyParams from './StrategyParams';
import BrokerStatus from './BrokerStatus';

const Header = ({ isStrategyRunning, strategyParams }) => {
  const [isLoading, setIsLoading] = useState(false);

  const isMarketHours = () => {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentTime = hours * 100 + minutes;
    return currentTime >= 915 && currentTime <= 1530;
  };

  const handleStrategyToggle = async () => {
    if (!isStrategyRunning && !isMarketHours()) {
      alert('Market is closed. Trading hours are 9:15 AM to 3:30 PM.');
      return;
    }

    const action = isStrategyRunning ? 'stop' : 'start';
    setIsLoading(true);
    try {
      const response = await axios.post('/api/strategy/control', { action });
      if (response.data.error) {
        alert(response.data.error);
      }
    } catch (err) {
      console.error('Strategy control error:', err);
      alert(`Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKillSwitch = async () => {
    if (window.confirm('EMERGENCY STOP: This will halt all trading. Are you sure?')) {
      try {
        await axios.post('/api/strategy/control', { action: 'kill' });
        alert('Kill switch activated.');
      } catch (err) {
        console.error('Kill switch error:', err);
        alert(`Error: ${err.message}`);
      }
    }
  };

  return (
    <header className="header">
      <div>
        <h1>⚡ Options Scalping Portal</h1>
        <div className="connection-status">
          <span className={`status-indicator ${isMarketHours() ? 'connected' : 'disconnected'}`}></span>
          {isMarketHours() ? 'Market Open' : 'Market Closed'}
        </div>
      </div>
      <div className="header-right">
        <BrokerStatus />
        <button 
          className={`strategy-button ${isStrategyRunning ? 'stop' : 'start'}`}
          onClick={handleStrategyToggle} 
          disabled={isLoading}
        >
          {isLoading ? 'Processing...' : (isStrategyRunning ? '⏹️ Stop Strategy' : '▶️ Start Strategy')}
        </button>
        <button 
          className="strategy-button stop"
          onClick={handleKillSwitch}
          style={{ background: 'linear-gradient(45deg, #e53e3e, #c53030)' }}
        >
          🛑 Emergency Stop
        </button>
        <StrategyParams params={strategyParams} />
      </div>
    </header>
  );
};

export default Header;