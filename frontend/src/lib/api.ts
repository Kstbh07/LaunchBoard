const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

export interface Job {
  id: string;
  title: string;
  company: string;
  description: string;
  location: string | null;
  employment_type: string | null;
  experience_level: string | null;
  application_url: string;
  source_name: string;
  source_url: string | null;
  posted_at: string | null;
  collected_at: string;
  last_verified_at: string;
  status: string;
  role_category: string | null;
  skills: string[];
  is_remote: boolean;
  city: string | null;
  classification_confidence: number | null;
  classification_status: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Stats {
  total_active_jobs: number;
  total_unique_jobs: number;
  total_companies: number;
  total_cities: number;
  total_remote_jobs: number;
  total_internships?: number;
  total_fresher_jobs?: number;
  jobs_by_role: Record<string, number>;
  jobs_by_city: Record<string, number>;
  jobs_by_employment_type: Record<string, number>;
  jobs_by_experience_level: Record<string, number>;
  last_successful_refresh: string | null;
  total_sources: number;
}

export interface RoleCount {
  role_category: string;
  count: number;
}

export interface CityCount {
  city: string;
  count: number;
}

export interface SearchParams {
  q?: string;
  role_category?: string;
  city?: string;
  employment_type?: string;
  experience_level?: string;
  is_remote?: boolean;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}

export interface CostReport {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_requests: number;
  total_cost_usd: number;
  avg_cost_per_job: number;
  cost_per_1000_jobs: number;
  model_name: string;
  pricing_config: Record<string, unknown>;
  last_updated?: string | null;
  note: string;
}

export interface SourceStat {
  id: string;
  source_name: string;
  is_enabled: boolean;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error_message: string | null;
  total_jobs_collected: number;
  total_runs: number;
  total_failures: number;
  consecutive_failures: number;
  config: Record<string, unknown>;
}

export interface CollectionRunItem {
  id: string;
  run_id?: string;
  status: string;
  trigger_type?: string;
  started_at: string;
  completed_at: string | null;
  total_fetched: number;
  total_new: number;
  total_updated: number;
  total_duplicates: number;
  total_classified: number;
  total_failed: number;
  total_errors?: number;
  error_details?: unknown[];
  source_results?: Record<string, unknown>;
  duration_seconds: number | null;
}

export interface RestrictedSource {
  name: string;
  type: string;
  status: string;
  reason: string;
  recommendation: string;
}

export interface SchedulerStatus {
  interval_seconds: number;
  interval_minutes: number;
  is_running: boolean;
  last_run_started_at: string | null;
  last_run_completed_at: string | null;
  next_run_at: string | null;
  total_scheduled_runs: number;
}

export interface AdminDashboardData {
  total_jobs_collected: number;
  unique_jobs: number;
  duplicate_jobs_detected: number;
  jobs_classified: number;
  failed_classifications: number;
  source_stats: SourceStat[];
  restricted_sources?: RestrictedSource[];
  scheduler_status?: SchedulerStatus | null;
  cost_report: CostReport;
  last_collection_run: CollectionRunItem | null;
  collection_history: CollectionRunItem[];
}

export interface RefreshResponse {
  run_id: string;
  status: string;
  message: string;
}

async function fetchAPI<T>(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>,
  init?: RequestInit
): Promise<T> {
  const url = new URL(`${API_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '' && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const res = await fetch(url.toString(), {
    next: { revalidate: 60 },
    ...init,
  });

  if (!res.ok) {
    let errorDetail = `${res.status} ${res.statusText}`;
    try {
      const errorJson = (await res.json()) as { message?: string; detail?: string };
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      } else if (errorJson.message) {
        errorDetail = errorJson.message;
      }
    } catch {
      // Use status text if body isn't JSON
    }
    throw new Error(`API error: ${errorDetail}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  getJobs: (params?: SearchParams) =>
    fetchAPI<JobListResponse>('/api/jobs', params as Record<string, string | number | boolean | undefined>),
  getJob: (id: string) => fetchAPI<Job>(`/api/jobs/${id}`),
  getRoles: () => fetchAPI<RoleCount[]>('/api/roles'),
  getCities: () => fetchAPI<CityCount[]>('/api/cities'),
  getStats: () => fetchAPI<Stats>('/api/stats'),
  
  // Admin methods
  getAdminDashboard: (apiKey: string) =>
    fetchAPI<AdminDashboardData>('/api/admin/dashboard', undefined, {
      headers: {
        'X-Admin-API-Key': apiKey,
      },
      cache: 'no-store',
    }),

  triggerRefresh: (apiKey: string, sources?: string[]) =>
    fetchAPI<RefreshResponse>(
      '/api/admin/refresh',
      undefined,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-API-Key': apiKey,
        },
        body: JSON.stringify({ sources: sources ?? null }),
        cache: 'no-store',
      }
    ),

  
  exportEvaluationCsv: async (apiKey: string): Promise<void> => {
    const response = await fetch(
      `${API_URL}/api/admin/evaluation/export`,
      {
        method: 'GET',
        headers: {
          'X-Admin-API-Key': apiKey,
        },
        cache: 'no-store',
      }
    );

    if (!response.ok) {
      throw new Error(`CSV export failed: ${response.status}`);
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'job_evaluation_export.csv';

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(downloadUrl);
  },
};
