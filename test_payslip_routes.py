"""Isolated tests for the authenticated employee payslip download route."""

from io import BytesIO

import pytest
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_payslip.db"
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


def create_payroll(client):
    response = client.post("/payroll/salary", data={
        "employee_id": "1", "basic_salary": "30000", "hra": "8000",
        "allowances": "2000", "deductions": "3000",
    })
    assert response.status_code == 302
    response = client.post("/payroll/generate", data={
        "employee_id": "1", "payroll_month": "2026-11",
    })
    assert response.status_code == 302
    conn = app_module.get_db_connection()
    try:
        record = conn.execute(
            "SELECT id FROM payroll_records WHERE employee_id = ? AND payroll_month = ?",
            (1, "2026-11"),
        ).fetchone()
        assert record is not None
        return record["id"]
    finally:
        conn.close()


def test_payslip_requires_login(client):
    payroll_id = create_payroll(client)
    client.post("/logout")
    response = client.get(f"/payroll/{payroll_id}/payslip")
    assert response.status_code == 302
    assert "/login" in response.location


def test_payslip_missing_record_returns_404(client):
    response = client.get("/payroll/999999/payslip")
    assert response.status_code == 404


def test_payslip_download_is_pdf(client):
    payroll_id = create_payroll(client)
    response = client.get(f"/payroll/{payroll_id}/payslip")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
    assert "attachment" in response.headers["Content-Disposition"]
    assert "no-store" in response.headers.get("Cache-Control", "")


def test_payslip_uses_saved_monthly_salary_snapshot(client, monkeypatch):
    payroll_id = create_payroll(client)
    captured = {}

    def fake_generate_payslip_pdf(payroll):
        captured.update(payroll)
        return BytesIO(b"%PDF-1.4\nmock")

    monkeypatch.setattr(app_module, "generate_payslip_pdf", fake_generate_payslip_pdf)

    # Changing the current salary must not change an already generated payslip.
    client.post("/payroll/salary", data={
        "employee_id": "1", "basic_salary": "50000", "hra": "0",
        "allowances": "0", "deductions": "0",
    })
    response = client.get(f"/payroll/{payroll_id}/payslip")
    assert response.status_code == 200
    assert captured["payroll_month"] == "2026-11"
    assert float(captured["basic_salary"]) == 30000
    assert float(captured["gross_salary"]) == 40000
    assert float(captured["net_salary"]) == 37000
    assert captured["payment_status"] == "Pending"


def test_payslip_reflects_paid_status(client, monkeypatch):
    payroll_id = create_payroll(client)
    response = client.post(
        f"/payroll/{payroll_id}/status", data={"status": "Paid"}
    )
    assert response.status_code == 302
    captured = {}

    def fake_generate_payslip_pdf(payroll):
        captured.update(payroll)
        return BytesIO(b"%PDF-1.4\nmock")

    monkeypatch.setattr(app_module, "generate_payslip_pdf", fake_generate_payslip_pdf)
    response = client.get(f"/payroll/{payroll_id}/payslip")
    assert response.status_code == 200
    assert captured["payment_status"] == "Paid"
