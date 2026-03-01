import React from 'react';
import { KPICard } from './KPICard';
import { Building2, DollarSign, Users, MapPin, Award, Shield } from 'lucide-react';
import type { KPIs } from '../../types/company';
import { formatCurrency, formatNumber, formatPercent } from '../../utils/formatters';

interface KPIGridProps {
  kpis: KPIs;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ kpis }) => {
  // Get top service type
  const topService = Object.entries(kpis.service_distribution)
    .sort(([, a], [, b]) => b - a)[0];

  // Count states and get top state
  const stateCount = Object.keys(kpis.state_distribution).length;
  const topState = Object.entries(kpis.state_distribution)
    .sort(([, a], [, b]) => b - a)[0];

  // Calculate ownership identification percentage
  const ownershipPercent = kpis.companies_with_ownership / kpis.total_companies;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 auto-rows-fr">
      <KPICard
        title="Total Companies"
        value={formatNumber(kpis.total_companies)}
        subtitle={`${kpis.excluded_companies} excluded`}
        icon={Building2}
        delay={0}
        glow
      />

      <KPICard
        title="Avg Confidence"
        value={formatPercent(kpis.avg_confidence_score)}
        subtitle="Thesis fit score"
        icon={Award}
        delay={0.1}
      />

      <KPICard
        title="Ownership Identified"
        value={formatPercent(ownershipPercent)}
        subtitle={`${kpis.companies_with_ownership} of ${kpis.total_companies} companies`}
        icon={Shield}
        delay={0.2}
      />

      <KPICard
        title="Avg Revenue"
        value={formatCurrency(kpis.revenue.average)}
        subtitle={`${kpis.revenue.companies_with_data} with data`}
        icon={DollarSign}
        delay={0.3}
      />

      <KPICard
        title="Geographic Coverage"
        value={`${stateCount} states`}
        subtitle={topState ? `${topState[0]} leads with ${topState[1]}` : 'N/A'}
        icon={MapPin}
        delay={0.4}
      />

      <KPICard
        title="Top Service"
        value={topService ? topService[1] : 0}
        subtitle={topService ? topService[0] : 'N/A'}
        icon={Users}
        delay={0.5}
      />
    </div>
  );
};
