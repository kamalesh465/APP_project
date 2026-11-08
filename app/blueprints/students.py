from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import DEPARTMENTS, Student, Mark
from ..services import analytics_service as an

bp = Blueprint("students", __name__)


@bp.route("/")
def list_students():
    q = request.args.get("q", "").strip()
    query = Student.query
    if q:
        like = f"%{q}%"
        query = query.filter(Student.name.ilike(like) | Student.roll_no.ilike(like))
    return render_template("students/list.html", students=query.order_by(Student.roll_no).all(), q=q)


def _save(student):
    department = request.form.get("department", "").strip()
    semester = request.form.get("semester", "")
    if department not in DEPARTMENTS or semester not in {
        str(value) for value in range(1, 9)
    }:
        return False
    student.roll_no = request.form["roll_no"].strip()
    student.name = request.form["name"].strip()
    student.department = department
    student.semester = int(semester)
    return True


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        try:
            if Student.query.filter_by(roll_no=request.form["roll_no"].strip()).first():
                flash("Roll number already exists.", "danger")
            else:
                s = Student()
                if _save(s):
                    db.session.add(s)
                    db.session.commit()
                    flash("Student added.", "success")
                    return redirect(url_for("students.list_students"))
                flash("Select a valid department and semester (1 through 8).", "danger")
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Unable to add student")
            flash("The student could not be added because of a database error.", "danger")
    return render_template("students/form.html", student=None,
                           departments=DEPARTMENTS)


@bp.route("/<int:sid>/edit", methods=["GET", "POST"])
def edit(sid):
    s = db.get_or_404(Student, sid)
    if request.method == "POST":
        try:
            if _save(s):
                db.session.commit()
                flash("Student updated.", "success")
                return redirect(url_for("students.list_students"))
            flash("Select a valid department and semester (1 through 8).", "danger")
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Unable to update student %s", sid)
            flash("The student could not be updated because of a database error.", "danger")
    return render_template("students/form.html", student=s,
                           departments=DEPARTMENTS)


@bp.route("/<int:sid>/delete", methods=["POST"])
def delete(sid):
    try:
        db.session.delete(db.get_or_404(Student, sid))
        db.session.commit()
        flash("Student deleted.", "info")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Unable to delete student %s", sid)
        flash("The student could not be deleted because of a database error.", "danger")
    return redirect(url_for("students.list_students"))


@bp.route("/<int:sid>")
def detail(sid):
    s = db.get_or_404(Student, sid)
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold)
    row = pct[pct["student_id"] == sid]
    overall = row.iloc[0].to_dict() if not row.empty else None
    labels, values = an.student_weekly_trend(df, sid)
    direction, slope = an.trend_direction(values)
    return render_template("students/detail.html", student=s, overall=overall,
                           subjects=an.student_subject_percentages(df, sid),
                           labels=labels, values=values,
                           direction=direction, slope=slope,
                           marks=Mark.query.filter_by(student_id=sid).all())
