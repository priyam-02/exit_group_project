import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 24,
  className = '',
}) => {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <Loader2 className="animate-spin text-cyan-500" size={size} />
    </div>
  );
};

export const LoadingCard: React.FC = () => {
  return (
    <div className="terminal-card space-y-4">
      <div className="skeleton h-6 w-32" />
      <div className="skeleton h-10 w-full" />
      <div className="skeleton h-4 w-3/4" />
    </div>
  );
};

export const LoadingTable: React.FC = () => {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="skeleton h-16 w-full" />
      ))}
    </div>
  );
};
