import React, { useState, useEffect } from 'react';
import axios from 'axios';

const OptionsChain = () => {
  const [optionsData, setOptionsData] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState('BANKNIFTY');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Clear existing data when switching indices
    setOptionsData([]);
    setLoading(true);
    
    // Fetch data for selected index
    const fetchOptionsChain = async () => {
      try {
        console.log(`Fetching options chain for ${selectedIndex}...`);
        const response = await axios.get(`/api/options-chain/${selectedIndex}`);
        console.log(`Received response for ${selectedIndex}:`, response.data);
        
        if (response.data && Array.isArray(response.data) && response.data.length > 0) {
          setOptionsData(response.data);
          console.log(`Set options data for ${selectedIndex}, length:`, response.data.length);
        } else {
          console.warn(`No options data received for ${selectedIndex}`, response.data);
          setOptionsData([]);
        }
      } catch (error) {
        console.error(`Failed to fetch options chain for ${selectedIndex}:`, error);
        setOptionsData([]);
      } finally {
        setLoading(false);
      }
    };

    // Immediate fetch when index changes
    fetchOptionsChain();
    
    // Set up interval for periodic updates
    const interval = setInterval(() => {
      fetchOptionsChain();
    }, 3000);
    return () => clearInterval(interval);
  }, [selectedIndex]);

  const isATM = (strike) => {
    if (optionsData.length === 0) return false;
    const middleIndex = Math.floor(optionsData.length / 2);
    const atmStrike = optionsData[middleIndex]?.strike || 0;
    // Different strike intervals for different indices
    const tolerance = selectedIndex === 'BANKNIFTY' ? 100 : 50;
    return Math.abs(strike - atmStrike) <= tolerance;
  };

  const hasData = optionsData.some(item => item.call?.ltp > 0 || item.put?.ltp > 0);

  // Check if market is likely closed
  const isMarketClosed = () => {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentTime = hours * 100 + minutes;
    return currentTime < 915 || currentTime > 1530;
  };

  const marketClosed = isMarketClosed();

  return (
    <div className="card" key={selectedIndex}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>
          {selectedIndex} Options Chain {hasData ? (marketClosed ? '📊' : '🟢') : '🔄'}
          {marketClosed && hasData && <span style={{ fontSize: '0.8rem', color: '#666' }}> (LTP)</span>}
        </h3>
        <select 
          id="index-selector"
          name="selectedIndex"
          value={selectedIndex} 
          onChange={(e) => setSelectedIndex(e.target.value)}
          style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          <option value="BANKNIFTY">BANKNIFTY</option>
          <option value="NIFTY">NIFTY</option>
          <option value="FINNIFTY">FINNIFTY</option>
        </select>
      </div>
      
      <div className="options-chain">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1rem', padding: '0.5rem', background: '#f8f9fa', fontWeight: '600' }}>
          <div style={{ textAlign: 'center', color: '#28a745' }}>CALL</div>
          <div style={{ textAlign: 'center' }}>STRIKE</div>
          <div style={{ textAlign: 'center', color: '#dc3545' }}>PUT</div>
        </div>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            Loading {selectedIndex} options data...
          </div>
        ) : optionsData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            No options data available for {selectedIndex}
          </div>
        ) : (
          optionsData.map((option) => (
            <div 
              key={option.strike} 
              className="option-strike"
              style={{
                background: isATM(option.strike) ? 'rgba(255, 193, 7, 0.1)' : 'transparent',
                border: isATM(option.strike) ? '2px solid #ffc107' : 'none'
              }}
            >
              <div className="call-option">
                <div>
                  <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>
                    ₹{option.call?.ltp > 0 ? option.call.ltp.toFixed(2) : '--'}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#666' }}>
                    Vol: {option.call?.volume?.toLocaleString() || 0}
                  </div>
                </div>
              </div>
              
              <div className="strike-price">
                {option.strike}
                {isATM(option.strike) && <div style={{ fontSize: '0.7rem', color: '#ffc107' }}>ATM</div>}
              </div>
              
              <div className="put-option">
                <div>
                  <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>
                    ₹{option.put?.ltp > 0 ? option.put.ltp.toFixed(2) : '--'}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#666' }}>
                    Vol: {option.put?.volume?.toLocaleString() || 0}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      
      <div style={{ 
        marginTop: '1rem', 
        padding: '1rem', 
        background: hasData ? (marketClosed ? '#e2e3e5' : '#d4edda') : '#fff3cd', 
        borderRadius: '8px' 
      }}>
        <h4 style={{ 
          color: hasData ? (marketClosed ? '#383d41' : '#155724') : '#856404', 
          marginBottom: '0.5rem' 
        }}>
          {hasData ? (marketClosed ? '📊 Market Closed - Last Traded Prices' : '✅ Live Options Data') : '🔄 Loading Data'}
        </h4>
        <div style={{ 
          fontSize: '0.9rem', 
          color: hasData ? (marketClosed ? '#383d41' : '#155724') : '#856404' 
        }}>
          • <strong>Focus:</strong> ATM options for high gamma scalping<br/>
          • <strong>Target:</strong> 20-50% profit in 2-5 minutes<br/>
          • <strong>Risk:</strong> 40% stop loss, theta protection<br/>
          • <strong>Status:</strong> {hasData ? (marketClosed ? 'Showing last traded prices' : 'Live market data active') : 'Fetching from broker...'}
        </div>
      </div>
    </div>
  );
};

export default OptionsChain;