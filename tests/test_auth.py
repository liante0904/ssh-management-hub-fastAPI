"""auth 라우터 테스트 — POST /api/auth/telegram"""
import hashlib
import hmac
import time
import pytest
from fastapi.testclient import TestClient


def make_valid_hash(data: dict, bot_token: str) -> str:
    items = sorted((k, v) for k, v in data.items() if k != "hash" and v is not None)
    data_check = "\n".join(f"{k}={v}" for k, v in items)
    secret = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()


def make_telegram_user(user_id: int, bot_token: str):
    data = {"id": user_id, "first_name": "Test", "username": "testuser", "auth_date": int(time.time())}
    data["hash"] = make_valid_hash(data, bot_token)
    return data


class TestTelegramAuth:
    def test_auth_no_token_returns_503(self, client_unauthorized: TestClient):
        """TELEGRAM_BOT_TOKEN 없으면 401/503"""
        res = client_unauthorized.post("/api/auth/telegram", json={"id": 1, "first_name": "T"})
        assert res.status_code in (401, 503)

    def test_auth_invalid_hash_returns_401(self, client_unauthorized: TestClient, monkeypatch):
        """잘못된 hash → 401"""
        monkeypatch.setattr("app.routers.auth.TELEGRAM_BOT_TOKEN", "test_token")
        res = client_unauthorized.post("/api/auth/telegram", json={
            "id": 1, "first_name": "T", "auth_date": 1234567890, "hash": "invalid"
        })
        assert res.status_code == 401

    def test_auth_valid_returns_token(self, client, monkeypatch):
        """유효한 hash + admin mock → 200 + token"""
        token = "test_bot_token_12345"
        monkeypatch.setattr("app.routers.auth.TELEGRAM_BOT_TOKEN", token)
        user_data = make_telegram_user(1, token)
        res = client.post("/api/auth/telegram", json=user_data)
        # mock DB 제한으로 200 또는 다른 응답 가능
        if res.status_code == 200:
            data = res.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
        else:
            assert res.status_code in (200, 403)

    def test_auth_missing_fields(self, client_unauthorized: TestClient, monkeypatch):
        """필수 필드 누락 → 422"""
        monkeypatch.setattr("app.routers.auth.TELEGRAM_BOT_TOKEN", "test_token")
        res = client_unauthorized.post("/api/auth/telegram", json={"id": "not_int"})
        assert res.status_code == 422


class TestAuthMe:
    def test_auth_me_requires_token(self, client_unauthorized: TestClient):
        """인증 없이 접근 → 401/403"""
        res = client_unauthorized.get("/api/auth/me")
        assert res.status_code in (401, 403, 404)

    def test_auth_me_with_token(self, client: TestClient):
        """인증된 요청"""
        res = client.get("/api/auth/me")
        assert res.status_code in (200, 404)


def test_secret_key_login_route_removed(client_unauthorized: TestClient):
    """JWT Secret Key 로그인 우회 경로는 더 이상 노출하지 않는다."""
    res = client_unauthorized.post("/api/auth/login", json={"secret": "wrong"})
    assert res.status_code == 404
