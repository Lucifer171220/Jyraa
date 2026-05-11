-- ============================================
-- SAMPLE DATA FOR JIRA CLONE
-- ============================================

USE JiraDB;
GO

-- ============================================
-- INSERT SAMPLE USERS (with password: password123)
-- ============================================
INSERT INTO users (username, email, password_hash, display_name, is_active)
VALUES
('admin', 'admin@jirademo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewldBPH6v9NlZ9G.', 'System Administrator', 1),
('john', 'john@jirademo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewldBPH6v9NlZ9G.', 'John Doe', 1),
('jane', 'jane@jirademo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewldBPH6v9NlZ9G.', 'Jane Smith', 1),
('bob', 'bob@jirademo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewldBPH6v9NlZ9G.', 'Bob Wilson', 1),
('alice', 'alice@jirademo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewldBPH6v9NlZ9G.', 'Alice Brown', 1);

-- Note: password_hash is bcrypt hash of 'password123' (use same for all demo)
-- In production, each user should have unique, strong passwords!
GO

-- ============================================
-- INSERT SAMPLE PROJECTS
-- ============================================
INSERT INTO projects (project_key, name, description, lead_user_id, project_type)
VALUES
('WEB', 'Website Redesign', 'Redesign and development of the company website', 1, 'software'),
('MOB', 'Mobile App', 'iOS and Android mobile application development', 1, 'software'),
('API', 'API Platform', 'Build RESTful APIs for external integrations', 2, 'software'),
('INFRA', 'Infrastructure', 'Cloud infrastructure and DevOps improvements', 3, 'infrastructure');

-- Get IDs for later use
DECLARE @project_web INT = (SELECT project_id FROM projects WHERE project_key = 'WEB');
DECLARE @project_mob INT = (SELECT project_id FROM projects WHERE project_key = 'MOB');
DECLARE @project_api INT = (SELECT project_id FROM projects WHERE project_key = 'API');
DECLARE @project_infra INT = (SELECT project_id FROM projects WHERE project_key = 'INFRA');
GO

-- ============================================
-- INSERT PROJECT COMPONENTS
-- ============================================
INSERT INTO components (project_id, name, description, lead_user_id)
VALUES
(@project_web, 'Frontend', 'User interface components and pages', 2),
(@project_web, 'Backend', 'Server-side logic and APIs', 1),
(@project_mob, 'iOS App', 'iOS application', 3),
(@project_mob, 'Android App', 'Android application', 4),
(@project_api, 'Authentication', 'User authentication and authorization', 1),
(@project_api, 'Rate Limiting', 'API rate limiting middleware', 2);
GO

-- ============================================
-- INSERT PROJECT VERSIONS
-- ============================================
INSERT INTO versions (project_id, name, description, release_date, is_released)
VALUES
(@project_web, 'v1.0', 'Initial website launch', '2026-01-15', 1),
(@project_web, 'v1.1', 'Mobile responsive updates', '2026-02-20', 1),
(@project_web, 'v2.0', 'Complete redesign', NULL, 0),
(@project_mob, 'v1.0-alpha', 'Alpha release for testing', '2026-03-01', 0),
(@project_api, 'v0.1', 'API prototype', '2026-01-10', 1);
GO

-- ============================================
-- INSERT LABELS
-- ============================================
INSERT INTO labels (name, color_hex)
VALUES
('security', '#FF0000'),
('performance', '#FFA500'),
('ui', '#0000FF'),
('database', '#008000'),
('bug', '#FFC0CB'),
('enhancement', '#800080'),
('frontend', '#00CED1'),
('backend', '#FFD700');
GO

-- ============================================
-- INSERT SAMPLE ISSUES
-- ============================================
-- Get status IDs
DECLARE @status_todo INT = (SELECT status_id FROM issue_statuses WHERE name = 'To Do');
DECLARE @status_inprogress INT = (SELECT status_id FROM issue_statuses WHERE name = 'In Progress');
DECLARE @status_inreview INT = (SELECT status_id FROM issue_statuses WHERE name = 'In Review');
DECLARE @status_done INT = (SELECT status_id FROM issue_statuses WHERE name = 'Done');

