from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, template_folder="templates", static_folder="static")

app.config["SECRET_KEY"] = "edutrack-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///edutrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# -------------------------
# DATABASE MODELS
# -------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    name = db.Column(db.String(100))
    email = db.Column(db.String(100))


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))

    department = db.Column(db.String(100))
    semester = db.Column(db.Integer)
    section = db.Column(db.String(20))


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    department = db.Column(db.String(100))


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

    department = db.Column(db.String(100))
    semester = db.Column(db.Integer)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"))

    date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    status = db.Column(db.String(20))

    student = db.relationship("Student")
    subject = db.relationship("Subject")


class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"))

    exam_type = db.Column(db.String(50))
    marks = db.Column(db.Float)

    student = db.relationship("Student")
    subject = db.relationship("Subject")


# -------------------------
# LOGIN
# -------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid username or password")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))


# -------------------------
# DASHBOARD
# -------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    student_count = Student.query.count()
    teacher_count = Teacher.query.count()
    subject_count = Subject.query.count()

    return render_template(
        "dashboard.html",
        student_count=student_count,
        teacher_count=teacher_count,
        subject_count=subject_count
    )


# -------------------------
# STUDENTS
# -------------------------

@app.route("/students")
@login_required
def students():

    students = Student.query.all()

    return render_template(
        "students.html",
        students=students
    )


@app.route("/students/add", methods=["POST"])
@login_required
def add_student():

    student = Student(
        roll_number=request.form.get("roll_number", "").strip(),
        name=request.form.get("name", "").strip(),
        email=request.form.get("email", "").strip() or None,
        department=request.form.get("department", "").strip() or None,
        semester=request.form.get("semester", type=int) or None,
        section=request.form.get("section", "").strip() or None
    )

    db.session.add(student)
    db.session.commit()

    flash("Student added successfully")

    return redirect(url_for("students"))


# -------------------------
# SUBJECTS
# -------------------------

@app.route("/subjects")
@login_required
def subjects():

    subjects = Subject.query.all()

    return render_template(
        "subjects.html",
        subjects=subjects
    )


@app.route("/subjects/add", methods=["POST"])
@login_required
def add_subject():

    subject = Subject(
        code=request.form.get("code", "").strip(),
        name=request.form.get("name", "").strip(),
        department=request.form.get("department", "").strip() or None,
        semester=request.form.get("semester", type=int) or None
    )

    db.session.add(subject)
    db.session.commit()

    flash("Subject added successfully")

    return redirect(url_for("subjects"))


# -------------------------
# ATTENDANCE
# -------------------------

@app.route("/attendance")
@login_required
def attendance():

    records = Attendance.query.all()
    students = Student.query.all()
    subjects = Subject.query.all()

    return render_template(
        "attendance.html",
        records=records,
        students=students,
        subjects=subjects
    )


@app.route("/attendance/add", methods=["POST"])
@login_required
def add_attendance():

    record = Attendance(
        student_id=request.form.get("student_id", type=int),
        subject_id=request.form.get("subject_id", type=int),
        status=request.form.get("status", "")
    )

    db.session.add(record)
    db.session.commit()

    flash("Attendance recorded")

    return redirect(url_for("attendance"))


# -------------------------
# MARKS
# -------------------------

@app.route("/marks")
@login_required
def marks():

    records = Mark.query.all()
    students = Student.query.all()
    subjects = Subject.query.all()

    return render_template(
        "marks.html",
        records=records,
        students=students,
        subjects=subjects
    )


@app.route("/marks/add", methods=["POST"])
@login_required
def add_marks():

    mark = Mark(
        student_id=request.form.get("student_id", type=int),
        subject_id=request.form.get("subject_id", type=int),
        exam_type=request.form.get("exam_type", ""),
        marks=request.form.get("marks", type=float)
    )

    db.session.add(mark)
    db.session.commit()

    flash("Marks added successfully")

    return redirect(url_for("marks"))


# -------------------------
# INITIAL DATABASE
# -------------------------

def create_database():

    db.create_all()

    # Create default admin
    admin = User.query.filter_by(username="admin").first()

    if not admin:

        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin",
            name="Administrator",
            email="admin@edutrack.com"
        )

        db.session.add(admin)

    # Create default teacher
    teacher = User.query.filter_by(username="teacher").first()

    if not teacher:

        teacher = User(
            username="teacher",
            password=generate_password_hash("teacher123"),
            role="teacher",
            name="Demo Teacher",
            email="teacher@edutrack.com"
        )

        db.session.add(teacher)

    db.session.commit()


if __name__ == "__main__":

    with app.app_context():
        create_database()

    app.run(debug=True)
