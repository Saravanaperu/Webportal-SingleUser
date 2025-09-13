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
import NotificationSystem from './components/NotificationSystem';
import BacktestPanel from './components/BacktestPanel';

import IndicesDisplay from './components/IndicesDisplay';
import OptionsChain from './components/OptionsChain';
import { TradingProvider, useTradingContext } from './context/TradingContext';
import ErrorBoundary from './components/ErrorBoundary';

const AppContent = () => {
  const { account, positions, indices, stats, isConnected, loading } = useTradingContext();
  const [trades, setTrades] = useState([]);
  // Fetch trades data
  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const tradesRes = await axios.get('/api/trades');
        setTrades(tradesRes.data);
      } catch (error) {
        console.error('Failed to fetch trades:', error);
      }
    };

    fetchTrades();
    const interval = setInterval(fetchTrades, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="App" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading trading data...</div>
      </div>
    );
  }

  return (
    <div className="App">
      <Header 
        isStrategyRunning={stats?.is_strategy_running || false} 
      />
      <main>
        <section id="overview">
          <ErrorBoundary>
            <AccountOverview account={account} />
          </ErrorBoundary>
          <ErrorBoundary>
            <DailyStats 
              stats={stats} 
              dataFeedConnected={stats?.data_feed_connected || isConnected} 
              isStrategyRunning={stats?.is_strategy_running || false} 
            />
          </ErrorBoundary>
        </section>
        
        <section id="indices-options">
          <ErrorBoundary>
            <IndicesDisplay indices={indices || {}} />
          </ErrorBoundary>
          <OptionsChain />
        </section>
        
        <section id="positions-and-orders">
          <ErrorBoundary>
            <PositionsTable positions={positions || []} />
          </ErrorBoundary>
          <ErrorBoundary>
            <TradesTable trades={trades} />
          </ErrorBoundary>
        </section>
        
        <section id="charts">
          <MarketChart data={[]} />
          <ErrorBoundary>
            <PnlChart trades={trades} />
          </ErrorBoundary>
        </section>
        
        <BacktestPanel />
        <NotificationSystem />
      </main>
    </div>
  );
};

function App() {
  return (
    <TradingProvider>
      <AppContent />
    </TradingProvider>
  );
}

export default App;