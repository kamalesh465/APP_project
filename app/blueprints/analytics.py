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
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold)
    risk = pct[pct["status"] == "At Risk"].sort_values("percentage")
    subject_pct = an.subject_percentages(df, threshold)
    below_subjects = (subject_pct[subject_pct["below_threshold"]]
                      .groupby("student_id")["subject"].agg(list).to_dict()
                      if not subject_pct.empty else {})
    rows = risk.to_dict("records")
    for row in rows:
        row["below_subjects"] = below_subjects.get(row["student_id"], [])
    return render_template("analytics/defaulters.html", rows=rows,
                           total=len(pct))


@bp.route("/trends")
def trends():
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    df = an.load_attendance_df()
    pct = an.student_percentages(df, threshold)
    labels, values = an.weekly_trend(df)
    direction, slope = an.trend_direction(values)
    marks_df = an.load_marks_df()
    r, points = an.attendance_marks_correlation(df, marks_df, threshold)
    subject_pct = an.subject_percentages(df, threshold)
    subject_corr, subject_pair_count, subject_points, subject_corr_reason = (
        an.subject_attendance_marks_correlation(df, marks_df)
    )
    return render_template("analytics/trends.html",
                           labels=labels, values=values,
                           direction=direction, slope=slope,
                           subjects=an.subject_percentages(df).to_dict("records"),
                           depts=an.department_percentages(df).to_dict("records"),
                           stats=an.class_stats(pct), corr=r, points=points,
                           subject_percentages=subject_pct.to_dict("records"),
                           subject_corr=subject_corr,
                           subject_pair_count=subject_pair_count,
                           subject_points=subject_points,
                           subject_corr_reason=subject_corr_reason)


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
