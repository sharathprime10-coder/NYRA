import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000', // FastAPI default port
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor to add the auth token to requests
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

import toast from 'react-hot-toast';

// Interceptor to handle global API errors
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            const status = error.response.status;
            if (status === 401) {
                // Clear token and force reload to login
                localStorage.removeItem('token');
                window.location.href = '/';
            } else if (status >= 500) {
                toast.error("An unexpected server error occurred. Please try again later.");
            }
        } else if (error.request) {
            // Network error (no response received)
            toast.error("Network error. Please check your connection.");
        }
        return Promise.reject(error);
    }
);

export default api;
