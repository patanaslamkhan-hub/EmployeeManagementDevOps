import pytest
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_employees.db"

    monkeypatch.setattr(
        app_module, "DATABASE", str(test_database)
    )

    monkeypatch.setattr(app_module, "admin_username", "testadmin")
    monkeypatch.setattr(app_module, "admin_password", "testpassword")

    app_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    app_module.init_db()

    with app_module.app.test_client() as test_client:
        test_client.post(
            "/login",
            data={
                "username": "testadmin",
                "password": "testpassword"
            }
        )

        yield test_client


def test_login_page():
    with app_module.app.test_client() as test_client:
        response = test_client.get("/login")
        assert response.status_code == 200


def test_unauthorized_dashboard_redirect():
    with app_module.app.test_client() as test_client:
        response = test_client.get("/")
        assert response.status_code == 302


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


def test_employee_names(client):
    response = client.get("/")
    assert b"Rahul" in response.data
    assert b"Priya" in response.data


def test_add_employee(client):
    response = client.post(
        "/add",
        data={"name": "Aslam", "department": "DevOps"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Aslam" in response.data


def test_edit_employee(client):
    response = client.post(
        "/edit/1",
        data={"name": "Rahul Updated", "department": "Testing"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Rahul Updated" in response.data
    assert b"Testing" in response.data


def test_delete_employee(client):
    response = client.post(
        "/delete/1",
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Rahul" not in response.data


def test_logout(client):
    response = client.post(
        "/logout",
        follow_redirects=True
    )

    assert response.status_code == 200

    dashboard_response = client.get("/")
    assert dashboard_response.status_code == 302


def test_employee_profile(client):
    response = client.get("/employee/1")

    assert response.status_code == 200
    assert b"Employee Profile" in response.data
    assert b"Rahul" in response.data
    assert b"IT" in response.data


def test_employee_profile_not_found(client):
    response = client.get("/employee/999")

    assert response.status_code == 404
    assert b"Employee not found" in response.data


def test_export_employees_csv(client):
    response = client.get("/export")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment; filename=employees.csv" in response.headers["Content-Disposition"]

    assert b"Employee ID,Full Name,Email,Phone,Job Designation,Department" in response.data
    assert b"Rahul" in response.data
    assert b"Priya" in response.data
