import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const LogsPanel = () => {
  const [logs, setLogs] = useState([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const logsEndRef = useRef(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await axios.get('/api/logs');
        setLogs(response.data.logs || []);
      } catch (error) {
        console.error('Failed to fetch logs:', error);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000); // Fetch logs every 2 seconds

    return () => clearInterval(interval);
  }, []);

  const getLogStyle = (level) => {
    switch (level?.toLowerCase()) {
      case 'error':
        return { color: '#dc3545' };
      case 'warning':
        return { color: '#ffc107' };
      case 'info':
        return { color: '#17a2b8' };
      default:
        return { color: '#333' };
    }
  };

  return (
    <section id="logs-panel" style={{ margin: '20px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
        <h2>System Logs</h2>
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ 
            padding: '5px 10px',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {isExpanded ? 'Collapse' : 'Expand'}
        </button>
      </div>
      
      {isExpanded && (
        <div style={{
          height: '300px',
          border: '1px solid #ccc',
          backgroundColor: '#f8f9fa',
          padding: '10px',
          overflow: 'auto',
          fontFamily: 'monospace',
          fontSize: '12px'
        }}>
          {logs.length === 0 ? (
            <p>No logs available</p>
          ) : (
            logs.map((log, index) => (
              <div key={index} style={getLogStyle(log.level)}>
                <span style={{ color: '#666' }}>[{log.timestamp}]</span> 
                <span style={{ fontWeight: 'bold' }}> {log.level?.toUpperCase()}</span>: {log.message}
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      )}
    </section>
  );
};

export default LogsPanel;