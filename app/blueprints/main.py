from flask import Blueprint, render_template, current_app
from sqlalchemy import func

from ..extensions import db
from ..models import Student, Subject, Attendance, Mark
from ..services import analytics_service as an
from .subjects import subject_csrf_token

bp = Blueprint("main", __name__)


def _subject_record_counts():
    """Return attendance and marks counts keyed by subject ID."""
    counts = {}
    for model, key in ((Attendance, "attendance"), (Mark, "marks")):
        rows = (db.session.query(model.subject_id, func.count(model.id))
                .group_by(model.subject_id).all())
        for subject_id, count in rows:
            counts.setdefault(subject_id, {"attendance": 0, "marks": 0})[key] = count
    return counts


@bp.route("/")
def dashboard():
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold)
    labels, values = an.weekly_trend(df)
    subjects = Subject.query.order_by(Subject.name).all()
    stats = {
        "students": Student.query.count(),
        "subjects": len(subjects),
        "records": Attendance.query.count(),
        "average": an.class_stats(pct)["mean"],
        "at_risk": int((pct["status"] == "At Risk").sum()) if not pct.empty else 0,
    }
    lowest = pct.sort_values("percentage").head(5).to_dict("records")
    return render_template("dashboard.html", stats=stats, lowest=lowest,
                           labels=labels, values=values, subjects=subjects,
                           subject_record_counts=_subject_record_counts(),
                           _subject_csrf_token=subject_csrf_token())