-- Get priority IDs
DECLARE @priority_highest INT = (SELECT priority_id FROM issue_priorities WHERE name = 'Highest');
DECLARE @priority_high INT = (SELECT priority_id FROM issue_priorities WHERE name = 'High');
DECLARE @priority_medium INT = (SELECT priority_id FROM issue_priorities WHERE name = 'Medium');
DECLARE @priority_low INT = (SELECT priority_id FROM issue_priorities WHERE name = 'Low');

-- Get issue type IDs
DECLARE @type_epic INT = (SELECT issue_type_id FROM issue_types WHERE name = 'Epic');
DECLARE @type_story INT = (SELECT issue_type_id FROM issue_types WHERE name = 'Story');
DECLARE @type_task INT = (SELECT issue_type_id FROM issue_types WHERE name = 'Task');
DECLARE @type_bug INT = (SELECT issue_type_id FROM issue_types WHERE name = 'Bug');

-- Insert issues for WEB project
INSERT INTO issues (issue_key, project_id, issue_type_id, summary, description, priority_id, status_id, reporter_user_id, assignee_user_id, due_date, original_estimate, time_spent)
VALUES
('WEB-1', @project_web, @type_epic, 'Website Redesign Initiative', 'Complete redesign of the company website with modern UI/UX, improved performance, and mobile responsiveness.', @priority_high, @status_inprogress, 1, 2, '2026-05-30', 320, 45),
('WEB-2', @project_web, @type_story, 'User can log in securely', 'Implement OAuth 2.0 authentication with social login options (Google, GitHub)', @priority_high, @status_inprogress, 1, 2, '2026-03-15', 24, 8),
('WEB-3', @project_web, @type_task, 'Design homepage mockups', 'Create Figma mockups for the new homepage with stakeholder approval', @priority_medium, @status_done, 2, 2, '2026-02-01', 16, 16),
('WEB-4', @project_web, @type_bug, 'Navigation menu broken on mobile', 'The hamburger menu does not open on iOS Safari', @priority_highest, @status_todo, 1, 4, '2026-02-20', 8, 0),
('WEB-5', @project_web, @type_story, 'User can search products', 'Implement product search with autocomplete and filters', @priority_medium, @status_todo, 1, NULL, '2026-04-01', 40, 0),
('WEB-6', @project_web, @type_task, 'Setup CI/CD pipeline', 'Configure GitHub Actions for automated testing and deployment', @priority_low, @status_inreview, 3, 1, NULL, 12, 10);

-- Insert issues for MOB project
INSERT INTO issues (issue_key, project_id, issue_type_id, summary, description, priority_id, status_id, reporter_user_id, assignee_user_id, due_date, original_estimate, time_spent)
VALUES
('MOB-1', @project_mob, @type_epic, 'Mobile App V1 Launch', 'Develop and launch iOS and Android apps for our platform', @priority_high, @status_inprogress, 1, 3, '2026-06-30', 480, 120),
('MOB-2', @project_mob, @type_story, 'User can browse products on mobile', 'Mobile-optimized product catalog with infinite scroll', @priority_medium, @status_inprogress, 3, 4, '2026-04-15', 40, 12),
('MOB-3', @project_mob, @type_bug, 'App crashes on login', 'App crashes with null pointer when network is slow', @priority_highest, @status_todo, 4, 3, '2026-02-25', 4, 0),
('MOB-4', @project_mob, @type_story, 'Push notifications', 'Send push notifications for order updates', @priority_medium, @status_todo, 3, NULL, '2026-05-01', 24, 0);

-- Insert issues for API project
INSERT INTO issues (issue_key, project_id, issue_type_id, summary, description, priority_id, status_id, reporter_user_id, assignee_user_id, due_date, original_estimate, time_spent)
VALUES
('API-1', @project_api, @type_story, 'Implement REST authentication endpoints', 'Create /auth/login, /auth/refresh, /auth/logout endpoints with JWT', @priority_highest, @status_done, 1, 1, '2026-01-25', 16, 20),
('API-2', @project_api, @type_task, 'Add API rate limiting', 'Implement sliding window rate limiting per API key', @priority_high, @status_inprogress, 2, 2, '2026-03-01', 12, 3),
('API-3', @project_api, @type_bug, 'Memory leak in GraphQL resolver', 'Server OOM after 24 hours of continuous operation', @priority_highest, @status_inprogress, 1, 1, '2026-02-28', 24, 8),
('API-4', @project_api, @type_story, 'API versioning', 'Support /api/v1/ and /api/v2/ endpoints', @priority_medium, @status_todo, 2, NULL, '2026-06-01', 32, 0);

