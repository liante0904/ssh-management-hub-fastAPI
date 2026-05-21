"""
Auth Router — Telegram 인증

POST /api/auth/telegram → Telegram Login Widget 데이터 검증 → JWT 발급
"""
import hashlib
import hmac
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from .admin import JWT_SECRET_KEY, JWT_ALGORITHM

load_dotenv()

logger = logging.getLogger("management-hub.auth")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TelegramUser(BaseModel):
    id: int
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int = 0
    hash: str = ""


def verify_telegram(data: dict) -> tuple[bool, str]:
    """Telegram Login Widget hash 검증"""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN is not configured"

    check_hash = data.get("hash")
    if not check_hash:
        return False, "Missing Telegram hash"

    data_list = [f"{k}={v}" for k, v in sorted(data.items()) if k != "hash" and v is not None]
    data_check_string = "\n".join(data_list)
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, check_hash):
        return False, "Telegram signature mismatch"
    return True, ""


def create_jwt(user_id: int) -> str:
    from jose import jwt
    return jwt.encode({"sub": str(user_id), "type": "access"}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@router.post("/telegram")
async def auth_telegram(user_data: TelegramUser, db: Session = Depends(get_db)):
    """Telegram 인증 → JWT 발급 (관리자만 허용)"""

    # 1. Telegram hash 검증
    is_valid, reason = verify_telegram(user_data.model_dump())
    if not is_valid:
        logger.warning("Telegram auth rejected: user_id=%s, reason=%s", user_data.id, reason)
        raise HTTPException(status_code=401, detail=f"Telegram Auth Failed: {reason}")

    # 2. DB upsert
    existing = db.execute(
        text("SELECT id, is_admin FROM tbm_sec_reports_telegram_users WHERE id = :uid"),
        {"uid": user_data.id},
    ).first()

    if existing:
        db.execute(
            text(
                "UPDATE tbm_sec_reports_telegram_users "
                "SET first_name = :fn, last_name = :ln, username = :un, photo_url = :pu WHERE id = :uid"
            ),
            {"fn": user_data.first_name, "ln": user_data.last_name,
             "un": user_data.username, "pu": user_data.photo_url, "uid": user_data.id},
        )
    else:
        db.execute(
            text(
                "INSERT INTO tbm_sec_reports_telegram_users (id, first_name, last_name, username, photo_url) "
                "VALUES (:uid, :fn, :ln, :un, :pu)"
            ),
            {"uid": user_data.id, "fn": user_data.first_name, "ln": user_data.last_name,
             "un": user_data.username, "pu": user_data.photo_url},
        )
    db.commit()

    # 3. admin 체크
    row = db.execute(
        text("SELECT id, status, is_admin FROM tbm_sec_reports_telegram_users WHERE id = :uid"),
        {"uid": user_data.id},
    ).first()

    is_admin = row.is_admin if row else False

    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="관리자 권한이 필요합니다. 관리자에게 승인을 요청하세요.",
        )

    # 4. JWT 발급
    token = create_jwt(user_data.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": row.id, "status": row.status, "is_admin": row.is_admin},
    }


@router.get("/me")
async def auth_me(
    db: Session = Depends(get_db),
    current_user: dict = Depends(__import__("app.routers.admin", fromlist=["get_current_admin"]).get_current_admin),
):
    """현재 로그인된 관리자 정보"""
    row = db.execute(
        text("SELECT id, first_name, last_name, username, status, is_admin FROM tbm_sec_reports_telegram_users WHERE id = :uid"),
        {"uid": current_user["user_id"]},
    ).first()
    if not row:
        raise HTTPException(status_code=404)
    return {"id": row.id, "first_name": row.first_name, "last_name": row.last_name,
            "username": row.username, "status": row.status, "is_admin": row.is_admin}
