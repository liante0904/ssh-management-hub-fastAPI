"""admin 라우터 테스트 — /admin/health, /admin/metrics"""
import pytest
from fastapi.testclient import TestClient


class TestAdminHealth:
    """비인증 헬스체크"""

    def test_admin_health_returns_ok(self, client: TestClient):
        res = client.get("/admin/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "management-hub"

    def test_root_health_returns_ok(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"


class TestAdminMetrics:
    """인증 필요 — /admin/metrics"""

    def test_metrics_requires_auth(self, client_unauthorized: TestClient):
        """mock auth 없으면 403 (dependency override 안 함 → 실제 JWT 검증 실패)"""
        # client_unauthorized 는 DB만 override, auth는 override 안 함
        # FastAPI 의존성 주입 체계상 get_current_admin 이 실패함
        res = client_unauthorized.get("/admin/metrics")
        # 실제 JWT_SECRET_KEY 가 설정되어 있지 않으면 503, 설정되어 있으면 401
        assert res.status_code in (401, 403, 503)

    def test_metrics_with_admin_auth(self, client: TestClient):
        """admin 인증 mock → 200"""
        res = client.get("/admin/metrics")
        assert res.status_code == 200
        data = res.json()
        assert data["overall"] in ("online", "degraded")
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert "database" in data
        assert "reports" in data
        assert data["reports"]["total"] >= 0

    def test_metrics_contains_oci2(self, client: TestClient):
        """oci2 서버 메트릭 필드 포함 여부 확인 (mocking subprocess)"""
        from unittest.mock import patch, MagicMock
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="%Cpu(s): 10.0 us\nMem: 8000000000 4000000000 2000000000\n/dev/sda1 50000000000 10000000000 40000000000 20% /"
            )
            res = client.get("/admin/metrics")
            assert res.status_code == 200
            data = res.json()
            assert "oci2" in data
            if data["oci2"]:
                assert "cpu_percent" in data["oci2"]
                assert "total_gb" in data["oci2"]

    def test_metrics_contains_oci(self, client: TestClient):
        """OCI (배포서버) 메트릭 필드 포함 여부 확인 (mocking subprocess)"""
        from unittest.mock import patch, MagicMock
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="%Cpu(s): 5.0 us\nMem: 4000000000 1500000000 2500000000\n/dev/sda1 30000000000 8000000000 22000000000 25% /"
            )
            res = client.get("/admin/metrics")
            assert res.status_code == 200
            data = res.json()
            assert "oci" in data
            if data["oci"]:
                assert "cpu_percent" in data["oci"]
                assert "total_gb" in data["oci"]
                assert "disk_percent" in data["oci"]

    def test_metrics_oci_offline_when_ssh_fails(self, client: TestClient):
        """OCI SSH 연결 실패 시 None 반환"""
        from unittest.mock import patch, MagicMock
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Connection refused")
            res = client.get("/admin/metrics")
            assert res.status_code == 200
            data = res.json()
            assert "oci" in data
            assert data["oci"] is None

    def test_metrics_oci2_offline_when_ssh_fails(self, client: TestClient):
        """OCI2 SSH 연결 실패 시 None 반환"""
        from unittest.mock import patch, MagicMock
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Connection refused")
            res = client.get("/admin/metrics")
            assert res.status_code == 200
            data = res.json()
            assert "oci2" in data
            assert data["oci2"] is None

    def test_list_db_tables(self, client: TestClient):
        """DB 테이블 목록 조회"""
        res = client.get("/admin/db/tables")
        assert res.status_code == 200
        assert "tables" in res.json()
        assert len(res.json()["tables"]) > 0

    def test_query_db_table(self, client: TestClient):
        """특정 테이블 데이터 조회"""
        res = client.get("/admin/db/query/tbl_sec_reports")
        assert res.status_code == 200
        data = res.json()
        assert data["table"] == "tbl_sec_reports"
        assert "columns" in data
        assert "data" in data


class TestAdminLogs:
    """로그 브라우징"""

    def test_logs_root_list(self, client: TestClient):
        """로그 디렉토리 최상위 목록"""
        res = client.get("/admin/logs")
        assert res.status_code in (200, 404)  # 마운트 경로가 없으면 404도 OK

    def test_logs_view_invalid_file(self, client: TestClient):
        """존재하지 않는 파일 조회 시 404"""
        res = client.get("/admin/logs/view?file=/nonexistent/file.log")
        assert res.status_code == 404

    def test_logs_invalid_path(self, client: TestClient):
        """유효하지 않은 디렉토리 경로"""
        res = client.get("/admin/logs?path=/nonexistent/dir")
        assert res.status_code == 404
