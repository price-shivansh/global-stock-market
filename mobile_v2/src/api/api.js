import axios from 'axios';

// Base URL is read from EXPO_PUBLIC_API_BASE_URL in .env at bundle time.
// For real Android device on Wi-Fi: http://<LAPTOP_LAN_IP>:8000
// For Android emulator only:        http://10.0.2.2:8000
// For production Render:            https://my-stock-backend.onrender.com
const baseURL = process.env.EXPO_PUBLIC_API_BASE_URL || 'http://192.168.1.8:8000';

console.log('[API] baseURL resolved to:', baseURL);

const apiClient = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});


apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API request failed:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url,
      baseURL: error.config?.baseURL,
    });
    return Promise.reject(error);
  }
);

export default apiClient;