-- Get label IDs
DECLARE @label_security INT = (SELECT label_id FROM labels WHERE name = 'security');
DECLARE @label_performance INT = (SELECT label_id FROM labels WHERE name = 'performance');
DECLARE @label_ui INT = (SELECT label_id FROM labels WHERE name = 'ui');
DECLARE @label_frontend INT = (SELECT label_id FROM labels WHERE name = 'frontend');
DECLARE @label_backend INT = (SELECT label_id FROM labels WHERE name = 'backend');

-- Link labels to issues
INSERT INTO issue_labels (issue_id, label_id)
SELECT i.issue_id, @label_security FROM issues i WHERE i.issue_key IN ('WEB-2', 'MOB-3');
INSERT INTO issue_labels (issue_id, label_id)
SELECT i.issue_id, @label_performance FROM issues i WHERE i.issue_key IN ('WEB-4', 'API-3');
INSERT INTO issue_labels (issue_id, label_id)
SELECT i.issue_id, @label_ui FROM issues i WHERE i.issue_key IN ('WEB-3', 'WEB-1');
INSERT INTO issue_labels (issue_id, label_id)
SELECT i.issue_id, @label_frontend FROM issues i WHERE i.issue_key IN ('WEB-2', 'WEB-3', 'WEB-4');
INSERT INTO issue_labels (issue_id, label_id)
SELECT i.issue_id, @label_backend FROM issues i WHERE i.issue_key IN ('WEB-2', 'API-1', 'API-2', 'API-3');
GO

-- ============================================
-- INSERT PROJECT ROLES
-- ============================================
INSERT INTO project_roles (project_id, user_id, role_type)
VALUES
(@project_web, 1, 'admin'),
(@project_web, 2, 'member'),
(@project_web, 4, 'member'),
(@project_mob, 1, 'admin'),
(@project_mob, 3, 'admin'),
(@project_mob, 4, 'member'),
(@project_api, 1, 'member'),
(@project_api, 2, 'admin'),
(@project_api, 3, 'member'),
(@project_infra, 3, 'admin'),
(@project_infra, 1, 'member');
GO

-- ============================================
-- INSERT SAMPLE COMMENTS
-- ============================================
INSERT INTO issue_comments (issue_id, user_id, body)
VALUES
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-1'), 1, 'This is the main initiative for Q1-Q2. Let''s make it happen!'),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-2'), 2, 'We should use Auth0 for faster implementation'),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-2'), 1, 'Agreed, let''s explore Auth0 vs AWS Cognito'),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-4'), 4, 'I''ll investigate the iOS Safari issue'),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'API-3'), 1, 'This is critical, we need to fix ASAP'),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'API-3'), 2, 'Found the root cause - circular reference in GraphQL schema');
GO

-- ============================================
-- INSERT WORKLOGS
-- ============================================
INSERT INTO worklogs (issue_id, user_id, time_spent, time_spent_seconds, comment, started_at)
VALUES
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-2'), 2, 8, 28800, 'Implemented OAuth flow', DATEADD(hour, -8, GETDATE())),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-2'), 1, 4, 14400, 'Code review', DATEADD(hour, -4, GETDATE())),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'API-3'), 1, 8, 28800, 'Memory profiling', DATEADD(hour, -24, GETDATE())),
((SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'API-1'), 1, 20, 72000, 'Full implementation and testing', DATEADD(day, -3, GETDATE()));
GO

-- ============================================
-- INSERT SAMPLE BOARDS
-- ============================================
INSERT INTO boards (project_id, name, description, board_type, is_active)
VALUES
(@project_web, 'Website Kanban', 'Kanban board for website redesign tasks', 'kanban', 1),
(@project_mob, 'Mobile Scrum Board', 'Scrum board for mobile app development', 'scrum', 1),
(@project_api, 'API Development', 'Track API development and bugs', 'kanban', 1);

