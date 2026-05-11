# Jira Clone - Project Management System

A full-stack Jira-like project management and issue tracking system built with **SQL Server**, **FastAPI** (Python), and **React/Next.js** (TypeScript).

## Features

- **Projects & Boards**: Create projects and Kanban/Scrum boards to organize work
- **Issue Tracking**: Create, edit, and manage issues with types (Epic, Story, Task, Bug)
- **Status Workflow**: Customizable workflow with statuses (To Do, In Progress, In Review, Done, Cancelled)
- **Priority System**: 5-level priority system from Lowest to Highest
- **Drag & Drop**: Intuitive board interface for moving issues between columns
- **Comments & Worklogs**: Add comments and track time spent on issues
- **User Management**: User registration, authentication via JWT tokens
- **Labels & Components**: Categorize issues with labels and components
- **Search**: Basic search functionality across issues

## Tech Stack

### Backend
- **FastAPI**: High-performance web framework
- **SQLAlchemy**: ORM for database operations
- **SQL Server**: Primary database
- **PyODBC**: SQL Server driver
- **JWT**: Authentication tokens
- **Alembic**: Database migrations (optional)

### Frontend
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Heroicons**: Beautiful hand-crafted SVG icons
- **Axios**: HTTP client

## Project Structure

```
Jira/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── issues.py
│   │   │   │   └── boards.py
│   │   │   └── __init__.py
│   │   ├── crud/
│   │   │   ├── base.py
│   │   │   └── __init__.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   └── __init__.py
│   │   ├── database.py
│   │   ├── config.py
│   │   ├── auth.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── register/
│   │   │   │   └── page.tsx
│   │   │   ├── projects/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── [projectId]/
│   │   │   │       └── page.tsx
│   │   │   └── boards/
│   │   │       └── [boardId]/
│   │   │           └── page.tsx
│   │   ├── components/
│   │   │   ├── IssueCard.tsx
│   │   │   ├── BoardColumn.tsx
│   │   │   ├── IssueBoard.tsx
│   │   │   └── IssueDetailModal.tsx
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── auth-context.tsx
│   │   ├── styles/
│   │   │   └── globals.css
│   │   └── types/
│   │       └── index.ts
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── tailwind.config.js
├── database/
│   └── schema.sql
└── docs/
    └── (to be added)
```

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- SQL Server (2019+) or Azure SQL Database
- ODBC Driver 17 for SQL Server

### 1. Database Setup

Connect to your SQL Server instance and run the provided schema:

```sql
-- Connect to your SQL Server
-- Create database
CREATE DATABASE JiraDB;

USE JiraDB;

-- Execute the schema from database/schema.sql
```

**Note**: The schema includes sample data for issue types, priorities, statuses, and resolutions.

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional)
# Create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Run development server
npm run dev
```

Open `http://localhost:3000` in your browser.

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Register new user

### Users
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user

### Projects
- `GET /api/v1/projects/` - List projects
- `POST /api/v1/projects/` - Create project
- `GET /api/v1/projects/{project_id}` - Get project by ID
- `PUT /api/v1/projects/{project_id}` - Update project
- `GET /api/v1/projects/{project_id}/issues` - Get project issues
- `GET /api/v1/projects/{project_id}/stats` - Get project statistics

### Issues
- `GET /api/v1/issues/` - List issues (with filtering)
- `POST /api/v1/issues/` - Create issue
- `GET /api/v1/issues/{issue_id}` - Get issue by ID
- `GET /api/v1/issues/key/{issue_key}` - Get issue by key
- `PUT /api/v1/issues/{issue_id}` - Update issue
- `DELETE /api/v1/issues/{issue_id}` - Delete issue
- `POST /api/v1/issues/{issue_id}/comments` - Add comment
- `GET /api/v1/issues/{issue_id}/comments` - Get comments
- `POST /api/v1/issues/{issue_id}/worklogs` - Add worklog
- `GET /api/v1/issues/{issue_id}/worklogs` - Get worklogs
- `POST /api/v1/issues/{issue_id}/link` - Link issue to another

