from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Student, Subject, Attendance
from ..services import analytics_service as an

bp = Blueprint("attendance", __name__)


@bp.route("/mark", methods=["GET", "POST"])
def mark():
    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        try:
            subject_id = int(request.form.get("subject_id", ""))
            d = date.fromisoformat(request.form.get("date", ""))
        except (TypeError, ValueError):
            flash("Select a valid subject and date.", "danger")
            return redirect(url_for("attendance.mark"))

        subject = db.session.get(Subject, subject_id)
        if subject is None:
            flash("Selected subject was not found.", "danger")
            return redirect(url_for("attendance.mark"))
        students = _roster_for(subject)
        if not students:
            return redirect(url_for("attendance.mark", subject_id=subject_id,
                                    date=d.isoformat()))
        try:
            existing = {a.student_id: a for a in
                        Attendance.query.filter_by(subject_id=subject_id, date=d)}
            for s in students:
                status = "Present" if request.form.get(f"present_{s.id}") else "Absent"
                rec = existing.get(s.id)
                if rec:
                    rec.status = status
                else:
                    db.session.add(Attendance(student_id=s.id, subject_id=subject_id,
                                              date=d, status=status))
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Unable to save attendance")
            flash("Attendance could not be saved because of a database error.", "danger")
            return redirect(url_for("attendance.mark", subject_id=subject_id,
                                    date=d.isoformat()))
        from .analytics import invalidate_spark_cache
        invalidate_spark_cache()
        flash("Attendance saved.", "success")
        return redirect(url_for("attendance.mark", subject_id=subject_id, date=d.isoformat()))

    raw_subject_id = request.args.get("subject_id")
    try:
        subject_id = int(raw_subject_id) if raw_subject_id else None
        d_str = request.args.get("date", date.today().isoformat())
        d = date.fromisoformat(d_str)
    except (TypeError, ValueError):
        flash("Select a valid subject and date.", "danger")
        return redirect(url_for("attendance.mark"))
    subject = db.session.get(Subject, subject_id) if subject_id else None
    if subject_id and subject is None:
        flash("Selected subject was not found.", "danger")
        return redirect(url_for("attendance.mark"))
    students, existing = [], {}
    if subject:
        students = _roster_for(subject)
        existing = {a.student_id: a.status for a in
                    Attendance.query.filter_by(subject_id=subject_id,
                                               date=d)}
    return render_template("attendance/mark.html", subjects=subjects, students=students,
                           existing=existing, subject=subject, subject_id=subject_id,
                           d_str=d_str)


def _roster_for(subject):
    return (Student.query.filter_by(department=subject.department,
                                    semester=subject.semester)
            .order_by(Student.roll_no).all())


@bp.route("/report")
def report():
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold).sort_values("roll_no")
    subjects, matrix = an.subject_matrix(df)
    return render_template("attendance/report.html", rows=pct.to_dict("records"),
                           subjects=subjects, matrix=matrix)
