import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh (future implementation)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      // In a real app, you would try to refresh the token here
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (username: string, password: string) =>
    api.post(
      '/auth/login',
      new URLSearchParams({ username, password }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    ),
  register: (userData: { username: string; email: string; password: string; display_name: string }) =>
    api.post('/auth/register', userData),
};

// User APIs
export const userAPI = {
  getProfile: () => api.get('/users/me'), // We'll add this endpoint
  updateProfile: (data: Partial<{ email: string; display_name: string; avatar_url: string }>) =>
    api.put('/users/me', data),
  search: (params?: { q?: string; limit?: number }) => api.get('/users/search', { params }),
};

// Project APIs
export const projectAPI = {
  getAll: (params?: { skip?: number; limit?: number }) =>
    api.get('/projects', { params }),
  getById: (projectId: number) => api.get(`/projects/${projectId}`),
  create: (data: { project_key: string; name: string; description?: string }) =>
    api.post('/projects', data),
  update: (projectId: number, data: Partial<{ name: string; description: string; is_archived: boolean }>) =>
    api.put(`/projects/${projectId}`, data),
  getIssues: (projectId: number, params?: { skip?: number; limit?: number; assignee_id?: number; status_id?: number; priority_id?: number }) =>
    api.get(`/projects/${projectId}/issues`, { params }),
  getStats: (projectId: number) => api.get(`/projects/${projectId}/stats`),
};

// Issue APIs
export const issueAPI = {
  getAll: (params?: {
    project_key?: string;
    issue_type_name?: string;
    assignee_username?: string;
    status?: string;
    priority?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/issues', { params }),
  getById: (issueId: number) => api.get(`/issues/${issueId}`),
  getByKey: (issueKey: string) => api.get(`/issues/key/${issueKey}`),
  create: (data: {
    project_key: string;
    issue_type: string;
    summary: string;
    description?: string;
    priority?: string;
    assignee_username?: string;
    auto_assign?: boolean;
    epic_issue_key?: string;
    component_name?: string;
    version_name?: string;
    original_estimate?: number;
    remaining_estimate?: number;
    due_date?: string;
    label_names?: string[];
  }) => api.post('/issues', data),
  update: (issueId: number, data: Partial<{
    project_key: string;
    issue_type: string;
    summary: string;
    description: string;
    priority: string | null;
    status: string;
    assignee_username: string | null;
    component_name: string | null;
    version_name: string | null;
    original_estimate: number;
    remaining_estimate: number;
    due_date: string | null;
    label_names: string[];
  }>) => api.put(`/issues/${issueId}`, data),
  delete: (issueId: number) => api.delete(`/issues/${issueId}`),
  addComment: (issueId: number, body: string) => api.post(`/issues/${issueId}/comments`, { body }),
  getComments: (issueId: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/issues/${issueId}/comments`, { params }),
  addWorklog: (issueId: number, data: { time_spent: number; comment?: string; started_at: string }) =>
    api.post(`/issues/${issueId}/worklogs`, data),
  getWorklogs: (issueId: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/issues/${issueId}/worklogs`, { params }),
  linkIssue: (issueId: number, issue_key_to: string, link_type?: string) =>
    api.post(`/issues/${issueId}/link`, { issue_key_to, link_type }),
  updateEpic: (issueId: number, epic_issue_key: string | null) =>
    api.put(`/issues/${issueId}/epic`, { epic_issue_key }),
};

// Board APIs
export const boardAPI = {
  create: (data: { project_key: string; name: string; description?: string; board_type: string }) =>
    api.post('/boards', data),
  getByProject: (projectId: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/boards/project/${projectId}`, { params }),
  getById: (boardId: number) => api.get(`/boards/${boardId}`),
  update: (boardId: number, data: Partial<{ name: string; description: string; is_archived: boolean }>) =>
    api.put(`/boards/${boardId}`, data),
  addColumn: (boardId: number, data: { name: string; column_type: string; mapped_status_name?: string; sort_order: number; is_editable?: boolean }) =>
    api.post(`/boards/${boardId}/columns`, data),
  getColumns: (boardId: number) => api.get(`/boards/${boardId}/columns`),
  getIssues: (boardId: number) => api.get(`/boards/${boardId}/issues`),
};

export const agentAPI = {
  getStatus: () => api.get('/agents/status'),
  runAutomation: (data: { intent?: string; issue_id?: number; board_id?: number }) =>
    api.post('/agents/automation/run', data),
  ask: (message: string) => api.post('/agents/workflow/ask', { message }),
  executePrompt: (prompt: string) => api.post('/agents/prompt/execute', { prompt }),
  reviewRepository: (data: { repository_url: string; branch?: string; github_token?: string; max_files?: number }) =>
    api.post('/agents/repository/review', data),
  approveAction: (actionId: number) => api.post(`/agents/actions/${actionId}/approve`),
  rejectAction: (actionId: number) => api.post(`/agents/actions/${actionId}/reject`),
};

// Default export
export default api;
