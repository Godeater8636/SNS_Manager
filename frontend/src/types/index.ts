// ── Common ────────────────────────────────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ── User ──────────────────────────────────────────────────────────────────────
export interface PlanInfo {
  name: string;
  display_name: string;
  price_jpy: number;
  max_accounts: number;
  max_posts_month: number | null;
  can_automate: boolean;
  expires_at: string | null;
}

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  timezone: string;
  is_active: boolean;
  plan: PlanInfo | null;
  created_at: string;
}

// ── Social Account ────────────────────────────────────────────────────────────
export interface SocialAccount {
  id: string;
  x_username: string;
  x_display_name: string | null;
  platform: string;
  is_active: boolean;
  last_login_at: string | null;
  session_expires_at: string | null;
  daily_likes_count: number;
  daily_follows_count: number;
  daily_like_limit: number;
  daily_follow_limit: number;
  action_min_interval_sec: number;
  action_max_interval_sec: number;
  active_hours_start: number;
  active_hours_end: number;
  burst_size: number;
  burst_rest_sec: number;
  created_at: string;
}

// ── Post ──────────────────────────────────────────────────────────────────────
export type PostStatus = "draft" | "scheduled" | "posting" | "posted" | "failed" | "cancelled";

export interface Post {
  id: string;
  social_account_id: string;
  parent_post_id: string | null;
  thread_order: number;
  content: string;
  media_urls: string[] | null;
  scheduled_at: string | null;
  posted_at: string | null;
  status: PostStatus;
  x_tweet_id: string | null;
  retry_count: number;
  is_template: boolean;
  created_at: string;
  updated_at: string;
}

// ── Affiliate Link ────────────────────────────────────────────────────────────
export interface AffiliateLink {
  id: string;
  name: string;
  destination_url: string;
  short_url: string;
  slug: string;
  tags: string[];
  description: string | null;
  total_clicks: number;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LinkStats {
  total_clicks: number;
  clicks_today: number;
  clicks_this_week: number;
  clicks_this_month: number;
  daily_series: { date: string; clicks: number }[];
}

// ── Task ──────────────────────────────────────────────────────────────────────
export type TaskType = "auto_like" | "auto_follow" | "auto_unfollow";

export interface Task {
  id: string;
  social_account_id: string;
  task_type: TaskType;
  search_keyword: string | null;
  target_username: string | null;
  is_enabled: boolean;
  cron_expression: string;
  total_executed: number;
  total_success: number;
  total_failed: number;
  last_executed_at: string | null;
  next_execute_at: string | null;
  created_at: string;
}

export interface TaskLog {
  id: string;
  task_id: string;
  executed_at: string;
  target_tweet_id: string | null;
  target_x_user_id: string | null;
  action: string;
  error_message: string | null;
  response_time_ms: number | null;
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export interface DashboardSummary {
  total_impressions: number;
  total_likes: number;
  total_retweets: number;
  total_link_clicks: number;
  avg_engagement_rate: number;
}

export interface DashboardData {
  summary: DashboardSummary;
  top_posts: { post_id: string; content: string; impressions: number; engagement_rate: number }[];
  top_links: { link_id: string; name: string; clicks: number }[];
  daily_series: { date: string; impressions: number; link_clicks: number; likes: number; retweets: number }[];
}

// ── Payment ───────────────────────────────────────────────────────────────────
export interface Plan {
  id: number;
  name: string;
  display_name: string;
  price_jpy: number;
  max_accounts: number;
  max_posts_month: number | null;
  can_automate: boolean;
}
