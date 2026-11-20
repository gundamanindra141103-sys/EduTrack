import os
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, Course, Attendance, Assignment, Submission, Result, Resource

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.context_processor
def inject_today():
    return {"today": date.today()}

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, valid email and a password of at least 8 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password), role="student")
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please sign in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"Welcome back, {user.name}.", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        stats = {
            "students": User.query.filter_by(role="student").count(),
            "teachers": User.query.filter_by(role="teacher").count(),
            "courses": Course.query.count(),
            "assignments": Assignment.query.count()
        }
        return render_template("dashboard_admin.html", stats=stats,
                               users=User.query.order_by(User.created_at.desc()).limit(6).all())
    if current_user.role == "teacher":
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        course_ids = [c.id for c in courses]
        assignments = Assignment.query.filter(Assignment.course_id.in_(course_ids)).order_by(Assignment.due_date).all() if course_ids else []
        return render_template("dashboard_teacher.html", courses=courses, assignments=assignments)
    courses = Course.query.order_by(Course.title).all()
    assignments = Assignment.query.order_by(Assignment.due_date).all()
    attendance_count = Attendance.query.filter_by(student_id=current_user.id, status="Present").count()
    results = Result.query.filter_by(student_id=current_user.id).order_by(Result.created_at.desc()).limit(5).all()
    return render_template("dashboard_student.html", courses=courses, assignments=assignments,
                           attendance_count=attendance_count, results=results)

@app.route("/admin/users", methods=["GET", "POST"])
@role_required("admin")
def users():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        if role not in ("student", "teacher", "admin") or not name or not email or len(password) < 8:
            flash("Check the entered details. Password must be at least 8 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
        else:
            db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password), role=role))
            db.session.commit()
            flash("User created successfully.", "success")
            return redirect(url_for("users"))
    return render_template("users.html", users=User.query.order_by(User.name).all())

@app.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    if request.method == "POST":
        if current_user.role not in ("admin", "teacher"):
            abort(403)
        title = request.form.get("title", "").strip()
        code = request.form.get("code", "").strip().upper()
        description = request.form.get("description", "").strip()
        teacher_id = current_user.id
        if current_user.role == "admin":
            teacher_id = request.form.get("teacher_id", type=int)
        if not title or not code or Course.query.filter_by(code=code).first():
            flash("Provide a title and unique course code.", "danger")
        elif not User.query.filter_by(id=teacher_id, role="teacher").first():
            flash("Select a valid teacher for this course.", "danger")
        else:
            db.session.add(Course(title=title, code=code, description=description, teacher_id=teacher_id))
            db.session.commit()
            flash("Course created.", "success")
            return redirect(url_for("courses"))
    if current_user.role == "teacher":
        course_list = Course.query.filter_by(teacher_id=current_user.id).all()
    else:
        course_list = Course.query.order_by(Course.title).all()
    teachers = User.query.filter_by(role="teacher").order_by(User.name).all()
    return render_template("courses.html", courses=course_list, teachers=teachers)

@app.route("/attendance", methods=["GET", "POST"])
@role_required("teacher", "admin")
def attendance():
    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        course_id = request.form.get("course_id", type=int)
        status = request.form.get("status")
        day = request.form.get("attendance_date")
        student = User.query.filter_by(id=student_id, role="student").first()
        course = Course.query.get(course_id)
        if not student or not course or status not in ("Present", "Absent", "Late"):
            flash("Please choose valid attendance details.", "danger")
        elif current_user.role == "teacher" and course.teacher_id != current_user.id:
            abort(403)
        else:
            record = Attendance.query.filter_by(student_id=student_id, course_id=course_id, attendance_date=date.fromisoformat(day)).first()
            if record:
                record.status = status
            else:
                db.session.add(Attendance(student_id=student_id, course_id=course_id, status=status, attendance_date=date.fromisoformat(day)))
            db.session.commit()
            flash("Attendance saved.", "success")
            return redirect(url_for("attendance"))
    course_query = Course.query.filter_by(teacher_id=current_user.id) if current_user.role == "teacher" else Course.query
    course_list = course_query.all()
    records = Attendance.query.order_by(Attendance.attendance_date.desc()).limit(100).all()
    return render_template("attendance.html", courses=course_list,
                           students=User.query.filter_by(role="student").order_by(User.name).all(), records=records)

@app.route("/assignments", methods=["GET", "POST"])
@login_required
def assignments():
    if request.method == "POST":
        if current_user.role not in ("teacher", "admin"):
            abort(403)
        course_id = request.form.get("course_id", type=int)
        course = Course.query.get(course_id)
        if not course or (current_user.role == "teacher" and course.teacher_id != current_user.id):
            abort(403)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due = request.form.get("due_date")
        if title and due:
            db.session.add(Assignment(title=title, description=description, due_date=date.fromisoformat(due), course_id=course_id, created_by=current_user.id))
            db.session.commit()
            flash("Assignment published.", "success")
            return redirect(url_for("assignments"))
        flash("Title and due date are required.", "danger")
    if current_user.role == "teacher":
        ids = [c.id for c in Course.query.filter_by(teacher_id=current_user.id).all()]
        items = Assignment.query.filter(Assignment.course_id.in_(ids)).order_by(Assignment.due_date).all() if ids else []
        course_list = Course.query.filter_by(teacher_id=current_user.id).all()
    else:
        items = Assignment.query.order_by(Assignment.due_date).all()
        course_list = Course.query.all()
    return render_template("assignments.html", assignments=items, courses=course_list)

