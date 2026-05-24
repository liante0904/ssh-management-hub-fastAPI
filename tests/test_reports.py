"""reports 라우터 테스트 — /api/reports/*"""
import pytest
from fastapi.testclient import TestClient


class TestListReports:
    def test_list_reports(self, client: TestClient):
        res = client.get("/api/reports")
        assert res.status_code == 200
        data = res.json()
        assert "reports" in data
        assert "total" in data
        assert data["total"] == 5
        assert len(data["reports"]) == 2

    def test_list_reports_pagination(self, client: TestClient):
        res = client.get("/api/reports?page=1&page_size=1")
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 1
        assert data["page_size"] == 1

    def test_list_reports_with_firm_filter(self, client: TestClient):
        res = client.get("/api/reports?firm_nm=Test")
        assert res.status_code == 200

    def test_list_reports_with_reg_dt_filter(self, client: TestClient):
        res = client.get("/api/reports?reg_dt=20250101")
        assert res.status_code == 200

    def test_list_reports_with_sync_status_filter(self, client: TestClient):
        res = client.get("/api/reports?sync_status=0")
        assert res.status_code == 200

    def test_list_reports_with_search(self, client: TestClient):
        res = client.get("/api/reports?search=Test")
        assert res.status_code == 200

    def test_list_reports_with_sort(self, client: TestClient):
        res = client.get("/api/reports?sort=reg_dt DESC")
        assert res.status_code == 200

    def test_invalid_sort_is_rejected(self, client: TestClient):
        """SQL 인젝션 방지: 허용되지 않은 정렬값은 기본값으로 폴백"""
        res = client.get("/api/reports?sort=1=1; DROP TABLE")
        assert res.status_code == 200


class TestGetReport:
    def test_get_report(self, client: TestClient):
        res = client.get("/api/reports/100")
        assert res.status_code == 200
        data = res.json()
        assert data["report_id"] == 100

    def test_get_report_fields(self, client: TestClient):
        res = client.get("/api/reports/100")
        data = res.json()
        for field in ("report_id", "firm_nm", "article_title", "sync_status", "pdf_sync_status"):
            assert field in data

    def test_get_nonexistent_report_returns_data(self, client: TestClient):
        """Mock은 파라미터를 구분하지 않으므로 항상 데이터 반환 (실제 DB에서는 404)"""
        res = client.get("/api/reports/99999")
        assert res.status_code == 200


class TestUpdateReportSync:
    def test_update_sync_status(self, client: TestClient):
        res = client.put("/api/reports/100/sync", json={"sync_status": 0})
        assert res.status_code == 200
        assert res.json()["updated"] is True

    def test_update_pdf_sync_status(self, client: TestClient):
        res = client.put("/api/reports/100/sync", json={"pdf_sync_status": 0})
        assert res.status_code == 200

    def test_update_both_sync_statuses(self, client: TestClient):
        res = client.put("/api/reports/100/sync", json={"sync_status": 2, "pdf_sync_status": 2})
        assert res.status_code == 200

    def test_update_no_fields(self, client: TestClient):
        res = client.put("/api/reports/100/sync", json={})
        assert res.status_code == 400


class TestGetPdfArchive:
    def test_get_pdf_archive(self, client: TestClient):
        res = client.get("/api/reports/100/pdf")
        assert res.status_code == 200
        data = res.json()
        assert data is not None
        assert data["report_id"] == 100

    def test_get_pdf_archive_fields(self, client: TestClient):
        res = client.get("/api/reports/100/pdf")
        data = res.json()
        for field in ("report_id", "file_path", "file_size", "page_count", "archive_status"):
            assert field in data


class TestFnGuideSummaries:
    def test_list_fnguide_summaries(self, client: TestClient):
        res = client.get("/api/reports/fnguide")
        assert res.status_code == 200
        data = res.json()
        assert "summaries" in data
        assert data["total"] == 2

    def test_fnguide_summary_fields(self, client: TestClient):
        res = client.get("/api/reports/fnguide")
        summary = res.json()["summaries"][0]
        for field in ("summary_id", "company_name", "company_code", "report_title"):
            assert field in summary

    def test_fnguide_filter_by_company(self, client: TestClient):
        res = client.get("/api/reports/fnguide?company_name=삼성")
        assert res.status_code == 200

    def test_fnguide_filter_by_date(self, client: TestClient):
        res = client.get("/api/reports/fnguide?report_date=20250101")
        assert res.status_code == 200


