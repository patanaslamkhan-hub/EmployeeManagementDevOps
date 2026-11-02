
import pytest
from app import app, get_db_connection, init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_employees.db"

    monkeypatch.setattr("app.DATABASE", str(test_database))

    init_db()

    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


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

