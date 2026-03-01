// Utility functions for formatting data

export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'N/A';

  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  } else if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value.toLocaleString()}`;
};

export const formatNumber = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'N/A';
  return value.toLocaleString();
};

export const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(0)}%`;
};

export const formatConfidenceScore = (score: number): string => {
  return `${(score * 100).toFixed(0)}%`;
};

export const getConfidenceColor = (score: number): string => {
  if (score >= 0.8) return 'text-emerald-400';
  if (score >= 0.6) return 'text-amber-400';
  return 'text-red-400';
};

export const getConfidenceBadgeClass = (score: number): string => {
  if (score >= 0.8) return 'badge-green';
  if (score >= 0.6) return 'badge-yellow';
  return 'badge-red';
};

export const formatDate = (dateString: string | null | undefined): string => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

export const formatDateTime = (dateString: string | null | undefined): string => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

export const getServiceColor = (service: string): string => {
  const serviceColors: Record<string, string> = {
    'R&D Tax Credits': 'badge-blue',
    'Cost Segregation': 'badge-green',
    'Work Opportunity Tax Credits': 'badge-purple',
    'WOTC': 'badge-purple',
    'Sales & Use Tax': 'badge-orange',
  };
  return serviceColors[service] || 'badge-blue';
};

export const truncateText = (text: string | null | undefined, maxLength: number): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};
