import React from 'react';
import {
  X,
  ExternalLink,
  MapPin,
  Phone,
  Mail,
  Users,
  DollarSign,
  Calendar,
  Star,
  Building2,
  Linkedin,
  Database,
  AlertTriangle,
} from 'lucide-react';
import type { CompanyDetail as CompanyDetailType } from '../../types/company';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import {
  formatCurrency,
  formatNumber,
  formatConfidenceScore,
  formatDateTime,
  getConfidenceBadgeClass,
  getServiceColor,
} from '../../utils/formatters';
import { motion, AnimatePresence } from 'framer-motion';

interface CompanyDetailProps {
  company: CompanyDetailType;
  onClose: () => void;
}

export const CompanyDetail: React.FC<CompanyDetailProps> = ({
  company,
  onClose,
}) => {
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', duration: 0.5 }}
          className="glass rounded-lg max-w-5xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 glass-hover border-b border-terminal-border p-6 flex items-start justify-between z-10">
            <div className="flex-1">
              <div className="flex items-start gap-3 mb-3">
                <div className="p-3 glass rounded-lg">
                  <Building2 className="w-6 h-6 text-cyan-500" />
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-white mb-2">{company.name}</h2>
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge variant={getConfidenceBadgeClass(company.confidence_score).replace('badge-', '') as any}>
                      {formatConfidenceScore(company.confidence_score)} Confidence
                    </Badge>
                    {company.is_pe_backed && (
                      <Badge variant="red">PE-Backed</Badge>
                    )}
                    {company.needs_review && (
                      <Badge variant="yellow">Needs Review</Badge>
                    )}
                    {company.is_excluded && (
                      <Badge variant="red">Excluded</Badge>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 glass-hover rounded-lg text-slate-400 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <div className="flex items-center gap-3">
                  <DollarSign className="w-5 h-5 text-emerald-500" />
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Revenue</p>
                    <p className="font-mono font-semibold text-white">
                      {formatCurrency(company.estimated_revenue)}
                    </p>
                  </div>
                </div>
              </Card>

              <Card>
                <div className="flex items-center gap-3">
                  <Users className="w-5 h-5 text-blue-500" />
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Employees</p>
                    <p className="font-mono font-semibold text-white">
                      {formatNumber(company.employee_count)}
                    </p>
                  </div>
                </div>
              </Card>

              <Card>
                <div className="flex items-center gap-3">
                  <Star className="w-5 h-5 text-amber-500" />
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Google Rating</p>
                    <p className="font-mono font-semibold text-white">
                      {company.google_rating ? `${company.google_rating} ⭐` : 'N/A'}
                    </p>
                  </div>
                </div>
              </Card>

              <Card>
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-purple-500" />
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Founded</p>
                    <p className="font-mono font-semibold text-white">
                      {company.year_founded || 'N/A'}
                    </p>
                  </div>
                </div>
              </Card>
            </div>

            {/* Services */}
            {company.services.length > 0 && (
              <Card>
                <h3 className="text-sm font-semibold text-white mb-3">Services Offered</h3>
                <div className="flex flex-wrap gap-2">
                  {company.services.map((service, i) => (
                    <Badge
                      key={i}
                      variant={getServiceColor(service).replace('badge-', '') as any}
                    >
                      {service}
                    </Badge>
                  ))}
                </div>
              </Card>
            )}

            {/* Contact & Location */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <h3 className="text-sm font-semibold text-white mb-4">Contact Information</h3>
                <div className="space-y-3">
                  {company.key_contact_name && (
                    <div className="flex items-start gap-3">
                      <Users className="w-4 h-4 text-slate-500 mt-0.5" />
                      <div>
                        <p className="text-sm text-white font-medium">{company.key_contact_name}</p>
                        {company.key_contact_title && (
                          <p className="text-xs text-slate-400">{company.key_contact_title}</p>
                        )}
                      </div>
                    </div>
                  )}
                  {company.key_contact_email && (
                    <div className="flex items-center gap-3">
                      <Mail className="w-4 h-4 text-slate-500" />
                      <a
                        href={`mailto:${company.key_contact_email}`}
                        className="text-sm text-cyan-400 hover:text-cyan-300"
                      >
                        {company.key_contact_email}
                      </a>
                    </div>
                  )}
                  {(company.phone || company.key_contact_phone) && (
                    <div className="flex items-center gap-3">
                      <Phone className="w-4 h-4 text-slate-500" />
                      <p className="text-sm text-slate-300 font-mono">
                        {company.key_contact_phone || company.phone}
                      </p>
                    </div>
                  )}
                  {company.website && (
                    <div className="flex items-center gap-3">
                      <ExternalLink className="w-4 h-4 text-slate-500" />
                      <a
                        href={company.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-cyan-400 hover:text-cyan-300 truncate"
                      >
                        {company.website}
                      </a>
                    </div>
                  )}
                  {company.linkedin_url && (
                    <div className="flex items-center gap-3">
                      <Linkedin className="w-4 h-4 text-slate-500" />
                      <a
                        href={company.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-cyan-400 hover:text-cyan-300"
                      >
                        LinkedIn Profile
                      </a>
                    </div>
                  )}
                </div>
              </Card>

              <Card>
                <h3 className="text-sm font-semibold text-white mb-4">Location</h3>
                <div className="space-y-3">
                  {company.address && (
                    <div className="flex items-start gap-3">
                      <MapPin className="w-4 h-4 text-slate-500 mt-0.5" />
                      <p className="text-sm text-slate-300">{company.address}</p>
                    </div>
                  )}
                  {(company.city || company.state) && (
                    <div className="flex items-center gap-3">
                      <MapPin className="w-4 h-4 text-slate-500" />
                      <p className="text-sm text-slate-300">
                        {company.city && company.state
                          ? `${company.city}, ${company.state}`
                          : company.state || company.city}
                      </p>
                    </div>
                  )}
                  {company.ownership_type && (
                    <div className="flex items-center gap-3">
                      <Building2 className="w-4 h-4 text-slate-500" />
                      <p className="text-sm text-slate-300 capitalize">{company.ownership_type}</p>
                    </div>
                  )}
                </div>
              </Card>
            </div>

            {/* Description */}
            {company.description && (
              <Card>
                <h3 className="text-sm font-semibold text-white mb-3">Description</h3>
                <p className="text-sm text-slate-300 leading-relaxed">{company.description}</p>
              </Card>
            )}

            {/* Exclusion/Review Warnings */}
            {(company.is_excluded || company.needs_review || company.exclusion_reason) && (
              <Card className="border-amber-500/30 bg-amber-500/5">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-semibold text-amber-400 mb-2">
                      {company.is_excluded ? 'Excluded from Thesis' : 'Flagged for Review'}
                    </h3>
                    {company.exclusion_reason && (
                      <p className="text-sm text-slate-300">{company.exclusion_reason}</p>
                    )}
                  </div>
                </div>
              </Card>
            )}

            {/* Data Provenance */}
            <Card>
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-500" />
                Data Sources
              </h3>
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {company.data_sources.map((source, i) => (
                    <Badge key={i} variant="blue">
                      {source}
                    </Badge>
                  ))}
                </div>
                {company.source_details && company.source_details.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {company.source_details.map((source) => (
                      <div
                        key={source.id}
                        className="p-3 glass rounded-md text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-cyan-400 font-semibold">{source.source_type}</span>
                          <span className="text-slate-500">{formatDateTime(source.scraped_at)}</span>
                        </div>
                        {source.source_query && (
                          <p className="text-slate-400">Query: {source.source_query}</p>
                        )}
                        {source.source_url && (
                          <a
                            href={source.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1"
                          >
                            View Source <ExternalLink size={10} />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>

            {/* Footer Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-terminal-border">
              <div className="text-xs text-slate-500 font-mono">
                Last updated: {formatDateTime(company.updated_at)}
              </div>
              <div className="flex gap-3">
                {company.website && (
                  <Button
                    variant="secondary"
                    onClick={() => window.open(company.website!, '_blank')}
                  >
                    <ExternalLink size={16} className="mr-2" />
                    Visit Website
                  </Button>
                )}
                <Button variant="primary" onClick={onClose}>
                  Close
                </Button>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
