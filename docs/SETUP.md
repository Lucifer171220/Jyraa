# Setup Guide

This guide will help you set up the Jira Clone application on your local machine.

## System Requirements

- **Python**: 3.9 or higher
- **Node.js**: 18.x or higher
- **SQL Server**: 2019+ (or Azure SQL Database)
- **ODBC Driver**: ODBC Driver 17 for SQL Server
- **Git**: for version control

## Installation Steps

### Step 1: Clone or Download the Project

If you have the project files, place them in your desired directory:
```
D:\Jira\
```

### Step 2: Set Up SQL Server

1. Install SQL Server (Developer edition recommended)
2. Install ODBC Driver 17 for SQL Server
3. Create a new database named `JiraDB`

   ```sql
   CREATE DATABASE JiraDB;
   ```

4. Run the database schema script:

   - Open SQL Server Management Studio (SSMS)
   - Connect to your server
   - Open `database/schema.sql`
   - Execute the entire script to create all tables, views, stored procedures, and sample data

5. (Optional) If you want more sample data, also run `database/sample_data.sql`

### Step 3: Configure Backend

1. Navigate to the backend directory:

   ```bash
   cd D:\Jira\backend
   ```

2. Create a virtual environment (Windows):

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

   Or on Linux/macOS:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:

   ```bash
   copy .env.example .env
   ```

   Edit `.env` with your database settings:

   ```env
   DATABASE_SERVER=localhost,1433
   DATABASE_NAME=JiraDB
   DATABASE_USER=sa
   DATABASE_PASSWORD=YourStrong@Passw0rd
   SECRET_KEY=change-this-to-a-random-32+char-string
   FRONTEND_URL=http://localhost:3000
   NIM_BASE_URL=https://integrate.api.nvidia.com/v1
   NVIDIA_API_KEY=your-nvidia-api-key
   NIM_MODEL=moonshotai/kimi-k2.6
   ```

   **Important**: Change `SECRET_KEY` to a secure random string in production!

### Step 4: Run Backend

Start the FastAPI server:

```bash
# Option 1: Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using the run.py script
python run.py
```

The API will be available at: `http://localhost:8000`

- Interactive docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Step 5: Configure Frontend

1. Navigate to the frontend directory:

   ```bash
   cd D:\Jira\frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. (Optional) Configure environment variables:

   Create `.env.local`:

   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```

   The default already points to localhost:8000, so this step is optional unless your backend is on a different host/port.

### Step 6: Run Frontend

Start the Next.js development server:

```bash
npm run dev
```

Open `http://localhost:3000` in your browser.

### Step 7: Create Your First User

1. Click "Sign up here" on the login page
2. Register a new account with:
   - Username
   - Email
   - Display Name
   - Password (min 8 characters)
3. You'll be automatically logged in and redirected to the home page

## Using the Application

### First Steps

1. **Create a Project**: From the home page or projects page, click "Create Project"
   - Enter a Project Key (e.g., "DEMO") - will be used in issue references
   - Enter a Project Name
   - Optional: Add a description

2. **Create a Board**: On the project detail page, click "Create Board"
   - Choose Board Type: Kanban (continuous flow) or Scrum (with sprints)
   - Enter a name and optional description
   - The board will have default columns based on issue statuses

3. **Create Issues**: Navigate to the board and:
   - Click "Create Issue" button (top right)
   - Fill in the issue form:
     - Summary (required)
     - Description
     - Issue Type (Task, Bug, Story, Epic, Subtask)
     - Priority (Highest, High, Medium, Low, Lowest)
     - Assignee (optional)
   - The issue will appear in the "To Do" column

4. **Move Issues**: Drag and drop issue cards between columns to change status

5. **View Issue Details**: Click on an issue card to:
   - View full details
   - Add comments
   - Log work (coming soon)
   - Edit issue
   - Link to other issues

## API Examples

### Create Project (using curl)

```bash
curl -X POST "http://localhost:8000/api/v1/projects/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_key": "TEST", "name": "Test Project"}'
```

### Create Issue (using curl)

```bash
curl -X POST "http://localhost:8000/api/v1/issues/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_key": "TEST",
    "issue_type": "Task",
    "summary": "Test task",
    "priority": "Medium"
  }'
```

### Get Board Issues

```bash
curl -X GET "http://localhost:8000/api/v1/boards/1/issues" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Troubleshooting

### Database Connection Errors

- Ensure SQL Server is running
- Verify credentials in `.env` are correct
- Check that the database `JiraDB` exists
- Ensure port 1433 is accessible

### Backend Won't Start

- Check Python dependencies: `pip install -r requirements.txt`
- Verify port 8000 is not in use: `netstat -ano | findstr :8000`
- Check for syntax errors: `python -m py_compile app/main.py`

### Frontend Won't Start

- Ensure Node.js is installed: `node --version`
- Reinstall dependencies: `rm -rf node_modules && npm install`
- Check port 3000 availability

### CORS Errors

- Confirm `FRONTEND_URL` in backend `.env` matches your frontend origin (usually `http://localhost:3000`)
- Restart backend after changing `.env`

### JWT Authentication Issues

- Tokens are stored in localStorage
- Token format: `Bearer <token>`
- Default token lifetime: 30 days
- If encountering 401 errors, try logging in again

## Docker Setup (Alternative)

If you prefer to use Docker for the database:

1. Start SQL Server container:

   ```bash
   cd docker
   docker-compose up -d
   ```

2. Wait a minute for SQL Server to initialize
3. Connect to `localhost,1433` with:
   - Username: `sa`
   - Password: `YourStrong@Passw0rd`
4. Create `JiraDB` and run schema.sql

## Next Steps

- Explore the API documentation at `/docs`
- Create sample data using `database/sample_data.sql`
- Customize the issue statuses, types, and priorities in the database
- Extend the API with new endpoints
- Add more UI components and features

## Getting Help

- Check the API docs: `http://localhost:8000/docs`
- Review database schema in `database/schema.sql`
- Check browser console for frontend errors
- Check terminal for backend errors

Enjoy building with Jira Clone!
