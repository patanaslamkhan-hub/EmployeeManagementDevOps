from datetime import datetime, timedelta, timezone

import app as app_module


def test_admin_session_expires_after_inactivity(tmp_path, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "DATABASE",
        str(tmp_path / "security_test.db")
    )

    app_module.init_db()

    app_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    client = app_module.app.test_client()

    # Simulate an administrator session inactive for 31 minutes.
    with client.session_transaction() as session:
        session["admin_id"] = 1
        session["admin_username"] = app_module.admin_username
        session["last_activity"] = (
            datetime.now(timezone.utc) - timedelta(minutes=31)
        ).isoformat()

    response = client.get("/", follow_redirects=False)

    # The administrator must be redirected to login.
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # The expired session must no longer be authenticated.
    with client.session_transaction() as session:
        assert "admin_id" not in session

import pytest


@pytest.mark.rate_limit
def test_login_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "DATABASE",
        str(tmp_path / "rate_limit_test.db")
    )

    app_module.init_db()

    app_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    # Use a unique IP to isolate this test
    client = app_module.app.test_client()

    responses = []

    for _ in range(6):
        response = client.post(
            "/login",
            data={
                "username": "invalid_user",
                "password": "invalid_password"
            },
            environ_overrides={
                "REMOTE_ADDR": "192.0.2.123"
            }
        )

        responses.append(response.status_code)

    assert 429 not in responses[:5]
    assert responses[5] == 429


@pytest.mark.rate_limit
def test_username_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "DATABASE",
        str(tmp_path / "username_rate_limit_test.db")
    )

    app_module.init_db()

    app_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    client = app_module.app.test_client()

    usernames = [
        "security_test_user",
        "SECURITY_TEST_USER",
        " Security_Test_User ",
        "security_test_user",
        "SECURITY_TEST_USER",
        "security_test_user"
    ]

    responses = []

    for index, username in enumerate(usernames):
        response = client.post(
            "/login",
            data={
                "username": username,
                "password": "invalid_password"
            },
            environ_overrides={
                "REMOTE_ADDR": f"198.51.100.{index + 1}"
            }
        )

        responses.append(response.status_code)

    assert responses[:5] == [200] * 5
    assert responses[5] == 429

    # A different username should have an independent limit.
    response = client.post(
        "/login",
        data={
            "username": "another_security_test_user",
            "password": "invalid_password"
        },
        environ_overrides={
            "REMOTE_ADDR": "198.51.100.7"
        }
    )

    assert response.status_code == 200
