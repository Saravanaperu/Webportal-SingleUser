import React, { useState, useEffect } from 'react';
import axios from 'axios';

const OptionsChain = React.memo(() => {
  const [optionsData, setOptionsData] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState('BANKNIFTY');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    const fetchOptionsChain = async () => {
      try {
        const response = await axios.get(`/api/options-chain/${selectedIndex}`);
        if (response.data && Array.isArray(response.data)) {
          setOptionsData(response.data);
        }
      } catch (error) {
        console.error(`Failed to fetch options chain:`, error);
      } finally {
        setLoading(false);
      }
    };

    fetchOptionsChain();
    const interval = setInterval(fetchOptionsChain, 10000); // Reduced frequency
    return () => clearInterval(interval);
  }, [selectedIndex]);

  const isATM = (strike) => {
    if (optionsData.length === 0) return false;
    const middleIndex = Math.floor(optionsData.length / 2);
    return optionsData[middleIndex]?.strike === strike;
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>💹 Options Chain</h3>
        <select 
          value={selectedIndex} 
          onChange={(e) => setSelectedIndex(e.target.value)}
          style={{ 
            padding: '0.5rem 1rem', 
            borderRadius: '8px', 
            border: '1px solid #e2e8f0',
            background: 'white',
            fontWeight: '600'
          }}
        >
          <option value="BANKNIFTY">BANKNIFTY</option>
          <option value="NIFTY">NIFTY</option>
          <option value="FINNIFTY">FINNIFTY</option>
        </select>
      </div>
      
      {loading ? (
        <div className="loading">Loading options data...</div>
      ) : (
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 80px 1fr', 
            gap: '0.5rem',
            padding: '0.5rem',
            background: 'linear-gradient(135deg, #4299e1, #63b3ed)',
            color: 'white',
            fontWeight: '600',
            fontSize: '0.9rem',
            borderRadius: '8px 8px 0 0',
            position: 'sticky',
            top: 0,
            zIndex: 1
          }}>
            <div style={{ textAlign: 'center' }}>CALL</div>
            <div style={{ textAlign: 'center' }}>STRIKE</div>
            <div style={{ textAlign: 'center' }}>PUT</div>
          </div>
          
          {optionsData.slice(0, 7).map((option) => (
            <div 
              key={option.strike}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 80px 1fr',
                gap: '0.5rem',
                padding: '0.5rem',
                borderBottom: '1px solid #e2e8f0',
                background: isATM(option.strike) ? 'rgba(255, 193, 7, 0.1)' : 'transparent'
              }}
            >
              <div style={{ textAlign: 'center', color: '#38a169', fontWeight: '600' }}>
                ₹{option.call?.ltp?.toFixed(2) || '--'}
                <div style={{ fontSize: '0.75rem', color: '#718096' }}>
                  {option.call?.volume ? `${(option.call.volume/1000).toFixed(0)}K` : '--'}
                </div>
              </div>
              
              <div style={{ 
                textAlign: 'center', 
                fontWeight: '700',
                background: isATM(option.strike) ? '#ffc107' : '#f7fafc',
                borderRadius: '4px',
                padding: '0.25rem',
                fontSize: '0.9rem'
              }}>
                {option.strike}
                {isATM(option.strike) && <div style={{ fontSize: '0.6rem', color: '#744210' }}>ATM</div>}
              </div>
              
              <div style={{ textAlign: 'center', color: '#e53e3e', fontWeight: '600' }}>
                ₹{option.put?.ltp?.toFixed(2) || '--'}
                <div style={{ fontSize: '0.75rem', color: '#718096' }}>
                  {option.put?.volume ? `${(option.put.volume/1000).toFixed(0)}K` : '--'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div style={{ 
        marginTop: '1rem', 
        padding: '0.75rem', 
        background: 'linear-gradient(135deg, #f7fafc, #edf2f7)', 
        borderRadius: '8px',
        fontSize: '0.85rem',
        color: '#4a5568'
      }}>
        <strong>Scalping Focus:</strong> ATM options • <strong>Target:</strong> 20-50% • <strong>Risk:</strong> 40% SL
      </div>
    </div>
  );
});

export default OptionsChain;