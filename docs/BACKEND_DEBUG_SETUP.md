# Backend Environment and Debug Setup

This repo is now set up to use a project-local virtual environment at `backend/.venv`.

## What was done

1. Created the virtual environment at `backend/.venv`
2. Installed the packages from `backend/requirements.txt`
3. Updated VS Code debug configuration to use `backend/.venv/Scripts/python.exe` explicitly

## How to use it

From PowerShell:

```powershell
cd D:\Jira\backend
.\.venv\Scripts\Activate.ps1
```

Check the interpreter:

```powershell
python --version
```

Install or refresh dependencies later:

```powershell
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
```

## VS Code debugger

The debugger in `.vscode/launch.json` now points directly at:

```text
${workspaceFolder}/backend/.venv/Scripts/python.exe
```

That means the FastAPI debug session should run inside the backend virtual environment even if a different global interpreter is selected elsewhere.

## Environment file

The debug config loads:

```text
backend/.env
```

If it does not exist yet, create it from the example:

```powershell
cd D:\Jira\backend
Copy-Item .env.example .env
```

Then update the database and secret values in `.env`.

## Current startup blocker

The virtual environment and debugger are configured, but the app still does not fully import yet because of an application code issue in `backend/app/models/__init__.py`.

Current error:

```text
ImportError: cannot import name 'Decimal' from 'sqlalchemy'
```

`Decimal` should come from Python's `decimal` module, not from `sqlalchemy`.

Until that code issue is fixed, the debugger may launch and then stop during app startup.

## Useful commands

Start the app manually from the backend folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify key packages:

```powershell
.\.venv\Scripts\python.exe -c "import fastapi, uvicorn; print(fastapi.__version__); print(uvicorn.__version__)"
```
