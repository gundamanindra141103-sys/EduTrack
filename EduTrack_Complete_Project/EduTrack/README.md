# EduTrack – Education Management System

A mini-project full-stack web application built with Python Flask, SQLite, SQLAlchemy, HTML, CSS and Bootstrap.

## Features
- Role-based login for admin, teacher and student
- Student self-registration
- Admin user creation and overview dashboard
- Course creation and listing
- Daily attendance entry (one record per student/course/date)
- Assignment publishing and student file submission
- Marks/results recording and student result view
- Study resource links
- Password hashing and role-protected routes

## Requirements
- Python 3.10 or newer
- VS Code
- Internet connection for Bootstrap CDN (optional after local styling is cached)

## Run in VS Code
1. Extract the project ZIP and open the `EduTrack` folder in VS Code.
2. Open Terminal → New Terminal.
3. Create a virtual environment:
   - Windows: `py -m venv .venv`
   - macOS/Linux: `python3 -m venv .venv`
4. Activate it:
   - Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
   - Windows CMD: `.venv\\Scripts\\activate.bat`
   - macOS/Linux: `source .venv/bin/activate`
5. Install packages: `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and set a unique `SECRET_KEY` for non-demo use.
7. Start the app: `python app.py`
8. Open `http://127.0.0.1:5000` in your browser.

The database and demo records are created automatically on first run.

## Demo accounts
| Role | Email | Password |
|---|---|---|
| Admin | admin@edutrack.local | Admin@123 |
| Teacher | teacher@edutrack.local | Teacher@123 |
| Student | student@edutrack.local | Student@123 |

Change or remove these demo credentials before deployment. The app is configured for local educational demonstration, not production deployment.

## Suggested demo flow
1. Sign in as admin and create a teacher/student if needed.
2. Sign in as teacher and create a course.
3. Publish an assignment, record attendance and enter marks.
4. Sign in as student to view assignments, submit a file and check results.
5. Add learning resource links as teacher/admin.

## Project structure
- `app.py` – routes, authentication, role checks and application startup
- `models.py` – SQLAlchemy database models
- `config.py` – application configuration
- `templates/` – Jinja HTML templates
- `static/css/style.css` – custom styling
- `uploads/` – assignment submissions (created automatically)

## Limitations / future enhancements
- Add CSRF protection with Flask-WTF and stricter upload file-type validation.
- Add course enrolment so students only see their enrolled courses.
- Add teacher grading and downloadable submission management.
- Add pagination, audit logs, email notifications and automated tests.
- Configure HTTPS, production WSGI server, secure secrets and cloud database before public deployment.

## Academic integrity / security notes
Passwords are stored as hashes, not plaintext. Do not use the included demo passwords outside a local demonstration. Upload size is limited to 8 MB. For a public production system, add CSRF protection, file-type allowlists, malware scanning, rate limiting, stronger authorization and secure deployment configuration.