-- Get board IDs
DECLARE @board_web INT = (SELECT TOP 1 board_id FROM boards WHERE project_id = @project_web);
DECLARE @board_mob INT = (SELECT TOP 1 board_id FROM boards WHERE project_id = @project_mob);
DECLARE @board_api INT = (SELECT TOP 1 board_id FROM boards WHERE project_id = @project_api);

-- Insert board columns for Kanban board (WEB)
INSERT INTO board_columns (board_id, name, column_type, mapped_status_id, sort_order, is_editable)
VALUES
(@board_web, 'To Do', 'status', @status_todo, 1, 0),
(@board_web, 'In Progress', 'status', @status_inprogress, 2, 0),
(@board_web, 'In Review', 'status', @status_inreview, 3, 0),
(@board_web, 'Done', 'status', @status_done, 4, 0);

-- Insert board columns for Scrum board (MOB)
INSERT INTO board_columns (board_id, name, column_type, mapped_status_id, sort_order, is_editable)
VALUES
(@board_mob, 'Backlog', 'status', @status_todo, 1, 0),
(@board_mob, 'Sprint', 'status', @status_inprogress, 2, 0),
(@board_mob, 'In Review', 'status', @status_inreview, 3, 0),
(@board_mob, 'Done', 'status', @status_done, 4, 0);

-- Insert board columns for API board
INSERT INTO board_columns (board_id, name, column_type, mapped_status_id, sort_order, is_editable)
VALUES
(@board_api, 'Todo', 'status', @status_todo, 1, 0),
(@board_api, 'Doing', 'status', @status_inprogress, 2, 0),
(@board_api, 'Review', 'status', @status_inreview, 3, 0),
(@board_api, 'Done', 'status', @status_done, 4, 0);
GO

-- ============================================
-- INSERT SAMPLE SPRINTS (for Scrum board)
-- ============================================
INSERT INTO sprints (board_id, name, goal, start_date, end_date, sprint_status, is_completed)
VALUES
(@board_mob, 'Sprint 1 - MVP', 'Complete core mobile features for MVP release', '2026-02-01', '2026-02-14', 'closed', 1),
(@board_mob, 'Sprint 2 - Polish', 'Polish and bug fixing before beta', '2026-02-15', '2026-02-28', 'active', 0),
(@board_mob, 'Sprint 3 - Features', 'Add remaining features for v1.0', '2026-03-01', '2026-03-14', 'future', 0);

-- Assign issues to sprint
INSERT INTO issue_sprints (issue_id, sprint_id)
SELECT 
  (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'MOB-2'),
  (SELECT TOP 1 sprint_id FROM sprints WHERE board_id = @board_mob AND name = 'Sprint 2 - Polish');

INSERT INTO issue_sprints (issue_id, sprint_id)
SELECT 
  (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'MOB-3'),
  (SELECT TOP 1 sprint_id FROM sprints WHERE board_id = @board_mob AND name = 'Sprint 2 - Polish');

INSERT INTO issue_sprints (issue_id, sprint_id)
SELECT 
  (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'MOB-4'),
  (SELECT TOP 1 sprint_id FROM sprints WHERE board_id = @board_mob AND name = 'Sprint 3 - Features');
GO

-- ============================================
-- INSERT SAMPLE NOTIFICATIONS
-- ============================================
INSERT INTO notifications (user_id, type, title, message, related_issue_id)
VALUES
(2, 'issue_assigned', 'Issue Assigned', 'WEB-2: User can log in securely has been assigned to you', (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-2')),
(4, 'issue_created', 'Issue Created', 'WEB-4: Navigation menu broken on mobile was created', (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-4')),
(3, 'comment_added', 'New Comment', 'Jane Smith commented on MOB-3', (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'MOB-3'));
GO

-- ============================================
-- INSERT FAVORITES
-- ============================================
INSERT INTO favorites (user_id, issue_id)
VALUES
(2, (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-1')),
(2, (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'WEB-5')),
(4, (SELECT TOP 1 issue_id FROM issues WHERE issue_key = 'MOB-4'));
GO

PRINT 'Sample data inserted successfully!';
PRINT 'Default admin credentials:';
PRINT '  Username: admin';
PRINT '  Password: password123';