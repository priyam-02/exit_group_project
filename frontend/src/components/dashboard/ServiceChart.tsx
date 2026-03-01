import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Card } from '../ui/Card';
import { motion } from 'framer-motion';

interface ServiceChartProps {
  data: Record<string, number>;
}

const SERVICE_COLORS: Record<string, string> = {
  'R&D Tax Credits': '#3b82f6',
  'Cost Segregation': '#10b981',
  'Work Opportunity Tax Credits': '#a855f7',
  'WOTC': '#a855f7',
  'Sales & Use Tax': '#f59e0b',
};

export const ServiceChart: React.FC<ServiceChartProps> = ({ data }) => {
  const chartData = Object.entries(data)
    .map(([name, value]) => ({
      name: name.replace(' Tax Credits', '').replace('Work Opportunity', 'WOTC'),
      value,
      fullName: name,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.6 }}
    >
      <Card className="h-full">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-1">Service Distribution</h3>
          <p className="text-sm text-slate-400">Companies by service type</p>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255, 255, 255, 0.05)"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'Archivo' }}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'IBM Plex Mono' }}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(30, 36, 51, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '12px',
                backdropFilter: 'blur(10px)',
              }}
              labelStyle={{ color: '#fff', fontWeight: 600, marginBottom: '4px' }}
              itemStyle={{ color: '#cbd5e1', fontFamily: 'IBM Plex Mono', fontSize: '12px' }}
              cursor={{ fill: 'rgba(6, 182, 212, 0.1)' }}
            />
            <Bar dataKey="value" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={SERVICE_COLORS[entry.fullName] || '#06b6d4'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-6 flex flex-wrap gap-3">
          {chartData.map((item) => (
            <div key={item.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded"
                style={{ backgroundColor: SERVICE_COLORS[item.fullName] || '#06b6d4' }}
              />
              <span className="text-xs text-slate-400 font-mono">
                {item.name}: {item.value}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </motion.div>
  );
};
