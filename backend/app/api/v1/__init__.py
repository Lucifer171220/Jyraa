from fastapi import APIRouter
from app.api.v1 import agents, auth, boards, issues, projects, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(issues.router)
api_router.include_router(boards.router)
api_router.include_router(agents.router)
