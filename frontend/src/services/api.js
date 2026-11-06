/**
 * ResearchMind AI – API Service Layer
 * =====================================
 * Centralizes all HTTP calls to the FastAPI backend using Axios.
 *
 * Usage:
 *   import api from '../services/api';
 *   const plan = await api.createResearchPlan({ topic: '...', depth: 'standard' });
 */

import axios from 'axios';

// The base URL is read from the Vite environment variable.
// In development, the Vite proxy handles this (see vite.config.js).
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Create an Axios instance with shared config
const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 minutes (research can take time)
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request Interceptor ───────────────────────────────────────────────────────
// Attach JWT token to every request if present
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor ──────────────────────────────────────────────────────
// Handle common errors globally (401 redirect, etc.)
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid – clear storage and redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ── API Methods ───────────────────────────────────────────────────────────────

const api = {
  // Health check
  health: () => axiosInstance.get('/health'),

  // Research – Phase 2: Planner
  createResearchPlan: (data) => axiosInstance.post('/research/plan', data),

  // Research – Phase 4+: Full workflow (stubs)
  startResearch: (data) => axiosInstance.post('/research', data),
  listResearch: (page = 1, pageSize = 10) =>
    axiosInstance.get('/research', { params: { page, page_size: pageSize } }),
  getResearch: (id) => axiosInstance.get(`/research/${id}`),
  getResearchStatus: (id) => axiosInstance.get(`/research/${id}/status`),
  getResearchPlan: (id) => axiosInstance.get(`/research/${id}/plan`),
  approveResearchPlan: (id) => axiosInstance.post(`/research/${id}/approve-plan`),
  getResearchReport: (id) => axiosInstance.get(`/research/${id}/report`),
  getResearchSources: (id) => axiosInstance.get(`/research/${id}/sources`),
  deleteResearch: (id) => axiosInstance.delete(`/research/${id}`),

  // Documents – Phase 5 (stubs)
  uploadDocument: (formData) =>
    axiosInstance.post('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  listDocuments: () => axiosInstance.get('/documents'),
  deleteDocument: (id) => axiosInstance.delete(`/documents/${id}`),

  // Reports – Phase 6 (stubs)
  listReports: () => axiosInstance.get('/reports'),
  getReport: (id) => axiosInstance.get(`/reports/${id}`),
  exportReport: (id) => axiosInstance.get(`/reports/${id}/export`, { responseType: 'blob' }),

  // Analytics – Phase 8 (stubs)
  getAnalyticsOverview: () => axiosInstance.get('/analytics/overview'),
  getAnalyticsUsage: () => axiosInstance.get('/analytics/usage'),
};

export default api;
