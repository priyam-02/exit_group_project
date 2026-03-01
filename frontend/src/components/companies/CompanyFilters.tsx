import React, { useState } from 'react';
import { Search, X, Filter } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import type { CompanyFilters as Filters } from '../../types/company';

interface CompanyFiltersProps {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  stateOptions: string[];
}

const SERVICE_OPTIONS = [
  'R&D Tax Credits',
  'Cost Segregation',
  'Work Opportunity Tax Credits',
  'Sales & Use Tax',
];

export const CompanyFilters: React.FC<CompanyFiltersProps> = ({
  filters,
  onFiltersChange,
  stateOptions,
}) => {
  const [searchInput, setSearchInput] = useState(filters.search || '');
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    // Debounce search
    const timeoutId = setTimeout(() => {
      onFiltersChange({ ...filters, search: value });
    }, 300);
    return () => clearTimeout(timeoutId);
  };

  const handleServiceToggle = (service: string) => {
    onFiltersChange({
      ...filters,
      service: filters.service === service ? undefined : service,
    });
  };

  const handleClearFilters = () => {
    setSearchInput('');
    onFiltersChange({
      sort_by: 'confidence_score',
      sort_dir: 'DESC',
    });
  };

  const activeFilterCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== '' && v !== 'confidence_score' && v !== 'DESC'
  ).length;

  return (
    <Card>
      <div className="space-y-4">
        {/* Search and Quick Actions */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="Search companies..."
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="input pl-10"
            />
            {searchInput && (
              <button
                onClick={() => handleSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                <X size={18} />
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-2"
            >
              <Filter size={16} />
              Filters
              {activeFilterCount > 0 && (
                <span className="px-2 py-0.5 bg-cyan-500 text-white text-xs rounded-full">
                  {activeFilterCount}
                </span>
              )}
            </Button>
            {activeFilterCount > 0 && (
              <Button variant="ghost" onClick={handleClearFilters}>
                Clear All
              </Button>
            )}
          </div>
        </div>

        {/* Expanded Filters */}
        {isExpanded && (
          <div className="pt-4 border-t border-terminal-border space-y-6">
            {/* Service Type */}
            <div>
              <label className="data-label mb-3 block">Service Type</label>
              <div className="flex flex-wrap gap-2">
                {SERVICE_OPTIONS.map((service) => (
                  <button
                    key={service}
                    onClick={() => handleServiceToggle(service)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                      filters.service === service
                        ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/30'
                        : 'glass hover:bg-terminal-hover text-slate-300'
                    }`}
                  >
                    {service}
                  </button>
                ))}
              </div>
            </div>

            {/* State and Advanced Filters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="data-label mb-2 block">State</label>
                <select
                  value={filters.state || ''}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      state: e.target.value || undefined,
                    })
                  }
                  className="input"
                >
                  <option value="">All States</option>
                  {stateOptions.slice(0, 15).map((state) => (
                    <option key={state} value={state}>
                      {state}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="data-label mb-2 block">
                  Min Revenue ($M)
                </label>
                <input
                  type="number"
                  placeholder="0"
                  value={filters.min_revenue || ''}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      min_revenue: e.target.value ? Number(e.target.value) * 1_000_000 : undefined,
                    })
                  }
                  className="input"
                />
              </div>

              <div>
                <label className="data-label mb-2 block">
                  Min Employees
                </label>
                <input
                  type="number"
                  placeholder="0"
                  value={filters.min_employees || ''}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      min_employees: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  className="input"
                />
              </div>
            </div>

            {/* Sort Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="data-label mb-2 block">Sort By</label>
                <select
                  value={filters.sort_by || 'confidence_score'}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      sort_by: e.target.value as any,
                    })
                  }
                  className="input"
                >
                  <option value="confidence_score">Confidence Score</option>
                  <option value="name">Name</option>
                  <option value="state">State</option>
                  <option value="estimated_revenue">Revenue</option>
                  <option value="employee_count">Employees</option>
                  <option value="google_rating">Google Rating</option>
                </select>
              </div>

              <div>
                <label className="data-label mb-2 block">Direction</label>
                <select
                  value={filters.sort_dir || 'DESC'}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      sort_dir: e.target.value as 'ASC' | 'DESC',
                    })
                  }
                  className="input"
                >
                  <option value="DESC">Descending</option>
                  <option value="ASC">Ascending</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
