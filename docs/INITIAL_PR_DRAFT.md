# PR Title
Initial import of ZYRAA project management platform

## Summary
- add the initial full-stack ZYRAA codebase to the new repository
- include the FastAPI backend, Next.js frontend, SQL schema, and setup documentation
- establish the base structure for projects, boards, issues, authentication, and agent workflows

## What Changed
- added `backend/` with the FastAPI application, API routes, models, schemas, services, and environment example
- added `frontend/` with the Next.js app, authenticated flows, dashboards, boards, issue views, and shared API client
- added `database/schema.sql` for the initial SQL Server schema and seed-style reference data
- added project documentation including `README.md`, setup notes, and supporting docs
- added repository ignore rules so local caches, build output, and editor files stay out of the initial commit

## Why
This PR seeds the new repository with the first working version of the application so future development can happen in a clean shared codebase instead of ad hoc local copies.

## Testing
- setup documentation reviewed for backend, frontend, and database bootstrap flow
- repository structure checked to confirm required app, database, and docs folders are present
- automated test execution was not run from this session

## Notes
- this is best treated as the initial import PR for the repository
- recommended follow-up work: add CI, automated backend tests, frontend test coverage, and deployment configuration
