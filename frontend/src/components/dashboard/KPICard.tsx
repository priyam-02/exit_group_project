import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Card } from '../ui/Card';
import { motion } from 'framer-motion';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  delay?: number;
  glow?: boolean;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  delay = 0,
  glow = false,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="h-full"
    >
      <Card className={`group hover:scale-[1.02] ${glow ? 'glow-cyan' : ''} h-full flex flex-col`} hover>
        <div className="flex items-start justify-between flex-1">
          <div className="flex-1 min-w-0">
            <p className="data-label mb-2">{title}</p>
            <p className="data-value text-white mb-1">{value}</p>
            <div className="h-5">
              {subtitle && (
                <p className="text-sm text-slate-400 font-mono truncate">{subtitle}</p>
              )}
            </div>
          </div>
          <div className="p-3 glass rounded-lg group-hover:bg-cyan-500/10 transition-colors flex-shrink-0">
            <Icon className="w-6 h-6 text-cyan-500" strokeWidth={1.5} />
          </div>
        </div>

        {trend && (
          <div className="mt-4 pt-4 border-t border-terminal-border">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold ${trend.direction === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
              </span>
              <span className="text-xs text-slate-500">vs. last week</span>
            </div>
          </div>
        )}
      </Card>
    </motion.div>
  );
};
