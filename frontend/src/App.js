import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// Import components
import Header from './components/Header';
import AccountOverview from './components/AccountOverview';
import DailyStats from './components/DailyStats';
import MarketChart from './components/MarketChart';
import PnlChart from './components/PnlChart';
import PositionsTable from './components/PositionsTable';
import TradesTable from './components/TradesTable';
import LogsPanel from './components/LogsPanel';
import BrokerDetails from './components/BrokerDetails';
import IndicesDisplay from './components/IndicesDisplay';
import OptionsChain from './components/OptionsChain';

function App() {
  const [stats, setStats] = useState(null);
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [strategyParams, setStrategyParams] = useState(null);
  const [isStrategyRunning, setIsStrategyRunning] = useState(false);
  const [dataFeedConnected, setDataFeedConnected] = useState(false);
  const [indices, setIndices] = useState({});
  const fetchFrequentData = async () => {
    try {
      const [statsRes, positionsRes, tradesRes, indicesRes] = await Promise.all([
        axios.get('/api/stats'),
        axios.get('/api/positions'),
        axios.get('/api/trades'),
        axios.get('/api/indices')
      ]);

      setStats(statsRes.data);
      setPositions(positionsRes.data);
      setTrades(tradesRes.data);
      setIsStrategyRunning(statsRes.data.is_strategy_running || false);
      setDataFeedConnected(statsRes.data.data_feed_connected || false);
      
      if (indicesRes.data && Object.keys(indicesRes.data).length > 0) {
        setIndices(indicesRes.data);
      }
      
    } catch (error) {
      console.error("Failed to fetch frequent data:", error);
    }
  };

  const fetchPeriodicData = async () => {
    try {
      const [paramsRes, accountRes] = await Promise.all([
        axios.get('/api/strategy/parameters'),
        axios.get('/api/account')
      ]);

      setStrategyParams(paramsRes.data);
      setAccount(accountRes.data);
      
    } catch (error) {
      console.error("Failed to fetch periodic data:", error);
    }
  };

  useEffect(() => {
    fetchFrequentData();
    fetchPeriodicData();
    
    // Frequent updates every 3 seconds for real-time data
    const frequentInterval = setInterval(fetchFrequentData, 3000);
    // Periodic updates every 15 seconds for account data
    const periodicInterval = setInterval(fetchPeriodicData, 15000);
    
    return () => {
      clearInterval(frequentInterval);
      clearInterval(periodicInterval);
    };
  }, []);

  return (
    <div className="App">
      <Header isStrategyRunning={isStrategyRunning} strategyParams={strategyParams} />
      <main>
        <section id="overview">
          <BrokerDetails />
          <AccountOverview account={account} />
          <DailyStats stats={stats} dataFeedConnected={dataFeedConnected} isStrategyRunning={isStrategyRunning} />
        </section>
        
        <section id="indices-options">
          <IndicesDisplay indices={indices} />
          <OptionsChain />
        </section>
        
        <section id="positions-and-orders">
          <PositionsTable positions={positions} />
          <TradesTable trades={trades} />
        </section>
        
        <section id="charts">
          <MarketChart data={[]} />
          <PnlChart trades={trades} />
        </section>
        
        <LogsPanel />
      </main>
    </div>
  );
}

export default App;