import os
import csv
import sqlite3
from io import StringIO
from functools import wraps
from datetime import date

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response
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
DEFAULT_DATABASE = DATABASE


def use_postgres():
    # A monkeypatched DATABASE path keeps existing SQLite tests isolated.
    return bool(os.environ.get("DATABASE_URL")) and DATABASE == DEFAULT_DATABASE


class PostgresConnection:
    """Compatibility layer for existing SQLite-style route queries."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        return self.connection.execute(query.replace("?", "%s"), parameters)

    def executemany(self, query, parameters):
        with self.connection.cursor() as cursor:
            cursor.executemany(query.replace("?", "%s"), parameters)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_db_connection():
    if use_postgres():
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            os.environ["DATABASE_URL"],
            row_factory=dict_row,
            connect_timeout=15
        )
        return PostgresConnection(connection)

    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    if use_postgres():
        init_postgres_db()
        return

    conn = get_db_connection()

    try:
        # Serialize initialization across Gunicorn workers
        conn.execute("BEGIN IMMEDIATE")

        # Create employee table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL
            )
        """)

        # Attendance records: one entry per employee per date
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('Present', 'Absent', 'Leave')),
                remarks TEXT,
                UNIQUE (employee_id, attendance_date),
                FOREIGN KEY (employee_id)
                    REFERENCES employees(id) ON DELETE CASCADE
            )
        """)

        # Create admin table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
        """)

        # Check existing employee columns
        existing_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(employees)"
            ).fetchall()
        }

        # Add missing employee columns
        new_columns = {
            "email": "TEXT",
            "phone": "TEXT",
            "designation": "TEXT"
        }

        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE employees ADD COLUMN {column_name} {column_type}"
                )

        # Insert admin only if the username does not already exist
        conn.execute(
            """
            INSERT OR IGNORE INTO admins (username, password_hash)
            VALUES (?, ?)
            """,
            (
                admin_username,
                generate_password_hash(admin_password)
            )
        )

        # Add sample employees only when the table is empty
        count = conn.execute(
            "SELECT COUNT(*) FROM employees"
        ).fetchone()[0]

        if count == 0:
            conn.executemany(
                "INSERT INTO employees (name, department) VALUES (?, ?)",
                [
                    ("Rahul", "IT"),
                    ("Priya", "HR")
                ]
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def init_postgres_db():
    conn = get_db_connection()

    try:
        # Prevent simultaneous Gunicorn workers from initializing together
        conn.execute("SELECT pg_advisory_xact_lock(48291017)")

        # Create employees table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                designation TEXT
            )
        """)

        # Create admins table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id BIGSERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
        """)

        # Create attendance table for PostgreSQL
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id BIGSERIAL PRIMARY KEY,
                employee_id BIGINT NOT NULL
                    REFERENCES employees(id) ON DELETE CASCADE,
                attendance_date DATE NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('Present', 'Absent', 'Leave')),
                remarks TEXT,
                UNIQUE (employee_id, attendance_date)
            )
        """)

        # Add missing employee columns
        for column in ("email", "phone", "designation"):
            conn.execute(
                f"ALTER TABLE employees ADD COLUMN IF NOT EXISTS {column} TEXT"
            )

        # Insert admin if missing
        conn.execute(
            """
            INSERT INTO admins (username, password_hash)
            VALUES (?, ?)
            ON CONFLICT (username) DO NOTHING
            """,
            (
                admin_username,
                generate_password_hash(admin_password)
            )
        )

        # Add sample employees only when the table is empty
        count = conn.execute(
            "SELECT COUNT(*) AS total FROM employees"
        ).fetchone()["total"]

        if count == 0:
            conn.executemany(
                "INSERT INTO employees (name, department) VALUES (?, ?)",
                [
                    ("Rahul", "IT"),
                    ("Priya", "HR")
                ]
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
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

        try:
            admin = conn.execute(
                "SELECT * FROM admins WHERE username = ?",
                (username,)
            ).fetchone()
        finally:
            conn.close()

        if admin and check_password_hash(
            admin["password_hash"], password
        ):
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

    try:
        employees = conn.execute(
            "SELECT * FROM employees ORDER BY id"
        ).fetchall()
    finally:
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
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    designation = request.form.get("designation", "").strip()

    if name and department:
        conn = get_db_connection()

        try:
            conn.execute(
                """
                INSERT INTO employees
                (name, department, email, phone, designation)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    department,
                    email,
                    phone,
                    designation
                )
            )

            conn.commit()

        finally:
            conn.close()

        flash("Employee added successfully.", "success")

    return redirect(url_for("home"))


