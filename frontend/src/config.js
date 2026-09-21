// The backend address. Set VITE_API_URL in .env after you deploy the backend.
export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
export const WS_URL = `${API_URL.replace(/^http/, 'ws')}/ws/chat`;
