import React, { useState, useEffect } from 'react';
import axios from 'axios';

const NotificationSystem = () => {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    const checkForIssues = async () => {
      try {
        const response = await axios.get('/api/system/health');
        const issues = response.data.issues || [];
        
        if (issues.length > 0) {
          setNotifications(issues.map(issue => ({
            id: Date.now() + Math.random(),
            type: issue.severity || 'warning',
            message: issue.message,
            timestamp: new Date().toLocaleTimeString()
          })));
        } else {
          setNotifications([]);
        }
      } catch (error) {
        setNotifications([{
          id: Date.now(),
          type: 'error',
          message: 'System health check failed',
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    };

    checkForIssues();
    const interval = setInterval(checkForIssues, 30000);
    return () => clearInterval(interval);
  }, []);

  const dismissNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  if (notifications.length === 0) return null;

  return (
    <div className="notification-container">
      {notifications.map(notification => (
        <div key={notification.id} className={`notification ${notification.type}`}>
          <span className="notification-message">{notification.message}</span>
          <span className="notification-time">{notification.timestamp}</span>
          <button onClick={() => dismissNotification(notification.id)}>×</button>
        </div>
      ))}
    </div>
  );
};

export default NotificationSystem;