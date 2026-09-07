import axios from 'axios';

// Create a centralized Axios instance configured for server-side session cookies
const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // Required for HttpOnly session cookie handling
  headers: {
    'Accept': 'application/json',
  },
});

// Response interceptor to format error messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'An unexpected error occurred';
    if (error.response?.data?.detail) {
      if (typeof error.response.data.detail === 'string') {
        message = error.response.data.detail;
      } else if (Array.isArray(error.response.data.detail)) {
        // FastAPI validation error array
        message = error.response.data.detail.map((d) => d.msg || d.message).join(', ');
      }
    } else if (error.message) {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);

export default api;
