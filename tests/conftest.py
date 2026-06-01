"""
공통 테스트 픽스처 — 모든 라우터 테스트에서 사용
"""
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Mock DB Session
# ---------------------------------------------------------------------------

class MockRow:
    """SQLAlchemy row 결과를 흉내내는 mock — 인덱싱 + 언패킹 지원"""
    __slots__ = ("_data",)

    def __init__(self, *args):
        self._data = args

    def __getitem__(self, idx):
        return self._data[idx]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"MockRow{self._data}"


class MockResult:
    """SQLAlchemy Result를 흉내내는 mock"""

    def __init__(self, rows, rowcount=None, keys=None):
        self._rows = rows
        self._rowcount = rowcount if rowcount is not None else len(rows)
        self._keys = keys or []

    def first(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def scalar(self):
        row = self.first()
        return row[0] if row else None

    def keys(self):
        return self._keys

    @property
    def rowcount(self):
        return self._rowcount


class MockDBSession:
    """실제 DB 연결 없이 테스트용 Session을 흉내냄"""
    def __init__(self, preset_rows=None):
        self._preset = preset_rows or {}
        self._committed = False

    def execute(self, stmt, params=None):
        stmt_lower = str(stmt).lower()
        # 단어 경계 매칭을 위해 앞뒤 공백 추가
        _w = f" {stmt_lower} "

        # ── users ──
        if "tbl_sec_reports_telegram_users" in stmt_lower:
            if " update " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif " delete " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif " insert " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif "count(*)" in stmt_lower:
                return MockResult([MockRow(3)])
            elif "id, status, is_admin" in stmt_lower.replace(" ", ""):
                return MockResult([MockRow(1, "active", True)])
            elif "id, first_name, last_name, username, status, is_admin" in stmt_lower.replace(" ", ""):
                return MockResult([MockRow(1, "John", "Doe", "johndoe", "active", True)])
            elif "id, is_admin" in stmt_lower.replace(" ", "") and "status," not in stmt_lower.replace(" ", ""):
                return MockResult([MockRow(1, True)])
            elif "where id = " in stmt_lower or "where id=" in stmt_lower.replace(" ", ""):
                return MockResult([MockRow(1, "John", "Doe", "johndoe", None, "active", True, 1700000000)])
            else:
                return MockResult([
                    MockRow(1, "John", "Doe", "johndoe", None, "active", True, 1700000000),
                    MockRow(2, "Jane", "Smith", "janesmith", None, "active", False, 1700000001),
                    MockRow(3, "Bob", "Lee", "boblee", None, "blocked", False, 1700000002),
                ])

        # ── firms ──
        if "tbm_sec_firm_info" in stmt_lower and "tbm_sec_firm_board_info" not in stmt_lower:
            if " insert " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif " update " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif " delete " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif "where sec_firm_order = " in stmt_lower.replace(" ", ""):
                return MockResult([MockRow(1, "Test Securities", "Y", None)])
            elif "select 1" in stmt_lower:
                return MockResult([MockRow(1)])
            else:
                return MockResult([
                    MockRow(1, "Test Securities", "Y", None),
                    MockRow(2, "Another Firm", "N", "https://example.com"),
                ])

        if "tbm_sec_firm_board_info" in stmt_lower:
            if " insert " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif " delete " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif " update " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif "select 1" in stmt_lower:
                return MockResult([MockRow(1)])
            else:
                return MockResult([
                    MockRow(1, 1, "Board A", "CD_A", "Label A"),
                    MockRow(1, 2, "Board B", "CD_B", "Label B"),
                ])

        # ── reports ──
        if "tbl_sec_reports" in stmt_lower and "pdf_archive" not in stmt_lower:
            if " update " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif "count(*)" in stmt_lower:
                return MockResult([MockRow(5)])
            elif "where report_id = " in stmt_lower.replace(" ", ""):
                return MockResult([MockRow(100, "Test Firm", "Test Title", "http://url", "Writer", "20250101_120000", "20250101", "KR", "Y", 2, 2, "summary...", "20250101_130000", "gemini-1.5")])
            else:
                return MockResult([
                    MockRow(100, "Test Firm", "Test Title", "http://url", "Writer", "20250101_120000", "20250101", "KR", "Y", 2, 2, "summary...", "20250101_130000", "gemini-1.5"),
                    MockRow(101, "Firm2", "Title2", "http://url2", "Writer2", "20250102_120000", "20250102", "KR", "N", 0, 0, None, None, None),
                ])

        if "tbl_sec_reports_pdf_archive" in stmt_lower:
            if " update " in _w:
                self._committed = True
                return MockResult([MockRow(1)])
            elif "count(*) filter" in stmt_lower and "group by" in stmt_lower:
                if "firm_nm" in stmt_lower:
                    return MockResult([
                        MockRow("하나증권", 100, 90, 10),
                        MockRow("KB증권", 50, 45, 5),
                    ])
                elif "created_at" in stmt_lower:
                    return MockResult([
                        MockRow("2025-01-01", 50, 45, 5),
                        MockRow("2025-01-02", 30, 28, 2),
                    ])
                elif "reg_dt" in stmt_lower:
                    # pdf_archive_stats_daily — GROUP BY r.reg_dt
                    return MockResult([
                        MockRow("20250101", 50, 45, 5),
                        MockRow("20250102", 30, 28, 2),
                    ])
                else:
                    return MockResult([MockRow(100)])
            elif "count(*)" in stmt_lower:
                if "coalesce(sync_status" in stmt_lower or ("archive_status" in stmt_lower and "not in" in stmt_lower):
                    return MockResult([MockRow(90)]) if "archived" in stmt_lower.replace(" ", "") else MockResult([MockRow(10)])
                if "archive_status = 'ARCHIVED'" in stmt_lower and "!=" not in stmt_lower:
                    return MockResult([MockRow(90)])
                elif "archive_status !=" in stmt_lower or "archive_status is null" in stmt_lower:
                    return MockResult([MockRow(10)])
                return MockResult([MockRow(100)])
            elif "report_id,firm_nm" in stmt_lower.replace(" ", "").replace("r.", ""):
                # list_pdf_archive — 19개 컬럼 (article_url 추가)
                return MockResult([
                    MockRow(100, "하나증권", "Title", "20250101", "https://example.com/report/100", "Author", "file.pdf", 1024000, 10,
                            "ARCHIVED", "onedrive", "Y", 2, 2, 0, True, False,
                            "2025-01-01 12:00:00", "2025-01-01 12:00:00"),
                    MockRow(101, "KB증권", "Title2", "20250102", "https://example.com/report/101", "Author2", "file2.pdf", 2048000, 20,
                            "INIT", "onedrive", "N", 0, 0, 3, False, True,
                            "2025-01-02 12:00:00", "2025-01-02 12:00:00"),
                ])
            elif "in (select report_id" in stmt_lower.replace(" ", ""):
                self._committed = True
                return MockResult([MockRow(10)])
            else:
                # /{report_id}/pdf 상세 조회
                return MockResult([MockRow(100, "/path/to/pdf", 1024000, 10, "archived", "onedrive", True, False, "2025-01-01 12:00:00")])

        if "tbl_fnguide_report_summaries" in stmt_lower:
            if "count(*)" in stmt_lower:
                return MockResult([MockRow(2)])
            return MockResult([
                MockRow(1, "삼성전자", "005930", "Report Title", "20250101", "BUY", "100000", "FnGuide", "Author1", "2025-01-01 12:00:00"),
                MockRow(2, "SK하이닉스", "000660", "Report Title2", "20250102", "HOLD", "200000", "FnGuide", "Author2", "2025-01-02 12:00:00"),
            ])

        if "tbl_report_send_history" in stmt_lower:
            return MockResult([
                MockRow(1, 100, 1, "삼성전자", "2025-01-01 12:00:00"),
            ])

        # ── information_schema + pg_class (DB Viewer) ──
        if "information_schema.tables" in stmt_lower:
            return MockResult([
                MockRow("tbl_sec_reports", "증권사 레포트"),
                MockRow("tbl_sec_reports_telegram_users", "텔레그램 유저"),
                MockRow("tbm_sec_firm_info", "증권사 정보"),
            ], keys=["table_name", "comment"])

        # ── Generic table query ──
        if "select * from" in stmt_lower:
            return MockResult([
                MockRow(1, "Data 1"),
                MockRow(2, "Data 2"),
            ], keys=["id", "name"])

        # ── admin / metrics ──
        if "select 1" in stmt_lower:
            return MockResult([MockRow(1)])
        if "select count(*) from" in stmt_lower:
            return MockResult([MockRow(100)])

        return MockResult([])

    def commit(self):
        self._committed = True

    def close(self):
        pass

    @property
    def rowcount(self):
        return 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """DB 세션 mock"""
    return MockDBSession()


@pytest.fixture
def client(mock_db):
    """TestClient + DB / Auth dependency override"""

    async def override_get_db():
        yield mock_db

    async def override_get_current_admin():
        return {"user_id": 1, "is_admin": True}

    app.dependency_overrides = {}
    from app.routers.admin import get_db as admin_get_db
    from app.routers.admin import get_current_admin
    from app.database import get_db as db_get_db

    # override DB
    app.dependency_overrides[db_get_db] = override_get_db
    app.dependency_overrides[admin_get_db] = override_get_db
    # override auth
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    yield TestClient(app)
    app.dependency_overrides = {}


@pytest.fixture
def client_unauthorized(mock_db):
    """TestClient — 인증 없는 요청용"""

    async def override_get_db():
        yield mock_db

    app.dependency_overrides = {}
    from app.database import get_db as db_get_db
    app.dependency_overrides[db_get_db] = override_get_db

    yield TestClient(app)
    app.dependency_overrides = {}
