"""
Unit-тесты health-check view: мокаются три приватных хелпера, проверяется
только логика view (статус-код и структура JSON-ответа).
"""

import pytest


def test_health_ok(client, mocker):
    mocker.patch("crypto.health._check_db", return_value=True)
    mocker.patch("crypto.health._check_cache", return_value=True)
    mocker.patch("crypto.health._check_celery", return_value=True)

    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"db": "ok", "cache": "ok", "celery": "ok"},
    }


@pytest.mark.parametrize(
    "failing_check, failing_key",
    [
        ("_check_db", "db"),
        ("_check_cache", "cache"),
        ("_check_celery", "celery"),
    ],
)
def test_health_degraded(client, mocker, failing_check, failing_key):
    for name in ("_check_db", "_check_cache", "_check_celery"):
        mocker.patch(f"crypto.health.{name}", return_value=name != failing_check)

    response = client.get("/health/")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["checks"][failing_key] == "fail"
