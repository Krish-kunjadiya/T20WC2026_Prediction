import axios from 'axios';

const GENDER_STORAGE_KEY = 't20wc:selectedGender';

export const normalizeGender = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized === 'female' ? 'female' : 'male';
};

const readStoredGender = () => {
  if (typeof window === 'undefined') {
    return 'male';
  }
  return normalizeGender(window.localStorage.getItem(GENDER_STORAGE_KEY));
};

let activeGender = readStoredGender();

export const getActiveGender = () => activeGender;

export const setActiveGender = (gender) => {
  activeGender = normalizeGender(gender);
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(GENDER_STORAGE_KEY, activeGender);
  }
  return activeGender;
};

const api = axios.create({
  baseURL: 'http://localhost:8001',
});

api.interceptors.request.use((config) => {
  const existingParams = config.params || {};
  const requestGender = existingParams.gender || getActiveGender();
  config.params = {
    ...existingParams,
    gender: normalizeGender(requestGender),
  };
  return config;
});

export const executeQuery = async (sql) => {
  const { data } = await api.post('/query', { sql });
  return data.data; // Server returns { data: [...] }
};

export default api;
