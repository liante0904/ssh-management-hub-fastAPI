"""
Admin Router — 시스템 메트릭, 로그 브라우징 등 관리자 전용 API
JWT 인증 기반 (Telegram Login → JWT 발급)
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional

import psutil
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db

load_dotenv()

logger = logging.getLogger("management-hub.admin")

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"

LOG_DIRS = [
    ("/host-logs",           "날짜별 로그 (scheduler, scraper 등)"),
    ("/host-scraper-logs",   "스크래퍼 전용 로그"),
]

# ---------------------------------------------------------------------------
# 의존성
# ---------------------------------------------------------------------------

def decode_token(token: str) -> dict:
    """JWT 토큰 디코딩"""
    if not JWT_SECRET_KEY:
        raise HTTPException(status_code=503, detail="JWT secret not configured")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/telegram")


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """JWT 검증 + User DB 조회 + admin 체크"""
    payload = decode_token(token)
    user_id = payload["sub"]

    # login 엔드포인트에서 발급된 admin token
    if user_id == "admin":
        return {"user_id": 0, "is_admin": True}

    try:
        result = db.execute(
            text("SELECT id, is_admin FROM tbl_sec_reports_telegram_users WHERE id = :uid"),
            {"uid": int(user_id)},
        ).first()
    except Exception as e:
        logger.warning("DB query failed: %s", e)
        raise HTTPException(status_code=503, detail="Database unavailable")

    if result is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not result.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"user_id": result.id, "is_admin": result.is_admin}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def health_check(current_user: dict = Depends(get_current_admin)):
    return {"status": "ok", "service": "management-hub", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/metrics")
async def get_system_metrics(current_user: dict = Depends(get_current_admin)):
    """시스템 메트릭 (CPU, RAM, Disk, DB 상태, 레포트 통계)"""
    # --- CPU ---
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    cpu_freq_mhz = round(cpu_freq.current, 1) if cpu_freq else None

    # --- Memory ---
    mem = psutil.virtual_memory()
    mem_total_gb = round(mem.total / (1024 ** 3), 2)
    mem_used_gb = round(mem.used / (1024 ** 3), 2)
    mem_percent = mem.percent

    # --- Disk ---
    disk_path = os.getenv("DISK_CHECK_PATH", "/")
    try:
        disk = psutil.disk_usage(disk_path)
        disk_total_gb = round(disk.total / (1024 ** 3), 1)
        disk_used_gb = round(disk.used / (1024 ** 3), 1)
        disk_percent = disk.percent
    except Exception:
        disk_total_gb = disk_used_gb = disk_percent = 0

    # --- Uptime ---
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_days = round((datetime.now() - boot_time).total_seconds() / 86400, 1)

    # --- DB health ---
    db_ok = False
    db_latency_ms = None
    try:
        db = SessionLocal()
        t0 = time.time()
        db.execute(text("SELECT 1"))
        t1 = time.time()
        db_ok = True
        db_latency_ms = round((t1 - t0) * 1000, 1)
        db.close()
    except Exception as e:
        logger.warning("DB health check failed: %s", e)

    # --- Report stats ---
    total_reports = 0
    today_reports = 0
    last_report_time = None
    last_report_title = None
    last_report_firm = None
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT COUNT(*) FROM tbl_sec_reports")).scalar()
        total_reports = result or 0

        today_str = datetime.now().strftime("%Y%m%d")
        today_result = db.execute(
            text("SELECT COUNT(*) FROM tbl_sec_reports WHERE reg_dt = :dt"),
            {"dt": today_str},
        ).scalar()
        today_reports = today_result or 0

        latest = db.execute(
            text("SELECT save_time, article_title, firm_nm FROM tbl_sec_reports ORDER BY save_time DESC LIMIT 1")
        ).first()
        if latest:
            last_report_time = latest[0]
            last_report_title = latest[1]
            last_report_firm = latest[2]
        db.close()
    except Exception as e:
        logger.warning("Report stats query failed: %s", e)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": "online" if db_ok else "degraded",
        "system": {
            "hostname": os.uname().nodename,
            "uptime_days": uptime_days,
            "python_version": __import__("sys").version,
        },
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
            "frequency_mhz": cpu_freq_mhz,
        },
        "memory": {
            "total_gb": mem_total_gb,
            "used_gb": mem_used_gb,
            "percent": mem_percent,
        },
        "disk": {
            "total_gb": disk_total_gb,
            "used_gb": disk_used_gb,
            "percent": disk_percent,
        },
        "oci": get_oci_metrics(),
        "oci2": get_oci2_metrics(),
        "database": {
            "status": "online" if db_ok else "offline",
            "latency_ms": db_latency_ms,
        },
        "reports": {
            "total": total_reports,
            "today_inserts": today_reports,
        },
        "last_activity": {
            "last_save_time": last_report_time,
            "last_title": last_report_title,
            "last_firm": last_report_firm,
        },
    }


def get_oci2_metrics():
    """oci2 서버의 메트릭을 SSH로 수집 (환경변수로 설정)"""
    # 환경변수에서 SSH 접속 정보 가져오기
    oci2_host = os.getenv("OCI2_SSH_HOST", "oci2")
    oci2_user = os.getenv("OCI2_SSH_USER", "")  # 빈 값이면 ~/.ssh/config 사용
    oci2_key  = os.getenv("OCI2_SSH_KEY", "")   # 빈 값이면 기본 키 사용
    oci2_port = os.getenv("OCI2_SSH_PORT", "22")
    oci2_timeout = int(os.getenv("OCI2_SSH_TIMEOUT", "5"))

    # SSH 옵션 구성
    ssh_opts = "-o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes"
    if oci2_key:
        ssh_opts += f" -i {oci2_key}"
    if oci2_port != "22":
        ssh_opts += f" -p {oci2_port}"

    # SSH 대상: user@host 또는 host만 (config 사용 시)
    if oci2_user:
        ssh_target = f"{oci2_user}@{oci2_host}"
    else:
        ssh_target = oci2_host

    # 원격 명령어 (LC_ALL=C로 영어 출력 강제)
    remote_cmd = "LC_ALL=C top -bn1 | head -n 5; LC_ALL=C free -b; LC_ALL=C df -B1 / | tail -1"

    try:
        cmd = f"ssh {ssh_opts} {ssh_target} '{remote_cmd}'"
        logger.info("OCI2 SSH command: %s", cmd)

        res = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=oci2_timeout
        )

        if res.returncode != 0:
            stderr = res.stderr.strip() if res.stderr else "(no stderr)"
            logger.warning("OCI2 SSH failed (exit=%d): %s", res.returncode, stderr[:300])
            return None

        output = res.stdout
        if not output.strip():
            logger.warning("OCI2 SSH returned empty output")
            return None

        metrics = {}

        # CPU
        cpu_match = re.search(r"%Cpu\(s\):\s+([\d.]+)\s+us", output)
        metrics["cpu_percent"] = float(cpu_match.group(1)) if cpu_match else 0.0

        # Memory (free -b 출력에서 Mem:/메모리: 라인 파싱)
        mem_match = re.search(r"(?:Mem|메모리):\s+(\d+)\s+(\d+)\s+(\d+)", output)
        if mem_match:
            total = int(mem_match.group(1))
            used  = int(mem_match.group(2))
            metrics["total_gb"] = round(total / (1024**3), 2)
            metrics["used_gb"] = round(used / (1024**3), 2)
            metrics["percent"] = round((used / total) * 100, 1) if total > 0 else 0.0

        # Disk
        disk_line = output.strip().split("\n")[-1]
        disk_parts = disk_line.split()
        if len(disk_parts) >= 5:
            try:
                total = int(disk_parts[1])
                used = int(disk_parts[2])
                metrics["disk_total_gb"] = round(total / (1024**3), 1)
                metrics["disk_used_gb"] = round(used / (1024**3), 1)
                metrics["disk_percent"] = int(disk_parts[4].replace("%", ""))
            except (ValueError, IndexError):
                pass

        return metrics if metrics else None

    except FileNotFoundError:
        logger.warning("SSH command not found on this system")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("OCI2 SSH timed out after %ds", oci2_timeout)
        return None
    except Exception as e:
        logger.warning("OCI2 SSH unexpected error: %s", e)
        return None


def get_oci_metrics():
    """OCI (배포서버=자기자신) 메트릭을 로컬 psutil로 수집"""
    try:
        import psutil as _psutil
    except ImportError:
        logger.warning("psutil not installed, skipping OCI metrics")
        return None

    try:
        cpu = _psutil.cpu_percent(interval=0.3)
        mem = _psutil.virtual_memory()
        disk = _psutil.disk_usage("/")
        return {
            "cpu_percent": round(cpu, 1),
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": round(mem.percent, 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_percent": round(disk.percent, 1),
        }
    except Exception as e:
        logger.warning("OCI local psutil failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# DB 테이블 뷰어
# ---------------------------------------------------------------------------


@router.get("/db/tables")
async def list_db_tables(
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """DB 테이블 목록 조회 (관리자용)"""
    rows = db.execute(
        text(
            "SELECT t.table_name, pg_catalog.obj_description(c.oid, 'pg_class') AS comment "
            "FROM information_schema.tables t "
            "JOIN pg_catalog.pg_class c ON c.relname = t.table_name "
            "AND c.relnamespace = (SELECT oid FROM pg_catalog.pg_namespace WHERE nspname = 'public') "
            "WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE' "
            "ORDER BY t.table_name"
        )
    ).fetchall()

    result = [{"name": r[0], "comment": r[1]} for r in rows]
    return {"tables": result}


@router.get("/db/query/{table}")
async def query_db_table(
    table: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: Optional[str] = Query(None),
    order_dir: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """특정 테이블 데이터 미리보기 (Read-only)"""
    # SQL Injection 방지를 위한 테이블명 검증
    allowed_tables = [
        r[0]
        for r in db.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        ).fetchall()
    ]

    if table not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table name")

    # ORDER BY 검증 (SQL Injection 방지)
    order_clause = ""
    if order_by:
        # 컬럼명은 실제 테이블 컬럼으로만 제한
        try:
            col_check = db.execute(text(f"SELECT * FROM {table} LIMIT 0"))
            allowed_cols = list(col_check.keys())
        except Exception:
            allowed_cols = []
        if order_by in allowed_cols:
            direction = "ASC" if (order_dir or "ASC").upper() == "ASC" else "DESC"
            order_clause = f" ORDER BY {order_by} {direction}"
        else:
            raise HTTPException(status_code=400, detail=f"Invalid column: {order_by}")

    try:
        query = f"SELECT * FROM {table}{order_clause} LIMIT :limit OFFSET :offset"
        res = db.execute(text(query), {"limit": limit, "offset": offset})
        columns = list(res.keys())
        data = [_serialize_row(columns, row) for row in res.fetchall()]

        # Fetch column comments
        col_comments = {}
        try:
            comment_rows = db.execute(
                text(
                    "SELECT a.attname AS column_name, pg_catalog.col_description(c.oid, a.attnum) AS comment "
                    "FROM pg_catalog.pg_attribute a "
                    "JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
                    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relname = :tbl_name "
                    "AND a.attnum > 0 AND NOT a.attisdropped "
                    "ORDER BY a.attnum"
                ),
                {"tbl_name": table},
            ).fetchall()
            for cr in comment_rows:
                if cr[1]:
                    col_comments[cr[0]] = cr[1]
        except Exception:
            pass

        return {
            "table": table,
            "columns": columns,
            "column_comments": col_comments,
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_msg = str(e)
        logger.error(
            "DB query failed for table=%s limit=%s offset=%s order_by=%s: %s\nTRACEBACK:\n%s",
            table, limit, offset, order_by, err_msg, traceback.format_exc(),
        )

        if "permission denied" in err_msg.lower():
            raise HTTPException(
                status_code=403,
                detail=f"접근 권한이 없습니다: {table} 테이블에 대한 SELECT 권한이 필요합니다.",
            )
        if "does not exist" in err_msg.lower() or "not found" in err_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"테이블이 존재하지 않습니다: {table}",
            )
        if "can't adapt type" in err_msg.lower() or "cannot adapt" in err_msg.lower():
            raise HTTPException(
                status_code=500,
                detail=f"지원되지 않는 데이터 타입이 있습니다 ({table}). 관리자에게 문의하세요.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"쿼리 실패 ({table}): {err_msg[:200]}",
        )


class CommentRequest(BaseModel):
    table_name: str = Field(..., description="테이블명")
    comment: str = Field("", description="코멘트 (빈 문자열이면 삭제)")
    column_name: Optional[str] = Field(None, description="컬럼명 (지정 시 컬럼 코멘트)")


@router.put("/db/comment")
async def update_db_comment(
    body: CommentRequest,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """테이블/컬럼 코멘트 수정 (관리자용)"""
    # Validate table exists
    allowed = [
        r[0]
        for r in db.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        ).fetchall()
    ]
    if body.table_name not in allowed:
        raise HTTPException(status_code=400, detail="Invalid table name")

    try:
        if body.column_name:
            # Validate column exists
            cols = [
                r[0]
                for r in db.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = :tbl"
                    ),
                    {"tbl": body.table_name},
                ).fetchall()
            ]
            if body.column_name not in cols:
                raise HTTPException(status_code=400, detail=f"Invalid column: {body.column_name}")

            sql = f"COMMENT ON COLUMN {body.table_name}.{body.column_name} IS :comment"
        else:
            sql = f"COMMENT ON TABLE {body.table_name} IS :comment"

        comment_val = body.comment if body.comment else None
        db.execute(text(sql), {"comment": comment_val})
        db.commit()
        return {"ok": True, "message": "코멘트가 업데이트되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Comment update failed: %s", e)
        raise HTTPException(status_code=500, detail=f"코멘트 수정 실패: {str(e)[:200]}")


# 직렬화 최대 재귀 깊이 (중첩된 jsonb/array 방어)
_MAX_SERIALIZE_DEPTH = 10


def _serialize_value(val, _depth=0):
    """단일 값을 JSON 직렬화 가능한 타입으로 재귀 변환"""
    import math
    import uuid as _uuid
    from datetime import date as _date, datetime as _dt, time as _time, timedelta as _td
    from decimal import Decimal as _Decimal

    if val is None:
        return None

    # ── 스칼라 기본형 (가장 흔한 케이스를 먼저) ──
    if isinstance(val, (bool, int, str)):
        return val

    # ── float: NaN/Inf 처리 ──
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None  # JSON 표준에 맞게 null로 변환
        return val

    # ── 날짜/시간 ──
    if isinstance(val, (_dt, _date, _time)):
        return val.isoformat()

    # ── timedelta (PostgreSQL INTERVAL) ──
    if isinstance(val, _td):
        return str(val)

    # ── Decimal → float (NaN/Inf 처리 포함) ──
    if isinstance(val, _Decimal):
        if val.is_nan() or val.is_infinite():
            return None
        return float(val)

    # ── UUID ──
    if isinstance(val, _uuid.UUID):
        return str(val)

    # ── bytes / binary ──
    if isinstance(val, (bytes, bytearray, memoryview)):
        return f"<binary:{len(val)} bytes>"

    # ── 재귀 깊이 초과 방어 ──
    if _depth >= _MAX_SERIALIZE_DEPTH:
        try:
            return str(val)
        except Exception:
            return f"<max_depth:{type(val).__name__}>"

    # ── PostgreSQL array → Python list (재귀 변환) ──
    if isinstance(val, list):
        return [_serialize_value(item, _depth + 1) for item in val]

    # ── PostgreSQL JSONB / composite type → dict ──
    if isinstance(val, dict):
        return {str(k): _serialize_value(v, _depth + 1) for k, v in val.items()}

    # ── tuple 등 기타 시퀀스 → list로 변환 ──
    if isinstance(val, tuple):
        return [_serialize_value(item, _depth + 1) for item in val]

    # ── set / frozenset → list ──
    if isinstance(val, (set, frozenset)):
        return [_serialize_value(item, _depth + 1) for item in sorted(val, key=str)]

    # ── isoformat이 있는 기타 타입 (예: pendulum, arrow 등) ──
    if hasattr(val, "isoformat"):
        try:
            return val.isoformat()
        except Exception:
            pass

    # ── 최종 fallback: str() ──
    try:
        return str(val)
    except Exception:
        return f"<unserializable: {type(val).__name__}>"


def _serialize_row(columns, row):
    """JSON 직렬화 가능한 타입으로 변환 (datetime, Decimal, bytes, UUID, PG array, JSONB 등)"""
    result = {}
    for col, val in zip(columns, row):
        try:
            result[col] = _serialize_value(val)
        except Exception as exc:
            logger.warning("Serialize failed for column=%s type=%s: %s", col, type(val).__name__, exc)
            result[col] = f"<serialize_error: {type(val).__name__}>"
    return result


class SqlQueryRequest(BaseModel):
    query: str = Field(..., description="SELECT 쿼리 (읽기 전용)")
    limit: int = Field(50, ge=1, le=200)


@router.post("/db/query")
async def run_sql_query(
    body: SqlQueryRequest,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """커스텀 SQL 쿼리 실행 (SELECT only, 읽기 전용)"""
    sql = body.query.strip()
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="SELECT 쿼리만 허용됩니다")

    dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
    for kw in dangerous:
        if kw in sql.upper():
            raise HTTPException(status_code=400, detail=f"허용되지 않는 키워드: {kw}")

    if "LIMIT" not in sql.upper():
        sql = f"{sql.rstrip(';').strip()} LIMIT {body.limit}"

    try:
        res = db.execute(text(sql), {"limit": body.limit})
        columns = list(res.keys()) if res.returns_rows else []
        if not columns:
            return {"columns": [], "data": [], "message": "Query executed (no rows)"}
        data = [_serialize_row(columns, row) for row in res.fetchall()]
        return {"columns": columns, "data": data}
    except Exception as e:
        logger.warning("Custom SQL query failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e)[:300])


# ---------------------------------------------------------------------------
# 로그 브라우징
# ---------------------------------------------------------------------------


@router.get("/logs")
async def list_logs(
    current_user: dict = Depends(get_current_admin),
    path: Optional[str] = Query(None, description="서브 디렉토리 경로 (생략 시 최상위)"),
):
    """로그 디렉토리/파일 목록"""
    if not path:
        entries = []
        for dir_path, desc in LOG_DIRS:
            if not os.path.isdir(dir_path):
                continue
            entries.append({
                "name": os.path.basename(dir_path),
                "full_path": dir_path,
                "type": "directory",
                "description": desc,
            })
            try:
                subs = sorted(
                    [f for f in os.listdir(dir_path)
                     if os.path.isdir(os.path.join(dir_path, f)) and f.isdigit()],
                    reverse=True,
                )[:5]
                for sub in subs:
                    sub_path = os.path.join(dir_path, sub)
                    entries.append({
                        "name": sub,
                        "full_path": sub_path,
                        "type": "directory",
                        "description": f"날짜 로그 ({sub})",
                        "parent": os.path.basename(dir_path),
                    })
            except PermissionError:
                pass
        return {"entries": entries, "current_path": None}

    req_path = path
    if not os.path.exists(req_path):
        raise HTTPException(status_code=404, detail="Path not found")
    if not os.path.isdir(req_path):
        raise HTTPException(status_code=400, detail="Not a directory")

    def safe_size(fp: str) -> str:
        try:
            sz = os.path.getsize(fp)
            if sz < 1024: return f"{sz} B"
            elif sz < 1024 * 1024: return f"{sz / 1024:.1f} KB"
            else: return f"{sz / (1024 * 1024):.1f} MB"
        except OSError: return "-"

    def safe_mtime(fp: str) -> str:
        try:
            return datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%m/%d %H:%M")
        except OSError: return "-"

    entries = []
    try:
        items = sorted(os.listdir(req_path))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    for item in items:
        if item.startswith("."):
            continue
        full = os.path.join(req_path, item)
        try:
            is_dir = os.path.isdir(full)
        except OSError:
            continue
        entry = {
            "name": item,
            "full_path": full,
            "type": "directory" if is_dir else "file",
            "size": safe_size(full) if not is_dir else None,
            "modified": safe_mtime(full),
        }
        if item.endswith(".zip"):
            entry["archived"] = True
        entries.append(entry)

    entries.sort(key=lambda e: (0 if e["type"] == "directory" else 1, e["name"]))
    return {"entries": entries, "current_path": req_path}


@router.get("/logs/view")
async def view_log_file(
    current_user: dict = Depends(get_current_admin),
    file: str = Query(..., description="로그 파일 절대경로"),
    lines: int = Query(500, ge=10, le=5000),
    offset: int = Query(0, ge=0),
    tail: bool = Query(False, description="끝에서 N라인 조회"),
):
    """로그 파일 내용 반환"""
    file_path = file
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail="Not a file")
    if file_path.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Cannot view archived (.zip) files")

    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        raise HTTPException(status_code=403, detail="Cannot access file")
    if file_size > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            if tail:
                chunk_size = 8192
                f.seek(0, os.SEEK_END)
                file_end = f.tell()
                pos = max(0, file_end - chunk_size)
                newline_count = 0
                collected = []
                while pos > 0 and newline_count < lines:
                    f.seek(pos)
                    chunk = f.read(min(chunk_size, file_end - pos))
                    newline_count += chunk.count("\n")
                    collected.append(chunk)
                    pos = max(0, pos - chunk_size)
                if collected:
                    collected.reverse()
                    content = "".join(collected)
                    split = content.splitlines()
                    content = "\n".join(split[-lines:]) if len(split) > lines else content
                else:
                    content = f.read()
                return {
                    "file": file_path, "lines": lines, "tail": True,
                    "content": content, "total_bytes": file_size,
                    "total_lines_approx": content.count("\n") + 1,
                }
            else:
                all_lines = f.readlines()
                total = len(all_lines)
                start = min(offset, total)
                end = min(offset + lines, total)
                content = "".join(all_lines[start:end])
                return {
                    "file": file_path, "lines": end - start, "offset": start,
                    "tail": False, "content": content,
                    "total_bytes": file_size, "total_lines": total,
                }
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Cannot decode file as text")
    except OSError as e:
        raise HTTPException(status_code=403, detail=f"Cannot read file: {e}")
