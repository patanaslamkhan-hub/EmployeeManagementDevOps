
import os
import sqlite3
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

# Load local environment variables
load_dotenv()

app = Flask(__name__)

# Security configuration
secret_key = os.environ.get("SECRET_KEY")
admin_username = os.environ.get("ADMIN_USERNAME")
admin_password = os.environ.get("ADMIN_PASSWORD")

if not secret_key or not admin_username or not admin_password:
    raise RuntimeError(
        "SECRET_KEY, ADMIN_USERNAME and ADMIN_PASSWORD must be configured."
    )

app.config["SECRET_KEY"] = secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "false").lower() == "true"
)

csrf = CSRFProtect(app)

# Database configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "data", "employees.db")


def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    # Create the initial admin only if the username does not exist.
    existing_admin = conn.execute(
        "SELECT id FROM admins WHERE username = ?",
        (admin_username,)
    ).fetchone()

    if existing_admin is None:
        conn.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            (admin_username, generate_password_hash(admin_password))
        )

    # Add sample employees only when the employee table is empty.
    count = conn.execute(
        "SELECT COUNT(*) FROM employees"
    ).fetchone()[0]

    if count == 0:
        conn.executemany(
            "INSERT INTO employees (name, department) VALUES (?, ?)",
            [("Rahul", "IT"), ("Priya", "HR")]
        )

    conn.commit()
    conn.close()


def admin_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if "admin_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("home"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
@admin_required
def home():
    conn = get_db_connection()
    employees = conn.execute(
        "SELECT * FROM employees ORDER BY id"
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        employees=employees,
        admin_username=session.get("admin_username")
    )


@app.route("/add", methods=["POST"])
@admin_required
def add_employee():
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()

    if name and department:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO employees (name, department) VALUES (?, ?)",
            (name, department)
        )
        conn.commit()
        conn.close()

    return redirect(url_for("home"))


@app.route("/edit/<int:employee_id>", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_id):
    conn = get_db_connection()

    employee = conn.execute(
        "SELECT * FROM employees WHERE id = ?",
        (employee_id,)
    ).fetchone()

    if employee is None:
        conn.close()
        return "Employee not found", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()

        if name and department:
            conn.execute(
                "UPDATE employees SET name = ?, department = ? WHERE id = ?",
                (name, department, employee_id)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("home"))

    conn.close()
    return render_template("edit.html", employee=employee)


@app.route("/delete/<int:employee_id>", methods=["POST"])
@admin_required
def delete_employee(employee_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM employees WHERE id = ?",
        (employee_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
