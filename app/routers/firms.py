"""
Firms Router — 증권사(Securities Firm) 정보 관리 API

tbm_sec_firm_info     : 증권사 마스터 (firm_nm, telegram_update_yn)
tbm_sec_firm_board_info: 증권사별 게시판 카테고리 (board_nm, board_cd, label_nm)

컬럼은 information_schema에서 동적으로 조회 → DB 스키마 변경에 자동 대응
"""
from __future__ import annotations

import logging
from functools import lru_cache
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
# 동적 컬럼 매핑 — DB 스키마 변경에 자동 대응
# ---------------------------------------------------------------------------

# Pydantic 필드명 → 예상 DB 컬럼명 (소문자). 실제 컬럼 존재 여부는 _get_columns() 로 확인
_FIRM_PYDANTIC_TO_DB = {
    "sec_firm_order": "sec_firm_order",
    "firm_nm": "firm_nm",
    "telegram_update_yn": "telegram_update_yn",
    "COMMENT_PDF_URL": "comment_pdf_url",
    "ga_enabled_yn": "ga_enabled_yn",
}

_BOARD_PYDANTIC_TO_DB = {
    "sec_firm_order": "sec_firm_order",
    "article_board_order": "article_board_order",
    "board_nm": "board_nm",
    "board_cd": "board_cd",
    "label_nm": "label_nm",
}


def _get_columns(db: Session, table_name: str, pydantic_to_db: dict) -> tuple[list[str], list[str], dict[str, str]]:
    """
    information_schema에서 실제 존재하는 컬럼만 조회.
    Returns: (db_cols_ordered, pydantic_fields_ordered, db_to_pydantic_map)
    """
    try:
        rows = db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :tbl "
                "ORDER BY ordinal_position"
            ),
            {"tbl": table_name},
        ).fetchall()
    except Exception:
        logger.warning("Failed to query information_schema for %s, using fallback", table_name)
        rows = []

    actual_cols = {r[0] for r in rows}

    db_cols = []
    pydantic_fields = []
    db_to_pydantic = {}

    for pydantic_field, db_col in pydantic_to_db.items():
        if db_col in actual_cols:
            db_cols.append(db_col)
            pydantic_fields.append(pydantic_field)
            db_to_pydantic[db_col] = pydantic_field

    if not db_cols:
        # fallback: 모든 매핑 사용
        db_cols = list(pydantic_to_db.values())
        pydantic_fields = list(pydantic_to_db.keys())
        db_to_pydantic = {v: k for k, v in pydantic_to_db.items()}

    return db_cols, pydantic_fields, db_to_pydantic


def _row_to_dict(db_cols: list[str], pydantic_fields: list[str], row) -> dict:
    """DB row → {pydantic_field: value} dict"""
    return {pydantic_fields[i]: row[i] for i in range(len(pydantic_fields))}


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
    """증권사 목록 조회 (컬럼 동적 조회)"""
    db_cols, pydantic_fields, _ = _get_columns(db, "tbm_sec_firm_info", _FIRM_PYDANTIC_TO_DB)
    col_str = ", ".join(db_cols)

    if search:
        rows = db.execute(
            text(
                f"SELECT {col_str} FROM tbm_sec_firm_info "
                f"WHERE firm_nm ILIKE :search ORDER BY sec_firm_order"
            ),
            {"search": f"%{search}%"},
        ).fetchall()
    else:
        rows = db.execute(
            text(f"SELECT {col_str} FROM tbm_sec_firm_info ORDER BY sec_firm_order")
        ).fetchall()

    return [FirmInfoOut(**_row_to_dict(db_cols, pydantic_fields, r)) for r in rows]


