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
import { TradingProvider, useTradingContext } from './context/TradingContext';
import ErrorBoundary from './components/ErrorBoundary';

const AppContent = () => {
  const { account, positions, indices, stats, isConnected, loading } = useTradingContext();
  const [trades, setTrades] = useState([]);
  const [strategyParams, setStrategyParams] = useState(null);

  // Fetch less frequent data
  useEffect(() => {
    const fetchStaticData = async () => {
      try {
        const [tradesRes, paramsRes] = await Promise.all([
          axios.get('/api/trades'),
          axios.get('/api/strategy/parameters')
        ]);
        setTrades(tradesRes.data);
        setStrategyParams(paramsRes.data);
      } catch (error) {
        console.error('Failed to fetch static data:', error);
      }
    };

    fetchStaticData();
    const interval = setInterval(fetchStaticData, 30000); // Every 30s
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
        strategyParams={strategyParams} 
      />
      <main>
        <section id="overview">
          <BrokerDetails />
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
        
        <LogsPanel />
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