### Boards
- `GET /api/v1/boards/project/{project_id}` - Get project boards
- `POST /api/v1/boards/` - Create board
- `GET /api/v1/boards/{board_id}` - Get board by ID
- `PUT /api/v1/boards/{board_id}` - Update board
- `POST /api/v1/boards/{board_id}/columns` - Add column
- `GET /api/v1/boards/{board_id}/columns` - Get columns
- `GET /api/v1/boards/{board_id}/issues` - Get board issues grouped by column

## Database Schema

The database includes the following main tables:

- **users**: User accounts
- **projects**: Project definitions
- **issues**: Core issue tracking
- **issue_types**: Issue type definitions (Epic, Story, Task, Bug, Subtask)
- **issue_statuses**: Issue statuses
- **issue_priorities**: Priority levels
- **issue_comments**: Comments on issues
- **issue_attachments**: File attachments
- **worklogs**: Time tracking entries
- **boards**: Kanban/Scrum boards
- **board_columns**: Board columns mapped to statuses
- **sprints**: Scrum sprints
- **issue_sprints**: Many-to-many relation
- **components**: Project components
- **versions**: Project versions/fixes
- **labels**: Labels for categorization
- **issue_labels**: Issue-label many-to-many
- **project_roles**: User roles per project
- **notifications**: User notifications
- **issue_history**: Audit trail
- **favorites**: User-favorite issues

Refer to `database/schema.sql` for the complete schema with indexes, triggers, and stored procedures.

## Key Concepts

### Issue Flow
1. An issue belongs to a **project** and has a unique key (e.g., `PROJ-123`)
2. Issues have a **type** (Epic, Story, Task, Bug)
3. Issues go through **statuses**: To Do → In Progress → In Review → Done/Cancelled
4. Issues can be assigned to a **user** (assignee)
5. Issues can have **priority**, **labels**, **components**, and **versions**
6. Issues can be linked to other issues (blocks, duplicates, relates)

### Boards
- Boards are associated with a project
- Each board has **columns** (typically mapped to issue statuses)
- Issues appear in columns based on their status
- Drag and drop moves issues between columns (updates status)
- Two board types: **Kanban** (continuous flow) and **Scrum** (with sprints)

### Authentication
- JWT-based authentication
- Include `Authorization: Bearer <token>` header in API requests
- Tokens expire after 30 days (configurable)

## Configuration

### Backend Environment Variables (.env)

```environment
DATABASE_SERVER=localhost,1433
DATABASE_NAME=JiraDB
DATABASE_USER=sa
DATABASE_PASSWORD=YourStrong@Passw0rd
SECRET_KEY=your-secret-jwt-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200
FRONTEND_URL=http://localhost:3000
```

### Frontend

- `NEXT_PUBLIC_API_URL`: Set to your backend URL (defaults to localhost:8000)

## Development

### Running Both Services

1. Start SQL Server (make sure JiraDB exists)
2. Start backend: `cd backend && uvicorn app.main:app --reload`
3. Start frontend: `cd frontend && npm run dev`
4. Access at `http://localhost:3000`

### API Documentation

Once backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Current Limitations & Future Work

- [ ] Email notifications
- [ ] Advanced permission system (ACLs)
- [ ] File attachments upload
- [ ] Sprint planning with capacity
- [ ] Roadmaps & Gantt charts
- [ ] Advanced search (JQL-like)
- [ ] Filters & saved searches
- [ ] Dashboards & gadgets
- [ ] Webhooks & integrations
- [ ] REST API pagination
- [ ] API rate limiting
- [ ] Bulk operations
- [ ] Issue templates
- [ ] Audit logging enhancements
- [ ] Background tasks (email, notifications)
- [ ] Docker deployment configuration

## Contributing

This is a learning/demo project. Feel free to fork and improve!

## License

MIT

## Support

For issues and feature requests, please open an issue on GitHub.