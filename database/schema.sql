-- ============================================
-- Jira Clone Database Schema for SQL Server
-- ============================================

-- Enable ANSI NULLs and QUOTED IDENTIFIER
SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
GO

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    username NVARCHAR(100) UNIQUE NOT NULL,
    email NVARCHAR(255) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    display_name NVARCHAR(200) NOT NULL,
    avatar_url NVARCHAR(500) NULL,
    is_active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
GO

-- ============================================
-- PROJECTS TABLE
-- ============================================
CREATE TABLE projects (
    project_id INT PRIMARY KEY IDENTITY(1,1),
    project_key NVARCHAR(20) UNIQUE NOT NULL,
    name NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    lead_user_id INT NULL,
    project_type NVARCHAR(50) DEFAULT 'software',
    is_archived BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_projects_lead_user FOREIGN KEY (lead_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);
GO

CREATE INDEX idx_projects_key ON projects(project_key);
GO

-- ============================================
-- ISSUE TYPES TABLE
-- ============================================
CREATE TABLE issue_types (
    issue_type_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(50) UNIQUE NOT NULL,
    description NVARCHAR(200) NULL,
    icon_name NVARCHAR(50) NULL,
    is_subtask_enabled BIT DEFAULT 0
);
GO

INSERT INTO issue_types (name, description, icon_name, is_subtask_enabled) VALUES
('Epic', 'Large body of work that can be broken down into smaller stories', 'epic', 1),
('Story', 'User story representing a feature from user perspective', 'story', 0),
('Task', 'A specific piece of work to be done', 'task', 0),
('Bug', 'An error or defect in the software', 'bug', 0),
('Subtask', 'A smaller piece of a larger issue', 'subtask', 0);
GO

-- ============================================
-- ISSUE PRIORITIES TABLE
-- ============================================
CREATE TABLE issue_priorities (
    priority_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(50) UNIQUE NOT NULL,
    description NVARCHAR(200) NULL,
    color_hex NVARCHAR(7) NULL,
    sort_order INT DEFAULT 0
);
GO

INSERT INTO issue_priorities (name, description, color_hex, sort_order) VALUES
('Highest', 'Must be fixed immediately', '#FF0000', 1),
('High', 'Important but not urgent', '#FF5733', 2),
('Medium', 'Normal priority', '#FFC300', 3),
('Low', 'Can be delayed', '#28B463', 4),
('Lowest', 'Can be done if time permits', '#3498DB', 5);
GO

-- ============================================
-- ISSUE STATUSES TABLE
-- ============================================
CREATE TABLE issue_statuses (
    status_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(50) UNIQUE NOT NULL,
    description NVARCHAR(200) NULL,
    color_hex NVARCHAR(7) NULL,
    sort_order INT DEFAULT 0,
    is_final_status BIT DEFAULT 0
);
GO

INSERT INTO issue_statuses (name, description, color_hex, sort_order, is_final_status) VALUES
('To Do', 'Issue is ready to be worked on', '#6BA4FF', 1, 0),
('In Progress', 'Work has started on this issue', '#0065FF', 2, 0),
('In Review', 'Work is complete and awaiting review', '#FF851B', 3, 0),
('Done', 'Issue is completed', '#28B463', 4, 1),
('Cancelled', 'Issue has been cancelled', '#7F8C8D', 5, 1);
GO

-- ============================================
-- RESOLUTIONS TABLE
-- ============================================
CREATE TABLE resolutions (
    resolution_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(50) UNIQUE NOT NULL,
    description NVARCHAR(200) NULL
);
GO

INSERT INTO resolutions (name, description) VALUES
('Fixed', 'The issue has been resolved'),
('Won''t Fix', 'The issue will not be fixed'),
('Duplicate', 'The issue is a duplicate of another'),
('Incomplete', 'Incomplete information provided'),
('Cannot Reproduce', 'The issue cannot be reproduced');
GO

-- ============================================
-- COMPONENTS TABLE
-- ============================================
CREATE TABLE components (
    component_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    name NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    lead_user_id INT NULL,
    is_archived BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_components_project FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    CONSTRAINT uq_component_project UNIQUE (project_id, name)
);
GO

CREATE INDEX idx_components_project ON components(project_id);
GO

-- ============================================
-- VERSIONS TABLE
-- ============================================
CREATE TABLE versions (
    version_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    name NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    release_date DATE NULL,
    is_released BIT DEFAULT 0,
    is_archived BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_versions_project FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
GO

CREATE INDEX idx_versions_project ON versions(project_id);
GO

-- ============================================
-- LABELS TABLE
-- ============================================
CREATE TABLE labels (
    label_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(100) UNIQUE NOT NULL,
    color_hex NVARCHAR(7) NULL
);
GO

-- ============================================
-- ISSUES TABLE (Main Table)
-- ============================================
CREATE TABLE issues (
    issue_id INT PRIMARY KEY IDENTITY(1,1),
    issue_key NVARCHAR(50) UNIQUE NOT NULL,
    project_id INT NOT NULL,
    issue_type_id INT NOT NULL,
    summary NVARCHAR(500) NOT NULL,
    description NVARCHAR(MAX) NULL,
    priority_id INT NULL,
    status_id INT NOT NULL,
    resolution_id INT NULL,
    assignee_user_id INT NULL,
    reporter_user_id INT NOT NULL,
    component_id INT NULL,
    version_id INT NULL,
    original_estimate DECIMAL(10,2) NULL, -- hours
    remaining_estimate DECIMAL(10,2) NULL, -- hours
    time_spent DECIMAL(10,2) DEFAULT 0, -- hours
    due_date DATE NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_issues_project FOREIGN KEY (project_id) REFERENCES projects(project_id),
    CONSTRAINT fk_issues_issue_type FOREIGN KEY (issue_type_id) REFERENCES issue_types(issue_type_id),
    CONSTRAINT fk_issues_priority FOREIGN KEY (priority_id) REFERENCES issue_priorities(priority_id),
    CONSTRAINT fk_issues_status FOREIGN KEY (status_id) REFERENCES issue_statuses(status_id),
    CONSTRAINT fk_issues_resolution FOREIGN KEY (resolution_id) REFERENCES resolutions(resolution_id),
    CONSTRAINT fk_issues_assignee FOREIGN KEY (assignee_user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_issues_reporter FOREIGN KEY (reporter_user_id) REFERENCES users(user_id),
    CONSTRAINT fk_issues_component FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE SET NULL,
    CONSTRAINT fk_issues_version FOREIGN KEY (version_id) REFERENCES versions(version_id)
);
GO

CREATE INDEX idx_issues_project ON issues(project_id);
CREATE INDEX idx_issues_assignee ON issues(assignee_user_id);
CREATE INDEX idx_issues_reporter ON issues(reporter_user_id);
CREATE INDEX idx_issues_status ON issues(status_id);
CREATE INDEX idx_issues_priority ON issues(priority_id);
CREATE INDEX idx_issues_due_date ON issues(due_date);
CREATE INDEX idx_issues_created ON issues(created_at);
GO

-- ============================================
-- ISSUE COMMENTS TABLE
-- ============================================
CREATE TABLE issue_comments (
    comment_id INT PRIMARY KEY IDENTITY(1,1),
    issue_id INT NOT NULL,
    user_id INT NOT NULL,
    body NVARCHAR(MAX) NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_comments_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id) ON DELETE CASCADE,
    CONSTRAINT fk_comments_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);
GO

CREATE INDEX idx_comments_issue ON issue_comments(issue_id);
GO

-- ============================================
-- ISSUE ATTACHMENTS TABLE
-- ============================================
CREATE TABLE issue_attachments (
    attachment_id INT PRIMARY KEY IDENTITY(1,1),
    issue_id INT NOT NULL,
    user_id INT NOT NULL,
    filename NVARCHAR(500) NOT NULL,
    file_path NVARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type NVARCHAR(100) NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_attachments_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id) ON DELETE CASCADE,
    CONSTRAINT fk_attachments_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);
GO

CREATE INDEX idx_attachments_issue ON issue_attachments(issue_id);
GO

-- ============================================
-- WORKLOGS TABLE
-- ============================================
CREATE TABLE worklogs (
    worklog_id INT PRIMARY KEY IDENTITY(1,1),
    issue_id INT NOT NULL,
    user_id INT NOT NULL,
    time_spent DECIMAL(10,2) NOT NULL, -- hours
    time_spent_seconds BIGINT NOT NULL, -- alternative storage in seconds
    comment NVARCHAR(MAX) NULL,
    started_at DATETIME2 NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_worklogs_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id) ON DELETE CASCADE,
    CONSTRAINT fk_worklogs_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);
