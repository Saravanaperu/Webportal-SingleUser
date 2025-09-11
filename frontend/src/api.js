import axios from 'axios';
import io from 'socket.io-client';

const API_URL = '/api';

export const getAccount = () => axios.get(`${API_URL}/account`);
export const getPositions = () => axios.get(`${API_URL}/positions`);
export const getTrades = () => axios.get(`${API_URL}/trades`);
export const getStats = () => axios.get(`${API_URL}/stats`);
export const getStrategyParams = () => axios.get(`${API_URL}/strategy/parameters`);

export const controlStrategy = (action) => axios.post(`${API_URL}/strategy/control`, { action });
export const setStrategyParams = (params) => axios.post(`${API_URL}/strategy/parameters`, params);

export const connectWebSocket = (onData) => {
  const socket = io({
    path: '/api/ws/data',
  });

  socket.on('connect', () => {
    console.log('WebSocket connected');
  });

  socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
  });

  socket.on('message', (data) => {
    onData(data);
  });

  return socket;
};
