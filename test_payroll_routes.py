import pytest
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_payroll.db"

    monkeypatch.setattr(app_module, "DATABASE", str(test_database))
    monkeypatch.setattr(app_module, "admin_username", "testadmin")
    monkeypatch.setattr(app_module, "admin_password", "testpassword")

    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    app_module.init_db()

    with app_module.app.test_client() as test_client:
        response = test_client.post(
            "/login",
            data={"username": "testadmin", "password": "testpassword"},
        )
        assert response.status_code == 302
        yield test_client


def salary_data():
    return {
        "employee_id": "1",
        "basic_salary": "30000",
        "hra": "8000",
        "allowances": "2000",
        "deductions": "3000",
    }


def save_test_salary(client):
    return client.post(
        "/payroll/salary", data=salary_data(), follow_redirects=True
    )


def test_payroll_dashboard(client):
    response = client.get("/payroll")
    assert response.status_code == 200
    assert b"Payroll" in response.data


def test_save_employee_salary(client):
    response = save_test_salary(client)
    assert response.status_code == 200
    assert b"Employee salary saved successfully" in response.data


def test_update_employee_salary(client):
    save_test_salary(client)
    updated_data = salary_data()
    updated_data["basic_salary"] = "35000"
    response = client.post(
        "/payroll/salary", data=updated_data, follow_redirects=True
    )
    assert response.status_code == 200

    conn = app_module.get_db_connection()
    try:
        records = conn.execute(
            "SELECT basic_salary FROM employee_salaries WHERE employee_id = ?",
            (1,),
        ).fetchall()
        assert len(records) == 1
        assert float(records[0]["basic_salary"]) == 35000
    finally:
        conn.close()


def test_reject_negative_salary(client):
    data = salary_data()
    data["basic_salary"] = "-100"
    response = client.post(
        "/payroll/salary", data=data, follow_redirects=True
    )
    assert response.status_code == 200

    conn = app_module.get_db_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM employee_salaries"
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_generate_monthly_payroll(client):
    save_test_salary(client)
    response = client.post(
        "/payroll/generate",
        data={"employee_id": "1", "payroll_month": "2026-11"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Monthly payroll generated successfully" in response.data

    conn = app_module.get_db_connection()
    try:
        record = conn.execute(
            """
            SELECT net_salary, payment_status
            FROM payroll_records
            WHERE employee_id = ? AND payroll_month = ?
            """,
            (1, "2026-11"),
        ).fetchone()
        assert record is not None
        assert float(record["net_salary"]) == 37000
        assert record["payment_status"] == "Pending"
    finally:
        conn.close()


def test_prevent_duplicate_payroll(client):
    save_test_salary(client)
    data = {"employee_id": "1", "payroll_month": "2026-11"}
    client.post("/payroll/generate", data=data)
    response = client.post(
        "/payroll/generate", data=data, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"already exists" in response.data

    conn = app_module.get_db_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM payroll_records"
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_reject_invalid_payroll_month(client):
    save_test_salary(client)
    response = client.post(
        "/payroll/generate",
        data={"employee_id": "1", "payroll_month": "2026-13"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = app_module.get_db_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM payroll_records"
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_mark_payroll_paid(client):
    save_test_salary(client)

    client.post(
        "/payroll/generate",
        data={"employee_id": "1", "payroll_month": "2026-11"},
    )

    conn = app_module.get_db_connection()
    try:
        record = conn.execute(
            """
            SELECT id, payment_status
            FROM payroll_records
            WHERE employee_id = ? AND payroll_month = ?
            """,
            (1, "2026-11"),
        ).fetchone()
        assert record is not None
        assert record["payment_status"] == "Pending"
        payroll_id = record["id"]
    finally:
        conn.close()

    response = client.post(
        f"/payroll/{payroll_id}/status",
        data={"status": "Paid"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = app_module.get_db_connection()
    try:
        updated_record = conn.execute(
            "SELECT payment_status FROM payroll_records WHERE id = ?",
            (payroll_id,),
        ).fetchone()
        assert updated_record is not None
        assert updated_record["payment_status"] == "Paid"
    finally:
        conn.close()


def test_reject_invalid_payment_status(client):
    save_test_salary(client)
    client.post(
        "/payroll/generate",
        data={"employee_id": "1", "payroll_month": "2026-11"},
    )
    response = client.post(
        "/payroll/1/status",
        data={"status": "Cancelled"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = app_module.get_db_connection()
    try:
        record = conn.execute(
            "SELECT payment_status FROM payroll_records WHERE id = ?", (1,)
        ).fetchone()
        assert record["payment_status"] == "Pending"
    finally:
        conn.close()


def test_payroll_requires_admin_login(client):
    client.post("/logout")
    response = client.get("/payroll")
    assert response.status_code == 302

    response = client.post("/payroll/salary", data=salary_data())
    assert response.status_code == 302

    response = client.post(
        "/payroll/generate",
        data={"employee_id": "1", "payroll_month": "2026-11"},
    )
    assert response.status_code == 302

    response = client.post(
        "/payroll/1/status", data={"status": "Paid"}
    )
    assert response.status_code == 302
