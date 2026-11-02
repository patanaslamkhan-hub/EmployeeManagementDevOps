
from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

# Database configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "data", "employees.db")


# Connect to SQLite database
def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create database and employee table
def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL
        )
    """)

    # Insert default employees only when the table is empty
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
    conn.close()


# Dashboard
@app.route("/")
def home():
    conn = get_db_connection()

    employees = conn.execute(
        "SELECT * FROM employees ORDER BY id"
    ).fetchall()

    conn.close()

    return render_template("index.html", employees=employees)


# Add employee
@app.route("/add", methods=["POST"])
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

    return redirect("/")


# Edit employee
@app.route("/edit/<int:employee_id>", methods=["GET", "POST"])
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
            return redirect("/")

    conn.close()
    return render_template("edit.html", employee=employee)


# Delete employee
@app.route("/delete/<int:employee_id>", methods=["POST"])
def delete_employee(employee_id):
    conn = get_db_connection()

    conn.execute(
        "DELETE FROM employees WHERE id = ?",
        (employee_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# Start Flask application
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)

