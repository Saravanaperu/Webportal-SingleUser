import React from 'react';
import { controlStrategy } from '../api';

const StrategyControls = ({ isRunning }) => {
  const handleToggle = () => {
    const action = isRunning ? 'stop' : 'start';
    controlStrategy(action).catch(err => console.error(err));
  };

  const handleKill = () => {
    if (window.confirm('Are you sure you want to emergency stop all trading?')) {
      controlStrategy('kill').catch(err => console.error(err));
    }
  };

  return (
    <section>
      <h2>Strategy Controls</h2>
      <div>
        <button onClick={handleToggle} disabled={false}>
          {isRunning ? 'Stop Strategy' : 'Start Strategy'}
        </button>
        <button id="kill-switch" onClick={handleKill}>
          EMERGENCY STOP
        </button>
      </div>
    </section>
  );
};

export default StrategyControls;
