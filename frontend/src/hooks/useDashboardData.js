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
      const response = await axios.get('/api/dashboard-data');
      setData(prevData => ({
        ...prevData,
        ...response.data
      }));
      setError(null);
      if (loading) setLoading(false);
    } catch (err) {
      setError(err.message);
      console.error('Dashboard data fetch error:', err);
      if (loading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Reduced frequency to 10s
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refetch: fetchData };
};

export default useDashboardData;