@app.route("/assignments/<int:assignment_id>/submit", methods=["POST"])
@role_required("student")
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    upload = request.files.get("file")
    if not upload or not upload.filename:
        flash("Choose a file to submit.", "danger")
        return redirect(url_for("assignments"))
    filename = secure_filename(upload.filename)
    if not filename or len(filename) > 120:
        flash("Invalid filename.", "danger")
        return redirect(url_for("assignments"))
    stored = f"{current_user.id}_{assignment.id}_{int(datetime.utcnow().timestamp())}_{filename}"
    upload.save(os.path.join(app.config["UPLOAD_FOLDER"], stored))
    existing = Submission.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).first()
    if existing:
        old_path = os.path.join(app.config["UPLOAD_FOLDER"], existing.filename)
        if os.path.exists(old_path):
            os.remove(old_path)
        existing.filename = stored
        existing.submitted_at = datetime.utcnow()
    else:
        db.session.add(Submission(assignment_id=assignment.id, student_id=current_user.id, filename=stored))
    db.session.commit()
    flash("Assignment submitted successfully.", "success")
    return redirect(url_for("assignments"))

@app.route("/results", methods=["GET", "POST"])
@role_required("teacher", "admin", "student")
def results():
    if request.method == "POST":
        if current_user.role not in ("teacher", "admin"):
            abort(403)
        student_id = request.form.get("student_id", type=int)
        course_id = request.form.get("course_id", type=int)
        marks = request.form.get("marks", type=float)
        maximum = request.form.get("maximum_marks", type=float)
        course = Course.query.get(course_id)
        student = User.query.filter_by(id=student_id, role="student").first()
        if not course or not student or marks is None or maximum is None or maximum <= 0 or marks < 0 or marks > maximum:
            flash("Enter valid student, course and marks.", "danger")
        elif current_user.role == "teacher" and course.teacher_id != current_user.id:
            abort(403)
        else:
            db.session.add(Result(student_id=student_id, course_id=course_id, marks=marks, maximum_marks=maximum, created_by=current_user.id))
            db.session.commit()
            flash("Result recorded.", "success")
            return redirect(url_for("results"))
    if current_user.role == "student":
        records = Result.query.filter_by(student_id=current_user.id).order_by(Result.created_at.desc()).all()
        students, course_list = [], []
    else:
        records = Result.query.order_by(Result.created_at.desc()).all()
        students = User.query.filter_by(role="student").order_by(User.name).all()
        course_list = Course.query.filter_by(teacher_id=current_user.id).all() if current_user.role == "teacher" else Course.query.all()
    return render_template("results.html", results=records, students=students, courses=course_list)

@app.route("/resources", methods=["GET", "POST"])
@login_required
def resources():
    if request.method == "POST":
        if current_user.role not in ("teacher", "admin"):
            abort(403)
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip()
        course_id = request.form.get("course_id", type=int)
        course = Course.query.get(course_id)
        if title and url.startswith(("https://", "http://")) and course:
            db.session.add(Resource(title=title, url=url, course_id=course_id, uploaded_by=current_user.id))
            db.session.commit()
            flash("Resource added.", "success")
            return redirect(url_for("resources"))
        flash("Provide a title, valid HTTP(S) URL and course.", "danger")
    items = Resource.query.order_by(Resource.created_at.desc()).all()
    course_list = Course.query.filter_by(teacher_id=current_user.id).all() if current_user.role == "teacher" else Course.query.all()
    return render_template("resources.html", resources=items, courses=course_list)

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The requested page could not be found."), 404

def seed_demo_data():
    if User.query.filter_by(email="admin@edutrack.local").first():
        return
    admin = User(name="System Admin", email="admin@edutrack.local", password_hash=generate_password_hash("Admin@123"), role="admin")
    teacher = User(name="Demo Teacher", email="teacher@edutrack.local", password_hash=generate_password_hash("Teacher@123"), role="teacher")
    student = User(name="Demo Student", email="student@edutrack.local", password_hash=generate_password_hash("Student@123"), role="student")
    db.session.add_all([admin, teacher, student])
    db.session.commit()
    course = Course(title="Introduction to Python", code="PY101", description="Python programming fundamentals.", teacher_id=teacher.id)
    db.session.add(course)
    db.session.commit()
    db.session.add(Assignment(title="Python Basics Worksheet", description="Complete the introductory exercises.", due_date=date.today(), course_id=course.id, created_by=teacher.id))
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_demo_data()
    app.run(debug=True)
