import React from 'react';
import { ExternalLink, MapPin, TrendingUp, Users, DollarSign } from 'lucide-react';
import type { Company } from '../../types/company';
import { Badge } from '../ui/Badge';
import { formatCurrency, formatNumber, formatConfidenceScore, getConfidenceBadgeClass, getServiceColor } from '../../utils/formatters';
import { motion } from 'framer-motion';

interface CompanyTableProps {
  companies: Company[];
  onCompanyClick: (company: Company) => void;
}

export const CompanyTable: React.FC<CompanyTableProps> = ({
  companies,
  onCompanyClick,
}) => {
  if (companies.length === 0) {
    return (
      <div className="terminal-card text-center py-16">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800/50 mb-4">
          <TrendingUp className="w-8 h-8 text-slate-600" />
        </div>
        <h3 className="text-lg font-semibold text-slate-400 mb-2">No Companies Found</h3>
        <p className="text-sm text-slate-500">Try adjusting your filters to see more results</p>
      </div>
    );
  }

  return (
    <div className="glass rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full table-fixed">
          <thead>
            <tr className="table-header">
              <th className="px-4 py-4 text-left w-[22%]">
                <span className="data-label">Company</span>
              </th>
              <th className="px-4 py-4 text-left w-[12%]">
                <span className="data-label">Location</span>
              </th>
              <th className="px-4 py-4 text-left w-[12%]">
                <span className="data-label">Ownership</span>
              </th>
              <th className="px-4 py-4 text-left w-[18%]">
                <span className="data-label">Services</span>
              </th>
              <th className="px-4 py-4 text-right w-[11%]">
                <span className="data-label">Revenue</span>
              </th>
              <th className="px-4 py-4 text-right w-[11%]">
                <span className="data-label">Employees</span>
              </th>
              <th className="px-4 py-4 text-right w-[8%]">
                <span className="data-label">Confidence</span>
              </th>
              <th className="px-4 py-4 text-center w-[6%]">
                <span className="data-label">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {companies.map((company, index) => (
              <motion.tr
                key={company.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.02 }}
                className="table-row"
                onClick={() => onCompanyClick(company)}
              >
                <td className="px-4 py-3">
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-white text-sm truncate">
                        {company.name}
                      </div>
                      {company.primary_service && (
                        <div className="text-xs text-slate-400 mt-0.5 truncate">
                          {company.primary_service}
                        </div>
                      )}
                    </div>
                    {!!company.is_pe_backed && (
                      <Badge variant="red" className="text-[9px] px-1.5 py-0.5 flex-shrink-0">
                        PE
                      </Badge>
                    )}
                  </div>
                </td>

                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5 text-xs text-slate-300">
                    <MapPin size={12} className="text-slate-500 flex-shrink-0" />
                    <span className="truncate">
                      {company.city && company.state
                        ? `${company.city}, ${company.state}`
                        : company.state || 'N/A'}
                    </span>
                  </div>
                </td>

                <td className="px-4 py-3">
                  <div className="text-xs text-slate-300 truncate">
                    {company.ownership_type ? (
                      <span>{company.ownership_type}</span>
                    ) : (
                      <span className="text-slate-500 italic">Unknown</span>
                    )}
                  </div>
                </td>

                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {company.services.slice(0, 2).map((service, i) => (
                      <Badge
                        key={i}
                        variant={getServiceColor(service).replace('badge-', '') as any}
                        className="text-[9px] px-1.5 py-0.5"
                      >
                        {service.replace(' Tax Credits', '').replace('Work Opportunity', 'WOTC').replace('Cost Segregation', 'Cost Seg')}
                      </Badge>
                    ))}
                    {company.services.length > 2 && (
                      <span className="text-[10px] text-slate-500 px-1">
                        +{company.services.length - 2}
                      </span>
                    )}
                  </div>
                </td>

                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <DollarSign size={12} className="text-emerald-500 flex-shrink-0" />
                    <span className="font-mono text-xs text-slate-200 truncate">
                      {formatCurrency(company.estimated_revenue)}
                    </span>
                  </div>
                </td>

                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Users size={12} className="text-blue-500 flex-shrink-0" />
                    <span className="font-mono text-xs text-slate-200">
                      {formatNumber(company.employee_count)}
                    </span>
                  </div>
                </td>

                <td className="px-4 py-3 text-right">
                  <Badge variant={getConfidenceBadgeClass(company.confidence_score).replace('badge-', '') as any} className="text-[10px]">
                    {formatConfidenceScore(company.confidence_score)}
                  </Badge>
                </td>

                <td className="px-4 py-3 text-center">
                  {company.website && (
                    <a
                      href={company.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center justify-center w-7 h-7 rounded-md glass hover:bg-cyan-500/20 hover:text-cyan-400 text-slate-400 transition-all"
                    >
                      <ExternalLink size={12} />
                    </a>
                  )}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-terminal-border bg-terminal-surface/50">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400 font-mono">
            Showing {companies.length} {companies.length === 1 ? 'company' : 'companies'}
          </span>
          <span className="text-slate-500 text-[11px]">
            Click any row to view details
          </span>
        </div>
      </div>
    </div>
  );
};
