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

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/data`);

    ws.onopen = () => {
      console.log("WebSocket connection established.");
      setDataFeedConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        switch (message.type) {
          case 'ping':
            ws.send(JSON.stringify({ type: 'pong' }));
            break;
          case 'stats_update':
            setStats(message.data);
            setIsStrategyRunning(message.data.is_strategy_running);
            break;
          case 'order_update':
            // An order was filled/changed, refresh positions and trades
            axios.get('/api/positions').then(res => setPositions(res.data));
            axios.get('/api/trades').then(res => setTrades(res.data));
            break;
          case 'full_update':
            setStats(message.data.stats);
            setPositions(message.data.positions);
            setTrades(message.data.trades);
            setIsStrategyRunning(message.data.stats.is_strategy_running);
            break;
          case 'market_data':
            setMarketData(prevData => [...prevData, message.data]);
            break;
          default:
            break;
        }
      } catch (err) {
        console.error('WebSocket message parse error:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket Error:', err);
      setDataFeedConnected(false);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed. Attempting to reconnect in 5 seconds...");
      setDataFeedConnected(false);
      // Optional: implement reconnection logic here
    };

    return () => {
      ws.close();
    };
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