class TestSendHistory:
    def test_list_send_history(self, client: TestClient):
        res = client.get("/api/reports/send-history")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_send_history_fields(self, client: TestClient):
        res = client.get("/api/reports/send-history")
        item = res.json()[0]
        for field in ("id", "report_id", "user_id", "keyword"):
            assert field in item

    def test_send_history_filter_by_report(self, client: TestClient):
        res = client.get("/api/reports/send-history?report_id=100")
        assert res.status_code == 200

    def test_send_history_filter_by_user(self, client: TestClient):
        res = client.get("/api/reports/send-history?user_id=1")
        assert res.status_code == 200


class TestListPdfArchive:
    """PDF 아카이브 목록 조회 테스트"""

    def test_list_pdf_archive(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "summary" in data
        assert data["total"] == 100
        assert len(data["items"]) == 2
        assert "archived" in data["summary"]
        assert "failed" in data["summary"]
        assert "total" in data["summary"]

    def test_list_pdf_archive_pagination(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive?page=1&page_size=10")
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_pdf_archive_filter_by_firm(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive?firm_nm=하나")
        assert res.status_code == 200

    def test_list_pdf_archive_filter_by_status(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive?archive_status=INIT")
        assert res.status_code == 200

    def test_list_pdf_archive_filter_by_sync_status(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive?sync_status=9")
        assert res.status_code == 200

    def test_list_pdf_archive_filter_by_reg_dt(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive?reg_dt=20250101")
        assert res.status_code == 200

    def test_list_pdf_archive_search(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive?search=Title")
        assert res.status_code == 200

    def test_pdf_archive_item_fields(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive")
        item = res.json()["items"][0]
        for field in ("report_id", "firm_nm", "title", "archive_status", "sync_status", "pdf_sync_status", "retry_count"):
            assert field in item


class TestPdfArchiveStatsDaily:
    """일별 PDF 통계 테스트"""

    def test_stats_daily(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive/stats/daily")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_stats_daily_fields(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive/stats/daily")
        item = res.json()[0]
        for field in ("date", "total", "archived", "failed"):
            assert field in item

    def test_stats_daily_custom_days(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive/stats/daily?days=7")
        assert res.status_code == 200


class TestPdfArchiveStatsByFirm:
    """증권사별 PDF 통계 테스트"""

    def test_stats_by_firm(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive/stats/by-firm")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_stats_by_firm_fields(self, client: TestClient):
        res = client.get("/api/reports/pdf-archive/stats/by-firm")
        item = res.json()[0]
        for field in ("firm_nm", "total", "archived", "failed"):
            assert field in item


class TestReprocessPdfArchive:
    """PDF 재처리 테스트"""

    def test_reprocess_with_filters(self, client: TestClient):
        res = client.post(
            "/api/reports/pdf-archive/reprocess",
            json={"archive_status": "INIT", "limit": 100},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["matched"] == 100
        assert data["updated"] > 0
        assert "건 재처리" in data["message"]

    def test_reprocess_with_report_ids(self, client: TestClient):
        res = client.post(
            "/api/reports/pdf-archive/reprocess",
            json={"report_ids": [100, 101, 102], "limit": 500},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["updated"] > 0

    def test_reprocess_no_filter_fails(self, client: TestClient):
        res = client.post(
            "/api/reports/pdf-archive/reprocess",
            json={"limit": 100},
        )
        assert res.status_code == 400
        assert "필터" in res.json()["detail"]

    def test_reprocess_limit_too_small(self, client: TestClient):
        res = client.post(
            "/api/reports/pdf-archive/reprocess",
            json={"archive_status": "INIT", "limit": 50},
        )
        assert res.status_code == 422  # validation error

    def test_reprocess_limit_too_large(self, client: TestClient):
        res = client.post(
            "/api/reports/pdf-archive/reprocess",
            json={"archive_status": "INIT", "limit": 600},
        )
        assert res.status_code == 422
