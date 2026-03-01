import React from 'react';
import { Database, Download } from 'lucide-react';
import { Button } from '../ui/Button';
import { companiesApi } from '../../services/api';

export const Header: React.FC = () => {
  return (
    <header className="glass border-b border-terminal-border sticky top-0 z-50 backdrop-blur-xl">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo and Title */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <Database className="w-8 h-8 text-cyan-500" strokeWidth={1.5} />
              <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-cyan-500 rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                M&A Research <span className="text-gradient-cyan">Terminal</span>
              </h1>
              <p className="text-xs text-slate-400 font-mono">
                Specialty Tax Advisory Targets
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              onClick={() => companiesApi.exportCSV()}
              className="flex items-center gap-2"
            >
              <Download size={16} />
              Export CSV
            </Button>
            <div className="flex items-center gap-2 px-4 py-2 glass rounded-md">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-sm text-slate-300 font-mono">LIVE</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
