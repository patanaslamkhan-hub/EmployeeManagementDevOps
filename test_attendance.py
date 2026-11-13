import pytest
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_attendance.db"

    monkeypatch.setattr(
        app_module, "DATABASE", str(test_database)
    )
    monkeypatch.setattr(
        app_module, "admin_username", "testadmin"
    )
    monkeypatch.setattr(
        app_module, "admin_password", "testpassword"
    )

    app_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    app_module.init_db()

    with app_module.app.test_client() as test_client:
        response = test_client.post(
            "/login",
            data={
                "username": "testadmin",
                "password": "testpassword"
            }
        )
        assert response.status_code in (200, 302)
        yield test_client


def get_attendance_records():
    conn = app_module.get_db_connection()
    try:
        return conn.execute(
            """
            SELECT employee_id, attendance_date, status, remarks
            FROM attendance
            ORDER BY employee_id
            """
        ).fetchall()
    finally:
        conn.close()


def test_attendance_page(client):
    response = client.get("/attendance")

    assert response.status_code == 200
    assert b"Rahul" in response.data
    assert b"Priya" in response.data


def test_attendance_requires_login():
    with app_module.app.test_client() as test_client:
        response = test_client.get("/attendance")

        assert response.status_code == 302


def test_mark_attendance_requires_login():
    with app_module.app.test_client() as test_client:
        response = test_client.post(
            "/attendance/mark",
            data={
                "employee_id": "1",
                "attendance_date": "2026-11-13",
                "status": "Present",
                "remarks": ""
            }
        )

        assert response.status_code == 302


def test_mark_attendance(client):
    response = client.post(
        "/attendance/mark",
        data={
            "employee_id": "1",
            "attendance_date": "2026-11-13",
            "status": "Present",
            "remarks": "Arrived on time"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Attendance saved successfully." in response.data

    records = get_attendance_records()
    matching = [
        row for row in records
        if row["employee_id"] == 1
        and row["attendance_date"] == "2026-11-13"
    ]

    assert len(matching) == 1
    assert matching[0]["status"] == "Present"
    assert matching[0]["remarks"] == "Arrived on time"


def test_update_attendance_without_duplicate(client):
    for status in ("Present", "Absent"):
        response = client.post(
            "/attendance/mark",
            data={
                "employee_id": "1",
                "attendance_date": "2026-11-13",
                "status": status,
                "remarks": "Updated record"
            }
        )

        assert response.status_code == 302

    records = get_attendance_records()
    matching = [
        row for row in records
        if row["employee_id"] == 1
        and row["attendance_date"] == "2026-11-13"
    ]

    assert len(matching) == 1
    assert matching[0]["status"] == "Absent"


def test_invalid_attendance_status(client):
    response = client.post(
        "/attendance/mark",
        data={
            "employee_id": "1",
            "attendance_date": "2026-11-13",
            "status": "Unknown",
            "remarks": ""
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Please select a valid attendance status." in response.data
    assert len(get_attendance_records()) == 0


def test_invalid_attendance_date(client):
    response = client.post(
        "/attendance/mark",
        data={
            "employee_id": "1",
            "attendance_date": "invalid-date",
            "status": "Present",
            "remarks": ""
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Invalid employee or attendance date." in response.data
    assert len(get_attendance_records()) == 0


def test_invalid_attendance_filter_date(client):
    response = client.get(
        "/attendance?date=invalid-date",
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Invalid attendance date." in response.data


def test_nonexistent_employee_attendance(client):
    response = client.post(
        "/attendance/mark",
        data={
            "employee_id": "999999",
            "attendance_date": "2026-11-13",
            "status": "Present",
            "remarks": ""
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Employee not found." in response.data
    assert len(get_attendance_records()) == 0


def test_attendance_remarks_too_long(client):
    response = client.post(
        "/attendance/mark",
        data={
            "employee_id": "1",
            "attendance_date": "2026-11-13",
            "status": "Present",
            "remarks": "A" * 251
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Remarks must be 250 characters or fewer." in response.data
    assert len(get_attendance_records()) == 0


def test_attendance_date_filter(client):
    response = client.post(
        "/attendance/mark",
        data={
            "employee_id": "1",
            "attendance_date": "2026-11-13",
            "status": "Present",
            "remarks": "Specific date note"
        }
    )

    assert response.status_code == 302

    matching_date = client.get("/attendance?date=2026-11-13")
    other_date = client.get("/attendance?date=2026-11-14")

    assert matching_date.status_code == 200
    assert other_date.status_code == 200
    assert b"Specific date note" in matching_date.data
    assert b"Specific date note" not in other_date.data
