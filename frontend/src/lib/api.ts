import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  withCredentials: true, // send refresh_token cookie
  headers: { "Content-Type": "application/json" },
});

// ── Token storage ─────────────────────────────────────────────────────────────
let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

export const getAccessToken = () => accessToken;

// ── Request interceptor: attach access token ──────────────────────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// ── Response interceptor: auto-refresh on 401 ────────────────────────────────
let isRefreshing = false;
let failedQueue: { resolve: (v: string) => void; reject: (e: unknown) => void }[] = [];

const processQueue = (error: unknown, token: string | null) => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)));
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (res: AxiosResponse) => res,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await apiClient.post<{ success: boolean; data: { access_token: string } }>(
          "/auth/refresh"
        );
        const newToken = data.data.access_token;
        setAccessToken(newToken);
        processQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        setAccessToken(null);
        if (typeof window !== "undefined") window.location.href = "/auth/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// ── Typed helpers ─────────────────────────────────────────────────────────────
export const api = {
  // Auth
  register: (email: string, password: string, display_name?: string) =>
    apiClient.post("/auth/register", { email, password, display_name }),
  login: (email: string, password: string, totp_code?: string) =>
    apiClient.post("/auth/login", { email, password, totp_code }),
  logout: () => apiClient.post("/auth/logout"),

  // Users
  getMe: () => apiClient.get("/users/me"),
  updateMe: (data: { display_name?: string; timezone?: string }) => apiClient.patch("/users/me", data),

  // Social accounts
  listAccounts: () => apiClient.get("/social-accounts"),
  createAccount: (data: object) => apiClient.post("/social-accounts", data),
  updateAccount: (id: string, data: object) => apiClient.patch(`/social-accounts/${id}`, data),
  deleteAccount: (id: string) => apiClient.delete(`/social-accounts/${id}`),
  refreshSession: (id: string) => apiClient.post(`/social-accounts/${id}/refresh-session`),

  // Posts
  listPosts: (params?: object) => apiClient.get("/posts", { params }),
  createPost: (data: object) => apiClient.post("/posts", data),
  getPost: (id: string) => apiClient.get(`/posts/${id}`),
  updatePost: (id: string, data: object) => apiClient.patch(`/posts/${id}`, data),
  deletePost: (id: string) => apiClient.delete(`/posts/${id}`),
  exportPostsCsv: (params?: object) =>
    apiClient.get("/posts/export-csv", { params, responseType: "blob" }),
  importPostsCsv: (socialAccountId: string, file: File) => {
    const form = new FormData();
    form.append("social_account_id", socialAccountId);
    form.append("file", file);
    return apiClient.post("/posts/import-csv", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  // Affiliate links
  listLinks: (params?: object) => apiClient.get("/affiliate-links", { params }),
  createLink: (data: object) => apiClient.post("/affiliate-links", data),
  getLink: (id: string) => apiClient.get(`/affiliate-links/${id}`),
  updateLink: (id: string, data: object) => apiClient.patch(`/affiliate-links/${id}`, data),
  deleteLink: (id: string) => apiClient.delete(`/affiliate-links/${id}`),

  // Tasks
  listTasks: () => apiClient.get("/tasks"),
  createTask: (data: object) => apiClient.post("/tasks", data),
  updateTask: (id: string, data: object) => apiClient.patch(`/tasks/${id}`, data),
  deleteTask: (id: string) => apiClient.delete(`/tasks/${id}`),
  getTaskLogs: (taskId: string, params?: object) => apiClient.get(`/tasks/${taskId}/logs`, { params }),
  exportTaskLogsCsv: (params?: object) =>
    apiClient.get("/tasks/logs/export-csv", { params, responseType: "blob" }),

  // Analytics
  getDashboard: (params?: object) => apiClient.get("/analytics/dashboard", { params }),

  // Payments
  listPlans: () => apiClient.get("/payments/plans"),
  subscribe: (plan_name: string, payment_method_id: string) =>
    apiClient.post("/payments/subscribe", { plan_name, payment_method_id }),
  changePlan: (new_plan_name: string) => apiClient.post("/payments/change-plan", { new_plan_name }),
  cancelSubscription: () => apiClient.post("/payments/cancel"),
  paymentHistory: () => apiClient.get("/payments/history"),
};
