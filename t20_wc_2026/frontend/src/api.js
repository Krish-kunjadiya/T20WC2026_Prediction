import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8001',
});

export const executeQuery = async (sql) => {
  const { data } = await api.post('/query', { sql });
  return data.data; // Server returns { data: [...] }
};

export default api;
