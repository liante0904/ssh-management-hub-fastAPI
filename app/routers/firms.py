"""
Firms Router — 증권사(Securities Firm) 정보 관리 API

tbm_sec_firm_info     : 증권사 마스터 (firm_nm, telegram_update_yn)
tbm_sec_firm_board_info: 증권사별 게시판 카테고리 (board_nm, board_cd, label_nm)
"""
from __future__ import annotations

import logging
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from .admin import get_current_admin

load_dotenv()

logger = logging.getLogger("management-hub.firms")


# ---------------------------------------------------------------------------
# Schemas — Firm Info
# ---------------------------------------------------------------------------

class FirmInfoOut(BaseModel):
    sec_firm_order: int
    firm_nm: str
    telegram_update_yn: Optional[str] = "N"
    COMMENT_PDF_URL: Optional[str] = None
    ga_enabled_yn: str = "N"


class FirmInfoCreate(BaseModel):
    sec_firm_order: int
    firm_nm: str
    telegram_update_yn: Optional[str] = "N"
    COMMENT_PDF_URL: Optional[str] = None
    ga_enabled_yn: Optional[str] = "N"


class FirmInfoUpdate(BaseModel):
    firm_nm: Optional[str] = None
    telegram_update_yn: Optional[str] = None
    COMMENT_PDF_URL: Optional[str] = None
    ga_enabled_yn: Optional[str] = None


# ---------------------------------------------------------------------------
# Schemas — Firm Board Info
# ---------------------------------------------------------------------------

class FirmBoardOut(BaseModel):
    sec_firm_order: int
    article_board_order: int
    board_nm: Optional[str] = None
    board_cd: Optional[str] = None
    label_nm: Optional[str] = None


class FirmBoardCreate(BaseModel):
    sec_firm_order: int
    article_board_order: int
    board_nm: Optional[str] = None
    board_cd: Optional[str] = None
    label_nm: Optional[str] = None


class FirmBoardUpdate(BaseModel):
    board_nm: Optional[str] = None
    board_cd: Optional[str] = None
    label_nm: Optional[str] = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/firms", tags=["firms"])

