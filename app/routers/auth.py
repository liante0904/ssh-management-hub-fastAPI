"""
Auth Router — Telegram 인증

POST /api/auth/telegram → Telegram Login Widget 데이터 검증 → JWT 발급
"""
import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..rate_limit import limiter
from .admin import JWT_SECRET_KEY, JWT_ALGORITHM

load_dotenv()

logger = logging.getLogger("management-hub.auth")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    secret: str


class TelegramUser(BaseModel):
    id: int
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int = 0
    hash: str = ""
    id_token: str | None = None  # 호환용 입력 필드; 검증되지 않은 토큰은 인증에 사용하지 않음


def verify_telegram(data: dict) -> tuple[bool, str]:
    """Telegram Login Widget hash 검증"""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN is not configured"

    check_hash = data.get("hash")
    if not check_hash:
        return False, "Missing Telegram hash"
    auth_date = data.get("auth_date", 0)
    now = time.time()
    if not isinstance(auth_date, (int, float)) or auth_date <= 0:
        return False, "Missing Telegram auth_date"
    if auth_date - now > 60 or now - auth_date > 86400:
        return False, "Telegram auth data is expired"

    # hash 계산에 사용할 데이터만 추출 (None이나 빈 값 제외, hash 필드 제외)
    data_list = []
    for k, v in sorted(data.items()):
        if k == "hash" or v is None or v == "":
            continue
        # auth_date가 0인 경우(기본값)도 실제 텔레그램 데이터가 아닐 확률이 높으므로 제외
        if k == "auth_date" and v == 0:
            continue
        data_list.append(f"{k}={v}")
    
    data_check_string = "\n".join(data_list)
    logger.debug(f"Telegram data_check_string:\n{data_check_string}")
    
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, check_hash):
        logger.error(f"Hash mismatch! Expected: {expected_hash}, Received: {check_hash}")
        return False, "Telegram signature mismatch"
    return True, ""


def create_jwt(user_id: int) -> str:
    from jose import jwt
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "type": "access", "iat": int(now.timestamp()), "exp": int((now + timedelta(hours=8)).timestamp())}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@router.post("/telegram")
async def auth_telegram(user_data: TelegramUser, db: Session = Depends(get_db)):
    """Telegram 인증 → JWT 발급 (관리자만 허용)"""

    # 1. Telegram hash is always required; an unverified OIDC token is not an authenticator.
    is_valid, reason = verify_telegram(user_data.model_dump(exclude={"id_token"}))
    if not is_valid:
        logger.warning("Telegram auth rejected: user_id=%s, reason=%s", user_data.id, reason)
        raise HTTPException(status_code=401, detail=f"Telegram Auth Failed: {reason}")

    # 2. DB upsert
    existing = db.execute(
        text("SELECT id, is_admin FROM tbl_sec_reports_telegram_users WHERE id = :uid"),
        {"uid": user_data.id},
    ).first()

    if existing:
        db.execute(
            text(
                "UPDATE tbl_sec_reports_telegram_users "
                "SET first_name = :fn, last_name = :ln, username = :un, photo_url = :pu WHERE id = :uid"
            ),
            {"fn": user_data.first_name, "ln": user_data.last_name,
             "un": user_data.username, "pu": user_data.photo_url, "uid": user_data.id},
        )
    else:
        db.execute(
            text(
                "INSERT INTO tbl_sec_reports_telegram_users (id, first_name, last_name, username, photo_url) "
                "VALUES (:uid, :fn, :ln, :un, :pu)"
            ),
            {"uid": user_data.id, "fn": user_data.first_name, "ln": user_data.last_name,
             "un": user_data.username, "pu": user_data.photo_url},
        )
    db.commit()

    # 3. admin 체크
    row = db.execute(
        text("SELECT id, status, is_admin FROM tbl_sec_reports_telegram_users WHERE id = :uid"),
        {"uid": user_data.id},
    ).first()

    is_active = row[1] == "active" if row else False
    is_admin = row[2] if row else False

    if not is_active or not is_admin:
        raise HTTPException(
            status_code=403,
            detail="활성화된 관리자 권한이 필요합니다. 관리자에게 승인을 요청하세요.",
        )

    # 4. JWT 발급
    token = create_jwt(user_data.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": row[0], "status": row[1], "is_admin": row[2]},
    }


@router.post("/login")
@limiter.limit("5/minute")
async def emergency_login(request: Request, body: LoginRequest):
    """비상 JWT Secret Key 로그인"""
    if not JWT_SECRET_KEY:
        raise HTTPException(status_code=503, detail="JWT secret not configured")
    if not hmac.compare_digest(body.secret, JWT_SECRET_KEY):
        logger.warning("Emergency login rejected: invalid secret")
        raise HTTPException(status_code=401, detail="Invalid secret key")

    # admin용 JWT 발급 (sub="admin"으로 admin bypass)
    from jose import jwt as jose_jwt
    now = datetime.now(timezone.utc)
    token = jose_jwt.encode(
        {"sub": "admin", "type": "access", "iat": int(now.timestamp()), "exp": int((now + timedelta(hours=8)).timestamp())},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    logger.info("Emergency admin login successful")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": 0, "first_name": "Admin", "is_admin": True},
    }


@router.get("/me")
async def auth_me(
    db: Session = Depends(get_db),
    current_user: dict = Depends(__import__("app.routers.admin", fromlist=["get_current_admin"]).get_current_admin),
):
    """현재 로그인된 관리자 정보"""
    row = db.execute(
        text("SELECT id, first_name, last_name, username, status, is_admin FROM tbl_sec_reports_telegram_users WHERE id = :uid"),
        {"uid": current_user["user_id"]},
    ).first()
    if not row:
        raise HTTPException(status_code=404)
    return {"id": row[0], "first_name": row[1], "last_name": row[2],
            "username": row[3], "status": row[4], "is_admin": row[5]}
