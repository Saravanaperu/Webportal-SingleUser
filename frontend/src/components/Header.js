import React, { useState } from 'react';
import axios from 'axios';
import StrategyParams from './StrategyParams';

const Header = ({ isStrategyRunning, strategyParams }) => {
  const [isLoading, setIsLoading] = useState(false);

  const isMarketHours = () => {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentTime = hours * 100 + minutes;
    
    // Market hours: 9:15 AM to 3:30 PM (915 to 1530)
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
    <header>
      <h1>Options Scalping Portal</h1>
      <div id="controls">
        <button id="strategy-toggle" onClick={handleStrategyToggle} disabled={isLoading}>
          {isLoading ? 'Processing...' : (isStrategyRunning ? 'Stop Strategy' : 'Start Strategy')}
        </button>
        <button id="kill-switch" onClick={handleKillSwitch}>EMERGENCY STOP</button>
        <StrategyParams params={strategyParams} />
      </div>
    </header>
  );
};

export default Header;