GO

CREATE INDEX idx_worklogs_issue ON worklogs(issue_id);
GO

-- ============================================
-- BOARDS TABLE
-- ============================================
CREATE TABLE boards (
    board_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    name NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    board_type NVARCHAR(50) NOT NULL, -- 'kanban' or 'scrum'
    is_active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_boards_project FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
GO

CREATE INDEX idx_boards_project ON boards(project_id);
GO

-- ============================================
-- BOARD COLUMNS TABLE
-- ============================================
CREATE TABLE board_columns (
    column_id INT PRIMARY KEY IDENTITY(1,1),
    board_id INT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    column_type NVARCHAR(50) NOT NULL, -- 'status' or 'custom'
    mapped_status_id INT NULL,
    sort_order INT NOT NULL,
    is_editable BIT DEFAULT 1,
    CONSTRAINT fk_board_columns_board FOREIGN KEY (board_id) REFERENCES boards(board_id) ON DELETE CASCADE,
    CONSTRAINT fk_board_columns_status FOREIGN KEY (mapped_status_id) REFERENCES issue_statuses(status_id)
);
GO

CREATE INDEX idx_board_columns_board ON board_columns(board_id);
GO

-- ============================================
-- SPRINTS TABLE
-- ============================================
CREATE TABLE sprints (
    sprint_id INT PRIMARY KEY IDENTITY(1,1),
    board_id INT NOT NULL,
    name NVARCHAR(200) NOT NULL,
    goal NVARCHAR(MAX) NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    sprint_status NVARCHAR(50) NOT NULL DEFAULT 'future', -- future, active, closed
    is_completed BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_sprints_board FOREIGN KEY (board_id) REFERENCES boards(board_id)
);
GO

CREATE INDEX idx_sprints_board ON sprints(board_id);
CREATE INDEX idx_sprints_status ON sprints(sprint_status);
GO

-- ============================================
-- ISSUE SPRINTS (Many-to-Many)
-- ============================================
CREATE TABLE issue_sprints (
    issue_id INT NOT NULL,
    sprint_id INT NOT NULL,
    PRIMARY KEY (issue_id, sprint_id),
    CONSTRAINT fk_issue_sprints_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id) ON DELETE CASCADE,
    CONSTRAINT fk_issue_sprints_sprint FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id) ON DELETE CASCADE
);
GO

