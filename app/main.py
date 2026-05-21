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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel

from .routers import admin_router, auth_router, firms_router, reports_router, users_router

logger = logging.getLogger("management-hub")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    secret: str


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(users_router)
app.include_router(reports_router)
app.include_router(firms_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "management-hub"}


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    """JWT Secret Key를 입력받아 admin 토큰 발급"""
    if not JWT_SECRET_KEY:
        logger.error("Login failed: JWT_SECRET_KEY not configured")
        raise HTTPException(status_code=503, detail="JWT secret not configured")
    if body.secret != JWT_SECRET_KEY:
        logger.warning(f"Login failed: Invalid secret key attempt. (Expected first 4 chars: {JWT_SECRET_KEY[:4]}...)")
        raise HTTPException(status_code=401, detail="Invalid secret key")
    token = jwt.encode({"sub": "admin", "type": "access"}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
