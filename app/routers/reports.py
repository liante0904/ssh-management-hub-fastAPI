"""
Reports Router — 수집된 레포트 관리 API

- tbl_sec_reports: 레포트 목록/검색/필터/상세 (페이지네이션)
- tbl_sec_reports_pdf_archive: PDF 아카이브 상태
- tbl_fnguide_report_summaries: FnGuide 요약 목록
- tbl_report_send_history: 발송 이력
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from .admin import get_current_admin

load_dotenv()

logger = logging.getLogger("management-hub.reports")


# ---------------------------------------------------------------------------
# Schemas — Report
# ---------------------------------------------------------------------------

class ReportOut(BaseModel):
    report_id: int
    firm_nm: Optional[str] = None
    article_title: Optional[str] = None
    article_url: Optional[str] = None
    writer: Optional[str] = None
    save_time: Optional[str] = None
    reg_dt: Optional[str] = None
    mkt_tp: Optional[str] = None
    download_status_yn: Optional[str] = None
    sync_status: Optional[int] = 0
    pdf_sync_status: Optional[int] = 0
    gemini_summary: Optional[str] = None
    summary_time: Optional[str] = None
    summary_model: Optional[str] = None


class ReportListOut(BaseModel):
    reports: list[ReportOut]
    total: int
    page: int
    page_size: int


class ReportSyncUpdate(BaseModel):
    sync_status: Optional[int] = Field(None, description="0=대기, 1=처리중, 2=완료, -1=실패")
    pdf_sync_status: Optional[int] = Field(None, description="PDF 동기화 상태")


# ---------------------------------------------------------------------------
# Schemas — PDF Archive
# ---------------------------------------------------------------------------

class PdfArchiveOut(BaseModel):
    report_id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    archive_status: Optional[str] = None
    storage_backend: Optional[str] = None
    has_text: Optional[bool] = None
    is_encrypted: Optional[bool] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Schemas — FnGuide Summary
# ---------------------------------------------------------------------------

class FnGuideSummaryOut(BaseModel):
    summary_id: int
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    report_title: Optional[str] = None
    report_date: Optional[str] = None
    opinion: Optional[str] = None
    target_price: Optional[str] = None
    provider: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None


class FnGuideSummaryListOut(BaseModel):
    summaries: list[FnGuideSummaryOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Schemas — Send History
# ---------------------------------------------------------------------------

class SendHistoryOut(BaseModel):
    id: int
    report_id: int
    user_id: int
    keyword: Optional[str] = None
    sent_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Schemas — PDF Archive List / Stats / Reprocess
# ---------------------------------------------------------------------------

class PdfArchiveItemOut(BaseModel):
    """PDF 아카이브 목록 아이템"""
    report_id: int
    firm_nm: Optional[str] = None
    title: Optional[str] = None
    reg_dt: Optional[str] = None
    author: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    archive_status: Optional[str] = None
    storage_backend: Optional[str] = None
    download_status_yn: Optional[str] = None
    sync_status: Optional[int] = 0
    pdf_sync_status: Optional[int] = 0
    retry_count: Optional[int] = 0
    has_text: Optional[bool] = None
    is_encrypted: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    article_url: Optional[str] = None


class PdfArchiveSummary(BaseModel):
    total: int = 0
    archived: int = 0
    failed: int = 0


class PdfArchiveListOut(BaseModel):
    items: list[PdfArchiveItemOut]
    total: int
    page: int
    page_size: int
    summary: PdfArchiveSummary = PdfArchiveSummary()


class DailyPdfStats(BaseModel):
    date: str
    total: int
    archived: int
    failed: int


class FirmPdfStats(BaseModel):
    firm_nm: str
    total: int
    archived: int
    failed: int


class ReprocessRequest(BaseModel):
    """PDF 재처리 요청 — 필터 조건에 맞는 건들의 sync_status를 0으로 초기화"""
    archive_status: Optional[str] = Field(None, description="필터: archive_status (예: 'INIT')")
    firm_nm: Optional[str] = Field(None, description="필터: 증권사명")
    reg_dt: Optional[str] = Field(None, description="필터: 등록일자 (YYYYMMDD)")
    sync_status: Optional[int] = Field(None, description="필터: sync_status (예: 9=실패)")
    pdf_sync_status: Optional[int] = Field(None, description="필터: pdf_sync_status")
    report_ids: Optional[list[int]] = Field(None, description="특정 report_id 목록 (최대 500개)")
    limit: int = Field(100, ge=100, le=500, description="재처리 최대 건수")


class ReprocessResponse(BaseModel):
    matched: int
    updated: int
    message: str


class DiagnoseResponse(BaseModel):
    """PDF 다운로드 URL 진단 결과"""
    report_id: int
    article_url: Optional[str] = None
    reachable: bool = False
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ── tbl_sec_reports ────────────────────────────────────────────────────────

@router.get("", response_model=ReportListOut)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    firm_nm: Optional[str] = Query(None, description="증권사명 검색"),
    reg_dt: Optional[str] = Query(None, description="등록일자 (YYYYMMDD)"),
    sync_status: Optional[int] = Query(None, description="0=대기, 1=처리중, 2=완료, -1=실패"),
    search: Optional[str] = Query(None, description="제목 검색"),
    sort: Optional[str] = Query("save_time DESC", description="정렬 (save_time DESC | reg_dt DESC)"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 목록 조회 (페이지네이션 + 필터)"""
    where = []
    params: dict = {}

    if firm_nm:
        where.append("firm_nm ILIKE :firm_nm")
        params["firm_nm"] = f"%{firm_nm}%"
    if reg_dt:
        where.append("reg_dt = :reg_dt")
        params["reg_dt"] = reg_dt
    if sync_status is not None:
        where.append("sync_status = :sync_status")
        params["sync_status"] = sync_status
    if search:
        where.append("article_title ILIKE :search")
        params["search"] = f"%{search}%"

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    # sort whitelist
    allowed_sorts = {"save_time DESC", "save_time ASC", "reg_dt DESC", "reg_dt ASC", "report_id DESC", "report_id ASC"}
    sort_col = sort if sort in allowed_sorts else "save_time DESC"

    total_row = db.execute(text(f"SELECT COUNT(*) FROM tbl_sec_reports {where_clause}"), params).scalar()
    total = total_row or 0

    offset = (page - 1) * page_size
    rows = db.execute(
        text(
            f"SELECT report_id, firm_nm, article_title, article_url, writer, save_time, reg_dt, mkt_tp, "
            f"download_status_yn, sync_status, pdf_sync_status, gemini_summary, summary_time, summary_model "
            f"FROM tbl_sec_reports {where_clause} "
            f"ORDER BY {sort_col} LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()

    reports = [
        ReportOut(
            report_id=r[0], firm_nm=r[1], article_title=r[2], article_url=r[3], writer=r[4],
            save_time=r[5], reg_dt=r[6], mkt_tp=r[7], download_status_yn=r[8],
            sync_status=r[9] or 0, pdf_sync_status=r[10] or 0,
            gemini_summary=r[11], summary_time=r[12], summary_model=r[13],
        )
        for r in rows
    ]
    return ReportListOut(reports=reports, total=total, page=page, page_size=page_size)


# ── tbl_fnguide_report_summaries (必 /{report_id} 보다 앞에 위치) ──────────

@router.get("/fnguide", response_model=FnGuideSummaryListOut)
async def list_fnguide_summaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_name: Optional[str] = Query(None),
    report_date: Optional[str] = Query(None, description="YYYYMMDD"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """FnGuide 요약 목록"""
    where = []
    params: dict = {}
    if company_name:
        where.append("company_name ILIKE :company_name")
        params["company_name"] = f"%{company_name}%"
    if report_date:
        where.append("report_date = :report_date")
        params["report_date"] = report_date

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(text(f"SELECT COUNT(*) FROM tbl_fnguide_report_summaries {where_clause}"), params).scalar() or 0
    offset = (page - 1) * page_size

    rows = db.execute(
        text(
            f"SELECT summary_id, company_name, company_code, report_title, report_date, "
            f"opinion, target_price, provider, author, "
            f"to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at "
            f"FROM tbl_fnguide_report_summaries {where_clause} "
            f"ORDER BY summary_id DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()

    summaries = [
        FnGuideSummaryOut(
            summary_id=r[0], company_name=r[1], company_code=r[2], report_title=r[3],
            report_date=r[4], opinion=r[5], target_price=r[6], provider=r[7], author=r[8],
            created_at=r[9],
        )
        for r in rows
    ]
    return FnGuideSummaryListOut(summaries=summaries, total=total, page=page, page_size=page_size)


# ── tbl_report_send_history (必 /{report_id} 보다 앞에 위치) ───────────────

@router.get("/send-history", response_model=list[SendHistoryOut])
async def list_send_history(
    report_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 발송 이력"""
    where = []
    params: dict = {"limit": limit}
    if report_id:
        where.append("report_id = :report_id")
        params["report_id"] = report_id
    if user_id:
        where.append("user_id = :user_id")
        params["user_id"] = user_id

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    rows = db.execute(
        text(
            f"SELECT id, report_id, user_id, keyword, "
            f"to_char(sent_at, 'YYYY-MM-DD HH24:MI:SS') as sent_at "
            f"FROM tbl_report_send_history {where_clause} "
            f"ORDER BY id DESC LIMIT :limit"
        ),
        params,
    ).fetchall()

    return [SendHistoryOut(id=r[0], report_id=r[1], user_id=r[2], keyword=r[3], sent_at=r[4]) for r in rows]


# ── PDF Archive 관리 (必 /{report_id} 보다 앞에 위치) ────────────────────────

@router.get("/pdf-archive", response_model=PdfArchiveListOut)
async def list_pdf_archive(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    firm_nm: Optional[str] = Query(None, description="증권사명"),
    archive_status: Optional[str] = Query(None, description="ARCHIVED / INIT"),
    reg_dt: Optional[str] = Query(None, description="등록일자 YYYYMMDD"),
    sync_status: Optional[int] = Query(None, description="0=대기, 2=완료, 9=실패"),
    pdf_sync_status: Optional[int] = Query(None),
    download_status_yn: Optional[str] = Query(None, description="Y/N"),
    search: Optional[str] = Query(None, description="제목 검색"),
    sort: Optional[str] = Query("report_id DESC"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """PDF 아카이브 목록 조회 — tbl_sec_reports r LEFT JOIN archive a"""
    where = []
    params: dict = {}

    if firm_nm:
        where.append("r.firm_nm ILIKE :firm_nm")
        params["firm_nm"] = f"%{firm_nm}%"
    if archive_status:
        where.append("a.archive_status = :archive_status")
        params["archive_status"] = archive_status
    if reg_dt:
        where.append("r.reg_dt = :reg_dt")
        params["reg_dt"] = reg_dt
    if sync_status is not None:
        where.append("a.sync_status = :sync_status")
        params["sync_status"] = sync_status
    if pdf_sync_status is not None:
        where.append("a.pdf_sync_status = :pdf_sync_status")
        params["pdf_sync_status"] = pdf_sync_status
    if download_status_yn:
        where.append("a.download_status_yn = :download_status_yn")
        params["download_status_yn"] = download_status_yn
    if search:
        where.append("r.article_title ILIKE :search")
        params["search"] = f"%{search}%"

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    # sort: prefix r. for reports table columns
    _raw_sort = sort
    if sort in {"report_id DESC", "report_id ASC", "reg_dt DESC", "reg_dt ASC"}:
        sort_col = f"r.{sort}"
    else:
        sort_col = "r.report_id DESC"

    # FROM 절: reports(모든 레코드) + LEFT JOIN archive(시도된 것만)
    FROM = "FROM tbl_sec_reports r LEFT JOIN tbl_sec_reports_pdf_archive a ON r.report_id = a.report_id"

    total = db.execute(text(f"SELECT COUNT(*) {FROM} {where_clause}"), params).scalar() or 0

    # Summary: 전체 집계 (필터 무관)
    # total = 모든 tbl_sec_reports, archived = archive_status='ARCHIVED' + pdf_sync 성공
    summary_total = db.execute(
        text("SELECT COUNT(*) FROM tbl_sec_reports")
    ).scalar() or 0
    summary_archived = db.execute(
        text("""
            SELECT COUNT(*) FROM tbl_sec_reports r
            INNER JOIN tbl_sec_reports_pdf_archive a ON r.report_id = a.report_id
            WHERE a.archive_status = 'ARCHIVED'
              AND COALESCE(a.pdf_sync_status, 0) NOT IN (3, 9, -1)
        """)
    ).scalar() or 0
    summary_failed = summary_total - summary_archived

    offset = (page - 1) * page_size

    rows = db.execute(
        text(
            f"SELECT r.report_id, r.firm_nm, r.article_title as title, r.reg_dt, r.article_url, "
            f"a.author, a.file_name, a.file_size, a.page_count, "
            f"a.archive_status, a.storage_backend, a.download_status_yn, "
            f"a.sync_status, a.pdf_sync_status, a.retry_count, "
            f"a.has_text, a.is_encrypted, "
            f"to_char(a.created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at, "
            f"to_char(a.updated_at, 'YYYY-MM-DD HH24:MI:SS') as updated_at "
            f"{FROM} {where_clause} "
            f"ORDER BY {sort_col} LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()

    items = [
        PdfArchiveItemOut(
            report_id=r[0], firm_nm=r[1], title=r[2], reg_dt=r[3], article_url=r[4],
            author=r[5], file_name=r[6], file_size=r[7], page_count=r[8], archive_status=r[9],
            storage_backend=r[10], download_status_yn=r[11], sync_status=r[12] or 0,
            pdf_sync_status=r[13] or 0, retry_count=r[14] or 0,
            has_text=r[15], is_encrypted=r[16], created_at=r[17], updated_at=r[18],
        )
        for r in rows
    ]
    return PdfArchiveListOut(
        items=items, total=total, page=page, page_size=page_size,
        summary=PdfArchiveSummary(total=summary_total, archived=summary_archived, failed=summary_failed),
    )


@router.get("/pdf-archive/stats/daily", response_model=list[DailyPdfStats])
async def pdf_archive_stats_daily(
    days: int = Query(30, ge=1, le=365, description="조회할 일수"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """일별 PDF 아카이브 통계 (레포트 등록일 기준, LEFT JOIN)"""
    rows = db.execute(
        text(
            "SELECT r.reg_dt as dt, "
            "COUNT(*) as total, "
            "COUNT(*) FILTER (WHERE a.archive_status = 'ARCHIVED' AND COALESCE(a.pdf_sync_status, 0) NOT IN (3, 9, -1)) as archived, "
            "COUNT(*) - COUNT(*) FILTER (WHERE a.archive_status = 'ARCHIVED' AND COALESCE(a.pdf_sync_status, 0) NOT IN (3, 9, -1)) as failed "
            "FROM tbl_sec_reports r "
            "LEFT JOIN tbl_sec_reports_pdf_archive a ON r.report_id = a.report_id "
            "WHERE r.reg_dt >= to_char(now() - (:days || ' days')::interval, 'YYYYMMDD') "
            "GROUP BY r.reg_dt ORDER BY dt DESC"
        ),
        {"days": str(days)},
    ).fetchall()
    return [DailyPdfStats(date=r[0], total=r[1], archived=r[2], failed=r[3]) for r in rows]


@router.get("/pdf-archive/stats/by-firm", response_model=list[FirmPdfStats])
async def pdf_archive_stats_by_firm(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """증권사별 PDF 아카이브 성공/실패 통계 (LEFT JOIN)"""
    rows = db.execute(
        text(
            "SELECT COALESCE(r.firm_nm, 'Unknown') as firm_nm, "
            "COUNT(*) as total, "
            "COUNT(*) FILTER (WHERE a.archive_status = 'ARCHIVED' AND COALESCE(a.pdf_sync_status, 0) NOT IN (3, 9, -1)) as archived, "
            "COUNT(*) - COUNT(*) FILTER (WHERE a.archive_status = 'ARCHIVED' AND COALESCE(a.pdf_sync_status, 0) NOT IN (3, 9, -1)) as failed "
            "FROM tbl_sec_reports r "
            "LEFT JOIN tbl_sec_reports_pdf_archive a ON r.report_id = a.report_id "
            "GROUP BY r.firm_nm ORDER BY total DESC"
        ),
    ).fetchall()
    return [FirmPdfStats(firm_nm=r[0], total=r[1], archived=r[2], failed=r[3]) for r in rows]


@router.post("/pdf-archive/reprocess", response_model=ReprocessResponse)
async def reprocess_pdf_archive(
    body: ReprocessRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """PDF 아카이브 재처리 — 필터 조건에 맞는 건들의 sync_status를 0으로 초기화 (100~500건 단위)"""
    where = []
    params: dict = {}

    if body.report_ids:
        if len(body.report_ids) > 500:
            raise HTTPException(status_code=400, detail="report_ids는 최대 500개까지 가능합니다")
        where.append("report_id = ANY(:report_ids)")
        params["report_ids"] = body.report_ids
    else:
        if body.archive_status:
            where.append("archive_status = :archive_status")
            params["archive_status"] = body.archive_status
        if body.firm_nm:
            where.append("firm_nm ILIKE :firm_nm")
            params["firm_nm"] = f"%{body.firm_nm}%"
        if body.reg_dt:
            where.append("reg_dt = :reg_dt")
            params["reg_dt"] = body.reg_dt
        if body.sync_status is not None:
            where.append("sync_status = :sync_status")
            params["sync_status"] = body.sync_status
        if body.pdf_sync_status is not None:
            where.append("pdf_sync_status = :pdf_sync_status")
            params["pdf_sync_status"] = body.pdf_sync_status

    if not where:
        raise HTTPException(status_code=400, detail="최소 하나의 필터 조건이 필요합니다")

    where_clause = "WHERE " + " AND ".join(where)

    # 매칭 건수 확인
    matched = db.execute(
        text(f"SELECT COUNT(*) FROM tbl_sec_reports_pdf_archive {where_clause}"),
        params,
    ).scalar() or 0

    if matched == 0:
        return ReprocessResponse(matched=0, updated=0, message="재처리 대상이 없습니다")

    # report_ids 직접 지정 시 LIMIT 없이 전체 업데이트, 그 외는 LIMIT 적용
    if body.report_ids:
        result = db.execute(
            text(
                f"UPDATE tbl_sec_reports_pdf_archive "
                f"SET sync_status = 0, pdf_sync_status = 0, retry_count = retry_count + 1, updated_at = now() "
                f"{where_clause}"
            ),
            params,
        )
    else:
        result = db.execute(
            text(
                f"UPDATE tbl_sec_reports_pdf_archive "
                f"SET sync_status = 0, pdf_sync_status = 0, retry_count = retry_count + 1, updated_at = now() "
                f"WHERE report_id IN ("
                f"  SELECT report_id FROM tbl_sec_reports_pdf_archive {where_clause} "
                f"  ORDER BY report_id LIMIT :limit"
                f")"
            ),
            {**params, "limit": body.limit},
        )

    db.commit()
    updated = result.rowcount

    return ReprocessResponse(
        matched=matched,
        updated=updated,
        message=f"{updated}건 재처리 요청 완료 (전체 대상: {matched}건)",
    )


@router.post("/pdf-archive/{report_id}/diagnose", response_model=DiagnoseResponse)
async def diagnose_pdf_download(
    report_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """PDF 원본 URL 접속 진단 — 서버에서 직접 URL에 접근하여 응답 상태 확인"""
    import time

    row = db.execute(
        text("SELECT article_url FROM tbl_sec_reports WHERE report_id = :rid"),
        {"rid": report_id},
    ).first()

    if not row or not row[0]:
        return DiagnoseResponse(
            report_id=report_id,
            reachable=False,
            error="article_url이 존재하지 않습니다 (레포트가 없거나 URL이 NULL)",
        )

    article_url = row[0]
    result = DiagnoseResponse(report_id=report_id, article_url=article_url)

    try:
        import httpx
    except ImportError:
        result.reachable = False
        result.error = "httpx 라이브러리가 설치되지 않았습니다"
        return result

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.head(article_url)
            elapsed = (time.monotonic() - start) * 1000

            result.reachable = resp.is_success or resp.status_code < 400
            result.http_status = resp.status_code
            result.content_type = resp.headers.get("content-type", "")
            cl = resp.headers.get("content-length")
            result.content_length = int(cl) if cl and cl.isdigit() else None
            result.elapsed_ms = round(elapsed, 1)

    except httpx.TimeoutException:
        result.reachable = False
        result.error = "연결 시간 초과 (15초)"
    except httpx.ConnectError as e:
        result.reachable = False
        result.error = f"연결 실패: {e}"
    except Exception as e:
        result.reachable = False
        result.error = f"오류: {type(e).__name__}: {e}"

    return result


# ── /{report_id} 이하 (파라미터 라우트 — 정적 경로 뒤에 위치) ──────────────


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 상세 조회"""
    row = db.execute(
        text(
            "SELECT report_id, firm_nm, article_title, article_url, writer, save_time, reg_dt, mkt_tp, "
            "download_status_yn, sync_status, pdf_sync_status, gemini_summary, summary_time, summary_model "
            "FROM tbl_sec_reports WHERE report_id = :rid"
        ),
        {"rid": report_id},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportOut(
        report_id=row[0], firm_nm=row[1], article_title=row[2], article_url=row[3], writer=row[4],
        save_time=row[5], reg_dt=row[6], mkt_tp=row[7], download_status_yn=row[8],
        sync_status=row[9] or 0, pdf_sync_status=row[10] or 0,
        gemini_summary=row[11], summary_time=row[12], summary_model=row[13],
    )


@router.put("/{report_id}/sync")
async def update_report_sync(
    report_id: int,
    body: ReportSyncUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 동기화 상태 재설정 (재처리 트리거용)"""
    updates = []
    params = {"rid": report_id}
    if body.sync_status is not None:
        updates.append("sync_status = :sync_status")
        params["sync_status"] = body.sync_status
    if body.pdf_sync_status is not None:
        updates.append("pdf_sync_status = :pdf_sync_status")
        params["pdf_sync_status"] = body.pdf_sync_status

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.execute(
        text(f"UPDATE tbl_sec_reports SET {', '.join(updates)} WHERE report_id = :rid"),
        params,
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report_id": report_id, "updated": True}


# ── tbl_sec_reports_pdf_archive ────────────────────────────────────────────

@router.get("/{report_id}/pdf", response_model=Optional[PdfArchiveOut])
async def get_report_pdf_archive(
    report_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 PDF 아카이브 상태"""
    row = db.execute(
        text(
            "SELECT report_id, file_path, file_size, page_count, archive_status, storage_backend, "
            "has_text, is_encrypted, "
            "to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at "
            "FROM tbl_sec_reports_pdf_archive WHERE report_id = :rid"
        ),
        {"rid": report_id},
    ).first()
    if not row:
        return None
    return PdfArchiveOut(
        report_id=row[0], file_path=row[1], file_size=row[2], page_count=row[3],
        archive_status=row[4], storage_backend=row[5], has_text=row[6], is_encrypted=row[7],
        created_at=row[8],
    )
