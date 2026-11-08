import math

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Student, Subject, Mark

bp = Blueprint("marks", __name__)


@bp.route("/")
def index():
    marks = (Mark.query.join(Student).join(Subject)
             .order_by(Student.roll_no, Subject.name).limit(200).all())
    return render_template("marks/index.html", marks=marks)


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        try:
            student_id = int(request.form.get("student_id", ""))
            subject_id = int(request.form.get("subject_id", ""))
        except (TypeError, ValueError):
            flash("Select a valid student and subject.", "danger")
            return redirect(url_for("marks.add"))

        student = db.session.get(Student, student_id)
        subject = db.session.get(Subject, subject_id)
        if student is None or subject is None:
            flash("Select a valid student and subject.", "danger")
            return redirect(url_for("marks.add"))
        if (student.department != subject.department
                or student.semester != subject.semester):
            flash("The selected subject does not match the student's department and semester.",
                  "danger")
            return redirect(url_for("marks.add", student_id=student.id))

        try:
            score = float(request.form.get("score", ""))
            max_score = float(request.form.get("max_score", ""))
        except (TypeError, ValueError):
            flash("Enter numeric values for score and maximum score.", "danger")
            return redirect(url_for("marks.add", student_id=student.id))
        if (not math.isfinite(score) or not math.isfinite(max_score)
                or max_score <= 0 or not 0 <= score <= max_score):
            flash("Score must be between 0 and the maximum score, and maximum score must be greater than 0.",
                  "danger")
            return redirect(url_for("marks.add", student_id=student.id))

        try:
            db.session.add(Mark(student_id=student_id,
                                subject_id=subject_id,
                                exam_type=request.form.get("exam_type", "").strip(),
                                score=score,
                                max_score=max_score))
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("The mark could not be saved because of a database error.", "danger")
            return redirect(url_for("marks.add", student_id=student.id))
        from .analytics import invalidate_spark_cache
        invalidate_spark_cache()
        flash("Mark recorded.", "success")
        return redirect(url_for("marks.index"))

    students = Student.query.order_by(Student.roll_no).all()
    subjects = Subject.query.order_by(Subject.name).all()
    student_id = request.args.get("student_id", type=int)
    selected_student = next((student for student in students
                             if student.id == student_id), None)
    if selected_student is None and students:
        selected_student = students[0]
    matching_subjects = [
        subject for subject in subjects
        if selected_student
        and subject.department == selected_student.department
        and subject.semester == selected_student.semester
    ]
    return render_template("marks/form.html",
                           students=students, subjects=matching_subjects,
                           selected_student=selected_student,
                           selected_subject_id=request.args.get("subject_id", ""),
                           student_options=[
                               {"id": student.id, "department": student.department,
                                "semester": student.semester}
                               for student in students
                           ],
                           subject_options=[
                               {"id": subject.id, "code": subject.code,
                                "name": subject.name,
                                "department": subject.department,
                                "semester": subject.semester}
                               for subject in subjects
                           ])
