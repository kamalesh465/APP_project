from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from ..extensions import db
from ..models import Student, Mark
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
    student.roll_no = request.form["roll_no"].strip()
    student.name = request.form["name"].strip()
    student.department = request.form["department"].strip()
    student.semester = int(request.form["semester"])


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        if Student.query.filter_by(roll_no=request.form["roll_no"].strip()).first():
            flash("Roll number already exists.", "danger")
        else:
            s = Student()
            _save(s)
            db.session.add(s)
            db.session.commit()
            flash("Student added.", "success")
            return redirect(url_for("students.list_students"))
    return render_template("students/form.html", student=None)


@bp.route("/<int:sid>/edit", methods=["GET", "POST"])
def edit(sid):
    s = db.get_or_404(Student, sid)
    if request.method == "POST":
        _save(s)
        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("students.list_students"))
    return render_template("students/form.html", student=s)


@bp.route("/<int:sid>/delete", methods=["POST"])
def delete(sid):
    db.session.delete(db.get_or_404(Student, sid))
    db.session.commit()
    flash("Student deleted.", "info")
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
