from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from ..extensions import db
from ..models import Student, Subject, Attendance
from ..services import analytics_service as an

bp = Blueprint("attendance", __name__)


@bp.route("/mark", methods=["GET", "POST"])
def mark():
    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        subject_id = int(request.form["subject_id"])
        d = date.fromisoformat(request.form["date"])
        existing = {a.student_id: a for a in
                    Attendance.query.filter_by(subject_id=subject_id, date=d)}
        for s in Student.query.all():
            status = "Present" if request.form.get(f"present_{s.id}") else "Absent"
            rec = existing.get(s.id)
            if rec:
                rec.status = status
            else:
                db.session.add(Attendance(student_id=s.id, subject_id=subject_id,
                                          date=d, status=status))
        db.session.commit()
        flash("Attendance saved.", "success")
        return redirect(url_for("attendance.mark", subject_id=subject_id, date=d.isoformat()))

    subject_id = request.args.get("subject_id", type=int)
    d_str = request.args.get("date", date.today().isoformat())
    students, existing = [], {}
    if subject_id:
        students = Student.query.order_by(Student.roll_no).all()
        existing = {a.student_id: a.status for a in
                    Attendance.query.filter_by(subject_id=subject_id,
                                               date=date.fromisoformat(d_str))}
    return render_template("attendance/mark.html", subjects=subjects, students=students,
                           existing=existing, subject_id=subject_id, d_str=d_str)


@bp.route("/report")
def report():
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold).sort_values("roll_no")
    subjects, matrix = an.subject_matrix(df)
    return render_template("attendance/report.html", rows=pct.to_dict("records"),
                           subjects=subjects, matrix=matrix)
