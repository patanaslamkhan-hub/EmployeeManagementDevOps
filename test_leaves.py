import pytest
import app as employee_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create an isolated database and Flask test client."""

    database_path = tmp_path / "employees_test.db"

    monkeypatch.setattr(
        employee_app,
        "DATABASE",
        str(database_path)
    )

    employee_app.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    employee_app.init_db()

    with employee_app.app.test_client() as test_client:
        with test_client.session_transaction() as session:
            session["admin_id"] = 1

        yield test_client

    employee_app.app.config["WTF_CSRF_ENABLED"] = True


def get_employee_id():
    """Return an employee from the temporary database."""

    conn = employee_app.get_db_connection()

    try:
        employee = conn.execute(
            "SELECT id FROM employees ORDER BY id LIMIT 1"
        ).fetchone()

        return employee["id"]
    finally:
        conn.close()


def get_leave_requests():
    """Retrieve all leave requests."""

    conn = employee_app.get_db_connection()

    try:
        return conn.execute(
            "SELECT * FROM leave_requests ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def submit_leave(client, **overrides):
    """Submit a valid leave request with optional overrides."""

    data = {
        "employee_id": str(get_employee_id()),
        "leave_type": "Sick",
        "start_date": "2026-11-20",
        "end_date": "2026-11-21",
        "reason": "Medical rest"
    }

    data.update(overrides)

    return client.post(
        "/leaves/apply",
        data=data,
        follow_redirects=True
    )


def test_leave_page_loads(client):
    response = client.get("/leaves")

    assert response.status_code == 200
    assert b"Employee Leave Management" in response.data


def test_submit_leave_request(client):
    response = submit_leave(client)

    assert response.status_code == 200

    requests = get_leave_requests()

    assert len(requests) == 1
    assert requests[0]["leave_type"] == "Sick"
    assert requests[0]["status"] == "Pending"
    assert requests[0]["reason"] == "Medical rest"


def test_approve_leave_request(client):
    submit_leave(client)

    leave_id = get_leave_requests()[0]["id"]

    response = client.post(
        f"/leaves/{leave_id}/status",
        data={"status": "Approved"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert get_leave_requests()[0]["status"] == "Approved"


def test_reject_leave_request(client):
    submit_leave(client)

    leave_id = get_leave_requests()[0]["id"]

    response = client.post(
        f"/leaves/{leave_id}/status",
        data={"status": "Rejected"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert get_leave_requests()[0]["status"] == "Rejected"


def test_invalid_leave_dates(client):
    response = submit_leave(
        client,
        start_date="2026-11-25",
        end_date="2026-11-20"
    )

    assert response.status_code == 200
    assert len(get_leave_requests()) == 0
    assert b"End date cannot be before start date" in response.data


def test_invalid_date_format(client):
    response = submit_leave(
        client,
        start_date="invalid-date"
    )

    assert response.status_code == 200
    assert len(get_leave_requests()) == 0


def test_invalid_leave_type(client):
    response = submit_leave(
        client,
        leave_type="Invalid"
    )

    assert response.status_code == 200
    assert len(get_leave_requests()) == 0


def test_nonexistent_employee(client):
    response = submit_leave(
        client,
        employee_id="999999"
    )

    assert response.status_code == 200
    assert len(get_leave_requests()) == 0


def test_reason_length_limit(client):
    response = submit_leave(
        client,
        reason="A" * 501
    )

    assert response.status_code == 200
    assert len(get_leave_requests()) == 0


def test_cannot_approve_twice(client):
    submit_leave(client)

    leave_id = get_leave_requests()[0]["id"]

    client.post(
        f"/leaves/{leave_id}/status",
        data={"status": "Approved"}
    )

    response = client.post(
        f"/leaves/{leave_id}/status",
        data={"status": "Rejected"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert get_leave_requests()[0]["status"] == "Approved"


def test_invalid_approval_status(client):
    submit_leave(client)

    leave_id = get_leave_requests()[0]["id"]

    response = client.post(
        f"/leaves/{leave_id}/status",
        data={"status": "Cancelled"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert get_leave_requests()[0]["status"] == "Pending"


def test_leave_page_requires_login(client):
    with client.session_transaction() as session:
        session.clear()

    response = client.get("/leaves")

    assert response.status_code == 302
    assert "/login" in response.location


def test_leave_submission_requires_login(client):
    with client.session_transaction() as session:
        session.clear()

    response = client.post(
        "/leaves/apply",
        data={
            "employee_id": "1",
            "leave_type": "Sick",
            "start_date": "2026-11-20",
            "end_date": "2026-11-21"
        }
    )

    assert response.status_code == 302
    assert "/login" in response.location
    assert len(get_leave_requests()) == 0


def test_leave_status_requires_login(client):
    submit_leave(client)

    leave_id = get_leave_requests()[0]["id"]

    with client.session_transaction() as session:
        session.clear()

    response = client.post(
        f"/leaves/{leave_id}/status",
        data={"status": "Approved"}
    )

    assert response.status_code == 302
    assert get_leave_requests()[0]["status"] == "Pending"


def test_csrf_protection(client):
    """Verify a POST without a CSRF token is rejected."""

    employee_app.app.config["WTF_CSRF_ENABLED"] = True

    response = client.post(
        "/leaves/apply",
        data={
            "employee_id": str(get_employee_id()),
            "leave_type": "Sick",
            "start_date": "2026-11-20",
            "end_date": "2026-11-21"
        }
    )

    assert response.status_code == 400
    assert len(get_leave_requests()) == 0
