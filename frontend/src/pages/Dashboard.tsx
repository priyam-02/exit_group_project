import React, { useState } from 'react';
import { KPIGrid } from '../components/dashboard/KPIGrid';
import { ServiceChart } from '../components/dashboard/ServiceChart';
import { GeographicChart } from '../components/dashboard/GeographicChart';
import { CompanyFilters } from '../components/companies/CompanyFilters';
import { CompanyTable } from '../components/companies/CompanyTable';
import { CompanyDetail } from '../components/companies/CompanyDetail';
import { LoadingSpinner, LoadingCard } from '../components/ui/LoadingSpinner';
import { useKPIs } from '../hooks/useKPIs';
import { useCompanies, useCompany } from '../hooks/useCompanies';
import type { CompanyFilters as Filters } from '../types/company';
import { AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export const Dashboard: React.FC = () => {
  const [filters, setFilters] = useState<Filters>({
    sort_by: 'confidence_score',
    sort_dir: 'DESC',
  });
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);

  // Fetch data
  const { data: kpisData, isLoading: kpisLoading, error: kpisError } = useKPIs();
  const { data: companiesData, isLoading: companiesLoading, error: companiesError } = useCompanies(filters);
  const { data: selectedCompany } = useCompany(selectedCompanyId!);

  // Extract state options from KPIs
  const stateOptions = kpisData
    ? Object.keys(kpisData.state_distribution).sort()
    : [];

  // Error states
  if (kpisError || companiesError) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="terminal-card max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Error Loading Data</h3>
          <p className="text-sm text-slate-400 mb-4">
            {(kpisError as Error)?.message || (companiesError as Error)?.message || 'Failed to connect to the API'}
          </p>
          <p className="text-xs text-slate-500">
            Make sure the backend server is running on http://localhost:5001
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl font-bold text-white mb-2">
          Acquisition Target <span className="text-gradient-cyan">Intelligence</span>
        </h1>
        <p className="text-slate-400">
          Specialty tax advisory firms matching investment thesis criteria
        </p>
      </motion.div>

      {/* KPI Dashboard */}
      {kpisLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
          {[...Array(6)].map((_, i) => (
            <LoadingCard key={i} />
          ))}
        </div>
      ) : kpisData ? (
        <KPIGrid kpis={kpisData} />
      ) : null}

      {/* Charts */}
      {kpisData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ServiceChart data={kpisData.service_distribution} />
          <GeographicChart data={kpisData.state_distribution} />
        </div>
      )}

      {/* Filters */}
      <CompanyFilters
        filters={filters}
        onFiltersChange={setFilters}
        stateOptions={stateOptions}
      />

      {/* Companies Table */}
      {companiesLoading ? (
        <div className="terminal-card">
          <LoadingSpinner size={32} className="py-12" />
        </div>
      ) : companiesData ? (
        <CompanyTable
          companies={companiesData.companies}
          onCompanyClick={(company) => setSelectedCompanyId(company.id)}
        />
      ) : null}

      {/* Company Detail Modal */}
      {selectedCompany && (
        <CompanyDetail
          company={selectedCompany}
          onClose={() => setSelectedCompanyId(null)}
        />
      )}
    </div>
  );
};