@router.get("/{sec_firm_order}", response_model=FirmInfoOut)
async def get_firm(
    sec_firm_order: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 상세"""
    db_cols, pydantic_fields, _ = _get_columns(db, "tbm_sec_firm_info", _FIRM_PYDANTIC_TO_DB)
    col_str = ", ".join(db_cols)

    row = db.execute(
        text(
            f"SELECT {col_str} FROM tbm_sec_firm_info "
            f"WHERE sec_firm_order = :oid"
        ),
        {"oid": sec_firm_order},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Firm not found")
    return FirmInfoOut(**_row_to_dict(db_cols, pydantic_fields, row))


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

    # body 필드 중 DB에 실제 존재하는 컬럼만 사용
    db_cols, pydantic_fields, _ = _get_columns(db, "tbm_sec_firm_info", _FIRM_PYDANTIC_TO_DB)
    insert_cols = []
    insert_params = []
    params = {}
    for p_field in pydantic_fields:
        if p_field == "sec_firm_order":
            continue  # 아래에서 별도 처리
        val = getattr(body, p_field, None)
        if val is not None:
            db_col = _FIRM_PYDANTIC_TO_DB[p_field]
            insert_cols.append(db_col)
            insert_params.append(f":{p_field}")
            params[p_field] = val

    db.execute(
        text(
            f"INSERT INTO tbm_sec_firm_info (sec_firm_order, {', '.join(insert_cols)}) "
            f"VALUES (:oid, {', '.join(insert_params)})"
        ),
        {"oid": body.sec_firm_order, **params},
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
    db_cols, pydantic_fields, _ = _get_columns(db, "tbm_sec_firm_info", _FIRM_PYDANTIC_TO_DB)

    for p_field in pydantic_fields:
        if p_field == "sec_firm_order":
            continue
        val = getattr(body, p_field, None)
        if val is not None:
            db_col = _FIRM_PYDANTIC_TO_DB[p_field]
            updates.append(f"{db_col} = :{p_field}")
            params[p_field] = val

    if updates:
        db.execute(
            text(f"UPDATE tbm_sec_firm_info SET {', '.join(updates)} WHERE sec_firm_order = :oid"),
            params,
        )
        db.commit()

    return {"sec_firm_order": sec_firm_order, "updated": True}


@router.delete("/{sec_firm_order}")
async def delete_firm(
    sec_firm_order: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 삭제"""
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
    db_cols, pydantic_fields, _ = _get_columns(db, "tbm_sec_firm_board_info", _BOARD_PYDANTIC_TO_DB)
    col_str = ", ".join(db_cols)

    rows = db.execute(
        text(
            f"SELECT {col_str} FROM tbm_sec_firm_board_info "
            f"WHERE sec_firm_order = :oid ORDER BY article_board_order"
        ),
        {"oid": sec_firm_order},
    ).fetchall()
    return [FirmBoardOut(**_row_to_dict(db_cols, pydantic_fields, r)) for r in rows]


@router.post("/{sec_firm_order}/boards", status_code=201)
async def create_firm_board(
    sec_firm_order: int,
    body: FirmBoardCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사 게시판 추가"""
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

    db_cols, pydantic_fields, _ = _get_columns(db, "tbm_sec_firm_board_info", _BOARD_PYDANTIC_TO_DB)
    insert_cols = []
    insert_params = []
    params = {}
    for p_field in pydantic_fields:
        val = getattr(body, p_field, None)
        if val is not None:
            db_col = _BOARD_PYDANTIC_TO_DB[p_field]
            insert_cols.append(db_col)
            insert_params.append(f":{p_field}")
            params[p_field] = val

    db.execute(
        text(f"INSERT INTO tbm_sec_firm_board_info ({', '.join(insert_cols)}) VALUES ({', '.join(insert_params)})"),
        params,
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
    db_cols, pydantic_fields, _ = _get_columns(db, "tbm_sec_firm_board_info", _BOARD_PYDANTIC_TO_DB)

    for p_field in pydantic_fields:
        if p_field in ("sec_firm_order", "article_board_order"):
            continue
        val = getattr(body, p_field, None)
        if val is not None:
            db_col = _BOARD_PYDANTIC_TO_DB[p_field]
            updates.append(f"{db_col} = :{p_field}")
            params[p_field] = val

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
