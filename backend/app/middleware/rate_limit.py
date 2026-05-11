from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import ApiRateLimit


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/docs", "/openapi.json", "/health", "/"]:
            return await call_next(request)

        db: Session = SessionLocal()
        try:
            user_id = getattr(request.state, "user_id", None)
            ip_address = self._get_client_ip(request)
            endpoint = request.url.path

            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window_seconds)

            rate_limit = db.query(ApiRateLimit).filter(
                ApiRateLimit.endpoint == endpoint,
                ApiRateLimit.ip_address == ip_address,
                ApiRateLimit.window_start >= window_start
            ).first()

            if rate_limit:
                if rate_limit.request_count >= self.requests_per_minute:
                    return Response(
                        content='{"detail": "Rate limit exceeded. Please try again later."}',
                        status_code=429,
                        headers={"Retry-After": str(self.window_seconds)}
                    )
                rate_limit.request_count += 1
            else:
                rate_limit = ApiRateLimit(
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    request_count=1,
                    window_start=now
                )
                db.add(rate_limit)

            db.commit()
            response = await call_next(request)
            return response

        finally:
            db.close()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


def check_rate_limit(
    db: Session,
    user_id: Optional[int],
    ip_address: str,
    endpoint: str,
    limit: int = 60,
    window_seconds: int = 60
) -> bool:
    window_start = datetime.utcnow() - timedelta(seconds=window_seconds)

    count = db.query(ApiRateLimit).filter(
        ApiRateLimit.endpoint == endpoint,
        ApiRateLimit.ip_address == ip_address,
        ApiRateLimit.window_start >= window_start
    ).count()

    return count < limit
