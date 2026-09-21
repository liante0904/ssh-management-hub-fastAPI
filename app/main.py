"""
Management Hub FastAPI — 통합 관리 API 서버

라우터:
  - /admin/*   : 시스템 메트릭, 로그 브라우징 (System Console)
  - /api/users/*  : 텔레그램 유저 관리
  - /api/reports/*: 레포트 관리 (목록/검색/PDF/발송이력)
  - /api/firms/*  : 증권사 정보 관리
  - (추후) 데이터 후처리, 정합성 검사 등 추가
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from .routers import admin_router, auth_router, backfill_router, firms_router, reports_router, users_router
from .rate_limit import limiter

logger = logging.getLogger("management-hub")

CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "https://ssh-management-hub.netlify.app,http://localhost:5175",
    ).split(",")
    if origin.strip()
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Management Hub API starting...")
    yield
    logger.info("Management Hub API shutting down.")


app = FastAPI(
    title="Management Hub API",
    description="Internal & External 통합 데이터 관리 및 후처리 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SecurityHeadersMiddleware)

# 라우터 등록
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(users_router)
app.include_router(reports_router)
app.include_router(firms_router)
app.include_router(backfill_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "management-hub"}
