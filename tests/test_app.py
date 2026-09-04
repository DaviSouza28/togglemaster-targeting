import importlib
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/testdb",
    )
    monkeypatch.setenv(
        "AUTH_SERVICE_URL",
        "http://auth-service",
    )

    fake_pool = MagicMock()

    monkeypatch.setattr(
        "psycopg2.pool.SimpleConnectionPool",
        lambda *args, **kwargs: fake_pool,
    )

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)

    return module


def test_health_returns_ok(app_module):
    client = app_module.app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_rules_requires_authorization(app_module):
    client = app_module.app.test_client()

    response = client.get("/rules/test-flag")

    assert response.status_code == 401
    assert "error" in response.get_json()


def test_invalid_api_key_returns_401(app_module, monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 401

    monkeypatch.setattr(
        app_module.requests,
        "get",
        MagicMock(return_value=fake_response),
    )

    client = app_module.app.test_client()

    response = client.get(
        "/rules/test-flag",
        headers={"Authorization": "Bearer invalid-test-key"},
    )

    assert response.status_code == 401
    assert "error" in response.get_json()


def test_update_rule_with_dynamic_sql(app_module, monkeypatch):
    auth_response = MagicMock()
    auth_response.status_code = 200

    monkeypatch.setattr(
        app_module.requests,
        "get",
        MagicMock(return_value=auth_response),
    )

    fake_cursor = MagicMock()
    fake_cursor.rowcount = 1
    fake_cursor.fetchone.return_value = {
        "flag_name": "checkout-v2",
        "is_enabled": True,
        "rules": {"country": "BR"},
    }

    fake_connection = MagicMock()
    fake_connection.cursor.return_value = fake_cursor

    app_module.pool.getconn.return_value = fake_connection

    client = app_module.app.test_client()

    response = client.put(
        "/rules/checkout-v2",
        headers={"Authorization": "Bearer valid-test-key"},
        json={
            "rules": {"country": "BR"},
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["flag_name"] == "checkout-v2"
    assert response.get_json()["is_enabled"] is True

    fake_cursor.execute.assert_called_once()
    fake_connection.commit.assert_called_once()
