import { useQuery } from '@tanstack/react-query';
import { companiesApi } from '../services/api';

export const useKPIs = () => {
  return useQuery({
    queryKey: ['kpis'],
    queryFn: () => companiesApi.getKPIs(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 1000 * 60 * 5, // Refetch every 5 minutes
  });
};
