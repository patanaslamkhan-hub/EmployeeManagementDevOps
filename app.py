
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

employees = [
    {"id": 1, "name": "Rahul", "department": "IT"},
    {"id": 2, "name": "Priya", "department": "HR"}
]

@app.route("/")
def home():
    return render_template("index.html", employees=employees)

@app.route("/add", methods=["POST"])
def add_employee():
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()

    if name and department:
        employees.append({
            "id": len(employees) + 1,
            "name": name,
            "department": department
        })

    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
