import os
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
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


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

    return redirect(url_for("landing"))


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "")

        if password != confirm_password:
            flash("Passwords do not match")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return render_template("register.html")

        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role,
            name=name,
            email=email
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/loading")
def loading():
    redirect_url = request.args.get("next", url_for("landing"))
    return render_template("loading.html", redirect_url=redirect_url)


# -------------------------
# DASHBOARD
# -------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    student_count = Student.query.count()
    teacher_count = Teacher.query.count()
    subject_count = Subject.query.count()
    user_count = User.query.filter_by(role="teacher").count()

    return render_template(
        "dashboard.html",
        student_count=student_count,
        teacher_count=teacher_count,
        subject_count=subject_count,
        user_count=user_count,
        current_user=current_user
    )


# -------------------------
# STUDENTS
# -------------------------

@app.route("/students")
@login_required
def students():
    search = request.args.get("search", "")
    department_filter = request.args.get("department", "")
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = Student.query

    if search:
        query = query.filter(
            (Student.name.contains(search)) |
            (Student.roll_number.contains(search)) |
            (Student.email.contains(search))
        )

    if department_filter:
        query = query.filter(Student.department == department_filter)

    total = query.count()
    students = query.offset((page - 1) * per_page).limit(per_page).all()

    departments = db.session.query(Student.department).distinct().all()
    departments = [d[0] for d in departments if d[0]]

    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if total > 0 else 1
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self):
            for page_num in range(1, self.pages + 1):
                yield page_num

    pagination = SimplePagination(students, page, per_page, total)

    return render_template(
        "students.html",
        students=pagination,
        search=search,
        department_filter=department_filter,
        departments=departments
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


@app.route("/students/edit/<int:id>", methods=["POST"])
@login_required
def edit_student(id):
    student = Student.query.get_or_404(id)

    student.roll_number = request.form.get("roll_number", "").strip()
    student.name = request.form.get("name", "").strip()
    student.email = request.form.get("email", "").strip() or None
    student.department = request.form.get("department", "").strip() or None
    student.semester = request.form.get("semester", type=int) or None
    student.section = request.form.get("section", "").strip() or None

    db.session.commit()

    flash("Student updated successfully")

    return redirect(url_for("students"))


@app.route("/students/delete/<int:id>", methods=["POST"])
@login_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()

    flash("Student deleted successfully")

    return redirect(url_for("students"))


# -------------------------
# SUBJECTS
# -------------------------

@app.route("/subjects")
@login_required
def subjects():
    search = request.args.get("search", "")
    department_filter = request.args.get("department", "")
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = Subject.query

    if search:
        query = query.filter(
            (Subject.name.contains(search)) |
            (Subject.code.contains(search))
        )

    if department_filter:
        query = query.filter(Subject.department == department_filter)

    total = query.count()
    subjects = query.offset((page - 1) * per_page).limit(per_page).all()

    departments = db.session.query(Subject.department).distinct().all()
    departments = [d[0] for d in departments if d[0]]

    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if total > 0 else 1
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self):
            for page_num in range(1, self.pages + 1):
                yield page_num

    pagination = SimplePagination(subjects, page, per_page, total)

    return render_template(
        "subjects.html",
        subjects=pagination,
        search=search,
        department_filter=department_filter,
        departments=departments
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


@app.route("/subjects/edit/<int:id>", methods=["POST"])
@login_required
def edit_subject(id):
    subject = Subject.query.get_or_404(id)

    subject.code = request.form.get("code", "").strip()
    subject.name = request.form.get("name", "").strip()
    subject.department = request.form.get("department", "").strip() or None
    subject.semester = request.form.get("semester", type=int) or None

    db.session.commit()

    flash("Subject updated successfully")

    return redirect(url_for("subjects"))


@app.route("/subjects/delete/<int:id>", methods=["POST"])
@login_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()

    flash("Subject deleted successfully")

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


# -------------------------
# TEACHER MANAGEMENT (ADMIN ONLY)
# -------------------------

@app.route("/teachers")
@login_required
def teachers():
    if current_user.role != "admin":
        flash("Access denied. Admin only.")
        return redirect(url_for("dashboard"))

    search = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = User.query.filter_by(role="teacher")

    if search:
        query = query.filter(
            (User.name.contains(search)) |
            (User.username.contains(search)) |
            (User.email.contains(search))
        )

    total = query.count()
    teachers = query.offset((page - 1) * per_page).limit(per_page).all()

    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if total > 0 else 1
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self):
            for page_num in range(1, self.pages + 1):
                yield page_num

    pagination = SimplePagination(teachers, page, per_page, total)

    return render_template(
        "teachers.html",
        teachers=pagination,
        search=search
    )


@app.route("/teachers/add", methods=["POST"])
@login_required
def add_teacher():
    if current_user.role != "admin":
        flash("Access denied. Admin only.")
        return redirect(url_for("dashboard"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if User.query.filter_by(username=username).first():
        flash("Username already exists")
        return redirect(url_for("teachers"))

    user = User(
        username=username,
        password=generate_password_hash(password),
        role="teacher",
        name=name,
        email=email
    )

    db.session.add(user)
    db.session.commit()

    flash("Teacher account created successfully")

    return redirect(url_for("teachers"))


@app.route("/teachers/edit/<int:id>", methods=["POST"])
@login_required
def edit_teacher(id):
    if current_user.role != "admin":
        flash("Access denied. Admin only.")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(id)

    if user.role != "teacher":
        flash("Cannot edit non-teacher accounts")
        return redirect(url_for("teachers"))

    user.name = request.form.get("name", "").strip()
    user.email = request.form.get("email", "").strip()

    password = request.form.get("password", "")
    if password:
        user.password = generate_password_hash(password)

    db.session.commit()

    flash("Teacher updated successfully")

    return redirect(url_for("teachers"))


@app.route("/teachers/delete/<int:id>", methods=["POST"])
@login_required
def delete_teacher(id):
    if current_user.role != "admin":
        flash("Access denied. Admin only.")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(id)

    if user.role != "teacher":
        flash("Cannot delete non-teacher accounts")
        return redirect(url_for("teachers"))

    db.session.delete(user)
    db.session.commit()

    flash("Teacher deleted successfully")

    return redirect(url_for("teachers"))


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

    port = int(os.environ.get("PORT", 5000))

    with app.app_context():
        create_database()

    app.run(host="0.0.0.0", port=port, debug=False)
