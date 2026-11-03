from flask import Blueprint, render_template, current_app

from ..models import Student, Subject, Attendance
from ..services import analytics_service as an

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold)
    labels, values = an.weekly_trend(df)
    stats = {
        "students": Student.query.count(),
        "subjects": Subject.query.count(),
        "records": Attendance.query.count(),
        "average": an.class_stats(pct)["mean"],
        "at_risk": int((pct["status"] == "At Risk").sum()) if not pct.empty else 0,
    }
    lowest = pct.sort_values("percentage").head(5).to_dict("records")
    return render_template("dashboard.html", stats=stats, lowest=lowest,
                           labels=labels, values=values)
