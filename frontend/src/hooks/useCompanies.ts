import { useQuery } from '@tanstack/react-query';
import { companiesApi } from '../services/api';
import type { CompanyFilters } from '../types/company';

export const useCompanies = (filters?: CompanyFilters) => {
  return useQuery({
    queryKey: ['companies', filters],
    queryFn: () => companiesApi.getCompanies(filters),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useCompany = (id: number) => {
  return useQuery({
    queryKey: ['company', id],
    queryFn: () => companiesApi.getCompanyById(id),
    enabled: !!id,
  });
};
