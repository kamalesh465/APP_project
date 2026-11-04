from flask import Blueprint, render_template, request, current_app, flash

from ..services import analytics_service as an

bp = Blueprint("analytics", __name__)

_spark_cache = {}      # keeps the last Spark result so the page is fast to reload


def invalidate_spark_cache():
    """Clear saved results and trigger a refresh on the next Spark page visit."""
    _spark_cache.clear()
    _spark_cache["invalidated"] = True


@bp.route("/defaulters")
def defaulters():
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    pct = an.student_percentages(an.load_attendance_df(), threshold)
    risk = pct[pct["status"] == "At Risk"].sort_values("percentage")
    return render_template("analytics/defaulters.html", rows=risk.to_dict("records"),
                           total=len(pct))


@bp.route("/trends")
def trends():
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold)
    labels, values = an.weekly_trend(df)
    direction, slope = an.trend_direction(values)
    r, points = an.attendance_marks_correlation(df, an.load_marks_df(), threshold)
    return render_template("analytics/trends.html",
                           labels=labels, values=values,
                           direction=direction, slope=slope,
                           subjects=an.subject_percentages(df).to_dict("records"),
                           depts=an.department_percentages(df).to_dict("records"),
                           stats=an.class_stats(pct), corr=r, points=points)


@bp.route("/spark", methods=["GET", "POST"])
def spark():
    refresh = _spark_cache.pop("invalidated", False)
    if request.method == "POST" or refresh:
        try:
            from ..services.spark_service import run_spark_analysis   # lazy import
            _spark_cache["result"] = run_spark_analysis(
                an.load_attendance_df(),
                current_app.config["EXPORT_DIR"],
                current_app.config["ATTENDANCE_THRESHOLD"])
            flash("Spark job completed.", "success")
        except Exception as exc:                                       # Java missing etc.
            flash(f"Spark job failed: {exc}", "danger")
    return render_template("analytics/spark.html", result=_spark_cache.get("result"))