-- ============================================
-- ISSUE LINKS TABLE
-- ============================================
CREATE TABLE issue_links (
    link_id INT PRIMARY KEY IDENTITY(1,1),
    issue_id_from INT NOT NULL,
    issue_id_to INT NOT NULL,
    link_type NVARCHAR(50) NOT NULL, -- 'blocks', 'is blocked by', 'duplicates', 'is duplicated by', 'relates to', 'parent-child'
    CONSTRAINT fk_issue_links_from FOREIGN KEY (issue_id_from) REFERENCES issues(issue_id),
    CONSTRAINT fk_issue_links_to FOREIGN KEY (issue_id_to) REFERENCES issues(issue_id)
);
GO

CREATE INDEX idx_issue_links_from ON issue_links(issue_id_from);
CREATE INDEX idx_issue_links_to ON issue_links(issue_id_to);
GO

-- ============================================
-- ISSUE LABELS (Many-to-Many)
-- ============================================
CREATE TABLE issue_labels (
    issue_id INT NOT NULL,
    label_id INT NOT NULL,
    PRIMARY KEY (issue_id, label_id),
    CONSTRAINT fk_issue_labels_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id) ON DELETE CASCADE,
    CONSTRAINT fk_issue_labels_label FOREIGN KEY (label_id) REFERENCES labels(label_id)
);
GO

-- ============================================
-- PROJECT ROLES TABLE
-- ============================================
CREATE TABLE project_roles (
    role_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    role_type NVARCHAR(50) NOT NULL, -- 'admin', 'member', 'viewer', etc.
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_project_roles_project FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    CONSTRAINT fk_project_roles_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_project_role_user UNIQUE (project_id, user_id)
);
GO

CREATE INDEX idx_project_roles_project ON project_roles(project_id);
CREATE INDEX idx_project_roles_user ON project_roles(user_id);
GO

-- ============================================
-- PERMISSIONS TABLE
-- ============================================
CREATE TABLE permissions (
    permission_id INT PRIMARY KEY IDENTITY(1,1),
    permission_key NVARCHAR(100) UNIQUE NOT NULL,
    description NVARCHAR(500) NULL
);
GO

INSERT INTO permissions (permission_key, description) VALUES
('browse_project', 'Can view the project and its issues'),
('create_issue', 'Can create new issues'),
('edit_issue', 'Can edit issue details'),
('assign_issue', 'Can assign issues to users'),
('resolve_issue', 'Can resolve/close issues'),
('delete_issue', 'Can delete issues'),
('comment_issue', 'Can add comments to issues'),
('admin_project', 'Can administer the project');
GO

-- ============================================
-- ROLE PERMISSIONS TABLE
-- ============================================
CREATE TABLE role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_id) REFERENCES project_roles(role_id) ON DELETE CASCADE,
    CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(permission_id)
);
GO

-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE notifications (
    notification_id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    type NVARCHAR(50) NOT NULL, -- 'issue_assigned', 'issue_updated', 'comment_added', etc.
    title NVARCHAR(200) NOT NULL,
    message NVARCHAR(MAX) NOT NULL,
    related_issue_id INT NULL,
    is_read BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_notifications_issue FOREIGN KEY (related_issue_id) REFERENCES issues(issue_id)
);
GO

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_created ON notifications(created_at);
GO

