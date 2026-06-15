"""
공통 DB 세션 — ssh_library 기반 credential + pool 관리
fallback: ssh_library 없으면 env-only (기존 동작 유지)
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ── ssh_library 연동 (external.reports-hub 와 동일한 패턴) ──
_SSH_LIB = None
for _root in [
    os.path.expanduser("~/workspace/lib/ssh_library"),
    os.path.expanduser("~/workspace/lib/ssh-library"),
    "/opt/ssh-library",
]:
    if _root and os.path.isdir(_root) and _root not in sys.path:
        sys.path.insert(0, _root)
        try:
            from ssh_library.database import get_sqlalchemy_engine, get_session_factory
            _SSH_LIB = True
            break
        except ImportError:
            sys.path.remove(_root)

if _SSH_LIB:
    engine = get_sqlalchemy_engine(
        db_name=os.getenv("POSTGRES_DB", "ssh_reports_hub"),
        user=os.getenv("POSTGRES_USER", "ssh_reports_hub"),
    )
    SessionLocal = get_session_factory(engine=engine)
else:
    # fallback: ssh_library 없으면 env-only
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    PG_USER = os.getenv("POSTGRES_USER", "ssh_reports_hub")
    PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    PG_HOST = os.getenv("POSTGRES_HOST", "main-postgres")
    PG_PORT = os.getenv("POSTGRES_PORT", "5432")
    PG_DB = os.getenv("POSTGRES_DB", "ssh_reports_hub")
    DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
