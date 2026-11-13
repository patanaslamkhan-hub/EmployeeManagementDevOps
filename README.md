
# Employee Management System — DevOps Project

A full-stack Employee Management System developed using Python Flask and PostgreSQL, with automated testing, Docker containerization, and a CI/CD pipeline using GitHub Actions and Render.

## Live Application

**Live Website:** https://employeemanagementdevops.onrender.com

**GitHub Repository:** https://github.com/patanaslamkhan-hub/EmployeeManagementDevOps

## Project Overview

The Employee Management System is a web application designed to manage employee records through a secure administrative dashboard.

The project demonstrates practical DevOps concepts, including version control, automated testing, continuous integration, continuous deployment, containerization, and cloud database integration.

## Key Features

- Secure administrator login and logout
- Add new employee records
- View employee information
- Edit employee details
- Delete employee records
- Individual employee profile pages
- Search employees
- Filter employees by department
- Employee and department statistics
- Department-wise employee overview
- Export employee data to CSV
- Responsive dashboard interface
- CSRF protection for forms
- Persistent PostgreSQL database in production

## Technology Stack

| Category | Technology |
|----------|------------|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Production Database | Neon PostgreSQL |
| Local Database | SQLite |
| Version Control | Git, GitHub |
| Automated Testing | Pytest |
| CI/CD | GitHub Actions |
| Containerization | Docker |
| Application Server | Gunicorn |
| Cloud Hosting | Render |
| Development Environment | Visual Studio Code |

## DevOps Architecture

```text
Developer
    |
    v
VS Code
    |
    v
Git Commit & Push
    |
    v
GitHub Repository (main)
    |
    v
GitHub Actions
    |
    v
Install Dependencies
    |
    v
Run Automated Tests (Pytest)
    |
    v
CI Checks Passed
    |
    v
Render Automatic Deployment
    |
    v
Docker Build
    |
    v
Gunicorn + Flask Application
    |
    v
Neon PostgreSQL Database
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and Render for continuous deployment.

### Continuous Integration

Whenever code is pushed to the `main` branch:

1. GitHub Actions starts automatically.
2. The workflow checks out the repository.
3. Python 3.11 is configured.
4. Project dependencies are installed.
5. Automated tests run using Pytest.
6. The workflow reports success or failure.

### Continuous Deployment

Render is configured to deploy after CI checks pass.

1. GitHub Actions completes successfully.
2. Render automatically starts deployment.
3. Docker builds the application image.
4. Gunicorn starts the Flask application.
5. The application connects to Neon PostgreSQL.
6. The updated application becomes available online.

This process reduces manual deployment work and helps prevent untested changes from reaching production.

## Automated Testing

The project includes automated tests using Pytest.

Latest verified local test result:

```text
11 passed
```

Run the tests locally:

```bash
python -m pytest -v
```

## Local Setup

### Prerequisites

- Python 3.11
- Git
- Visual Studio Code

### Clone the Repository

```bash
git clone https://github.com/patanaslamkhan-hub/EmployeeManagementDevOps.git
```

### Navigate to the Project

```bash
cd EmployeeManagementDevOps
```

### Create a Virtual Environment

```bash
python -m venv .venv
```

### Activate the Virtual Environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
SECRET_KEY=replace-with-a-long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-password
```

Never commit the `.env` file or real credentials to GitHub.

For local development, the application uses SQLite when `DATABASE_URL` is not configured.

For production, configure `DATABASE_URL` with the PostgreSQL connection string provided by Neon.

### Run the Application

```bash
python app.py
```

Open:

http://127.0.0.1:5000

## Docker Support

The application includes a Dockerfile for containerized deployment.

Build the Docker image:

```bash
docker build -t employee-management .
```

Run the Docker container with the required environment variables:

```bash
docker run --rm -p 5000:5000 --env-file .env employee-management
```

Open:

http://127.0.0.1:5000

## Database

The project supports two database environments.

**Development:** SQLite for local development and automated tests.

**Production:** Neon PostgreSQL for persistent cloud storage.

Employee records include:

- Employee ID
- Full Name
- Email Address
- Phone Number
- Designation
- Department

## Security Features

- Administrator authentication
- Password hashing
- Protected application routes
- CSRF protection
- Environment-based configuration
- Credentials excluded from source code

## Deployment

The production application is hosted on Render.

The deployment uses:

- GitHub repository integration
- GitHub Actions CI checks
- Docker-based deployment
- Gunicorn application server
- Neon PostgreSQL database
- Render environment variables

**Production URL:** https://employeemanagementdevops.onrender.com

## Future Enhancements

- Employee attendance management
- Role-based access control
- Employee leave management
- Advanced reporting and analytics
- Pagination for large employee directories
- Additional automated integration tests

## Project Learning Outcomes

This project demonstrates experience with:

- Python web application development
- CRUD operations
- Relational databases
- Git and GitHub workflows
- Docker containerization
- Automated testing with Pytest
- CI/CD using GitHub Actions
- Cloud deployment using Render
- Managed PostgreSQL databases

## Author

**Aslam Khan**

GitHub: https://github.com/patanaslamkhan-hub
