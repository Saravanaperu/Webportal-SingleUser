import { useState, useEffect } from 'react';
import axios from 'axios';

const useDashboardData = () => {
  const [data, setData] = useState({
    account: null,
    positions: [],
    indices: {},
    stats: null
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/dashboard-data');
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Dashboard data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Fallback polling every 5s
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refetch: fetchData };
};

export default useDashboardData;