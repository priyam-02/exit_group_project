// TypeScript interfaces matching backend API responses

export interface Company {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
  website: string | null;
  services: string[];
  primary_service: string | null;
  estimated_revenue: number | null;
  revenue_source: string | null;
  employee_count: number | null;
  employee_count_source: string | null;
  ownership_type: string | null;
  is_pe_backed: boolean;
  key_contact_name: string | null;
  key_contact_title: string | null;
  key_contact_email: string | null;
  key_contact_phone: string | null;
  data_sources: string[];
  source_urls: string[];
  description: string | null;
  year_founded: number | null;
  phone: string | null;
  address: string | null;
  google_place_id: string | null;
  google_rating: number | null;
  google_reviews_count: number | null;
  linkedin_url: string | null;
  confidence_score: number;
  is_excluded: boolean;
  exclusion_reason: string | null;
  needs_review: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompanyDetail extends Company {
  source_details: SourceDetail[];
}

export interface SourceDetail {
  id: number;
  company_id: number;
  source_type: string;
  source_query: string | null;
  source_url: string | null;
  raw_data: string | null;
  scraped_at: string;
}

export interface CompaniesResponse {
  companies: Company[];
  total: number;
}

export interface KPIs {
  total_companies: number;
  excluded_companies: number;
  service_distribution: Record<string, number>;
  state_distribution: Record<string, number>;
  revenue: {
    companies_with_data: number;
    average: number;
    min: number;
    max: number;
    total: number;
  };
  employees: {
    companies_with_data: number;
    average: number;
    min: number;
    max: number;
  };
  ownership_breakdown: Record<string, number>;
  companies_with_ownership: number;
  pe_backed_count: number;
  with_website: number;
  with_contact: number;
  needs_review: number;
  avg_confidence_score: number;
}

export interface CompanyFilters {
  service?: string;
  state?: string;
  min_revenue?: number;
  min_employees?: number;
  include_excluded?: boolean;
  search?: string;
  sort_by?: 'name' | 'state' | 'estimated_revenue' | 'employee_count' | 'confidence_score' | 'primary_service' | 'google_rating';
  sort_dir?: 'ASC' | 'DESC';
}
