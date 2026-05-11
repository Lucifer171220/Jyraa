export type IssueType = 'Epic' | 'Story' | 'Task' | 'Bug' | 'Subtask';
export type Priority = 'Highest' | 'High' | 'Medium' | 'Low' | 'Lowest';
export type Status = 'To Do' | 'In Progress' | 'In Review' | 'Done' | 'Cancelled';
export type BoardType = 'kanban' | 'scrum';

export interface User {
  user_id: number;
  username: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
  avatar_url?: string;
}

export interface Project {
  project_id: number;
  project_key: string;
  name: string;
  description?: string;
  lead_user_id?: number;
  project_type: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Issue {
  issue_id: number;
  issue_key: string;
  project_id?: number;
  project_key?: string;
  project_name?: string;
  issue_type: IssueType;
  summary: string;
  description?: string;
  priority?: Priority;
  priority_color?: string;
  status: Status;
  assignee_user_id?: number;
  assignee_name?: string;
  assignee_username?: string;
  assignee_avatar?: string;
  reporter_username: string;
  reporter_display_name: string;
  component_id?: number;
  component_name?: string;
  component_description?: string;
  version_id?: number;
  version_name?: string;
  version_released?: boolean;
  original_estimate?: number;
  remaining_estimate?: number;
  time_spent: number;
  due_date?: string;
  label_names?: string[];
  epic_issue_id?: number;
  epic_issue_key?: string;
  epic_issue_summary?: string;
  resolution?: string;
  created_at: string;
  updated_at: string;
  recommendation?: Record<string, unknown>;
}

export interface Board {
  board_id: number;
  project_id: number;
  project_key?: string;
  name: string;
  description?: string;
  board_type: BoardType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BoardColumn {
  column_id: number;
  board_id: number;
  name: string;
  column_type: string;
  status_name?: string;
  status_color?: string;
  mapped_status_id?: number;
  sort_order: number;
  is_editable: boolean;
}

export interface BoardWithColumns extends Board {
  columns: BoardColumn[];
}

export interface Sprint {
  sprint_id: number;
  board_id: number;
  name: string;
  goal?: string;
  start_date: string;
  end_date: string;
  sprint_status: 'future' | 'active' | 'closed';
  is_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface Comment {
  comment_id: number;
  issue_id: number;
  user_id: number;
  body: string;
  username: string;
  display_name: string;
  created_at: string;
  updated_at?: string;
}

export interface Worklog {
  worklog_id: number;
  issue_id: number;
  user_id: number;
  time_spent: number;
  time_spent_seconds: number;
  comment?: string;
  started_at: string;
  username?: string;
  display_name?: string;
  created_at: string;
  updated_at?: string;
}

export interface Label {
  label_id: number;
  name: string;
  color_hex?: string;
}
