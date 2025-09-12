import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const LogsPanel = () => {
  const [logs, setLogs] = useState([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const logsEndRef = useRef(null);

  const scrollToBottom = () => {
    if (isExpanded) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs, isExpanded]);

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
    const interval = setInterval(fetchLogs, 5000); // Reduced frequency
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card logs-panel">
      <div 
        className="logs-header" 
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3>🔍 System Logs ({logs.length})</h3>
        <span style={{ 
          fontSize: '1.2rem', 
          transition: 'transform 0.3s ease', 
          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' 
        }}>
          ▼
        </span>
      </div>
      <div className={`logs-content ${!isExpanded ? 'collapsed' : ''}`}>
        {logs.length > 0 ? (
          logs.slice(-50).reverse().map((log, index) => (
            <div key={index} className="log-entry">
              <span className="log-timestamp">{log.timestamp}</span>
              <span className={`log-level ${log.level?.toLowerCase() || 'info'}`}>
                {log.level?.toUpperCase() || 'INFO'}
              </span>
              <span>{log.message}</span>
            </div>
          ))
        ) : (
          <div style={{ color: '#718096', textAlign: 'center', padding: '1rem' }}>
            No logs available
          </div>
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
};

export default LogsPanel;