-- ============================================
-- ISSUE HISTORY TABLE (Audit Trail)
-- ============================================
CREATE TABLE issue_history (
    history_id INT PRIMARY KEY IDENTITY(1,1),
    issue_id INT NOT NULL,
    user_id INT NOT NULL,
    field_name NVARCHAR(100) NOT NULL,
    old_value NVARCHAR(MAX) NULL,
    new_value NVARCHAR(MAX) NULL,
    changed_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_history_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id) ON DELETE CASCADE,
    CONSTRAINT fk_history_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);
GO

CREATE INDEX idx_history_issue ON issue_history(issue_id);
CREATE INDEX idx_history_changed ON issue_history(changed_at);
GO

-- ============================================
-- FAVORITES TABLE
-- ============================================
CREATE TABLE favorites (
    favorite_id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    issue_id INT NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_favorites_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_favorites_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id),
    CONSTRAINT uq_favorite_user_issue UNIQUE (user_id, issue_id)
);
GO

-- ============================================
-- CREATE TRIGGERS FOR UPDATED_AT
-- ============================================
CREATE TRIGGER trg_users_updated
ON users
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE users SET updated_at = GETDATE() WHERE user_id IN (SELECT user_id FROM inserted);
END;
GO

CREATE TRIGGER trg_projects_updated
ON projects
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE projects SET updated_at = GETDATE() WHERE project_id IN (SELECT project_id FROM inserted);
END;
GO

CREATE TRIGGER trg_issues_updated
ON issues
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE issues SET updated_at = GETDATE() WHERE issue_id IN (SELECT issue_id FROM inserted);
END;
GO

CREATE TRIGGER trg_sprints_updated
ON sprints
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE sprints SET updated_at = GETDATE() WHERE sprint_id IN (SELECT sprint_id FROM inserted);
END;
GO

CREATE TRIGGER trg_boards_updated
ON boards
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE boards SET updated_at = GETDATE() WHERE board_id IN (SELECT board_id FROM inserted);
END;
GO

-- ============================================
-- CREATE STORED PROCEDURES
-- ============================================

-- SP: Get project statistics
CREATE PROCEDURE sp_GetProjectStats
    @project_id INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        COUNT(*) as total_issues,
        SUM(CASE WHEN status_id = (SELECT status_id FROM issue_statuses WHERE name = 'Done') THEN 1 ELSE 0 END) as completed_issues,
        SUM(CASE WHEN status_id != (SELECT status_id FROM issue_statuses WHERE name = 'Done') THEN 1 ELSE 0 END) as open_issues,
        SUM(original_estimate) as total_estimate,
        SUM(time_spent) as total_time_spent
    FROM issues
    WHERE project_id = @project_id;
END;
GO

-- SP: Get board issues by column
CREATE PROCEDURE sp_GetBoardIssues
    @board_id INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        bc.column_id,
        bc.name as column_name,
        bc.sort_order,
        i.issue_id,
        i.issue_key,
        i.summary,
        i.description,
        it.name as issue_type,
        it.icon_name,
        ip.name as priority,
        ip.color_hex as priority_color,
        isn.name as status,
        isn.color_hex as status_color,
        u.display_name as assignee,
        u.avatar_url as assignee_avatar
    FROM board_columns bc
    LEFT JOIN issues i ON bc.mapped_status_id = i.status_id
    LEFT JOIN issue_types it ON i.issue_type_id = it.issue_type_id
    LEFT JOIN issue_priorities ip ON i.priority_id = ip.priority_id
    LEFT JOIN issue_statuses isn ON i.status_id = isn.status_id
    LEFT JOIN users u ON i.assignee_user_id = u.user_id
    WHERE bc.board_id = @board_id
    ORDER BY bc.sort_order, i.priority_id;
END;
GO

-- ============================================
-- CREATE VIEWS
-- ============================================

-- View: Issue Summary
CREATE VIEW vw_IssueSummary AS
SELECT
    i.issue_id,
    i.issue_key,
    i.project_id,
    p.project_key,
    p.name as project_name,
    i.issue_type_id,
    it.name as issue_type,
    i.summary,
    ip.name as priority,
    ip.color_hex as priority_color,
    isn.name as status,
    isn.color_hex as status_color,
    i.assignee_user_id,
    u.display_name as assignee_name,
    r.display_name as reporter_name,
    i.due_date,
    i.created_at,
    i.updated_at
FROM issues i
JOIN projects p ON i.project_id = p.project_id
JOIN issue_types it ON i.issue_type_id = it.issue_type_id
JOIN issue_statuses isn ON i.status_id = isn.status_id
LEFT JOIN issue_priorities ip ON i.priority_id = ip.priority_id
LEFT JOIN users u ON i.assignee_user_id = u.user_id
LEFT JOIN users r ON i.reporter_user_id = r.user_id;
GO

PRINT 'Database schema created successfully!';