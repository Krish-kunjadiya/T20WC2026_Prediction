import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const simulatorAPI = {
  predictMatch: (payload) => api.post('/simulator/predict', payload),
  liveState: (payload) => api.post('/simulator/live', payload),
  tossDecision: (payload) => api.post('/simulator/toss-decision', payload),
  targetScore: (payload) => api.post('/simulator/target-score', payload),
  getFormOptions: () => api.get('/simulator/form-options'),
};
export const playerAPI = {
  list: (params) => api.get('/players', { params }),
};
export const strategyAPI = {
  chat: (payload) => api.post('/strategy/chat', payload),
};

export default api;