@app.route("/edit/<int:employee_id>", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_id):
    conn = get_db_connection()

    try:
        employee = conn.execute(
            "SELECT * FROM employees WHERE id = ?",
            (employee_id,)
        ).fetchone()

        if employee is None:
            return "Employee not found", 404

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            department = request.form.get("department", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            designation = request.form.get("designation", "").strip()

            if name and department:
                conn.execute(
                    """
                    UPDATE employees
                    SET name = ?, department = ?, email = ?,
                        phone = ?, designation = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        department,
                        email,
                        phone,
                        designation,
                        employee_id
                    )
                )

                conn.commit()

                flash("Employee updated successfully.", "success")

                return redirect(url_for("home"))

    finally:
        conn.close()

    return render_template("edit.html", employee=employee)


@app.route("/employee/<int:employee_id>")
@admin_required
def employee_profile(employee_id):
    conn = get_db_connection()

    try:
        employee = conn.execute(
            "SELECT * FROM employees WHERE id = ?",
            (employee_id,)
        ).fetchone()
    finally:
        conn.close()

    if employee is None:
        return "Employee not found", 404

    return render_template("profile.html", employee=employee)


# Export employee records to CSV
@app.route("/export")
@admin_required
def export_employees():
    conn = get_db_connection()

    try:
        employees = conn.execute(
            """
            SELECT id, name, email, phone, designation, department
            FROM employees
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Employee ID",
        "Full Name",
        "Email",
        "Phone",
        "Job Designation",
        "Department"
    ])

    for employee in employees:
        writer.writerow([
            employee["id"],
            employee["name"],
            employee["email"] or "",
            employee["phone"] or "",
            employee["designation"] or "",
            employee["department"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=employees.csv"
        }
    )


@app.route("/delete/<int:employee_id>", methods=["POST"])
@admin_required
def delete_employee(employee_id):
    conn = get_db_connection()

    try:
        conn.execute(
            "DELETE FROM employees WHERE id = ?",
            (employee_id,)
        )

        conn.commit()

    finally:
        conn.close()

    flash("Employee deleted successfully.", "success")

    return redirect(url_for("home"))


# ============================================================
# EMPLOYEE ATTENDANCE ROUTES
# ============================================================

@app.route("/attendance", methods=["GET"])
@admin_required
def attendance():
    selected_date = request.args.get(
        "date", date.today().isoformat()
    ).strip()

    try:
        selected_date = date.fromisoformat(selected_date).isoformat()
    except ValueError:
        flash("Invalid attendance date.", "error")
        return redirect(url_for("attendance"))

    conn = get_db_connection()

    try:
        employees = conn.execute(
            """
            SELECT
                e.id,
                e.name,
                e.department,
                a.status,
                a.remarks
            FROM employees AS e
            LEFT JOIN attendance AS a
                ON a.employee_id = e.id
                AND a.attendance_date = ?
            ORDER BY e.id
            """,
            (selected_date,)
        ).fetchall()

    finally:
        conn.close()

    stats = {
        "total": len(employees),
        "present": sum(
            row["status"] == "Present" for row in employees
        ),
        "absent": sum(
            row["status"] == "Absent" for row in employees
        ),
        "leave": sum(
            row["status"] == "Leave" for row in employees
        )
    }

    return render_template(
        "attendance.html",
        employees=employees,
        selected_date=selected_date,
        stats=stats
    )


@app.route("/attendance/mark", methods=["POST"])
@admin_required
def mark_attendance():
    employee_id_text = request.form.get(
        "employee_id", ""
    ).strip()

    attendance_date_text = request.form.get(
        "attendance_date", ""
    ).strip()

    status = request.form.get("status", "").strip()
    remarks = request.form.get("remarks", "").strip()

    try:
        employee_id = int(employee_id_text)

        if employee_id <= 0:
            raise ValueError("Invalid employee ID")

        attendance_date = date.fromisoformat(
            attendance_date_text
        ).isoformat()

    except ValueError:
        flash("Invalid employee or attendance date.", "error")
        return redirect(url_for("attendance"))

    if status not in {"Present", "Absent", "Leave"}:
        flash("Please select a valid attendance status.", "error")
        return redirect(
            url_for("attendance", date=attendance_date)
        )

    if len(remarks) > 250:
        flash("Remarks must be 250 characters or fewer.", "error")
        return redirect(
            url_for("attendance", date=attendance_date)
        )

    conn = get_db_connection()

    try:
        employee = conn.execute(
            "SELECT id FROM employees WHERE id = ?",
            (employee_id,)
        ).fetchone()

        if employee is None:
            flash("Employee not found.", "error")
            return redirect(
                url_for("attendance", date=attendance_date)
            )

        # Insert or update attendance for the selected date
        conn.execute(
            """
            INSERT INTO attendance
                (employee_id, attendance_date, status, remarks)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (employee_id, attendance_date)
            DO UPDATE SET
                status = excluded.status,
                remarks = excluded.remarks
            """,
            (
                employee_id,
                attendance_date,
                status,
                remarks
            )
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    flash("Attendance saved successfully.", "success")

    return redirect(
        url_for("attendance", date=attendance_date)
    )


# Initialize database when Flask/Gunicorn imports this module
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
