import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// Import components
import Header from './components/Header';
import AccountOverview from './components/AccountOverview';
import DailyStats from './components/DailyStats';
import StrategyParams from './components/StrategyParams';
import MarketChart from './components/MarketChart';
import PnlChart from './components/PnlChart';
import PositionsTable from './components/PositionsTable';
import TradesTable from './components/TradesTable';

function App() {
  const [stats, setStats] = useState(null);
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [strategyParams, setStrategyParams] = useState(null);
  const [isStrategyRunning, setIsStrategyRunning] = useState(false);
  const [dataFeedConnected, setDataFeedConnected] = useState(false);
  const [marketData, setMarketData] = useState([]);

  const fetchInitialData = async () => {
    try {
      console.log("Fetching initial data...");
      const [statsRes, positionsRes, tradesRes, paramsRes, accountRes] = await Promise.all([
        axios.get('/api/stats'),
        axios.get('/api/positions'),
        axios.get('/api/trades'),
        axios.get('/api/strategy/parameters'),
        axios.get('/api/account'),
      ]);

      setStats(statsRes.data);
      setPositions(positionsRes.data);
      setTrades(tradesRes.data);
      setStrategyParams(paramsRes.data);
      setAccount(accountRes.data);
      setIsStrategyRunning(statsRes.data.is_strategy_running);
      setDataFeedConnected(statsRes.data.data_feed_connected);
    } catch (error) {
      console.error("Failed to fetch initial data:", error);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  return (
    <div className="App">
      <Header isStrategyRunning={isStrategyRunning} />
      <main>
        <section id="overview">
          <AccountOverview account={account} />
          <DailyStats stats={stats} dataFeedConnected={dataFeedConnected} isStrategyRunning={isStrategyRunning} />
        </section>
        <StrategyParams params={strategyParams} />
        <section id="charts">
          <MarketChart data={marketData} />
          <PnlChart trades={trades} />
        </section>
        <section id="positions-and-orders">
          <PositionsTable positions={positions} />
          <TradesTable trades={trades} />
        </section>
      </main>
    </div>
  );
}

export default App;