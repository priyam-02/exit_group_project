import axios from 'axios';
import type { CompaniesResponse, CompanyDetail, CompanyFilters, KPIs } from '../types/company';

// Create axios instance
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API functions
export const companiesApi = {
  // Get all companies with optional filters
  getCompanies: async (filters?: CompanyFilters): Promise<CompaniesResponse> => {
    const params = new URLSearchParams();

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }

    const response = await api.get(`/companies?${params.toString()}`);
    return response.data;
  },

  // Get single company by ID
  getCompanyById: async (id: number): Promise<CompanyDetail> => {
    const response = await api.get(`/companies/${id}`);
    return response.data;
  },

  // Get dashboard KPIs
  getKPIs: async (): Promise<KPIs> => {
    const response = await api.get('/kpis');
    return response.data;
  },

  // Export to CSV
  exportCSV: () => {
    window.open('/api/export/csv', '_blank');
  },

  // Export to JSON
  exportJSON: () => {
    window.open('/api/export/json', '_blank');
  },
};

export default api;