# ── Firm Info ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[FirmInfoOut])
async def list_firms(
    search: Optional[str] = Query(None, description="증권사명 검색"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 목록 조회"""
    if search:
        rows = db.execute(
            text(
                "SELECT sec_firm_order, firm_nm, telegram_update_yn, \"COMMENT_PDF_URL\", ga_enabled_yn "
                "FROM tbm_sec_firm_info WHERE firm_nm ILIKE :search ORDER BY sec_firm_order"
            ),
            {"search": f"%{search}%"},
        ).fetchall()
    else:
        rows = db.execute(
            text(
                "SELECT sec_firm_order, firm_nm, telegram_update_yn, \"COMMENT_PDF_URL\", ga_enabled_yn "
                "FROM tbm_sec_firm_info ORDER BY sec_firm_order"
            )
        ).fetchall()
    return [FirmInfoOut(sec_firm_order=r[0], firm_nm=r[1], telegram_update_yn=r[2], COMMENT_PDF_URL=r[3], ga_enabled_yn=r[4]) for r in rows]


@router.get("/{sec_firm_order}", response_model=FirmInfoOut)
async def get_firm(
    sec_firm_order: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 상세"""
    row = db.execute(
        text(
            "SELECT sec_firm_order, firm_nm, telegram_update_yn, \"COMMENT_PDF_URL\", ga_enabled_yn "
            "FROM tbm_sec_firm_info WHERE sec_firm_order = :oid"
        ),
        {"oid": sec_firm_order},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Firm not found")
    return FirmInfoOut(sec_firm_order=row[0], firm_nm=row[1], telegram_update_yn=row[2], COMMENT_PDF_URL=row[3], ga_enabled_yn=row[4])


@router.post("", status_code=201)
async def create_firm(
    body: FirmInfoCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 신규 등록"""
    existing = db.execute(
        text("SELECT 1 FROM tbm_sec_firm_info WHERE sec_firm_order = :oid"),
        {"oid": body.sec_firm_order},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Firm already exists")

    db.execute(
        text(
            "INSERT INTO tbm_sec_firm_info (sec_firm_order, firm_nm, telegram_update_yn, \"COMMENT_PDF_URL\", ga_enabled_yn) "
            "VALUES (:oid, :firm_nm, :telegram_update_yn, :COMMENT_PDF_URL, :ga_enabled_yn)"
        ),
        {
            "oid": body.sec_firm_order,
            "firm_nm": body.firm_nm,
            "telegram_update_yn": body.telegram_update_yn,
            "COMMENT_PDF_URL": body.COMMENT_PDF_URL,
            "ga_enabled_yn": body.ga_enabled_yn,
        },
    )
    db.commit()
    return {"sec_firm_order": body.sec_firm_order, "created": True}


@router.put("/{sec_firm_order}")
async def update_firm(
    sec_firm_order: int,
    body: FirmInfoUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 정보 수정"""
    existing = db.execute(
        text("SELECT 1 FROM tbm_sec_firm_info WHERE sec_firm_order = :oid"),
        {"oid": sec_firm_order},
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Firm not found")

    updates = []
    params = {"oid": sec_firm_order}
    for field in ("firm_nm", "telegram_update_yn", "\"COMMENT_PDF_URL\"", "ga_enabled_yn"):
        val = getattr(body, field.replace('"', ''), None)
        if val is not None:
            clean_field = field.replace('"', '')
            updates.append(f"{field} = :{clean_field}")
            params[clean_field] = val

    if updates:
        db.execute(text(f"UPDATE tbm_sec_firm_info SET {', '.join(updates)} WHERE sec_firm_order = :oid"), params)
        db.commit()

    return {"sec_firm_order": sec_firm_order, "updated": True}


@router.delete("/{sec_firm_order}")
async def delete_firm(
    sec_firm_order: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 삭제"""
    # 보드 정보도 함께 삭제
    db.execute(text("DELETE FROM tbm_sec_firm_board_info WHERE sec_firm_order = :oid"), {"oid": sec_firm_order})
    result = db.execute(text("DELETE FROM tbm_sec_firm_info WHERE sec_firm_order = :oid"), {"oid": sec_firm_order})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Firm not found")
    return {"sec_firm_order": sec_firm_order, "deleted": True}


# ── Firm Board Info ────────────────────────────────────────────────────────

@router.get("/{sec_firm_order}/boards", response_model=list[FirmBoardOut])
async def list_firm_boards(
    sec_firm_order: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사별 게시판 목록"""
    rows = db.execute(
        text(
            "SELECT sec_firm_order, article_board_order, board_nm, board_cd, label_nm "
            "FROM tbm_sec_firm_board_info WHERE sec_firm_order = :oid ORDER BY article_board_order"
        ),
        {"oid": sec_firm_order},
    ).fetchall()
    return [FirmBoardOut(sec_firm_order=r[0], article_board_order=r[1], board_nm=r[2], board_cd=r[3], label_nm=r[4]) for r in rows]


@router.post("/{sec_firm_order}/boards", status_code=201)
async def create_firm_board(
    sec_firm_order: int,
    body: FirmBoardCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 게시판 추가"""
    # 증권사 존재 확인
    firm = db.execute(
        text("SELECT 1 FROM tbm_sec_firm_info WHERE sec_firm_order = :oid"), {"oid": sec_firm_order}
    ).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")

    existing = db.execute(
        text(
            "SELECT 1 FROM tbm_sec_firm_board_info "
            "WHERE sec_firm_order = :oid AND article_board_order = :boid"
        ),
        {"oid": sec_firm_order, "boid": body.article_board_order},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Board already exists for this firm")

    db.execute(
        text(
            "INSERT INTO tbm_sec_firm_board_info (sec_firm_order, article_board_order, board_nm, board_cd, label_nm) "
            "VALUES (:oid, :boid, :board_nm, :board_cd, :label_nm)"
        ),
        {
            "oid": sec_firm_order,
            "boid": body.article_board_order,
            "board_nm": body.board_nm,
            "board_cd": body.board_cd,
            "label_nm": body.label_nm,
        },
    )
    db.commit()
    return {"sec_firm_order": sec_firm_order, "article_board_order": body.article_board_order, "created": True}


@router.put("/{sec_firm_order}/boards/{article_board_order}")
async def update_firm_board(
    sec_firm_order: int,
    article_board_order: int,
    body: FirmBoardUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """게시판 정보 수정"""
    existing = db.execute(
        text(
            "SELECT 1 FROM tbm_sec_firm_board_info "
            "WHERE sec_firm_order = :oid AND article_board_order = :boid"
        ),
        {"oid": sec_firm_order, "boid": article_board_order},
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Board not found")

    updates = []
    params = {"oid": sec_firm_order, "boid": article_board_order}
    for field in ("board_nm", "board_cd", "label_nm"):
        val = getattr(body, field, None)
        if val is not None:
            updates.append(f"{field} = :{field}")
            params[field] = val

    if updates:
        db.execute(
            text(
                f"UPDATE tbm_sec_firm_board_info SET {', '.join(updates)} "
                f"WHERE sec_firm_order = :oid AND article_board_order = :boid"
            ),
            params,
        )
        db.commit()

    return {"sec_firm_order": sec_firm_order, "article_board_order": article_board_order, "updated": True}


@router.delete("/{sec_firm_order}/boards/{article_board_order}")
async def delete_firm_board(
    sec_firm_order: int,
    article_board_order: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """게시판 삭제"""
    result = db.execute(
        text(
            "DELETE FROM tbm_sec_firm_board_info "
            "WHERE sec_firm_order = :oid AND article_board_order = :boid"
        ),
        {"oid": sec_firm_order, "boid": article_board_order},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Board not found")
    return {"sec_firm_order": sec_firm_order, "article_board_order": article_board_order, "deleted": True}
