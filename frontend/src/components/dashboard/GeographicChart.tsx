import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Card } from '../ui/Card';
import { motion } from 'framer-motion';

interface GeographicChartProps {
  data: Record<string, number>;
}

export const GeographicChart: React.FC<GeographicChartProps> = ({ data }) => {
  // Get top 10 states
  const chartData = Object.entries(data)
    .map(([state, count]) => ({ state, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.7 }}
    >
      <Card className="h-full">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-1">Geographic Distribution</h3>
          <p className="text-sm text-slate-400">Top 10 states by company count</p>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255, 255, 255, 0.05)"
              vertical={false}
            />
            <XAxis
              dataKey="state"
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
            <Bar
              dataKey="count"
              fill="#06b6d4"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-6 grid grid-cols-5 gap-2">
          {chartData.map((item) => (
            <div
              key={item.state}
              className="px-3 py-2 glass rounded text-center"
            >
              <div className="text-xs text-slate-400 mb-1">{item.state}</div>
              <div className="font-mono font-semibold text-cyan-400">{item.count}</div>
            </div>
          ))}
        </div>
      </Card>
    </motion.div>
  );
};
