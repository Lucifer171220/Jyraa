# Advanced Implementation Changes

This document summarizes the advanced Jira-like features added to ZYRAA across the backend, frontend, database schema, and deployment configuration.

## Implementation Scope

The completed implementation covers the following roadmap items:

- Email notifications
- In-app notifications
- Advanced permission system and ACLs
- File attachment upload, listing, download, and deletion
- Sprint planning with capacity summaries
- Roadmaps and Gantt-style timeline data
- Advanced JQL-like search
- Filters and saved searches
- Dashboards and gadgets
- Webhooks and integrations
- REST API pagination
- API rate limiting
- Bulk issue operations
- Issue templates
- Audit logging enhancements
- Background tasks for email and notifications
- Docker deployment configuration

## Backend Changes

### API Routers

The API router now registers the expanded module set in `backend/app/api/v1/__init__.py`.

New or expanded routers:

- `audit.py`: exposes audit event listing with entity filters.
- `boards.py`: adds sprint listing, sprint creation, issue assignment to sprints, and sprint capacity endpoints.
- `bulk.py`: supports bulk issue status, assignee, delete, and label operations.
- `dashboards.py`: supports dashboard creation/list/detail and gadget add/delete.
- `filters.py`: supports saved search CRUD.
- `issues.py`: adds issue pagination, JQL-like search, assignment notifications, audit writes, attachment upload/list/download/delete, and comment notifications.
- `notifications.py`: supports notification listing, mark-read, and mark-all-read.
- `permissions.py`: supports permission listing and project role/ACL assignment.
- `projects.py`: automatically grants project creator an admin project role with seeded permissions.
- `roadmaps.py`: supports roadmap CRUD, roadmap items, and Gantt-style item output.
- `tasks.py`: exposes background task queue and email queue visibility plus manual task processing.
- `templates.py`: supports issue template CRUD.
- `users.py`: fixes user creation behavior and adds `/users/me` profile read/update endpoints.
- `webhooks.py`: supports webhook CRUD and test delivery.

### Services

New or expanded service modules:

- `attachment_service.py`: stores uploaded files under `uploads/attachments`, creates attachment records, lists issue attachments, and deletes attachment files/records.
- `jql_service.py`: parses a compact JQL-like query syntax and applies SQLAlchemy filters for project, issue type, priority, status, assignee, reporter, labels, issue key, text, summary, description, created, updated, and due date.
- `permission_service.py`: provides project role assignment, permission checks, role permission attachment, and simplified admin detection.
- `task_processor.py`: queues email and notification tasks and processes pending background tasks.

Existing `email_service.py` is used by the task processor to send queued email when SMTP settings are configured.

### Middleware

Added middleware support:

- `rate_limit.py`: request rate limiting by endpoint and client IP, backed by the `api_rate_limits` table.
- `audit.py`: helper for creating audit log rows.

`backend/app/main.py` now installs `RateLimitMiddleware`.

### Models

`backend/app/models/__init__.py` now contains ORM models and relationships for:

- `Webhook`
- `IssueTemplate`
- `Filter`
- `Dashboard`
- `DashboardGadget`
- `Roadmap`
- `RoadmapItem`
- `AuditLog`
- `BackgroundTask`
- `EmailQueue`
- `ApiRateLimit`

Relationship fixes were made for:

- `Roadmap.items` and `RoadmapItem.roadmap`
- `IssueTemplate.assignee` and `IssueTemplate.creator` with explicit foreign keys
- `ProjectRole.permissions` using `back_populates`

### Database Setup

`backend/app/database.py` now reads `DATABASE_SERVER` from the environment when provided, while preserving the original trusted local SQL Server default.

Seed data now includes default permission keys:

- `project.admin`
- `project.read`
- `issue.create`
- `issue.update`
- `issue.delete`
- `sprint.manage`
- `roadmap.manage`
- `webhook.manage`
- `template.manage`
- `dashboard.manage`

## Database Schema Changes

`database/schema.sql` includes advanced feature tables and indexes for:

- Webhooks
- Issue templates
- Saved filters
- Dashboards
- Dashboard gadgets
- Roadmaps
- Roadmap items
- Audit logs
- API rate limits
- Email queue
- Background tasks

Important note: `Base.metadata.create_all` creates missing tables but does not modify existing tables. Existing databases should be updated through schema scripts or migrations before using all advanced features.

## Frontend Changes

### New Pages

Added new App Router pages:

- `frontend/src/app/search/page.tsx`
- `frontend/src/app/planning/page.tsx`
- `frontend/src/app/dashboards/page.tsx`
- `frontend/src/app/admin/page.tsx`

### Search Page

Route: `/search`

Capabilities:

- Run JQL-like issue searches.
- View paginated-style result payloads.
- Create saved filters.
- Re-run saved filters.
- Jump from search results to issue details.

Example queries:

```text
project = DEMO status != Done
assignee ~ rupam priority = High
text ~ "login" labels = frontend
```

### Planning Page

Route: `/planning`

Capabilities:

- Select a project and board.
- Create sprints.
- View sprint issue count, planned capacity, and remaining capacity.
- Create roadmaps.
- Add project issues to a roadmap.
- Display roadmap items in a lightweight Gantt-style timeline.

### Dashboards Page

Route: `/dashboards`

Capabilities:

- Create shared dashboards.
- View dashboard details.
- Add gadget blocks.
- Delete gadget blocks.

Initial gadget types used by the UI:

- `issue_stats`
- `assigned_work`
- `sprint_capacity`

### Admin Page

Route: `/admin`

