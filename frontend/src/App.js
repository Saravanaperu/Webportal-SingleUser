import React, { useState, useEffect } from 'react';
import AccountOverview from './components/AccountOverview';
import DailyStats from './components/DailyStats';
import StrategyControls from './components/StrategyControls';
import StrategyParameters from './components/StrategyParameters';
import Positions from './components/Positions';
import Trades from './components/Trades';
import { getAccount, getPositions, getTrades, getStats, connectWebSocket } from './api';

function App() {
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [accountRes, positionsRes, tradesRes, statsRes] = await Promise.all([
          getAccount(),
          getPositions(),
          getTrades(),
          getStats(),
        ]);
        setAccount(accountRes.data);
        setPositions(positionsRes.data);
        setTrades(tradesRes.data);
        setStats(statsRes.data);
      } catch (error) {
        console.error('Error fetching initial data:', error);
      }
    };

    fetchData();

    const socket = connectWebSocket((data) => {
      const message = JSON.parse(data);
      switch (message.type) {
        case 'stats_update':
          setStats(message.data);
          break;
        case 'order_update':
          getPositions().then(res => setPositions(res.data));
          getTrades().then(res => setTrades(res.data));
          break;
        case 'full_update':
          setStats(message.data.stats);
          setPositions(message.data.positions);
          setTrades(message.data.trades);
          break;
        default:
          break;
      }
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Options Scalping Portal</h1>
      </header>
      <main>
        <AccountOverview data={account} />
        <DailyStats data={stats} />
        <StrategyControls isRunning={stats?.is_strategy_running} />
        <StrategyParameters />
        <Positions data={positions} />
        <Trades data={trades} />
      </main>
    </div>
  );
}

export default App;
