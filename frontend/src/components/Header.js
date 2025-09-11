import React, { useState } from 'react';
import axios from 'axios';

const Header = ({ isStrategyRunning }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleStrategyToggle = async () => {
    const action = isStrategyRunning ? 'stop' : 'start';
    setIsLoading(true);
    try {
      await axios.post('/api/strategy/control', { action });
      // The UI will be updated via a WebSocket 'stats_update' message.
    } catch (err) {
      console.error('Strategy control error:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKillSwitch = async () => {
    if (window.confirm('EMERGENCY STOP: This will halt all trading. Are you sure?')) {
      try {
        await axios.post('/api/strategy/control', { action: 'kill' });
        alert('Kill switch activated.');
        // UI will update via WebSocket.
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
      </div>
    </header>
  );
};

export default Header;