Capabilities:

- Select project and user.
- View and assign project roles.
- Display available permissions.
- Create project webhooks.
- Create issue templates.
- View background tasks.
- Trigger task processing.
- View audit events.

### Issue Detail Attachments

`frontend/src/components/IssueDetailPage.tsx` now includes an `Attachments` activity tab.

Capabilities:

- Upload a file to the current issue.
- List issue attachments.
- Download attachments through authenticated Axios requests.
- Delete attachments.

### Navigation

`frontend/src/app/AppFrame.tsx` now includes navigation links and route metadata for:

- Search
- Planning
- Dashboards
- Admin

### API Client

`frontend/src/lib/api.ts` now exposes clients for:

- `attachmentAPI`
- `auditAPI`
- `bulkAPI`
- `dashboardAPI`
- `filterAPI`
- `notificationAPI`
- `permissionAPI`
- `roadmapAPI`
- `taskAPI`
- `templateAPI`
- `webhookAPI`

Existing clients were expanded for issue pagination/search and board sprint/capacity operations.

### Types

`frontend/src/types/index.ts` now includes TypeScript interfaces for:

- `Attachment`
- `SavedFilter`
- `Dashboard`
- `DashboardGadget`
- `Roadmap`
- `RoadmapItem`
- `ProjectRole`
- `Permission`
- `AuditEvent`
- `BackgroundTask`

`Sprint` now includes optional capacity summary fields.

## Docker Deployment Changes

Docker-related files:

- `backend/Dockerfile`
- `docker/docker-compose.yml`
- `docker/nginx.conf`

The Docker stack includes:

- SQL Server 2022
- Redis
- FastAPI backend
- Next.js frontend
- nginx reverse proxy

Key fixes:

- Backend Docker image installs Microsoft ODBC Driver 18.
- Compose backend uses a container SQL Server URL through `DATABASE_SERVER`.
- Compose frontend uses `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.
- Removed a stale Celery worker definition that referenced a missing module.
- Added nginx config for frontend and API proxying.
- Updated SQL Server health check path to `mssql-tools18`.

## Important API Endpoints

### Issues

- `GET /api/v1/issues/`
- `GET /api/v1/issues/paginated`
- `GET /api/v1/issues/search`
- `POST /api/v1/issues/`
- `PUT /api/v1/issues/{issue_id}`
- `DELETE /api/v1/issues/{issue_id}`
- `POST /api/v1/issues/{issue_id}/attachments`
- `GET /api/v1/issues/{issue_id}/attachments`
- `GET /api/v1/issues/attachments/{attachment_id}/download`
- `DELETE /api/v1/issues/attachments/{attachment_id}`

### Boards and Sprints

- `GET /api/v1/boards/{board_id}/sprints`
- `POST /api/v1/boards/{board_id}/sprints`
- `POST /api/v1/boards/sprints/{sprint_id}/issues`
- `GET /api/v1/boards/sprints/{sprint_id}/capacity`

### Roadmaps

- `GET /api/v1/roadmaps`
- `POST /api/v1/roadmaps`
- `GET /api/v1/roadmaps/{roadmap_id}`
- `POST /api/v1/roadmaps/{roadmap_id}/items`
- `GET /api/v1/roadmaps/{roadmap_id}/gantt`

### Admin and Operations

- `GET /api/v1/permissions`
- `GET /api/v1/permissions/projects/{project_id}/roles`
- `POST /api/v1/permissions/projects/{project_id}/roles`
- `GET /api/v1/audit`
- `GET /api/v1/tasks`
- `POST /api/v1/tasks/process`
- `GET /api/v1/tasks/emails`

### Saved Filters, Dashboards, Templates, and Webhooks

- `GET /api/v1/filters`
- `POST /api/v1/filters`
- `GET /api/v1/dashboards`
- `POST /api/v1/dashboards`
- `POST /api/v1/dashboards/{dashboard_id}/gadgets`
- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `GET /api/v1/webhooks`
- `POST /api/v1/webhooks`
- `POST /api/v1/webhooks/{webhook_id}/test`

### Notifications

- `GET /api/v1/notifications`
- `PUT /api/v1/notifications/{notification_id}/read`
- `PUT /api/v1/notifications/read-all`

## Verification Performed

The following checks were run successfully:

```powershell
python -m compileall backend\app
python -c "from app.main import app; print('backend app import ok')"
python -c "import app.models; from sqlalchemy.orm import configure_mappers; configure_mappers(); print('mappers ok')"
cd frontend
npm run type-check
npm run build
cd ..
docker compose -f docker\docker-compose.yml config
```

Notes:

- The first sandboxed Python/frontend checks could not write cache files in some cases, so they were rerun with approval outside the sandbox.
- SQLAlchemy mapper validation passed.
- SQLAlchemy still reports pre-existing overlap warnings for relationships in assignment and code-review models. These are warnings, not blocking errors.
- Docker Compose config validation passed. Docker emitted local warnings about access to the user's Docker config file, but the compose file rendered correctly.

## Known Follow-Ups

These items are useful next steps, but were outside the completed implementation scope:

- Add Alembic migrations for all advanced schema changes.
- Add backend pytest coverage for the new routers and services.
- Add frontend component/integration tests for Search, Planning, Dashboards, Admin, and attachment flows.
- Replace simplified admin detection in `permission_service.py` with a first-class global admin model.
- Add webhook delivery retries and delivery history.
- Add notification preferences per user.
- Add richer dashboard gadget data visualization.
- Add stricter API response schemas for dict-based endpoints.
